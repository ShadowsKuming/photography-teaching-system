"""
Profile persistence.

Reads and writes UserProfile as JSON in an SQLite database.
Stores teaching briefs as a column in the profiles table,
regenerated on every save so it stays in sync with the student's current skill state.

This is the only place in the codebase that touches the database
for profile data — swap this module to change the storage backend.
"""

from __future__ import annotations

import json
import sqlite3

from backend.models.profile import UserProfile
from backend.core.brief import build_teaching_brief
from backend.core.db import _lock, database_path


def _get_db() -> sqlite3.Connection:
    """Get database connection. Thread-safe via _lock in calling functions."""
    conn = sqlite3.connect(database_path(), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            brief TEXT
        )
    """)
    conn.commit()
    return conn


def save_profile(profile: UserProfile) -> None:
    data = profile.model_dump_json(indent=2)
    brief = build_teaching_brief(profile)
    with _lock:
        with _get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO profiles (name, data, brief) VALUES (?, ?, ?)",
                (profile.name, data, brief)
            )
            conn.commit()


def load_profile(name: str) -> UserProfile:
    with _lock:
        with _get_db() as conn:
            cursor = conn.execute("SELECT data FROM profiles WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                raise FileNotFoundError(f"No profile found for '{name}'")
            data = json.loads(row[0])
            return UserProfile(**data)


def load_brief(name: str) -> str | None:
    """Load the teaching brief from the database, or None if not yet saved."""
    with _lock:
        with _get_db() as conn:
            cursor = conn.execute("SELECT brief FROM profiles WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row or row[0] is None:
                return None
            return row[0]


def profile_exists(name: str) -> bool:
    with _lock:
        with _get_db() as conn:
            cursor = conn.execute("SELECT 1 FROM profiles WHERE name = ?", (name,))
            return cursor.fetchone() is not None


def list_profiles() -> list[str]:
    with _lock:
        with _get_db() as conn:
            cursor = conn.execute("SELECT name FROM profiles ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

