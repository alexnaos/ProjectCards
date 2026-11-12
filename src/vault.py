"""vault.py — обход Obsidian Vault и поиск папок-проектов."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml

from .logger import get_logger
from .cache import load_cache, save_cache, is_unchanged, update_cache

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
    """Подсчитать файлы рекурсивно во всех подпапках проекта.

    Args:
        folder_path: Путь к папке проекта.
        config: Данные конфигурации (используются для card_filename и attachments_dir).

    Returns:
        Количество «данных» файлов в папке и её подпапках.
    """
    card_filename = config.get("card_filename", "{{folder_name}}.md")
    attachments_dir = config.get("attachments_dir", "_attachments")
    card_name = card_filename.replace("{{folder_name}}", folder_path.name)
    exclude_names = {card_name, attachments_dir}

    count = 0
    try:
        for entry in folder_path.rglob("*"):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                continue
            if entry.name in exclude_names:
                continue
            if entry.is_file():
                count += 1
    except Exception:
        pass
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

    Кэширование (roadmap 4a):
    - Если ``cache.enabled = true``, загружает ``.cache.json`` и пропускает
      unchanged проекты (skip_unchanged).
    - Ключ кэша основан на mtime, size и хеше файлов.

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
    
    # Cache setup (roadmap 4a)
    cache_config = config.get("cache", {})
    cache_enabled = cache_config.get("enabled", True)
    skip_unchanged = cache_config.get("skip_unchanged", True)
    cache_file = vault_root / cache_config.get("file", ".cache.json")
    
    cache = {}
    cache_updated = False
    found_projects = []
    if cache_enabled and cache_file.exists():
        try:
            cache = load_cache(vault_root, config)
        except Exception:
            cache = {}
            logger.warning("Could not load cache, recomputing all projects")
    
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
        
        # Check cache for unchanged
        if skip_unchanged and cache_enabled:
            is_cached, cached_data = is_unchanged(entry, cache, config)
            if is_cached and cached_data is not None:
                logger.debug("skip unchanged: %s", entry.name)
                # Восстанавливаем ProjectFolder из кэша (roadmap 4a)
                try:
                    cached_project = ProjectFolder(
                        path=entry,
                        name=entry.name,
                        card_path=entry / "{}.md".format(entry.name),
                        file_count=cached_data.get("file_count", 0),
                    )
                    found_projects.append(cached_project)
                except Exception:
                    pass
                continue
        
        file_count = _count_files(entry, config)
        if file_count < min_files:
            continue

        if ignore_if_only_card and _is_only_card(entry, config, file_count):
            logger.info("skipped (only card): %s", entry.name)
            continue

        project = ProjectFolder(
            path=entry,
            name=entry.name,
            card_path=entry / "{}.md".format(entry.name),
            file_count=file_count,
        )
        found_projects.append(project)

        # Обновляем кэш (roadmap 4a)
        if cache_enabled:
            cache_data = {
                "file_count": file_count,
                "card_path": str(project.card_path),
            }
            cache = update_cache(entry, cache_data, cache, config)
            cache_updated = True

    # Сохраняем кэш после обхода всех проектов (roadmap 4a)
    if cache_enabled and cache_updated:
        try:
            save_cache(cache, vault_root, config)
            logger.debug("Cache saved to %s", cache_file)
        except Exception as e:
            logger.warning("Could not save cache: %s", e)

    for project in found_projects:
        yield project


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
