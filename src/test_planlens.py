
from planlens.document import open_document

# Укажите путь к любому вашему PDF для теста
pdf_path = r"C:\test\Госп3\РД\002. 63-0622-ОК-1Н-СГП1\63-0622-ОК-1Н-СГП1 изм1.pdf"  # <-- ЗАМЕНИТЕ НА РЕАЛЬНЫЙ ПУТЬ

print(f"Анализ файла: {pdf_path}")
with open_document(pdf_path) as doc:
    for row in doc.page_map():
        # row.kind покажет тип страницы: 'text page', 'drawing sheet', 'form', 'figure', 'scan'
        print(f"Страница {row.page}: Тип = {row.kind}, Заголовок = {row.heading}")