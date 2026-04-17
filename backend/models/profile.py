"""
UserProfile and all related data structures.

This is the central contract that flows from the Interview into every
downstream component (TeacherAgent, Planner, Progression, LiveLayer).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, Field, model_validator


# ── Enums (plain Literals so values are self-documenting) ─────────────────────

PrimaryGoal    = Literal["social_media", "portfolio", "skill_building"]
PrimarySubject = Literal["portrait", "scene", "object"]
MilestoneLevel = Literal["beginner", "developing", "intermediate", "advanced"]
DeviceType     = Literal["phone", "camera"]
DeviceConstraint = Literal["low_light_limitations", "low_dynamic_range"]
AttemptResult  = Literal["advance", "guided_retry", "retry"]

StyleName = Literal[
    "Warm & Film",
    "Clean & Bright",
    "Moody & Dark",
    "Documentary",
    "Soft & Dreamy",
    "Gritty & Urban",
]

StyleConfidence = Literal["low", "medium", "high"]


# ── Sub-models ────────────────────────────────────────────────────────────────

class SkillDimension(BaseModel):
    """
    One skill axis. level 1-5 with plain-language meaning per level.
    recent_attempts stores the last 3 results to support the 2/3 advancement
    rule and the stuck protocol (>= 3 consecutive retries).
    """
    level: Annotated[int, Field(ge=1, le=5)] = 1
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    recent_attempts: list[AttemptResult] = Field(default_factory=list, max_length=3)

    def record_attempt(self, result: AttemptResult) -> "SkillDimension":
        """Return a new SkillDimension with the attempt appended (max 3 kept)."""
        updated = list(self.recent_attempts) + [result]
        return self.model_copy(update={
            "recent_attempts": updated[-3:],
            "last_updated": datetime.utcnow(),
        })

    def should_advance(self) -> bool:
        """2 advances in the last 3 attempts."""
        return self.recent_attempts.count("advance") >= 2

    def is_stuck(self) -> bool:
        """3 consecutive retries (guided or plain) without an advance."""
        if len(self.recent_attempts) < 3:
            return False
        return all(r != "advance" for r in self.recent_attempts[-3:])


class SkillState(BaseModel):
    composition:        SkillDimension = Field(default_factory=SkillDimension)
    lighting:           SkillDimension = Field(default_factory=SkillDimension)
    subject_clarity:    SkillDimension = Field(default_factory=SkillDimension)
    pose_expression:    SkillDimension = Field(default_factory=SkillDimension)
    background_control: SkillDimension = Field(default_factory=SkillDimension)

    def get(self, skill: str) -> SkillDimension:
        return getattr(self, skill)

    def set(self, skill: str, dimension: SkillDimension) -> "SkillState":
        return self.model_copy(update={skill: dimension})

    def as_dict(self) -> dict[str, int]:
        """Flat {skill: level} view — convenient for milestone checks."""
        return {
            "composition":        self.composition.level,
            "lighting":           self.lighting.level,
            "subject_clarity":    self.subject_clarity.level,
            "pose_expression":    self.pose_expression.level,
            "background_control": self.background_control.level,
        }


class StylePreference(BaseModel):
    selected_style: StyleName
    confidence: StyleConfidence = "medium"
    source: Literal["style_grid"] = "style_grid"
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class Device(BaseModel):
    type: DeviceType
    constraints: list[DeviceConstraint] = Field(default_factory=list)


class MilestoneState(BaseModel):
    current_milestone: MilestoneLevel = "beginner"
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ── Root contract ─────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    """
    Central learner contract.

    Stable fields  : primary_goal, style_preference, primary_subject, device
    Dynamic fields : skill_state, milestone_state  (updated after each session)

    is_diagnostic is True until the first real session block completes.
    During diagnostic mode the stuck protocol and 2/3 advancement rule
    are suppressed — skill levels come from interview estimates only.
    """
    name: str
    primary_goal: PrimaryGoal
    style_preference: StylePreference
    primary_subject: PrimarySubject
    device: Device
    skill_state: SkillState = Field(default_factory=SkillState)
    milestone_state: MilestoneState = Field(default_factory=MilestoneState)
    is_diagnostic: bool = True          # flipped to False after first real session

    @model_validator(mode="after")
    def _pose_only_for_portrait(self) -> "UserProfile":
        """
        pose_expression is only meaningful for portrait subjects.
        If the subject is not portrait we cap the level at 1 so the
        target-skill selector never picks it.
        """
        if self.primary_subject != "portrait":
            locked = self.skill_state.pose_expression.model_copy(
                update={"level": 1}
            )
            self.skill_state = self.skill_state.set("pose_expression", locked)
        return self
