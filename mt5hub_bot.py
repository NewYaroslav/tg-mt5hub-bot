# mt5hub_bot.py

import os
import asyncio
import colorlog

from datetime import datetime
from telegram import BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
)
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from modules.template_engine import render_template
from modules.telegram_commands import (
    handle_balances_command,
    handle_status_command,
    handle_allow_trade_command,
    handle_block_trade_command,
    handle_start_command,
    handle_help_command,
    handle_my_id_command,
    handle_clear_db_command,
)
from modules.storage import db_init
from modules.config import TG_BOT_TOKEN, telegram_menu
from modules.log_utils import log_async_call, log_sync_call
from modules.logging_config import logger
from modules.telegram_utils import init_bot, send_admin_message
from modules.http_server import start_http_server
from modules.bot_registry import initialize_bots, periodic_disconnect_check

# Консоль и логгер
console = Console()
background_tasks = []

@log_async_call
async def setup_bot_commands(app: Application):
    try:
        commands = [BotCommand(cmd["command"], cmd["description"]) for cmd in telegram_menu]
        
        for lang in [None, "ru", "en"]:
            await app.bot.delete_my_commands(language_code=lang)
            logger.info(f"Deleted bot commands for language: {lang or 'default'}")
            
        await app.bot.set_my_commands(commands)
        
        logger.info(f"Bot commands set: {[cmd.command for cmd in commands]}")
    except Exception as e:
        logger.exception("Failed to set bot commands")

@log_async_call
async def post_init(app: Application):
    await setup_bot_commands(app)
    
    # Инициализируем бота
    init_bot(app.bot)
    
    initialize_bots()

    # Проверка отключений ботов
    disconnect_task = asyncio.create_task(periodic_disconnect_check())
    background_tasks.append(disconnect_task)
    logger.debug("Background task periodic_disconnect_check started")
    
    # Запускаем HTTP сервер
    try:
        http_runner = await start_http_server()
        background_tasks.append(http_runner)
    except Exception as e:
        logger.exception("Failed to start HTTP server")
        
    try:
        text = render_template("startup_notification.txt", now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        await send_admin_message(text)
    except Exception as e:
        logger.warning(f"Failed to send startup notification: {e}")

# Запуск
@log_sync_call
def run_bot():
    if not TG_BOT_TOKEN:
        logger.critical("TG_BOT_TOKEN not set in .env")
        console.print("[bold red]Error: TG_BOT_TOKEN not set in .env[/bold red]")
        exit(1)

    logger.info("Starting Telegram bot...")
    db_init()

    app = ApplicationBuilder().token(TG_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", handle_start_command))
    app.add_handler(CommandHandler("balances", handle_balances_command))
    app.add_handler(CommandHandler("status", handle_status_command))
    app.add_handler(CommandHandler("allow_trade", handle_allow_trade_command))
    app.add_handler(CommandHandler("block_trade", handle_block_trade_command))
    app.add_handler(CommandHandler("clear_db", handle_clear_db_command))
    app.add_handler(CommandHandler("help", handle_help_command))
    app.add_handler(CommandHandler("myid", handle_my_id_command))

    console.print("[bold green]Telegram bot is running[/bold green]")
    logger.info("Telegram bot is now polling for messages")

    try:
        app.run_polling(close_loop=False)
    finally:
        logger.info("Bot is shutting down, cancelling background tasks...")
        for task in background_tasks:
            if isinstance(task, asyncio.Task):
                if not task.done():
                    task.cancel()
            elif hasattr(task, "cleanup"):  # aiohttp AppRunner
                asyncio.run(task.cleanup())

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        console.print("\n[yellow][!] Stopped by user (Ctrl+C).[/yellow]")
    finally:
        # 
        pass