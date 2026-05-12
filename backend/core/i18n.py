"""
Language helpers shared across API and LLM prompts.
"""

from __future__ import annotations

from typing import Literal, cast

from backend.models.session import RecommendedAction

LanguageCode = Literal["en-GB", "pt-BR"]

DEFAULT_LANGUAGE: LanguageCode = "en-GB"

_SUPPORTED = {"en-GB", "pt-BR"}

_LANGUAGE_NAMES: dict[LanguageCode, str] = {
    "en-GB": "English (UK)",
    "pt-BR": "Brazilian Portuguese (pt-BR)",
}

_REASON_BY_ACTION: dict[LanguageCode, dict[RecommendedAction, str]] = {
    "en-GB": {
        "advance": "Great work - ready to move on.",
        "guided_retry": "You're making progress - one more focused attempt.",
        "retry": "Let's try again with fresh eyes.",
        "end_lesson": "You've done excellent work today.",
    },
    "pt-BR": {
        "advance": "Otimo trabalho - pronto para avancar.",
        "guided_retry": "Voce esta progredindo - mais uma tentativa focada.",
        "retry": "Vamos tentar de novo com um novo olhar.",
        "end_lesson": "Voce fez um excelente trabalho hoje.",
    },
}


def normalize_language(language: str | None) -> LanguageCode:
    """Return a supported language code, defaulting to English (UK)."""
    if language in _SUPPORTED:
        return cast(LanguageCode, language)
    return DEFAULT_LANGUAGE


def language_name(language: LanguageCode) -> str:
    return _LANGUAGE_NAMES[language]


def language_instruction(language: LanguageCode) -> str:
    return (
        "Language requirement: respond only in "
        f"{language_name(language)}. Keep this language consistently in all user-facing text."
    )


def localized_reason(action: RecommendedAction, language: LanguageCode) -> str:
    return _REASON_BY_ACTION[language][action]
