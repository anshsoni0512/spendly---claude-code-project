import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "expense_tracker.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS months (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            year_month TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now')),
            UNIQUE(user_id, year_month)
        )
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        conn.close()
        return

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    expenses = [
        (user_id, 450.00, "Food", "2026-05-01", "Lunch at café"),
        (user_id, 180.00, "Transport", "2026-05-02", "Ola cab to office"),
        (user_id, 1200.00, "Bills", "2026-05-03", "Electricity bill"),
        (user_id, 850.00, "Health", "2026-05-05", "Pharmacy - vitamins"),
        (user_id, 599.00, "Entertainment", "2026-05-07", "Netflix subscription"),
        (user_id, 2300.00, "Shopping", "2026-05-09", "New headphones"),
        (user_id, 200.00, "Other", "2026-05-10", "Miscellaneous"),
        (user_id, 320.00, "Food", "2026-05-11", "Grocery run"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
