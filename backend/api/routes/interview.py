"""
Interview routes.

POST /interview/start          → create session, return opening message
POST /interview/{id}/chat      → send message, get reply
POST /interview/{id}/style     → submit style grid selection
POST /interview/{id}/name      → submit student name, complete interview
POST /interview/{id}/complete  → extract and return UserProfile
DELETE /interview/{id}         → clean up session
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import (
    InterviewChatRequest,
    InterviewChatResponse,
    InterviewCompleteResponse,
    InterviewNameRequest,
    InterviewNameResponse,
    InterviewStartResponse,
    InterviewStyleRequest,
    InterviewStyleResponse,
)
from backend.api.sessions import (
    create_interview_session,
    delete_interview_session,
    get_interview_session,
)
from backend.core.storage import save_profile

router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/start", response_model=InterviewStartResponse)
def start_interview():
    """Create a new interview session and return the opening message."""
    session = create_interview_session()
    return InterviewStartResponse(
        session_id=session.session_id,
        opening_message=session.agent.opening_message,
    )


@router.post("/{session_id}/chat", response_model=InterviewChatResponse)
def chat(session_id: str, body: InterviewChatRequest):
    """Send a student message and get the agent's reply."""
    try:
        session = get_interview_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Interview session not found")

    turn = session.agent.chat(body.message)
    return InterviewChatResponse(
        reply=turn.reply,
        show_style_grid=turn.show_style_grid,
        is_complete=turn.is_complete,
        state=turn.state,
    )


@router.post("/{session_id}/style", response_model=InterviewStyleResponse)
def submit_style(session_id: str, body: InterviewStyleRequest):
    """Submit the student's style grid selection."""
    try:
        session = get_interview_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if session.agent.state not in ("style_shown", "naming"):
        raise HTTPException(status_code=400, detail="Style grid has not been shown yet")

    turn = session.agent.select_style(body.selected_styles)
    return InterviewStyleResponse(reply=turn.reply, state=turn.state)


@router.post("/{session_id}/name", response_model=InterviewNameResponse)
def submit_name(session_id: str, body: InterviewNameRequest):
    """Submit the student's name to complete the interview conversation."""
    try:
        session = get_interview_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if session.agent.state != "naming":
        raise HTTPException(status_code=400, detail="Not ready for name yet")

    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Name cannot be empty")

    turn = session.agent.submit_name(body.name)
    return InterviewNameResponse(reply=turn.reply, is_complete=turn.is_complete)


@router.post("/{session_id}/complete", response_model=InterviewCompleteResponse)
def complete_interview(session_id: str):
    """
    Extract UserProfile from the completed interview and persist it.
    Returns the profile. The frontend should then call POST /teach/start.
    """
    try:
        session = get_interview_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if session.agent.state != "complete":
        raise HTTPException(
            status_code=400,
            detail=f"Interview not complete yet (state: {session.agent.state})",
        )

    profile = session.agent.extract_profile()
    save_profile(profile)

    return InterviewCompleteResponse(profile=profile)


@router.delete("/{session_id}")
def delete_session(session_id: str):
    """Clean up an interview session from memory."""
    delete_interview_session(session_id)
    return {"deleted": session_id}
