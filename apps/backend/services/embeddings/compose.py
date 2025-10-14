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
    return "\n".join(parts)


