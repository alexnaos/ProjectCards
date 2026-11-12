"""cache.py — кэширование данных проектов.

Сохраняет и загружает информацию о проектах во ``.cache.json``.
Использует хеш mtime + size + первые N байт для определения изменений.
Поддерживает skip_unchanged для пропуска неmodified проектов.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


def _cache_key(folder_path: Path, config: dict) -> str:
    """Generate a cache key based on folder mtime, size, and file hashes."""
    rel = folder_path.relative_to(config.get("vault_path", "."))
    
    # Basic key from folder mtime and modified time
    try:
        stat = folder_path.stat()
        mtime_size = f"{stat.st_mtime:.6f}_{stat.st_size}"
    except OSError:
        mtime_size = "0_0"
    
    # Hash first few files for more accurate detection
    hash_parts = []
    card_name = f"{folder_path.name}.md"
    attachments_dir = config.get("attachments_dir", "_attachments")
    
    exclude_names = {card_name, attachments_dir}
    
    try:
        files_count = 0
        for entry in sorted(folder_path.iterdir(), key=lambda p: p.name.lower()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                continue
            if entry.name in exclude_names:
                continue
            if not entry.is_file():
                continue
            files_count += 1
            # Hash first 8KB of each file
            try:
                with open(entry, "rb") as f:
                    hash_parts.append(f"{entry.name}:{hashlib.md5(f.read(8192)).hexdigest()[:8]}")
            except:
                hash_parts.append(f"{entry.name}:00000000")
    except:
        pass
    
    key_data = f"{mtime_size}_{files_count}_{'_'.join(hash_parts)}"
    return hashlib.md5(key_data.encode("utf-8")).hexdigest()[:16]


def load_cache(vault_path: Path, config: dict) -> dict:
    """Load cache from .cache.json file.
    
    Returns dict mapping folder names to cache data.
    """
    cache_file = vault_path / config.get("cache", {}).get("file", ".cache.json")
    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_cache(cache: dict, vault_path: Path, config: dict) -> None:
    """Save cache to .cache.json file."""
    cache_file = vault_path / config.get("cache", {}).get("file", ".cache.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.debug("Cache saved to %s", cache_file)
    except IOError as e:
        logger.warning("Could not save cache: %s", e)


def is_unchanged(folder_path: Path, cache: dict, config: dict) -> Tuple[bool, Optional[dict]]:
    """Check if folder contents are unchanged since last cache.
    
    Returns (is_unchanged, cached_data) tuple.
    """
    cache_key = _cache_key(folder_path, config)
    folder_name = folder_path.name
    
    if folder_name in cache:
        cached = cache[folder_name]
        if cached.get("key") == cache_key:
            # Key matches - project unchanged
            return True, cached.get("data")
    
    return False, None


def update_cache(folder_path: Path, data: dict, cache: dict, config: dict) -> dict:
    """Update cache with new project data."""
    folder_name = folder_path.name
    cache_key = _cache_key(folder_path, config)
    
    cache[folder_name] = {
        "key": cache_key,
        "data": data,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    
    return cache