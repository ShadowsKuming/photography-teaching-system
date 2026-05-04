"""
Persistent session store using SQLite.

Two session types:
  InterviewSession  — holds an InterviewAgent instance
  TeachingSession   — holds profile + current lesson plan + last report

Both are keyed by UUID session_id.
Sessions expire after 24 hours and are automatically cleaned up.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.core.i18n import LanguageCode
from backend.core.interview import InterviewAgent
from backend.models.profile import UserProfile
from backend.models.teaching import EvaluationReport, LessonPlan
from backend.core.db import _lock

# ── Database setup ──────────────────────────────────────────────────────────

_DB_PATH = Path(__file__).parent.parent.parent / "database.db"
_SESSION_EXPIRY_HOURS = 24

def _get_db() -> sqlite3.Connection:
    """Get database connection with row factory."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    """Initialize database and create tables if they don't exist."""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                session_type TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_type ON sessions(session_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)
        """)
        conn.commit()

def _cleanup_expired_sessions():
    """Remove sessions older than SESSION_EXPIRY_HOURS."""
    expiry_time = time.time() - (_SESSION_EXPIRY_HOURS * 3600)
    with _get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE updated_at < ?", (expiry_time,))
        conn.commit()

# Initialize database on import
_init_db()


# ── Session dataclasses ───────────────────────────────────────────────────────

@dataclass
class InterviewSession:
    session_id: str
    agent: InterviewAgent
    language: LanguageCode = "en-GB"

    def to_dict(self) -> dict:
        """Serialize to dict for database storage."""
        return {
            "session_id": self.session_id,
            "agent_state": self.agent.state,
            "agent_history": self.agent.history,
            "agent_style_selection": self.agent.style_selection,
            "agent_student_name": self.agent.student_name,
            "agent_turn_count": self.agent._turn_count,
            "agent_opening": getattr(self.agent, '_opening', '')
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InterviewSession":
        """Deserialize from dict."""
        agent = InterviewAgent.__new__(InterviewAgent)  # Create without calling __init__
        agent.state = data["agent_state"]
        agent.history = data["agent_history"]
        agent.style_selection = data["agent_style_selection"]
        agent.student_name = data["agent_student_name"]
        agent._turn_count = data["agent_turn_count"]
        agent._opening = data["agent_opening"]
        return cls(session_id=data["session_id"], agent=agent)


@dataclass
class TeachingSession:
    session_id: str
    profile: UserProfile
    lesson_plan: LessonPlan | None = None
    last_report: EvaluationReport | None = None
    language: LanguageCode = "en-GB"

    def to_dict(self) -> dict:
        """Serialize to dict for database storage."""
        return {
            "session_id": self.session_id,
            "profile": self.profile.model_dump(),
            "lesson_plan": self.lesson_plan.model_dump() if self.lesson_plan else None,
            "last_report": self.last_report.model_dump() if self.last_report else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TeachingSession":
        """Deserialize from dict."""
        profile = UserProfile.model_validate(data["profile"])
        lesson_plan = LessonPlan.model_validate(data["lesson_plan"]) if data["lesson_plan"] else None
        last_report = EvaluationReport.model_validate(data["last_report"]) if data["last_report"] else None
        return cls(
            session_id=data["session_id"],
            profile=profile,
            lesson_plan=lesson_plan,
            last_report=last_report
        )


# ── Interview session management ──────────────────────────────────────────────

def create_interview_session(language: LanguageCode = "en-GB") -> InterviewSession:
    agent = InterviewAgent(language=language)
    session = InterviewSession(session_id=str(uuid.uuid4()), agent=agent, language=language)
    now = time.time()

    with _lock:
        with _get_db() as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, session_type, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session.session_id,
                "interview",
                json.dumps(session.to_dict()),
                now,
                now
            ))
            conn.commit()

    return session


def get_interview_session(session_id: str) -> InterviewSession:
    with _lock:
        _cleanup_expired_sessions()
        with _get_db() as conn:
            row = conn.execute("""
                SELECT data FROM sessions
                WHERE session_id = ? AND session_type = 'interview'
            """, (session_id,)).fetchone()

    if row is None:
        raise KeyError(f"Interview session '{session_id}' not found")

    data = json.loads(row["data"])
    return InterviewSession.from_dict(data)


def update_interview_session(session: InterviewSession) -> None:
    now = time.time()
    with _lock:
        with _get_db() as conn:
            conn.execute("""
                UPDATE sessions
                SET data = ?, updated_at = ?
                WHERE session_id = ? AND session_type = 'interview'
            """, (
                json.dumps(session.to_dict()),
                now,
                session.session_id
            ))
            conn.commit()


def delete_interview_session(session_id: str) -> None:
    with _lock:
        with _get_db() as conn:
            conn.execute("""
                DELETE FROM sessions WHERE session_id = ? AND session_type = 'interview'
            """, (session_id,))
            conn.commit()


# ── Teaching session management ───────────────────────────────────────────────

def create_teaching_session(profile: UserProfile, language: LanguageCode = "en-GB") -> TeachingSession:
    session = TeachingSession(session_id=str(uuid.uuid4()), profile=profile, language=language)
    now = time.time()

    with _lock:
        with _get_db() as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, session_type, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session.session_id,
                "teaching",
                json.dumps(session.to_dict()),
                now,
                now
            ))
            conn.commit()

    return session


def get_teaching_session(session_id: str) -> TeachingSession:
    with _lock:
        _cleanup_expired_sessions()
        with _get_db() as conn:
            row = conn.execute("""
                SELECT data FROM sessions
                WHERE session_id = ? AND session_type = 'teaching'
            """, (session_id,)).fetchone()

    if row is None:
        raise KeyError(f"Teaching session '{session_id}' not found")

    data = json.loads(row["data"])
    return TeachingSession.from_dict(data)


def update_teaching_session(session: TeachingSession) -> None:
    now = time.time()
    with _lock:
        with _get_db() as conn:
            conn.execute("""
                UPDATE sessions
                SET data = ?, updated_at = ?
                WHERE session_id = ? AND session_type = 'teaching'
            """, (
                json.dumps(session.to_dict()),
                now,
                session.session_id
            ))
            conn.commit()
