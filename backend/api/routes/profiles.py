"""
Profile management routes.

GET  /profiles          → list all saved profiles
GET  /profiles/{name}   → get a profile by name
DELETE /profiles/{name} → delete a profile
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.routes.teaching import _profile_response
from backend.api.schemas import ProfileResponse
from backend.core.storage import list_profiles, load_profile, profile_exists
from pathlib import Path
import re

router = APIRouter(prefix="/profiles", tags=["profiles"])

_PROFILES_DIR = Path("profiles")


@router.get("", response_model=list[str])
def get_profiles():
    """List names of all saved student profiles."""
    return list_profiles()


@router.get("/{name}", response_model=ProfileResponse)
def get_profile(name: str):
    """Get a student profile by name."""
    if not profile_exists(name):
        raise HTTPException(status_code=404, detail=f"No profile found for '{name}'")
    profile = load_profile(name)
    return _profile_response(profile)


@router.delete("/{name}")
def delete_profile(name: str):
    """Delete a student profile."""
    if not profile_exists(name):
        raise HTTPException(status_code=404, detail=f"No profile found for '{name}'")
    slug = re.sub(r"\s+", "_", name.strip().lower())
    path = _PROFILES_DIR / f"{slug}.json"
    path.unlink()
    return {"deleted": name}
