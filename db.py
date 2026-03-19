from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Optional

# Файл БД (создаётся автоматически при подключении, если не существует)
DB_PATH = Path(__file__).resolve().parent / "netdata.db"


class Database:

    def __init__(self, path: Optional[Path] = None) -> None:
        self.db_path = path or DB_PATH
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def init_db(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL
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
    db.init_db()
    print(f"SQLite DB initialized at {db.db_path}")
    db.close()
