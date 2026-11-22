from concurrent.futures import ThreadPoolExecutor
import re
import os
import threading
import time
from pathlib import Path

import yaml
from flask import Flask, abort, render_template_string, request, send_from_directory

app = Flask(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
config = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

# Путь к контенту: значение переменной окружения CARDS_CONTENT_DIR (по умолчанию /data),
# иначе берём vault_path из config.yaml.
VAULT_PATH = Path(
    os.environ.get("CARDS_CONTENT_DIR", "") or config.get("vault_path") or "C:/YandexDisk"
)

# ========================================== list()
# КЭШ СПИСКА ПРОЕКТОВ В ПАМЯТИ (TTL 300 c)
# ========================================== list()
# Сканирование WebDAV (Яндекс.Диск) — дорогая операция с сетевыми задержками,
# поэтому результат держим в памяти и пересобираем не чаще раза в 5 минут.
CACHE_TTL = 3600  # секунд

# Папки с медиа-мусором Яндекс.Диска — при os.walk их можно не обходить вообще.
EXCLUDED_MEDIA_FOLDERS = {
    "Фотокамера",
    "Загрузки",
    "Скриншоты",
    "Социальные сети",
    "Видео",
    "Музыка",
}
# Кэш и примитивы синхронизации.
_cache_cond = threading.Condition()
_cache_projects = []      # готовый список проектов
_cache_mtime = None       # time.monotonic() последней сборки
_scan_in_progress = False # защита от «стаи запросов» на одном и том же сканe


def _scan_projects():
    """Строго 1 уровень в корне + 1 уровень внутри container_folders (без рекурсии)."""
    projects = []
    if not VAULT_PATH.exists():
        return projects

    exclude_paths = set(config.get("exclusions", {}).get("exclude_paths") or [])
    exclude_names = set(config.get("exclusions", {}).get("folder_names") or []) | EXCLUDED_MEDIA_FOLDERS
    containers = set(config.get("project_detection", {}).get("container_folders") or [])

    def _check_folder(item):
        folder_path, rel_path = item
        folder_name = folder_path.name
        card_path = folder_path / f"{folder_name}.md"
        if not card_path.is_file():
            return None
        try:
            content = card_path.read_text(encoding="utf-8")
            fm = extract_fm(content)
        except Exception:
            return None
        publish_val = fm.get("publish", False)
        if str(publish_val).lower() != "true" and publish_val is not True:
            return None
        cover = fm.get("cover", "")
        cover_url = None
        if cover:
            cover_clean = str(cover).replace("![[", "").replace("]]", "").replace("\\", "/")
            cover_url = f"/projects/image/_attachments/{folder_name}/{Path(cover_clean).name}"
        return {
            "folder": folder_name,
            "path": rel_path,
            "title": fm.get("title", folder_name),
            "description": fm.get("description", ""),
            "cover": cover_url,
        }

    targets = list()
    try:
        for entry in os.scandir(VAULT_PATH):
            name = entry.name
            if name.startswith(".") or not entry.is_dir(follow_symlinks=False):
                continue
            if name in exclude_paths or name in exclude_names:
                continue
            if name in containers:
                try:
                    for sub in os.scandir(entry.path):
                        sname = sub.name
                        if sname.startswith(".") or not sub.is_dir(follow_symlinks=False):
                            continue
                        if sname in exclude_names or f"{name}/{sname}" in exclude_paths:
                            continue
                        targets.append((Path(sub.path), f"{name}/{sname}"))
                except OSError:
                    pass
            else:
                targets.append((Path(entry.path), name))
    except OSError:
        pass

    with ThreadPoolExecutor(max_workers=8) as pool:
        for res in pool.map(_check_folder, targets):
            if res:
                projects.append(res)

    projects.sort(key=lambda x: x["path"])
    return projects


def get_projects(force=False):
    """Вернуть кэшированный список проектов (при необходимости пересобрать).

    force=True — принудительно пересобрать (кнопка ?refresh=1).
    При одновременных запросах один поток реально сканирует, остальные ждут.
    """
    global _cache_projects, _cache_mtime, _scan_in_progress
    while True:
        with _cache_cond:
            now = time.monotonic()
            if _cache_mtime is not None and not force and (now - _cache_mtime) < CACHE_TTL:
                return _cache_projects
            if _scan_in_progress:
                # Другой поток уже сканирует — ждём его результат.
                _cache_cond.wait()
                force = False
                continue
            _scan_in_progress = True

        # Тяжёлый сетевой скан выполняем ВНЕ блокировки, чтобы другие потоки
        # не блокировались на время ожидания ответа WebDAV.
        projects = _scan_projects()
        with _cache_cond:
            _cache_projects = projects
            _cache_mtime = time.monotonic()
            _scan_in_progress = False
            _cache_cond.notify_all()
        return projects


def _warmup_cache():
    """Прогрев кэша: заполняет его сразу после старта приложения."""
    start = time.monotonic()
    try:
        get_projects(force=True)
        print(
            f"[web_app] Кэш проектов прогрет: {len(_cache_projects)} карточек "
            f"за {time.monotonic() - start:.1f}s"
        )
    except Exception as e:  # не роняем приложение из-за недоступного WebDAV
        print(f"[web_app] Прогрев кэша не удался: {e}")


def _start_warmup():
    """Запустить фоновый поток прогрева кэша при старте приложения."""
    thread = threading.Thread(target=_warmup_cache, daemon=True, name="cache-warmup")
    thread.start()


# ========================================== list()
# ШАБЛОН СПИСКА ПРОЕКТОВ (ГЛАВНАЯ)
# ========================================== list()
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
        
        <h1 class="mb-4 border-bottom pb-3 d-flex justify-content-between align-items-center">Проекты
            <a href="/projects/?refresh=1" class="btn btn-outline-secondary btn-sm" title="Пересканировать Яндекс.Диск">⟳ Обновить</a>
        </h1>
        
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

# ========================================== list()
# ШАБЛОН ДЕТАЛЬНОЙ СТРАНИЦЫ КАРТОЧКИ
# ========================================== list()
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
    # ?refresh=1 — принудительно пересобрать список (кнопка «Обновить»).
    force = request.args.get("refresh", "") == "1"
    projects = get_projects(force=force)
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

# Запускаем фоновый прогрев кэша при старте приложения (срабатывает и при
# импорте из combined_app.py в контейнере, и при прямом запуске этого файла).
_start_warmup()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

threading.Thread(target=get_projects, daemon=True).start()

