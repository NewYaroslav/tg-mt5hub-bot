# http_auth.py

import hmac
import hashlib
import time
from typing import Dict
from modules.logging_config import logger
from modules.config import get_bot_ids, get_login_mismatch_threshold_sec, get_max_allowed_delay_sec

_last_login_by_bot: Dict[int, tuple] = {}  # bot_id → (login, timestamp)

def verify_signature(secret: str, bot_id: int, login: int, timestamp: int, body: str, signature: str) -> bool:
    """
    Verifies HMAC-SHA256 signature for a given bot ID, login, timestamp, and body.
    Includes logic to reject login mismatches within a short time window.
    Accepts ±1 minute HMAC window.
    """
    now = int(time.time())

    # 1. Проверка времени (anti-replay)
    max_delay = get_max_allowed_delay_sec()
    if abs(now - timestamp) > max_delay:
        logger.warning(f"[AUTH] Rejected: timestamp too far for bot_id {bot_id} (delta={abs(now - timestamp)}s)")
        return False

    # 2. Проверка ID бота
    allowed_bot_ids = get_bot_ids()
    if bot_id not in allowed_bot_ids:
        logger.warning(f"[AUTH] Rejected: unknown bot_id {bot_id}")
        return False

    # 3. Проверка смены логина
    threshold_sec = get_login_mismatch_threshold_sec()
    last_login, last_time = _last_login_by_bot.get(bot_id, (None, 0))

    if last_login is not None and login != last_login:
        if (now - last_time) < threshold_sec:
            logger.warning(f"[AUTH] Rejected: bot_id {bot_id} used different login too soon "
                           f"(prev: {last_login}, now: {login}, delta: {now - last_time}s)")
            return False

    _last_login_by_bot[bot_id] = (login, now)

    # 4. Проверка подписи по трём временным окнам
    time_bucket = timestamp // 60
    for offset in (-1, 0, 1):
        bucket = time_bucket + offset
        msg = f"{bot_id}:{login}:{bucket}:{body}".encode()
        expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, signature):
            return True

    logger.warning(f"[AUTH] Rejected: bad HMAC for bot_id {bot_id}, login {login}, timestamp {timestamp}")
    return False

def generate_signature(secret: str, bot_id: int, login: int, timestamp: int, body: str) -> str:
    bucket = timestamp // 60
    msg = f"{bot_id}:{login}:{bucket}:{body}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
