from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Optional

# Файл БД (создаётся автоматически при подключении, если не существует)
DB_PATH = Path(__file__).resolve().parent / "netdata.db"


class Database:

    def __init__(self, custom_path: Optional[Path] = None) -> None:
        self.db_path = custom_path or DB_PATH
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _table_exists(self, table_name: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cur.fetchone() is not None

    def _init_db(self) -> None:
        with self.conn:
            if not self._table_exists('users'):
                self.conn.execute(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        login TEXT NOT NULL UNIQUE CHECK(length(login) <= 25),
                        password TEXT NOT NULL CHECK(length(password) > 8 AND length(password) < 25)
                        email TEXT NOT NULL UNIQUE CHECK(length(email) <= 128),
                        verified INTEGER DEFAULT 0,
                    )
                    """
                )
            if not self._table_exists('organization'):
                self.conn.execute(
                    """
                    CREATE TABLE organization (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL CHECK(length(name) <= 128),
                        address TEXT,
                        geolocation TEXT,
                        phone TEXT,
                        post_index TEXT,
                        email TEXT,
                        info TEXT CHECK(length(info) <= 128)
                    )
                    """
                )
            if not self._table_exists('token'):
                self.conn.execute(
                    """
                    CREATE TABLE token (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        token_tag TEXT NOT NULL CHECK(length(token_tag) <= 128),
                        remaining_requests_counter INTEGER DEFAULT 0,
                        remaining_time INTEGER DEFAULT 0,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur

    def close(self) -> None:
        self.conn.close()


if __name__ == "__main__":
    db = Database()
    print(f"SQLite DB initialized at {db.db_path}")
    db.close()
