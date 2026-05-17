import sqlite3
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config


def get_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE,
                password    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                email       TEXT    NOT NULL UNIQUE,
                phone       TEXT,
                created_at  TEXT    NOT NULL
            )
        ''')
        conn.commit()


# ---------- users ----------

def create_user(username, password):
    hashed = generate_password_hash(password)
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
            (username, hashed, created_at)
        )
        conn.commit()
        return cursor.lastrowid


def get_user_by_username(username):
    with get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        ).fetchone()
    return dict(row) if row else None


# ---------- customers ----------

def get_all_customers():
    with get_connection() as conn:
        rows = conn.execute(
            'SELECT id, name, email, phone, created_at FROM customers ORDER BY id'
        ).fetchall()
    return [dict(row) for row in rows]
