import os
import sys
from pathlib import Path

PROJECT_CARDS_DIR = Path(r"C:\Projects\ProjectCards")
MYFLASK_DIR = Path(r"C:\Projects\MyFlask")

sys.path.insert(0, str(MYFLASK_DIR))
sys.path.insert(0, str(PROJECT_CARDS_DIR))

from web_app import app as cards_app

# Переключаем директорию для MyFlask
os.chdir(MYFLASK_DIR)

from api.index import app as myflask_app
from waitress import serve
from werkzeug.middleware.dispatcher import DispatcherMiddleware

application = DispatcherMiddleware(myflask_app, {
    '/projects': cards_app
})

if __name__ == '__main__':
    print("Starting combined server on http://0.0.0.0:8080")
    serve(application, host='0.0.0.0', port=8080, threads=4)