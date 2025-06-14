# telegram_utils.py

import logging
from typing import Dict, List
from telegram import Bot
from datetime import datetime
from modules.logging_config import logger
from modules.config import ADMIN_CHAT_ID, FORWARD_CHAT_IDS
from modules.template_engine import (
    render_template, 
    render_bot_connection_report, 
    render_bot_balance_report, 
    render_bot_signal_report, 
    render_signal_batch_report,
)

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
        
async def send_report_to_chats(text: str, chat_ids: list[int]):
    logger.debug(f"Sending report to {len(chat_ids)} chats.")
    for chat_id in chat_ids:
        try:
            await _bot_instance.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            logger.info(f"Report sent to chat {chat_id}")
        except Exception as e:
            logger.exception(f"Failed to send report to chat {chat_id}: {e}")
            
async def send_bot_connection_report(bots_raw: dict, chat_ids: list[int] = None):
    if chat_ids is None:
        chat_ids = [ADMIN_CHAT_ID] + FORWARD_CHAT_IDS
    text = render_bot_connection_report(bots_raw)
    await send_report_to_chats(text, chat_ids)
    
async def send_bot_balance_report(bots_raw: dict, chat_ids: list[int] = None):
    if chat_ids is None:
        chat_ids = [ADMIN_CHAT_ID] + FORWARD_CHAT_IDS

    text = render_bot_balance_report(bots_raw)
    await send_report_to_chats(text, chat_ids)

async def send_bot_signal_report_batch(batch: Dict[int, List[dict]], chat_ids: list[int] = None):
    if chat_ids is None:
        chat_ids = [ADMIN_CHAT_ID] + FORWARD_CHAT_IDS
    
    text = render_signal_batch_report(batch)
    await send_report_to_chats(text, chat_ids)

async def send_admin_message(text: str, chat_id: int = ADMIN_CHAT_ID):
    """
    Sends a plain message to the admin chat. Used for hub startup, errors, etc.
    """
    if not _bot_instance:
        logger.error("Cannot send admin message — bot instance is not initialized")
        return

    try:
        await _bot_instance.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        logger.info(f"Admin message sent to chat {chat_id}")
    except Exception as e:
        logger.exception(f"Failed to send admin message to chat {chat_id}: {e}")
