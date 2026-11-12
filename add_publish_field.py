import re
from pathlib import Path

import yaml

# Читаем путь из конфига
CONFIG_PATH = Path("config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
    VAULT_PATH = Path(config.get("vault_path", r"C:\test"))

def add_publish_field(card_path: Path):
    content = card_path.read_text(encoding="utf-8")
    
    # Проверяем, есть ли frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False
        
    fm_text = match.group(1)
    
    # Если поле publish уже есть — пропускаем
    if re.search(r"^publish:\s*", fm_text, re.MULTILINE):
        return False
        
    # Добавляем publish: false перед закрывающим ---
    new_content = content.replace(
        f"---\n{match.group(1)}\n---",
        f"---\n{match.group(1)}\npublish: false\n---",
        1
    )
    
    card_path.write_text(new_content, encoding="utf-8")
    return True

def main():
    count = 0
    for card_path in VAULT_PATH.rglob("*.md"):
        if card_path.stem != card_path.parent.name:
            continue
        if any(part.startswith(".") for part in card_path.parts):
            continue
        if "_attachments" in card_path.parts:
            continue
            
        if add_publish_field(card_path):
            print(f"✅ Добавлено publish: {card_path.relative_to(VAULT_PATH)}")
            count += 1

    print(f"\nГотово! Обновлено карточек: {count}")

if __name__ == "__main__":
    main()