"""
Teaching domain models.

SkillDefinition     — applies_to rules + plain-language level descriptions
SKILL_DEFINITIONS   — canonical registry, used by planner and progression
FALLBACK_ASSIGNMENTS — one simplified task per skill for the stuck protocol
MILESTONE_THRESHOLDS — deterministic milestone computation from skill levels
DimensionObservation — one axis of a photo analysis
EvaluationReport    — full photo analysis from the evaluator
GapAnalysis         — TeacherAgent's internal reasoning about what to address
FeedbackMessage     — structured feedback before it becomes prose
LessonPlan          — planner output: what to teach and what to assign
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from .profile import MilestoneLevel, PrimarySubject
from .session import TargetSkill, DimensionStatus


# ── Skill definitions ─────────────────────────────────────────────────────────

AppliesTo = Literal["all", "portrait"]

LEVEL_DESCRIPTIONS: dict[TargetSkill, dict[int, str]] = {
    "composition": {
        1: "Subject placement is inconsistent; framing often feels unintentional",
        2: "Can achieve basic framing but with noticeable issues (e.g. too much empty space, tilt)",
        3: "Maintains stable framing and uses simple composition rules (e.g. centering or thirds)",
        4: "Applies composition intentionally to guide viewer attention",
        5: "Uses composition expressively to reinforce intent",
    },
    "lighting": {
        1: "Frequently produces poorly lit or unusable images",
        2: "Recognises basic lighting issues but struggles to correct them",
        3: "Can adjust position or angle to achieve acceptable lighting",
        4: "Uses light direction and intensity intentionally",
        5: "Uses lighting creatively to shape mood",
    },
    "subject_clarity": {
        1: "Subject is often unclear or blends into background",
        2: "Subject is visible but not clearly emphasised",
        3: "Subject is clearly identifiable and separated from background",
        4: "Uses framing and depth to highlight subject",
        5: "Strong visual hierarchy centred on subject",
    },
    "pose_expression": {
        1: "Poses appear stiff or unintentional",
        2: "Basic poses but lack alignment with intent",
        3: "Poses are natural and readable",
        4: "Poses reinforce mood or character",
        5: "Strong expressive control of pose and gesture",
    },
    "background_control": {
        1: "Background is cluttered or distracting",
        2: "Some awareness but inconsistent control",
        3: "Maintains relatively clean background",
        4: "Selects or adjusts background to support subject",
        5: "Uses background composition intentionally",
    },
}


class SkillDefinition(BaseModel):
    name: TargetSkill
    applies_to: AppliesTo
    level_descriptions: dict[int, str]

    def description_for(self, level: int) -> str:
        return self.level_descriptions.get(level, "")

    def is_active_for(self, subject: PrimarySubject) -> bool:
        return self.applies_to == "all" or subject == "portrait"


SKILL_DEFINITIONS: dict[TargetSkill, SkillDefinition] = {
    skill: SkillDefinition(
        name=skill,
        applies_to="portrait" if skill == "pose_expression" else "all",
        level_descriptions=LEVEL_DESCRIPTIONS[skill],
    )
    for skill in LEVEL_DESCRIPTIONS
}


# ── Fallback assignments (stuck protocol) ─────────────────────────────────────
# One simplified task per skill. Used when a student is stuck (>= 3 retries).

FALLBACK_ASSIGNMENTS: dict[TargetSkill, str] = {
    "composition":        "Centre the subject clearly in the frame.",
    "lighting":           "Place the subject in even, front-facing natural light.",
    "subject_clarity":    "Make the subject clearly separated from the background.",
    "pose_expression":    "Use one simple, natural standing pose.",
    "background_control": "Remove or step away from any distracting objects behind the subject.",
}


# ── Milestone thresholds ──────────────────────────────────────────────────────

def compute_milestone(levels: dict[str, int]) -> MilestoneLevel:
    """
    Deterministic milestone from a flat {skill: level} dict.

    Advanced     : all 5 dimensions >= 4
    Intermediate : all 5 >= 3  AND  composition + lighting >= 4
    Developing   : composition + lighting + subject_clarity all >= 3
    Beginner     : everything else
    """
    core_three = (
        levels.get("composition", 1),
        levels.get("lighting", 1),
        levels.get("subject_clarity", 1),
    )
    all_five = list(levels.values())

    if all(v >= 4 for v in all_five):
        return "advanced"
    if all(v >= 3 for v in all_five) and levels.get("composition", 1) >= 4 and levels.get("lighting", 1) >= 4:
        return "intermediate"
    if all(v >= 3 for v in core_three):
        return "developing"
    return "beginner"


# Expose thresholds as a plain dict for documentation / tests
MILESTONE_THRESHOLDS: dict[MilestoneLevel, str] = {
    "beginner":     "Starting state",
    "developing":   "composition + lighting + subject_clarity all >= 3",
    "intermediate": "All 5 dimensions >= 3 AND composition + lighting >= 4",
    "advanced":     "All 5 dimensions >= 4",
}


# ── Evaluation models ─────────────────────────────────────────────────────────

class DimensionObservation(BaseModel):
    """
    Objective observations for one analysis dimension.
    No scores, no teaching language — the evaluator is a pure observer.
    """
    dimension: TargetSkill
    observations: str                   # factual description of what the photo shows
    status: DimensionStatus             # derived assessment for downstream use
    vs_previous: str | None = None      # delta vs previous submission if available


class EvaluationReport(BaseModel):
    """
    Full photo analysis from AssignmentEvaluationAssistant.
    Stateless — produced fresh for each submitted photo.
    """
    composition:        DimensionObservation
    lighting:           DimensionObservation
    subject_clarity:    DimensionObservation
    pose_expression:    DimensionObservation
    background_control: DimensionObservation
    focus_dimension:    TargetSkill      # which dimension was primary focus this session

    def get(self, skill: TargetSkill) -> DimensionObservation:
        return getattr(self, skill)

    def focus_status(self) -> DimensionStatus:
        return self.get(self.focus_dimension).status


# ── Gap analysis ──────────────────────────────────────────────────────────────

GapType = Literal["skill", "vision", "mixed"]


class GapAnalysis(BaseModel):
    """
    TeacherAgent's internal reasoning about what kind of gap to address.

    skill  — student understood what to do but execution fell short
    vision — student didn't see the opportunity (pre-visualisation)
    mixed  — both; vision addressed first, then technique
    """
    gap_type: GapType
    what_works: str
    primary_gap: str
    reasoning: str
    intent_alignment: str               # how this connects to student's photographic intent


# ── Structured feedback ───────────────────────────────────────────────────────

class FeedbackMessage(BaseModel):
    """
    Structured feedback components before the TeacherAgent converts them
    to natural prose. Keeping structure explicit ensures content quality
    is validated before naturalising tone.
    """
    acknowledgment: str     # what the student did well or tried
    focus: str              # the one thing to address
    principle: str          # why it matters (not just what to do)
    intent_connection: str  # how it relates to the student's photographic intent
    exercise: str           # what to try next


# ── Lesson plan ───────────────────────────────────────────────────────────────

class LessonPlan(BaseModel):
    """
    LessonPlanningAssistant output.
    Tells the TeacherAgent what concept to teach and what task to assign.
    """
    target_skill: TargetSkill
    concept: str            # what concept to explain
    assignment: str         # what the student should try to capture
    rationale: str          # why this skill / concept was selected now
    is_fallback: bool = False   # True if stuck protocol triggered fallback assignment
