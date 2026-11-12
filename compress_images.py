import re
from pathlib import Path

import yaml
from PIL import Image

# Настройки сжатия
MAX_DIMENSION = 1920  # Максимальная ширина или высота (в пикселях)
JPEG_QUALITY = 75     # Качество сжатия (75 - оптимально для веба)

# Читаем путь к Vault
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
    VAULT_PATH = Path(config.get("vault_path", r"C:\test"))

ATTACHMENTS_DIR = VAULT_PATH / "_attachments"

def compress_and_resize(img_path: Path):
    try:
        with Image.open(img_path) as img:
            # Конвертируем в RGB (JPEG не поддерживает прозрачность)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            width, height = img.size
            
            # Вычисляем новые пропорциональные размеры
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                if width > height:
                    new_width = MAX_DIMENSION
                    new_height = int(height * (MAX_DIMENSION / width))
                else:
                    new_height = MAX_DIMENSION
                    new_width = int(width * (MAX_DIMENSION / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Сохраняем как JPG
            new_path = img_path.with_suffix(".jpg")
            img.save(new_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
            
        # Если JPG успешно создан, удаляем старый PNG
        if new_path.exists() and new_path.stat().st_size > 0:
            if img_path.exists():
                img_path.unlink()
            print(f"✅ Сжато: {img_path.name} -> {new_path.name}")
            return True
    except Exception as e:
        print(f"❌ Ошибка с {img_path.name}: {e}")
        return False

def update_markdown_links():
    print("\nОбновляем ссылки в карточках (.md)...")
    count = 0
    for md_path in VAULT_PATH.rglob("*.md"):
        if any(part.startswith(".") for part in md_path.parts): continue
        if "_attachments" in md_path.parts: continue
        
        content = md_path.read_text(encoding="utf-8")
        # Регулярка заменяет ![[*.png]] на ![[*.jpg]]
        new_content = re.sub(r'(!\[\[)(.*?)\.png(\]\])', r'\1\2.jpg\3', content)
        
        if new_content != content:
            md_path.write_text(new_content, encoding="utf-8")
            count += 1

    print(f"✅ Обновлено карточек: {count}")

def main():
    if not ATTACHMENTS_DIR.exists():
        print("Папка _attachments не найдена.")
        return

    png_files = list(ATTACHMENTS_DIR.rglob("*.png"))
    print(f"Найдено PNG-файлов: {len(png_files)}")

    converted = 0
    for png_file in png_files:
        if compress_and_resize(png_file):
            converted += 1

    if converted > 0:
        update_markdown_links()

    print("\nГотово! Размеры картинок уменьшены, вес сжат, ссылки обновлены.")

if __name__ == "__main__":
    main()