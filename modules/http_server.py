# http_server.py

from aiohttp import web
from modules.http_handlers import (
    handle_bot_heartbeat,
    handle_bot_signal,
    handle_balance_report,
    handle_last_balance,
)
from modules.config import get_http_server_port
from modules.log_utils import log_async_call
from modules.logging_config import logger

@log_async_call
async def start_http_server():
    app = web.Application()

    app.router.add_post("/api/v1/bot/heartbeat", handle_bot_heartbeat)
    app.router.add_post("/api/v1/bot/balance", handle_balance_report)
    app.router.add_post("/api/v1/bot/signal", handle_bot_signal)
    app.router.add_get("/api/v1/last_balance", handle_last_balance)

    runner = web.AppRunner(app)
    await runner.setup()
    port = get_http_server_port()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"HTTP server started on port {port}")
    return runner
