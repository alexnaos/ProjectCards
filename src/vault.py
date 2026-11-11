"""vault.py — обход Obsidian Vault и поиск папок-проектов."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProjectFolder:
    """Информация о папке-проекте."""

    path: Path
    name: str
    card_path: Path
    file_count: int = 0


def load_config(config_path: Path) -> dict:
    """Загрузить конфигурацию ``config.yaml``.

    Args:
        config_path: Путь к файлу конфигурации.

    Returns:
        Данные конфигурации в виде словаря.
    """
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _is_excluded_by_path(folder_path: Path, vault_root: Path, config: dict) -> bool:
    """Проверить исключение по exact относительному пути (exclusions.exclude_paths)."""
    rel = folder_path.relative_to(vault_root)
    for p in config.get("exclusions", {}).get("exclude_paths", []):
        if str(rel) == p.rstrip("/") or str(rel) == p.rstrip("/").lstrip("./"):
            return True
    return False


def _is_excluded_by_name(folder_path: Path, config: dict) -> bool:
    """Проверить исключение по имени папки (exclusions.folder_names)."""
    for name in config.get("exclusions", {}).get("folder_names", []):
        if folder_path.name == name:
            return True
    return False


def _is_excluded_by_regex(folder_path: Path, config: dict) -> bool:
    """Проверить исключение по regex (exclusions.folder_regex) — по имени папки."""
    for pattern in config.get("exclusions", {}).get("folder_regex", []):
        if re.match(pattern, folder_path.name):
            return True
    return False


def _is_excluded_by_glob(folder_path: Path, vault_root: Path, config: dict) -> bool:
    """Проверить исключение по glob (exclusions.folder_globs) — по относительному пути."""
    rel = folder_path.relative_to(vault_root)
    for pattern in config.get("exclusions", {}).get("folder_globs", []):
        if fnmatch.fnmatch(str(rel), pattern) or fnmatch.fnmatch(str(rel.parent), pattern):
            return True

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
    exclude_names = {card_filename.format(folder_name=folder_path.name), attachments_dir}

    count = 0
    for entry in folder_path.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            continue
        if entry.is_file() and entry.name not in exclude_names:
            count += 1
    return count


def _is_only_card(folder_path: Path, config: dict, file_count: int) -> bool:
    """Проверить: папка содержит только карточку (и ничего более)."""
    if file_count != 0:
        return False
    card_filename = config.get("card_filename", "{}.md")
    card_file = folder_path / card_filename.format(folder_name=folder_path.name)
    return card_file.exists()


def iter_projects(vault_path: Path, config: dict | None = None) -> Iterator[ProjectFolder]:
    """Найти все папки-проекты в Vault.

    Папка считается проектом, если:
    - это директория, не являющаяся исключённой (config.yaml exclusions);
    - в ней не менее ``project_detection.min_files`` обычных файлов;
    - при ``project_detection.ignore_if_only_card = true`` папка не содержит
      только свой файл карточки.

    Args:
        vault_path: Корень Vault.
        config: Данные конфигурации. Если None — загружается из ``config.yaml``.

    Yields:
        Объекты ``ProjectFolder`` для каждой папки-проекта.
    """
    if config is None:
        config = load_config(vault_path / "config.yaml")

    vault_root = vault_path.resolve()
    project_detection = config.get("project_detection", {})
    min_files = project_detection.get("min_files", 1)
    ignore_if_only_card = project_detection.get("ignore_if_only_card", True)

    for entry in sorted(vault_root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue

        # Исключения
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
        if file_count < min_files:
            continue

        if ignore_if_only_card and _is_only_card(entry, config, file_count):
            logger.info("skipped (only card): %s", entry.name)
            continue

        yield ProjectFolder(
            path=entry,
            name=entry.name,
            card_path=entry / "{}.md".format(entry.name),
            file_count=file_count,
        )


def find_project(vault_path: Path, folder_name: str, config: dict | None = None) -> ProjectFolder | None:
    """Найти проектную папку по имени среди папок-проектов.

    Args:
        vault_path: Корень Vault.
        folder_name: Имя подпапки.
        config: Данные конфигурации.

    Returns:
        ``ProjectFolder`` или None, если не найдено.
    """
    for project in iter_projects(vault_path, config):
        if project.name == folder_name:
            return project
    return None

    return False
