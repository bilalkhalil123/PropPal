"""
Specialized sub-agent for creating a new builder service via conversation.
The implementation is intentionally deterministic so that the agent behaves
predictably even when users provide unstructured answers.
"""

import logging
import re
from typing import Awaitable, Callable, Dict, Any, Optional, List

from dotenv import load_dotenv

from .tools import check_builder_profile_exists
from .tools.builder_creation import create_builder_service_sync

load_dotenv()
logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = [
    "plumbing",
    "electrical",
    "construction",
    "renovation",
    "interior",
    "painting",
    "landscaping",
    "hvac",
    "roofing",
    "masonry",
    "civil",
    "maintenance",
]


def _parse_features_list(text_or_list: Any) -> Optional[List[str]]:
    """Normalize service_features to a clean list of strings."""
    if text_or_list is None:
        return None
    if isinstance(text_or_list, list):
        cleaned = [str(item).strip() for item in text_or_list if str(item).strip()]
        return cleaned if cleaned else None
    text = str(text_or_list).replace("\n", ",")
    parts = re.split(r",|\band\b|&|\b\d+\.|\s-\s|•", text, flags=re.IGNORECASE)
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return cleaned if cleaned else None


def _parse_price_and_unit(text: str) -> tuple[Optional[float], Optional[str]]:
    """Extract numeric base price and a price unit from free text."""
    if not text:
        return None, None
    t = text.lower().strip()
    num: Optional[float] = None
    m = re.search(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)", t)
    if m:
        raw = m.group(1).replace(",", "")
        try:
            num = float(raw)
        except Exception:
            num = None
    mk = re.search(r"(\d+(?:\.\d+)?)\s*k\b", t)
    if mk:
        try:
            num = float(mk.group(1)) * 1000.0
        except Exception:
            pass
    unit: Optional[str] = None
    mu = re.search(r"per\s+([a-zA-Z ]{2,20})", t)
    if mu:
        unit = f"per {mu.group(1).strip()}"
    if not unit and ("fixed" in t or "flat" in t):
        unit = "fixed price"
    return num, unit

def _extract_structured_service_info(text: str) -> Dict[str, Any]:
    """Extract service information from structured text formats."""
    extracted = {}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Extract title - look for "Title:" at start of line
    for i, line in enumerate(lines):
        if re.match(r"^title\s*:?\s*(.+)$", line, re.IGNORECASE):
            title = re.sub(r"^title\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            # Remove "Description:" if it accidentally got included
            if "description:" in title.lower():
                title = re.split(r"\s+description\s*:", title, flags=re.IGNORECASE)[0].strip()
            if title and len(title) > 2:
                extracted["title"] = title
                break
    
    # Extract description - look for "Description:" at start of line
    for i, line in enumerate(lines):
        if re.match(r"^description\s*:?\s*(.+)$", line, re.IGNORECASE):
            desc = re.sub(r"^description\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            # Remove "Category:" or other field labels if they got included
            desc = re.split(r"\s+(?:category|base price|price unit|unit)\s*:", desc, flags=re.IGNORECASE)[0].strip()
            if desc and len(desc) > 10:
                extracted["description"] = desc
                break
    
    # Extract category
    for line in lines:
        if re.match(r"^category\s*:?\s*(.+)$", line, re.IGNORECASE):
            cat = re.sub(r"^category\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            if "/" in cat:
                cat = cat.split("/")[0].strip()
            if cat and len(cat) > 2:
                extracted["category"] = cat
                break
    
    # Extract base price
    for line in lines:
        m = re.search(r"base\s+price\s*:?\s*\$?\s*([\d,]+(?:\.\d+)?)", line, re.IGNORECASE)
        if m:
            try:
                price_str = m.group(1).replace(",", "")
                price_val = float(price_str)
                if price_val > 0:
                    extracted["base_price"] = price_val
                    break
            except (ValueError, AttributeError):
                pass
    
    # Extract price unit
    for line in lines:
        m = re.search(r"unit\s*:?\s*([^\n,]+)", line, re.IGNORECASE)
        if m:
            unit = m.group(1).strip()
            if "per" not in unit.lower():
                unit = f"per {unit}"
            if unit and len(unit) > 3:
                extracted["price_unit"] = unit
                break
    
    # Fallback: try parsing price and unit from whole text
    if "base_price" not in extracted or "price_unit" not in extracted:
        price_num, price_unit = _parse_price_and_unit(text)
        if price_num and "base_price" not in extracted:
            extracted["base_price"] = price_num
        if price_unit and "price_unit" not in extracted:
            extracted["price_unit"] = price_unit
    
    return extracted

def _extract_structured_service_info(text: str) -> Dict[str, Any]:
    """Extract service information from structured text formats."""
    extracted: Dict[str, Any] = {}
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines:
        if re.match(r"^title\s*:?", line, re.IGNORECASE):
            value = re.sub(r"^title\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            value = re.split(r"\s+description\s*:", value, flags=re.IGNORECASE)[0].strip()
            if value and len(value) > 2:
                extracted["title"] = value
            break

    for line in lines:
        if re.match(r"^description\s*:?", line, re.IGNORECASE):
            value = re.sub(r"^description\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            value = re.split(r"\s+(?:category|base price|price unit|unit)\s*:", value, flags=re.IGNORECASE)[0].strip()
            if value and len(value) > 10:
                extracted["description"] = value
            break

    for line in lines:
        if re.match(r"^category\s*:?", line, re.IGNORECASE):
            value = re.sub(r"^category\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            if "/" in value:
                value = value.split("/")[0].strip()
            if value and len(value) > 2:
                extracted["category"] = value
            break

    for line in lines:
        m = re.search(r"base\s+price\s*:?\s*\$?\s*([\d,]+(?:\.\d+)?)", line, re.IGNORECASE)
        if m:
            try:
                extracted["base_price"] = float(m.group(1).replace(",", ""))
            except (ValueError, AttributeError):
                pass
            break

    for line in lines:
        m = re.search(r"(?:price\s+unit|unit)\s*:?\s*([^\n,]+)", line, re.IGNORECASE)
        if m:
            unit = m.group(1).strip()
            if "per" not in unit.lower():
                unit = f"per {unit}"
            if len(unit) > 3:
                extracted["price_unit"] = unit
            break

    if "base_price" not in extracted or "price_unit" not in extracted:
        price_num, price_unit = _parse_price_and_unit(text)
        if price_num and "base_price" not in extracted:
            extracted["base_price"] = price_num
        if price_unit and "price_unit" not in extracted:
            extracted["price_unit"] = price_unit

    return extracted


def _categorize_from_text(text: str) -> Optional[str]:
    text_lower = text.lower()
    for keyword in CATEGORY_KEYWORDS:
        if keyword in text_lower:
            return keyword
    return None


def _update_service_data_from_text(text: str, data: Dict[str, Any]) -> bool:
    """Apply heuristics to pull service info out of arbitrary text."""
    if not text:
        return False
    updated = False

    structured = _extract_structured_service_info(text)
    for key, value in structured.items():
        if value is None:
            continue
        if key == "base_price":
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
        if key not in data or data.get(key) in (None, [], ""):
            data[key] = value
            updated = True

    # Title heuristics
    if not data.get("title"):
        title_match = re.search(r"(?:service\s+title|title)\s*(?:is|=|:)\s*(.+)", text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            if len(title) > 2:
                data["title"] = title
                updated = True

    # Description heuristic: treat long sentences as description if we lack one
    if not data.get("description"):
        cleaned = text.strip()
        if len(cleaned) > 40 and not cleaned.lower().startswith(("title", "category", "base price", "price unit")):
            data["description"] = cleaned
            updated = True

    # Category heuristics
    if not data.get("category"):
        category = _categorize_from_text(text)
        if category:
            data["category"] = category.title()
            updated = True

    # Price heuristics
    if data.get("base_price") is None or not data.get("price_unit"):
        price_num, price_unit = _parse_price_and_unit(text)
        if data.get("base_price") is None and price_num is not None:
            data["base_price"] = price_num
            updated = True
        if not data.get("price_unit") and price_unit:
            data["price_unit"] = price_unit
            updated = True

    return updated


def _format_missing_prompt(missing: List[str]) -> str:
    labels = {
        "title": "service title",
        "description": "service description",
        "category": "service category",
        "base_price": "base price",
        "price_unit": "pricing unit (e.g., 'per sqft')",
    }
    readable = [labels[m] for m in missing if m in labels]
    if len(readable) == 1:
        fields_text = readable[0]
    else:
        fields_text = ", ".join(readable[:-1]) + f", and {readable[-1]}"
    return f"I still need the following details: {fields_text}. Please provide them in any order."


class BuilderServiceCreationAgent:
    """Deterministic agent that gathers required information for a builder service."""

    REQUIRED_FIELDS = ["title", "description", "category", "base_price", "price_unit"]

    def process_query(self, query: str, clerk_id: str) -> Dict[str, Any]:
        """Non-interactive entry point retained for API compatibility."""
        return {
            "success": True,
            "response": "Service creation runs in interactive mode. Please use the chat interface.",
            "status": "handoff",
        }

    async def process_query_interactive(
        self,
        query: str,
        clerk_id: str,
        send: Callable[[Dict[str, Any]], Awaitable[None]],
        recv_text: Callable[[], Awaitable[str]],
    ) -> Dict[str, Any]:
        """Interactive websocket flow for service creation."""
        if not query or not query.strip():
            return {"success": False, "response": "Please provide a valid query.", "error": "empty_query"}
        if not clerk_id:
            return {"success": False, "response": "User could not be identified.", "error": "missing_clerk_id"}

        # Guardrails
        profile_check = check_builder_profile_exists(clerk_id=clerk_id)
        if not profile_check.get("user_exists", False):
            message = "User account not found. Please ensure you are registered."
            await send({"type": "agent", "message": message})
            return {"success": False, "response": message, "error": "user_not_found"}
        if not profile_check.get("exists", False):
            message = profile_check.get("error") or "You need a builder profile before creating a service."
            await send({"type": "agent", "message": message})
            return {"success": False, "response": message, "error": "profile_missing"}

        service_data: Dict[str, Any] = {
            "title": None,
            "description": None,
            "category": None,
            "base_price": None,
            "price_unit": None,
            "estimated_duration": None,
            "service_features": None,
        }
        _update_service_data_from_text(query, service_data)

        greeting_sent = False
        optional_duration_done = False
        optional_features_done = False

        while True:
            missing_fields = [field for field in self.REQUIRED_FIELDS if not service_data.get(field)]

            if missing_fields:
                if not greeting_sent:
                    message = (
                        "I'll help you create your builder service! "
                        "Please share the service title, description, category, base price, and pricing unit."
                    )
                    greeting_sent = True
                else:
                    message = _format_missing_prompt(missing_fields)

                await send({"type": "agent", "message": message, "status": "continue"})
                user_input = (await recv_text()).strip()
                
                # Enhanced cancel detection
                user_input_lower = user_input.lower()
                cancel_keywords = [
                    "quit", "exit", "cancel", "stop", "no", "nevermind", "never mind",
                    "don't", "do not", "don't want", "do not want", "not interested",
                    "i don't want", "i do not want", "i don't want to", "i do not want to",
                    "don't create", "do not create", "don't make", "do not make",
                    "cancel it", "stop it", "forget it", "skip it"
                ]
                
                # Check if input contains any cancel keywords
                if any(keyword in user_input_lower for keyword in cancel_keywords):
                    cancel_msg = "No problem. I've cancelled the service creation process."
                    await send({"type": "agent", "message": cancel_msg, "status": "cancelled"})
                    return {"success": False, "response": cancel_msg, "status": "cancelled"}

                if not _update_service_data_from_text(user_input, service_data):
                    await send({
                        "type": "agent",
                        "message": "I didn't catch any of the required details. Could you rephrase or provide them again?",
                        "status": "continue",
                    })
                continue

            # Ask optional estimated duration
            if not optional_duration_done:
                prompt = "Would you like to add an estimated duration (e.g., '2 weeks')? Reply 'skip' if not."
                await send({"type": "agent", "message": prompt, "status": "ask_duration"})
                user_input = (await recv_text()).strip()
                
                # Check for cancel
                user_input_lower = user_input.lower()
                cancel_keywords = [
                    "quit", "exit", "cancel", "stop", "no", "nevermind", "never mind",
                    "don't", "do not", "don't want", "do not want", "not interested",
                    "i don't want", "i do not want", "i don't want to", "i do not want to",
                    "don't create", "do not create", "don't make", "do not make",
                    "cancel it", "stop it", "forget it", "skip it"
                ]
                if any(keyword in user_input_lower for keyword in cancel_keywords):
                    cancel_msg = "No problem. I've cancelled the service creation process."
                    await send({"type": "agent", "message": cancel_msg, "status": "cancelled"})
                    return {"success": False, "response": cancel_msg, "status": "cancelled"}
                
                if user_input.lower() not in {"skip", "no", "none", ""}:
                    service_data["estimated_duration"] = user_input
                optional_duration_done = True
                continue

            # Ask optional service features
            if not optional_features_done:
                prompt = "Would you like to list any notable features (e.g., warranty, free consultation)? Reply 'skip' if not."
                await send({"type": "agent", "message": prompt, "status": "ask_features"})
                user_input = (await recv_text()).strip()
                
                # Check for cancel
                user_input_lower = user_input.lower()
                cancel_keywords = [
                    "quit", "exit", "cancel", "stop", "no", "nevermind", "never mind",
                    "don't", "do not", "don't want", "do not want", "not interested",
                    "i don't want", "i do not want", "i don't want to", "i do not want to",
                    "don't create", "do not create", "don't make", "do not make",
                    "cancel it", "stop it", "forget it", "skip it"
                ]
                if any(keyword in user_input_lower for keyword in cancel_keywords):
                    cancel_msg = "No problem. I've cancelled the service creation process."
                    await send({"type": "agent", "message": cancel_msg, "status": "cancelled"})
                    return {"success": False, "response": cancel_msg, "status": "cancelled"}
                
                if user_input.lower() not in {"skip", "no", "none", ""}:
                    service_data["service_features"] = _parse_features_list(user_input) or user_input
                optional_features_done = True
                continue

            # All required info present – create the service
            tool_result = create_builder_service_sync(
                clerk_id=clerk_id,
                title=service_data["title"],
                description=service_data["description"],
                category=service_data["category"],
                base_price=service_data["base_price"],
                price_unit=service_data["price_unit"],
                service_features=service_data.get("service_features") or None,
                estimated_duration=service_data.get("estimated_duration") or None,
            )

            message = tool_result.get("message", "Service created successfully!")
            await send({"type": "completed", "success": tool_result.get("success", True), "message": message})
            return {
                "success": tool_result.get("success", True),
                "response": message,
                "status": "completed" if tool_result.get("success", True) else "failed",
                "error": tool_result.get("error", None),
            }
