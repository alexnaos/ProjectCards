import re
from pathlib import Path

import yaml
from flask import Flask, abort, render_template_string, send_from_directory

app = Flask(__name__)

CONFIG_PATH = Path("config.yaml")
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        VAULT_PATH = Path(config.get("vault_path", r"C:\test"))
else:
    VAULT_PATH = Path(r"C:\test")

BASE_STYLE = """
    <style>
        body { font-family: Arial, sans-serif; background: #f4f5f7; margin: 0; padding: 20px; }
        h1, h2 { color: #333; }
        .btn { display: inline-block; background: #0b57d0; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; font-weight: bold; }
        .btn:hover { background: #0842a0; }
        .btn-back { background: #666; margin-bottom: 20px; }
        .btn-back:hover { background: #444; }
    </style>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><title>Project Cards</title>""" + BASE_STYLE + """
    <style>
        h1 { border-bottom: 2px solid #ccc; padding-bottom: 10px; }
        .grid { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px; }
        .card { background: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); width: 300px; padding: 15px; display: flex; flex-direction: column; }
        .card img { width: 100%; height: 180px; object-fit: cover; border-radius: 4px; margin-bottom: 10px; background: #eee; }
        .card h2 { margin: 0 0 5px 0; font-size: 18px; }
        .path-text { color: #888; font-size: 12px; margin-bottom: 10px; }
        .card p { color: #666; font-size: 14px; flex-grow: 1; }
        .btn { display: block; text-align: center; margin-top: 15px; }
        .no-img { height: 180px; background: #eee; border-radius: 4px; margin-bottom: 10px; display: flex; align-items: center; justify-content: center; color: #aaa; }
    </style>
</head>
<body>
    <h1>Project Cards — Обзор проектов</h1>
    <div class="grid">
        {% for p in projects %}
        <div class="card">
            {% if p.cover %}
                <img src="{{ p.cover }}" alt="Обложка" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                <div class="no-img" style="display:none;">Ошибка загрузки</div>
            {% else %}
                <div class="no-img">Нет обложки</div>
            {% endif %}
            <h2>{{ p.title }}</h2>
            <div class="path-text">Путь: {{ p.path }}</div>
            <p>{{ p.description[:100] if p.description else 'Описание отсутствует' }}...</p>
            <a href="/project/{{ p.path }}" class="btn">Открыть карточку</a>
        </div>
        {% else %}
        <p>Проекты не найдены.</p>
        {% endfor %}
    </div>
</body>
</html>
"""

PROJECT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><title>{{ title }}</title>""" + BASE_STYLE + """
    <style>
        .container { display: flex; gap: 30px; margin-top: 20px; }
        .sidebar { flex: 1; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); height: fit-content; }
        .main-content { flex: 2; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .cover-img { width: 100%; border-radius: 8px; margin-bottom: 20px; }
        .meta-table { width: 100%; border-collapse: collapse; }
        .meta-table td { padding: 8px; border-bottom: 1px solid #eee; }
        .meta-table td:first-child { font-weight: bold; color: #555; width: 40%; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; margin-top: 20px; }
        .gallery img { width: 100%; height: 120px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc; cursor: pointer; transition: transform 0.2s; }
        .gallery img:hover { transform: scale(1.05); }
        .raw-text { background: #f9f9f9; padding: 15px; border-radius: 4px; white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #444; margin-top: 20px; }
    </style>
</head>
<body>
    <a href="/" class="btn btn-back">← Назад к списку</a>
    <div class="container">
        <div class="sidebar">
            {% if cover %}<img src="{{ cover }}" class="cover-img" alt="Обложка">{% endif %}
            <h2>{{ title }}</h2>
            <table class="meta-table">
                <tr><td>Адрес:</td><td>{{ meta.address or 'Не указан' }}</td></tr>
                <tr><td>Файлов:</td><td>{{ meta.volume_files or 0 }}</td></tr>
                <tr><td>Размер:</td><td>{{ meta.volume_size_mb or 0 }} МБ</td></tr>
            </table>
        </div>
        <div class="main-content">
            <h2>Описание</h2>
            <p>{{ meta.description or 'Описание отсутствует' }}</p>
            {% if schematics %}
            <h2>Схемы и планы</h2>
            <div class="gallery">
                {% for img in schematics %}<a href="{{ img }}" target="_blank"><img src="{{ img }}" alt="Схема"></a>{% endfor %}
            </div>
            {% endif %}
            <h2>Исходный текст карточки</h2>
            <div class="raw-text">{{ raw_text }}</div>
        </div>
    </div>
</body>
</html>
"""

def extract_fm(content: str):
    fm = {}
    match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if match:
        try:
            parsed = yaml.safe_load(match.group(1))
            if isinstance(parsed, dict):
                fm = parsed
        except Exception:
            pass
    schematics = []
    for m in re.finditer(r"!\[\[(.*?)\]\]", content):
        schematics.append(m.group(1))
    fm["schematics"] = list(set(schematics))
    return fm

@app.route("/")
def index():
    projects = []
    if VAULT_PATH.exists():
        for card_path in VAULT_PATH.rglob("*.md"):
            if card_path.stem != card_path.parent.name:
                continue
            if any(part.startswith(".") for part in card_path.parts):
                continue
            if "_attachments" in card_path.parts:
                continue

            folder_name = card_path.parent.name
            rel_path = card_path.parent.relative_to(VAULT_PATH).as_posix()
            
            content = card_path.read_text(encoding="utf-8")
            fm = extract_fm(content)
            
            cover = fm.get("cover", "")
            cover_url = None
            if cover:
                cover_clean = str(cover).replace("![[", "").replace("]]", "").replace("\\", "/")
                cover_url = f"/image/_attachments/{folder_name}/{Path(cover_clean).name}"
            
            projects.append({
                "folder": folder_name,
                "path": rel_path,
                "title": fm.get("title", folder_name),
                "description": fm.get("description", ""),
                "cover": cover_url
            })
            
    # Сортируем по пути: сначала корневые папки (Б, В, Г...), потом папки внутри ССК (ССК/1.Небо...)
    projects.sort(key=lambda x: x["path"])
    return render_template_string(INDEX_TEMPLATE, projects=projects)

@app.route("/project/<path:folder_path>")
def project_detail(folder_path):
    folder = VAULT_PATH / folder_path
    folder_name = folder.name
    card = folder / f"{folder_name}.md"
    
    if not card.exists():
        return f"<h1>Карточка не найдена: {folder_path}</h1><a href='/'>Назад</a>", 404
        
    content = card.read_text(encoding="utf-8")
    fm = extract_fm(content)
    
    raw_text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL).strip()
    
    cover_url = None
    if fm.get("cover"):
        cover_clean = str(fm["cover"]).replace("![[", "").replace("]]", "").replace("\\", "/")
        cover_url = f"/image/_attachments/{folder_name}/{Path(cover_clean).name}"
        
    schematics_urls = []
    for img in fm.get("schematics", []):
        img_clean = img.replace("![[", "").replace("]]", "").replace("\\", "/")
        schematics_urls.append(f"/image/_attachments/{folder_name}/{Path(img_clean).name}")

    return render_template_string(
        PROJECT_TEMPLATE, 
        title=fm.get("title", folder_name),
        meta=fm,
        cover=cover_url,
        schematics=schematics_urls,
        raw_text=raw_text
    )

@app.route("/image/<path:relative_path>")
def serve_image(relative_path):
    image_path = VAULT_PATH / relative_path
    if image_path.exists() and image_path.is_file():
        return send_from_directory(str(image_path.parent), image_path.name)
    
    filename = Path(relative_path).name
    for found in VAULT_PATH.rglob(filename):
        if found.is_file():
            return send_from_directory(str(found.parent), found.name)
            
    abort(404)

if __name__ == "__main__":
    app.run(debug=True, port=5000)