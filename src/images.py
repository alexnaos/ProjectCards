"""images.py — Поиск и рендеринг чертежей из PDF."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from .logger import get_logger

logger = get_logger(__name__)
pymupdf.TOOLS.mupdf_display_errors(False)

def render_best_drawings_from_pdfs(
    folder_path: Path,
    output_dir: Path,
    max_images: int = 4,
    dpi: int = 150
) -> list[Path]:
    """Ищет PDF, анализирует штампы и жестко фильтрует текст/таблицы."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths = []
    
    pdf_files = list(folder_path.rglob("*.pdf"))
    pdf_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # Слова, которые ДОЛЖНЫ быть в штампе чертежа
    GOOD_WORDS = ["план", "фасад", "разрез", "чертеж", "генплан", "стройгенплан"]
    # Слова, которых НЕ ДОЛЖНО быть (текст, разделы, таблицы)
    BAD_WORDS = [
        "ведомость", "содержание", "спецификация", "смета", "договор", "акт", 
        "письмо", "заключение", "пояснительная", "таблица", "раздел", "текстовая", "записка"
    ]

    for pdf_file in pdf_files:
        if len(rendered_paths) >= max_images:
            break

        try:
            doc = pymupdf.open(str(pdf_file))
            
            for page_num in range(min(len(doc), 100)):
                if len(rendered_paths) >= max_images:
                    break

                page = doc[page_num]
                rect = page.rect
                
                # 1. Жесткий лимит по тексту. Если текста больше 1200 символов — это документ.
                full_text = page.get_text("text").lower()
                text_length = len(full_text)
                if text_length > 1200:
                    continue

                # 2. Если есть слова-маркеры таблиц/разделов — пропускаем
                if any(bad in full_text for bad in BAD_WORDS):
                    continue

                # 3. Вырезаем ТОЛЬКО правый нижний угол (штамп)
                # От 60% ширины и 60% высоты. Так мы не захватим текст из тела чертежа.
                clip_rect = pymupdf.Rect(rect.width * 0.6, rect.height * 0.6, rect.width, rect.height)
                stamp_text = page.get_text("text", clip=clip_rect).lower()
                
                # 4. В штампе ДОЛЖНЫ быть слова-маркеры чертежа
                if not any(good in stamp_text for good in GOOD_WORDS):
                    continue
                    
                # 5. В штампе НЕ ДОЛЖНО быть плохих слов
                if any(bad in stamp_text for bad in BAD_WORDS):
                    continue

                # 6. Проверяем графику (чтобы отсечь пустые листы)
                drawings_count = len(page.get_drawings())
                has_large_image = any(img[2] > 1500 and img[3] > 1500 for img in page.get_images())
                
                if drawings_count < 50 and not has_large_image:
                    continue

                # ЕСЛИ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ — РЕНДЕРИМ
                pix = page.get_pixmap(dpi=dpi)
                out_name = f"{pdf_file.stem}_p{page_num + 1}.png"
                out_path = output_dir / "".join(c for c in out_name if c.isalnum() or c in "._- ")
                
                pix.save(str(out_path))
                rendered_paths.append(out_path)
                logger.info(f"  Найден чертеж: {pdf_file.name} (Стр. {page_num+1}). Линий: {drawings_count}, Текста: {text_length}")
                    
            doc.close()
        except Exception as e:
            logger.warning(f"  Ошибка анализа PDF {pdf_file.name}: {e}")

    return rendered_paths

def find_and_render_plans(folder_path: Path, config: dict, output_subdir: str = "_attachments") -> dict:
    attachments_dir = Path(config.get("attachments_dir", output_subdir))
    folder_slug = folder_path.name
    max_plan_images = config.get("images", {}).get("max_plan_images", 4)
    
    attachments_subdir = folder_path.parent / attachments_dir / folder_slug
    
    rendered_images = render_best_drawings_from_pdfs(
        folder_path=folder_path,
        output_dir=attachments_subdir,
        max_images=max_plan_images
    )
    
    result = {"cover": None, "schematics": []}
    
    if rendered_images:
        result["cover"] = rendered_images[0]
        result["schematics"] = [str(p.relative_to(folder_path.parent)) for p in rendered_images]

    return result