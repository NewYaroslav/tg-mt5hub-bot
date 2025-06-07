# logging_config.py

import logging
import colorlog
import os
from modules.config import LOG_LEVEL

os.makedirs("logs", exist_ok=True)

# Создаем логгер
logger = logging.getLogger("mt5hub_bot")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Обработчик логов в файл
file_handler = logging.FileHandler("logs/bot.log", encoding="utf-8")
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Обработчик логов в цветную консоль
console_handler = colorlog.StreamHandler()
console_formatter = colorlog.ColoredFormatter(
    "%(log_color)s[%(levelname)s]%(reset)s %(message)s",
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'bold_red',
    }
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)
logger.debug(f"Logging initialized at {LOG_LEVEL} level")