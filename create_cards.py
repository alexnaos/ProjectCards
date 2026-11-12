import re
from pathlib import Path

import docx
import pymupdf
import yaml

from src.address import extract_address
from src.images import find_and_render_plans
from src.logger import get_logger
from src.summarizer import summarize

pymupdf.TOOLS.mupdf_display_errors(False)
logger = get_logger(__name__)
MAX_FILE_SIZE = 20 * 1024 * 1024

def extract_docx_data(file_path: Path):
    doc = docx.Document(str(file_path))
    text = []
    meta = {}
    cp = doc.core_properties
    
    meta['doc_title'] = cp.title or ""
    meta['doc_subject'] = cp.subject or ""
    meta['doc_tags'] = cp.keywords or ""
    meta['doc_comments'] = cp.comments or ""
    meta['doc_category'] = cp.category or ""
    meta['doc_status'] = cp.content_status or ""
    
    if cp.title: text.append(f"Название: {cp.title}")
    if cp.subject: text.append(f"Тема: {cp.subject}")
    if cp.comments: text.append(f"Примечания: {cp.comments}")
    
    for p in doc.paragraphs:
        if p.text.strip(): text.append(p.text.strip())
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join([cell.text.strip().replace('\n', ' ') for cell in row.cells if cell.text.strip()])
            if row_text: text.append(row_text)
            
    return "\n".join(text), meta

def extract_pdf_text(file_path: Path) -> str:
    try:
        doc = pymupdf.open(str(file_path))
        text = []
        for page_num in range(min(len(doc), 15)):
            try: text.append(doc[page_num].get_text("text"))
            except: pass
        doc.close()
        return "\n".join(text)
    except Exception as e:
        logger.warning(f"Ошибка чтения PDF {file_path.name}: {e}")
        return ""

def get_project_data(folder: Path):
    texts = []
    best_meta = {}
    
    # ШАГ 1: Ищем Word-файлы с метаданными. Они в приоритете.
    for f in folder.rglob("*.docx"):
        if f.name.startswith("~$") or "_attachments" in str(f): continue
        try:
            doc = docx.Document(str(f))
            cp = doc.core_properties
            
            if cp.comments and ("адресу" in cp.comments.lower() or "объект" in cp.comments.lower() or "здание" in cp.comments.lower()):
                best_meta = {
                    'doc_title': cp.title or "—",
                    'doc_subject': cp.subject or "—",
                    'doc_tags': cp.keywords or "—",
                    'doc_comments': cp.comments or "—",
                    'doc_category': cp.category or "—",
                    'doc_status': cp.content_status or "—",
                }
                texts.append(cp.comments)
                if cp.title: texts.append(cp.title)
                break 
        except Exception as e:
            logger.warning(f"Ошибка чтения DOCX {f.name}: {e}")

    # ШАГ 2: Если метаданных нет, собираем текст из ТОП-5 важных файлов
    if not best_meta:
        files_to_read = []
        for f in folder.rglob("*"):
            if not f.is_file() or "_attachments" in str(f) or f.stat().st_size > MAX_FILE_SIZE: continue
            ext = f.suffix.lower()
            if ext not in [".pdf", ".docx", ".txt", ".md"]: continue
                
            score = 0
            name_lower = f.name.lower()
            if any(word in name_lower for word in ["титул", "пз", "пзу", "ппт", "сп ", "сп-"]): score += 5000
            if any(word in name_lower for word in ["договор", "смет", "акт"]): score -= 5000
            
            score += f.stat().st_mtime 
            files_to_read.append((score, f, ext))
            
        files_to_read.sort(key=lambda x: x[0], reverse=True)
        
        for score, f, ext in files_to_read[:5]:
            try:
                if ext == ".docx":
                    txt, _ = extract_docx_data(f)
                    texts.append(txt)
                elif ext == ".pdf":
                    txt = extract_pdf_text(f)
                    if txt.strip(): texts.append(txt)
                elif ext in [".txt", ".md"]:
                    texts.append(f.read_text(encoding="utf-8", errors="ignore"))
            except Exception as e:
                logger.warning(f"Ошибка при обработке {f.name}: {e}")

    return texts, best_meta

def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    vault_path = Path(config.get("vault_path", r"C:\test"))
    
    for folder in vault_path.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"): continue
        logger.info(f"АНАЛИЗ: {folder.name}")

        texts, best_meta = get_project_data(folder)
        
        # --- Определение АДРЕСА ---
        address = ""
        if best_meta.get('doc_comments'):
            clean_comments = best_meta['doc_comments'].replace('\n', ' ').replace('\r', ' ')
            m = re.search(r'по\s+адресу\s*:\s*(.+)', clean_comments, re.IGNORECASE)
            if m:
                address = m.group(1).strip().rstrip('.,; ')
        
        if not address:
            address = extract_address(texts, config)
            
        if address == "Не определено" or not address:
            address = ""

        # --- Определение ОПИСАНИЯ --- (Исправлено)
        description = ""
        if best_meta.get('doc_comments'):
            clean_comments = best_meta['doc_comments'].replace('\n', ' ').replace('\r', ' ').strip()
            
            # Если есть название в кавычках
            m = re.search(r'«([^»]+)»', clean_comments)
            if m:
                description = f"Объект: «{m.group(1)}»"
            else:
                # Если кавычек нет, берем весь текст примечаний (до 250 символов)
                description = clean_comments[:250]
                if len(clean_comments) > 250:
                    description += "..."
                
        if not description:
            description = summarize(texts, config)
            
        if description == "Описание не сформировано." or not description:
            description = ""

        logger.info(f"  -> Адрес: {address if address else '—'}")
        logger.info(f"  -> Описание: {description if description else '—'}")

        img_results = find_and_render_plans(folder, config)
        cover = img_results.get("cover")
        schematics = img_results.get("schematics", [])
                
        card_data = {
            "title": folder.name,
            "created": "2026-11-12", 
            "modified": "2026-11-12",
            "description": description, 
            "tags": ["project"], 
            "address": address,
            "volume_files": sum(1 for _ in folder.rglob("*") if _.is_file() and "_attachments" not in str(_)),
            "volume_size_mb": round(sum(f.stat().st_size for f in folder.rglob("*") if f.is_file() and "_attachments" not in str(f)) / (1024 * 1024), 1),
            "cover": f"![[{cover.name}]]" if cover else "",
            "schematics": [f"![[{Path(s).name}]]" for s in schematics],
            
            "doc_title": best_meta.get('doc_title', '—'),
            "doc_subject": best_meta.get('doc_subject', '—'),
            "doc_tags": best_meta.get('doc_tags', '—'),
            "doc_comments": best_meta.get('doc_comments', '—'),
            "doc_category": best_meta.get('doc_category', '—'),
            "doc_status": best_meta.get('doc_status', '—'),
        }

        with open(folder / f"{folder.name}.md", "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.dump(card_data, f, allow_unicode=True, sort_keys=False)
            f.write("---\n\n# Схемы\n")
            f.writelines(f"{s}\n" for s in card_data["schematics"])

if __name__ == "__main__":
    main()