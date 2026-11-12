"""images.py — работа с изображениями: поиск обложек и планов, рендер PDF в PNG."""

from __future__ import annotations

from pathlib import Path

import pymupdf  # fitz

from .logger import get_logger

logger = get_logger(__name__)

PLAN_KEYWORDS = [
    "план", "plan", "генплан", "genplan", "фасад", "facade",
    "разрез", "section", "схема", "scheme"
]

COVER_KEYWORDS = [
    "фасад", "facade", "render", "вид", "photo", "обложка", "general",
    "перспектива", "visual"
]

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

def find_images_in_folder(
    folder_path: Path,
    keywords: list[str],
    max_images: int = 10,
    exclude_names: set | None = None,
    fallback_any: bool = False,
) -> list[Path]:
    if exclude_names is None:
        exclude_names = set()

    found: list[Path] = []
    fallback_found: list[Path] = []

    try:
        entries = list(folder_path.iterdir())
    except OSError:
        return found

    for entry in entries:
        if not entry.is_file():
            continue
        if entry.name in exclude_names:
            continue
        ext = entry.suffix.lower()
        if ext not in SUPPORTED_IMAGE_EXTENSIONS:
            continue

        name_lower = entry.name.lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in name_lower]

        if matched_keywords:
            found.append(entry)
        elif fallback_any:
            fallback_found.append(entry)

        if len(found) >= max_images:
            break

    if not found and fallback_any:
        found = fallback_found

    found.sort(key=lambda p: p.name)
    return found[:max_images]


def _iter_image_files(folder_path: Path, exclude_names: set | None = None) -> list[Path]:
    if exclude_names is None:
        exclude_names = set()

    images: list[Path] = []
    try:
        for entry in folder_path.rglob("*"):
            if not entry.is_file():
                continue
            if entry.name in exclude_names:
                continue
            if entry.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                images.append(entry)
    except OSError:
        pass
    images.sort(key=lambda p: p.name)
    return images


def render_pdf_pages_to_png(
    pdf_path: Path,
    output_dir: Path,
    plan_keywords: list[str],
    max_pages: int = 3,
    dpi: int = 150,
    exclude_names: set | None = None,
    render_first_page: bool = False,
) -> list[Path]:
    if exclude_names is None:
        exclude_names = set()

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception as e:
        logger.warning(f"Cannot open PDF {pdf_path}: {e}")
        return []

    rendered: list[Path] = []
    first_page_rendered = False

    for page_num in range(min(doc.page_count, max_pages)):
        page = doc[page_num]
        page_text = page.get_text("text")
        text_lower = page_text.lower()
        has_keyword = any(kw.lower() in text_lower for kw in plan_keywords)

        should_render = has_keyword or (
            render_first_page and page_num == 0 and not first_page_rendered
        )

        if should_render:
            pix = page.get_pixmap(dpi=dpi)
            png_filename = f"plan_{page_num + 1}.png"
            png_path = output_dir / png_filename

            if str(png_path) in exclude_names:
                continue

            pix.save(str(png_path))
            rendered.append(png_path)

            if page_num == 0:
                first_page_rendered = True

    doc.close()
    return rendered


def find_and_render_plans(
    folder_path: Path,
    config: dict,
    output_subdir: str = "_attachments",
) -> dict:
    attachments_dir = Path(config.get("attachments_dir", output_subdir))
    folder_slug = folder_path.name
    plan_keywords = config.get("images", {}).get("plan_keywords", PLAN_KEYWORDS)
    cover_keywords = config.get("images", {}).get("cover_keywords", COVER_KEYWORDS)
    max_plan_images = config.get("images", {}).get("max_plan_images", 6)

    attachments_subdir = folder_path.parent / attachments_dir / folder_slug
    attachments_subdir.mkdir(parents=True, exist_ok=True)

    exclude_names = {attachments_dir}
    result: dict = {"cover": None, "schematics": []}

    found_images: list[Path] = []
    direct_images = find_images_in_folder(
        folder_path, cover_keywords, max_images=max_plan_images,
        exclude_names=exclude_names, fallback_any=False,
    )
    found_images.extend(direct_images)

    if not found_images:
        all_images = _iter_image_files(folder_path, exclude_names=exclude_names)
        if all_images:
            found_images.extend(all_images[:max_plan_images])

    pdf_files = list(folder_path.rglob("*.pdf"))

    for pdf_file in pdf_files:
        if "_attachments" in pdf_file.parts:
            continue

        rendered = render_pdf_pages_to_png(
            pdf_file, attachments_subdir, plan_keywords=plan_keywords,
            max_pages=max_plan_images, exclude_names=exclude_names,
            render_first_page=True,
        )
        found_images.extend(rendered)

    unique_images: list[Path] = []
    seen: set = set()
    for img_path in found_images:
        if str(img_path) not in seen:
            seen.add(str(img_path))
            unique_images.append(img_path)

    unique_images.sort(key=lambda p: p.name)
    schematics = unique_images[:max_plan_images]

    cover = None
    if schematics:
        cover = schematics[0]
    elif found_images:
        cover = found_images[0]

    result["cover"] = cover
    result["schematics"] = [str(p.relative_to(folder_path.parent)) for p in schematics]

    logger.info(
        "Found %d images in %s: cover=%s, %d schematics",
        len(found_images), folder_path.name, cover, len(schematics),
    )

    return result