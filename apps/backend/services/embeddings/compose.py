from __future__ import annotations

from typing import Dict


def compose_property_text(p: Dict) -> str:
    parts = []
    for key in ["title", "description", "property_type", "city", "area"]:
        val = p.get(key)
        if isinstance(val, str) and val:
            parts.append(val)
    # Numeric context (beds/baths/area)
    beds = p.get("bedrooms")
    baths = p.get("bathrooms")
    sqft = p.get("area_sqft")
    numeric_bits = []
    if isinstance(beds, (int, float)):
        numeric_bits.append(f"bedrooms: {int(beds)}")
    if isinstance(baths, (int, float)):
        numeric_bits.append(f"bathrooms: {int(baths)}")
    if isinstance(sqft, (int, float)):
        numeric_bits.append(f"area_sqft: {float(sqft)}")
    if numeric_bits:
        parts.append(", ".join(numeric_bits))
    # Amenity summary (if available) — enriches the embedding so
    # queries like "house near a good school" match naturally.
    amenity_summary = p.get("amenity_summary")
    if isinstance(amenity_summary, str) and amenity_summary.strip():
        parts.append(f"Nearby amenities: {amenity_summary.strip()}")
    return "\n".join(parts)


def compose_builder_profile_text(doc: Dict) -> str:
    """
    Composes a text string from a builder profile document for embedding.
    """
    specializations = ", ".join(doc.get("specialization", []))
    location_parts = []
    location_info = doc.get("location", {})
    if isinstance(location_info, dict):
        city = location_info.get("city")
        latitude = location_info.get("latitude")
        longitude = location_info.get("longitude")
        if city:
            location_parts.append(city)
        if latitude and longitude:
            location_parts.append(f"at coordinates {latitude}, {longitude}")

    details_parts = [
        f"Builder Profile: {doc.get('company_name', 'N/A')}",
        f"Specializations: {specializations if specializations else 'Not specified'}",
        f"Experience: {doc.get('experience_years', 0)} years",
        f"About: {doc.get('about', 'No description available.')}",
        f"Location: {' '.join(location_parts) if location_parts else 'N/A'}",
    ]

    rating = doc.get("rating")
    if isinstance(rating, (int, float)):
        details_parts.append(f"Rating: {rating} out of 5 stars.")

    founded_year = doc.get("founded_year")
    if isinstance(founded_year, int):
        details_parts.append(f"Founded in {founded_year}.")

    return ". ".join(part for part in details_parts if part)


def compose_builder_services_text(service: Dict) -> str:
    """
    Composes a text string from a builder service document for embedding.
    """
    parts = [
        f"Service Title: {service.get('title', 'N/A')}",
        f"Description: {service.get('description', 'No description available.')}",
        f"Category: {service.get('category', 'N/A')}",
        f"Base Price: {service.get('base_price', 'N/A')} {service.get('price_unit', '')}",
        f"Estimated Duration: {service.get('estimated_duration', 'N/A')}",
    ]

    # Add service features
    features = service.get("service_features", [])
    if features:
        parts.append(f"Features: {', '.join(features)}")

    return ". ".join(part for part in parts if part)



