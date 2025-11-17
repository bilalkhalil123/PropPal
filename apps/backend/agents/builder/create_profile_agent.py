"""
Specialized sub-agent for creating a new builder profile via conversation.
This implementation is deterministic so that the agent behaves reliably even
when users provide unstructured or partial answers.
"""

import logging
import re
from typing import Awaitable, Callable, Dict, Any, Optional, List

from dotenv import load_dotenv

from .tools import check_builder_profile_exists
from .tools.builder_creation import create_builder_profile_sync

load_dotenv()
logger = logging.getLogger(__name__)


def _parse_list(text_or_list: Any) -> Optional[List[str]]:
    """Normalize a list from string with commas, 'and', '&', newlines, bullets, or numbered items."""
    if text_or_list is None:
        return None
    if isinstance(text_or_list, list):
        cleaned = [str(item).strip() for item in text_or_list if str(item).strip()]
        return cleaned if cleaned else None
    text = str(text_or_list).replace("\n", ",")
    parts = re.split(r",|\band\b|&|\b\d+\.|\s-\s|•", text, flags=re.IGNORECASE)
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return cleaned if cleaned else None


def _extract_structured_profile_info(text: str) -> Dict[str, Any]:
    """Extract profile info from labelled input."""
    extracted: Dict[str, Any] = {}
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines:
        if re.match(r"^(?:company|business)(?:\s+name)?\s*:?", line, re.IGNORECASE):
            value = re.sub(r"^(?:company|business)(?:\s+name)?\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            if value:
                extracted["company_name"] = value
            break

    for line in lines:
        if re.match(r"^(?:city|based\s+in|located\s+in|location)\s*:?", line, re.IGNORECASE):
            value = re.sub(r"^(?:city|based\s+in|located\s+in|location)\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            if value:
                extracted["city"] = value
            break

    for line in lines:
        if re.match(r"^(?:specialization|services|expertise)\s*:?", line, re.IGNORECASE):
            value = re.sub(r"^(?:specialization|services|expertise)\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            specs = _parse_list(value)
            if specs:
                extracted["specialization"] = specs
            break

    for line in lines:
        m = re.search(r"experience\s*:?\s*(\d+)\s*(?:years?|yrs?)?", line, re.IGNORECASE)
        if m:
            try:
                extracted["experience_years"] = int(m.group(1))
            except (ValueError, TypeError):
                pass
            break

    for line in lines:
        if re.match(r"^(?:about|description)\s*:?", line, re.IGNORECASE):
            value = re.sub(r"^(?:about|description)\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            if value and len(value) > 10:
                extracted["about"] = value
            break

    return extracted


def _update_profile_data_from_text(text: str, data: Dict[str, Any]) -> bool:
    """Apply heuristics to pull profile info out of arbitrary text."""
    if not text:
        return False
    updated = False

    structured = _extract_structured_profile_info(text)
    for key, value in structured.items():
        if value and not data.get(key):
            if key == "specialization":
                data[key] = value
            elif key == "experience_years":
                try:
                    data[key] = int(value)
                except (ValueError, TypeError):
                    continue
            else:
                data[key] = str(value).strip()
            updated = True

    text_lower = text.lower()

    if not data.get("company_name"):
        m = re.search(r"(?:company|business)(?:\s+name)?\s*(?:is|=|:)\s*(.+)", text, re.IGNORECASE)
        if m:
            company = m.group(1).strip()
            if len(company) > 2:
                data["company_name"] = company
                updated = True
        else:
            m = re.search(r"(?:we\s+are|our\s+company\s+is)\s+([a-zA-Z0-9 &_-]{3,})", text, re.IGNORECASE)
            if m:
                data["company_name"] = m.group(1).strip().title()
                updated = True

    if not data.get("city"):
        m = re.search(r"(?:based\s+in|located\s+in|in)\s+([a-zA-Z ]{2,})", text_lower)
        if m:
            data["city"] = m.group(1).strip().title()
            updated = True

    if not data.get("specialization"):
        specs = _parse_list(text)
        if specs:
            data["specialization"] = specs
            updated = True

    if data.get("experience_years") is None:
        m = re.search(r"(\d{1,2})\s*years?", text_lower)
        if m:
            data["experience_years"] = int(m.group(1))
            updated = True

    if not data.get("about"):
        cleaned = text.strip()
        if len(cleaned) > 40 and ("we " in text_lower or "our " in text_lower):
            data["about"] = cleaned
            updated = True

    return updated


def _format_missing_prompt(missing: List[str]) -> str:
    labels = {
        "company_name": "company name",
        "city": "city",
        "specialization": "areas of specialization",
        "experience_years": "years of experience",
        "about": "a brief description about your company",
    }
    readable = [labels[m] for m in missing if m in labels]
    if len(readable) == 1:
        fields = readable[0]
    else:
        fields = ", ".join(readable[:-1]) + f", and {readable[-1]}"
    return f"I still need the following details: {fields}. Please share them in any order."


class BuilderProfileCreationAgent:
    """Deterministic agent for builder profile onboarding."""

    REQUIRED_FIELDS = ["company_name", "city", "specialization", "experience_years", "about"]

    def process_query(self, query: str, clerk_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "response": "Profile creation runs in interactive mode. Please use the chat interface.",
            "status": "handoff",
        }

    async def process_query_interactive(
        self,
        query: str,
        clerk_id: str,
        send: Callable[[Dict[str, Any]], Awaitable[None]],
        recv_text: Callable[[], Awaitable[str]],
    ) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"success": False, "response": "Please provide a valid query.", "error": "empty_query"}
        if not clerk_id:
            return {"success": False, "response": "User could not be identified.", "error": "missing_clerk_id"}

        profile_check = check_builder_profile_exists(clerk_id=clerk_id)
        if not profile_check.get("user_exists", False):
            message = "User account not found. Please ensure you are registered."
            await send({"type": "agent", "message": message})
            return {"success": False, "response": message, "error": "user_not_found"}
        if profile_check.get("exists", False):
            message = "You already have a builder profile. Each user can only create one."
            await send({"type": "agent", "message": message})
            return {"success": False, "response": message, "error": "profile_exists"}

        profile_data: Dict[str, Any] = {
            "company_name": None,
            "city": None,
            "specialization": None,
            "experience_years": None,
            "about": None,
        }

        _update_profile_data_from_text(query, profile_data)

        greeting_sent = False

        while True:
            missing = [field for field in self.REQUIRED_FIELDS if not profile_data.get(field)]

            if missing:
                if not greeting_sent:
                    message = (
                        "I'll help you create your builder profile! "
                        "Please share your company name, city, areas of specialization, years of experience, and a short description."
                    )
                    greeting_sent = True
                else:
                    message = _format_missing_prompt(missing)

                await send({"type": "agent", "message": message, "status": "continue"})
                user_input = (await recv_text()).strip()
                if user_input.lower() in {"quit", "exit", "cancel", "stop"}:
                    cancel_msg = "No problem. I've cancelled the profile creation process."
                    await send({"type": "agent", "message": cancel_msg, "status": "cancelled"})
                    return {"success": False, "response": cancel_msg, "status": "cancelled"}

                if not _update_profile_data_from_text(user_input, profile_data):
                    await send({
                        "type": "agent",
                        "message": "I didn't catch those details. Could you rephrase or provide them again?",
                        "status": "continue",
                    })
                continue

            tool_result = create_builder_profile_sync(
                clerk_id=clerk_id,
                company_name=profile_data["company_name"],
                specialization=_parse_list(profile_data["specialization"]) or profile_data["specialization"],
                experience_years=profile_data["experience_years"],
                about=profile_data["about"],
                city=profile_data["city"],
            )
            message = tool_result.get("message", "Profile created successfully!")
            await send({"type": "completed", "success": tool_result.get("success", True), "message": message})
            return {
                "success": tool_result.get("success", True),
                "response": message,
                "status": "completed" if tool_result.get("success", True) else "failed",
                "error": tool_result.get("error", None),
            }

