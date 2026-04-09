"""
teaching/evaluator.py
---------------------
AssignmentEvaluationAssistant

Analyzes a submitted photograph and returns structured observations.
No scores. No teaching language. No judgement.
The Teacher interprets — this assistant only observes.

Supports two backends:
  - "openai"  : GPT-4o vision (recommended for quality)
  - "qwen"    : Qwen2.5-VL local (no API cost)
"""

from __future__ import annotations

import base64
import json
import os
import re
from io import BytesIO
from typing import Optional

from dotenv import load_dotenv
from PIL import Image

from teaching.models import DimensionObservation, EvaluationReport

load_dotenv()

# ------------------------------------------------------------------ #
#  Prompts                                                            #
# ------------------------------------------------------------------ #

_SYSTEM = """\
You are a visual analysis assistant for a photography teaching system.
Your only job is to describe what is present in a photograph with precision and objectivity.

You must NEVER use:
  - teaching language: "you should", "try to", "consider", "improve", "better to"
  - quality judgements: "good", "bad", "weak", "strong", "poor", "excellent"
  - numerical scores of any kind

You ONLY describe what you observe:
  "the light source is directional from the upper left"
  "the subject occupies the right third of the frame"
  "the background is out of focus with warm circular highlights"

Be precise, specific, and factual."""

_ANALYSIS_PROMPT = """\
Analyze this photograph across five visual dimensions.
{intent_context}
{focus_context}
{prev_context}

For each dimension, write 2-4 sentences of factual observation.
Go deeper on the focus dimension — it was the one being actively practiced.

Dimensions to cover:
1. light          — quality, direction, hardness, source, shadows
2. composition    — framing, subject placement, depth, negative space, layers
3. color          — palette, temperature, contrast, saturation, tonal range
4. subject_clarity — subject definition, separation from background, sharpness
5. moment_storytelling — what the image conveys, what is happening, the feel

{prev_instruction}

Return ONLY valid JSON:
{{
  "light": {{
    "observation": "...",
    "is_focus": true or false
  }},
  "composition": {{
    "observation": "...",
    "is_focus": true or false
  }},
  "color": {{
    "observation": "...",
    "is_focus": true or false
  }},
  "subject_clarity": {{
    "observation": "...",
    "is_focus": true or false
  }},
  "moment_storytelling": {{
    "observation": "...",
    "is_focus": true or false
  }},
  "summary": "one paragraph factual description of the image overall",
  "vs_previous": "one sentence factual comparison with the previous submission, or null"
}}"""


def _build_prompt(
    shot_intent:     Optional[str],
    focus_dim:       str,
    prev_report:     Optional[EvaluationReport],
) -> str:
    intent_context = (
        f'The photographer described their intent as: "{shot_intent}"'
        if shot_intent else
        "No shot-level intent was provided."
    )
    focus_context = (
        f'The dimension being actively practiced this session is: "{focus_dim}". '
        f'Go into more detail on this dimension than the others.'
    )
    if prev_report:
        prev_context = (
            f'Previous submission summary: "{prev_report.summary}"\n'
            f'Previous focus observation: '
            f'"{prev_report.focus_observation().observation if prev_report.focus_observation() else "N/A"}"'
        )
        prev_instruction = (
            'In the "vs_previous" field, describe one factual difference in the '
            f'"{focus_dim}" dimension compared to the previous submission.'
        )
    else:
        prev_context     = "This is the first submission — no previous submission to compare."
        prev_instruction = 'Set "vs_previous" to null.'

    return _ANALYSIS_PROMPT.format(
        intent_context   = intent_context,
        focus_context    = focus_context,
        prev_context     = prev_context,
        prev_instruction = prev_instruction,
    )


def _parse_report(raw: str, focus_dim: str) -> EvaluationReport:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    match   = re.search(r"\{.*\}", cleaned, re.DOTALL)
    data    = json.loads(match.group()) if match else {}

    dims = []
    for key in ("light", "composition", "color", "subject_clarity", "moment_storytelling"):
        entry = data.get(key, {})
        dims.append(DimensionObservation(
            dimension   = key,
            observation = entry.get("observation", "No observation available."),
            is_focus    = (key == focus_dim),
        ))

    return EvaluationReport(
        dimensions  = dims,
        summary     = data.get("summary", ""),
        vs_previous = data.get("vs_previous") or None,
    )


# ------------------------------------------------------------------ #
#  OpenAI backend                                                     #
# ------------------------------------------------------------------ #

def _image_to_base64(image: Image.Image) -> str:
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _evaluate_openai(
    image:       Image.Image,
    prompt_text: str,
    focus_dim:   str,
) -> EvaluationReport:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    b64 = _image_to_base64(image)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": [
                    {
                        "type":      "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                    {"type": "text", "text": prompt_text},
                ],
            },
        ],
        max_tokens=800,
        temperature=0.1,
    )
    raw = response.choices[0].message.content
    return _parse_report(raw, focus_dim)


# ------------------------------------------------------------------ #
#  Qwen backend                                                       #
# ------------------------------------------------------------------ #

_qwen_model     = None
_qwen_processor = None


def _load_qwen():
    global _qwen_model, _qwen_processor
    if _qwen_model is not None:
        return
    import torch
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
    from qwen_vl_utils import process_vision_info

    model_id = "Qwen/Qwen2.5-VL-3B-Instruct"
    _qwen_processor = AutoProcessor.from_pretrained(model_id)
    _qwen_model     = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_id, torch_dtype=torch.float16, device_map="auto"
    )


def _evaluate_qwen(
    image:       Image.Image,
    prompt_text: str,
    focus_dim:   str,
) -> EvaluationReport:
    import torch
    from qwen_vl_utils import process_vision_info

    _load_qwen()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text",  "text":  _SYSTEM + "\n\n" + prompt_text},
            ],
        }
    ]
    text = _qwen_processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = _qwen_processor(
        text=[text], images=image_inputs, videos=video_inputs,
        padding=True, return_tensors="pt",
    ).to(_qwen_model.device)

    with torch.no_grad():
        out = _qwen_model.generate(**inputs, max_new_tokens=800, temperature=0.1)
    raw = _qwen_processor.batch_decode(
        out[:, inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )[0]
    return _parse_report(raw, focus_dim)


# ------------------------------------------------------------------ #
#  Public interface                                                   #
# ------------------------------------------------------------------ #

class AssignmentEvaluationAssistant:
    """
    Analyzes a submitted photo and returns structured observations.
    Stateless — call it like a function.
    """

    def __init__(self, provider: str = "openai"):
        assert provider in ("openai", "qwen"), f"Unknown provider: {provider}"
        self.provider = provider

    def __call__(
        self,
        image:       Image.Image,
        shot_intent: Optional[str]          = None,
        prev_report: Optional[EvaluationReport] = None,
        focus_dim:   str                    = "light",
    ) -> EvaluationReport:
        prompt = _build_prompt(shot_intent, focus_dim, prev_report)
        if self.provider == "openai":
            return _evaluate_openai(image, prompt, focus_dim)
        return _evaluate_qwen(image, prompt, focus_dim)
