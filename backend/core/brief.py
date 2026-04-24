"""
Teaching brief builder.

Converts a UserProfile into a concise, narrative teaching brief that LLM agents
use as system context. Built deterministically — no LLM call required.

The brief is regenerated every time the profile is saved, so it is always
in sync with the student's current skill state and progress.

Public API:
    build_teaching_brief(profile) -> str
"""

from __future__ import annotations

from backend.models.profile import UserProfile
from backend.models.teaching import FALLBACK_ASSIGNMENTS, LEVEL_DESCRIPTIONS, SKILL_DEFINITIONS
from backend.models.session import TargetSkill
from backend.core.progression import select_target_skill, is_stuck_on_skill

# ── Style → emotional outcome ─────────────────────────────────────────────────

_STYLE_OUTCOME: dict[str, str] = {
    "Warm & Film":    "warm, nostalgic, timeless images with a film-like feel",
    "Clean & Bright": "fresh, minimal images with clear light and simple compositions",
    "Moody & Dark":   "atmospheric, emotionally intense images with dark tones and dramatic shadows",
    "Documentary":    "authentic, narrative-driven images that capture real moments",
    "Soft & Dreamy":  "gentle, romantic images with soft light and flowing compositions",
    "Gritty & Urban": "raw, energetic images with strong contrast and urban texture",
}

# ── Style + goal → single lead teaching principle ────────────────────────────

_LEAD_PRINCIPLE: dict[tuple[str, str], str] = {
    ("Warm & Film",    "social_media"):   "Connect every technique to the warmth and feel of the shot — the goal is an image that resonates immediately on screen.",
    ("Warm & Film",    "portfolio"):      "Build intentionality and consistency across shots — the student is developing a warm, timeless visual identity.",
    ("Warm & Film",    "skill_building"): "Explain why each technique produces the warm, nostalgic feeling the student is after.",
    ("Clean & Bright", "social_media"):   "Keep feedback results-oriented — clarity and brightness translate directly to scroll-stopping images.",
    ("Clean & Bright", "portfolio"):      "Encourage visual consistency and deliberate minimalism across every shot.",
    ("Clean & Bright", "skill_building"): "Explain how simplicity in light and composition creates the clean aesthetic.",
    ("Moody & Dark",   "social_media"):   "Connect technique to emotional impact — the student wants images that feel immediately powerful on screen.",
    ("Moody & Dark",   "portfolio"):      "Lead with emotional intent before technique — the student is building a dark, dramatic visual identity, not just learning rules.",
    ("Moody & Dark",   "skill_building"): "Explain how each technique serves mood and atmosphere — the student wants to understand the 'why' behind the darkness.",
    ("Documentary",    "social_media"):   "Focus on timing and authenticity — the student wants images that feel real and immediate.",
    ("Documentary",    "portfolio"):      "Encourage the student to develop a consistent perspective and point of view across their documentary work.",
    ("Documentary",    "skill_building"): "Explain how technical choices (light, framing) serve the story without disrupting the scene.",
    ("Soft & Dreamy",  "social_media"):   "Connect technique to the gentle, romantic feeling the student wants their audience to experience.",
    ("Soft & Dreamy",  "portfolio"):      "Build a consistent soft aesthetic — every shot should feel like it belongs to the same dream.",
    ("Soft & Dreamy",  "skill_building"): "Explain how light direction and composition create the softness and mood the student is after.",
    ("Gritty & Urban", "social_media"):   "Keep feedback energetic and practical — the student wants images with immediate visual impact.",
    ("Gritty & Urban", "portfolio"):      "Encourage the student to develop a raw, consistent urban voice across their body of work.",
    ("Gritty & Urban", "skill_building"): "Explain how contrast, texture, and framing build the gritty energy the student is chasing.",
}

_SUBJECT_NOTE: dict[str, str] = {
    "portrait": "The student photographs people — acknowledge the human element in every lesson. Connection and expression matter as much as technique. Guide them to direct their subject, not just react to them.",
    "scene":    "The student photographs scenes and environments — help them see compositions to enter and frame, not just capture. Patience and timing are as important as technique.",
    "object":   "The student photographs objects — encourage deliberate control. Every variable (angle, light, background) can be adjusted. Small changes in position have large visual impact.",
}

_DEVICE_NOTE: dict[str, str] = {
    "phone":  "Phone constraint: no manual controls. All guidance must work through positioning, timing, and light direction only — avoid references to aperture, ISO, or shutter speed.",
    "camera": "The student uses a dedicated camera — assignments can involve aperture, ISO, and shutter speed when directly relevant to the skill being taught.",
}

_GOAL_LABEL: dict[str, str] = {
    "social_media":   "create compelling content for social media",
    "portfolio":      "build a strong photography portfolio",
    "skill_building": "develop their photography skills",
}

_SUBJECT_LABEL: dict[str, str] = {
    "portrait": "portrait",
    "scene":    "scene and landscape",
    "object":   "product and object",
}


# ── Skill snapshot ────────────────────────────────────────────────────────────

_SKILLS: list[TargetSkill] = [
    "composition", "lighting", "subject_clarity",
    "pose_expression", "background_control",
]


def _skill_status(profile: UserProfile, skill: TargetSkill, active: TargetSkill) -> str:
    dim = profile.skill_state.get(skill)
    marker = "  ← active focus" if skill == active else ""
    if profile.is_diagnostic or len(dim.recent_attempts) == 0:
        return f"first session{marker}"
    if dim.is_stuck():
        return f"STUCK{marker}"
    if dim.should_advance():
        return f"ready to advance{marker}"
    return f"progressing{marker}"


def _format_snapshot(profile: UserProfile, active: TargetSkill) -> str:
    lines = []
    for skill in _SKILLS:
        defn = SKILL_DEFINITIONS[skill]
        label = skill.replace("_", " ").title()
        if not defn.is_active_for(profile.primary_subject):
            lines.append(f"  {label:22s} N/A")
            continue
        dim = profile.skill_state.get(skill)
        status = _skill_status(profile, skill, active)
        lines.append(f"  {label:22s} {dim.level}/5  {status}")
    return "\n".join(lines)


def _what_is_working(profile: UserProfile, active: TargetSkill) -> str:
    gains, near_advance = [], []
    for skill in _SKILLS:
        if skill == active:
            continue
        defn = SKILL_DEFINITIONS[skill]
        if not defn.is_active_for(profile.primary_subject):
            continue
        dim = profile.skill_state.get(skill)
        if dim.should_advance():
            near_advance.append(skill.replace("_", " "))
        elif "advance" in dim.recent_attempts:
            gains.append(skill.replace("_", " "))

    parts = []
    if near_advance:
        parts.append(f"{', '.join(near_advance).title()} {'is' if len(near_advance) == 1 else 'are'} close to advancing — use {'this' if len(near_advance) == 1 else 'these'} as a confidence builder when the student is discouraged.")
    if gains:
        parts.append(f"{', '.join(gains).title()} showing recent progress.")
    if not parts:
        if profile.is_diagnostic:
            return "No session data yet. Open with a low-stakes task. Acknowledge effort explicitly regardless of outcome — the goal right now is to make the student feel capable and curious."
        return "No clear gains yet. Name something specific the student did right in each attempt, even if the overall result missed the mark. Progress feels invisible at this stage — make it visible."
    return " ".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────

def build_teaching_brief(profile: UserProfile) -> str:
    """
    Build a concise, narrative teaching brief from a UserProfile.

    Returns a markdown string suitable for use as LLM system context.
    Deterministic — no LLM call required.
    """
    style = profile.style_preference.selected_style
    subject = profile.primary_subject
    goal = profile.primary_goal
    device = profile.device.type
    milestone = profile.milestone_state.current_milestone
    name = profile.name

    active_skill = select_target_skill(profile)
    stuck = is_stuck_on_skill(profile, active_skill)
    active_dim = profile.skill_state.get(active_skill)
    active_label = active_skill.replace("_", " ").title()
    active_desc = LEVEL_DESCRIPTIONS[active_skill][active_dim.level]

    # ── Section 1: Who they are ───────────────────────────────────────────────
    outcome = _STYLE_OUTCOME.get(style, "images that reflect their personal vision")
    identity = (
        f"{name} is learning photography to {_GOAL_LABEL[goal]}. "
        f"{name} shoots {_SUBJECT_LABEL[subject]} photography and wants to create {outcome}."
    )

    # ── Section 2: How to teach them ─────────────────────────────────────────
    lead = _LEAD_PRINCIPLE.get((style, goal), "Connect every technique back to the student's photographic intent.")
    subject_note = _SUBJECT_NOTE[subject]
    device_note = _DEVICE_NOTE[device]

    # ── Section 3: Current focus ──────────────────────────────────────────────
    is_first = profile.is_diagnostic or len(active_dim.recent_attempts) == 0

    if is_first:
        focus_status = "first session"
        focus_action = (
            f"This is {name}'s first attempt at this skill. Current level description: \"{active_desc}\".\n"
            f"**Instruction:** Give one simple, observable task. "
            f"The goal is to understand {name}'s current baseline, not to push progression yet."
        )
    elif stuck:
        focus_status = "STUCK"
        focus_action = (
            f"{name} has struggled with this skill 3 times consecutively.\n"
            f"**Instruction:** Use only this simplified assignment verbatim: \"{FALLBACK_ASSIGNMENTS[active_skill]}\". "
            f"Do not introduce new concepts — rebuild confidence first."
        )
    elif active_dim.should_advance():
        focus_status = "ready to advance"
        focus_action = (
            f"{name} is performing well here. Current level description: \"{active_desc}\".\n"
            f"**Instruction:** Give a slightly more demanding assignment — {name} is ready for the next level."
        )
    else:
        focus_status = "progressing"
        focus_action = (
            f"Current level description: \"{active_desc}\".\n"
            f"**Instruction:** Give one focused assignment on {active_label.lower()}. "
            f"Keep the concept explanation to 2–3 sentences calibrated to level {active_dim.level}."
        )

    # Next priority after active skill
    levels = profile.skill_state.as_dict()
    next_skills = [
        s for s in _SKILLS
        if s != active_skill and SKILL_DEFINITIONS[s].is_active_for(subject)
    ]
    next_skills.sort(key=lambda s: (profile.skill_state.get(s).level, s))
    next_priority = next_skills[0].replace("_", " ") if next_skills else "—"

    # ── Section 4: Skill snapshot ─────────────────────────────────────────────
    snapshot = _format_snapshot(profile, active_skill)

    # ── Section 5: What's working ─────────────────────────────────────────────
    working = _what_is_working(profile, active_skill)

    brief = f"""# Teaching Brief — {name}

## Who {name} is
{identity}

## How to teach {name}
{lead}

{subject_note}

{device_note}

## Current focus — {active_label} ({active_dim.level}/5) [{focus_status}]
{focus_action}
Next priority after this skill: {next_priority}.

## Skill snapshot
{snapshot}

## What's working
{working}
"""
    return brief.strip()
