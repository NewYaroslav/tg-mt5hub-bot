# bot_registry.py

import time
import asyncio
from typing import Dict, Callable
from collections import defaultdict
from datetime import datetime
from modules.telegram_utils import send_bot_connection_report
from modules.storage import db_get_trading_permission, db_set_trading_permission
from modules.config import get_bot_ids, get_heartbeat_timeout_sec, get_report_delay_sec, get_total_balance_offset, get_total_profit_offset
from modules.logging_config import logger

# bot_id → данные
_bot_status: Dict[int, dict] = {}
_pending_status_task: asyncio.Task | None = None
_last_report_fingerprint: str = ""
_bot_fingerprints: Dict[int, str] = {}

# --- heartbeat

def initialize_bots():
    for bot_id in get_bot_ids():
        _bot_status.setdefault(bot_id, {
            "connected": 0,
            "login": "N/A",
            "broker": "N/A",
            "leverage": "N/A",
        })
        _bot_status[bot_id]["trade_allowed"] = db_get_trading_permission(bot_id)

async def update_heartbeat(bot_id: int, login: int = None, broker: str = None, leverage: int = None):
    old_fp = _bot_fingerprints.get(bot_id, "")
    
    entry = _bot_status.setdefault(bot_id, {})
    entry["last_ping"] = int(time.time())
    entry["login"] = login
    entry["broker"] = broker
    entry["leverage"] = leverage
    entry["connected"] = 1

    new_fp = compute_bot_fingerprint(bot_id)
    _bot_fingerprints[bot_id] = new_fp

    if old_fp != new_fp:
        await schedule_status_report()
        
def is_bot_connected(bot_id: int) -> bool:
    return _bot_status.get(bot_id, {}).get("connected") == 1

def get_all_bot_statuses() -> Dict[int, int]:
    return {bot_id: data.get("connected", 0) for bot_id, data in _bot_status.items()}

async def schedule_status_report():
    global _pending_status_task
    if _pending_status_task:
        logger.debug("schedule_status_report: task cancel")
        _pending_status_task.cancel()
        try:
            await _pending_status_task
        except asyncio.CancelledError:
            logger.debug("_delayed_send_connection_report: cancelled before execution")

    logger.debug("schedule_status_report: scheduling connection report task")
    _pending_status_task = asyncio.create_task(_delayed_send_connection_report())

def compute_bot_fingerprint(bot_id: int) -> str:
    entry = _bot_status.get(bot_id, {})
    return f"{bot_id}:{entry.get('connected', 0)}:{entry.get('login')}:{entry.get('broker')}:{entry.get('leverage')}:{entry.get('max_spread')}"

def compute_status_fingerprint() -> str:
    parts = []
    for bot_id, entry in sorted(_bot_status.items()):
        parts.append(f"{bot_id}:{entry.get('connected', 0)}:{entry.get('login')}:{entry.get('broker')}:{entry.get('leverage')}:{entry.get('max_spread')}")
    return "|".join(parts)

async def _delayed_send_connection_report():
    global _pending_status_task, _last_report_fingerprint
    try:
        delay = get_report_delay_sec()
        logger.debug(f"_delayed_send_connection_report: sleeping {delay}s")
        await asyncio.sleep(delay)

        fingerprint = compute_status_fingerprint()
        if fingerprint != _last_report_fingerprint:
            logger.debug("Connection report changed. Sending update.")
            await send_bot_connection_report(list_all_bots())
            _last_report_fingerprint = fingerprint
        else:
            logger.debug("Connection report unchanged. Skipping send.")

    except asyncio.CancelledError:
        logger.debug("_delayed_send_connection_report: cancelled before execution")
        raise
    except Exception as e:
        logger.exception(f"_delayed_send_connection_report error: {e}")
    finally:
        _pending_status_task = None

async def periodic_disconnect_check():
    while True:
        await asyncio.sleep(get_report_delay_sec())
        now = int(time.time())
        changed = False

        for bot_id, data in _bot_status.items():
            last = data.get("last_ping", 0)
            if now - last > get_heartbeat_timeout_sec() and data.get("connected") != 0:
                data["connected"] = 0
                changed = True

        if changed:
            await schedule_status_report()

# --- balance

def update_balance(bot_id: int, balance: float, profit: float) -> bool:
    entry = _bot_status.setdefault(bot_id, {})
    prev_balance = entry.get("balance")
    prev_profit = entry.get("profit")

    changed = (prev_balance != balance) or (prev_profit != profit)

    entry = _bot_status.setdefault(bot_id, {})
    entry["balance"] = balance
    entry["profit"] = profit
    entry["last_balance_time"] = int(time.time())
    
    return changed

def get_status(bot_id: int) -> dict:
    return _bot_status.get(bot_id, {})

def set_trading_allowed(bot_id: int, allowed: bool):
    entry = _bot_status.setdefault(bot_id, {})
    current = entry.get("trade_allowed")

    if current != allowed:
        entry["trade_allowed"] = allowed
        db_set_trading_permission(bot_id, allowed)

def is_trading_allowed(bot_id: int) -> bool:
    entry = _bot_status.get(bot_id)
    if entry is None or "trade_allowed" not in entry:
        allowed = db_get_trading_permission(bot_id)
        _bot_status.setdefault(bot_id, {})["trade_allowed"] = allowed
        return allowed

    return entry["trade_allowed"]

def list_all_bots() -> Dict[int, dict]:
    return _bot_status.copy()

def update_max_spread(bot_id: int, spread: float):
    entry = _bot_status.setdefault(bot_id, {})
    entry["max_spread"] = spread