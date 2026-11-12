import sys
from pathlib import Path
import os
sys.path.insert(0, '.')
from src.frontmatter import read_card_file, build_frontmatter, write_card_file, parse_frontmatter, frontmatter_to_yaml

# Rewrite cards with proper fresh frontmatter
print("Rewriting project cards with fresh frontmatter...\n")

# First, get the config
config = {}
try:
    from src.vault import load_config
    config = load_config(Path('c:\\Projects\\ProjectCards\\config.yaml'))
    config['vault_path'] = 'C:/test'
except:
    pass

# Use default config if load fails
if not config.get('vault_path'):
    config['vault_path'] = 'C:/test'

# Process each project folder
folders = ['Зеленоград', 'Малининская', 'Нижнелихоборская']

for folder_name in folders:
    project_path = Path(f'c:/test/{folder_name}')
    card_path = project_path / f'{folder_name}.md'
    
    if not project_path.exists():
        print(f"Folder not found: {folder_name}")
        continue
    
    print(f"Processing: {folder_name}")
    
    # Count files in folder (excluding card and attachments)
    card_filename = config.get("card_filename", "{}.md").format(folder_name=folder_name)
    attachments_dir = config.get("attachments_dir", "_attachments")
    exclude_names = {card_filename, attachments_dir}
    
    file_count = 0
    files_list = []
    for entry in project_path.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            continue
        if entry.name in exclude_names:
            continue
        file_count += 1
        files_list.append(entry.name)
    
    # Build description from file names
    description = "; ".join(files_list[:4]) if files_list else ""
    if len(description) > 300:
        description = description[:300] + "..."
    
    # Create frontmatter
    today = datetime.now().strftime("%Y-%m-%d") if 'datetime' in dir() else "2026-11-12"
    try:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
    except:
        today = "2026-11-12"
    
    created = today
    modified = today
    
    fm = build_frontmatter(
        folder_name=folder_name,
        source="",
        author="",
        publish=False,
        published=None,
        created=created,
        modified=modified,
        description=description,
        tags=["project"],
        address="",
        rating=None,
        volume_files=file_count,
        volume_size_mb=0.0,
        cover="",
        schematics=[],
    )
    
    # Write fresh card (no merging)
    # Read existing content to potentially preserve it, but start fresh
    existing_content = ""
    if card_path.exists():
        try:
            existing_text = card_path.read_text(encoding="utf-8", errors="replace")
            # Check if there's useful content after frontmatter
            if "---\n" in existing_text:
                parts = existing_text.split("---\n", 2)
                if len(parts) > 2:
                    existing_content = parts[2].strip()
        except:
            pass
    
    # Write fresh card with frontmatter and scanned files list
    file_list_text = "\n".join([f"- {f}" for f in files_list]) if files_list else ""
    full_content = fm + "\n\n" + existing_content + "\n\n## Scanned files:\n" + file_list_text if file_list_text else fm
    
    success = write_card_file(card_path, fm, full_content)
    print(f"  Card written: {card_path} (files: {file_count})")
    print()

print("Done rewriting cards.")
frontmatter, content = read_card_file(card_path)

print("=" * 60)
print("CARD: Зеленоград.md")
print("=" * 60)
if frontmatter:
    print("FRONTMATTER:")
    for k, v in frontmatter.items():
        print(f"  {k}: {v}")
else:
    print("No frontmatter found")

print()
print("CONTENT (first 500 chars):")
if content:
    print(content[:500])
else:
    print("No content")

print()
print("=" * 60)
print("CARD: Малининская.md")
print("=" * 60)
card_path2 = Path('c:/test/Малининская/Малининская.md')
frontmatter2, content2 = read_card_file(card_path2)
if frontmatter2:
    print("FRONTMATTER:")
    for k, v in frontmatter2.items():
        print(f"  {k}: {v}")
else:
    print("No frontmatter found")

print()
print("CONTENT (first 500 chars):")
if content2:
    print(content2[:500])
else:
    print("No content")

print()
print("=" * 60)
print("CARD: Нижнелихоборская.md")
print("=" * 60)
card_path3 = Path('c:/test/Нижнелихоборская/Нижнелихоборская.md')
frontmatter3, content3 = read_card_file(card_path3)
if frontmatter3:
    print("FRONTMATTER:")
    for k, v in frontmatter3.items():
        print(f"  {k}: {v}")
else:
    print("No frontmatter found")

print()
print("CONTENT (first 500 chars):")
if content3:
    print(content3[:500])
else:
    print("No content")