# telegram_utils.py

import logging
from telegram import Bot
from modules.logging_config import logger
from modules.config import ADMIN_CHAT_ID
from modules.template_engine import render_template
from datetime import datetime

_bot_instance: Bot = None  # Инициализируется через init

def init_bot(bot: Bot):
    global _bot_instance
    if _bot_instance is not None:
        logger.warning("Bot instance already initialized — reinitializing")
    _bot_instance = bot

async def send_signal_report(chat_id: int, text: str):
    """
    Sends formatted signal report to the admin chat via Telegram bot.
    """
    if not _bot_instance:
        logger.error("Cannot send signal report — bot instance is not initialized")
        return

    try:
        await _bot_instance.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        logger.info(f"Signal report sent to admin chat {chat_id}")
    except Exception as e:
        logger.exception(f"Failed to send signal report to admin chat {chat_id}: {e}")
        
async def send_bot_connection_report(bots_raw: dict, chat_id: int = ADMIN_CHAT_ID):
    """
    Принимает dict[int, dict] из list_all_bots() и сам обогащает данными.
    """
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
        message = "ℹ️ <b>No bot data.</b>"
    else:
        message = render_template("all_bot_status.txt", bots=bots, now=datetime.now().strftime("%Y.%m.%d %H:%M:%S"))

    try:
        await _bot_instance.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
        logger.info(f"Connection status report sent to chat {chat_id}")
    except Exception as e:
        logger.exception(f"Failed to send connection report: {e}")