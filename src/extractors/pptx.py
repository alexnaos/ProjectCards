"""pptx.py — извлечение текста из PPTX файлов.

Содержит функцию для извлечения текста из презентаций PowerPoint (.pptx)
с использованием python-pptx.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Union

try:
    from pptx import Presentation
    from pptx.util import Inches
except ImportError:
    Presentation = None
    Inches = None


def extract_text_from_pptx(
    file_path: Union[str, Path],
    max_chars: int = 8000,
) -> Optional[str]:
    """Извлечь текст из PPTX файла.

    Args:
        file_path: Путь к PPTX файлу.
        max_chars: Максимальное количество символов для извлечения.

    Returns:
        Текстовое содержимое PPTX файла или None если не удалось извлечь.
    """
    if Presentation is None:
        print("python-pptx not installed. PPTX extraction unavailable.")
        return None

    try:
        prs = Presentation(str(file_path))

        text_parts: List[str] = []
        total_chars = 0

        # Извлекаем текст из слайдов
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        if paragraph.text.strip():
                            text_parts.append(paragraph.text.strip())
                            total_chars += len(paragraph.text)

                            if total_chars >= max_chars:
                                remaining = total_chars - max_chars
                                text_parts.append(f"\n\n... [обрезано, осталось {remaining} chars] ...")
                                prs = None  # Release resource
                                return " ".join(text_parts)

                # Also extract from tables in the slide
                if shape.has_table:
                    table = shape.table
                    for row in table.rows:
                        for cell in row.cells:
                            if cell.text.strip():
                                text_parts.append(cell.text.strip())
                                total_chars += len(cell.text)

                                if total_chars >= max_chars:
                                    remaining = total_chars - max_chars
                                    text_parts.append(f"\n\n... [обрезано, осталось {remaining} chars] ...")
                                    prs = None
                                    return " ".join(text_parts)

        if not text_parts:
            return None

        result = " ".join(text_parts)
        return result

    except Exception as e:
        print(f"Error extracting text from PPTX {file_path}: {e}")
        return None