# auth_utils.py

import os
from dotenv import load_dotenv
from modules.config import FORWARD_CHAT_IDS

load_dotenv()
ROOT_ADMIN_ID = int(os.getenv("ROOT_ADMIN_ID", 0))

def is_admin(telegram_id: int) -> bool:
    try:
        telegram_id = int(telegram_id)
    except (ValueError, TypeError):
        return False
    return telegram_id == ROOT_ADMIN_ID or telegram_id in FORWARD_CHAT_IDS

def is_root_admin(telegram_id: int) -> bool:
    try:
        return int(telegram_id) == ROOT_ADMIN_ID
    except (ValueError, TypeError):
        return False