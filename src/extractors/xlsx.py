"""xlsx.py — извлечение текста из XLSX файлов.

Содержит функцию для извлечения текста из файлов Excel (.xlsx)
с использованием openpyxl.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Union

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None


def extract_text_from_xlsx(
    file_path: Union[str, Path],
    max_chars: int = 8000,
    sheet_names: Optional[List[str]] = None,
) -> Optional[str]:
    """Извлечь текст из XLSX файла.

    Args:
        file_path: Путь к XLSX файлу.
        max_chars: Максимальное количество символов для извлечения.
        sheet_names: Список имен листов для извлечения (None = все листы).

    Returns:
        Текстовое содержимое XLSX файла или None если не удалось извлечь.
    """
    if load_workbook is None:
        print("openpyxl not installed. XLSX extraction unavailable.")
        return None

    try:
        wb = load_workbook(str(file_path), data_only=True)

        # Определяем, какие листы обрабатывать
        sheets_to_process = sheet_names if sheet_names else wb.sheetnames

        text_parts: List[str] = []
        total_chars = 0

        for sheet_name in sheets_to_process:
            if sheet_name not in wb.sheetnames:
                print(f"Sheet '{sheet_name}' not found in workbook")
                continue

            ws = wb[sheet_name]

            # Извлекаем текст из ячеек
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        cell_text = str(cell.value).strip()
                        if cell_text:
                            # Очистка текста от лишних пробелов и переносов
                            cell_text = re.sub(r"\s+", " ", cell_text).strip()
                            text_parts.append(f"[ {sheet_name} ] {cell_text}")
                            total_chars += len(cell.value) if cell.value else 0

                            if total_chars >= max_chars:
                                remaining = total_chars - max_chars
                                text_parts.append(f"\n\n... [обрезано, осталось {remaining} chars] ...")
                                wb.close()
                                return " ".join(text_parts)

        wb.close()

        if not text_parts:
            return None

        result = " \n ".join(text_parts)
        return result

    except Exception as e:
        print(f"Error extracting text from XLSX {file_path}: {e}")
        return None