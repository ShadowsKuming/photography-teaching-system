"""
Teaching routes.

POST /teach/start          → load profile, generate first lesson plan
POST /teach/{id}/submit    → submit photo + live context → feedback
POST /teach/{id}/next      → advance to next lesson plan
GET  /teach/{id}/profile   → get current profile state
"""

from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, HTTPException
from PIL import Image

from backend.api.schemas import (
    ProfileResponse,
    SkillLevelOut,
    TeachNextResponse,
    TeachStartRequest,
    TeachStartResponse,
    TeachSubmitRequest,
    TeachSubmitResponse,
)
from backend.api.sessions import (
    create_teaching_session,
    get_teaching_session,
    update_teaching_session,
)
from backend.core.planner import plan_lesson
from backend.core.storage import load_profile, save_profile
from backend.core.teacher import complete_session_block
from backend.models.session import (
    CaptureRecord,
    FinalCaptureState,
    LiveSessionContext,
    ObservedIssue,
    SessionEvent,
)

router = APIRouter(prefix="/teach", tags=["teaching"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _decode_image(image_base64: str) -> Image.Image:
    try:
        data = base64.b64decode(image_base64)
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid image data: {exc}")


def _parse_live_context(schema) -> LiveSessionContext:
    """Convert the loose API schema into the strict LiveSessionContext model."""
    def _ts(s: str) -> datetime:
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.utcnow()

    issues = [
        ObservedIssue(
            issue_type=i.issue_type,
            first_detected=_ts(i.first_detected),
            last_detected=_ts(i.last_detected),
            severity=i.severity,
        )
        for i in schema.observed_issues
    ]

    events = [
        SessionEvent(
            type=e.type,
            detail=e.detail,
            timestamp=_ts(e.timestamp),
            linked_issue=e.linked_issue,
        )
        for e in schema.events
    ]

    captures = [CaptureRecord(timestamp=_ts(c.timestamp)) for c in schema.captures]
    if not captures:
        captures = [CaptureRecord()]

    fcs_data = schema.final_capture_state.model_dump()
    final_state = FinalCaptureState(**fcs_data)

    return LiveSessionContext(
        target_skill=schema.target_skill,
        observed_issues=issues,
        events=events,
        final_capture_state=final_state,
        captures=captures,
    )


def _profile_response(profile) -> ProfileResponse:
    return ProfileResponse(
        name=profile.name,
        primary_goal=profile.primary_goal,
        primary_subject=profile.primary_subject,
        style=profile.style_preference.selected_style,
        milestone=profile.milestone_state.current_milestone,
        skill_state={
            skill: SkillLevelOut(
                level=profile.skill_state.get(skill).level,
                recent_attempts=profile.skill_state.get(skill).recent_attempts,
            )
            for skill in ["composition", "lighting", "subject_clarity",
                          "pose_expression", "background_control"]
        },
        device_type=profile.device.type,
        device_constraints=profile.device.constraints,
        is_diagnostic=profile.is_diagnostic,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start", response_model=TeachStartResponse)
def start_teaching(body: TeachStartRequest):
    """
    Load an existing profile by name and create a teaching session.
    Generates the first lesson plan immediately.
    """
    try:
        profile = load_profile(body.name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No profile found for '{body.name}'")

    lesson_plan = plan_lesson(profile)
    session = create_teaching_session(profile)
    session.lesson_plan = lesson_plan
    update_teaching_session(session)

    return TeachStartResponse(
        session_id=session.session_id,
        lesson_plan=lesson_plan,
        profile=profile,
    )


@router.post("/{session_id}/submit", response_model=TeachSubmitResponse)
def submit_photo(session_id: str, body: TeachSubmitRequest):
    """
    Submit a photo + live context for evaluation.
    Runs the full post-shot pipeline and returns SessionBlockResult.
    Updates and persists the student profile.
    """
    try:
        session = get_teaching_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Teaching session not found")

    if session.lesson_plan is None:
        raise HTTPException(status_code=400, detail="No active lesson plan — call /teach/start first")

    image = _decode_image(body.image_base64)
    live_ctx = _parse_live_context(body.live_context)

    result, updated_profile = complete_session_block(
        profile=session.profile,
        image=image,
        live_ctx=live_ctx,
        lesson_plan=session.lesson_plan,
        shot_intent=body.shot_intent,
        prev_report=session.last_report,
    )

    # Persist updated profile and update session
    save_profile(updated_profile)
    session.profile = updated_profile
    update_teaching_session(session)

    levels = updated_profile.skill_state.as_dict()

    return TeachSubmitResponse(
        feedback_text=result.feedback_text,
        recommended_action=result.recommended_action,
        reason=result.reason,
        skill_updated=result.skill_updated,
        milestone_reached=result.milestone_reached,
        current_milestone=updated_profile.milestone_state.current_milestone,
        updated_skill_levels=levels,
    )


@router.post("/{session_id}/next", response_model=TeachNextResponse)
def next_lesson(session_id: str):
    """
    Generate the next lesson plan (called after 'advance' or 'end_lesson').
    The planner automatically selects the next target skill.
    """
    try:
        session = get_teaching_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Teaching session not found")

    lesson_plan = plan_lesson(session.profile)
    session.lesson_plan = lesson_plan
    update_teaching_session(session)

    return TeachNextResponse(lesson_plan=lesson_plan)


@router.get("/{session_id}/profile", response_model=ProfileResponse)
def get_profile(session_id: str):
    """Get the current profile state for a teaching session."""
    try:
        session = get_teaching_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Teaching session not found")

    return _profile_response(session.profile)
