"""
In-memory session store for v1.

Two session types:
  InterviewSession  — holds an InterviewAgent instance
  TeachingSession   — holds profile + current lesson plan + last report

Both are keyed by UUID session_id.
Thread-safe via a simple lock (single-process FastAPI with uvicorn).
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

from backend.core.interview import InterviewAgent
from backend.models.profile import UserProfile
from backend.models.teaching import EvaluationReport, LessonPlan

_lock = threading.Lock()
_interview_sessions:  dict[str, "InterviewSession"]  = {}
_teaching_sessions:   dict[str, "TeachingSession"]   = {}


# ── Session dataclasses ───────────────────────────────────────────────────────

@dataclass
class InterviewSession:
    session_id: str
    agent: InterviewAgent


@dataclass
class TeachingSession:
    session_id: str
    profile: UserProfile
    lesson_plan: LessonPlan | None = None
    last_report: EvaluationReport | None = None


# ── Interview session management ──────────────────────────────────────────────

def create_interview_session() -> InterviewSession:
    agent = InterviewAgent()
    session = InterviewSession(session_id=str(uuid.uuid4()), agent=agent)
    with _lock:
        _interview_sessions[session.session_id] = session
    return session


def get_interview_session(session_id: str) -> InterviewSession:
    with _lock:
        session = _interview_sessions.get(session_id)
    if session is None:
        raise KeyError(f"Interview session '{session_id}' not found")
    return session


def delete_interview_session(session_id: str) -> None:
    with _lock:
        _interview_sessions.pop(session_id, None)


# ── Teaching session management ───────────────────────────────────────────────

def create_teaching_session(profile: UserProfile) -> TeachingSession:
    session = TeachingSession(session_id=str(uuid.uuid4()), profile=profile)
    with _lock:
        _teaching_sessions[session.session_id] = session
    return session


def get_teaching_session(session_id: str) -> TeachingSession:
    with _lock:
        session = _teaching_sessions.get(session_id)
    if session is None:
        raise KeyError(f"Teaching session '{session_id}' not found")
    return session


def update_teaching_session(session: TeachingSession) -> None:
    with _lock:
        _teaching_sessions[session.session_id] = session
