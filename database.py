import sqlite3
from pathlib import Path
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

DB_PATH = None

def set_db_path(path: Path):
    global DB_PATH
    DB_PATH = path

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                channel_type TEXT NOT NULL,
                value TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                UNIQUE(chat_id, channel_type)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                reminder_text TEXT NOT NULL,
                run_at TEXT NOT NULL,
                job_name TEXT NOT NULL
            )
        """)
        
        logger.info("Database initialized successfully")

def save_channel(chat_id: int, channel_type: str, value: str, verified: bool):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM user_channels WHERE chat_id = ? AND channel_type = ?",
            (chat_id, channel_type)
        )
        row = cur.fetchone()
        
        if row:
            cur.execute(
                "UPDATE user_channels SET value = ?, is_verified = ? WHERE id = ?",
                (value, int(verified), row[0])
            )
            logger.info(f"Updated channel {channel_type} for chat {chat_id}")
        else:
            cur.execute(
                "INSERT INTO user_channels (chat_id, channel_type, value, is_verified) "
                "VALUES (?, ?, ?, ?)",
                (chat_id, channel_type, value, int(verified))
            )
            logger.info(f"Added channel {channel_type} for chat {chat_id}")

def delete_channel(chat_id: int, channel_type: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM user_channels WHERE chat_id = ? AND channel_type = ?",
            (chat_id, channel_type)
        )
        logger.info(f"Deleted channel {channel_type} for chat {chat_id}")

def get_channels_summary(chat_id: int) -> str:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT channel_type, value, is_verified "
            "FROM user_channels WHERE chat_id = ?",
            (chat_id,)
        )
        rows = cur.fetchall()
    
    if not rows:
        return "Koi channel select nahi kiya."
    
    lines = []
    for ctype, value, verified in rows:
        status = "✅ verified" if verified else "⏳ pending"
        lines.append(f"• {ctype}: {value} ({status})")
    return "\n".join(lines)

def is_user_verified(chat_id: int) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM user_channels "
            "WHERE chat_id = ? AND is_verified = 1",
            (chat_id,)
        )
        count = cur.fetchone()[0]
    return count > 0

def get_user_channels(chat_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT channel_type, value FROM user_channels "
            "WHERE chat_id = ? AND is_verified = 1",
            (chat_id,)
        )
        return cur.fetchall()

def save_reminder(chat_id: int, text: str, run_at: str, job_name: str) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reminders (chat_id, reminder_text, run_at, job_name) "
            "VALUES (?, ?, ?, ?)",
            (chat_id, text, run_at, job_name)
        )
        rid = cur.lastrowid
        logger.info(f"Saved reminder {rid} for chat {chat_id}")
        return rid

def delete_reminder(reminder_id: int, chat_id: int = None):
    with get_db() as conn:
        cur = conn.cursor()
        if chat_id:
            cur.execute(
                "DELETE FROM reminders WHERE id = ? AND chat_id = ?",
                (reminder_id, chat_id)
            )
        else:
            cur.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        logger.info(f"Deleted reminder {reminder_id}")

def get_pending_reminders(chat_id: int = None):
    with get_db() as conn:
        cur = conn.cursor()
        if chat_id:
            cur.execute(
                "SELECT id, reminder_text, run_at FROM reminders "
                "WHERE chat_id = ? ORDER BY run_at",
                (chat_id,)
            )
        else:
            cur.execute(
                "SELECT id, chat_id, reminder_text, run_at, job_name "
                "FROM reminders ORDER BY run_at"
            )
        return cur.fetchall()

def get_reminder_by_id(reminder_id: int, chat_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT job_name FROM reminders WHERE id = ? AND chat_id = ?",
            (reminder_id, chat_id)
        )
        return cur.fetchone()
