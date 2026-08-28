import sqlite3
from datetime import datetime, timedelta
from core.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-64000;")
    except Exception:
        pass
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        current_mode TEXT DEFAULT 'general',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # AI Suhbat xotirasi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Eslatmalar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        reminder_text TEXT,
        remind_at TIMESTAMP,
        is_sent INTEGER DEFAULT 0
    )
    """)
    
    # Statistika jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action_type TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Kanallar jadvali (Majburiy obuna)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE,
        channel_title TEXT,
        channel_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Sozlamalar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Bloklanganlar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS banned_users (
        user_id INTEGER PRIMARY KEY,
        reason TEXT,
        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 🚀 File Cache Jadvali (0.01 soniyalik tezkor file_id keshlash)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS file_cache (
        url_hash TEXT PRIMARY KEY,
        file_id TEXT,
        file_type TEXT,
        caption TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('force_sub', '0')")
    
    conn.commit()
    conn.close()

def save_cached_file(url_hash: str, file_id: str, file_type: str, caption: str = ""):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO file_cache (url_hash, file_id, file_type, caption) VALUES (?, ?, ?, ?)", (url_hash, file_id, file_type, caption))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_cached_file(url_hash: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type, caption FROM file_cache WHERE url_hash = ?", (url_hash,))
        row = cursor.fetchone()
        conn.close()
        return row
    except Exception:
        return None

def upsert_user(user_id: int, first_name: str, last_name: str, username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO users (user_id, first_name, last_name, username, last_active)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id) DO UPDATE SET
        first_name=excluded.first_name,
        last_name=excluded.last_name,
        username=excluded.username,
        last_active=CURRENT_TIMESTAMP
    """, (user_id, first_name, last_name, username))
    conn.commit()
    conn.close()

def set_user_mode(user_id: int, mode: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_mode = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (mode, user_id))
    conn.commit()
    conn.close()

def get_user_mode(user_id: int) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_mode FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["current_mode"] if row and row["current_mode"] else "general"

def save_ai_message(user_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ai_memory (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def get_ai_history(user_id: int, limit: int = 12):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM ai_memory WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return list(reversed(rows))

def clear_ai_history(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ai_memory WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def log_stat(user_id: int, action_type: str, details: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO stats (user_id, action_type, details) VALUES (?, ?, ?)", (user_id, action_type, details))
    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()

def get_channels():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_title, channel_url FROM channels")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_channel(channel_id: str, title: str, url: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO channels (channel_id, channel_title, channel_url) VALUES (?, ?, ?)", (channel_id, title, url))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def remove_channel(channel_id: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def is_banned(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM banned_users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row)

def ban_user(user_id: int, reason: str = "Qoidabuzarlik"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO banned_users (user_id, reason) VALUES (?, ?)", (user_id, reason))
    conn.commit()
    conn.close()

def unban_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_user_ids():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = [r["user_id"] for r in cursor.fetchall()]
    conn.close()
    return rows

def get_detailed_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as today FROM users WHERE date(created_at) = date('now')")
    today_users = cursor.fetchone()["today"]
    cursor.execute("SELECT COUNT(*) as active FROM users WHERE last_active >= datetime('now', '-1 day')")
    active_users = cursor.fetchone()["active"]
    cursor.execute("SELECT COUNT(*) as total_dl FROM stats WHERE action_type LIKE 'download%'")
    total_downloads = cursor.fetchone()["total_dl"]
    cursor.execute("SELECT COUNT(*) as total_ai FROM stats WHERE action_type LIKE 'ai_%'")
    total_ai = cursor.fetchone()["total_ai"]
    cursor.execute("SELECT COUNT(*) as total_shazam FROM stats WHERE action_type LIKE 'shazam_%' OR action_type = 'music_search'")
    total_shazam = cursor.fetchone()["total_shazam"]
    conn.close()
    return {
        "total_users": total_users,
        "today_users": today_users,
        "active_users": active_users,
        "total_downloads": total_downloads,
        "total_ai": total_ai,
        "total_shazam": total_shazam
    }
