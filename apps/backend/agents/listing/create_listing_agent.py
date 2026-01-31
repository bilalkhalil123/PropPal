"""
Specialized sub-agent for creating a new property listing via conversation.
This implementation extracts structured property data from natural language using LLM.
"""

import logging
import re
import os
from typing import Awaitable, Callable, Dict, Any, Optional, List
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from .tools.property_creation import create_property_sync

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize LLM for property extraction
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


def _clean_text(text: str) -> str:
    """
    Remove filler words and clean up text for better extraction.
    """
    if not text:
        return ""
    
    # Convert to lowercase for matching
    text_lower = text.lower()
    
    # Remove filler words (with word boundaries to avoid partial matches)
    cleaned = text
    for filler in sorted(FILLER_WORDS, key=len, reverse=True):  # Sort by length to match longer phrases first
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(filler) + r'\b'
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove leading/trailing spaces and punctuation artifacts
    cleaned = cleaned.strip(' ,.-')
    
    return cleaned.strip()


def _detect_field_update_intent(text: str) -> Dict[str, Optional[str]]:
    """
    Detect if user wants to update a specific field.
    Returns dict with field name and new value if detected.
    Enhanced to catch more explicit field mentions.
    """
    text_lower = _clean_text(text).lower()
    original_text = text  # Keep original for better extraction
    
    # Enhanced patterns for field updates - more comprehensive
    update_patterns = {
        'title': [
            r'(?:title|name)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,|the)',
            r'(?:call|name)\s+it\s+(.+?)(?:\.|$|and|,)',
            r'title:\s*(.+?)(?:\.|$|and|,)',
            r'the\s+title\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
        ],
        'description': [
            r'(?:description|details?|detail)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'description:\s*(.+?)(?:\.|$|and|,)',
            r'the\s+description\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
            r'its?\s+description\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
        ],
        'price': [
            r'(?:price|cost)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'(?:price|cost):\s*(.+?)(?:\.|$|and|,)',
            r'(?:change|update|set)\s+(?:price|cost)\s+(?:to|as)\s+(.+?)(?:\.|$|and|,)',
            r'the\s+price\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
            r'its?\s+price\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
            r'(?:rs\.?|pkr)\s+(.+?)(?:\.|$|and|,)',  # "Rs 1.5 million" or "PKR 1.5 million"
            # Order-independent: "15 million price" or "price 15 million", also handle units
            r'(\d+(?:\.\d+)?)\s*(?:million|m|crore|cr|lakh|lac|l|thousand|k)\s*(?:rupees?|pkr|rs\.?)?\s*(?:price|cost)?',
            r'(?:price|cost)\s+(\d+(?:\.\d+)?)\s*(?:million|m|crore|cr|lakh|lac|l|thousand|k)\s*(?:rupees?|pkr|rs\.?)?',
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rupees?|pkr|rs\.?)\s*(?:price|cost)?',
            r'(?:price|cost)\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rupees?|pkr|rs\.?)?',
        ],
        'property_type': [
            r'(?:type|property type|property)\s+(?:is|should be|will be|to|as)\s+(?:a|an)?\s*(.+?)(?:\.|$|and|,)',
            r'(?:it\'?s|it is)\s+(?:a|an)\s+(.+?)(?:\.|$|and|,)',
            r'property type:\s*(.+?)(?:\.|$|and|,)',
            r'the\s+property\s+(?:is|should be|will be)\s+(?:a|an)?\s*(.+?)(?:\.|$|and|,)',
            # Order-independent: "house type" or "type house"
            r'(house|apartment|plot|commercial|villa|flat|penthouse|townhouse)\s+(?:type|property)',
            r'(?:type|property)\s+(house|apartment|plot|commercial|villa|flat|penthouse|townhouse)',
            r'\b(house|apartment|plot|commercial|villa|flat|penthouse|townhouse)\b',
        ],
        'bedrooms': [
            r'(?:bedrooms?|beds?|bedroom)\s+(?:is|are|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'bedrooms?:\s*(.+?)(?:\.|$|and|,)',
            # Order-independent: "3 bedrooms" or "bedrooms 3"
            r'(\d+)\s+bedrooms?',
            r'bedrooms?\s+(\d+)',
            r'(\d+)\s+bed',
            r'bed\s+(\d+)',
            r'(?:has|have)\s+(\d+)\s+bedrooms?',
        ],
        'bathrooms': [
            r'(?:bathrooms?|baths?|bathroom)\s+(?:is|are|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'bathrooms?:\s*(.+?)(?:\.|$|and|,)',
            # Order-independent: "2 bathrooms" or "bathrooms 2"
            r'(\d+)\s+bathrooms?',
            r'bathrooms?\s+(\d+)',
            r'(\d+)\s+bath',
            r'bath\s+(\d+)',
            r'(?:has|have)\s+(\d+)\s+bathrooms?',
        ],
        'area_sqft': [
            r'(?:area|size)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'area:\s*(.+?)(?:\.|$|and|,)',
            r'the\s+area\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
            r'its?\s+area\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
            # Order-independent: "2500 sqft" or "sqft 2500", also handle units
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:sqft|square\s+feet|sq\s+ft|marla|kanal|sq\s*yard|square\s*yard|sq\s*meter|square\s*meter|acre)',
            r'(?:sqft|square\s+feet|sq\s+ft|marla|kanal|sq\s*yard|square\s*yard|sq\s*meter|square\s*meter|acre)\s+(\d+(?:,\d+)*(?:\.\d+)?)',
        ],
        'city': [
            r'(?:city|location)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'(?:in|at|located in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'city:\s*(.+?)(?:\.|$|and|,)',
            r'the\s+city\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
            # Order-independent: "Islamabad city" or "city Islamabad"
            r'(Islamabad|Karachi|Lahore|Rawalpindi|Peshawar|Quetta|Faisalabad|Multan)\s+(?:city|location)',
            r'(?:city|location)\s+(Islamabad|Karachi|Lahore|Rawalpindi|Peshawar|Quetta|Faisalabad|Multan)',
            r'\b(Islamabad|Karachi|Lahore|Rawalpindi|Peshawar|Quetta|Faisalabad|Multan)\b',
        ],
        'area': [
            r'(?:area|sector|society)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'(?:in|at|located in)\s+([A-Z]\s*-\s*\d+(?:/\d+)?|DHA\s+Phase\s+\d+|Sector\s+[A-Z]?\s*\d+)',
            r'area:\s*(.+?)(?:\.|$|and|,)',
            r'the\s+(?:area|sector)\s+(?:is|should be|will be)\s+(.+?)(?:\.|$|and|,)',
            # Order-independent patterns: "g13 sector" or "sector g13"
            r'([A-Z]\s*\d+)\s+(?:sector|area)',
            r'(?:sector|area)\s+([A-Z]\s*\d+)',
            r'([A-Z]\s*-\s*\d+(?:/\d+)?)',
            r'(DHA\s+Phase\s+\d+)',
            r'(Sector\s+[A-Z]?\s*\d+)',
        ],
        'lng': [
            r'(?:longitude|lng)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'longitude:\s*(.+?)(?:\.|$|and|,)',
            r'lng:\s*(.+?)(?:\.|$|and|,)',
            r'(?:coordinates?|location)\s+(?:is|are|at)\s+([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)',  # "coordinates are 73.0479, 33.6844"
        ],
        'lat': [
            r'(?:latitude|lat)\s+(?:is|should be|will be|to|as)\s+(.+?)(?:\.|$|and|,)',
            r'latitude:\s*(.+?)(?:\.|$|and|,)',
            r'lat:\s*(.+?)(?:\.|$|and|,)',
        ],
    }
    
    # Special handling for coordinates (lng, lat together)
    coord_match = re.search(r'(?:coordinates?|location|gps)\s+(?:is|are|at)\s+([+-]?\d+\.?\d*)\s*[,;]\s*([+-]?\d+\.?\d*)', text_lower, re.IGNORECASE)
    if coord_match:
        lng_val = coord_match.group(1).strip()
        lat_val = coord_match.group(2).strip()
        result = {}
        try:
            lng_float = float(lng_val)
            lat_float = float(lat_val)
            # Validate ranges (Pakistan is roughly 60-75 lng, 24-37 lat)
            if 60 <= lng_float <= 75 and 24 <= lat_float <= 37:
                result['lng'] = str(lng_float)
                result['lat'] = str(lat_float)
                return result
        except (ValueError, TypeError):
            pass
    
    # Check patterns in order of specificity (more specific first)
    for field, patterns in update_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Extract the value - use group 1 if available, otherwise use the full match
                if match.groups():
                    value = match.group(1).strip()
                else:
                    # For patterns without groups, extract what comes after the field name
                    full_match = match.group(0)
                    # Try to extract the value part
                    if 'is' in full_match or 'are' in full_match or 'to' in full_match or 'as' in full_match:
                        parts = full_match.split()
                        # Find the field name index and get what comes after
                        field_keywords = {
                            'title': ['title', 'name'],
                            'description': ['description', 'details', 'detail'],
                            'price': ['price', 'cost'],
                            'property_type': ['type', 'property'],
                            'bedrooms': ['bedroom', 'bed', 'beds'],
                            'bathrooms': ['bathroom', 'bath', 'baths'],
                            'area_sqft': ['area', 'size'],
                            'city': ['city', 'location'],
                            'area': ['area', 'sector', 'society'],
                        }
                        value = None
                        for i, word in enumerate(parts):
                            if any(kw in word.lower() for kw in field_keywords.get(field, [])):
                                # Get everything after the field keyword
                                if i + 1 < len(parts):
                                    # Skip "is", "are", "to", "as"
                                    start_idx = i + 1
                                    if parts[start_idx] in ['is', 'are', 'to', 'as', 'should', 'will']:
                                        start_idx += 1
                                        if parts[start_idx] == 'be':
                                            start_idx += 1
                                    value = ' '.join(parts[start_idx:])
                                break
                        if not value:
                            value = full_match
                    else:
                        value = full_match
                
                # Clean the extracted value
                value = _clean_text(str(value)) if value else None
                if value and len(value) > 0:
                    # Remove the field name itself from the value if it appears
                    field_words = {
                        'title': ['title', 'name'],
                        'description': ['description', 'details'],
                        'price': ['price', 'cost'],
                        'property_type': ['type'],
                        'bedrooms': ['bedroom', 'bed'],
                        'bathrooms': ['bathroom', 'bath'],
                        'area_sqft': ['area', 'size'],
                        'city': ['city'],
                        'area': ['area', 'sector'],
                    }
                    for word in field_words.get(field, []):
                        value = re.sub(rf'\b{word}\b', '', value, flags=re.IGNORECASE).strip()
                    value = _clean_text(value)
                    if value and len(value) > 0:
                        return {field: value}
    
    return {}


class PropertyExtraction(BaseModel):
    """Structured output for property information extraction."""
    title: Optional[str] = Field(None, description="Property title or name (short, 5-10 words max, no filler words)")
    description: Optional[str] = Field(None, description="Property description (detailed text, 20+ words, no filler words)")
    price: Optional[float] = Field(None, description="Price in PKR (convert millions/lakhs/thousands to actual numbers)")
    property_type: Optional[str] = Field(None, description="Type: house, apartment, plot, commercial, villa, flat, etc.")
    area_sqft: Optional[float] = Field(None, description="Area in square feet")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")
    floors: Optional[int] = Field(None, description="Number of floors")
    city: Optional[str] = Field(None, description="City name (e.g., Islamabad, Karachi, Lahore)")
    area: Optional[str] = Field(None, description="Area/sector (e.g., F-10, DHA Phase 5, Sector G-11)")
    lng: Optional[float] = Field(None, description="Longitude coordinate")
    lat: Optional[float] = Field(None, description="Latitude coordinate")


def _extract_number(text: str) -> Optional[float]:
    """Extract a number from text, handling various formats."""
    if not text:
        return None
    
    # Remove commas and common currency symbols
    cleaned = re.sub(r'[,\s]', '', str(text))
    # Match numbers with optional decimals
    match = re.search(r'(\d+\.?\d*)', cleaned)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass
    return None


def _extract_integer(text: str) -> Optional[int]:
    """Extract an integer from text."""
    num = _extract_number(text)
    return int(num) if num is not None else None


def _convert_price_to_pkr(text: str) -> Optional[float]:
    """Convert price text to PKR, handling various units."""
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # Extract number
    num_match = re.search(r'(\d+(?:\.\d+)?)', text_lower)
    if not num_match:
        return None
    
    try:
        base_num = float(num_match.group(1))
    except (ValueError, TypeError):
        return None
    
    # Check for units
    if 'crore' in text_lower or 'cr' in text_lower:
        return base_num * 10000000
    elif 'million' in text_lower or 'm ' in text_lower or text_lower.endswith('m'):
        return base_num * 1000000
    elif 'lakh' in text_lower or 'lac' in text_lower or 'l ' in text_lower or text_lower.endswith('l'):
        return base_num * 100000
    elif 'thousand' in text_lower or 'k ' in text_lower or text_lower.endswith('k'):
        return base_num * 1000
    else:
        # Assume already in PKR
        return base_num


def _convert_area_to_sqft(text: str) -> Optional[float]:
    """Convert area text to square feet, handling various units."""
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # Extract number
    num_match = re.search(r'(\d+(?:\.\d+)?)', text_lower)
    if not num_match:
        return None
    
    try:
        base_num = float(num_match.group(1))
    except (ValueError, TypeError):
        return None
    
    # Check for units
    if 'kanal' in text_lower:
        return base_num * 5445  # 1 kanal = 5445 sqft
    elif 'marla' in text_lower:
        return base_num * 272.25  # 1 marla = 272.25 sqft
    elif 'acre' in text_lower:
        return base_num * 43560  # 1 acre = 43560 sqft
    elif 'sq yard' in text_lower or 'square yard' in text_lower or 'yard' in text_lower:
        return base_num * 9  # 1 sq yard = 9 sqft
    elif 'sq meter' in text_lower or 'square meter' in text_lower or 'sq m' in text_lower:
        return base_num * 10.764  # 1 sq meter = 10.764 sqft
    elif 'sqft' in text_lower or 'sq ft' in text_lower or 'square feet' in text_lower:
        return base_num  # Already in sqft
    else:
        # Assume square feet if no unit specified
        return base_num


def _improve_text_with_llm(text: str) -> str:
    """
    Use LLM to improve grammar, fix English, and clean up the text.
    This helps convert speech-to-text output into proper English.
    """
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
        
        # Extract the text from the response
        if hasattr(result, 'content'):
            improved = result.content.strip()
        elif isinstance(result, str):
            improved = result.strip()
        else:
            improved = str(result).strip()
        
        # Fallback to original if improvement failed or is too different
        if len(improved) < len(text) * 0.5:  # If too much was removed, use original
            return text
        
        return improved
    except Exception as e:
        logger.error(f"LLM text improvement failed: {e}, using original text")
        return text


def _extract_structured_property_info(text: str, current_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract property info using LLM for better accuracy.
    Uses current_data context to understand what's already filled.
    Can extract multiple fields at once.
    """
    if not text or len(text.strip()) < 5:
        return {}
    
    # Clean text first
    cleaned_text = _clean_text(text)
    if len(cleaned_text.strip()) < 5:
        return {}
    
    # Improve text with LLM for better grammar/English
    improved_text = _improve_text_with_llm(cleaned_text)
    
    # Check for field update intent first (faster) - but don't return early, allow multiple fields
    update_intent = _detect_field_update_intent(improved_text)
    # Don't return early - we want to extract ALL fields mentioned, not just one
    
    # Build context about current data
    current_context = ""
    if current_data:
        filled_fields = {k: v for k, v in current_data.items() if v is not None and k != "images"}
        if filled_fields:
            current_context = f"\n\nCurrent property data:\n{str(filled_fields)}\n\n"
            current_context += "If the user wants to UPDATE a field, extract the new value. "
            current_context += "If the user provides NEW information, extract it. "
            current_context += "Do NOT include filler words (uh, um, like, you know) in extracted values."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a property information extraction assistant. Extract structured property details from natural language.\n\n"
            "CRITICAL RULES:\n"
            "- Extract ALL fields mentioned in the text in a SINGLE pass, not just one\n"
            "- If user says '3 bedrooms, 2 bathrooms, price 15 million, area 5 marla' - extract ALL of them at once\n"
            "- Look for multiple field mentions in the same sentence or across sentences\n"
            "- Do NOT stop after extracting the first field - continue to extract all mentioned fields\n"
            "- NEVER include filler words, meta-text, or phrases like 'the description is', 'the title is', 'service title', etc.\n"
            "- title: Should be SHORT (5-10 words max), descriptive, professional (e.g., 'Beautiful 3-Bedroom House in F-10')\n"
            "  * Do NOT include phrases like 'the title is', 'service title is', 'title is' in the title\n"
            "  * If user says 'title is X', extract ONLY X, not 'title is X'\n"
            "- description: Should be DETAILED (20+ words), comprehensive property description\n"
            "  * Do NOT include phrases like 'the description is', 'description for this property is', 'the description' at the end\n"
            "  * Do NOT include phrases like 'description is', 'its description is', 'description for this property is'\n"
            "  * Extract ONLY the actual description content, not meta-text about descriptions\n"
            "  * If text contains 'description is X' or 'description for this property is X', extract ONLY X\n"
            "  * Remove any trailing text like 'the description' or 'description' from the end\n"
            "- price: CRITICAL - Convert units to PKR and return ONLY the numeric value (float):\n"
            "  * '15 million' or '15M' or '15 million rupees' -> 15000000.0\n"
            "  * '50 lakh' or '50L' or '50 lakh rupees' -> 5000000.0\n"
            "  * '2 crore' or '2Cr' or '2 crore rupees' -> 20000000.0\n"
            "  * '1.5 crore' -> 15000000.0\n"
            "  * '25 thousand' or '25K' -> 25000.0\n"
            "  * '5 million PKR' -> 5000000.0\n"
            "  * Extract the number and multiply by the unit. Return ONLY the number, not text.\n"
            "- area_sqft: Convert ALL area units to square feet:\n"
            "  * Marla: 1 marla = 272.25 sqft (e.g., '5 marla' -> 1361.25)\n"
            "  * Kanal: 1 kanal = 5445 sqft (e.g., '2 kanal' -> 10890)\n"
            "  * Square yards: 1 sq yard = 9 sqft (e.g., '100 sq yards' -> 900)\n"
            "  * Square meters: 1 sq meter = 10.764 sqft (e.g., '100 sq meters' -> 1076.4)\n"
            "  * Acres: 1 acre = 43560 sqft (e.g., '0.5 acres' -> 21780)\n"
            "  * If no unit specified, assume square feet\n"
            "- lng/lat: Extract coordinates in decimal format:\n"
            "  * 'longitude 73.0479' -> 73.0479\n"
            "  * 'coordinates are 73.0479, 33.6844' -> lng=73.0479, lat=33.6844\n"
            "  * 'lat 33.6844' -> 33.6844\n"
            "- property_type: Use lowercase (house, apartment, plot, commercial, villa, flat, penthouse, townhouse)\n"
            "- city: Use title case (Islamabad, Karachi, Lahore, Rawalpindi, Peshawar, Quetta, Faisalabad, Multan)\n"
            "- Only extract information that is EXPLICITLY mentioned\n"
            "- If user says 'change X to Y' or 'update X', extract the NEW value for X\n"
            "- Be precise with numbers and unit conversions\n"
            "- Remove all filler words and meta-phrases from text fields\n"
            "- For description: If text says 'description is X' or 'description for this property is X', extract ONLY X\n\n"
            "Extract the following if mentioned (can extract multiple at once):\n"
            "- title: Property title/name (short, professional, NO meta-text)\n"
            "- description: Detailed property description (NO phrases like 'the description is')\n"
            "- price: Price in PKR (convert all units to PKR)\n"
            "- property_type: Type (house, apartment, etc.)\n"
            "- area_sqft: Area in square feet (convert from marla, kanal, sq yards, sq meters, acres)\n"
            "- bedrooms: Number of bedrooms (integer)\n"
            "- bathrooms: Number of bathrooms (integer)\n"
            "- floors: Number of floors (integer)\n"
            "- city: City name\n"
            "- area: Area/sector (F-10, DHA Phase 5, etc.)\n"
            "- lng: Longitude coordinate (decimal format, e.g., 73.0479)\n"
            "- lat: Latitude coordinate (decimal format, e.g., 33.6844)"
        ) + current_context),
        ("human", "{text}")
    ])
    
    structured_llm = _extraction_llm.with_structured_output(PropertyExtraction)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"text": improved_text})
        extracted = result.model_dump(exclude_none=True)
        
        # Post-process price and area_sqft to ensure they are numbers and convert units if needed
        if 'price' in extracted and extracted['price'] is not None:
            price_val = extracted['price']
            # If it's a string, try to convert it
            if isinstance(price_val, str):
                converted = _convert_price_to_pkr(price_val)
                if converted is not None:
                    extracted['price'] = converted
                else:
                    # Try to extract number from string
                    num = _extract_number(price_val)
                    if num is not None:
                        extracted['price'] = num
            elif isinstance(price_val, (int, float)):
                # Already a number, ensure it's float
                extracted['price'] = float(price_val)
        
        if 'area_sqft' in extracted and extracted['area_sqft'] is not None:
            area_val = extracted['area_sqft']
            # If it's a string, try to convert it
            if isinstance(area_val, str):
                converted = _convert_area_to_sqft(area_val)
                if converted is not None:
                    extracted['area_sqft'] = converted
                else:
                    # Try to extract number from string
                    num = _extract_number(area_val)
                    if num is not None:
                        extracted['area_sqft'] = num
            elif isinstance(area_val, (int, float)):
                # Already a number, ensure it's float
                extracted['area_sqft'] = float(area_val)
        
        # Post-process to remove any remaining filler words and meta-phrases
        for key in ['title', 'description', 'area']:
            if key in extracted and extracted[key]:
                value = str(extracted[key])
                # Remove meta-phrases from beginning
                meta_phrases_start = [
                    r'^(the\s+title\s+is\s*)',
                    r'^(service\s+title\s+is\s*)',
                    r'^(title\s+is\s*)',
                    r'^(the\s+description\s+is\s*)',
                    r'^(description\s+for\s+this\s+property\s+is\s*)',
                    r'^(description\s+is\s*)',
                    r'^(its?\s+description\s+is\s*)',
                ]
                for phrase in meta_phrases_start:
                    value = re.sub(phrase, '', value, flags=re.IGNORECASE).strip()
                
                # Remove meta-phrases from end (especially for description)
                meta_phrases_end = [
                    r'(the\s+description\s*)$',
                    r'(description\s*)$',
                    r'(\.\s*the\s+description\s*)$',
                    r'(\.\s*description\s*)$',
                ]
                for phrase in meta_phrases_end:
                    value = re.sub(phrase, '', value, flags=re.IGNORECASE).strip()
                
                # Clean up any double spaces or trailing punctuation
                value = re.sub(r'\s+', ' ', value).strip(' ,.-')
                extracted[key] = _clean_text(value)
        
        # Merge with update_intent if any (for multiple field extraction)
        if update_intent:
            extracted.update(update_intent)
        
        logger.info(f"Extracted property info: {extracted}")
        return extracted
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}, falling back to regex")
        # Fallback to regex-based extraction
        return _extract_with_regex(cleaned_text)


def _extract_with_regex(text: str) -> Dict[str, Any]:
    """Fallback regex-based extraction if LLM fails."""
    extracted: Dict[str, Any] = {}
    text_lower = text.lower()
    
    # Price extraction with better patterns - order-independent and unit conversion
    price_patterns = [
        # Order-independent: "15 million" or "million 15", "15M price" or "price 15M"
        r"(\d+(?:\.\d+)?)\s*(?:million|m)\s*(?:rupees?|pkr|rs\.?)?\s*(?:price|cost)?",
        r"(?:million|m)\s+(\d+(?:\.\d+)?)\s*(?:rupees?|pkr|rs\.?)?\s*(?:price|cost)?",
        r"(?:price|cost)\s+(\d+(?:\.\d+)?)\s*(?:million|m)\s*(?:rupees?|pkr|rs\.?)?",
        r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)\s*(?:rupees?|pkr|rs\.?)?\s*(?:price|cost)?",
        r"(?:lakh|lac|l)\s+(\d+(?:\.\d+)?)\s*(?:rupees?|pkr|rs\.?)?\s*(?:price|cost)?",
        r"(?:price|cost)\s+(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)\s*(?:rupees?|pkr|rs\.?)?",
        r"(\d+(?:\.\d+)?)\s*(?:crore|cr)\s*(?:rupees?|pkr|rs\.?)?\s*(?:price|cost)?",
        r"(?:crore|cr)\s+(\d+(?:\.\d+)?)\s*(?:rupees?|pkr|rs\.?)?\s*(?:price|cost)?",
        r"(?:price|cost)\s+(\d+(?:\.\d+)?)\s*(?:crore|cr)\s*(?:rupees?|pkr|rs\.?)?",
        r"(?:price|cost|rs\.?|pkr)\s*:?\s*(\d+(?:,\d+)*(?:\.\d+)?)",
        r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rupees?|pkr|rs\.?)\s*(?:price|cost)?",
    ]
    for pattern in price_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                price = float(match.group(1).replace(',', ''))
                match_text = match.group(0).lower()
                if 'million' in match_text or ('m ' in match_text and 'm ' not in 'marla'):
                    price *= 1000000
                elif 'lakh' in match_text or 'lac' in match_text or ('l ' in match_text and 'l ' not in 'lng'):
                    price *= 100000
                elif 'crore' in match_text or 'cr' in match_text:
                    price *= 10000000
                elif 'thousand' in match_text or 'k ' in match_text:
                    price *= 1000
                extracted["price"] = price
                break
            except (ValueError, TypeError):
                pass
    
    # Property type
    property_types = ['house', 'apartment', 'plot', 'commercial', 'villa', 'flat', 'penthouse', 'townhouse']
    for prop_type in property_types:
        if prop_type in text_lower:
            extracted["property_type"] = prop_type
            break
    
    # Bedrooms - order-independent
    bed_patterns = [
        r"(\d+)\s*(?:bed|bedroom|beds|br|beds?)",
        r"(?:bed|bedroom|beds|br|beds?)\s+(\d+)",
    ]
    for pattern in bed_patterns:
        bed_match = re.search(pattern, text_lower)
        if bed_match:
            try:
                extracted["bedrooms"] = int(bed_match.group(1))
                break
            except (ValueError, TypeError):
                pass
    
    # Bathrooms - order-independent
    bath_patterns = [
        r"(\d+)\s*(?:bath|bathroom|baths|bathrooms?)",
        r"(?:bath|bathroom|baths|bathrooms?)\s+(\d+)",
    ]
    for pattern in bath_patterns:
        bath_match = re.search(pattern, text_lower)
        if bath_match:
            try:
                extracted["bathrooms"] = int(bath_match.group(1))
                break
            except (ValueError, TypeError):
                pass
    
    # Area (sqft) - with unit conversion
    area_patterns = [
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:kanal)", 5445),  # 1 kanal = 5445 sqft
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:marla)", 272.25),  # 1 marla = 272.25 sqft
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:sq\s*yard|square\s*yard)", 9),  # 1 sq yard = 9 sqft
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:sq\s*meter|square\s*meter|sq\s*m)", 10.764),  # 1 sq meter = 10.764 sqft
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:acre)", 43560),  # 1 acre = 43560 sqft
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:sqft|square\s+feet|sq\s+ft)", 1),  # Already in sqft
    ]
    for pattern, multiplier in area_patterns:
        area_match = re.search(pattern, text_lower)
        if area_match:
            try:
                base_num = float(area_match.group(1).replace(',', ''))
                extracted["area_sqft"] = base_num * multiplier
                break
            except (ValueError, TypeError):
                pass
    
    # City
    cities = ['islamabad', 'karachi', 'lahore', 'rawalpindi', 'peshawar', 'quetta', 'faisalabad', 'multan']
    for city in cities:
        if city in text_lower:
            extracted["city"] = city.title()
            break
    
    # Area/sector - order-independent patterns
    area_patterns = [
        r"([A-Z]\s*-\s*\d+(?:/\d+)?)",  # F-10, F-10/3
        r"(DHA\s+Phase\s+\d+)",  # DHA Phase 5
        r"(Sector\s+[A-Z]?\s*\d+)",  # Sector G-11, Sector 13
        r"([A-Z]\s*\d+)\s+(?:sector|area)",  # G13 sector, F10 area
        r"(?:sector|area)\s+([A-Z]\s*\d+)",  # sector G13, area F10
        r"([A-Z]\d+)",  # G13, F10 (simple pattern)
        r"(Gulberg|Bahria|Model\s+Town)",  # Named areas
    ]
    for pattern in area_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted["area"] = match.group(1).strip()
            break
    
    # Coordinates (longitude, latitude)
    coord_patterns = [
        r"(?:coordinates?|location|gps)\s+(?:is|are|at)\s+([+-]?\d+\.?\d*)\s*[,;]\s*([+-]?\d+\.?\d*)",
        r"longitude\s+(?:is|:)?\s*([+-]?\d+\.?\d*)",
        r"latitude\s+(?:is|:)?\s*([+-]?\d+\.?\d*)",
        r"lng\s+(?:is|:)?\s*([+-]?\d+\.?\d*)",
        r"lat\s+(?:is|:)?\s*([+-]?\d+\.?\d*)",
    ]
    for pattern in coord_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            try:
                if len(match.groups()) == 2:  # Both lng and lat
                    lng_val = float(match.group(1))
                    lat_val = float(match.group(2))
                    if 60 <= lng_val <= 75 and 24 <= lat_val <= 37:  # Pakistan bounds
                        extracted["lng"] = lng_val
                        extracted["lat"] = lat_val
                        break
                elif 'longitude' in match.group(0) or 'lng' in match.group(0):
                    lng_val = float(match.group(1))
                    if 60 <= lng_val <= 75:
                        extracted["lng"] = lng_val
                elif 'latitude' in match.group(0) or 'lat' in match.group(0):
                    lat_val = float(match.group(1))
                    if 24 <= lat_val <= 37:
                        extracted["lat"] = lat_val
            except (ValueError, TypeError):
                pass
    
    return extracted


def _update_property_data_from_text(text: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply heuristics to pull property info out of arbitrary text.
    Supports both new field extraction and field updates.
    Returns a dict of only the fields that were actually updated: {field_name: new_value}
    """
    if not text:
        return {}
    
    # Clean text first
    cleaned_text = _clean_text(text)
    if not cleaned_text or len(cleaned_text.strip()) < 5:
        return {}
    
    updated_fields: Dict[str, Any] = {}
    
    # Check for explicit field update intent first
    update_intent = _detect_field_update_intent(cleaned_text)
    if update_intent:
        for field, new_value in update_intent.items():
            if new_value:
                old_value = data.get(field)
                # Handle different field types
                if field in ["bedrooms", "bathrooms", "floors"]:
                    try:
                        num = _extract_integer(new_value)
                        if num is not None and num != old_value:
                            data[field] = num
                            updated_fields[field] = num
                    except (ValueError, TypeError):
                        pass
                elif field == "price":
                    try:
                        # Try conversion first (handles units like million, lakh, etc.)
                        converted = _convert_price_to_pkr(new_value)
                        if converted is not None and converted != old_value:
                            data[field] = converted
                            updated_fields[field] = converted
                        else:
                            # Fallback to direct number extraction
                            num = _extract_number(new_value)
                            if num is not None and float(num) != old_value:
                                data[field] = float(num)
                                updated_fields[field] = float(num)
                    except (ValueError, TypeError):
                        pass
                elif field == "area_sqft":
                    try:
                        # Try conversion first (handles units like marla, kanal, etc.)
                        converted = _convert_area_to_sqft(new_value)
                        if converted is not None and converted != old_value:
                            data[field] = converted
                            updated_fields[field] = converted
                        else:
                            # Fallback to direct number extraction
                            num = _extract_number(new_value)
                            if num is not None and float(num) != old_value:
                                data[field] = float(num)
                                updated_fields[field] = float(num)
                    except (ValueError, TypeError):
                        pass
                elif field in ["lng", "lat"]:
                    try:
                        num = _extract_number(new_value)
                        if num is not None and float(num) != old_value:
                            data[field] = float(num)
                            updated_fields[field] = float(num)
                    except (ValueError, TypeError):
                        pass
                else:
                    # String fields
                    cleaned_value = _clean_text(new_value)
                    if cleaned_value and cleaned_value != old_value:
                        data[field] = cleaned_value
                        updated_fields[field] = cleaned_value
        if updated_fields:
            return updated_fields
    
    # Use LLM extraction with current data context
    structured = _extract_structured_property_info(cleaned_text, current_data=data)
    
    for key, value in structured.items():
        if value is not None:
            old_value = data.get(key)
            # CRITICAL: Preserve existing fields unless explicitly updated
            # Only update if:
            # 1. Field is empty/null (new field)
            # 2. User explicitly mentioned updating this field (update_intent)
            # 3. User used update keywords (change, update, set, modify, edit)
            should_update = False
            
            # Always update if field is empty
            if not old_value or old_value == '' or old_value == 0:
                should_update = True
            # Update if explicitly mentioned in update_intent
            elif key in update_intent:
                should_update = True
            # Update if user used update keywords AND mentioned this field
            elif any(update_key in cleaned_text.lower() for update_key in ['change', 'update', 'set', 'modify', 'edit']):
                # Check if this specific field was mentioned in the text
                field_keywords = {
                    'title': ['title', 'name'],
                    'description': ['description', 'details', 'detail'],
                    'price': ['price', 'cost'],
                    'property_type': ['type', 'property type'],
                    'area_sqft': ['area', 'size', 'square feet', 'sqft'],
                    'bedrooms': ['bedroom', 'bed'],
                    'bathrooms': ['bathroom', 'bath'],
                    'city': ['city'],
                    'area': ['area', 'sector', 'location'],
                    'lng': ['longitude', 'lng'],
                    'lat': ['latitude', 'lat'],
                }
                keywords = field_keywords.get(key, [])
                if any(kw in cleaned_text.lower() for kw in keywords):
                    should_update = True
            
            if should_update:
                new_val = None
                if key in ["bedrooms", "bathrooms", "floors"]:
                    try:
                        new_val = int(value)
                        if new_val != old_value:
                            data[key] = new_val
                            updated_fields[key] = new_val
                    except (ValueError, TypeError):
                        continue
                elif key == "price":
                    try:
                        # If value is a string, try conversion
                        if isinstance(value, str):
                            converted = _convert_price_to_pkr(value)
                            if converted is not None:
                                new_val = converted
                            else:
                                new_val = float(value)
                        else:
                            new_val = float(value)
                        if new_val != old_value:
                            data[key] = new_val
                            updated_fields[key] = new_val
                    except (ValueError, TypeError):
                        continue
                elif key == "area_sqft":
                    try:
                        # If value is a string, try conversion
                        if isinstance(value, str):
                            converted = _convert_area_to_sqft(value)
                            if converted is not None:
                                new_val = converted
                            else:
                                new_val = float(value)
                        else:
                            new_val = float(value)
                        if new_val != old_value:
                            data[key] = new_val
                            updated_fields[key] = new_val
                    except (ValueError, TypeError):
                        continue
                elif key in ["lng", "lat"]:
                    try:
                        new_val = float(value)
                        if new_val != old_value:
                            data[key] = new_val
                            updated_fields[key] = new_val
                    except (ValueError, TypeError):
                        continue
                else:
                    # String fields - clean them
                    cleaned_value = _clean_text(str(value))
                    if cleaned_value and cleaned_value != old_value:
                        data[key] = cleaned_value
                        updated_fields[key] = cleaned_value
    
    # Additional heuristics for title and description - be very careful
    # Only set title if it's clearly a short, descriptive title
    # Only set description if it's substantial descriptive text
    
    # Title should be short and specific - avoid if it looks like a full description
    # CRITICAL: Only set title if it's empty - preserve existing title
    if (not data.get("title") or data.get("title") == '') and len(cleaned_text) > 10:
        # Look for a short, specific title pattern (not a full description)
        # Title should be 5-60 characters, not too long
        sentences = cleaned_text.split('.')
        first_sentence = sentences[0].strip() if sentences else ""
        
        # Only use as title if:
        # 1. It's reasonably short (5-60 chars)
        # 2. It contains property-related keywords (bedroom, house, apartment, etc.)
        # 3. It doesn't look like a full description
        if 5 <= len(first_sentence) <= 60:
            property_keywords = ['bedroom', 'bathroom', 'house', 'apartment', 'villa', 'flat', 
                               'plot', 'commercial', 'property', 'room', 'sqft', 'area']
            has_property_keyword = any(kw in first_sentence.lower() for kw in property_keywords)
            
            # Don't use if it contains description-like phrases
            description_phrases = ['description is', 'it is', 'it has', 'this property', 
                                 'the property', 'located in', 'features']
            has_description_phrase = any(phrase in first_sentence.lower() for phrase in description_phrases)
            
            if has_property_keyword and not has_description_phrase:
                potential_title = _clean_text(first_sentence)
                if potential_title and not any(filler in potential_title.lower() for filler in FILLER_WORDS):
                    if potential_title != data.get("title"):
                        data["title"] = potential_title
                        updated_fields["title"] = potential_title
    
    # Description should be substantial text (50+ chars) and not already set
    # CRITICAL: Only set description if it's empty - preserve existing description
    # Only set if it doesn't contain meta-phrases or look like a title
    if (not data.get("description") or data.get("description") == '') and len(cleaned_text) > 50:
        # Check for meta-phrases that indicate this is NOT a description
        meta_indicators = [
            'the description is', 'description for this property is', 'description is',
            'the service title is', 'service title is', 'the title is',
            'its description is', 'its title is'
        ]
        has_meta_indicator = any(indicator in cleaned_text.lower() for indicator in meta_indicators)
        
        # Only use as description if:
        # 1. It's substantial (50+ chars)
        # 2. Doesn't have meta-indicators
        # 3. Doesn't look like just a title (not too short with property keywords)
        if (len(cleaned_text) > 50 and 
            not has_meta_indicator and
            not (len(cleaned_text) < 100 and 'bedroom' in cleaned_text.lower() and 'apartment' in cleaned_text.lower())):
            cleaned_desc = _clean_text(cleaned_text)
            # Remove any trailing meta-phrases
            for phrase in ['the description', 'description']:
                if cleaned_desc.lower().endswith(phrase):
                    cleaned_desc = cleaned_desc[:-len(phrase)].strip()
            if cleaned_desc and len(cleaned_desc) > 50:
                if cleaned_desc != data.get("description"):
                    data["description"] = cleaned_desc
                    updated_fields["description"] = cleaned_desc
    
    return updated_fields


def _generate_description_with_llm(property_data: Dict[str, Any]) -> str:
    """
    Generate a property description using LLM based on all available property details.
    """
    # Build context from property data
    details = []
    if property_data.get("title"):
        details.append(f"Title: {property_data['title']}")
    if property_data.get("property_type"):
        details.append(f"Type: {property_data['property_type']}")
    if property_data.get("bedrooms"):
        details.append(f"Bedrooms: {property_data['bedrooms']}")
    if property_data.get("bathrooms"):
        details.append(f"Bathrooms: {property_data['bathrooms']}")
    if property_data.get("floors"):
        details.append(f"Floors: {property_data['floors']}")
    if property_data.get("area_sqft"):
        details.append(f"Area: {property_data['area_sqft']} sqft")
    if property_data.get("price"):
        details.append(f"Price: PKR {property_data['price']:,}")
    if property_data.get("city"):
        details.append(f"City: {property_data['city']}")
    if property_data.get("area"):
        details.append(f"Location: {property_data['area']}")
    
    existing_description = property_data.get("description", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a professional property description writer. "
            "Generate a compelling, detailed property description based on the provided details.\n\n"
            "Guidelines:\n"
            "1. Write in a professional, engaging tone\n"
            "2. Highlight key features and selling points\n"
            "3. Include all relevant details provided\n"
            "4. Make it appealing to potential buyers\n"
            "5. Keep it between 100-200 words\n"
            "6. If an existing description is provided, enhance it with the new details\n"
            "7. Use proper grammar and professional language\n"
            "8. Focus on benefits and features\n\n"
            "Return ONLY the description text, nothing else."
        )),
        ("human", (
            f"Property Details:\n" + "\n".join(details) + 
            (f"\n\nExisting Description:\n{existing_description}" if existing_description else "") +
            "\n\nGenerate a professional property description:"
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
        
        # Fallback if generation fails
        if not description or len(description) < 50:
            description = (
                f"This {property_data.get('property_type', 'property')} "
                f"features {property_data.get('bedrooms', 'N/A')} bedrooms and "
                f"{property_data.get('bathrooms', 'N/A')} bathrooms. "
                f"Located in {property_data.get('city', 'the city')}, "
                f"{property_data.get('area', '')}. "
                f"Total area: {property_data.get('area_sqft', 'N/A')} sqft. "
                f"Price: PKR {property_data.get('price', 'N/A'):,}."
            )
        
        return description
    except Exception as e:
        logger.error(f"LLM description generation failed: {e}")
        # Return a basic description as fallback
        return (
            f"This {property_data.get('property_type', 'property')} "
            f"features {property_data.get('bedrooms', 'N/A')} bedrooms and "
            f"{property_data.get('bathrooms', 'N/A')} bathrooms. "
            f"Located in {property_data.get('city', 'the city')}, "
            f"{property_data.get('area', '')}. "
            f"Total area: {property_data.get('area_sqft', 'N/A')} sqft. "
            f"Price: PKR {property_data.get('price', 'N/A'):,}."
        )


def _format_missing_prompt(missing: List[str]) -> str:
    """Format a user-friendly prompt for missing fields."""
    labels = {
        "title": "property title",
        "description": "property description",
        "price": "price",
        "property_type": "property type (house, apartment, plot, etc.)",
        "area_sqft": "area in square feet",
        "bedrooms": "number of bedrooms",
        "bathrooms": "number of bathrooms",
        "city": "city",
        "area": "area/sector (e.g., F-10, DHA Phase 5)",
        "lng": "longitude",
        "lat": "latitude",
    }
    readable = [labels[m] for m in missing if m in labels]
    if len(readable) == 1:
        fields = readable[0]
    elif len(readable) == 2:
        fields = f"{readable[0]} and {readable[1]}"
    else:
        fields = ", ".join(readable[:-1]) + f", and {readable[-1]}"
    return f"I still need the following details: {fields}. Please share them. You can also update any existing field by saying 'change [field] to [value]'."


class PropertyListingCreationAgent:
    """Deterministic agent for property listing creation."""

    REQUIRED_FIELDS = [
        "title", "description", "price", "property_type", "area_sqft",
        "bedrooms", "bathrooms", "city", "area", "lng", "lat"
    ]

    def process_query(self, query: str, clerk_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "response": "Property listing creation runs in interactive mode. Please use the chat interface.",
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

        property_data: Dict[str, Any] = {
            "title": None,
            "description": None,
            "price": None,
            "property_type": None,
            "area_sqft": None,
            "bedrooms": None,
            "bathrooms": None,
            "floors": 1,  # Default
            "city": None,
            "area": None,
            "lng": None,
            "lat": None,
            "images": [],
        }

        # Clean and accumulate text for processing
        accumulated_text = _clean_text(query.strip())
        if accumulated_text:
            initial_updates = _update_property_data_from_text(accumulated_text, property_data)
            # Send initial updates if any
            if initial_updates:
                await send({
                    "type": "field_update",
                    "updates": initial_updates,  # Only send updated fields
                    "status": "continue"
                })

        greeting_sent = False

        while True:
            missing = [field for field in self.REQUIRED_FIELDS if not property_data.get(field)]

            if missing:
                if not greeting_sent:
                    message = (
                        "I'll help you create your property listing! "
                        "Please share details like title, description, price, property type, area, "
                        "bedrooms, bathrooms, city, location area, and coordinates. "
                        "You can update any field later by saying 'change [field] to [value]'."
                    )
                    greeting_sent = True
                else:
                    message = _format_missing_prompt(missing)

                # Send missing fields info (no data update if nothing changed)
                await send({
                    "type": "field_update",
                    "missing_fields": missing,
                    "message": message,
                    "status": "continue"
                })
                
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
                
                if any(keyword in user_input_lower for keyword in cancel_keywords):
                    cancel_msg = "No problem. I've cancelled the property listing creation process."
                    await send({"type": "agent", "message": cancel_msg, "status": "cancelled"})
                    return {"success": False, "response": cancel_msg, "status": "cancelled"}

                # Clean and accumulate text for better extraction
                cleaned_input = _clean_text(user_input)
                if cleaned_input:
                    accumulated_text += " " + cleaned_input
                
                # Show processing indicator
                await send({
                    "type": "processing",
                    "message": "Processing your input...",
                    "status": "processing"
                })
                
                # Update property data and get only the fields that changed
                updated_fields = {}
                if cleaned_input:
                    updated_fields = _update_property_data_from_text(accumulated_text, property_data)
                
                if updated_fields:
                    # Send ALL updated fields together in one message (no delay)
                    await send({
                        "type": "field_update",
                        "updates": updated_fields,  # All changed fields sent together
                        "missing_fields": [field for field in self.REQUIRED_FIELDS if not property_data.get(field)],
                        "status": "continue"
                    })
                elif cleaned_input:
                    # Couldn't extract, but input was provided
                    await send({
                        "type": "agent",
                        "message": "I didn't catch those details clearly. Could you rephrase or provide them again?",
                        "status": "continue",
                    })
                continue

            # All required fields are present, create the property
            # For coordinates, if not provided, we could use a geocoding service
            # For now, we'll require them or set defaults (0, 0) - but this should be improved
            if property_data.get("lng") is None:
                property_data["lng"] = 0.0
            if property_data.get("lat") is None:
                property_data["lat"] = 0.0

            tool_result = create_property_sync(
                clerk_id=clerk_id,
                title=property_data["title"],
                description=property_data["description"],
                price=property_data["price"],
                property_type=property_data["property_type"],
                area_sqft=property_data["area_sqft"],
                bedrooms=property_data["bedrooms"],
                bathrooms=property_data["bathrooms"],
                floors=property_data.get("floors", 1),
                city=property_data["city"],
                area=property_data["area"],
                lng=property_data["lng"],
                lat=property_data["lat"],
                images=property_data.get("images", []),
            )
            
            message = tool_result.get("message", "Property listing created successfully!")
            property_id = tool_result.get("property_id")
            
            await send({
                "type": "completed",
                "success": tool_result.get("success", True),
                "message": message,
                "property_id": property_id
            })
            
            return {
                "success": tool_result.get("success", True),
                "response": message,
                "status": "completed" if tool_result.get("success", True) else "failed",
                "error": tool_result.get("error", None),
                "property_id": property_id,
            }
