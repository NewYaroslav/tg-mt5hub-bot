# telegram_commands.py

import yaml
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from modules.template_engine import render_template
from modules.log_utils import log_async_call
from modules.logging_config import logger
from modules.auth_utils import is_admin, is_root_admin
from modules.bot_registry import list_all_bots, set_trading_allowed, get_all_bot_statuses
from modules.config import get_total_balance_offset, get_total_profit_offset
from modules.storage import db_clear_balance_history, db_remove_trading_permission
from modules.telegram_utils import send_bot_balance_report, send_bot_connection_report

@log_async_call
async def handle_balances_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    all_data = list_all_bots()
    if not all_data:
        await update.message.reply_text("❌ No balance data available.")
        return

    await send_bot_balance_report(all_data, chat_ids=[update.effective_chat.id])
    
@log_async_call
async def handle_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    all_data = list_all_bots()
    if not all_data:
        await update.message.reply_text("ℹ️ <b>No bot data.</b>", parse_mode="HTML")
        return

    await send_bot_connection_report(all_data, chat_ids=[update.effective_chat.id])

@log_async_call
async def handle_allow_trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.first_name or user.username or "user"

    if not is_root_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    bots_data = list_all_bots()
    affected = []

    if context.args:
        try:
            bot_id = int(context.args[0])
            if bot_id not in bots_data:
                await update.message.reply_text(f"❌ Bot ID {bot_id} not found.")
                return

            set_trading_allowed(bot_id, True)
            affected.append({**bots_data[bot_id], "bot_id": bot_id})
        except ValueError:
            await update.message.reply_text("⚠️ Invalid bot ID format. Use: /allow_trade [bot_id]")
            return
    else:
        for bot_id, data in bots_data.items():
            set_trading_allowed(bot_id, True)
            affected.append({**data, "bot_id": bot_id})

    now_str = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    message = render_template("allow_trade_report.txt", bots=affected, now=now_str)
    await update.message.reply_text(message, parse_mode="HTML")
    
@log_async_call
async def handle_block_trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.first_name or user.username or "user"

    if not is_root_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    bots_data = list_all_bots()
    affected = []

    if context.args:
        try:
            bot_id = int(context.args[0])
            if bot_id not in bots_data:
                await update.message.reply_text(f"❌ Bot ID {bot_id} not found.")
                return

            set_trading_allowed(bot_id, False)
            affected.append({**bots_data[bot_id], "bot_id": bot_id})
        except ValueError:
            await update.message.reply_text("⚠️ Invalid bot ID format. Use: /block_trade [bot_id]")
            return
    else:
        for bot_id, data in bots_data.items():
            set_trading_allowed(bot_id, False)
            affected.append({**data, "bot_id": bot_id})

    now_str = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    message = render_template("block_trade_report.txt", bots=affected, now=now_str)
    await update.message.reply_text(message, parse_mode="HTML")

@log_async_call
async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.first_name or user.username or "User"
    
    if not is_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    bots_data = list_all_bots()
    bots = []

    for bot_id, data in sorted(bots_data.items()):
        bots.append({
            "bot_id": bot_id,
            "login": data.get("login", "N/A"),
            "broker": data.get("broker", "N/A"),
            "leverage": data.get("leverage", "N/A"),
        })

    now_str = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    message = render_template("start_description.txt", bots=bots, now=now_str, username=username)
    await update.message.reply_text(message, parse_mode="HTML")
    
@log_async_call
async def handle_clear_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_root_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    args = context.args
    if not args:
        await update.message.reply_text(render_template("clear_db_help.txt"), parse_mode="HTML")
        return

    if "balance" in args:
        db_clear_balance_history()
        await update.message.reply_text("✅ Balance history has been cleared.")

    if "permission" in args:
        bots = list_all_bots()
        for bot_id in bots:
            db_remove_trading_permission(bot_id)
        await update.message.reply_text("✅ All bot trading permissions have been cleared.")

@log_async_call
async def handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text(render_template("not_authorized.txt"))
            return

        text = render_template("help.txt")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML")
    
    except Exception as e:
        logger.exception("Error in handle_help_command")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

@log_async_call
async def handle_my_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    text = render_template(
        "my_id.txt",
        telegram_id=user.id,
        username=user.username or user.first_name or "user",
        chat_id=chat.id
    )

    await update.message.reply_text(text)
