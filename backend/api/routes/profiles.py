"""
Profile management routes.

GET  /profiles          → list all saved profiles
GET  /profiles/{name}   → get a profile by name
DELETE /profiles/{name} → delete a profile
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ProfileResponse, profile_to_response
from backend.core.storage import delete_profile as storage_delete, list_profiles, load_profile, profile_exists

router = APIRouter(prefix="/profiles", tags=["profiles"])


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
    return profile_to_response(profile)


@router.delete("/{name}")
def delete_profile(name: str):
    """Delete a student profile."""
    if not profile_exists(name):
        raise HTTPException(status_code=404, detail=f"No profile found for '{name}'")
    storage_delete(name)
    return {"deleted": name}
