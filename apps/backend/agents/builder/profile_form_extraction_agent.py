"""
Specialized agent for extracting builder profile form fields from natural language.
Uses LLM to extract structured profile data and sends updates via WebSocket.
Similar to PropertyListingCreationAgent but for builder profiles.

This agent is for FORM FILLING mode - extracting fields from text to populate form.
It does NOT create the profile directly - the frontend form handles submission.
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

# Initialize LLM for profile extraction
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

# Common cities in Pakistan
PAKISTAN_CITIES = [
    'Islamabad', 'Karachi', 'Lahore', 'Rawalpindi', 'Peshawar',
    'Quetta', 'Faisalabad', 'Multan', 'Hyderabad', 'Sialkot',
    'Gujranwala', 'Abbottabad', 'Bahawalpur', 'Sargodha', 'Sukkur'
]

# Common specializations
SPECIALIZATION_KEYWORDS = [
    'construction', 'renovation', 'interior design', 'electrical',
    'plumbing', 'hvac', 'roofing', 'landscaping', 'painting',
    'masonry', 'carpentry', 'flooring', 'kitchen', 'bathroom',
    'commercial', 'residential', 'industrial', 'civil engineering',
    'architecture', 'project management', 'home improvement'
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
        'company_name': [
            r'(?:company|business)\s+(?:name)?\s*(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'(?:call|name)\s+(?:it|us|the company)\s+(.+?)(?:\.|$|and|,)',
            r'company\s*(?:name)?:\s*(.+?)(?:\.|$|and|,)',
            r'(?:we\s+are|our\s+company\s+is)\s+(.+?)(?:\.|$|and|,)',
        ],
        'city': [
            r'(?:city|location|based\s+in|located\s+in)\s+(?:is|should be|will be|to|as)?\s*(.+?)(?:\.|$|and|,)',
            r'(?:in|at|from)\s+(' + '|'.join(PAKISTAN_CITIES) + r')(?:\.|$|and|,)',
            r'city:\s*(.+?)(?:\.|$|and|,)',
        ],
        'experience_years': [
            r'(?:experience|years)\s+(?:is|should be|will be|of)?\s*(\d+)\s*(?:years?)?',
            r'(\d+)\s+years?\s+(?:of\s+)?(?:experience|in\s+the\s+field)',
            r'experience:\s*(\d+)',
            r'(\d+)\s+years?\s+experience',
        ],
        'specialization': [
            r'(?:specialization|expertise|specialize\s+in|services?)\s+(?:is|are|include)?\s*(?:in)?\s*(.+?)(?:\.|$)',
            r'(?:we\s+do|we\s+offer|we\s+provide)\s+(.+?)(?:\.|$)',
            r'specialization:\s*(.+?)(?:\.|$)',
        ],
        'about': [
            r'(?:about|description)\s+(?:is|should be|will be)?\s*(.+?)(?:\.|$)',
            r'about:\s*(.+?)(?:\.|$)',
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


class ProfileExtraction(BaseModel):
    """Structured output for builder profile information extraction."""
    company_name: Optional[str] = Field(None, description="Company or business name")
    city: Optional[str] = Field(None, description="City where the company is based")
    experience_years: Optional[int] = Field(None, description="Years of experience in the field")
    specialization: Optional[List[str]] = Field(None, description="List of areas of specialization/expertise")
    about: Optional[str] = Field(None, description="Brief description about the company (30+ words)")


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


def _extract_structured_profile_info(text: str, current_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract profile info using LLM for better accuracy."""
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
            current_context = f"\n\nCurrent profile data:\n{str(filled_fields)}\n\n"
            current_context += "If the user wants to UPDATE a field, extract the new value. "
            current_context += "If the user provides NEW information, extract it. "
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a builder profile information extraction assistant. Extract structured profile details from natural language.\n\n"
            "CRITICAL RULES:\n"
            "- Extract ALL fields mentioned in the text in a SINGLE pass\n"
            "- NEVER include filler words or meta-text\n"
            "- company_name: The name of the construction/builder company\n"
            "- city: City in Pakistan (use proper capitalization: Islamabad, Karachi, Lahore, etc.)\n"
            "- experience_years: Number of years of experience (integer only)\n"
            "- specialization: List of areas of expertise (e.g., ['construction', 'renovation', 'interior design'])\n"
            "  * If user says 'we specialize in X, Y, and Z', return ['X', 'Y', 'Z']\n"
            "  * Common specializations: construction, renovation, interior design, electrical, plumbing, etc.\n"
            "- about: A brief company description (should be 30+ words, professional)\n"
            "- Only extract information that is EXPLICITLY mentioned\n"
            "- If user says 'change X to Y' or 'update X', extract the NEW value for X"
        ) + current_context),
        ("human", "{text}")
    ])
    
    structured_llm = _extraction_llm.with_structured_output(ProfileExtraction)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"text": improved_text})
        extracted = result.model_dump(exclude_none=True)
        
        # Post-process specialization to ensure it's a list
        if 'specialization' in extracted:
            if isinstance(extracted['specialization'], str):
                extracted['specialization'] = _parse_list(extracted['specialization'])
            elif isinstance(extracted['specialization'], list):
                extracted['specialization'] = [s.strip() for s in extracted['specialization'] if s and s.strip()]
        
        # Ensure experience_years is an integer
        if 'experience_years' in extracted:
            try:
                extracted['experience_years'] = int(extracted['experience_years'])
            except (ValueError, TypeError):
                del extracted['experience_years']
        
        # Clean string fields
        for key in ['company_name', 'city', 'about']:
            if key in extracted and extracted[key]:
                extracted[key] = _clean_text(str(extracted[key]))
        
        logger.info(f"Extracted profile info: {extracted}")
        return extracted
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}, falling back to regex")
        return _extract_with_regex(cleaned_text)


def _extract_with_regex(text: str) -> Dict[str, Any]:
    """Fallback regex-based extraction if LLM fails."""
    extracted: Dict[str, Any] = {}
    text_lower = text.lower()
    
    # Company name
    company_match = re.search(r"(?:company|business)(?:\s+name)?\s*(?:is|=|:)\s*(.+?)(?:\.|,|$)", text, re.IGNORECASE)
    if company_match:
        extracted['company_name'] = company_match.group(1).strip()
    
    # City - check for Pakistan cities
    for city in PAKISTAN_CITIES:
        if city.lower() in text_lower:
            extracted['city'] = city
            break
    
    # Experience years
    exp_match = re.search(r"(\d+)\s*years?(?:\s+of)?\s*(?:experience)?", text_lower)
    if exp_match:
        try:
            extracted['experience_years'] = int(exp_match.group(1))
        except (ValueError, TypeError):
            pass
    
    # Specialization - look for keywords
    found_specs = []
    for spec in SPECIALIZATION_KEYWORDS:
        if spec.lower() in text_lower:
            found_specs.append(spec.title())
    if found_specs:
        extracted['specialization'] = found_specs
    
    return extracted


def _update_profile_data_from_text(text: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply extraction to update profile data.
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
            if field == "experience_years":
                try:
                    new_val = int(new_value) if isinstance(new_value, str) else new_value
                    if new_val != old_value:
                        data[field] = new_val
                        updated_fields[field] = new_val
                except (ValueError, TypeError):
                    pass
            elif field == "specialization":
                specs = _parse_list(new_value)
                if specs and specs != old_value:
                    data[field] = specs
                    updated_fields[field] = specs
            else:
                cleaned_value = _clean_text(str(new_value))
                if cleaned_value and cleaned_value != old_value:
                    data[field] = cleaned_value
                    updated_fields[field] = cleaned_value
    
    # Use LLM extraction with current data context
    structured = _extract_structured_profile_info(cleaned_text, current_data=data)
    
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
                    'company_name': ['company', 'business', 'name'],
                    'city': ['city', 'location', 'based'],
                    'experience_years': ['experience', 'years'],
                    'specialization': ['specialization', 'expertise', 'specialize', 'services'],
                    'about': ['about', 'description'],
                }
                keywords = field_keywords.get(key, [])
                if any(kw in cleaned_text.lower() for kw in keywords):
                    should_update = True
            
            if should_update:
                if key == "experience_years":
                    try:
                        new_val = int(value)
                        if new_val != old_value:
                            data[key] = new_val
                            updated_fields[key] = new_val
                    except (ValueError, TypeError):
                        continue
                elif key == "specialization":
                    if isinstance(value, list):
                        specs = [s.strip() for s in value if s and s.strip()]
                    else:
                        specs = _parse_list(value)
                    if specs and specs != old_value:
                        data[key] = specs
                        updated_fields[key] = specs
                else:
                    cleaned_value = _clean_text(str(value))
                    if cleaned_value and cleaned_value != old_value:
                        data[key] = cleaned_value
                        updated_fields[key] = cleaned_value
    
    return updated_fields


def _generate_about_with_llm(profile_data: Dict[str, Any]) -> str:
    """Generate a company description using LLM based on available profile details."""
    details = []
    if profile_data.get("company_name"):
        details.append(f"Company: {profile_data['company_name']}")
    if profile_data.get("city"):
        details.append(f"City: {profile_data['city']}")
    if profile_data.get("experience_years"):
        details.append(f"Experience: {profile_data['experience_years']} years")
    if profile_data.get("specialization"):
        specs = profile_data['specialization']
        if isinstance(specs, list):
            details.append(f"Specializations: {', '.join(specs)}")
        else:
            details.append(f"Specializations: {specs}")
    
    existing_about = profile_data.get("about", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a professional company description writer. "
            "Generate a compelling, professional company description based on the provided details.\n\n"
            "Guidelines:\n"
            "1. Write in a professional, engaging tone\n"
            "2. Highlight key expertise and experience\n"
            "3. Include all relevant details provided\n"
            "4. Make it appealing to potential clients\n"
            "5. Keep it between 50-100 words\n"
            "6. If an existing description is provided, enhance it\n"
            "7. Use proper grammar and professional language\n\n"
            "Return ONLY the description text, nothing else."
        )),
        ("human", (
            f"Company Details:\n" + "\n".join(details) + 
            (f"\n\nExisting Description:\n{existing_about}" if existing_about else "") +
            "\n\nGenerate a professional company description:"
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
                f"{profile_data.get('company_name', 'Our company')} is a trusted builder "
                f"based in {profile_data.get('city', 'Pakistan')} with "
                f"{profile_data.get('experience_years', 'several')} years of experience. "
                f"We specialize in {', '.join(profile_data.get('specialization', ['construction'])) if isinstance(profile_data.get('specialization'), list) else profile_data.get('specialization', 'construction')}."
            )
        
        return description
    except Exception as e:
        logger.error(f"LLM description generation failed: {e}")
        return (
            f"{profile_data.get('company_name', 'Our company')} is a trusted builder "
            f"based in {profile_data.get('city', 'Pakistan')} with "
            f"{profile_data.get('experience_years', 'several')} years of experience."
        )


def _format_missing_prompt(missing: List[str]) -> str:
    """Format a user-friendly prompt for missing fields."""
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
    elif len(readable) == 2:
        fields = f"{readable[0]} and {readable[1]}"
    else:
        fields = ", ".join(readable[:-1]) + f", and {readable[-1]}"
    return f"I still need the following details: {fields}. Please share them. You can also update any existing field by saying 'change [field] to [value]'."


class BuilderProfileFormExtractionAgent:
    """Agent for extracting builder profile form fields from natural language."""

    REQUIRED_FIELDS = ["company_name", "city", "specialization", "experience_years", "about"]

    def process_query(self, query: str, clerk_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "response": "Profile form extraction runs in interactive mode. Please use the chat interface.",
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
        Single-pass extraction for profile form field extraction.
        Extracts fields from the query and sends updates, then returns immediately.
        Does NOT loop waiting for more input - the frontend handles the conversation flow.
        """
        if not query or not query.strip():
            await send({
                "type": "field_update",
                "updates": {},
                "missing_fields": self.REQUIRED_FIELDS,
                "message": "Please provide profile details.",
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

        profile_data: Dict[str, Any] = {
            "company_name": None,
            "city": None,
            "specialization": None,
            "experience_years": None,
            "about": None,
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
            updated_fields = _update_profile_data_from_text(cleaned_text, profile_data)

        # Calculate missing fields
        missing = [field for field in self.REQUIRED_FIELDS if not profile_data.get(field)]

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
                "data": profile_data,
                "updates": updated_fields,
                "missing_fields": missing,
            }
        else:
            # Couldn't extract any fields
            await send({
                "type": "field_update",
                "updates": {},
                "missing_fields": missing,
                "message": "I couldn't extract profile details from that. Please try providing details like: company name, city, years of experience, and specializations.",
                "status": "continue"
            })
            
            return {
                "success": True,
                "response": "No fields extracted.",
                "status": "continue",
                "missing_fields": missing,
            }
