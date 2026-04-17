"""
Request and response schemas for the API layer.

Kept separate from domain models (backend/models/) so the API surface
can evolve independently from the internal contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.profile import (
    DeviceConstraint,
    DeviceType,
    MilestoneLevel,
    PrimaryGoal,
    PrimarySubject,
    StyleName,
    UserProfile,
)
from backend.models.session import RecommendedAction, TargetSkill
from backend.models.teaching import LessonPlan


# ── Interview ─────────────────────────────────────────────────────────────────

class InterviewStartResponse(BaseModel):
    session_id: str
    opening_message: str


class InterviewChatRequest(BaseModel):
    message: str


class InterviewChatResponse(BaseModel):
    reply: str
    show_style_grid: bool = False
    is_complete: bool = False
    state: str


class InterviewStyleRequest(BaseModel):
    selected_styles: list[StyleName]


class InterviewStyleResponse(BaseModel):
    reply: str
    state: str


class InterviewNameRequest(BaseModel):
    name: str


class InterviewNameResponse(BaseModel):
    reply: str
    is_complete: bool


class InterviewCompleteResponse(BaseModel):
    profile: UserProfile


# ── Teaching ──────────────────────────────────────────────────────────────────

class TeachStartRequest(BaseModel):
    name: str  # load existing profile by name


class TeachStartResponse(BaseModel):
    session_id: str
    lesson_plan: LessonPlan
    profile: UserProfile


class LiveIssueSchema(BaseModel):
    issue_type: str
    first_detected: str   # ISO timestamp string from frontend
    last_detected: str
    severity: str


class LiveEventSchema(BaseModel):
    type: str
    detail: str
    timestamp: str
    linked_issue: str | None = None


class LiveCaptureSchema(BaseModel):
    timestamp: str


class LiveFinalStateSchema(BaseModel):
    composition_status: str = "poor"
    lighting_status: str = "poor"
    subject_clarity_status: str = "poor"
    pose_expression_status: str = "not_applicable"
    background_control_status: str = "poor"


class LiveContextSchema(BaseModel):
    """Loose schema for incoming live context from frontend."""
    target_skill: TargetSkill
    observed_issues: list[LiveIssueSchema] = Field(default_factory=list)
    events: list[LiveEventSchema] = Field(default_factory=list)
    final_capture_state: LiveFinalStateSchema = Field(default_factory=LiveFinalStateSchema)
    captures: list[LiveCaptureSchema] = Field(default_factory=list)


class TeachSubmitRequest(BaseModel):
    image_base64: str          # base64-encoded JPEG
    live_context: LiveContextSchema
    shot_intent: str | None = None


class TeachSubmitResponse(BaseModel):
    feedback_text: str
    recommended_action: RecommendedAction
    reason: str
    skill_updated: bool
    milestone_reached: bool
    current_milestone: MilestoneLevel
    updated_skill_levels: dict[str, int]


class TeachNextResponse(BaseModel):
    lesson_plan: LessonPlan


class SkillLevelOut(BaseModel):
    level: int
    recent_attempts: list[str]


class ProfileResponse(BaseModel):
    name: str
    primary_goal: PrimaryGoal
    primary_subject: PrimarySubject
    style: StyleName
    milestone: MilestoneLevel
    skill_state: dict[str, SkillLevelOut]
    device_type: DeviceType
    device_constraints: list[DeviceConstraint]
    is_diagnostic: bool
