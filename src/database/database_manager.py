import sqlite3

from src.database.database_paths import DATABASE_DIR, DATABASE_PATH
from src.database.database_schema import SCHEMA_SQL


class DatabaseManager:
    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = database_path
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.database_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def execute(self, sql, params=None):
        params = params or ()

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def fetch_all(self, sql, params=None):
        params = params or ()

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def fetch_one(self, sql, params=None):
        params = params or ()

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()
