"""
Profile persistence.

Reads and writes UserProfile as JSON under profiles/{name}.json.
Also saves a teaching brief as profiles/{name}_brief.md, regenerated
on every save so it stays in sync with the student's current skill state.

Reads and writes UserProfile as JSON in an SQLite database.
This is the only place in the codebase that touches the filesystem
for profile data — swap this module to change the storage backend.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.models.profile import UserProfile
from backend.core.brief import build_teaching_brief

_DB_PATH = Path(__file__).parent.parent.parent / "database.db"


def _slug(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip().lower())


def _profile_path(name: str) -> Path:
    return _PROFILES_DIR / f"{_slug(name)}.json"


def _brief_path(name: str) -> Path:
    return _PROFILES_DIR / f"{_slug(name)}_brief.md"


def save_profile(profile: UserProfile) -> Path:
    _PROFILES_DIR.mkdir(exist_ok=True)
    path = _profile_path(profile.name)
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")

    # Regenerate teaching brief on every save
    brief = build_teaching_brief(profile)
    _brief_path(profile.name).write_text(brief, encoding="utf-8")

    return path
def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            data TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_profile(profile: UserProfile) -> None:
    data = profile.model_dump_json(indent=2)
    with _get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO profiles (name, data) VALUES (?, ?)",
            (profile.name, data)
        )
        conn.commit()


def load_profile(name: str) -> UserProfile:
    with _get_db() as conn:
        cursor = conn.execute("SELECT data FROM profiles WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            raise FileNotFoundError(f"No profile found for '{name}'")
        data = json.loads(row[0])
        return UserProfile(**data)


def load_brief(name: str) -> str | None:
    """Load the pre-generated teaching brief, or None if not yet saved."""
    path = _brief_path(name)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def profile_exists(name: str) -> bool:
    with _get_db() as conn:
        cursor = conn.execute("SELECT 1 FROM profiles WHERE name = ?", (name,))
        return cursor.fetchone() is not None


def list_profiles() -> list[str]:
    with _get_db() as conn:
        cursor = conn.execute("SELECT name FROM profiles ORDER BY name")
        return [row[0] for row in cursor.fetchall()]
