"""
Thin LLM abstraction layer.

All LLM calls in the system go through here. This is the only place
that imports openai or google.genai directly, so swapping providers
only requires changes in this file.

Public API:
    call_text(messages)           → str
    call_vision(image, prompt)    → str
    parse_json(text)              → dict   (robust, handles markdown fences)
    call_text_json(messages)      → dict   (call_text + parse_json + retry)
"""

from __future__ import annotations

import base64
import json
import logging
import re
from io import BytesIO
from typing import Any

from PIL import Image

from backend.config import settings

logger = logging.getLogger(__name__)


# ── JSON extraction ───────────────────────────────────────────────────────────

def parse_json(text: str) -> dict[str, Any]:
    """
    Extract a JSON object from LLM output.
    Handles markdown fences (```json ... ```) and bare JSON objects.
    Raises ValueError if no valid JSON is found.
    """
    # Strip markdown fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        return json.loads(fenced.group(1).strip())

    # Find the outermost JSON object
    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        return json.loads(brace.group(0))

    raise ValueError(f"No JSON found in LLM output: {text[:300]}")


# ── Image encoding ────────────────────────────────────────────────────────────

def _encode_image(image: Image.Image) -> str:
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


# ── OpenAI calls ──────────────────────────────────────────────────────────────

def _openai_text(messages: list[dict], as_json: bool = False) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    kwargs: dict[str, Any] = {
        "model": settings.text_model,
        "messages": messages,
    }
    if as_json:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def _openai_vision(image: Image.Image, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    b64 = _encode_image(image)
    resp = client.chat.completions.create(
        model=settings.vision_model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                    "detail": "high",
                }},
            ],
        }],
    )
    return resp.choices[0].message.content or ""


# ── Gemini calls ──────────────────────────────────────────────────────────────

def _gemini_text(messages: list[dict], as_json: bool = False) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)

    # Convert OpenAI-style messages to Gemini contents
    contents = []
    system_text = ""
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        else:
            contents.append(m["content"])

    config_kwargs: dict[str, Any] = {}
    if as_json:
        config_kwargs["response_mime_type"] = "application/json"
    if system_text:
        config_kwargs["system_instruction"] = system_text

    resp = client.models.generate_content(
        model=settings.text_model,
        contents="\n\n".join(contents),
        config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
    )
    return resp.text or ""


# ── Public API ────────────────────────────────────────────────────────────────

def call_text(messages: list[dict]) -> str:
    """Send a chat conversation to the configured text LLM, return raw string."""
    if settings.text_llm_provider == "openai":
        return _openai_text(messages)
    return _gemini_text(messages)


def call_vision(image: Image.Image, prompt: str) -> str:
    """Send an image + prompt to the configured vision LLM, return raw string."""
    if settings.vision_llm_provider == "openai":
        return _openai_vision(image, prompt)
    raise NotImplementedError("Only openai vision is supported in v1")


def call_text_json(messages: list[dict], fallback: dict | None = None) -> dict[str, Any]:
    """
    Call the text LLM expecting a JSON response.
    Retries once with an explicit reminder if the first response is not valid JSON.
    Returns fallback dict on repeated failure (or raises if no fallback given).
    """
    for attempt in range(2):
        try:
            if settings.text_llm_provider == "openai":
                raw = _openai_text(messages, as_json=True)
            else:
                raw = _gemini_text(messages, as_json=True)
            return parse_json(raw)
        except (ValueError, Exception) as exc:
            logger.warning("JSON parse failed (attempt %d): %s", attempt + 1, exc)
            if attempt == 0:
                # Append a correction nudge and retry
                messages = messages + [{
                    "role": "user",
                    "content": "Your response was not valid JSON. Reply with only a JSON object, no markdown.",
                }]

    if fallback is not None:
        logger.error("Returning fallback after 2 failed JSON attempts")
        return fallback
    raise ValueError("LLM did not return valid JSON after 2 attempts")


def call_vision_json(image: Image.Image, prompt: str, fallback: dict | None = None) -> dict[str, Any]:
    """Call the vision LLM expecting JSON output."""
    for attempt in range(2):
        try:
            raw = call_vision(image, prompt)
            return parse_json(raw)
        except (ValueError, Exception) as exc:
            logger.warning("Vision JSON parse failed (attempt %d): %s", attempt + 1, exc)
            if attempt == 0:
                prompt = prompt + "\n\nIMPORTANT: Reply with only a valid JSON object. No markdown, no explanation."

    if fallback is not None:
        logger.error("Returning vision fallback after 2 failed attempts")
        return fallback
    raise ValueError("Vision LLM did not return valid JSON after 2 attempts")
