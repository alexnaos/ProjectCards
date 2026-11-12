from pathlib import Path

import docx

# УКАЖИ ЗДЕСЬ ПУТЬ К ПАПКЕ, КОТОРУЮ ХОЧЕШЬ ПРОСКАНИРОВАТЬ
# Например: TARGET_FOLDER = Path(r"C:\test\Сокольники")
TARGET_FOLDER = Path(r"C:\test\Малининская") 

def analyze_docx(file_path):
    print("\n==============================================")
    print(f"АНАЛИЗ ФАЙЛА: {file_path.name}")
    print("==============================================")
    
    try:
        doc = docx.Document(str(file_path))
        
        # --- 1. Читаем МЕТАДАННЫЕ (Свойства документа) ---
        cp = doc.core_properties
        print("--- СВОЙСТВА ФАЙЛА (Метаданные) ---")
        print(f"  Название:   {cp.title}")
        print(f"  Тема:       {cp.subject}")
        print(f"  Автор:      {cp.author}")
        print(f"  Примечания: {cp.comments}")
        print(f"  Категория:  {cp.category}")
        
        # --- 2. Читаем ТЕКСТ (первые 15 непустых строк) ---
        print("\n--- ТЕКСТ (Первые 15 строк) ---")
        count = 0
        for p in doc.paragraphs:
            if p.text.strip():
                print(f"  {p.text.strip()}")
                count += 1
                if count >= 15:
                    break
                    
        # --- 3. Читаем ТАБЛИЦЫ (первые 5 строк из первой таблицы) ---
        if doc.tables:
            print("\n--- ТАБЛИЦА (Первые 5 строк) ---")
            table = doc.tables[0]
            for row in table.rows[:5]:
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    print(f"  {row_text}")
                    
    except Exception as e:
        print(f"ОШИБКА ЧТЕНИЯ: {e}")

def main():
    if not TARGET_FOLDER.exists():
        print(f"Папка {TARGET_FOLDER} не найдена. Проверь путь.")
        return
        
    print(f"Сканирую папку: {TARGET_FOLDER}")
    
    # Ищем все docx файлы, кроме временных (начинающихся с ~$)
    docx_files = [f for f in TARGET_FOLDER.rglob("*.docx") if not f.name.startswith("~$")]
    
    print(f"Найдено Word-документов: {len(docx_files)}")
    
    # Для теста проанализируем первые 10 файлов, чтобы не завалило консоль
    for f in docx_files[:10]:
        analyze_docx(f)

if __name__ == "__main__":
    main()