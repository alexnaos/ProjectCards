"""text.py — извлечение текста из простых текстовых файлов.

Содержит функции для чтения текстовых файлов различных кодировок.
"""

from __future__ import annotations

import chardet
from pathlib import Path
from typing import Optional, List, Union


def detect_encoding(file_path: Union[str, Path]) -> str:
    """Автоопределение кодировки файла.

    Args:
        file_path: Путь к файлу.

    Returns:
        Название кодировки.
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result.get("encoding", "utf-8")
        if encoding:
            return encoding
    except Exception:
        pass
    return "utf-8"


def extract_text_from_text(
    file_path: Union[str, Path],
    encoding: Optional[str] = None,
    max_chars: int = 8000,
) -> Optional[str]:
    """Извлечь текст из простого текстового файла.

    Поддерживает автоматическое определение кодировки и кодировки:
    - utf-8
    - windows-1251
    - cp866
    - iso-8859-1

    Args:
        file_path: Путь к текстовому файлу.
        encoding: Явное указание кодировки (None = автоопределение).
        max_chars: Максимальное количество символов для извлечения.

    Returns:
        Текстовое содержимое файла или None если не удалось извлечь.
    """
    # Определяем кодировку
    if encoding is None:
        encoding = detect_encoding(file_path)

    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        # Обрезаем если нужно
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n... [обрезано] ..."

        if not content.strip():
            return None

        return content.strip()

    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        # Попытка с кодировкой windows-1251
        try:
            with open(file_path, "r", encoding="windows-1251", errors="replace") as f:
                content = f.read()
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n... [обрезано] ..."
            return content.strip() if content.strip() else None
        except Exception:
            return None