"""
Filter extraction utility for property searches.
Uses LLM to extract structured filters from natural language queries.
Supports amenity-aware queries (generic amenity type, specific named POI, distance constraints).
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM for filter extraction
_filter_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)


class PropertyFilters(BaseModel):
    """Filters for property searches."""
    city: Optional[str] = Field(None, description="City name (e.g., 'Islamabad', 'Karachi', 'Lahore', 'Rawalpindi')")
    area: Optional[str] = Field(None, description="Area/sector/locality (e.g., 'F-10', 'DHA Phase 5', 'Gulberg')")
    property_type: Optional[str] = Field(None, description="Property type (house, apartment, plot, commercial, villa, flat, penthouse)")
    price_min: Optional[float] = Field(None, description="Minimum price in PKR")
    price_max: Optional[float] = Field(None, description="Maximum price in PKR")
    bedrooms_min: Optional[int] = Field(None, description="Minimum number of bedrooms")
    bedrooms_max: Optional[int] = Field(None, description="Maximum number of bedrooms")
    bathrooms_min: Optional[int] = Field(None, description="Minimum number of bathrooms")
    bathrooms_max: Optional[int] = Field(None, description="Maximum number of bathrooms")
    area_sqft_min: Optional[float] = Field(None, description="Minimum area in square feet")
    area_sqft_max: Optional[float] = Field(None, description="Maximum area in square feet")

    # Amenity-aware fields
    amenity_query_type: Optional[str] = Field(
        None,
        description=(
            "Type of amenity requirement. One of: "
            "'generic' (e.g., 'near a school'), "
            "'specific_poi' (e.g., 'near Beaconhouse school', 'near Fast University', 'under 10km of FAST'), "
            "'workplace' (e.g., '10km from my office at Blue Area'), "
            "or null if no amenity/POI mentioned. IMPORTANT: If the user refers to a specific name or specific distance constraint in km/miles, ALWAYS select 'specific_poi' or 'workplace' instead of generic."
        ),
    )
    poi_name: Optional[str] = Field(
        None,
        description=(
            "The specific place/POI name mentioned by the user. "
            "Examples: 'Centaurus Mall', 'Beaconhouse school', 'Shifa Hospital', 'FAST University'. "
            "Only set when amenity_query_type is 'specific_poi' or 'workplace'."
        ),
    )
    distance_km: Optional[float] = Field(
        None,
        description=(
            "Maximum distance in kilometers from the specified POI. "
            "Examples: 'under 10km' -> 10, 'within 5km' -> 5, 'nearby' -> 3. "
            "Default to 5 if a POI is mentioned but no distance is specified."
        ),
    )


def extract_property_filters(query: str) -> Dict[str, Any]:
    """
    Extract structured filters from a natural language query for property searches.
    
    Args:
        query: User's natural language query
        
    Returns:
        Dictionary of extracted filters (city, price_min, price_max, bedrooms, etc.)
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a filter extraction assistant for property searches. Extract structured filters from user queries.\n\n"
            "Extract the following information if mentioned:\n"
            "- city: City name (Islamabad, Karachi, Lahore, Rawalpindi, Peshawar, Quetta, Faisalabad, Multan, etc.)\n"
            "- area: Area/sector/locality (F-10, DHA Phase 5, Gulberg, Bahria Town, etc.)\n"
            "- property_type: Type of property (house, apartment, plot, commercial, villa, flat, penthouse, townhouse)\n"
            "  * Map common terms: 'home' -> 'house', 'flat' -> 'apartment', 'land' -> 'plot'\n"
            "  * Convert units:\n"
            "    - 1 crore = 10000000 (7 zeros)\n"
            "    - 2 crore = 20000000\n"
            "    - 4 crore = 40000000\n"
            "    - 10 crore = 100000000\n"
            "    - 50 lakh = 5000000\n"
            "    - 1 million = 1000000\n"
            "  * IMPORTANT: If user mentions a single price like 'around 1 crore' or 'about 50 lakh':\n"
            "    - Set price_min to 90% of that value\n"
            "    - Set price_max to 110% of that value\n"
            "    - Example: 'around 1 crore' -> price_min=9000000, price_max=11000000\n"
            "  * 'under 50 lakh' -> price_max=5000000\n"
            "  * 'above 1 crore' or 'more than 1 crore' -> price_min=10000000\n"
            "  * 'between 50 lakh and 1 crore' -> price_min=5000000, price_max=10000000\n"
            "- bedrooms_min/bedrooms_max: Number of bedrooms\n"
            "  * '3 bedroom' -> bedrooms_min=3, bedrooms_max=3\n"
            "  * '3+ bedrooms' or 'at least 3 bedrooms' -> bedrooms_min=3\n"
            "  * '2-4 bedrooms' -> bedrooms_min=2, bedrooms_max=4\n"
            "- bathrooms_min/bathrooms_max: Number of bathrooms (same logic as bedrooms)\n"
            "- area_sqft_min/area_sqft_max: Area in square feet\n"
            "  * Convert units: 1 marla = 272 sqft, 1 kanal = 5445 sqft, 1 acre = 43560 sqft\n"
            "  * '5 marla' -> area_sqft_min=1360, area_sqft_max=1360\n"
            "  * '5-10 marla' -> area_sqft_min=1360, area_sqft_max=2720\n"
            "  * '1 kanal' -> area_sqft_min=5445, area_sqft_max=5445\n\n"
            "AMENITY / POI EXTRACTION:\n"
            "- amenity_query_type: Classify the user's intent:\n"
            "  * 'generic' — user mentions a TYPE of amenity without a specific name. E.g., 'near a good school', 'close to hospitals'\n"
            "  * 'specific_poi' — user mentions a SPECIFIC named place. E.g., 'near Centaurus Mall', 'close to Beaconhouse', 'near Shifa Hospital'\n"
            "  * 'workplace' — user mentions their workplace or office. E.g., '10km from my office at Blue Area', 'near where I work at PIMS'\n"
            "  * null — no amenity or POI mentioned\n"
            "- poi_name: The specific place or organization name (only for 'specific_poi' or 'workplace')\n"
            "- distance_km: Distance in km from the named POI. 'under 10km' -> 10. Default 5 if POI is mentioned but no distance given.\n\n"
            "If a filter is not mentioned, set it to null. Be precise and only extract what is explicitly stated or clearly implied."
        )),
        ("human", "{query}")
    ])
    
    structured_llm = _filter_llm.with_structured_output(PropertyFilters)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"query": query})
        filters = {}
        
        if result.city:
            # Normalize city name (capitalize first letter of each word)
            filters["city"] = result.city.strip().title()
        if result.area:
            filters["area"] = result.area.strip()
        if result.property_type:
            # Normalize property type to lowercase
            filters["property_type"] = result.property_type.strip().lower()
        if result.price_min is not None:
            filters["price_min"] = result.price_min
        if result.price_max is not None:
            filters["price_max"] = result.price_max
        if result.bedrooms_min is not None:
            filters["bedrooms_min"] = result.bedrooms_min
        if result.bedrooms_max is not None:
            filters["bedrooms_max"] = result.bedrooms_max
        if result.bathrooms_min is not None:
            filters["bathrooms_min"] = result.bathrooms_min
        if result.bathrooms_max is not None:
            filters["bathrooms_max"] = result.bathrooms_max
        if result.area_sqft_min is not None:
            filters["area_sqft_min"] = result.area_sqft_min
        if result.area_sqft_max is not None:
            filters["area_sqft_max"] = result.area_sqft_max

        # Amenity / POI fields
        if result.amenity_query_type:
            filters["amenity_query_type"] = result.amenity_query_type.strip().lower()
        if result.poi_name:
            filters["poi_name"] = result.poi_name.strip()
        if result.distance_km is not None:
            filters["distance_km"] = result.distance_km
            
        print(f"[DEBUG] Extracted property filters: {filters}")
        return filters
    except Exception as e:
        # If extraction fails, return empty filters (search will proceed without filters)
        print(f"Property filter extraction error (continuing without filters): {e}")
        return {}
