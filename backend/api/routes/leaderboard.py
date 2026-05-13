"""
Leaderboard routes.

GET /leaderboard/{subject}  → top 20 students by daily XP for a subject type (today only)
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.storage import get_leaderboard
from backend.models.profile import PrimarySubject

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    daily_xp: int


class LeaderboardResponse(BaseModel):
    subject: str
    date: str
    entries: list[LeaderboardEntry]


@router.get("/{subject}", response_model=LeaderboardResponse)
def get_subject_leaderboard(subject: PrimarySubject):
    """
    Return today's top 20 students for a given subject type (portrait / scene / object).
    Rankings reset at midnight each day.
    """
    rows = get_leaderboard(subject)
    return LeaderboardResponse(
        subject=subject,
        date=date.today().isoformat(),
        entries=[
            LeaderboardEntry(rank=i + 1, name=row["name"], daily_xp=int(row["daily_xp"]))
            for i, row in enumerate(rows)
        ],
    )
