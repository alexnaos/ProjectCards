import os
import sys
from pathlib import Path

# Каталоги подпроектов: берутся из переменных окружения, по умолчанию — рядом с этим файлом.
# Скрипт лежит в ProjectCards/, а MyFlask/ находится как соседний каталог.
HERE = Path(__file__).resolve().parent

PROJECT_CARDS_DIR = Path(os.environ.get("PROJECT_CARDS_DIR", str(HERE)))
MYFLASK_DIR = Path(os.environ.get("MYFLASK_DIR", str(HERE.parent / "MyFlask")))

sys.path.insert(0, str(MYFLASK_DIR))
sys.path.insert(0, str(PROJECT_CARDS_DIR))

# Опционально загружаем .env (для локальной разработки и удобства на сервере)
try:
    from dotenv import load_dotenv

    load_dotenv(HERE / ".env")
    load_dotenv(HERE.parent / ".env")
except ImportError:
    pass

# ProjectCards: web_app читает config.yaml относительно своего каталога — переходим туда
os.chdir(PROJECT_CARDS_DIR)
from web_app import app as cards_app

# MyFlask: api.index читает конфиг относительно своего файла, но CWD важен для вложений
os.chdir(MYFLASK_DIR)
from api.index import app as myflask_app

from waitress import serve
from werkzeug.middleware.dispatcher import DispatcherMiddleware

application = DispatcherMiddleware(myflask_app, {
    '/projects': cards_app
})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "8080"))
    print(f"Starting combined server on http://0.0.0.0:{port}")
    serve(application, host='0.0.0.0', port=port, threads=4)