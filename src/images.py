"""images.py — Поиск и рендеринг чертежей из PDF с помощью planlens."""

from __future__ import annotations

from pathlib import Path

import pymupdf
from planlens.document import open_document

from .exclusions import is_excluded
from .logger import get_logger

logger = get_logger(__name__)
pymupdf.TOOLS.mupdf_display_errors(False)

def render_best_drawings_from_pdfs(
    folder_path: Path,
    output_dir: Path,
    config: dict,
    max_images: int = 4,
    dpi: int = 150
) -> list[Path]:
    """Ищет PDF, использует planlens для поиска чертежей и рендерит их."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths = []
    
    # Ищем все PDF и сортируем по дате (сначала новые)
    pdf_files = list(folder_path.rglob("*.pdf"))
    
    # Фильтруем исключенные файлы
    valid_pdfs = []
    for f in pdf_files:
        rel_path = f.relative_to(folder_path.parent)
        excl, _ = is_excluded(rel_path, is_dir=False, config=config)
        if not excl:
            valid_pdfs.append(f)
            
    valid_pdfs.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    for pdf_file in valid_pdfs:
        if len(rendered_paths) >= max_images:
            break

        try:
            with open_document(str(pdf_file)) as doc:
                # Ищем страницы, которые planlens определил как "drawing_sheet"
                drawing_pages = [row.page for row in doc.page_map() if row.kind == "drawing_sheet"]
                
                if not drawing_pages:
                    continue

                doc_pymupdf = pymupdf.open(str(pdf_file))
                for page_num in drawing_pages:
                    if len(rendered_paths) >= max_images:
                        break
                        
                    page_index = max(0, min(page_num, len(doc_pymupdf) - 1))
                    page = doc_pymupdf[page_index]
                    
                    pix = page.get_pixmap(dpi=dpi)
                    out_name = f"{pdf_file.stem}_p{page_num + 1}.png"
                    out_path = output_dir / "".join(c for c in out_name if c.isalnum() or c in "._- ")
                    
                    pix.save(str(out_path))
                    rendered_paths.append(out_path)
                    logger.info(f"  Найден чертеж (planlens): {pdf_file.name} (Стр. {page_num + 1})")
                
                doc_pymupdf.close()
                    
        except Exception as e:
            logger.warning(f"  Ошибка анализа PDF {pdf_file.name}: {e}")

    return rendered_paths

def find_and_render_plans(folder_path: Path, config: dict, output_subdir: str = "_attachments") -> dict:
    """Основная функция: найти обложку и схемы ТОЛЬКО из PDF."""
    vault_root = folder_path
    while vault_root.parent != vault_root:
        if (vault_root / output_subdir).exists(): break
        vault_root = vault_root.parent
        
    attachments_root = vault_root / output_subdir
    attachments_subdir = attachments_root / folder_path.name
    
    max_plan_images = config.get("images", {}).get("max_plan_images", 4)
    
    rendered_images = render_best_drawings_from_pdfs(
        folder_path=folder_path,
        output_dir=attachments_subdir,
        config=config,
        max_images=max_plan_images
    )
    
    result = {"cover": None, "schematics": []}
    
    if rendered_images:
        result["cover"] = rendered_images[0]
        result["schematics"] = [str(p.relative_to(vault_root)) for p in rendered_images]

    return result