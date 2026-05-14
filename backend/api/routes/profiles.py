"""
Profile management routes.

GET  /profiles          → list all saved profiles
GET  /profiles/{name}   → get a profile by name
DELETE /profiles/{name} → delete a profile
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ProfileResponse, ProfileSummary, profile_to_response
from backend.core.storage import delete_profile as storage_delete, list_profiles, load_profile, profile_exists

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileSummary])
def get_profiles():
    """List all student profiles as {student_id, name} summaries."""
    return list_profiles()


@router.get("/{student_id:path}", response_model=ProfileResponse)
def get_profile(student_id: str):
    """Get a student profile by student_id."""
    if not profile_exists(student_id):
        raise HTTPException(status_code=404, detail=f"No profile found for '{student_id}'")
    profile = load_profile(student_id)
    return profile_to_response(profile)


@router.delete("/{student_id:path}")
def delete_profile(student_id: str):
    """Delete a student profile."""
    if not profile_exists(student_id):
        raise HTTPException(status_code=404, detail=f"No profile found for '{student_id}'")
    storage_delete(student_id)
    return {"deleted": student_id}
