# config.py

import yaml
import os
from functools import lru_cache
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
ROOT_ADMIN_ID = int(os.getenv("ROOT_ADMIN_ID", 0))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))
FORWARD_CHAT_IDS = [
    int(x.strip()) for x in os.getenv("FORWARD_CHAT_IDS", "").split(",") if x.strip().isdigit()
]
MT5_SECRET_KEY = os.getenv("MT5_SECRET_KEY")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- UI config
with open("config/ui_config.yaml", "r", encoding="utf-8") as f:
    _ui_config = yaml.safe_load(f)

telegram_menu = _ui_config.get("telegram_menu", [])

# --- AUTH config
with open("config/auth.yaml", "r", encoding="utf-8") as f:
    _auth = yaml.safe_load(f)

@lru_cache()
def get_auth_config():
    return _auth.get("auth", {})

def get_login_mismatch_threshold_sec() -> int:
    return get_auth_config().get("login_mismatch_threshold_sec", 10)

def get_max_allowed_delay_sec() -> int:
    return get_auth_config().get("max_allowed_delay_sec", 60)

# --- RUNTIME config
with open("config/runtime.yaml", "r", encoding="utf-8") as f:
    _runtime = yaml.safe_load(f)

@lru_cache()
def get_http_server_config():
    return _runtime.get("http_server", {})

def get_http_server_port() -> int:
    return int(get_http_server_config().get("port", 8080))

@lru_cache()
def get_bot_runtime_config():
    return _runtime.get("bot_runtime", {})

def get_message_batch_delay_sec() -> int:
    return int(get_bot_runtime_config().get("message_batch_delay_sec", 5))

def get_heartbeat_timeout_sec() -> int:
    return int(get_bot_runtime_config().get("heartbeat_timeout_sec", 30))

def get_report_delay_sec() -> int:
    return int(get_bot_runtime_config().get("report_delay_sec", 5))

def get_bot_ids() -> set[int]:
    return set(get_bot_runtime_config().get("bot_ids", []))
    
def get_total_balance_offset() -> float:
    return float(get_bot_runtime_config().get("total_balance_offset", 0.0))

def get_total_profit_offset() -> float:
    return float(get_bot_runtime_config().get("total_profit_offset", 0.0))

# --- GLOBAL reload
def reload_all_configs():
    get_auth_config.cache_clear()
    get_http_server_config.cache_clear()
    get_bot_runtime_config.cache_clear()
