# signal_collector.py

import asyncio
import time
from collections import defaultdict
from typing import List, Dict, Callable
from datetime import datetime
from modules.template_engine import render_template
from modules.config import ADMIN_CHAT_ID, FORWARD_CHAT_IDS, get_message_batch_delay_sec, get_total_balance_offset, get_total_profit_offset
from modules.bot_registry import list_all_bots, update_max_spread
from modules.storage import db_add_balance_record
from modules.logging_config import logger

_signal_buffers: Dict[int, List[dict]] = defaultdict(list)
_signal_timers: Dict[int, asyncio.Task] = {}
_balance_report_timer: asyncio.Task = None  # ← fix here

def collect_signal(bot_id: int, login: int, signal: dict, send_func: Callable):
    signal["login"] = login
    _signal_buffers[bot_id].append(signal)

    if bot_id in _signal_timers:
        _signal_timers[bot_id].cancel()

    _signal_timers[bot_id] = asyncio.create_task(_delayed_send_signal(bot_id, send_func))

async def _delayed_send_signal(bot_id: int, send_func: Callable):
    try:
        await asyncio.sleep(get_message_batch_delay_sec())
        signals = _signal_buffers.pop(bot_id, [])
        _signal_timers.pop(bot_id, None)

        if signals:
            for s in signals:
                ts = s.get("timestamp")
                if isinstance(ts, int):
                    s["timestamp_str"] = datetime.fromtimestamp(ts / 1000).strftime("%Y.%m.%d %H:%M:%S")
            
            
            spread_values = [s.get("spread") for s in signals if isinstance(s.get("spread"), (int, float))]
            if spread_values:
                update_max_spread(bot_id, max(spread_values))

            now_str = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            message = render_template("bot_signals.txt", signals=signals, bot_id=bot_id, now=now_str)

            for chat_id in [ADMIN_CHAT_ID] + FORWARD_CHAT_IDS:
                await send_func(chat_id, message)

    except asyncio.CancelledError:
        logger.debug(f"_delayed_send_signal for bot {bot_id} cancelled")
        raise
    except Exception as e:
        logger.exception(f"Error while sending signals for bot {bot_id}")

def collect_all_balances(send_func: Callable):
    global _balance_report_timer
    if _balance_report_timer:
        _balance_report_timer.cancel()
    _balance_report_timer = asyncio.create_task(_delayed_send_balance_summary(send_func))

async def _delayed_send_balance_summary(send_func: Callable):
    global _balance_report_timer
    try:
        await asyncio.sleep(get_message_batch_delay_sec())
        _balance_report_timer = None

        all_data = list_all_bots()
        if not all_data:
            return

        now = datetime.now()
        ts_min = 0
        total_balance = 0.0
        total_profit = 0.0
        enriched = []

        for bot_id, entry in all_data.items():
            login = entry.get("login", "N/A")
            broker = entry.get("broker", "N/A")
            balance = float(entry.get("balance", 0))
            balance = round(balance, 2)
            profit = float(entry.get("profit", 0))
            profit = round(profit, 2)
            trade_allowed = entry.get("trade_allowed", False)

            ts = entry.get("last_balance_time")
            if ts and ts > ts_min:
                ts_min = ts
            timestamp_str = datetime.fromtimestamp(ts).strftime("%Y.%m.%d %H:%M:%S") if ts else "N/A"

            total_balance += balance
            total_profit += profit

            enriched.append({
                "bot_id": bot_id,
                "login": login,
                "broker": broker,
                "balance": balance,
                "profit": profit,
                "trade_allowed": trade_allowed,
                "timestamp_str": timestamp_str
            })
            
        total_balance += get_total_balance_offset()
        total_profit += get_total_profit_offset()
        total_balance = round(total_balance, 2)
        total_profit = round(total_profit, 2)

        if ts_min > 0:
            db_add_balance_record(timestamp=ts_min, balance=total_balance, profit=total_profit)

        message = render_template(
            "all_bot_balances.txt",
            bots=enriched,
            total_balance=total_balance,
            total_profit=total_profit,
            now=now.strftime("%Y.%m.%d %H:%M:%S")
        )

        for chat_id in [ADMIN_CHAT_ID] + FORWARD_CHAT_IDS:
            await send_func(chat_id, message)

    except asyncio.CancelledError:
        logger.debug("_delayed_send_balance_summary cancelled")
        raise
    except Exception as e:
        logger.exception(f"Error while sending signals for bot {bot_id}")