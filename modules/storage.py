import os
import sqlite3
from modules.log_utils import log_sync_call
from modules.logging_config import logger
from modules.config import DB_PATH

@log_sync_call
def db_init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица истории балансов и профитов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balance_history (
            timestamp INTEGER NOT NULL,
            profit REAL NOT NULL,
            balance REAL NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_balance_history_timestamp ON balance_history(timestamp)")

    # Таблица разрешения торговли для ботов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_trading_permission (
            bot_id INTEGER PRIMARY KEY,
            allowed INTEGER DEFAULT 1
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_id_permission ON bot_trading_permission(bot_id)")

    conn.commit()
    conn.close()
    logger.info("Database initialized")

@log_sync_call
def db_add_balance_record(timestamp: int, profit: float, balance: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO balance_history (timestamp, profit, balance) VALUES (?, ?, ?)", (timestamp, profit, balance))
    conn.commit()
    conn.close()

@log_sync_call
def db_get_balance_history(start_ts: int = None, end_ts: int = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if start_ts is not None and end_ts is not None:
        cursor.execute("SELECT * FROM balance_history WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp", (start_ts, end_ts))
    else:
        cursor.execute("SELECT * FROM balance_history ORDER BY timestamp")
    rows = cursor.fetchall()
    conn.close()
    return rows
    
@log_sync_call
def db_get_latest_balance_record():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, profit, balance
        FROM balance_history
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return row  # (timestamp, profit, balance) or None
    
@log_sync_call
def db_clear_balance_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM balance_history")
    conn.commit()
    conn.close()

@log_sync_call
def db_set_trading_permission(bot_id: int, allowed: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO bot_trading_permission (bot_id, allowed) VALUES (?, ?)", (bot_id, allowed))
    conn.commit()
    conn.close()

@log_sync_call
def db_get_trading_permission(bot_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT allowed FROM bot_trading_permission WHERE bot_id = ?", (bot_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 1  # По умолчанию разрешено
    
@log_sync_call
def db_remove_trading_permission(bot_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bot_trading_permission WHERE bot_id = ?", (bot_id,))
    conn.commit()
    conn.close()
