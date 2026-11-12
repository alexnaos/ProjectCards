from pathlib import Path

import docx
import openpyxl
import pymupdf  # для PDF
import yaml
from pptx import Presentation

from src.address import extract_address
from src.images import find_and_render_plans
from src.logger import get_logger
from src.summarizer import summarize

logger = get_logger(__name__)

# Максимальный размер файла для чтения (15 МБ). Большие тома PDF будут пропущены.
MAX_FILE_SIZE = 15 * 1024 * 1024

def extract_pdf_text(file_path: Path) -> str:
    doc = pymupdf.open(str(file_path))
    text = []
    # Читаем только первые 50 страниц, чтобы не зависать
    for page_num in range(min(len(doc), 50)):
        text.append(doc[page_num].get_text("text"))
    doc.close()
    return "\n".join(text)

def extract_docx_text(file_path: Path) -> str:
    doc = docx.Document(str(file_path))
    return "\n".join([p.text for p in doc.paragraphs])

def extract_xlsx_text(file_path: Path) -> str:
    wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
    text = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            text.extend([str(cell) for cell in row if cell is not None])
    wb.close()
    return " ".join(text)

def extract_pptx_text(file_path: Path) -> str:
    prs = Presentation(str(file_path))
    text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)
    return "\n".join(text)

def extract_txt_text(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="cp1251", errors="ignore")

def collect_texts(folder: Path) -> list[str]:
    texts = []
    for f in folder.rglob("*"):
        if not f.is_file() or "_attachments" in str(f):
            continue
        
        # Защита от гигантских файлов
        if f.stat().st_size > MAX_FILE_SIZE:
            logger.info(f"Пропуск (слишком большой): {f.name}")
            continue
            
        ext = f.suffix.lower()
        try:
            if ext == ".pdf":
                texts.append(extract_pdf_text(f))
            elif ext == ".docx":
                texts.append(extract_docx_text(f))
            elif ext == ".xlsx":
                texts.append(extract_xlsx_text(f))
            elif ext == ".pptx":
                texts.append(extract_pptx_text(f))
            elif ext in [".md", ".txt", ".csv", ".json"]:
                texts.append(extract_txt_text(f))
        except Exception as e:
            logger.warning(f"Ошибка чтения {f.name}: {e}")
            
    return [t for t in texts if t.strip()]

def main():
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.error("config.yaml не найден!")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    vault_path = Path(config.get("vault_path", r"C:\test"))
    if not vault_path.exists():
        logger.error(f"Папка Vault не найдена: {vault_path}")
        return

    logger.info(f"Сканирую Vault: {vault_path}")

    for folder in vault_path.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue

        logger.info(f"Обработка проекта: {folder.name}")

        texts = collect_texts(folder)
        
        if not texts:
            logger.warning(f"В папке {folder.name} не найдено текстов. Создаю пустую карточку.")

        description = summarize(texts, config)
        address = extract_address(texts, config)

        img_results = find_and_render_plans(folder, config)
        cover = img_results.get("cover")
        schematics = img_results.get("schematics", [])

        file_count = 0
        total_size = 0
        for f in folder.rglob("*"):
            if f.is_file() and f.name != f"{folder.name}.md" and "_attachments" not in str(f):
                file_count += 1
                total_size += f.stat().st_size
        size_mb = round(total_size / (1024 * 1024), 1)

        cover_str = f"![[{cover.name}]]" if cover else ""
        
        card_data = {
            "title": folder.name,
            "source": "",
            "author": "",
            "publish": False,
            "published": None,
            "created": "2026-11-12",
            "modified": "2026-11-12",
            "description": description,
            "tags": ["project"],
            "address": address,
            "rating": None,
            "volume_files": file_count,
            "volume_size_mb": size_mb,
            "cover": cover_str,
            "schematics": [f"![[{Path(s).name}]]" for s in schematics]
        }

        card_path = folder / f"{folder.name}.md"
        body_text = f"# Проект: {folder.name}\n\nАвтоматически сгенерированная карточка.\n\n## Схемы\n"
        for s in card_data["schematics"]:
            body_text += f"{s}\n"

        with open(card_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.dump(card_data, f, allow_unicode=True, sort_keys=False)
            f.write("---\n\n")
            f.write(body_text)

        logger.info(f"✅ Карточка создана: {card_path.name}")

if __name__ == "__main__":
    main()