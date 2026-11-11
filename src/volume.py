"""volume.py — подсчёт файлов и размера папок-проектов.

Считает количество обычных файлов и общий размер папки,
исключая карточку, папку _attachments и скрытые файлы.
"""

from __future__ import annotations

from pathlib import Path

from typing import Iterator, Dict

from .logger import get_logger

logger = get_logger(__name__)


def _count_files(folder_path: Path, config: dict) -> int:
    """Подсчитать файлы в папке, исключая карточку, _attachments и скрытые файлы.

    Args:
        folder_path: Путь к папке проекта.
        config: Данные конфигурации (используются для card_filename и attachments_dir).

    Returns:
        Количество «данных» файлов в папке.
    """
    card_filename = config.get("card_filename", "{}.md")
    attachments_dir = config.get("attachments_dir", "_attachments")

    # Обработка шаблона card_filename:
    # Config uses Jinja2-style {{ }} syntax, e.g. "{{folder_name}}.md"
    # Python's .format() uses { } syntax. Convert {{ to { and }} to } for compatibility.
    # Also handle the case where the template already uses Python format syntax.
    cf = card_filename
    if "{{" in card_filename:
        # Convert Jinja2 {{ }} to Python { }
        cf = card_filename.replace("{{", "{").replace("}}", "}")
    card_name = cf.format(folder_name=folder_path.name)
    exclude_names = {card_name, attachments_dir}

    count = 0
    for entry in folder_path.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            continue
        if entry.is_file() and entry.name not in exclude_names:
            count += 1
    return count


def _calc_folder_size_mb(folder_path: Path) -> float:
    """Рассчитать общий размер папки в МБ.

    Считает размер всех файлов (не папок) в байтах и переводит в МБ.

    Args:
        folder_path: Путь к папке проекта.

    Returns:
        Общий размер в МБ (с точностью до 1 decimal).
    """
    total_bytes = 0
    try:
        for entry in folder_path.iterdir():
            if entry.is_file():
                total_bytes += entry.stat().st_size
            # Фolders are not counted in size, but their files are
            # We only count direct files, subdirectories handled by iter_projects logic
    except OSError:
        return 0.0
    return round(total_bytes / (1024 * 1024), 1)


def iter_projects_with_volume(vault_path: Path, config: dict) -> Iterator[dict]:
    """Генератор информации о папках-проектах с объемом.

    Yields:
        Словарь с информацией о проекте:
        - path: Path к папке
        - name: имя папки
        - file_count: количество файлов
        - volume_size_mb: общий размер в МБ
    """
    vault_root = vault_path.resolve()

    for entry in sorted(vault_root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue

        # Исключения (переиспользуем логику из vault.py)
        from .vault import (
            _is_excluded_by_path,
            _is_excluded_by_name,
            _is_excluded_by_regex,
            _is_excluded_by_glob,
        )

        if _is_excluded_by_path(entry, vault_root, config):
            logger.debug("excluded by path: %s", entry)
            continue
        if _is_excluded_by_name(entry, config):
            logger.debug("excluded by name: %s", entry)
            continue
        if _is_excluded_by_regex(entry, config):
            logger.debug("excluded by regex: %s", entry)
            continue
        if _is_excluded_by_glob(entry, vault_root, config):
            logger.debug("excluded by glob: %s", entry)
            continue

        file_count = _count_files(entry, config)
        if file_count < 1:  # min_files default
            continue

        volume_size_mb = _calc_folder_size_mb(entry)

        yield {
            "path": entry,
            "name": entry.name,
            "file_count": file_count,
            "volume_size_mb": volume_size_mb,
        }