"""
Infrastructure: SQLite Database Connection
Handles database connection and initialization.
"""

import os
import sqlite3
from typing import Optional


class SQLiteConnection:
    """SQLite database connection manager."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self._ensure_database_dir()

    def _ensure_database_dir(self):
        """Ensure database directory exists."""
        db_dir = os.path.dirname(self.database_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Get a SQLite connection with row factory."""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return cursor

    def execute_many(self, query: str, params_list: list) -> None:
        """Execute a query with multiple parameter sets."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        conn.close()

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch a single row."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        return row

    def fetch_all(self, query: str, params: tuple = ()) -> list:
        """Fetch all rows."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def close(self):
        """Close connection (no-op for sqlite3, but interface consistent)."""
        pass


def init_database(db_path: str) -> SQLiteConnection:
    """
    Initialize the database with required tables.

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLiteConnection instance
    """
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    conn = SQLiteConnection(db_path)

    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create meetings table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            scheduled_at DATETIME,
            duration_minutes INTEGER,
            status TEXT DEFAULT 'pending',
            created_by INTEGER REFERENCES users(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create audio_files table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audio_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER REFERENCES meetings(id),
            filename TEXT NOT NULL,
            original_filename TEXT,
            file_path TEXT NOT NULL,
            file_size_bytes INTEGER,
            duration_seconds REAL,
            sample_rate INTEGER,
            audio_format TEXT DEFAULT 'wav',
            status TEXT DEFAULT 'uploaded',
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create transcriptions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audio_file_id INTEGER REFERENCES audio_files(id),
            full_text TEXT,
            language TEXT DEFAULT 'vi',
            speaker_count INTEGER,
            segments_json TEXT,
            confidence REAL,
            processing_time_seconds REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create meeting_minutes table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS meeting_minutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transcription_id INTEGER REFERENCES transcriptions(id),
            meeting_id INTEGER REFERENCES meetings(id),
            summary TEXT,
            key_decisions TEXT,
            action_items TEXT,
            mom_text TEXT,
            generated_by TEXT DEFAULT 'gemma4',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create settings table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    return conn
