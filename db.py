from __future__ import annotations

import csv
from pathlib import Path
import sqlite3
from typing import Optional


DB_PATH = Path(__file__).resolve().parent / "netdata.db"

CSV_PATH = Path(__file__).resolve().parent / "data_with_coords.csv"

ORG_CSV_PATH = Path(__file__).resolve().parent / "organizations.csv"


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
                        password TEXT NOT NULL CHECK(length(password) > 8 AND length(password) < 25),
                        email TEXT NOT NULL UNIQUE CHECK(length(email) <= 128),
                        verified INTEGER DEFAULT 0,
                        verification_token TEXT
                    )
                    """
                )
            
            
            if not self._table_exists('organization'):
                self.conn.execute(
                    """
                    CREATE VIRTUAL TABLE organization USING fts5(
                        name,
                        address,
                        foundation_date,
                        founder_surname
                    )
                    """
                )
                
                if ORG_CSV_PATH.exists():
                    with open(ORG_CSV_PATH, mode='r', encoding='utf-8') as file:
                        reader = csv.reader(file)
                        
                        org_data = [row for row in reader if len(row) == 4]
                        if org_data:
                            self.conn.executemany(
                                "INSERT INTO organization (name, address, foundation_date, founder_surname) VALUES (?, ?, ?, ?)",
                                org_data
                            )

            
            if not self._table_exists('token'):
                self.conn.execute(
                    """
                     CREATE TABLE token (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        token_tag TEXT NOT NULL,
                        remaining_requests_counter INTEGER DEFAULT 0,
                        expires_at DATETIME NOT NULL, 
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )
            
            
            if not self._table_exists('buildings'):
                self.conn.execute(
                    """
                    CREATE TABLE buildings (
                        region_code TEXT,
                        full_address TEXT,
                        city TEXT,
                        street_address TEXT,
                        street_type TEXT,
                        street_name TEXT,
                        house_number TEXT,
                        unom_id TEXT,
                        district TEXT,
                        build_year INTEGER,
                        longitude REAL,  -- Числовой тип
                        latitude REAL    -- Числовой тип
                    )
                    """
                )
                
                
                self.conn.execute("CREATE INDEX idx_coords ON buildings (latitude, longitude)")

                if CSV_PATH.exists():
                    with open(CSV_PATH, mode='r', encoding='utf-8') as file:
                        reader = csv.reader(file)
                        data_to_insert = []
                        
                        for row in reader:
                            if len(row) == 12:
                                try:
                                    
                                    processed_row = list(row)
                                    processed_row[9] = int(row[9]) if row[9].isdigit() else 0 # build_year
                                    processed_row[10] = float(row[10]) # longitude
                                    processed_row[11] = float(row[11]) # latitude
                                    data_to_insert.append(tuple(processed_row))
                                except ValueError:
                                
                                    continue
                        
                        if data_to_insert:
                            self.conn.executemany(
                                "INSERT INTO buildings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                data_to_insert
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

    
    res = db.execute("SELECT COUNT(*) FROM organization").fetchone()
    print(f"Organizations loaded into FTS5 table: {res[0]}")
    db.close()