"""
Specialized agent for extracting builder service form fields from natural language.
Uses LLM to extract structured service data and sends updates via WebSocket.
Similar to PropertyListingCreationAgent but for builder services.

This agent is for FORM FILLING mode - extracting fields from text to populate form.
It does NOT create the service directly - the frontend form handles submission.
"""

import logging
import re
import os
from typing import Awaitable, Callable, Dict, Any, Optional, List
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize LLM for service extraction
_extraction_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

# Filler words and phrases to remove
FILLER_WORDS = {
    'uh', 'um', 'er', 'ah', 'oh', 'hmm', 'hm',
    'like', 'you know', 'you see', 'i mean', 'well',
    'actually', 'basically', 'literally', 'sort of', 'kind of',
    'right', 'okay', 'ok', 'so', 'yeah', 'yep', 'yup',
    'i guess', 'i think', 'i suppose', 'maybe', 'perhaps'
}

# Service categories
CATEGORY_KEYWORDS = [
    "plumbing", "electrical", "construction", "renovation",
    "interior", "painting", "landscaping", "hvac",
    "roofing", "masonry", "civil", "maintenance",
    "carpentry", "flooring", "kitchen", "bathroom",
    "commercial", "residential", "industrial"
]

# Price units
PRICE_UNITS = [
    "per sqft", "per square foot", "per marla", "per kanal",
    "per hour", "per day", "per project", "per room",
    "fixed price", "flat rate", "per unit", "per meter"
]


def _clean_text(text: str) -> str:
    """Remove filler words and clean up text for better extraction."""
    if not text:
        return ""
    
    cleaned = text
    for filler in sorted(FILLER_WORDS, key=len, reverse=True):
        pattern = r'\b' + re.escape(filler) + r'\b'
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip(' ,.-')
    
    return cleaned.strip()


def _detect_field_update_intent(text: str) -> Dict[str, Optional[str]]:
    """Detect if user wants to update a specific field."""
    text_lower = _clean_text(text).lower()
    
    update_patterns = {
        'title': [
            r'(?:title|service\s+name)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'(?:call|name)\s+(?:it|the\s+service)\s+(.+?)(?:\.|$|and|,)',
            r'title:\s*(.+?)(?:\.|$|and|,)',
        ],
        'description': [
            r'(?:description|details?)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$)',
            r'description:\s*(.+?)(?:\.|$)',
        ],
        'category': [
            r'(?:category|type)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'category:\s*(.+?)(?:\.|$|and|,)',
            r'\b(' + '|'.join(CATEGORY_KEYWORDS) + r')\b',
        ],
        'base_price': [
            r'(?:price|cost|base\s+price)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,|per)',
            r'(?:rs\.?|pkr|rupees?)\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rs\.?|pkr|rupees?)',
            r'(?:charge|charges?)\s+(\d+(?:,\d+)*(?:\.\d+)?)',
            r'price:\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:thousand|k)\b',
        ],
        'price_unit': [
            r'(?:price\s+unit|unit|pricing)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'(?:per|each)\s+(.+?)(?:\.|$|and|,)',
            r'unit:\s*(.+?)(?:\.|$|and|,)',
        ],
        'estimated_duration': [
            r'(?:duration|time|takes?)\s+(?:is|should be|will be|to|as)?\s*(.+?)(?:\.|$|and|,)',
            r'(?:takes?|requires?)\s+(\d+\s*(?:days?|weeks?|hours?|months?))',
            r'duration:\s*(.+?)(?:\.|$|and|,)',
        ],
        'service_features': [
            r'(?:features?|includes?|includes|offers?)\s+(?:is|are|should be|will be|to|as)?\s*(.+?)(?:\.|$)',
            r'features?:\s*(.+?)(?:\.|$)',
        ],
    }
    
    for field, patterns in update_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                value = match.group(1).strip() if match.groups() else None
                if value and len(value) > 1:
                    value = _clean_text(value)
                    if value:
                        return {field: value}
    
    return {}


class ServiceExtraction(BaseModel):
    """Structured output for builder service information extraction."""
    title: Optional[str] = Field(None, description="Service title/name (short, professional, 5-10 words)")
    description: Optional[str] = Field(None, description="Detailed service description (30+ words)")
    category: Optional[str] = Field(None, description="Service category (plumbing, electrical, construction, etc.)")
    base_price: Optional[float] = Field(None, description="Base price in PKR (numeric value only)")
    price_unit: Optional[str] = Field(None, description="Pricing unit (per sqft, per hour, per project, fixed price, etc.)")
    estimated_duration: Optional[str] = Field(None, description="Estimated time to complete (e.g., '2-3 days', '1 week')")
    service_features: Optional[List[str]] = Field(None, description="List of service features/inclusions")


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
    
    # Extract number with k multiplier
    mk = re.search(r"(\d+(?:\.\d+)?)\s*k\b", t)
    if mk:
        try:
            num = float(mk.group(1)) * 1000.0
        except Exception:
            pass
    
    # Extract plain number
    if num is None:
        m = re.search(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)", t)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                num = float(raw)
            except Exception:
                num = None
    
    # Extract unit
    unit: Optional[str] = None
    mu = re.search(r"per\s+([a-zA-Z ]{2,20})", t)
    if mu:
        unit = f"per {mu.group(1).strip()}"
    if not unit and ("fixed" in t or "flat" in t):
        unit = "fixed price"
    
    return num, unit


def _convert_price_to_pkr(text: str) -> Optional[float]:
    """Convert price text to PKR, handling various formats."""
    if not text:
        return None
    
    text_lower = str(text).lower().strip()
    
    # Try to extract number
    num_match = re.search(r"(\d+(?:\.\d+)?)", text_lower.replace(",", ""))
    if not num_match:
        return None
    
    try:
        base_num = float(num_match.group(1))
    except (ValueError, TypeError):
        return None
    
    # Check for multipliers
    if 'lakh' in text_lower or 'lac' in text_lower:
        return base_num * 100000
    elif 'thousand' in text_lower or 'k' in text_lower:
        return base_num * 1000
    elif 'million' in text_lower or 'm' in text_lower:
        return base_num * 1000000
    
    return base_num


def _improve_text_with_llm(text: str) -> str:
    """Use LLM to improve grammar, fix English, and clean up the text."""
    if not text or len(text.strip()) < 5:
        return text
    
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are a text improvement assistant. Your job is to:\n"
                "1. Fix grammar and spelling errors\n"
                "2. Improve sentence structure and flow\n"
                "3. Remove filler words (uh, um, like, you know, etc.)\n"
                "4. Make the text sound natural and professional\n"
                "5. Keep the original meaning and information intact\n"
                "6. Do NOT add information that wasn't in the original\n"
                "7. Do NOT remove important details\n\n"
                "Return ONLY the improved text, nothing else."
            )),
            ("human", "{text}")
        ])
        
        chain = prompt | _extraction_llm
        result = chain.invoke({"text": text})
        
        if hasattr(result, 'content'):
            improved = result.content.strip()
        elif isinstance(result, str):
            improved = result.strip()
        else:
            improved = str(result).strip()
        
        if len(improved) < len(text) * 0.5:
            return text
        
        return improved
    except Exception as e:
        logger.error(f"LLM text improvement failed: {e}, using original text")
        return text


def _extract_structured_service_info(text: str, current_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract service info using LLM for better accuracy."""
    if not text or len(text.strip()) < 5:
        return {}
    
    cleaned_text = _clean_text(text)
    if len(cleaned_text.strip()) < 5:
        return {}
    
    improved_text = _improve_text_with_llm(cleaned_text)
    
    # Build context about current data
    current_context = ""
    if current_data:
        filled_fields = {k: v for k, v in current_data.items() if v is not None}
        if filled_fields:
            current_context = f"\n\nCurrent service data:\n{str(filled_fields)}\n\n"
            current_context += "If the user wants to UPDATE a field, extract the new value. "
            current_context += "If the user provides NEW information, extract it. "
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a builder service information extraction assistant. Extract structured service details from natural language.\n\n"
            "CRITICAL RULES:\n"
            "- Extract ALL fields mentioned in the text in a SINGLE pass\n"
            "- If user says 'title is X, price is Y, category is Z' - extract ALL of them at once\n"
            "- NEVER include filler words or meta-text\n"
            "- title: Service title/name (short, professional, 5-10 words)\n"
            "  * Do NOT include 'title is' or 'service title is' in the extracted value\n"
            "- description: Detailed service description (30+ words, professional)\n"
            "  * Do NOT include 'description is' or 'service description is'\n"
            "- category: Service category (lowercase: plumbing, electrical, construction, renovation, interior, painting, landscaping, hvac, roofing, masonry, civil, maintenance)\n"
            "- base_price: CRITICAL - Convert to numeric PKR value:\n"
            "  * '5000 rupees' -> 5000.0\n"
            "  * '10k' or '10 thousand' -> 10000.0\n"
            "  * '2 lakh' -> 200000.0\n"
            "  * Return ONLY the number, not text\n"
            "- price_unit: Pricing unit (e.g., 'per sqft', 'per hour', 'per project', 'per room', 'fixed price')\n"
            "- estimated_duration: Time estimate (e.g., '2-3 days', '1 week', '3-4 hours')\n"
            "- service_features: List of features/inclusions (e.g., ['materials included', 'cleanup included', 'warranty'])\n"
            "- Only extract information that is EXPLICITLY mentioned\n"
            "- If user says 'change X to Y' or 'update X', extract the NEW value for X"
        ) + current_context),
        ("human", "{text}")
    ])
    
    structured_llm = _extraction_llm.with_structured_output(ServiceExtraction)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"text": improved_text})
        extracted = result.model_dump(exclude_none=True)
        
        # Post-process base_price
        if 'base_price' in extracted:
            price_val = extracted['base_price']
            if isinstance(price_val, str):
                converted = _convert_price_to_pkr(price_val)
                if converted is not None:
                    extracted['base_price'] = converted
                else:
                    try:
                        extracted['base_price'] = float(price_val.replace(",", ""))
                    except (ValueError, TypeError):
                        del extracted['base_price']
            elif isinstance(price_val, (int, float)):
                extracted['base_price'] = float(price_val)
        
        # Post-process service_features
        if 'service_features' in extracted:
            if isinstance(extracted['service_features'], str):
                extracted['service_features'] = _parse_features_list(extracted['service_features'])
            elif isinstance(extracted['service_features'], list):
                extracted['service_features'] = [s.strip() for s in extracted['service_features'] if s and s.strip()]
        
        # Post-process category to lowercase
        if 'category' in extracted and extracted['category']:
            extracted['category'] = extracted['category'].lower()
        
        # Clean string fields
        for key in ['title', 'description', 'price_unit', 'estimated_duration']:
            if key in extracted and extracted[key]:
                extracted[key] = _clean_text(str(extracted[key]))
        
        logger.info(f"Extracted service info: {extracted}")
        return extracted
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}, falling back to regex")
        return _extract_with_regex(cleaned_text)


def _extract_with_regex(text: str) -> Dict[str, Any]:
    """Fallback regex-based extraction if LLM fails."""
    extracted: Dict[str, Any] = {}
    text_lower = text.lower()
    
    # Title
    title_match = re.search(r"(?:service\s+title|title)\s*(?:is|=|:)\s*(.+?)(?:\.|,|$)", text, re.IGNORECASE)
    if title_match:
        extracted['title'] = title_match.group(1).strip()
    
    # Category - check for category keywords
    for cat in CATEGORY_KEYWORDS:
        if cat.lower() in text_lower:
            extracted['category'] = cat.lower()
            break
    
    # Price and unit
    price_num, price_unit = _parse_price_and_unit(text)
    if price_num:
        extracted['base_price'] = price_num
    if price_unit:
        extracted['price_unit'] = price_unit
    
    # Duration
    duration_match = re.search(r"(\d+(?:\s*-\s*\d+)?)\s*(days?|weeks?|hours?|months?)", text_lower)
    if duration_match:
        extracted['estimated_duration'] = f"{duration_match.group(1)} {duration_match.group(2)}"
    
    return extracted


def _update_service_data_from_text(text: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply extraction to update service data.
    Returns dict of only the fields that were updated.
    """
    if not text:
        return {}
    
    cleaned_text = _clean_text(text)
    if not cleaned_text:
        return {}
    
    updated_fields: Dict[str, Any] = {}
    
    # Check for field update intent first
    update_intent = _detect_field_update_intent(cleaned_text)
    
    # If there's explicit update intent, process it
    if update_intent:
        for field, new_value in update_intent.items():
            old_value = data.get(field)
            if field == "base_price":
                try:
                    converted = _convert_price_to_pkr(str(new_value))
                    new_val = converted if converted else float(str(new_value).replace(",", ""))
                    if new_val != old_value:
                        data[field] = new_val
                        updated_fields[field] = new_val
                except (ValueError, TypeError):
                    pass
            elif field == "service_features":
                features = _parse_features_list(new_value)
                if features and features != old_value:
                    data[field] = features
                    updated_fields[field] = features
            else:
                cleaned_value = _clean_text(str(new_value))
                if cleaned_value and cleaned_value != old_value:
                    data[field] = cleaned_value
                    updated_fields[field] = cleaned_value
    
    # Use LLM extraction with current data context
    structured = _extract_structured_service_info(cleaned_text, current_data=data)
    
    for key, value in structured.items():
        if value is not None:
            old_value = data.get(key)
            should_update = False
            
            # Always update if field is empty
            if not old_value or old_value == '' or old_value == 0 or old_value == []:
                should_update = True
            # Update if explicitly mentioned in update_intent
            elif key in update_intent:
                should_update = True
            # Update if user used update keywords
            elif any(kw in cleaned_text.lower() for kw in ['change', 'update', 'set', 'modify', 'edit']):
                field_keywords = {
                    'title': ['title', 'name', 'service title'],
                    'description': ['description', 'details'],
                    'category': ['category', 'type'],
                    'base_price': ['price', 'cost', 'charge'],
                    'price_unit': ['unit', 'per', 'pricing'],
                    'estimated_duration': ['duration', 'time', 'takes'],
                    'service_features': ['features', 'includes', 'offers'],
                }
                keywords = field_keywords.get(key, [])
                if any(kw in cleaned_text.lower() for kw in keywords):
                    should_update = True
            
            if should_update:
                if key == "base_price":
                    try:
                        if isinstance(value, str):
                            converted = _convert_price_to_pkr(value)
                            new_val = converted if converted else float(value.replace(",", ""))
                        else:
                            new_val = float(value)
                        if new_val != old_value:
                            data[key] = new_val
                            updated_fields[key] = new_val
                    except (ValueError, TypeError):
                        continue
                elif key == "service_features":
                    if isinstance(value, list):
                        features = [s.strip() for s in value if s and s.strip()]
                    else:
                        features = _parse_features_list(value)
                    if features and features != old_value:
                        data[key] = features
                        updated_fields[key] = features
                else:
                    cleaned_value = _clean_text(str(value))
                    if cleaned_value and cleaned_value != old_value:
                        data[key] = cleaned_value
                        updated_fields[key] = cleaned_value
    
    return updated_fields


def _generate_description_with_llm(service_data: Dict[str, Any]) -> str:
    """Generate a service description using LLM based on available service details."""
    details = []
    if service_data.get("title"):
        details.append(f"Service: {service_data['title']}")
    if service_data.get("category"):
        details.append(f"Category: {service_data['category']}")
    if service_data.get("base_price"):
        details.append(f"Price: PKR {service_data['base_price']:,.0f}")
    if service_data.get("price_unit"):
        details.append(f"Pricing: {service_data['price_unit']}")
    if service_data.get("estimated_duration"):
        details.append(f"Duration: {service_data['estimated_duration']}")
    if service_data.get("service_features"):
        features = service_data['service_features']
        if isinstance(features, list):
            details.append(f"Features: {', '.join(features)}")
    
    existing_description = service_data.get("description", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a professional service description writer. "
            "Generate a compelling, professional service description based on the provided details.\n\n"
            "Guidelines:\n"
            "1. Write in a professional, engaging tone\n"
            "2. Highlight key features and benefits\n"
            "3. Include all relevant details provided\n"
            "4. Make it appealing to potential clients\n"
            "5. Keep it between 50-100 words\n"
            "6. If an existing description is provided, enhance it\n"
            "7. Use proper grammar and professional language\n\n"
            "Return ONLY the description text, nothing else."
        )),
        ("human", (
            f"Service Details:\n" + "\n".join(details) + 
            (f"\n\nExisting Description:\n{existing_description}" if existing_description else "") +
            "\n\nGenerate a professional service description:"
        ))
    ])
    
    chain = prompt | _extraction_llm
    
    try:
        result = chain.invoke({})
        if hasattr(result, 'content'):
            description = result.content.strip()
        elif isinstance(result, str):
            description = result.strip()
        else:
            description = str(result).strip()
        
        if not description or len(description) < 30:
            description = (
                f"Professional {service_data.get('category', 'service')} service. "
                f"{service_data.get('title', 'Quality service')} available at competitive rates."
            )
        
        return description
    except Exception as e:
        logger.error(f"LLM description generation failed: {e}")
        return (
            f"Professional {service_data.get('category', 'service')} service. "
            f"Contact us for quality work and competitive pricing."
        )


def _format_missing_prompt(missing: List[str]) -> str:
    """Format a user-friendly prompt for missing fields."""
    labels = {
        "title": "service title",
        "description": "service description",
        "category": "service category (e.g., plumbing, electrical, construction)",
        "base_price": "base price",
        "price_unit": "pricing unit (e.g., 'per sqft', 'per hour', 'fixed price')",
        "estimated_duration": "estimated duration",
        "service_features": "service features/inclusions",
    }
    readable = [labels[m] for m in missing if m in labels]
    if len(readable) == 1:
        fields = readable[0]
    elif len(readable) == 2:
        fields = f"{readable[0]} and {readable[1]}"
    else:
        fields = ", ".join(readable[:-1]) + f", and {readable[-1]}"
    return f"I still need the following details: {fields}. Please share them. You can also update any existing field by saying 'change [field] to [value]'."


class BuilderServiceFormExtractionAgent:
    """Agent for extracting builder service form fields from natural language."""

    REQUIRED_FIELDS = ["title", "description", "category", "base_price", "price_unit"]
    OPTIONAL_FIELDS = ["estimated_duration", "service_features"]

    def process_query(self, query: str, clerk_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "response": "Service form extraction runs in interactive mode. Please use the chat interface.",
            "status": "handoff",
        }

    async def process_query_interactive(
        self,
        query: str,
        clerk_id: str,
        send: Callable[[Dict[str, Any]], Awaitable[None]],
        recv_text: Callable[[], Awaitable[str]],
    ) -> Dict[str, Any]:
        """
        Single-pass extraction for service form field extraction.
        Extracts fields from the query and sends updates, then returns immediately.
        Does NOT loop waiting for more input - the frontend handles the conversation flow.
        """
        if not query or not query.strip():
            await send({
                "type": "field_update",
                "updates": {},
                "missing_fields": self.REQUIRED_FIELDS,
                "message": "Please provide service details.",
                "status": "continue"
            })
            return {"success": True, "response": "Waiting for input.", "status": "continue"}
        
        if not clerk_id:
            await send({
                "type": "error",
                "message": "User could not be identified.",
                "success": False
            })
            return {"success": False, "response": "User could not be identified.", "error": "missing_clerk_id"}

        service_data: Dict[str, Any] = {
            "title": None,
            "description": None,
            "category": None,
            "base_price": None,
            "price_unit": None,
            "estimated_duration": None,
            "service_features": None,
        }

        # Show processing indicator
        await send({
            "type": "processing",
            "message": "Processing your input...",
            "status": "processing"
        })

        # Clean text and extract fields
        cleaned_text = _clean_text(query.strip())
        updated_fields = {}
        
        if cleaned_text:
            updated_fields = _update_service_data_from_text(cleaned_text, service_data)

        # Calculate missing fields
        missing = [field for field in self.REQUIRED_FIELDS if not service_data.get(field)]

        if updated_fields:
            # Send field updates
            await send({
                "type": "field_update",
                "updates": updated_fields,
                "missing_fields": missing,
                "message": _format_missing_prompt(missing) if missing else "All required fields extracted!",
                "status": "continue"
            })
            
            return {
                "success": True,
                "response": "Fields extracted successfully.",
                "status": "continue",
                "data": service_data,
                "updates": updated_fields,
                "missing_fields": missing,
            }
        else:
            # Couldn't extract any fields
            await send({
                "type": "field_update",
                "updates": {},
                "missing_fields": missing,
                "message": "I couldn't extract service details from that. Please try providing details like: service title, category (plumbing, electrical, etc.), base price, and pricing unit.",
                "status": "continue"
            })
            
            return {
                "success": True,
                "response": "No fields extracted.",
                "status": "continue",
                "missing_fields": missing,
            }
