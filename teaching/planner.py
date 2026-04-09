"""
teaching/planner.py
-------------------
LessonPlanningAssistant

Recommends what to teach next and what assignment to give.
Called only at two moments:
  1. Session start (no current plan)
  2. Teacher explicitly decides to advance the teaching direction

The Teacher makes the final call — this is a recommendation, not an instruction.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import List, Optional

from dotenv import load_dotenv

from teaching.models import LessonPlan, SkillObservation
from interview.profile import UserProfile

load_dotenv()

# ------------------------------------------------------------------ #
#  Prompt                                                             #
# ------------------------------------------------------------------ #

_PLANNER_PROMPT = """\
You are a lesson planning assistant for a photography teacher.
Your job is to recommend what concept to teach next and what assignment to give.

You have access to:
1. The student's profile — their intent, what they want to express, their device
2. Their skill observations — what signals have been seen across sessions
3. Their session history — what has already been taught
4. The current plan — what was being taught (null if this is the first session)

Student profile:
  photographic_intent : {photographic_intent}
  subject_world       : {subject_world}
  teaching_direction  : {teaching_direction}
  device              : {device}
  inferred_level      : {inferred_level}
  visual_references   : {visual_references}

Skill observations (most recent first):
{skill_observations}

Sessions so far: {session_n}
Current plan: {current_plan}

---

Rules:
- If this is session 1 (no current plan): derive the first concept directly from teaching_direction
- If current plan exists: assess whether the focus dimension has shown "strong" signals
  in the last 2 sessions. If yes, advance. If not, stay on the same dimension with a new angle.
- Pick ONE concept. One assignment. Keep it concrete and specific.
- The assignment must be achievable with the student's device ({device}).
- Connect the concept to their photographic_intent — not generic technique.
- Do NOT recommend something already covered in recent sessions.

Return ONLY valid JSON:
{{
  "concept": "the principle to teach — one sentence",
  "assignment": "concrete task — what to go out and shoot, with specific constraints",
  "focus_dimension": "light | composition | color | subject_clarity | moment_storytelling",
  "rationale": "why this concept now, given their intent and current signals — 2 sentences"
}}"""


def _format_observations(observations: List[SkillObservation]) -> str:
    if not observations:
        return "  (none yet — first session)"
    recent = sorted(observations, key=lambda o: o.session_n, reverse=True)[:6]
    lines  = [
        f"  session {o.session_n} | {o.dimension:20s} | {o.signal:12s} | {o.note}"
        for o in recent
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------ #
#  LLM call                                                           #
# ------------------------------------------------------------------ #

def _call_llm(prompt: str, provider: str) -> str:
    if provider == "openai":
        from openai import OpenAI
        client   = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model    = "gpt-4o-mini",
            messages = [{"role": "user", "content": prompt}],
            max_tokens  = 300,
            temperature = 0.2,
        )
        return response.choices[0].message.content

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp   = client.models.generate_content(
        model    = "gemini-2.5-flash",
        contents = [types.Content(
            role  = "user",
            parts = [types.Part(text=prompt)],
        )],
        config = types.GenerateContentConfig(
            temperature      = 0.2,
            max_output_tokens= 300,
        ),
    )
    return resp.text.strip()


# ------------------------------------------------------------------ #
#  Public interface                                                   #
# ------------------------------------------------------------------ #

class LessonPlanningAssistant:
    """
    Recommends concept + assignment based on profile and observation history.
    Stateless — call it like a function.
    """

    def __init__(self, provider: str = "openai"):
        assert provider in ("openai", "gemini")
        self.provider = provider

    def __call__(
        self,
        profile:          UserProfile,
        skill_obs:        List[SkillObservation],
        session_n:        int,
        current_plan:     Optional[LessonPlan] = None,
    ) -> LessonPlan:
        current_plan_str = (
            f"concept='{current_plan.concept}', "
            f"focus_dimension='{current_plan.focus_dimension}'"
            if current_plan else "null (first session)"
        )

        prompt = _PLANNER_PROMPT.format(
            photographic_intent = profile.photographic_intent or "(not yet known)",
            subject_world       = profile.subject_world       or "(not yet known)",
            teaching_direction  = profile.teaching_direction  or "(not yet known)",
            device              = profile.device              or "unknown",
            inferred_level      = profile.inferred_level,
            visual_references   = profile.visual_references   or "(none)",
            skill_observations  = _format_observations(skill_obs),
            session_n           = session_n,
            current_plan        = current_plan_str,
        )

        raw = _call_llm(prompt, self.provider)

        try:
            cleaned = re.sub(r"```(?:json)?", "", raw).strip()
            match   = re.search(r"\{.*\}", cleaned, re.DOTALL)
            data    = json.loads(match.group()) if match else {}
        except (json.JSONDecodeError, AttributeError):
            data = {}

        return LessonPlan(
            concept         = data.get("concept",         "Understanding light quality"),
            assignment      = data.get("assignment",      "Photograph the same subject in two different light conditions."),
            focus_dimension = data.get("focus_dimension", "light"),
            rationale       = data.get("rationale",       ""),
        )
