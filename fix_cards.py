import re
from pathlib import Path

import yaml

VAULT_PATH = Path(r"C:\test")

for folder in VAULT_PATH.iterdir():
    if folder.is_dir() and not folder.name.startswith("_"):
        card = folder / f"{folder.name}.md"
        if card.exists():
            content = card.read_text(encoding="utf-8")
            match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if not match:
                continue
                
            yaml_text = match.group(1)
            fm = {}
            
            # Читаем сырые строки, чтобы вытащить данные
            for line in yaml_text.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    
                    # 1. Лечим адрес (если в него попал volume_files)
                    if key == "address":
                        if "volume_files" in val:
                            val = "" # Сбрасываем мусорный адрес
                    
                    # 2. Лечим описание (если это мусор из кода LISP)
                    if key == "description":
                        if any(bad in val.lower() for bad in ["vlax", "setq", "elist", "obj", "regex"]):
                            val = "Описание не сформировано (найдены только технические файлы)."
                            
                    fm[key] = val
            
            # 3. Пересчитываем размер
            total_size = 0
            file_count = 0
            for f in folder.rglob("*"):
                if f.is_file() and f.name != f"{folder.name}.md" and "_attachments" not in str(f):
                    total_size += f.stat().st_size
                    file_count += 1
                    
            fm["volume_size_mb"] = round(total_size / (1024 * 1024), 1)
            fm["volume_files"] = file_count
            
            # Перезаписываем файл с правильным YAML (yaml.dump сам ставит кавычки где надо)
            clean_yaml = yaml.dump(fm, allow_unicode=True, sort_keys=False)
            body = content.split('---', 2)[-1] if content.count('---') >= 2 else ""
            new_content = f"---\n{clean_yaml}---\n\n{body.strip()}"
            
            card.write_text(new_content, encoding="utf-8")
            print(f"✅ Исправлена карточка: {folder.name}")

print("Готово! Все карточки приведены в порядок.")