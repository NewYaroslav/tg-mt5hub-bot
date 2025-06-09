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
            "balance": balance,
            "broker": broker,
            "profit": profit,
            "trade_allowed": trade_allowed,
            "timestamp_str": timestamp_str
        })

    total_balance += get_total_balance_offset()
    total_profit += get_total_profit_offset()
    total_balance = round(total_balance, 2)
    total_profit = round(total_profit, 2)
    
    message = render_template(
        "all_bot_balances.txt",
        bots=enriched,
        total_balance=total_balance,
        total_profit=total_profit,
        now=now.strftime("%Y.%m.%d %H:%M:%S")
    )

    await update.message.reply_text(message, parse_mode="HTML")
    
@log_async_call
async def handle_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    all_data = list_all_bots()
    bots = []

    for bot_id, entry in all_data.items():
        last_ping = entry.get("last_ping")
        last_ping_str = (
            datetime.fromtimestamp(last_ping).strftime("%Y.%m.%d %H:%M:%S")
            if last_ping else "N/A"
        )

        bots.append({
            "bot_id": bot_id,
            "connected": entry.get("connected", 0),
            "last_ping_str": last_ping_str,
            "login": entry.get("login", "N/A"),
            "broker": entry.get("broker", "N/A"),
            "leverage": entry.get("leverage", "N/A"),
            "max_spread": entry.get("max_spread", "N/A"),
            "trade_allowed": entry.get("trade_allowed", True),
        })

    if not bots:
        message = "ℹ️ <b>No bot data.</b>"
    else:
        message = render_template(
            "all_bot_status.txt",
            bots=bots,
            now=datetime.now().strftime("%Y.%m.%d %H:%M:%S")
        )

    await update.message.reply_text(message, parse_mode="HTML")

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
