import re
import os
from pathlib import Path

import yaml
from flask import Flask, abort, render_template_string, send_from_directory

app = Flask(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
config = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

# Путь к контенту: значение переменной окружения CARDS_CONTENT_DIR (по умолчанию /data),
# иначе берём vault_path из config.yaml.
VAULT_PATH = Path(
    os.environ.get("CARDS_CONTENT_DIR", "") or config.get("vault_path") or "/data"
)

# ==========================================
# ШАБЛОН СПИСКА ПРОЕКТОВ (ГЛАВНАЯ)
# ==========================================
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Проекты</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css">
</head>
<body class="bg-light text-dark">
    <div class="container py-5" style="max-width: 960px;">
        
        <a href="/" class="btn btn-outline-dark mb-4">← На главную</a>
        
        <h1 class="mb-4 border-bottom pb-3">Проекты</h1>
        
        <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
            {% for p in projects %}
            <div class="col">
                <div class="card h-100 shadow-sm border-0">
                    
                    <!-- Контейнер для обложки с защитой от ошибок -->
                    <div class="bg-light d-flex align-items-center justify-content-center" style="height: 180px; position: relative; overflow: hidden; border-top-left-radius: var(--bs-card-inner-border-radius); border-top-right-radius: var(--bs-card-inner-border-radius); border-bottom: 1px solid #eee;">
                        {% if p.cover %}
                            <img src="{{ p.cover }}" alt="Обложка" style="width: 100%; height: 100%; object-fit: cover; position: absolute; top: 0; left: 0; z-index: 1;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div class="text-secondary w-100 text-center" style="display: none; z-index: 0;">Ошибка загрузки</div>
                        {% else %}
                            <div class="text-secondary w-100 text-center">Нет обложки</div>
                        {% endif %}
                    </div>
                    
                    <div class="card-body d-flex flex-column">
                        <h5 class="card-title">{{ p.title }}</h5>
                        <p class="card-text text-muted small mb-3">Путь: {{ p.path }}</p>
                        <p class="card-text flex-grow-1">{{ p.description[:100] if p.description else 'Описание отсутствует' }}...</p>
                        <a href="/projects/project/{{ p.path }}" class="btn btn-primary w-100 mt-auto">Открыть</a>
                    </div>
                </div>
            </div>
            {% else %}
            <div class="col-12">
                <div class="alert alert-secondary" role="alert">Проекты не найдены.</div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ==========================================
# ШАБЛОН ДЕТАЛЬНОЙ СТРАНИЦЫ КАРТОЧКИ
# ==========================================
PROJECT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css">
    <style>
        .lightbox {
            display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%;
            background-color: rgba(0, 0, 0, 0.9); justify-content: center; align-items: center;
        }
        .lightbox img { max-width: 90%; max-height: 90%; object-fit: contain; border-radius: 4px; box-shadow: 0 0 20px rgba(0,0,0,0.5); cursor: default; }
        .lightbox-close { position: absolute; top: 20px; right: 40px; color: white; font-size: 50px; font-weight: bold; cursor: pointer; z-index: 10000; }
        .lightbox-prev, .lightbox-next {
            position: absolute; top: 50%; transform: translateY(-50%); color: white; font-size: 40px; font-weight: bold;
            cursor: pointer; padding: 20px; background-color: rgba(0, 0, 0, 0.5); border-radius: 4px; user-select: none; z-index: 10000;
        }
        .lightbox-prev:hover, .lightbox-next:hover { background-color: rgba(0, 0, 0, 0.8); }
        .lightbox-prev { left: 20px; }
        .lightbox-next { right: 20px; }
        .gallery-img { cursor: pointer; transition: transform 0.2s; object-fit: cover; height: 150px; width: 100%; border-radius: 4px; }
        .gallery-img:hover { transform: scale(1.05); }
        .raw-text { background: #f8f9fa; padding: 15px; border-radius: 4px; white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #212529; border: 1px solid #dee2e6; }
    </style>
</head>
<body class="bg-light text-dark">
    <div class="container py-5" style="max-width: 800px;">
        
        <a href="/projects/" class="btn btn-outline-dark mb-4">← Назад к списку</a>
        
        <div class="row g-4">
            <!-- Сайдбар -->
            <div class="col-md-4">
                <div class="card shadow-sm border-0 h-100">
                    {% if cover %}
                        <div class="bg-light d-flex align-items-center justify-content-center" style="height: 250px; position: relative; overflow: hidden; border-top-left-radius: var(--bs-card-inner-border-radius); border-top-right-radius: var(--bs-card-inner-border-radius); border-bottom: 1px solid #eee;">
                            <img src="{{ cover }}" alt="Обложка" style="width: 100%; height: 100%; object-fit: cover; position: absolute; top: 0; left: 0; z-index: 1;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div class="text-secondary w-100 text-center" style="display: none; z-index: 0;">Ошибка загрузки</div>
                        </div>
                    {% endif %}
                    
                    <div class="card-body">
                        <h4 class="card-title">{{ title }}</h4>
                        <hr>
                        <table class="table table-borderless table-sm mb-0">
                            <tr><td class="text-muted">Адрес:</td><td>{{ meta.address or 'Не указан' }}</td></tr>
                            <tr><td class="text-muted">Файлов:</td><td>{{ meta.volume_files or 0 }}</td></tr>
                            <tr><td class="text-muted">Размер:</td><td>{{ meta.volume_size_mb or 0 }} МБ</td></tr>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- Основной контент -->
            <div class="col-md-8">
                <div class="card shadow-sm border-0 mb-4">
                    <div class="card-body">
                        <h4 class="card-title border-bottom pb-2 mb-3">Описание</h4>
                        <p class="card-text">{{ meta.description or 'Описание отсутствует' }}</p>
                    </div>
                </div>

                {% if schematics %}
                <div class="card shadow-sm border-0 mb-4">
                    <div class="card-body">
                        <h4 class="card-title border-bottom pb-2 mb-3">Схемы и планы</h4>
                        <div class="row g-3">
                            {% for img in schematics %}
                                <div class="col-6 col-md-4">
                                    <a href="javascript:void(0);" onclick="openLightbox({{ loop.index0 }})">
                                        <img src="{{ img }}" class="gallery-img shadow-sm" alt="Схема">
                                    </a>
                                </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                {% endif %}

                <div class="card shadow-sm border-0 mb-4">
                    <div class="card-body">
                        <h4 class="card-title border-bottom pb-2 mb-3">Содержание</h4>
                        <div class="raw-text">{{ raw_text }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Галерея (Lightbox) - оставляем темной, так как это стандарт для просмотра фото -->
    <div id="lightbox" class="lightbox" onclick="closeLightbox()">
        <span class="lightbox-close">&times;</span>
        <span class="lightbox-prev" onclick="prevImage(event)">&#10094;</span>
        <img id="lightbox-img" src="" alt="Просмотр" onclick="event.stopPropagation()">
        <span class="lightbox-next" onclick="nextImage(event)">&#10095;</span>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const images = {{ schematics | tojson }};
        let currentIndex = 0;

        function openLightbox(index) {
            currentIndex = index;
            updateImage();
            document.getElementById('lightbox').style.display = 'flex';
        }

        function closeLightbox() {
            document.getElementById('lightbox').style.display = 'none';
            document.getElementById('lightbox-img').src = '';
        }

        function updateImage() {
            if (images.length > 0) {
                document.getElementById('lightbox-img').src = images[currentIndex];
            }
        }

        function nextImage(event) {
            if (event) event.stopPropagation();
            if (images.length === 0) return;
            currentIndex = (currentIndex + 1) % images.length;
            updateImage();
        }

        function prevImage(event) {
            if (event) event.stopPropagation();
            if (images.length === 0) return;
            currentIndex = (currentIndex - 1 + images.length) % images.length;
            updateImage();
        }

        document.addEventListener('keydown', function(e) {
            const lightbox = document.getElementById('lightbox');
            if (lightbox.style.display === 'flex') {
                if (e.key === 'ArrowRight') nextImage(e);
                else if (e.key === 'ArrowLeft') prevImage(e);
                else if (e.key === 'Escape') closeLightbox();
            }
        });
    </script>
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
            
            publish_val = fm.get("publish", False)
            if str(publish_val).lower() != "true" and publish_val is not True:
                continue
            
            cover = fm.get("cover", "")
            cover_url = None
            if cover:
                cover_clean = str(cover).replace("![[", "").replace("]]", "").replace("\\", "/")
                cover_url = f"/projects/image/_attachments/{folder_name}/{Path(cover_clean).name}"
            
            projects.append({
                "folder": folder_name,
                "path": rel_path,
                "title": fm.get("title", folder_name),
                "description": fm.get("description", ""),
                "cover": cover_url
            })
            
    projects.sort(key=lambda x: x["path"])
    return render_template_string(INDEX_TEMPLATE, projects=projects)

@app.route("/project/<path:folder_path>")
def project_detail(folder_path):
    folder = VAULT_PATH / folder_path
    folder_name = folder.name
    card = folder / f"{folder_name}.md"
    
    if not card.exists():
        return f"<div style='padding:50px; background:#f8f9fa; color:#212529;'><h1>Карточка не найдена: {folder_path}</h1><a href='/projects/' style='color:#0d6efd;'>Назад</a></div>", 404
        
    content = card.read_text(encoding="utf-8")
    fm = extract_fm(content)
    
    raw_text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL).strip()
    
    cover_url = None
    if fm.get("cover"):
        cover_clean = str(fm["cover"]).replace("![[", "").replace("]]", "").replace("\\", "/")
        cover_url = f"/projects/image/_attachments/{folder_name}/{Path(cover_clean).name}"
        
    schematics_urls = []
    for img in fm.get("schematics", []):
        img_clean = img.replace("![[", "").replace("]]", "").replace("\\", "/")
        schematics_urls.append(f"/projects/image/_attachments/{folder_name}/{Path(img_clean).name}")

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
