# Project Cards

Инструмент для сканирования Obsidian Vault и создания карточек проектов с метаданными, описанием, обложками и планами.

## Возможности

- 📁 Сканирование папок Obsidian Vault и поиск проектов
- 🃏 Генерация карточек проектов (`.md` с YAML frontmatter)
- 📝 Извлечение описания проекта через суммаризацию (TF-IDF + Counter fallback)
- 📍 Извлечение адреса из текстов документов
- 🖼️ Поиск обложек и планов (PDF → PNG рендеринг)
- 💾 Кэширование для пропуска неизменённых проектов
- ⏰ Планировщик запуска (cron / Task Scheduler)

## Установка

```bash
# Клонировать репозиторий
git clone <repository-url>
cd project-cards

# Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows
# или
source venv/bin/activate  # Linux/macOS

# Установить зависимости
pip install -r requirements.txt

# Скопировать пример конфигурации
cp .env.example .env
# Отредактировать .env с вашими настройками
```

## Настройка

### config.yaml

Основная конфигурация в `config.yaml`:

```yaml
vault_path: "C:/test"              # Путь к Obsidian Vault
card_filename: "{{folder_name}}.md" # Имя файла карточки
attachments_dir: "_attachments"     # Папка для вложений

project_detection:
  min_files: 1                     # Минимум файлов для проекта
  ignore_if_only_card: true        # Пропускать папки с только карточкой

cache:
  enabled: true                    # Включить кэширование
  file: ".cache.json"              # Файл кэша (не в Vault!)
  skip_unchanged: true             # Пропускать неизменённые проекты

llm:
  enabled: false                   # LLM по умолчанию выключен
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o-mini"

images:
  cover_keywords: ["обложка", "facade", "render", "photo"]
  plan_keywords: ["план", "genplan", "фасад", "section"]
  max_plan_images: 6
  pdf_render:
    enabled: true
    dpi: 150
    max_pages_per_file: 3
```

### .env

```bash
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
SERPAPI_KEY=your_key_here
```

## Использование

### Запуск генерации карточек

```bash
python create_cards.py
```

### Планировщик (cron / Task Scheduler)

#### Windows (Task Scheduler)

Создайте задачу в планировщике Windows:
- **Программа:** `python`
- **Аргументы:** `c:\Projects\ProjectCards\create_cards.py`
- **Рабочая папка:** `c:\Projects\ProjectCards`
- **Расписание:** ежедневно или по необходимости

Или используйте `run_scheduled.bat`:

```batch
run_scheduled.bat
```

#### Linux/macOS (cron)

Добавьте в crontab (`crontab -e`):

```bash
# Запуск каждый день в 09:00
0 9 * * * cd /path/to/project-cards && python create_cards.py
```

## Структура карточки проекта

Каждая карточка — это Markdown-файл с YAML frontmatter:

```yaml
---
title: "Название проекта"
source: ""
author: ""
publish: false
created: "2026-11-11"
modified: "2026-11-12"
description: "Краткое описание проекта (2-4 предложения)"
tags:
  - project
address: "Адрес объекта"
rating: null
volume_files: 598
volume_size_mb: 0
cover: "_attachments/Проект/plan_1.png"
schematics:
  - "_attachments/Проект/plan_1.png"
  - "_attachments/Проект/plan_2.png"
---
```

## Дорожная карта

- [x] 4a. Кэширование (`.cache.json`, `skip_unchanged`)
- [x] 4b. PDF plan rendering (PDF → PNG обложки и схемы)
- [x] 4c. README + cron планировщик
- [ ] 4d. Web-интерфейс для просмотра планов
- [ ] LLM-суммаризация (OpenAI API)
- [ ] Тесты (pytest)

## Требования

- Python 3.11+
- pymupdf (fitz) — для чтения PDF
- python-docx — для DOCX
- openpyxl — для XLSX
- python-pptx — для PPTX
- Pillow — для изображений
- pyyaml — для YAML
- python-dotenv — для .env
- tqdm — для прогресс-баров