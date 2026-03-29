"""Translation utilities using Groq LLM (optional)."""
from __future__ import annotations

from typing import Tuple, Optional

from groq import Groq

from common.config import get_settings


def _get_client() -> Optional[Groq]:
    settings = get_settings()
    if not settings.GROQ_API_KEY:
        return None
    return Groq(api_key=settings.GROQ_API_KEY)


def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
) -> Tuple[str, bool, Optional[str]]:
    """
    Translate input text between languages using Groq.

    Returns (translated_text, did_translate, error_message).
    """
    if not text:
        return "", False, None

    settings = get_settings()
    client = _get_client()
    if client is None:
        return text, False, "GROQ_API_KEY not configured"

    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_TRANSLATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a translation assistant. Translate the user's message to the target language. "
                        "Return only the translated text, no extra commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Translate from {source_lang} to {target_lang}: {text}",
                },
            ],
            temperature=0.2,
            max_tokens=256,
        )
        translated = completion.choices[0].message.content.strip()
        return translated or text, True, None
    except Exception as exc:  # noqa: BLE001
        return text, False, str(exc)


def translate_to_english(text: str, source_lang: str = "ur") -> Tuple[str, bool, Optional[str]]:
    return translate_text(text, source_lang=source_lang, target_lang="en")


def translate_to_urdu(text: str, source_lang: str = "en") -> Tuple[str, bool, Optional[str]]:
    return translate_text(text, source_lang=source_lang, target_lang="ur")
