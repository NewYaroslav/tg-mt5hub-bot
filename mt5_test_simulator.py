import asyncio
import json
import aiohttp
import os
import time
from dotenv import load_dotenv
from random import uniform, randint
from datetime import datetime
from rich.console import Console

from modules.config import (
    get_bot_ids,
    get_heartbeat_timeout_sec,
    get_message_batch_delay_sec,
    get_http_server_port,
    MT5_SECRET_KEY
)
from modules.http_auth import generate_signature, verify_signature as verify_response_signature

console = Console()

# --- Конфигурация
port = get_http_server_port()
SERVER_URL = f"http://localhost:{port}"
BOT_IDS = sorted(get_bot_ids())
LOGINS = [9000 + i for i in BOT_IDS]

async def post_with_error_handling(session, url, data, headers, tag):
    try:
        async with session.post(url, data=data, headers=headers) as resp:
            resp_data = await resp.json()
            console.print(f"[{tag}] [cyan]{resp.status}[/cyan]: {resp_data}")
            if resp.status == 200:
                sig_ok = verify_response_signature(
                    MT5_SECRET_KEY, int(headers["x-bot-id"]), int(headers["x-mt5-login"]),
                    int(time.time()), "", resp_data.get("signature", "")
                )
                color = "green" if sig_ok else "red"
                console.print(f"[{tag}] ↪️ [bold {color}]Signature OK: {sig_ok}[/bold {color}]")
    except Exception as e:
        console.print(f"[{tag}] [red]Request failed:[/red] {e}")

# --- Цикл одного бота
async def simulate_bot(bot_id: int, login: int, session: aiohttp.ClientSession):
    hb_interval = get_heartbeat_timeout_sec() // 2
    while True:
        # --- 1. Heartbeat
        now = int(time.time())

         # --- 1. Heartbeat
        heartbeat_body = json.dumps({
            "broker": "DemoBroker",
            "leverage": randint(50, 200)
        })
        heartbeat_headers = {
            "x-bot-id": str(bot_id),
            "x-mt5-login": str(login),
            "x-mt5-time": str(now),
            "x-mt5-signature": generate_signature(MT5_SECRET_KEY, bot_id, login, now, heartbeat_body)
        }

        await post_with_error_handling(
            session,
            f"{SERVER_URL}/api/v1/bot/heartbeat",
            heartbeat_body,
            heartbeat_headers,
            tag=f"{bot_id} Heartbeat"
        )

        await asyncio.sleep(1)

        # --- 2. Balance report
        balance_body = json.dumps({
            "balance": round(uniform(1, 20), 0),
            "profit": round(uniform(-200, 200), 2)
        })
        now = int(time.time())
        balance_headers = {
            "x-bot-id": str(bot_id),
            "x-mt5-login": str(login),
            "x-mt5-time": str(now),
            "x-mt5-signature": generate_signature(MT5_SECRET_KEY, bot_id, login, now, balance_body)
        }

        await post_with_error_handling(
            session,
            f"{SERVER_URL}/api/v1/bot/balance",
            balance_body,
            balance_headers,
            tag=f"{bot_id} Balance"
        )

        await asyncio.sleep(1)

        # --- 3. Signal report
        signals = [{
            "timestamp": int(time.time() * 1000),
            "symbol": "EURUSD",
            "spread": round(uniform(1, 20), 0),
            "volume": round(uniform(0.01, 1.0), 2),
            "direction": 1 if uniform(0, 1) > 0.5 else -1
        }]
        signal_body = json.dumps(signals)
        
        now = int(time.time())
        signal_headers = {
            "x-bot-id": str(bot_id),
            "x-mt5-login": str(login),
            "x-mt5-time": str(now),
            "x-mt5-signature": generate_signature(MT5_SECRET_KEY, bot_id, login, now, signal_body)
        }

        await post_with_error_handling(
            session,
            f"{SERVER_URL}/api/v1/bot/signal",
            signal_body,
            signal_headers,
            tag=f"{bot_id} Signal"
        )
        
        await asyncio.sleep(1)
        
        # ---
        
        signals = [{
            "timestamp": int(time.time() * 1000),
            "symbol": "GBPUSD",
            "spread": round(uniform(1, 20), 0),
            "volume": round(uniform(0.01, 1.0), 2),
            "direction": 1 if uniform(0, 1) > 0.5 else -1
        }]
        signal_body = json.dumps(signals)
        
        now = int(time.time())
        signal_headers = {
            "x-bot-id": str(bot_id),
            "x-mt5-login": str(login),
            "x-mt5-time": str(now),
            "x-mt5-signature": generate_signature(MT5_SECRET_KEY, bot_id, login, now, signal_body)
        }

        await post_with_error_handling(
            session,
            f"{SERVER_URL}/api/v1/bot/signal",
            signal_body,
            signal_headers,
            tag=f"{bot_id} Signal"
        )

        await asyncio.sleep(hb_interval)

# --- Главный запуск
async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [simulate_bot(bot_id, login, session) for bot_id, login in zip(BOT_IDS, LOGINS)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("[yellow]❌ Stopped by user[/yellow]")