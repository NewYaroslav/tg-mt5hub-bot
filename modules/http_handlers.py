# http_handlers.py

import io
import time
import csv
import json
from aiohttp import web
from datetime import datetime
from modules.http_auth import verify_signature, generate_signature
from modules.telegram_utils import send_signal_report
from modules.logging_config import logger
from modules.bot_registry import update_heartbeat, is_trading_allowed, update_balance, collect_signal
from modules.config import get_bot_ids, MT5_SECRET_KEY, BALANCE_API_KEY
from modules.storage import db_get_latest_balance_record

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

        update_heartbeat(bot_id, login=login, broker=broker, leverage=leverage)
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
        
        update_balance(bot_id, balance, profit)

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
        
async def handle_last_balance(request: web.Request):
    try:
        key = request.query.get("key")
        if key != BALANCE_API_KEY:
            return web.Response(text="unauthorized", status=403)

        record = db_get_latest_balance_record()
        if not record:
            return web.Response(text="timestamp,profit,balance\n", content_type="text/csv")

        timestamp, profit, balance = record
        dt_str = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "datetime", "profit", "balance"])
        writer.writerow([timestamp, dt_str, profit, balance])

        return web.Response(text=output.getvalue(), content_type="text/csv")
    except Exception as e:
        logger.exception("Error in handle_last_balance")
        return web.Response(text="error", status=500)
