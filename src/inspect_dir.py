import fnmatch
import os
import re
from pathlib import Path

import yaml


def is_excluded(rel_path: Path, is_dir: bool, config: dict) -> tuple[bool, str]:
    """Возвращает (True, причина), если путь нужно исключить."""
    exclude = config.get("exclusions", {})
    
    # 1. exclude_paths
    for p in exclude.get("exclude_paths", []):
        if rel_path.as_posix() == p or rel_path.as_posix().startswith(p + "/"):
            return True, f"exclude_paths: {p}"
    
    # 2. folder_names
    if is_dir and rel_path.name in exclude.get("folder_names", []):
        return True, f"folder_names: {rel_path.name}"
    
    # 3. folder_globs
    if is_dir:
        for g in exclude.get("folder_globs", []):
            if fnmatch.fnmatch(rel_path.as_posix(), g):
                return True, f"folder_globs: {g}"
        for r in exclude.get("folder_regex", []):
            if re.search(r, rel_path.as_posix()):
                return True, f"folder_regex: {r}"
    
    # 4. file_globs
    if not is_dir:
        for g in exclude.get("file_globs", []):
            if fnmatch.fnmatch(rel_path.name, g):
                return True, f"file_globs: {g}"
        for r in exclude.get("file_regex", []):
            if re.search(r, rel_path.as_posix()):
                return True, f"file_regex: {r}"
    return False, ""


def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    vault = Path(config.get("vault_path", r"C:\test"))
    report_path = Path("structure_report.txt")
    
    if not vault.exists():
        print(f"❌ Vault не найден: {vault}")
        return

    print(f"Сканирую Vault: {vault}")
    
    excluded_count = 0
    included_count = 0
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("ОТЧЕТ О СТРУКТУРЕ (с учётом исключений)\n")
        f.write(f"Vault: {vault}\n")
        f.write("=" * 70 + "\n\n")
        
        # Обходим только первые 2 уровня, чтобы не углубляться в каждый проект
        for root, dirs, files in os.walk(vault):
            current = Path(root)
            rel = current.relative_to(vault)
            depth = len(rel.parts)
            
            # Проверка на исключение для текущей папки
            if depth > 0:
                excl, reason = is_excluded(rel, is_dir=True, config=config)
                if excl:
                    f.write(f"{'  ' * depth}❌ EXCLUDED: {current.name} ({reason})\n")
                    excluded_count += 1
                    dirs[:] = []  # не идем внутрь
                    continue
            
            # Не заходим глубже 3 уровней (для обзора структуры)
            if depth > 3:
                dirs[:] = []
                continue
            
            # Фильтруем файлы
            pdf_count = 0
            docx_count = 0
            other_count = 0
            total_size = 0
            
            for file in files:
                file_path = current / file
                file_rel = file_path.relative_to(vault)
                
                file_excl, _ = is_excluded(file_rel, is_dir=False, config=config)
                if file_excl:
                    continue
                    
                try:
                    size = file_path.stat().st_size
                    total_size += size
                except OSError:
                    continue
                    
                ext = file_path.suffix.lower()
                if ext == ".pdf": pdf_count += 1
                elif ext in (".docx", ".doc"): docx_count += 1
                elif ext in (".xlsx", ".xls", ".dwg"): other_count += 1
            
            has_files = (pdf_count + docx_count + other_count) > 0
            has_subdirs = len(dirs) > 0
            
            if has_files or has_subdirs or depth == 0:
                indent = "  " * depth
                icon = "📁" if has_subdirs else "📄"
                size_mb = total_size / (1024 * 1024)
                
                f.write(f"{indent}{icon} {current.name}/  [Глубина: {depth}]\n")
                if has_files:
                    f.write(f"{indent}   └─ PDF: {pdf_count}, DOCX: {docx_count}, "
                            f"XLS/DWG: {other_count}, Размер: {size_mb:.1f} MB\n")
                    included_count += 1
                f.write("\n")

    print("\n✅ Готово.")
    print(f"📊 Исключено папок: {excluded_count}")
    print(f"📊 Обработано (осталось): {included_count}")
    print(f"📄 Отчет: {report_path.absolute()}")
    print("\nОткрой structure_report.txt и пришли его содержимое для настройки дальнейших фильтров.")


if __name__ == "__main__":
    main()