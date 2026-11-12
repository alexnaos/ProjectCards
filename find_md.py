import glob
import os

# Find all .md files in c:/test
for root, dirs, files in os.walk('c:/test'):
    for f in files:
        if f.endswith('.md'):
            full_path = os.path.join(root, f)
            print(full_path)

# Also check specific folders
for folder in ['Зеленоград', 'Малининская', 'Нижнелихоборская', 'Сокольники']:
    path = os.path.join('c:/test', folder, f'{folder}.md')
    if os.path.exists(path):
        print(f"EXISTS: {path}")
    else:
        print(f"NOT FOUND: {path}")