"""
Shared database configuration and utilities.

Provides a thread lock for coordinating SQLite access across modules
(profiles and sessions), and a single resolved path for the DB file.

Set DATABASE_PATH to override the SQLite file location (e.g. /app/data/database.db
in Docker). If unset, uses <repo root>/database.db.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def database_path() -> Path:
    """Resolved path to the SQLite database file. Ensures parent directory exists."""
    raw = os.environ.get("DATABASE_PATH")
    if raw:
        p = Path(raw).expanduser()
        p = p if p.is_absolute() else (Path.cwd() / p).resolve()
    else:
        p = _REPO_ROOT / "database.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# Shared lock for all SQLite operations on database_path()
_lock = threading.Lock()
