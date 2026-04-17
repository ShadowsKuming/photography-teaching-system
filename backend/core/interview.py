"""
InterviewAgent — conversational onboarding agent.

Runs a short natural conversation to build a UserProfile.
No questionnaires — everything comes from dialogue.

Flow:
  chatting     → open conversation, collect goal / subject / device
  style_shown  → style grid has been presented, waiting for selection
  naming       → have enough context, collecting student name
  complete     → profile extracted and ready

Public API:
    agent = InterviewAgent()
    turn  = agent.chat(user_message)      → InterviewTurn
    turn  = agent.select_style(styles)    → InterviewTurn
    profile = agent.extract_profile()     → UserProfile
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from backend.core.llm import call_text, call_text_json
from backend.models.profile import (
    Device,
    MilestoneState,
    SkillDimension,
    SkillState,
    StylePreference,
    UserProfile,
)

InterviewState = Literal["chatting", "style_shown", "naming", "complete"]

_STYLE_NAMES = [
    "Warm & Film",
    "Clean & Bright",
    "Moody & Dark",
    "Documentary",
    "Soft & Dreamy",
    "Gritty & Urban",
]

_SYSTEM = """You are a warm, curious photography teacher meeting a new student for the first time.
Your goal is to understand their photographic intent through natural conversation — not a questionnaire.

In the first 3 turns, gently explore:
- What draws them to photography (their goal or feeling)
- What they like to photograph (subject or scene)
- What device they shoot with (phone or camera)

Rules:
- Ask only ONE question per turn
- Keep replies short (2-4 sentences max)
- Be encouraging and curious, not clinical
- Do not use bullet points or lists
- Do not mention skill levels or scores

After 3 turns, you will be asked to present a style grid. Follow the instruction when given.
After style selection, collect the student's name and wrap up warmly."""

_STYLE_PROMPT = """The student has been chatting with you for a few turns.
It's time to show them a visual style grid. Write a short, natural transition (1-2 sentences)
inviting them to look at the style options and pick what feels closest to their vision.
Don't explain the styles — just invite them to choose."""

_NAME_PROMPT_AFTER_STYLE = """The student selected these visual styles: {styles}.
Respond warmly to their style choice (1 sentence), then ask for their first name so you can personalise their lessons."""

_WRAP_PROMPT = """The student's name is {name}.
Write a warm 2-sentence closing: acknowledge their name, and tell them you're ready to start their first lesson together."""

_EXTRACT_PROMPT = """Based on this conversation, extract the student's profile.

Conversation:
{conversation}

Selected styles: {styles}
Student name: {name}

Return a JSON object with exactly these fields:
{{
  "primary_goal": "social_media" | "portfolio" | "skill_building",
  "primary_subject": "portrait" | "scene" | "object",
  "device_type": "phone" | "camera",
  "device_constraints": [],
  "initial_composition": 1,
  "initial_lighting": 1,
  "initial_subject_clarity": 1,
  "initial_pose_expression": 1,
  "initial_background_control": 1
}}

For primary_goal:
  social_media    — sharing, building audience, everyday capture
  portfolio       — serious craft, quality over quantity
  skill_building  — learning and improving deliberately

For primary_subject:
  portrait — people, faces, expressions (includes cosplay, street portraits)
  scene    — landscapes, environments, travel, architecture
  object   — products, food, still life, macro

For device_constraints, include any of:
  "low_light_limitations"   — if they mentioned shooting in dim conditions on phone
  "low_dynamic_range"       — if they mentioned blown highlights or crushed shadows

For initial skill levels (1-3 only, never higher from interview alone):
  1 — no evidence of experience or clearly a beginner
  2 — some experience mentioned or implied
  3 — confident, experienced language used

Reply with JSON only."""


@dataclass
class InterviewTurn:
    reply: str
    show_style_grid: bool = False
    is_complete: bool = False
    state: InterviewState = "chatting"


@dataclass
class InterviewAgent:
    state: InterviewState = "chatting"
    history: list[dict] = field(default_factory=list)
    style_selection: list[str] = field(default_factory=list)
    student_name: str = ""
    _turn_count: int = 0

    def __post_init__(self):
        # Seed with system prompt
        self.history = [{"role": "system", "content": _SYSTEM}]
        # Generate opening message
        opening = call_text(self.history + [{
            "role": "user",
            "content": "[The student has just opened the app for the first time. Greet them warmly and ask your first question.]"
        }])
        self.history.append({"role": "assistant", "content": opening})
        self._opening = opening

    @property
    def opening_message(self) -> str:
        return self._opening

    def chat(self, user_message: str) -> InterviewTurn:
        """Process a student message. Returns the agent's reply and state flags."""
        if self.state == "complete":
            return InterviewTurn(reply="Your profile is ready!", is_complete=True, state="complete")

        self.history.append({"role": "user", "content": user_message})
        self._turn_count += 1

        # After 3 turns of chatting, transition to style grid
        if self.state == "chatting" and self._turn_count >= 3:
            transition = call_text(
                self.history + [{"role": "user", "content": _STYLE_PROMPT}]
            )
            self.history.append({"role": "assistant", "content": transition})
            self.state = "style_shown"
            return InterviewTurn(reply=transition, show_style_grid=True, state="style_shown")

        # Normal conversation turn
        reply = call_text(self.history)
        self.history.append({"role": "assistant", "content": reply})

        return InterviewTurn(reply=reply, state=self.state)

    def select_style(self, styles: list[str]) -> InterviewTurn:
        """Called when the student picks from the style grid."""
        valid = [s for s in styles if s in _STYLE_NAMES]
        self.style_selection = valid if valid else [_STYLE_NAMES[0]]

        prompt = _NAME_PROMPT_AFTER_STYLE.format(styles=", ".join(self.style_selection))
        reply = call_text(self.history + [{"role": "user", "content": prompt}])

        self.history.append({"role": "user", "content": f"[Selected styles: {', '.join(self.style_selection)}]"})
        self.history.append({"role": "assistant", "content": reply})
        self.state = "naming"

        return InterviewTurn(reply=reply, state="naming")

    def submit_name(self, name: str) -> InterviewTurn:
        """Called when the student provides their name. Wraps up the interview."""
        self.student_name = name.strip()

        wrap = call_text(
            self.history + [{"role": "user", "content": _WRAP_PROMPT.format(name=self.student_name)}]
        )
        self.history.append({"role": "user", "content": self.student_name})
        self.history.append({"role": "assistant", "content": wrap})
        self.state = "complete"

        return InterviewTurn(reply=wrap, is_complete=True, state="complete")

    def extract_profile(self) -> UserProfile:
        """
        Extract a UserProfile from the conversation.
        Called after state == 'complete'.
        Raises ValueError if called before the interview is complete.
        """
        if self.state != "complete":
            raise ValueError("Cannot extract profile before interview is complete")

        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in self.history
            if m["role"] in ("user", "assistant")
        )

        fallback = {
            "primary_goal": "skill_building",
            "primary_subject": "portrait",
            "device_type": "phone",
            "device_constraints": [],
            "initial_composition": 1,
            "initial_lighting": 1,
            "initial_subject_clarity": 1,
            "initial_pose_expression": 1,
            "initial_background_control": 1,
        }

        data = call_text_json(
            messages=[{"role": "user", "content": _EXTRACT_PROMPT.format(
                conversation=conversation_text,
                styles=", ".join(self.style_selection),
                name=self.student_name,
            )}],
            fallback=fallback,
        )

        def _clamp(val: int) -> int:
            return max(1, min(3, int(val)))

        skill_state = SkillState(
            composition=       SkillDimension(level=_clamp(data.get("initial_composition", 1))),
            lighting=          SkillDimension(level=_clamp(data.get("initial_lighting", 1))),
            subject_clarity=   SkillDimension(level=_clamp(data.get("initial_subject_clarity", 1))),
            pose_expression=   SkillDimension(level=_clamp(data.get("initial_pose_expression", 1))),
            background_control=SkillDimension(level=_clamp(data.get("initial_background_control", 1))),
        )

        valid_goals    = {"social_media", "portfolio", "skill_building"}
        valid_subjects = {"portrait", "scene", "object"}
        valid_devices  = {"phone", "camera"}
        valid_constraints = {"low_light_limitations", "low_dynamic_range"}

        raw_goal    = data.get("primary_goal", "skill_building")
        raw_subject = data.get("primary_subject", "portrait")
        raw_device  = data.get("device_type", "phone")
        raw_constraints = data.get("device_constraints", [])

        selected = self.style_selection[0] if self.style_selection else "Clean & Bright"

        return UserProfile(
            name=self.student_name,
            primary_goal=raw_goal if raw_goal in valid_goals else "skill_building",
            primary_subject=raw_subject if raw_subject in valid_subjects else "portrait",
            style_preference=StylePreference(selected_style=selected),
            device=Device(
                type=raw_device if raw_device in valid_devices else "phone",
                constraints=[c for c in raw_constraints if c in valid_constraints],
            ),
            skill_state=skill_state,
            milestone_state=MilestoneState(),
            is_diagnostic=True,
        )
