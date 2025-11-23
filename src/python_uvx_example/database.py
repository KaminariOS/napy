"""SQLite database module for storing command execution history."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


def get_db_path() -> Path:
    """Get the path to the SQLite database file."""
    config_root = Path.home() / ".config" / "napy"
    config_root.mkdir(parents=True, exist_ok=True)
    return config_root / "commands.db"


def init_database() -> None:
    """Initialize the database with the commands table if it doesn't exist."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            exit_code INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def save_command(command: str, start_time: datetime, end_time: datetime | None = None, exit_code: int | None = None) -> None:
    """Save a command execution record to the database."""
    init_database()
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO commands (command, start_time, end_time, exit_code)
        VALUES (?, ?, ?, ?)
    """, (
        command,
        start_time.isoformat(),
        end_time.isoformat() if end_time else None,
        exit_code
    ))
    
    conn.commit()
    conn.close()

