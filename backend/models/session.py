"""
LiveSessionContext  — one composition attempt in the live camera stage.
SessionBlockResult  — TeacherAgent output to the UI at end of each session block.

These are the interface contracts between:
  live camera layer  →  LiveSessionContext  →  TeacherAgent
  TeacherAgent       →  SessionBlockResult  →  UI
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

TargetSkill = Literal[
    "composition",
    "lighting",
    "subject_clarity",
    "pose_expression",
    "background_control",
]

IssueType = Literal[
    "off_center_subject",
    "tilted_frame",
    "backlit_subject",
    "cluttered_background",
    "unclear_pose",
]

Severity = Literal["low", "medium", "high"]

EventType = Literal["prompt_given", "user_adjustment"]

EventDetail = Literal[
    # prompts
    "reposition_subject",
    "straighten_frame",
    "move_to_better_light",
    "simplify_background",
    "adjust_pose",
    # adjustments
    "reframed",
    "changed_angle",
    "moved_closer",
    "moved_subject",
    "changed_pose",
]

DimensionStatus = Literal["poor", "acceptable", "strong", "not_applicable"]

RecommendedAction = Literal["retry", "guided_retry", "advance", "end_lesson"]


# ── Sub-models ────────────────────────────────────────────────────────────────

class ObservedIssue(BaseModel):
    """
    A compositional problem detected by the live layer.
    Resolved status is derived: if last_detected < captures[-1].timestamp
    the issue disappeared before the final shot was taken.
    """
    issue_type: IssueType
    first_detected: datetime
    last_detected: datetime
    severity: Severity

    def resolved_before(self, capture_time: datetime) -> bool:
        return self.last_detected < capture_time


class SessionEvent(BaseModel):
    """
    A single event in the composition timeline.
    linked_issue connects a prompt or adjustment back to the issue it addresses,
    so the TeacherAgent can tell which prompts were responded to.
    """
    type: EventType
    detail: EventDetail
    timestamp: datetime
    linked_issue: IssueType | None = None


class CaptureRecord(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FinalCaptureState(BaseModel):
    """
    Compact snapshot of all dimensions at the moment the student submitted.
    pose_expression uses not_applicable when subject is not portrait.
    """
    composition_status:        DimensionStatus = "poor"
    lighting_status:           DimensionStatus = "poor"
    subject_clarity_status:    DimensionStatus = "poor"
    pose_expression_status:    DimensionStatus = "not_applicable"
    background_control_status: DimensionStatus = "poor"

    def get(self, skill: str) -> DimensionStatus:
        return getattr(self, f"{skill}_status")


# ── Root contracts ────────────────────────────────────────────────────────────

class LiveSessionContext(BaseModel):
    """
    Everything the live camera layer observed during one composition attempt.
    Passed to the TeacherAgent alongside the submitted photo so it can reason
    about process (how the student composed) not just outcome (final image).
    """
    target_skill: TargetSkill
    observed_issues: list[ObservedIssue] = Field(default_factory=list)
    events: list[SessionEvent] = Field(default_factory=list)
    final_capture_state: FinalCaptureState = Field(default_factory=FinalCaptureState)
    captures: list[CaptureRecord] = Field(default_factory=list)

    def prompts_given(self) -> list[SessionEvent]:
        return [e for e in self.events if e.type == "prompt_given"]

    def adjustments_made(self) -> list[SessionEvent]:
        return [e for e in self.events if e.type == "user_adjustment"]

    def student_responded_to_prompts(self) -> bool:
        """True if at least one adjustment follows at least one prompt."""
        if not self.prompts_given():
            return False
        return len(self.adjustments_made()) > 0

    def issues_resolved_at_capture(self) -> list[IssueType]:
        """Issues that disappeared before the final capture."""
        if not self.captures:
            return []
        last_capture = self.captures[-1].timestamp
        return [
            i.issue_type for i in self.observed_issues
            if i.resolved_before(last_capture)
        ]

    def issues_persisted_at_capture(self) -> list[IssueType]:
        """Issues that were still present at the moment of final capture."""
        if not self.captures:
            return [i.issue_type for i in self.observed_issues]
        last_capture = self.captures[-1].timestamp
        return [
            i.issue_type for i in self.observed_issues
            if not i.resolved_before(last_capture)
        ]


class SessionBlockResult(BaseModel):
    """
    TeacherAgent output at end of each session block.
    The UI maps recommended_action directly to the primary button label:
      retry / guided_retry  →  "Try again"
      advance               →  "Next challenge"
      end_lesson            →  "End lesson"
    """
    feedback_text: str
    recommended_action: RecommendedAction
    reason: str                         # one sentence shown to student
    skill_updated: bool = False
    milestone_reached: bool = False
    is_diagnostic: bool = False         # True only for the first session block
