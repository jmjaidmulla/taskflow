# =============================================================================
# database.py
# SQLite connection helper and database initialiser.
# Creates the 'users' and 'tasks' tables if they don't exist,
# and runs safe ALTER TABLE migrations for older databases.
# =============================================================================

import sqlite3

DB_NAME = "database.db"


def get_connection() -> sqlite3.Connection:
    """Open and return a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")   # enforce FK constraints
    conn.row_factory = sqlite3.Row             # access columns by name
    return conn


def init_db():
    """
    Create tables and run migrations.
    Safe to call on every startup — uses IF NOT EXISTS.
    """
    conn   = get_connection() # Open DB
    cursor = conn.cursor()

    # ── Users table ───────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER  PRIMARY KEY AUTOINCREMENT,
        username      TEXT     UNIQUE NOT NULL,
        display_name  TEXT,
        password      TEXT     NOT NULL,
        mobile        TEXT     UNIQUE,
        profile_image TEXT,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── Tasks table ───────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id          INTEGER  PRIMARY KEY AUTOINCREMENT,
        title       TEXT     NOT NULL,
        description TEXT,
        category    TEXT     DEFAULT 'personal',
        priority    TEXT     DEFAULT 'medium',
        due_date    TEXT,
        is_done     INTEGER  DEFAULT 0,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_id     INTEGER  NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # ── Safe migrations for existing databases ────────────────────────────────
    # These will silently fail if the column already exists — that's intentional.
    migrations = [
        "ALTER TABLE users ADD COLUMN mobile TEXT",
        "ALTER TABLE users ADD COLUMN display_name TEXT",
        "ALTER TABLE users ADD COLUMN profile_image TEXT",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
            col = sql.split("COLUMN ")[1].split(" ")[0]
            print(f"[DB] Migration applied: added '{col}' column.")
        except Exception:
            pass  # column already exists — skip silently

    conn.commit()
    conn.close()
    print("[DB] Database ready.")