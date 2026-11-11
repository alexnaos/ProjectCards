"""pdf.py — извлечение текста из PDF файлов.

Содержит функцию для извлечения текста из PDF документов с использованием pymupdf (fitz).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Union

try:
    import pymupdf  # fitz
except ImportError:
    pymupdf = None


def extract_text_from_pdf(
    file_path: Union[str, Path],
    max_chars: int = 8000,
    start_page: int = 1,
    end_page: Optional[int] = None,
) -> Optional[str]:
    """Извлечь текст из PDF файла.

    Args:
        file_path: Путь к PDF файлу.
        max_chars: Максимальное количество символов для извлечения.
        start_page: Номер страницы с которой начать извлечение (1-indexed).
        end_page: Номер последней страницы для извлечения (1-indexed, None = до конца).

    Returns:
        Текстовое содержимое PDF или None если не удалось извлечь.
    """
    if pymupdf is None:
        print("pymupdf (fitz) not installed. PDF extraction unavailable.")
        return None

    try:
        doc = pymupdf.open(str(file_path))
        total_pages = doc.page_count

        # Определяем диапазон страниц
        if end_page is None or end_page > total_pages:
            end_page = total_pages

        if start_page < 1 or start_page > total_pages:
            print(f"Invalid start_page {start_page}, document has {total_pages} pages")
            return None

        if start_page > end_page:
            print(f"start_page {start_page} > end_page {end_page}")
            return None

        # Извлекаем текст со страниц
        text_parts: List[str] = []
        total_chars = 0

        for page_num in range(start_page - 1, end_page):  # 0-indexed
            page = doc[page_num]
            page_text = page.get_text("text")

            # Очистка текста
            page_text = re.sub(r"\s+", " ", page_text).strip()
            page_text = re.sub(r"\n\s*\n", "\n", page_text)

            if page_text:
                text_parts.append(page_text)
                total_chars += len(page_text)

                if total_chars >= max_chars:
                    # Добавляем many_chars indicator если обрезали
                    remaining = total_chars - max_chars
                    text_parts.append(f"\n\n... [обрезано, осталось {remaining} chars] ...")
                    break

        doc.close()

        result = " ".join(text_parts)
        return result if result else None

    except Exception as e:
        print(f"Error extracting text from PDF {file_path}: {e}")
        return None