"""
AssignmentEvaluationAssistant — stateless photo analyser.

Takes a PIL image and returns an EvaluationReport with objective
observations across all five skill dimensions. No scores, no teaching
language — the evaluator is a pure observer.

The TeacherAgent uses the report to:
  - determine final_capture_state for each dimension
  - perform gap analysis
  - generate targeted feedback
"""

from __future__ import annotations

from PIL import Image

from backend.models.session import DimensionStatus, TargetSkill
from backend.models.teaching import DimensionObservation, EvaluationReport
from backend.core.llm import call_vision_json

_SYSTEM = """You are an objective photo analysis assistant.
Your job is to describe what you observe in a photograph across five dimensions.
Rules:
- Be factual and specific. Describe only what is visible.
- Do not score, praise, or critique. No teaching language.
- Keep each observation to 2-3 concise sentences.
- For status, choose exactly one of: poor, acceptable, strong.
  poor       = significant issues that undermine the dimension
  acceptable = works but has noticeable room for improvement
  strong     = clearly executed, serves the image well
- If pose_expression is not applicable (no person in frame), set status to not_applicable and observations to "N/A".
"""

_PROMPT_TEMPLATE = """{system}

Analyse this photograph and return a JSON object with this exact structure:
{{
  "composition": {{
    "observations": "<what you see>",
    "status": "poor|acceptable|strong",
    "vs_previous": "<one sentence on change vs previous, or null>"
  }},
  "lighting": {{
    "observations": "<what you see>",
    "status": "poor|acceptable|strong",
    "vs_previous": null
  }},
  "subject_clarity": {{
    "observations": "<what you see>",
    "status": "poor|acceptable|strong",
    "vs_previous": null
  }},
  "pose_expression": {{
    "observations": "<what you see, or N/A>",
    "status": "poor|acceptable|strong|not_applicable",
    "vs_previous": null
  }},
  "background_control": {{
    "observations": "<what you see>",
    "status": "poor|acceptable|strong",
    "vs_previous": null
  }}
}}

Focus dimension for this session: {focus_dim}
Give slightly more detail on the focus dimension than the others.

{shot_intent_section}
{prev_section}

Reply with the JSON object only.
"""

_DIMENSION_KEYS: list[TargetSkill] = [
    "composition", "lighting", "subject_clarity",
    "pose_expression", "background_control",
]

_FALLBACK_STATUS: DimensionStatus = "acceptable"


def _build_prompt(
    focus_dim: TargetSkill,
    shot_intent: str | None,
    prev_report: EvaluationReport | None,
) -> str:
    shot_section = (
        f"Student's stated intent for this shot: {shot_intent}"
        if shot_intent else ""
    )
    prev_section = ""
    if prev_report:
        prev_lines = []
        for key in _DIMENSION_KEYS:
            obs = prev_report.get(key)
            prev_lines.append(f"  {key}: {obs.observations}")
        prev_section = (
            "Previous submission observations (for vs_previous comparison):\n"
            + "\n".join(prev_lines)
        )
    return _PROMPT_TEMPLATE.format(
        system=_SYSTEM,
        focus_dim=focus_dim,
        shot_intent_section=shot_section,
        prev_section=prev_section,
    )


def _parse_dimension(
    key: TargetSkill,
    data: dict,
    prev_report: EvaluationReport | None,
) -> DimensionObservation:
    raw_status = data.get("status", _FALLBACK_STATUS)
    # Normalise unexpected values to fallback
    valid = {"poor", "acceptable", "strong", "not_applicable"}
    status: DimensionStatus = raw_status if raw_status in valid else _FALLBACK_STATUS

    vs_previous = data.get("vs_previous")
    # Inherit vs_previous from previous report if LLM left it null
    if vs_previous is None and prev_report:
        prev_obs = prev_report.get(key)
        vs_previous = f"Previously: {prev_obs.observations}"

    return DimensionObservation(
        dimension=key,
        observations=data.get("observations", "No observation available."),
        status=status,
        vs_previous=vs_previous,
    )


def _fallback_report(focus_dim: TargetSkill) -> EvaluationReport:
    """Safe default when the LLM call fails entirely."""
    def _obs(key: TargetSkill) -> DimensionObservation:
        return DimensionObservation(
            dimension=key,
            observations="Evaluation unavailable.",
            status="acceptable",
        )
    return EvaluationReport(
        composition=_obs("composition"),
        lighting=_obs("lighting"),
        subject_clarity=_obs("subject_clarity"),
        pose_expression=DimensionObservation(
            dimension="pose_expression",
            observations="N/A",
            status="not_applicable",
        ),
        background_control=_obs("background_control"),
        focus_dimension=focus_dim,
    )


def evaluate(
    image: Image.Image,
    focus_dim: TargetSkill,
    shot_intent: str | None = None,
    prev_report: EvaluationReport | None = None,
) -> EvaluationReport:
    """
    Analyse a submitted photo and return an EvaluationReport.

    Args:
        image       : the submitted PIL image
        focus_dim   : which skill dimension is the primary focus this session
        shot_intent : what the student said they were trying to achieve
        prev_report : previous session's report for delta comparison

    Returns:
        EvaluationReport with observations for all five dimensions
    """
    prompt = _build_prompt(focus_dim, shot_intent, prev_report)
    fallback_raw = {
        key: {"observations": "Evaluation unavailable.", "status": "acceptable", "vs_previous": None}
        for key in _DIMENSION_KEYS
    }
    fallback_raw["pose_expression"] = {"observations": "N/A", "status": "not_applicable", "vs_previous": None}

    data = call_vision_json(image, prompt, fallback=fallback_raw)

    dims = {
        key: _parse_dimension(key, data.get(key, {}), prev_report)
        for key in _DIMENSION_KEYS
    }

    return EvaluationReport(**dims, focus_dimension=focus_dim)
