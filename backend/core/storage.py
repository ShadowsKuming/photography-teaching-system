"""
Profile persistence.

Reads and writes UserProfile as JSON in an SQLite database.
student_id (e.g. "John#2352") is the primary key; name is display-only.

Schema v2 changes vs v1:
  profiles : added student_id column as PK, name as separate column
  leaderboard : student_id replaces name as PK component; subject added to PK;
                name stored for display
"""

from __future__ import annotations

import json
import random
import sqlite3
from datetime import date

from backend.models.profile import UserProfile
from backend.core.brief import build_teaching_brief
from backend.core.db import _lock, database_path


# ── Schema management ─────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(database_path(), check_same_thread=False)
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    if 'profiles' not in tables:
        conn.execute("""
            CREATE TABLE profiles (
                student_id TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                data       TEXT NOT NULL,
                brief      TEXT
            )
        """)
    else:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(profiles)")}
        if 'student_id' not in cols:
            _migrate_profiles_v1_to_v2(conn)

    if 'leaderboard' not in tables:
        conn.execute("""
            CREATE TABLE leaderboard (
                student_id TEXT NOT NULL,
                name       TEXT NOT NULL,
                subject    TEXT NOT NULL,
                date       TEXT NOT NULL,
                daily_xp   REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (student_id, subject, date)
            )
        """)
    else:
        lb_cols = {r[1] for r in conn.execute("PRAGMA table_info(leaderboard)")}
        if 'student_id' not in lb_cols:
            conn.execute("DROP TABLE leaderboard")
            conn.execute("""
                CREATE TABLE leaderboard (
                    student_id TEXT NOT NULL,
                    name       TEXT NOT NULL,
                    subject    TEXT NOT NULL,
                    date       TEXT NOT NULL,
                    daily_xp   REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (student_id, subject, date)
                )
            """)

    conn.commit()


def _migrate_profiles_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Migrate profiles table from name-keyed v1 to student_id-keyed v2."""
    conn.execute("ALTER TABLE profiles RENAME TO _profiles_v1")
    conn.execute("""
        CREATE TABLE profiles (
            student_id TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            data       TEXT NOT NULL,
            brief      TEXT
        )
    """)
    rows = conn.execute("SELECT name, data, brief FROM _profiles_v1").fetchall()
    for (name, data_json, brief) in rows:
        student_id = _make_student_id(name, conn)
        data = json.loads(data_json)
        data['student_id'] = student_id
        conn.execute(
            "INSERT INTO profiles (student_id, name, data, brief) VALUES (?, ?, ?, ?)",
            (student_id, name, json.dumps(data), brief),
        )
    conn.execute("DROP TABLE _profiles_v1")
    conn.commit()


# ── student_id generation ─────────────────────────────────────────────────────

def _make_student_id(name: str, conn: sqlite3.Connection) -> str:
    """Generate a unique student_id. Caller must hold _lock."""
    for _ in range(20):
        sid = f"{name.strip()}#{random.randint(1000, 9999)}"
        if not conn.execute("SELECT 1 FROM profiles WHERE student_id = ?", (sid,)).fetchone():
            return sid
    raise RuntimeError(f"Could not generate unique student_id for '{name}'")


# ── Public CRUD ───────────────────────────────────────────────────────────────

def create_profile(profile: UserProfile) -> UserProfile:
    """
    Persist a brand-new profile. Generates and sets student_id atomically.
    Returns the profile with student_id populated.
    """
    brief = build_teaching_brief(profile)
    with _lock:
        with _get_db() as conn:
            student_id = _make_student_id(profile.name, conn)
            profile = profile.model_copy(update={"student_id": student_id})
            data = profile.model_dump_json(indent=2)
            conn.execute(
                "INSERT INTO profiles (student_id, name, data, brief) VALUES (?, ?, ?, ?)",
                (student_id, profile.name, data, brief),
            )
            conn.commit()
    return profile


def save_profile(profile: UserProfile) -> None:
    """Update an existing profile (student_id must already be set)."""
    if not profile.student_id:
        raise ValueError("save_profile called with empty student_id — use create_profile for new profiles")
    data = profile.model_dump_json(indent=2)
    brief = build_teaching_brief(profile)
    with _lock:
        with _get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO profiles (student_id, name, data, brief) VALUES (?, ?, ?, ?)",
                (profile.student_id, profile.name, data, brief),
            )
            conn.commit()


def load_profile(student_id: str) -> UserProfile:
    with _lock:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT data FROM profiles WHERE student_id = ?", (student_id,)
            ).fetchone()
    if not row:
        raise FileNotFoundError(f"No profile found for '{student_id}'")
    return UserProfile.model_validate(json.loads(row[0]))


def load_brief(student_id: str) -> str | None:
    with _lock:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT brief FROM profiles WHERE student_id = ?", (student_id,)
            ).fetchone()
    if not row or row[0] is None:
        return None
    return row[0]


def profile_exists(student_id: str) -> bool:
    with _lock:
        with _get_db() as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM profiles WHERE student_id = ?", (student_id,)
                ).fetchone()
            )


def delete_profile(student_id: str) -> None:
    with _lock:
        with _get_db() as conn:
            conn.execute("DELETE FROM profiles WHERE student_id = ?", (student_id,))
            conn.commit()


def list_profiles() -> list[dict]:
    """Return all profiles as {student_id, name} summaries, ordered by name."""
    with _lock:
        with _get_db() as conn:
            rows = conn.execute("SELECT student_id, name FROM profiles ORDER BY name").fetchall()
    return [{"student_id": r[0], "name": r[1]} for r in rows]


# ── Leaderboard ───────────────────────────────────────────────────────────────

def update_leaderboard(student_id: str, name: str, subject: str, daily_xp: float) -> None:
    today = date.today().isoformat()
    with _lock:
        with _get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO leaderboard (student_id, name, subject, date, daily_xp)
                   VALUES (?, ?, ?, ?, ?)""",
                (student_id, name, subject, today, daily_xp),
            )
            conn.commit()


def get_leaderboard(subject: str, limit: int = 20) -> list[dict]:
    today = date.today().isoformat()
    with _lock:
        with _get_db() as conn:
            rows = conn.execute(
                """SELECT student_id, name, daily_xp FROM leaderboard
                   WHERE subject = ? AND date = ?
                   ORDER BY daily_xp DESC LIMIT ?""",
                (subject, today, limit),
            ).fetchall()
    return [{"student_id": r[0], "name": r[1], "daily_xp": r[2]} for r in rows]
