"""
Profile persistence.

Reads and writes UserProfile as JSON under profiles/{name}.json.
Also saves a teaching brief as profiles/{name}_brief.md, regenerated
on every save so it stays in sync with the student's current skill state.

This is the only place in the codebase that touches the filesystem
for profile data — swap this module to change the storage backend.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.models.profile import UserProfile
from backend.core.brief import build_teaching_brief

_PROFILES_DIR = Path("profiles")


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


def load_profile(name: str) -> UserProfile:
    path = _profile_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No profile found for '{name}' at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return UserProfile(**data)


def load_brief(name: str) -> str | None:
    """Load the pre-generated teaching brief, or None if not yet saved."""
    path = _brief_path(name)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def profile_exists(name: str) -> bool:
    return _profile_path(name).exists()


def list_profiles() -> list[str]:
    if not _PROFILES_DIR.exists():
        return []
    return [p.stem for p in sorted(_PROFILES_DIR.glob("*.json"))]
