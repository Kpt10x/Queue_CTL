import sqlite3 #I'm using sqlite3 for database management
from pathlib import Path
from datetime import datetime


DB_PATH= Path("queue.db")
def now_iso()-> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_database():
    """create queue.db and the jobs table if not present."""
    DB_PATH.touch(exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                state TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                max_retries INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                next_run_at TEXT NOT NULL
            );
            """)