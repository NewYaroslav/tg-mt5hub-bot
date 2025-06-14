# bot_registry.py

import time
import asyncio
from typing import Dict, Callable, List
from collections import defaultdict
from datetime import datetime
from modules.config import (
    ADMIN_CHAT_ID,
    FORWARD_CHAT_IDS,
    get_bot_ids,
    get_heartbeat_timeout_sec,
    get_report_delay_sec,
    get_message_batch_delay_sec,
    get_total_balance_offset,
    get_total_profit_offset,
)
from modules.storage import (
    db_get_trading_permission,
    db_set_trading_permission,
    db_add_balance_record,
)
from modules.telegram_utils import (
    send_bot_connection_report,
    send_bot_balance_report,
    send_bot_signal_report_batch,
)
from modules.logging_config import logger

# bot_id → данные
_bot_status: Dict[int, dict] = {}
_bot_heartbeat_fingerprints: Dict[int, str] = {}
_bot_balance_fingerprints: Dict[int, str] = {}

_signal_buffers: Dict[int, List[dict]] = defaultdict(list)
_signal_time: Dict[int, int] = {}

_last_balance_fingerprint: str = ""
_last_heartbeat_fingerprint: str = ""
_last_balance_time: int = 0
_last_heartbeat_time: int = 0

# ---

def initialize_bots():
    for bot_id in get_bot_ids():
        _bot_status.setdefault(bot_id, {
            "connected": 0,
            "login": "N/A",
            "broker": "N/A",
            "leverage": "N/A",
        })
        _bot_status[bot_id]["trade_allowed"] = db_get_trading_permission(bot_id)

# --- heartbeat

def update_heartbeat(bot_id: int, login: int = None, broker: str = None, leverage: int = None):
    global _last_heartbeat_time
    now = int(time.time())
    old_fp = _bot_heartbeat_fingerprints.get(bot_id, "")
    
    entry = _bot_status.setdefault(bot_id, {})
    entry["last_ping"] = now
    entry["login"] = login
    entry["broker"] = broker
    entry["leverage"] = leverage
    entry["connected"] = 1

    new_fp = compute_heartbeat_fingerprint(bot_id)
    _bot_heartbeat_fingerprints[bot_id] = new_fp

    if old_fp != new_fp:
        _last_heartbeat_time = now
        
def is_bot_connected(bot_id: int) -> bool:
    return _bot_status.get(bot_id, {}).get("connected") == 1

def get_all_bot_statuses() -> Dict[int, int]:
    return {bot_id: data.get("connected", 0) for bot_id, data in _bot_status.items()}

def compute_heartbeat_fingerprint(bot_id: int = None) -> str:
    if bot_id is not None:
        entry = _bot_status.get(bot_id, {})
        return f"{bot_id}:{entry.get('connected', 0)}:{entry.get('login')}:{entry.get('broker')}:{entry.get('leverage')}:{entry.get('max_spread')}"
    else:
        parts = []
        for bot_id, entry in sorted(_bot_status.items()):
            parts.append(f"{bot_id}:{entry.get('connected', 0)}:{entry.get('login')}:{entry.get('broker')}:{entry.get('leverage')}:{entry.get('max_spread')}")
        return "|".join(parts)

# --- balance

def update_balance(bot_id: int, balance: float, profit: float):
    global _last_balance_time
    now = int(time.time())
    old_fp = _bot_balance_fingerprints.get(bot_id, "")
    
    entry = _bot_status.setdefault(bot_id, {})
    entry["balance"] = balance
    entry["profit"] = profit
    entry["last_balance_time"] = now
    
    new_fp = compute_balance_fingerprint(bot_id)
    _bot_balance_fingerprints[bot_id] = new_fp

    if old_fp != new_fp:
        _last_balance_time = now

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
    
def compute_balance_fingerprint(bot_id: int = None) -> str:
    if bot_id is not None:
        entry = _bot_status.get(bot_id, {})
        return f"{bot_id}:{entry.get('login')}:{entry.get('broker')}:{entry.get('balance')}:{entry.get('profit')}"
    else:
        parts = []
        for bot_id, entry in sorted(_bot_status.items()):
            parts.append(f"{bot_id}:{entry.get('login')}:{entry.get('broker')}:{entry.get('balance')}:{entry.get('profit')}")
        return "|".join(parts)
    
# ---

def collect_signal(bot_id: int, login: int, signal: dict, send_func: Callable):
    now = int(time.time())
    signal["login"] = login
    _signal_buffers[bot_id].append(signal)
    _signal_time[bot_id] = now
    logger.debug(f"[SIGNAL] Collected signal for bot {bot_id}, login={login}, buffer now has {len(_signal_buffers[bot_id])} signals")

# ---

async def flush_stale_signals_old(now: int):
    for bot_id, last in list(_signal_time.items()):
        try:
            age = now - last
            if age < get_message_batch_delay_sec():
                logger.debug(f"[SIGNAL] Bot {bot_id}: only {age}s passed, skipping.")
                continue

            signals = _signal_buffers.pop(bot_id, [])
            if not signals:
                logger.debug(f"[SIGNAL] Bot {bot_id}: no buffered signals, skipping.")
                continue

            _signal_time.pop(bot_id, None)
            logger.debug(f"[SIGNAL] Bot {bot_id}: flushing {len(signals)} signals.")

            spread_values = [s.get("spread") for s in signals if isinstance(s.get("spread"), (int, float))]
            if spread_values:
                max_spread = max(spread_values)
                update_max_spread(bot_id, max_spread)
                logger.debug(f"[SIGNAL] Bot {bot_id}: max spread = {max_spread}")

            await send_bot_signal_report(bot_id=bot_id, signals=signals)
        except Exception as e:
                logger.exception("[SIGNAL] Exception during balance update")
                
async def flush_stale_signals(now: int):
    batch: Dict[int, List[dict]] = {}
    flushed_bot_ids: List[int] = []

    for bot_id, last in list(_signal_time.items()):
        try:
            age = now - last
            if age < get_message_batch_delay_sec():
                logger.debug(f"[SIGNAL] Bot {bot_id}: only {age}s passed, skipping.")
                continue

            signals = _signal_buffers.pop(bot_id, [])
            if not signals:
                logger.debug(f"[SIGNAL] Bot {bot_id}: no buffered signals, skipping.")
                continue

            _signal_time.pop(bot_id, None)
            logger.debug(f"[SIGNAL] Bot {bot_id}: flushing {len(signals)} signals.")

            spread_values = [s.get("spread") for s in signals if isinstance(s.get("spread"), (int, float))]
            if spread_values:
                max_spread = max(spread_values)
                update_max_spread(bot_id, max_spread)
                logger.debug(f"[SIGNAL] Bot {bot_id}: max spread = {max_spread}")

            batch[bot_id] = signals
            flushed_bot_ids.append(bot_id)

            # Отправляем, если достигли лимита
            if len(batch) >= 10:
                await send_bot_signal_report_batch(batch)
                batch.clear()

        except Exception as e:
            logger.exception(f"[SIGNAL] Exception while processing signals for bot {bot_id}")

    # Отправим остаток
    if batch:
        try:
            await send_bot_signal_report_batch(batch)
        except Exception as e:
            logger.exception("[SIGNAL] Exception while sending final batch")

async def status_change_reporter():
    global _last_balance_fingerprint, _last_heartbeat_fingerprint
    global _last_heartbeat_time, _last_balance_time

    logger.debug("[INIT] status_change_reporter started")
    while True:
        try:
            await asyncio.sleep(get_report_delay_sec())
            now = int(time.time())

            # === BALANCE ===
            try:
                balance_fingerprint = compute_balance_fingerprint()
                change_time = now - _last_balance_time
                if balance_fingerprint != _last_balance_fingerprint and change_time > get_message_batch_delay_sec():
                    _last_balance_fingerprint = balance_fingerprint
                    logger.debug("[BALANCE] Fingerprint changed. Sending balance report...")
                    
                    bots_raw = list_all_bots()

                    # проверим условие all_online
                    all_online = all(entry.get("connected", 0) == 1 for entry in bots_raw.values())

                    # найдём максимальный ts
                    ts_min = max((entry.get("last_balance_time", 0) for entry in bots_raw.values()), default=0)

                    balance = sum(float(b.get("balance", 0)) for b in bots_raw.values()) + get_total_balance_offset()
                    profit  = sum(float(b.get("profit", 0))  for b in bots_raw.values()) + get_total_profit_offset()

                    balance = round(balance, 2)
                    profit = round(profit, 2)

                    if all_online and ts_min > 0:
                        logger.debug(f"[BALANCE] All bots online, saving snapshot at ts={ts_min}, balance={balance}, profit={profit}")
                        db_add_balance_record(timestamp=ts_min,
                                              balance=balance,
                                              profit=profit)

                    await send_bot_balance_report(list_all_bots())
            except Exception as e:
                logger.exception("[BALANCE] Exception during balance update")
     
            # === HEARTBEAT ===
            try:
                heartbeat_fingerprint = compute_heartbeat_fingerprint()
                change_time = now - _last_heartbeat_time    
                if heartbeat_fingerprint != _last_heartbeat_fingerprint and change_time > get_message_batch_delay_sec():
                    _last_heartbeat_fingerprint = heartbeat_fingerprint
                    logger.debug("[HEARTBEAT] Fingerprint changed. Sending heartbeat report...")
                    await send_bot_connection_report(list_all_bots())
            except Exception as e:
                logger.exception("[HEARTBEAT] Exception during heartbeat update")

            # === DISCONNECT CHECK ===
            try:
                changed = False
                for bot_id, data in _bot_status.items():
                    last = data.get("last_ping", 0)
                    if now - last > get_heartbeat_timeout_sec() and data.get("connected") != 0:
                        logger.debug(f"[DISCONNECT] Bot {bot_id} marked as disconnected")
                        data["connected"] = 0
                        changed = True

                if changed:
                    _last_heartbeat_time = int(time.time())
                    _last_heartbeat_fingerprint = compute_heartbeat_fingerprint()
                    logger.debug("[DISCONNECT] Sending updated heartbeat report")
                    await send_bot_connection_report(list_all_bots())
            except Exception as e:
                logger.exception("[DISCONNECT] Exception during disconnect check")
                
            # === SINGAL ===
            try:
                await flush_stale_signals(now)
            except Exception as e:
                logger.exception("[SIGNAL] Exception during signal flush")
        
        except Exception as outer_e:
            logger.exception("[status_change_reporter] Unhandled exception — loop will continue")
