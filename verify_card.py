import sys
from pathlib import Path
sys.path.insert(0, '.')
from src.frontmatter import parse_frontmatter

# Check all three cards
card_files = [
    Path('c:/test/Зеленоград/Зеленоград.md'),
    Path('c:/test/Малининская/Малининская.md'),
    Path('c:/test/Нижнелихоборская/Нижнелихоборская.md'),
]

for card_path in card_files:
    print(f"Checking: {card_path.name}")
    if card_path.exists():
        try:
            content = card_path.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(content)
            if fm:
                print("  Frontmatter parsed successfully!")
                print("  Fields:")
                for k, v in fm.items():
                    print(f"    {k}: {v}")
            else:
                print("  No frontmatter parsed")
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print("  File not found")
    print()