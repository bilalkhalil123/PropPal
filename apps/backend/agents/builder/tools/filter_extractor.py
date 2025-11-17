"""
Filter extraction utility for builder and service searches.
Uses LLM to extract structured filters from natural language queries.
"""

import os
from typing import Dict, Any, Optional
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


class BuilderFilters(BaseModel):
    """Filters for builder profile searches."""
    city: Optional[str] = Field(None, description="City name (e.g., 'Islamabad', 'Karachi', 'Lahore')")
    experience_years_min: Optional[int] = Field(None, description="Minimum years of experience")
    experience_years_max: Optional[int] = Field(None, description="Maximum years of experience")
    specialization: Optional[list[str]] = Field(None, description="List of specializations (e.g., ['residential', 'commercial'])")
    rating_min: Optional[float] = Field(None, description="Minimum rating (0-5)")


class ServiceFilters(BaseModel):
    """Filters for builder service searches."""
    city: Optional[str] = Field(None, description="City name where the builder operates")
    category: Optional[str] = Field(None, description="Service category (e.g., 'plumbing', 'electrical', 'interior design')")
    price_min: Optional[float] = Field(None, description="Minimum price")
    price_max: Optional[float] = Field(None, description="Maximum price")
    base_price_min: Optional[float] = Field(None, description="Minimum base price")
    base_price_max: Optional[float] = Field(None, description="Maximum base price")
    estimated_duration: Optional[str] = Field(None, description="Estimated duration (e.g., '2 hours', '1 day', '1 week')")


def extract_builder_filters(query: str) -> Dict[str, Any]:
    """
    Extract structured filters from a natural language query for builder searches.
    
    Args:
        query: User's natural language query
        
    Returns:
        Dictionary of extracted filters (city, experience_years_min, etc.)
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a filter extraction assistant. Extract structured filters from user queries about builders.\n\n"
            "Extract the following information if mentioned:\n"
            "- city: City name (Islamabad, Karachi, Lahore, Rawalpindi, etc.)\n"
            "- experience_years_min: Minimum years of experience (e.g., '5 years' -> 5, 'more than 10 years' -> 10)\n"
            "- experience_years_max: Maximum years of experience\n"
            "- specialization: List of specializations mentioned (residential, commercial, infrastructure, etc.)\n"
            "- rating_min: Minimum rating if mentioned\n\n"
            "If a filter is not mentioned, set it to null. Be precise and only extract what is explicitly stated."
        )),
        ("human", "{query}")
    ])
    
    structured_llm = _filter_llm.with_structured_output(BuilderFilters)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"query": query})
        filters = {}
        
        if result.city:
            filters["city"] = result.city.strip()
        if result.experience_years_min is not None:
            filters["experience_years_min"] = result.experience_years_min
        if result.experience_years_max is not None:
            filters["experience_years_max"] = result.experience_years_max
        if result.specialization:
            filters["specialization"] = result.specialization
        if result.rating_min is not None:
            filters["rating_min"] = result.rating_min
            
        return filters
    except Exception as e:
        # If extraction fails, return empty filters (search will proceed without filters)
        print(f"Filter extraction error (continuing without filters): {e}")
        return {}


def extract_service_filters(query: str) -> Dict[str, Any]:
    """
    Extract structured filters from a natural language query for service searches.
    
    Args:
        query: User's natural language query
        
    Returns:
        Dictionary of extracted filters (city, category, price ranges, etc.)
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a filter extraction assistant. Extract structured filters from user queries about builder services.\n\n"
            "Extract the following information if mentioned:\n"
            "- city: City name where the builder operates (Islamabad, Karachi, Lahore, etc.)\n"
            "- category: Service category (plumbing, electrical, interior design, construction, renovation, etc.)\n"
            "- price_min: Minimum price mentioned (e.g., 'under 50000' -> 50000, 'more than 100000' -> 100000)\n"
            "- price_max: Maximum price mentioned\n"
            "- base_price_min: Minimum base price if mentioned\n"
            "- base_price_max: Maximum base price if mentioned\n"
            "- estimated_duration: Duration mentioned (e.g., '2 hours', '1 day', '1 week')\n\n"
            "If a filter is not mentioned, set it to null. Be precise and only extract what is explicitly stated."
        )),
        ("human", "{query}")
    ])
    
    structured_llm = _filter_llm.with_structured_output(ServiceFilters)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"query": query})
        filters = {}
        
        if result.city:
            filters["city"] = result.city.strip()
        if result.category:
            filters["category"] = result.category.strip()
        if result.price_min is not None:
            filters["price_min"] = result.price_min
        if result.price_max is not None:
            filters["price_max"] = result.price_max
        if result.base_price_min is not None:
            filters["base_price_min"] = result.base_price_min
        if result.base_price_max is not None:
            filters["base_price_max"] = result.base_price_max
        if result.estimated_duration:
            filters["estimated_duration"] = result.estimated_duration.strip()
            
        return filters
    except Exception as e:
        # If extraction fails, return empty filters (search will proceed without filters)
        print(f"Filter extraction error (continuing without filters): {e}")
        return {}

