"""Language detection helpers for Urdu/English inputs."""
from __future__ import annotations

import re
from typing import Literal

_URDU_REGEX = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


LanguageCode = Literal["ur", "en"]


def is_urdu_text(text: str) -> bool:
    if not text:
        return False
    return bool(_URDU_REGEX.search(text))


def detect_language(text: str, default: LanguageCode = "en") -> LanguageCode:
    if is_urdu_text(text):
        return "ur"
    return default
