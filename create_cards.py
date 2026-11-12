import re
from pathlib import Path

import docx
import pymupdf
import yaml

from src.address import extract_address
from src.exclusions import is_excluded
from src.images import find_and_render_plans
from src.logger import get_logger
from src.summarizer import summarize

logger = get_logger(__name__)
MAX_FILE_SIZE = 20 * 1024 * 1024
pymupdf.TOOLS.mupdf_display_errors(False)

def get_project_folders(vault: Path, config: dict) -> list[Path]:
    projects = []
    containers = config.get("project_detection", {}).get("container_folders", [])
    
    for item in vault.iterdir():
        if not item.is_dir() or item.name.startswith("."): continue
        excl, _ = is_excluded(item.relative_to(vault), is_dir=True, config=config)
        if excl: continue
        
        if item.name in containers:
            for sub_item in item.iterdir():
                if sub_item.is_dir() and not sub_item.name.startswith("."):
                    sub_excl, _ = is_excluded(sub_item.relative_to(vault), is_dir=True, config=config)
                    if not sub_excl: projects.append(sub_item)
        else:
            projects.append(item)
    return projects

def extract_docx_data(file_path: Path):
    doc = docx.Document(str(file_path))
    text = []
    meta = {}
    cp = doc.core_properties
    
    meta['title'] = cp.title or ""
    meta['subject'] = cp.subject or ""
    meta['comments'] = cp.comments or ""
    
    if cp.title: text.append(cp.title)
    if cp.subject: text.append(cp.subject)
    if cp.comments: text.append(cp.comments)
    
    for p in doc.paragraphs:
        if p.text.strip(): text.append(p.text.strip())
    for table in doc.tables:
        for row in table.rows:
            text.append(" | ".join(c.text for c in row.cells if c.text))
            
    return "\n".join(text), meta

def get_project_data(folder: Path, config: dict):
    texts = []
    best_meta = {}
    
    # 1. Ищем метаданные в Word
    for f in folder.rglob("*.docx"):
        if is_excluded(f.relative_to(folder.parent), is_dir=False, config=config)[0]: continue
        try:
            txt, meta = extract_docx_data(f)
            # Если в свойствах есть адрес или объект - это то, что нужно
            if meta.get('comments') and ("адрес" in meta['comments'].lower() or "объект" in meta['comments'].lower()):
                best_meta = meta
                texts.append(txt)
                break
        except: pass

    # 2. Если метаданных нет, собираем текст из ТОП-5 файлов
    if not best_meta:
        files_to_read = []
        for f in folder.rglob("*"):
            if not f.is_file(): continue
            if is_excluded(f.relative_to(folder.parent), is_dir=False, config=config)[0]: continue
            if f.stat().st_size > MAX_FILE_SIZE: continue
            if f.suffix.lower() in [".pdf", ".docx"]:
                files_to_read.append(f)
        
        files_to_read.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        for f in files_to_read[:5]:
            try:
                if f.suffix.lower() == ".docx":
                    txt, _ = extract_docx_data(f)
                    texts.append(txt)
                elif f.suffix.lower() == ".pdf":
                    doc = pymupdf.open(str(f))
                    texts.append("\n".join(doc[i].get_text("text") for i in range(min(10, len(doc)))))
                    doc.close()
            except: pass
            
    return texts, best_meta

def process_project(folder: Path, vault: Path, config: dict):
    logger.info(f"АНАЛИЗ: {folder.name}")
    
    texts, best_meta = get_project_data(folder, config)
    
    # --- Адрес ---
    address = ""
    if best_meta.get('comments'):
        clean = best_meta['comments'].replace('\n', ' ')
        m = re.search(r'по\s+адресу\s*:\s*(.+)', clean, re.IGNORECASE)
        if m: address = m.group(1).strip().rstrip('.,; ')
    if not address:
        address = extract_address(texts, config)
        
    if address == "Не определено": address = ""
        
    # --- Описание ---
    description = ""
    if best_meta.get('comments'):
        clean = best_meta['comments'].replace('\n', ' ')
        m = re.search(r'«([^»]+)»', clean)
        if m: description = f"Объект: «{m.group(1)}»"
        else: description = clean[:250]
    if not description:
        description = summarize(texts, config)
        
    logger.info(f"  -> Адрес: {address}")
    logger.info(f"  -> Описание: {description}")

    # --- Картинки (ТОЛЬКО PDF) ---
    img_results = find_and_render_plans(folder, config)
    cover = img_results.get("cover")
    schematics = img_results.get("schematics", [])
    
    # --- Объем ---
    valid_files = [f for f in folder.rglob("*") if f.is_file() and not is_excluded(f.relative_to(folder.parent), is_dir=False, config=config)[0]]
    file_count = len(valid_files)
    total_size = sum(f.stat().st_size for f in valid_files)
    size_mb = round(total_size / (1024 * 1024), 1)

    cover_str = f"![[{Path(cover).name}]]" if cover else ""
    schematics_str = [f"![[{Path(s).name}]]" for s in schematics]
    
    card_data = {
        "title": folder.name,
        "created": "2026-11-12",
        "modified": "2026-11-12",
        "description": description,
        "tags": ["project"],
        "address": address,
        "volume_files": file_count,
        "volume_size_mb": size_mb,
        "cover": cover_str,
        "schematics": schematics_str
    }

    card_path = folder / f"{folder.name}.md"
    with open(card_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(card_data, f, allow_unicode=True, sort_keys=False)
        f.write("---\n\n# Схемы\n")
        f.writelines(f"{s}\n" for s in card_data["schematics"])
        
    logger.info(f"✅ Сохранено: {card_path.name}")

def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    vault = Path(config.get("vault_path", r"C:\test"))
    
    projects = get_project_folders(vault, config)
    logger.info(f"Найдено проектов: {len(projects)}")
    
    for project in projects:
        process_project(project, vault, config)

if __name__ == "__main__":
    main()