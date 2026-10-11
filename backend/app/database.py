import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.config import settings

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory and WAL mode."""
    db_path = settings.resolved_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure 0600 permissions on POSIX
    is_new = not db_path.exists()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    if is_new and os.name != "nt":
        try:
            os.chmod(str(db_path), 0o600)
        except OSError:
            pass

    # Enable WAL mode for better concurrency and integrity
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db() -> None:
    """Initializes tables for users, credentials, invites, challenges, and sessions."""
    conn = get_db_connection()
    try:
        with conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS credentials (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                public_key BLOB NOT NULL,
                sign_count INTEGER NOT NULL DEFAULT 0,
                transports TEXT,
                name TEXT NOT NULL DEFAULT 'Passkey',
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS invites (
                token TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                used_by TEXT
            );

            CREATE TABLE IF NOT EXISTS challenges (
                challenge TEXT PRIMARY KEY,
                user_id TEXT,
                type TEXT NOT NULL, -- 'registration' or 'authentication'
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_credentials_user_id ON credentials(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            """)
    finally:
        conn.close()
