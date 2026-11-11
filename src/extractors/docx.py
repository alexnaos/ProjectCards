"""docx.py — извлечение текста из DOCX файлов.

Содержит функцию для извлечения текста из документов Microsoft Word (.docx)
с использованием python-docx.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Union

try:
    from docx import Document
except ImportError:
    Document = None


def extract_text_from_docx(
    file_path: Union[str, Path],
    max_chars: int = 8000,
) -> Optional[str]:
    """Извлечь текст из DOCX файла.

    Args:
        file_path: Путь к DOCX файлу.
        max_chars: Максимальное количество символов для извлечения.

    Returns:
        Текстовое содержимое DOCX файла или None если не удалось извлечь.
    """
    if Document is None:
        print("python-docx not installed. DOCX extraction unavailable.")
        return None

    try:
        doc = Document(str(file_path))

        text_parts: List[str] = []
        total_chars = 0

        # Извлекаем текст из параграфов
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text.strip())
                total_chars += len(paragraph.text)

                if total_chars >= max_chars:
                    remaining = total_chars - max_chars
                    text_parts.append(f"\n\n... [обрезано, осталось {remaining} chars] ...")
                    break

        # Также извлекаем текст из таблиц
        if not total_chars >= max_chars:  # Only if we haven't reached limit yet
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text.strip())
                            total_chars += len(cell.text)

                            if total_chars >= max_chars:
                                remaining = total_chars - max_chars
                                text_parts.append(f"\n\n... [обрезано, осталось {remaining} chars] ...")
                                break

        if not text_parts:
            return None

        result = " ".join(text_parts)
        return result

    except Exception as e:
        print(f"Error extracting text from DOCX {file_path}: {e}")
        return None