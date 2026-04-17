"""
Profile persistence.

Reads and writes UserProfile as JSON under profiles/{name}.json.
This is the only place in the codebase that touches the filesystem
for profile data — swap this module to change the storage backend.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.models.profile import UserProfile

_PROFILES_DIR = Path("profiles")


def _profile_path(name: str) -> Path:
    slug = re.sub(r"\s+", "_", name.strip().lower())
    return _PROFILES_DIR / f"{slug}.json"


def save_profile(profile: UserProfile) -> Path:
    _PROFILES_DIR.mkdir(exist_ok=True)
    path = _profile_path(profile.name)
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_profile(name: str) -> UserProfile:
    path = _profile_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No profile found for '{name}' at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return UserProfile(**data)


def profile_exists(name: str) -> bool:
    return _profile_path(name).exists()


def list_profiles() -> list[str]:
    if not _PROFILES_DIR.exists():
        return []
    return [p.stem for p in sorted(_PROFILES_DIR.glob("*.json"))]
