"""frontmatter.py — reading/merging/writing YAML frontmatter for project cards.

Supports:
- Reading existing frontmatter from .md files
- Merging (merge) with preservation of custom fields not in the spec
- Writing new frontmatter with fixed field order
- Automatic title renaming when folder name changes
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

CARD_FIELDS = [
    "title",
    "source",
    "author",
    "publish",
    "published",
    "created",
    "modified",
    "description",
    "tags",
    "address",
    "rating",
    "volume_files",
    "volume_size_mb",
    "cover",
    "schematics",
]


def parse_frontmatter(md_content: str) -> dict | None:
    """Extract YAML frontmatter from .md file content.

    Args:
        md_content: Full content of .md file.

    Returns:
        Dictionary with frontmatter data or None if frontmatter absent.
    """
    match = re.match(r"^---\n(.*?)\n---", md_content, re.DOTALL)
    if not match:
        return None
    yaml_str = match.group(1)
    try:
        data = yaml.safe_load(yaml_str)
        return data if data else {}
    except yaml.YAMLError:
        return None


def build_frontmatter(
    folder_name: str,
    source: str = "",
    author: str = "",
    publish: bool = False,
    published: str | None = None,
    created: str | None = None,
    modified: str | None = None,
    description: str = "",
    tags: list | None = None,
    address: str = "",
    rating: float | None = None,
    volume_files: int = 0,
    volume_size_mb: float = 0.0,
    cover: str = "",
    schematics: list | None = None,
) -> str:
    """Form frontmatter string with fixed field order.

    Args:
        folder_name: Folder name (set as title).
        source: Source project.
        author: Author.
        publish: Whether published.
        published: Publication date (ISO).
        created: Creation date (ISO - card file ctime).
        modified: Modification date (ISO - now).
        description: Description (2-4 sentences).
        tags: Project tags.
        address: Address.
        rating: Rating.
        volume_files: Number of files.
        volume_size_mb: Total size in MB.
        cover: Cover path.
        schematics: List of schematics/images.

    Returns:
        YAML frontmatter string.
    """
    data: dict = {
        "title": folder_name,
        "source": source,
        "author": author,
        "publish": publish,
        "published": published,
        "created": created,
        "modified": modified,
        "description": description,
        "tags": tags if tags is not None else [],
        "address": address,
        "rating": rating,
        "volume_files": volume_files,
        "volume_size_mb": volume_size_mb,
        "cover": cover,
        "schematics": schematics if schematics is not None else [],
    }

    lines = ["---"]
    for key in CARD_FIELDS:
        if key in data:
            value = data[key]
            if isinstance(value, bool):
                lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, float):
                if value == int(value):
                    lines.append(f"{key}: {int(value)}")
                else:
                    lines.append(f"{key}: {value}")
            elif isinstance(value, list):
                if value:
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - {item}")
            elif value is not None:
                lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def merge_frontmatter(
    existing: dict | None,
    overwrite: dict | None = None,
    *,
    folder_name: str | None = None,
) -> dict:
    """Merge existing frontmatter with new data.

    Merge rules:
    - All fields from ``overwrite`` overwrite existing ones.
    - Fields not in ``overwrite`` are preserved from ``existing``.
    - If ``folder_name`` is specified, ``title`` is always updated.
    - Custom fields (not in CARD_FIELDS) are preserved automatically.

    Args:
        existing: Existing frontmatter dict or None.
        overwrite: Data to overwrite.
        folder_name: New folder name (will update title).

    Returns:
        Merged frontmatter dict.
    """
    result: dict = {}

    # First copy existing fields (except title, which we replace separately)
    if existing:
        for key, value in existing.items():
            if key != "title" or folder_name is not None:
                result[key] = value

    # Apply overwrite
    if overwrite:
        result.update(overwrite)

    # Always update title if folder_name specified
    if folder_name is not None:
        result["title"] = folder_name

def frontmatter_to_yaml(frontmatter: dict) -> str:
    """Convert frontmatter dict to YAML string.

    Args:
        frontmatter: Dictionary with frontmatter data.

    Returns:
        YAML string.
    """
    # Remove None values
    cleaned = {k: v for k, v in frontmatter.items() if v is not None}
    return yaml.dump(cleaned, default_flow_style=False, allow_unicode=True).strip()


def read_card_file(card_path: Path) -> tuple:
    """Read card and extract frontmatter and content.

    Args:
        card_path: Path to .md card file.

    Returns:
        Tuple (frontmatter_dict, content_without_frontmatter) or (None, None),
        if file doesn't exist or doesn't contain frontmatter.
    """
    if not card_path.exists():
        return None, None

    try:
        content = card_path.read_text(encoding="utf-8")
    except Exception:
        return None, None

    fm = parse_frontmatter(content)
    if fm is None:
        return None, None

    # Remove frontmatter from content
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if match:
        rest = content[match.end() :]
    else:
        rest = content

    return fm, rest


def write_card_file(
    card_path: Path,
    frontmatter_yaml: str,
    content: str = "",
    force: bool = False,
) -> bool:
    """Write card with frontmatter.

    Args:
        card_path: Path to .md card file.
        frontmatter_yaml: YAML frontmatter string (without ``---`` delimiters).
        content: Content after frontmatter (optional).
        force: If True - overwrite even if file exists and is empty.

    Returns:
        True if file was written.
    """
    card_path.parent.mkdir(parents=True, exist_ok=True)

    # Add frontmatter delimiters
    fm_with_delims = f"---\n{frontmatter_yaml}\n---"

    existing_frontmatter, existing_content = read_card_file(card_path)

    if existing_frontmatter is not None and not force:
        # Merge: keep old data, update with what was provided
        merged = merge_frontmatter(existing_frontmatter, {}, folder_name="")
        final_content = fm_with_delims
        if existing_content and existing_content.strip():
            final_content += "\n" + existing_content.strip()
        else:
            final_content += "\n"
    else:
        final_content = fm_with_delims
        if content:
            final_content += "\n" + content.strip()

    card_path.write_text(final_content, encoding="utf-8")
    return True


def rename_card_title(card_path: Path, new_title: str) -> bool:
    """Rename title in card frontmatter.

    Args:
        card_path: Path to .md card file.
        new_title: New title.

    Returns:
        True if title was updated.
    """
    frontmatter, content = read_card_file(card_path)
    if frontmatter is None:
        return False

    frontmatter["title"] = new_title
    yaml_str = frontmatter_to_yaml(frontmatter)

    # Add frontmatter delimiters
    fm_with_delims = f"---\n{yaml_str}\n---"

    if content and content.strip():
        final_content = fm_with_delims + "\n" + content.strip() + "\n"
    else:
        final_content = fm_with_delims

    card_path.write_text(final_content, encoding="utf-8")
    return True
    return result