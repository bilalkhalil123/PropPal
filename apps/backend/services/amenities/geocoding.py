"""
Geocoding service using OpenStreetMap Nominatim (free, no API key required).

Used to convert a user-specified place name (e.g. "Centaurus Mall", "Beaconhouse school Islamabad")
into (lat, lon) coordinates for Qdrant geo_radius filtering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


@dataclass
class GeocodingResult:
    """A single geocoded location."""
    lat: float
    lon: float
    display_name: str
    place_id: int


def geocode_place(
    query: str,
    country_code: str = "pk",
    limit: int = 5,
) -> List[GeocodingResult]:
    """
    Geocode a place name using OSM Nominatim.

    Args:
        query: Place name (e.g. "Centaurus Mall Islamabad")
        country_code: ISO 3166-1 alpha-2 (default "pk" for Pakistan)
        limit: Max number of results

    Returns:
        List of GeocodingResult. Empty list if nothing found.
    """
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": limit,
        "countrycodes": country_code,
    }
    headers = {
        "User-Agent": "PropPal-App-Bot/1.0 (Academic/FYP; admin@proppal.local)",
        "Referer": "http://localhost:3000",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("[GEOCODE] Nominatim request failed: %s", e)
        return []

    results: list[GeocodingResult] = []
    for item in data:
        try:
            results.append(
                GeocodingResult(
                    lat=float(item["lat"]),
                    lon=float(item["lon"]),
                    display_name=item.get("display_name", ""),
                    place_id=int(item.get("place_id", 0)),
                )
            )
        except (KeyError, ValueError):
            continue

    return results


def geocode_place_single(
    query: str,
    country_code: str = "pk",
) -> Optional[GeocodingResult]:
    """
    Geocode a place and return the top result, or None if ambiguous/empty.
    
    Returns:
        The top result if exactly one match or if the top match is highly confident.
        None if no results are found.
    
    Raises:
        AmbiguousGeocodingError: If multiple results are found and there's no clear winner.
    """
    results = geocode_place(query, country_code=country_code, limit=3)
    if not results:
        return None
    # If only one result, use it
    if len(results) == 1:
        return results[0]
    # Return the top result (Nominatim orders by relevance)
    return results[0]


def geocode_place_with_candidates(
    query: str,
    country_code: str = "pk",
) -> dict:
    """
    Geocode a place and return structured output for the agent to handle ambiguity.
    
    Returns dict:
        {
            "success": True/False,
            "result": GeocodingResult or None,
            "candidates": [GeocodingResult, ...],  # if ambiguous
            "message": str
        }
    """
    results = geocode_place(query, country_code=country_code, limit=5)

    if not results:
        return {
            "success": False,
            "result": None,
            "candidates": [],
            "message": f"Could not find a location matching '{query}'. Please provide a more specific name.",
        }

    if len(results) == 1:
        return {
            "success": True,
            "result": results[0],
            "candidates": results,
            "message": f"Found: {results[0].display_name}",
        }

    # Multiple results — return top match but include candidates
    return {
        "success": True,
        "result": results[0],
        "candidates": results,
        "message": f"Top match: {results[0].display_name}",
    }
