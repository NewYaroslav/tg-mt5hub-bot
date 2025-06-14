# template_engine.py

import logging
from typing import Dict, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from modules.config import get_total_balance_offset, get_total_profit_offset

logger = logging.getLogger("tg_support_bot.template")

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["txt", "html"])
)

def render_template(template_name: str, fallback: str = "⚠ Template error", **kwargs) -> str:
    """
    Renders a template safely.

    @param template_name: Template filename from /templates
    @param fallback: Text to return on error
    @param kwargs: Template context
    @return Rendered string or fallback
    """
    try:
        template = env.get_template(template_name)
        return template.render(**kwargs)
    except TemplateNotFound:
        logger.error(f"Template not found: {template_name}")
        return f"[ERROR] Template '{template_name}' not found"
    except Exception as e:
        logger.error(f"Template rendering failed for {template_name} with context: {kwargs}. Error: {e}")
        return fallback
        
def render_bot_connection_report(bots_raw: dict) -> str:
    bots = []
    for bot_id, entry in bots_raw.items():
        last_ping = entry.get("last_ping")
        last_ping_str = (
            datetime.fromtimestamp(last_ping).strftime("%Y.%m.%d %H:%M:%S")
            if last_ping else "—"
        )
        bots.append({
            "bot_id": bot_id,
            "connected": entry.get("connected", 0),
            "login": entry.get("login", "N/A"),
            "broker": entry.get("broker", "N/A"),
            "leverage": entry.get("leverage", "N/A"),
            "max_spread": entry.get("max_spread", "N/A"),
            "trade_allowed": entry.get("trade_allowed", True),
            "last_ping_str": last_ping_str,
        })

    if not bots:
        return "ℹ️ <b>No bot data.</b>"

    return render_template(
        "all_bot_status.txt",
        bots=bots,
        now=datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    )
    
def render_bot_balance_report(bots_raw: dict) -> str:
    bots = []
    total_balance = 0.0
    total_profit = 0.0
    ts_min = 0

    for bot_id, entry in bots_raw.items():
        login = entry.get("login", "N/A")
        broker = entry.get("broker", "N/A")
        balance = float(entry.get("balance", 0))
        profit = float(entry.get("profit", 0))
        trade_allowed = entry.get("trade_allowed", False)
        ts = entry.get("last_balance_time", 0)

        total_balance += balance
        total_profit += profit

        if ts and ts > ts_min:
            ts_min = ts

        timestamp_str = datetime.fromtimestamp(ts).strftime("%Y.%m.%d %H:%M:%S") if ts else "N/A"

        bots.append({
            "bot_id": bot_id,
            "login": login,
            "broker": broker,
            "balance": round(balance, 2),
            "profit": round(profit, 2),
            "trade_allowed": trade_allowed,
            "timestamp_str": timestamp_str
        })

    total_balance += get_total_balance_offset()
    total_profit += get_total_profit_offset()
    total_balance = round(total_balance, 2)
    total_profit = round(total_profit, 2)

    if not bots:
        return "ℹ️ <b>No bot data.</b>"

    return render_template(
        "all_bot_balances.txt",
        bots=bots,
        total_balance=total_balance,
        total_profit=total_profit,
        now=datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    )
    
def render_bot_signal_report(signals: list[dict], bot_id: int) -> str:
    for s in signals:
        ts = s.get("timestamp")
        if isinstance(ts, int):
            s["timestamp_str"] = datetime.fromtimestamp(ts / 1000).strftime("%Y.%m.%d %H:%M:%S")

    now_str = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    return render_template("bot_signals.txt", signals=signals, bot_id=bot_id, now=now_str)
    
def render_signal_batch_report(batch: Dict[int, List[dict]]) -> str:
    for bot_id, signals in batch.items():
        for s in signals:
            ts = s.get("timestamp")
            if isinstance(ts, int):
                dt = datetime.fromtimestamp(ts / 1000.0)
                ms = int(ts % 1000)
                s["timestamp_str"] = dt.strftime("%Y.%m.%d %H:%M:%S") + f".{ms:03}"

    now_str = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    return render_template("bot_signals_batch.txt", batch=batch, now=now_str)
