"""
LessonPlanningAssistant — stateless lesson planner.

Given a student profile and selected target skill, returns a LessonPlan
with a plain-language concept explanation and a concrete shooting assignment.

Stateless: no session memory. All context comes from UserProfile.
"""

from __future__ import annotations

from backend.models.profile import UserProfile
from backend.models.session import TargetSkill
from backend.models.teaching import (
    FALLBACK_ASSIGNMENTS,
    SKILL_DEFINITIONS,
    LessonPlan,
)
from backend.core.llm import call_text_json
from backend.core.progression import is_stuck_on_skill, select_target_skill

_SYSTEM = """You are an expert photography teacher designing a single lesson for a student.
Your output must be a JSON object. Be concise and practical.
Adapt your language to the student's level (1=absolute beginner, 5=advanced).
Connect everything to the student's photographic intent and style."""

_PROMPT_TEMPLATE = """Design a short lesson for this student.

Student profile:
- Name: {name}
- Goal: {goal}
- Subject type: {subject}
- Style preference: {style}
- Device: {device}
- Current level for {skill}: {level}/5 — "{level_description}"
- Photographic intent context: {intent_context}

Focus skill for this session: {skill}
{fallback_note}

Return a JSON object with exactly these fields:
{{
  "concept": "<2-3 sentence explanation of the concept to focus on, calibrated to level {level}>",
  "assignment": "<one concrete, actionable shooting task the student can do right now>"
}}

The concept should explain WHY this matters for their photography, not just what to do.
The assignment should be specific enough that the student knows exactly what to shoot.
Reply with the JSON object only.
"""


def plan_lesson(
    profile: UserProfile,
    target_skill: TargetSkill | None = None,
) -> LessonPlan:
    """
    Generate a lesson plan for the student's next session block.

    Args:
        profile      : current UserProfile
        target_skill : override skill selection (uses select_target_skill if None)

    Returns:
        LessonPlan with concept, assignment, target_skill, rationale
    """
    if target_skill is None:
        target_skill = select_target_skill(profile)

    is_fallback = is_stuck_on_skill(profile, target_skill)
    dim = profile.skill_state.get(target_skill)
    level_desc = SKILL_DEFINITIONS[target_skill].description_for(dim.level)

    fallback_note = ""
    if is_fallback:
        assignment_override = FALLBACK_ASSIGNMENTS[target_skill]
        fallback_note = (
            f"NOTE: The student has struggled with this skill. "
            f"Use this simplified assignment exactly: \"{assignment_override}\""
        )

    intent_context = (
        f"{profile.style_preference.selected_style} style, "
        f"{profile.primary_subject} photography, "
        f"goal: {profile.primary_goal}"
    )

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _PROMPT_TEMPLATE.format(
            name=profile.name,
            goal=profile.primary_goal,
            subject=profile.primary_subject,
            style=profile.style_preference.selected_style,
            device=profile.device.type,
            skill=target_skill,
            level=dim.level,
            level_description=level_desc,
            intent_context=intent_context,
            fallback_note=fallback_note,
        )},
    ]

    fallback_data = {
        "concept": f"Focus on {target_skill.replace('_', ' ')} in your photography.",
        "assignment": FALLBACK_ASSIGNMENTS[target_skill],
    }

    data = call_text_json(messages, fallback=fallback_data)

    return LessonPlan(
        target_skill=target_skill,
        concept=data.get("concept", fallback_data["concept"]),
        assignment=data.get("assignment", fallback_data["assignment"]),
        rationale=f"Level {dim.level}/5 on {target_skill} — selected as lowest active skill.",
        is_fallback=is_fallback,
    )
