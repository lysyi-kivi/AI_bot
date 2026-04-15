"""
Модуль настройки логирования для проекта.

Использует logging для структурированного вывода логов.
Поддерживает вывод в консоль и файл.
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO", log_file: str | None = None, format_type: str = "detailed"
) -> logging.Logger:
    """
    Настраивает логирование для всего приложения.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов (None для вывода только в консоль)
        format_type: Тип форматирования ("simple" или "detailed")

    Returns:
        Настроенный logger для корневого модуля
    """
    # Форматы логов
    formats = {
        "simple": "%(levelname)s: %(message)s",
        "detailed": ("%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"),
    }

    log_format = formats.get(format_type, formats["detailed"])

    # Создаем root logger
    root_logger = logging.getLogger("ai_bot")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Очищаем существующие handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # File handler (если указан файл)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Получает logger с указанным именем.

    Args:
        name: Имя logger (обычно __name__ модуля)

    Returns:
        Logger с указанным именем
    """
    return logging.getLogger(f"ai_bot.{name}")
