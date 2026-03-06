import sqlite3

DB_NAME = "database.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        display_name  TEXT,
        password      TEXT NOT NULL,
        mobile        TEXT UNIQUE,
        profile_image TEXT,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        description TEXT,
        category    TEXT DEFAULT 'personal',
        priority    TEXT DEFAULT 'medium',
        due_date    TEXT,
        is_done     INTEGER DEFAULT 0,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_id     INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Safe migrations for existing databases
    migrations = [
        "ALTER TABLE users ADD COLUMN mobile TEXT",
        "ALTER TABLE users ADD COLUMN display_name TEXT",
        "ALTER TABLE users ADD COLUMN profile_image TEXT",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
            col = sql.split("COLUMN ")[1].split(" ")[0]
            print(f"Migration: added '{col}' column.")
        except Exception:
            pass

    conn.commit()
    conn.close()
    print("Database ready.")