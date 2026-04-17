"""
Progression — the deterministic teaching loop core.

All functions here are pure (no LLM, no I/O). They take typed contracts
and return typed contracts, which makes them fully unit-testable in isolation.

Public API:
    select_target_skill(profile)              → TargetSkill
    decide_attempt_result(live_ctx, report)   → AttemptResult
    apply_progression(profile, skill, result) → (UserProfile, bool, bool)
        returns (updated_profile, skill_level_changed, milestone_changed)
"""

from __future__ import annotations

from datetime import datetime

from backend.models.profile import (
    AttemptResult,
    MilestoneLevel,
    SkillDimension,
    UserProfile,
)
from backend.models.session import (
    LiveSessionContext,
    RecommendedAction,
    TargetSkill,
)
from backend.models.teaching import (
    EvaluationReport,
    SKILL_DEFINITIONS,
    compute_milestone,
)


# ── Target skill selection ─────────────────────────────────────────────────────

# Core dimensions are preferred when levels are tied
_CORE_DIMENSIONS: list[TargetSkill] = ["composition", "lighting", "subject_clarity"]
_ALL_DIMENSIONS:  list[TargetSkill] = [
    "composition", "lighting", "subject_clarity",
    "pose_expression", "background_control",
]


def select_target_skill(profile: UserProfile) -> TargetSkill:
    """
    Choose the skill to focus on this session.

    Priority order (first criterion wins):
      1. Filter out dimensions not applicable to this subject type
      2. Lowest current level
      3. Tiebreak: least recently practised (oldest last_updated)
      4. Tiebreak: core dimensions before conditional ones
    """
    active = [
        skill for skill in _ALL_DIMENSIONS
        if SKILL_DEFINITIONS[skill].is_active_for(profile.primary_subject)
    ]

    skill_state = profile.skill_state

    def sort_key(skill: TargetSkill) -> tuple:
        dim = skill_state.get(skill)
        is_core = 0 if skill in _CORE_DIMENSIONS else 1
        # oldest last_updated = smallest timestamp = practised least recently
        return (dim.level, dim.last_updated.timestamp(), is_core)

    return min(active, key=sort_key)


# ── Advance / retry decision ──────────────────────────────────────────────────

def decide_attempt_result(
    live_ctx: LiveSessionContext,
    report: EvaluationReport,
) -> AttemptResult:
    """
    Deterministic advance/retry decision from session evidence.

    Advance       : focus dimension status is strong AND
                    at least one issue resolved (or no issues detected)
    Guided retry  : status is acceptable AND student responded to prompts
    Retry         : status is poor OR student did not respond to prompts
    """
    status = report.focus_status()

    if status == "strong":
        resolved = live_ctx.issues_resolved_at_capture()
        no_issues = len(live_ctx.observed_issues) == 0
        if resolved or no_issues:
            return "advance"

    if status == "acceptable" and live_ctx.student_responded_to_prompts():
        return "guided_retry"

    return "retry"


def decide_recommended_action(
    result: AttemptResult,
    dimension: SkillDimension,
    is_diagnostic: bool,
) -> RecommendedAction:
    """
    Map an AttemptResult + current dimension state to a UI-facing action.

    During diagnostic mode, advancement rules are suppressed —
    always recommend continuing to build baseline data.
    """
    if is_diagnostic:
        return "advance"  # diagnostic session always moves forward

    if result == "advance":
        return "advance"

    if dimension.is_stuck():
        # 3 consecutive non-advances: recommend end or rotate skill
        return "advance"  # rotate to next skill rather than infinite retry

    if result == "guided_retry":
        return "guided_retry"

    return "retry"


# ── Progression update ────────────────────────────────────────────────────────

def apply_progression(
    profile: UserProfile,
    target_skill: TargetSkill,
    result: AttemptResult,
) -> tuple[UserProfile, bool, bool]:
    """
    Record the attempt result and update skill level + milestone if warranted.

    Returns:
        updated_profile     : UserProfile with new skill_state + milestone_state
        skill_level_changed : True if the dimension level was incremented
        milestone_changed   : True if the student crossed a milestone threshold

    Rules:
        - During diagnostic mode: record the attempt but do not increment levels
        - Level increments only when should_advance() is True (2/3 rule)
        - Milestone is recomputed after every update
    """
    dim = profile.skill_state.get(target_skill)
    dim = dim.record_attempt(result)

    skill_level_changed = False

    if not profile.is_diagnostic and dim.should_advance() and dim.level < 5:
        dim = dim.model_copy(update={
            "level": dim.level + 1,
            "last_updated": datetime.utcnow(),
        })
        skill_level_changed = True

    new_skill_state = profile.skill_state.set(target_skill, dim)

    # Recompute milestone
    old_milestone = profile.milestone_state.current_milestone
    new_milestone = compute_milestone(new_skill_state.as_dict())
    milestone_changed = new_milestone != old_milestone

    from backend.models.profile import MilestoneState
    new_milestone_state = (
        MilestoneState(current_milestone=new_milestone)
        if milestone_changed
        else profile.milestone_state
    )

    # After first real session, flip diagnostic flag
    is_diagnostic = False if profile.is_diagnostic else profile.is_diagnostic

    updated = profile.model_copy(update={
        "skill_state":     new_skill_state,
        "milestone_state": new_milestone_state,
        "is_diagnostic":   is_diagnostic,
    })

    return updated, skill_level_changed, milestone_changed


# ── Stuck protocol ────────────────────────────────────────────────────────────

def is_stuck_on_skill(profile: UserProfile, target_skill: TargetSkill) -> bool:
    """
    True if the student has had 3 consecutive non-advance attempts on this skill.
    Used by the planner to decide whether to apply a fallback assignment.
    """
    return profile.skill_state.get(target_skill).is_stuck()
