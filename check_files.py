import os

folders = ['Зеленоград', 'Малининская', 'Нижнелихоборская', 'Сокольники']
base = 'c:/test'

for folder in folders:
    path = os.path.join(base, folder)
    if os.path.exists(path):
        print(f"Folder: {folder}")
        for f in sorted(os.listdir(path)):
            full = os.path.join(path, f)
            if os.path.isfile(full):
                size = os.path.getsize(full)
                print(f"  FILE: {f} ({size} bytes)")
            elif os.path.isdir(full):
                print(f"  DIR: {f}")
    else:
        print(f"Folder not found: {folder}")