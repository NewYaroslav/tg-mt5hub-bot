# http_handlers.py

import time
import json
from aiohttp import web
from dotenv import load_dotenv
from modules.http_auth import verify_signature, generate_signature
from modules.telegram_utils import send_signal_report
from modules.logging_config import logger
from modules.bot_registry import update_heartbeat, is_trading_allowed, update_balance
from modules.config import get_bot_ids, MT5_SECRET_KEY
from modules.signal_collector import collect_all_balances, collect_signal

async def handle_bot_heartbeat(request: web.Request):
    try:
        bot_id = int(request.headers.get("x-bot-id"))
        login = int(request.headers.get("x-mt5-login"))
        timestamp = int(request.headers.get("x-mt5-time"))
        signature = request.headers.get("x-mt5-signature")
        body = await request.text()

        # Проверка HMAC
        if not verify_signature(MT5_SECRET_KEY, bot_id, login, timestamp, body, signature):
            return web.json_response({"ok": False, "error": "bad signature"}, status=403)
            
        data = json.loads(body)
        broker = data.get("broker")
        leverage = data.get("leverage")

        await update_heartbeat(bot_id, login=login, broker=broker, leverage=leverage)
        allowed = is_trading_allowed(bot_id)
        logger.debug(f"Ping received from bot {bot_id}, allowed={allowed}")
        signature = generate_signature(MT5_SECRET_KEY, bot_id, login, int(time.time()), body="")
        return web.json_response({"ok": True, "allowed": allowed, "signature": signature})

    except Exception as e:
        logger.exception(f"Heartbeat error: {str(e)}")
        return web.json_response({"ok": False, "error": str(e)}, status=400)

async def handle_balance_report(request: web.Request):
    try:
        bot_id = int(request.headers.get("x-bot-id"))
        login = int(request.headers.get("x-mt5-login"))
        timestamp = int(request.headers.get("x-mt5-time"))
        signature = request.headers.get("x-mt5-signature")
        body = await request.text()
        
        # Проверка HMAC
        if not verify_signature(MT5_SECRET_KEY, bot_id, login, timestamp, body, signature):
            return web.json_response({"ok": False, "error": "bad signature"}, status=403)

        data = json.loads(body)
        balance = float(data.get("balance", 0))
        profit = float(data.get("profit", 0))
        
        changed = update_balance(bot_id, balance, profit)

        if changed:
            collect_all_balances(send_signal_report)
            logger.debug(f"Bot {bot_id} updated balance: {balance}, profit: {profit}")
        else:
            logger.debug(f"Bot {bot_id} balance unchanged")

        signature = generate_signature(MT5_SECRET_KEY, bot_id, login, int(time.time()), body="")
        return web.json_response({"ok": True, "signature": signature})

    except Exception as e:
        logger.exception("Balance report error")
        return web.json_response({"ok": False, "error": str(e)}, status=400)

async def handle_bot_signal(request):
    try:
        bot_id = int(request.headers.get("x-bot-id"))
        login = int(request.headers.get("x-mt5-login"))
        timestamp = int(request.headers.get("x-mt5-time"))
        signature = request.headers.get("x-mt5-signature")
        body = await request.text()

        # Проверка HMAC
        if not verify_signature(MT5_SECRET_KEY, bot_id, login, timestamp, body, signature):
            return web.json_response({"ok": False, "error": "bad signature"}, status=403)

        data = json.loads(body)
        if not isinstance(data, list):
            logger.error(f"Bot signal error: expected list of signals")
            return web.json_response({"ok": False, "error": "expected list of signals"}, status=400)

        for signal in data:
            collect_signal(bot_id, login, signal, send_signal_report)

        signature = generate_signature(MT5_SECRET_KEY, bot_id, login, int(time.time()), body="")
        return web.json_response({"ok": True, "signature": signature})

    except Exception as e:
        logger.exception(f"Bot signal error: {str(e)}")
        return web.json_response({"ok": False, "error": str(e)}, status=400)
