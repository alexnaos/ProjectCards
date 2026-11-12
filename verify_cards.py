import sys
from pathlib import Path

cards = [
    Path('c:/test/Зеленоград/Зеленоград.md'),
    Path('c:/test/Малининская/Малининская.md'),
    Path('c:/test/Нижнелихоборская/Нижнелихоборская.md'),
    Path('c:/test/Сокольники/Сокольники.md'),
]

for card_path in cards:
    print("=" * 60)
    print(f"CARD: {card_path}")
    print("=" * 60)
    if card_path.exists():
        content = card_path.read_text(encoding="utf-8", errors="replace")
        print(f"File size: {len(content)} chars")
        print(f"First 200 chars repr: {repr(content[:200])}")
        print()
        # Print frontmatter section only (first --- block)
        if content.startswith("---\n"):
            end = content.find("\n---\n", 4)
            if end > 0:
                print("--- FRONTMATTER ---")
                print(content[4:end])
                print("--- END FRONTMATTER ---")
            else:
                print("No closing --- found, first 500 chars:")
                print(content[:500])
        else:
            print("No frontmatter found, first 500 chars:")
            print(content[:500])
    else:
        print("FILE NOT FOUND")
    print()