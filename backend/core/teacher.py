"""
TeacherAgent — session block orchestrator.

Coordinates the full post-shot pipeline:
  1. Evaluate submitted photo (evaluator)
  2. Decide advance / retry outcome (progression)
  3. Analyse the gap (skill vs vision vs mixed)
  4. Generate structured feedback
  5. Convert structured feedback to natural prose
  6. Update student profile (progression)
  7. Return SessionBlockResult + updated profile

Public API:
    complete_session_block(profile, image, live_ctx, lesson_plan, shot_intent)
        → (SessionBlockResult, updated_profile)
"""

from __future__ import annotations

from PIL import Image

from backend.models.profile import UserProfile
from backend.models.session import LiveSessionContext, SessionBlockResult
from backend.models.teaching import (
    EvaluationReport,
    FeedbackMessage,
    GapAnalysis,
    LessonPlan,
)
from backend.core import evaluator as eval_module
from backend.core.llm import call_text_json, call_text
from backend.core.progression import (
    apply_progression,
    decide_attempt_result,
    decide_recommended_action,
    is_stuck_on_skill,
)

# ── Gap analysis ──────────────────────────────────────────────────────────────

_GAP_SYSTEM = """You are an expert photography teacher analysing a student's learning gap.
Classify the primary gap as one of:
  skill  — the student understood the goal but execution fell short (technique, timing, settings)
  vision — the student didn't see the opportunity before shooting (pre-visualisation)
  mixed  — both; address vision first, then technique
Be specific. Reference what you observe in the photo analysis."""

_GAP_PROMPT = """Student profile:
- Style: {style}, Subject: {subject}, Goal: {goal}
- Current level for {skill}: {level}/5

Photo analysis for focus dimension ({skill}):
  Observations: {observations}
  Status: {status}

Live session context:
  Issues detected: {issues_detected}
  Student responded to prompts: {responded}
  Issues resolved before capture: {resolved}
  Issues still present at capture: {persisted}

Assignment given: {assignment}

Based on this, identify the gap. Return JSON:
{{
  "gap_type": "skill|vision|mixed",
  "what_works": "<what the student got right>",
  "primary_gap": "<the single most important thing to address>",
  "reasoning": "<why you classified it this way>",
  "intent_alignment": "<how this gap connects to their {style} {subject} photography goal>"
}}"""

# ── Structured feedback ───────────────────────────────────────────────────────

_FEEDBACK_SYSTEM = """You are an expert photography teacher giving targeted feedback.
Your feedback must:
- Address ONE thing only
- Connect to the student's photographic intent
- Explain the principle (why), not just what to do
- Be warm but direct
Return a structured JSON, not prose."""

_FEEDBACK_PROMPT = """Student: {name} | Style: {style} | Subject: {subject} | Level: {level}/5

Gap analysis:
  Type: {gap_type}
  What works: {what_works}
  Primary gap: {primary_gap}
  Intent alignment: {intent_alignment}

Return feedback as JSON:
{{
  "acknowledgment": "<1-2 sentences: what the student tried or achieved>",
  "focus": "<the one thing to improve, stated clearly>",
  "principle": "<the underlying principle that explains why this matters>",
  "intent_connection": "<1 sentence connecting this to their {style} {subject} photography>",
  "exercise": "<a concrete thing to try in their next shot>"
}}"""

# ── Prose conversion ──────────────────────────────────────────────────────────

_PROSE_SYSTEM = """You are a supportive photography teacher writing feedback to a student.
Convert the structured feedback below into 3-4 natural, encouraging sentences.
Keep it conversational. Do not use lists or headers. Do not add new content."""

_PROSE_PROMPT = """Convert this structured feedback to natural prose:

Acknowledgment: {acknowledgment}
Focus: {focus}
Principle: {principle}
Intent connection: {intent_connection}
Exercise: {exercise}

Write 3-4 sentences. Start with the acknowledgment. End with the exercise."""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _analyse_gap(
    profile: UserProfile,
    report: EvaluationReport,
    live_ctx: LiveSessionContext,
    lesson_plan: LessonPlan,
) -> GapAnalysis:
    skill = lesson_plan.target_skill
    focus_obs = report.get(skill)
    dim = profile.skill_state.get(skill)

    messages = [
        {"role": "system", "content": _GAP_SYSTEM},
        {"role": "user", "content": _GAP_PROMPT.format(
            style=profile.style_preference.selected_style,
            subject=profile.primary_subject,
            goal=profile.primary_goal,
            skill=skill,
            level=dim.level,
            observations=focus_obs.observations,
            status=focus_obs.status,
            issues_detected=[i.issue_type for i in live_ctx.observed_issues],
            responded=live_ctx.student_responded_to_prompts(),
            resolved=live_ctx.issues_resolved_at_capture(),
            persisted=live_ctx.issues_persisted_at_capture(),
            assignment=lesson_plan.assignment,
        )},
    ]

    fallback = {
        "gap_type": "skill",
        "what_works": "The student made a genuine attempt.",
        "primary_gap": f"Needs more practice with {skill.replace('_', ' ')}.",
        "reasoning": "Based on photo analysis.",
        "intent_alignment": f"This will help with {profile.style_preference.selected_style} photography.",
    }

    data = call_text_json(messages, fallback=fallback)

    valid_gap_types = {"skill", "vision", "mixed"}
    gap_type = data.get("gap_type", "skill")
    if gap_type not in valid_gap_types:
        gap_type = "skill"

    return GapAnalysis(
        gap_type=gap_type,
        what_works=data.get("what_works", fallback["what_works"]),
        primary_gap=data.get("primary_gap", fallback["primary_gap"]),
        reasoning=data.get("reasoning", fallback["reasoning"]),
        intent_alignment=data.get("intent_alignment", fallback["intent_alignment"]),
    )


def _generate_feedback(
    profile: UserProfile,
    gap: GapAnalysis,
    lesson_plan: LessonPlan,
) -> FeedbackMessage:
    dim = profile.skill_state.get(lesson_plan.target_skill)

    messages = [
        {"role": "system", "content": _FEEDBACK_SYSTEM},
        {"role": "user", "content": _FEEDBACK_PROMPT.format(
            name=profile.name,
            style=profile.style_preference.selected_style,
            subject=profile.primary_subject,
            level=dim.level,
            gap_type=gap.gap_type,
            what_works=gap.what_works,
            primary_gap=gap.primary_gap,
            intent_alignment=gap.intent_alignment,
        )},
    ]

    fallback = {
        "acknowledgment": "Good effort on this attempt.",
        "focus": gap.primary_gap,
        "principle": "Every improvement in technique serves your creative vision.",
        "intent_connection": gap.intent_alignment,
        "exercise": "Try the same shot again with this in mind.",
    }

    data = call_text_json(messages, fallback=fallback)

    return FeedbackMessage(
        acknowledgment=data.get("acknowledgment", fallback["acknowledgment"]),
        focus=data.get("focus", fallback["focus"]),
        principle=data.get("principle", fallback["principle"]),
        intent_connection=data.get("intent_connection", fallback["intent_connection"]),
        exercise=data.get("exercise", fallback["exercise"]),
    )


def _to_prose(feedback: FeedbackMessage) -> str:
    messages = [
        {"role": "system", "content": _PROSE_SYSTEM},
        {"role": "user", "content": _PROSE_PROMPT.format(
            acknowledgment=feedback.acknowledgment,
            focus=feedback.focus,
            principle=feedback.principle,
            intent_connection=feedback.intent_connection,
            exercise=feedback.exercise,
        )},
    ]
    return call_text(messages).strip()


# ── Public API ────────────────────────────────────────────────────────────────

def complete_session_block(
    profile: UserProfile,
    image: Image.Image,
    live_ctx: LiveSessionContext,
    lesson_plan: LessonPlan,
    shot_intent: str | None = None,
    prev_report: EvaluationReport | None = None,
) -> tuple[SessionBlockResult, UserProfile]:
    """
    Run the full post-shot pipeline for one session block.

    Args:
        profile      : current UserProfile (will be updated)
        image        : submitted PIL image
        live_ctx     : LiveSessionContext from the camera layer
        lesson_plan  : the plan that was shown to the student this session
        shot_intent  : what the student said they were trying to achieve
        prev_report  : EvaluationReport from the previous session (for delta)

    Returns:
        (SessionBlockResult, updated_profile)
    """
    target_skill = lesson_plan.target_skill

    # Step 1 — Evaluate the photo
    report = eval_module.evaluate(
        image=image,
        focus_dim=target_skill,
        shot_intent=shot_intent,
        prev_report=prev_report,
    )

    # Step 2 — Decide outcome (deterministic)
    attempt_result = decide_attempt_result(live_ctx, report)

    # Step 3 — Gap analysis (LLM)
    gap = _analyse_gap(profile, report, live_ctx, lesson_plan)

    # Step 4 — Structured feedback (LLM)
    feedback_struct = _generate_feedback(profile, gap, lesson_plan)

    # Step 5 — Convert to prose (LLM)
    feedback_prose = _to_prose(feedback_struct)

    # Step 6 — Update profile (deterministic)
    updated_profile, skill_level_changed, milestone_changed = apply_progression(
        profile, target_skill, attempt_result
    )

    # Step 7 — Recommended action for UI
    dim_after = updated_profile.skill_state.get(target_skill)
    recommended = decide_recommended_action(
        result=attempt_result,
        dimension=dim_after,
        is_diagnostic=profile.is_diagnostic,
    )

    reason_map = {
        "advance":      "Great work — ready to move on.",
        "guided_retry": "You're making progress — one more focused attempt.",
        "retry":        "Let's try again with fresh eyes.",
        "end_lesson":   "You've done excellent work today.",
    }

    return SessionBlockResult(
        feedback_text=feedback_prose,
        recommended_action=recommended,
        reason=reason_map[recommended],
        skill_updated=skill_level_changed,
        milestone_reached=milestone_changed,
        is_diagnostic=profile.is_diagnostic,
    ), updated_profile
