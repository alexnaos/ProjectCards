"""Логирование для project-cards.

Настраивает логгер с консольным выводом и опционально в файл.
Поддерживает уровни логгирования: DEBUG, INFO, WARNING, ERROR.
"""

import logging
import sys
from pathlib import Path

__all__ = ["get_logger", "setup_logger"]


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Path | None = None,
    format_str: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
) -> logging.Logger:
    """Создать и настроить logger.

    Args:
        name: Имя логгера.
        level: Уровень логгирования.
        log_file: Путь к файлу логов. Если None — пишет только в консоль.
        format_str: Формат сообщений.

    Returns:
        Настроенный логгер.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Сброс старых обработчиков, чтобы не дублировать логи при переиспользовании
    logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format_str))
    logger.addHandler(console_handler)

    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str, level: int = logging.INFO, log_file: Path | None = None) -> logging.Logger:
    """Псевдоним ``setup_logger``. Возвращает уже настроенный логгер.

    Args:
        name: Имя логгера.
        level: Уровень логгирования.
        log_file: Путь к файлу логов.

    Returns:
        Настроенный логгер.
    """
    return setup_logger(name, level=level, log_file=log_file)
