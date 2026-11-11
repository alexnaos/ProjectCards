"""images.py — работа с изображениями: поиск обложек и планов, рендер PDF в PNG."""

from __future__ import annotations

import re
def find_images_in_folder(
    folder_path: Path,
    keywords: List[str],
    max_images: int = 10,
    exclude_names: set | None = None,
) -> List[Path]:
    """Найти изображения в папке по ключевым словам.

    Ищет файлы с расширениями .png, .jpg, .jpeg, .gif, .webp в папке (не рекурсивно по умолчанию).

    Args:
        folder_path: Путь к папке проекта.
        keywords: Список ключевых слов для поиска (регистронезависимо).
        max_images: Максимальное количество файлов для возврата.
        exclude_names: Набор имен файлов/папок, которые нужно исключить.

    Returns:
        Список путей к найденным изображениям (отсортированными).
    """
    if exclude_names is None:
        exclude_names = set()

    supported_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    found: List[Path] = []

    # Обходим файлы в папке (1 уровень deep)
    try:
        entries = list(folder_path.iterdir())
    except OSError:
        return found

    # Сначала проверяем файлы текущего уровня
    for entry in entries:
        if not entry.is_file():
            continue
        if entry.name in exclude_names:
            continue
        ext = entry.suffix.lower()
        if ext not in supported_extensions:
            continue

        # Проверяем, содержится ли ключевое слово в имени файла
        name_lower = entry.name.lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in name_lower]

        if matched_keywords:
            found.append(entry)
            if len(found) >= max_images:
                break

    found.sort(key=lambda p: p.name)
    return found[:max_images]
import os
from pathlib import Path
from typing import List, Tuple, Optional

from PIL import Image
import pymupdf  # fitz

from .logger import get_logger

logger = get_logger(__name__)

# Keywords for searching plans/covers (from config.yaml defaults)
PLAN_KEYWORDS = [
    "план", "plan", "генплан", "genplan", "фасад", "facade",
    "разрез", "section", "схема", "scheme"
]

COVER_KEYWORDS = [
    "фасад", "facade", "render", "вид", "photo", "обложка", "general",
    "перспектива", "visual"
]
def render_pdf_pages_to_png(
    pdf_path: Path,
    output_dir: Path,
    plan_keywords: List[str],
    max_pages: int = 3,
    dpi: int = 150,
    exclude_names: set | None = None,
) -> List[Path]:
    """Рендерить страницы PDF в PNG, отбирая те, что содержат план-ключевые слова.

    Страницы рендерятся целиком, но в имен файла включается индекс страницы.
    Фильтрация происходит по совпадению ключевых слов с текстом первой страницы
    или именом файла.

    Args:
        pdf_path: Путь к PDF файлу.
        output_dir: Директория для сохранения PNG файлов.
        plan_keywords: Ключевые слова для фильтрации страниц.
        max_pages: Максимальное количество страниц для рендера.
        dpi: Разрешение рендера (по умолчанию 150).
        exclude_names: Наименования для исключения.

    Returns:
        Список путей к сохраненным PNG файлам.
    """
    if exclude_names is None:
        exclude_names = set()

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception as e:
        logger.warning(f"Cannot open PDF {pdf_path}: {e}")
        return []

    rendered: List[Path] = []
    text_cache: dict[int, str] = {}

    for page_num in range(min(doc.page_count, max_pages)):
        page = doc[page_num]

        # Получаем текст страницы для фильтрации
        page_text = page.get_text("text")
        text_cache[page_num] = page_text

        # Проверяем, совпадает ли текст с план-ключевыми словами
        text_lower = page_text.lower()
        has_keyword = any(kw.lower() in text_lower for kw in plan_keywords)

        if has_keyword:
            # Генерируем PNG
            pix = page.get_pixmap(dpi=dpi)
            png_filename = f"plan_{page_num + 1}.png"
            png_path = output_dir / png_filename

            # Исключаем, если файл с таким именем уже существует
            if str(png_path) in exclude_names:
                continue

            pix.save(str(png_path))
            rendered.append(png_path)

    doc.close()
    return rendered
def find_and_render_plans(
    folder_path: Path,
    config: dict,
    output_subdir: str = "_attachments",
) -> dict:
    """Основная функция: найти планы и обложки в папке проекта.

    Сначала ищет готовые изображения, затем пытается отрендерить PDF-планы.

    Args:
        folder_path: Путь к папке проекта.
        config: Конфигурационные настройки (из config.yaml).
        output_subdir: Имя поддиректории для сохранений (по умолчанию _attachments).

    Returns:
        Словарь с результатами:
        - cover: путь к обложке (или None)
        - schematics: список путей к план-схемам
    """
    attachments_dir = Path(config.get("attachments_dir", output_subdir))
    folder_slug = folder_path.name  # простой slug (можно улучшить translit)
    plan_keywords = config.get("images", {}).get("plan_keywords", PLAN_KEYWORDS)
    cover_keywords = config.get("images", {}).get("cover_keywords", COVER_KEYWORDS)
    max_plan_images = config.get("images", {}).get("max_plan_images", 6)

    # Путь к папке вложений
    attachments_subdir = folder_path.parent / attachments_dir / folder_slug
    attachments_subdir.mkdir(parents=True, exist_ok=True)

    exclude_names = {attachments_dir}  # базовые исключения

    result: dict = {"cover": None, "schematics": []}

    # 1. Ищем готовые изображения в папке проекта
    # Ищем как в самой папке, так и в подпапках
    found_images: List[Path] = []

    # Прямой поиск в папке проекта
    direct_images = find_images_in_folder(
        folder_path, cover_keywords, max_images=max_plan_images, exclude_names=exclude_names
    )
    found_images.extend(direct_images)

    # 2. Ищем PDF файлы и рендерим планы
    pdf_files = list(folder_path.rglob("*.pdf"))

    for pdf_file in pdf_files:
        # Пропускаем PDF в папке _attachments
        if "_attachments" in pdf_file.parts:
            continue

        rendered = render_pdf_pages_to_png(
            pdf_file,
            attachments_subdir,
            plan_keywords=plan_keywords,
            max_pages=max_plan_images,
            exclude_names=exclude_names,
        )
        found_images.extend(rendered)

    # Уникализация и сортировка
    # Убираем дубликаты путей
    unique_images: List[Path] = []
    seen: set = set()
    for img_path in found_images:
        if str(img_path) not in seen:
            seen.add(str(img_path))
            unique_images.append(img_path)

    unique_images.sort(key=lambda p: p.name)

    # Ограничиваем количество планов
    schematics = unique_images[:max_plan_images]

    # Обложка - первое подходящее изображение
    cover = None
    if cover_keywords and schematics:
        cover = schematics[0]
    elif found_images:
        cover = found_images[0]

    result["cover"] = cover
    result["schematics"] = [str(p.relative_to(folder_path.parent)) for p in schematics]

    logger.info(
        "Found %d images in %s: cover=%s, %d schematics",
        len(found_images),
        folder_path.name,
        cover,
        len(schematics),
    )

    return result