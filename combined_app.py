import os
import sys
from pathlib import Path

for _k, _v in list(os.environ.items()):
    _lines = [x.strip() for x in _v.splitlines() if x.strip()]
    if len(_lines) > 1:
        os.environ[_k] = _lines.pop(0)
        for _extra in _lines:
            if "=" in _extra:
                _ek, _ev = _extra.split("=", 1)
                os.environ.setdefault(_ek.strip(), _ev.strip())

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Функция для очистки значения переменной окружения от лишних символов
def clean_env_var(value):
    if not value:
        return ""
    
    print(f"Original value: {repr(value)}")
    
    # Убираем символы перевода строки и возврата каретки
    value = value.strip()
    
    # Если значение содержит несколько строк, берем только первую
    if '\n' in value or '\r' in value:
        print("Value contains newlines, splitting...")
        # Разбиваем по любому символу новой строки
        lines = []
        for line in value.replace('\r\n', '\n').split('\n'):
            line = line.strip()
            if line:
                lines.append(line)
        
        print(f"Lines found: {lines}")
        
        if lines:
            # Сначала ищем строку, которая выглядит как путь (не содержит '=')
            for line in lines:
                if '=' not in line:
                    print(f"Selected line (no '='): {line}")
                    return line
            
            # Если все строки содержат '=', ищем строку, которая выглядит как путь
            for line in lines:
                # Ищем что-то вроде "C:\Projects\MyFlask"
                if ':\\' in line or ':/' in line:
                    # Возможно, это строка вида "C:\Projects\MyFlask" перед другими переменными
                    # Разделим по первому '=' если есть
                    if '=' in line:
                        parts = line.split('=', 1)
                        if len(parts) > 1:
                            # Проверяем, является ли первая часть путем
                            if ':\\' in parts[0] or ':/' in parts[0]:
                                print(f"Selected line (looks like path with '='): {parts[0]}")
                                return parts[0]
                    
                    print(f"Selected line (looks like path): {line}")
                    return line
            
            # Если ничего не нашли, возвращаем первую строку
            print(f"Selected first line: {lines[0]}")
            return lines[0]
    
    print(f"Final cleaned value: {value}")
    return value

# Проверяем все переменные окружения для отладки
print("Environment variables:")
for key in ["PROJECT_CARDS_DIR", "MYFLASK_DIR", "MYFLASK_CONTENT_DIR", "CARDS_CONTENT_DIR", "HOST", "PORT"]:
    val = os.environ.get(key)
    print(f"  {key}: {repr(val)}")

PROJECT_CARDS_DIR = Path(clean_env_var(os.environ.get("PROJECT_CARDS_DIR", str(HERE))))
MYFLASK_DIR = Path(clean_env_var(os.environ.get("MYFLASK_DIR", str(HERE.parent / "MyFlask"))))

print(f"PROJECT_CARDS_DIR: {PROJECT_CARDS_DIR}")
print(f"MYFLASK_DIR: {MYFLASK_DIR}")

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

# Создаем обертку для отладки
class DebugMiddleware:
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        # Записываем в файл для гарантии
        with open(str(LOG_DIR / "debug.log"), 'a', encoding='utf-8') as f:
            f.write(f"DebugMiddleware: Request path: {path}\\n")
            if path.startswith('/projects'):
                f.write(f"DebugMiddleware: This should go to cards_app\\n")
        print(f"DebugMiddleware: Request path: {path}")
        if path.startswith('/projects'):
            print(f"DebugMiddleware: This should go to cards_app")
        return self.app(environ, start_response)

# Проверим, что приложения импортированы правильно
print(f"myflask_app type: {type(myflask_app)}")
print(f"cards_app type: {type(cards_app)}")

# Протестируем маршруты
print("Testing myflask_app routes:")
try:
    with myflask_app.test_client() as client:
        response = client.get('/')
        print(f"  GET /: {response.status_code}")
except Exception as e:
    print(f"  Error testing myflask_app: {e}")

print("Skipping cards_app route test")
# Вместо DispatcherMiddleware создадим свое простое приложение
class SimpleDispatcher:
    def __init__(self, main_app, mount_app, mount_point):
        self.main_app = main_app
        self.mount_app = mount_app
        self.mount_point = mount_point
    
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        
        # Записываем в файл для отладки
        with open(str(LOG_DIR / "simple_dispatcher.log"), 'a', encoding='utf-8') as f:
            f.write(f"SimpleDispatcher: path={path}, mount_point={self.mount_point}\\n")
        
        # Если путь начинается с mount_point, передаем запрос mount_app
        if path.startswith(self.mount_point):
            # Удаляем префикс из пути
            new_path = path[len(self.mount_point):]
            if not new_path:
                new_path = '/'
            elif not new_path.startswith('/'):
                new_path = '/' + new_path
            
            environ['PATH_INFO'] = new_path
            environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + self.mount_point
            
            with open(str(LOG_DIR / "simple_dispatcher.log"), 'a', encoding='utf-8') as f:
                f.write(f"SimpleDispatcher: forwarding to mount_app with path={new_path}\\n")
            
            return self.mount_app(environ, start_response)
        
        # Иначе передаем запрос main_app
        with open(str(LOG_DIR / "simple_dispatcher.log"), 'a', encoding='utf-8') as f:
            f.write(f"SimpleDispatcher: forwarding to main_app\\n")
        
        return self.main_app(environ, start_response)

# Используем наш простой диспетчер вместо DispatcherMiddleware
application = SimpleDispatcher(myflask_app, cards_app, '/projects')

if __name__ == '__main__':
    # Адрес прослушивания берём из env HOST (по умолчанию 0.0.0.0 — как в контейнере).
    # Локально (Win-сервис резерва) задаётся HOST=127.0.0.1, чтобы не выставлять в LAN.
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    print(f"Starting combined server on http://{host}:{port}")
    serve(application, host=host, port=port, threads=4)