# src/exclusions.py
import fnmatch
import re
from pathlib import Path


def is_excluded(rel_path: Path, is_dir: bool, config: dict) -> tuple[bool, str]:
    """Возвращает (True, причина), если путь нужно исключить."""
    exclude = config.get("exclusions", {})
    posix_path = rel_path.as_posix()
    
    # 1. exclude_paths
    for p in exclude.get("exclude_paths", []):
        if posix_path == p or posix_path.startswith(p + "/"):
            return True, f"exclude_paths: {p}"
    
    # 2. folder_names
    if is_dir and rel_path.name in exclude.get("folder_names", []):
        return True, f"folder_names: {rel_path.name}"
    
    # 3. folder_globs
    if is_dir:
        for g in exclude.get("folder_globs", []):
            if fnmatch.fnmatch(posix_path, g):
                return True, f"folder_globs: {g}"
        for r in exclude.get("folder_regex", []):
            if re.search(r, posix_path):
                return True, f"folder_regex: {r}"
    
    # 4. file_globs
    if not is_dir:
        for g in exclude.get("file_globs", []):
            if fnmatch.fnmatch(rel_path.name, g):
                return True, f"file_globs: {g}"
        for r in exclude.get("file_regex", []):
            if re.search(r, posix_path):
                return True, f"file_regex: {r}"
                
    return False, ""