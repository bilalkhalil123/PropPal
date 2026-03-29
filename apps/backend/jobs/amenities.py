import time
import requests
import math
from typing import Any, Dict, List, Literal, Tuple

# Stable Overpass API mirrors
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]

AmenityType = Literal[
    "school", "university", "college",
    "clinic", "pharmacy", "dentist",
    "police", "fountain", "place_of_worship",
    "restaurant", "cafe", "fast_food",
    "bank", "atm",
    "supermarket", "marketplace", "mall", "department_store",
    "park", "playground",
]


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in meters between two lat/lng points."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def build_overpass_query(
    lat: float,
    lon: float,
    radius_m: int,
    amenity_types: List[AmenityType],
) -> str:
    """
    Build an Overpass QL query for given amenity types and related shop types around (lat, lon).
    """
    amenity_regex = "|".join(amenity_types)
    
    # Common shop types that correspond to our amenity categories
    shop_types = ["supermarket", "mall", "department_store", "pharmacy", "chemist"]
    shop_regex = "|".join(shop_types)

    # Overpass QL
    query = f"""
[out:json][timeout:30];
(
  node["amenity"~"{amenity_regex}"](around:{radius_m},{lat},{lon});
  way["amenity"~"{amenity_regex}"](around:{radius_m},{lat},{lon});
  node["shop"~"{shop_regex}"](around:{radius_m},{lat},{lon});
  way["shop"~"{shop_regex}"](around:{radius_m},{lat},{lon});
);
out center;
"""
    return query.strip()


def call_overpass(query: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Call Overpass API with reliable mirrors and timeout.
    """
    last_error = "No mirrors attempted"
    
    for url in OVERPASS_MIRRORS:
        try:
            print(f"[AMENITY] Querying Overpass mirror: {url}")
            resp = requests.post(url, data={"data": query}, timeout=35)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])
                print(f"[AMENITY] SUCCESS: Found {len(elements)} elements from {url}")
                return data
            
            last_error = f"HTTP {resp.status_code}"
            print(f"[AMENITY] Mirror {url} failed: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f"[AMENITY] Mirror {url} error: {last_error}")
            
    raise Exception(f"All Overpass mirrors failed. Last error: {last_error}")


def mock_rating(osm_id: int) -> float:
    """Deterministic pseudo-rating between 3.0 and 5.0 based on OSM ID."""
    return 3.0 + ((osm_id % 20) / 10.0)


def normalize_element(
    element: Dict[str, Any],
    property_lat: float,
    property_lon: float,
) -> Tuple[str, Dict[str, Any]]:
    """Convert raw Overpass element into normalized amenity dict."""
    tags = element.get("tags", {}) or {}
    amenity_type = tags.get("amenity") or tags.get("shop")
    if not amenity_type:
        raise ValueError("No amenity/shop tag")

    if element.get("type") == "node":
        lat = element["lat"]
        lon = element["lon"]
    else:
        center = element.get("center")
        if not center:
            raise ValueError("No center")
        lat = center["lat"]
        lon = center["lon"]

    dist = haversine_distance_m(property_lat, property_lon, lat, lon)
    name = tags.get("name", "Unknown")

    # Category Mapping
    if amenity_type in ("school", "university", "college"):
        category = "schools"
    elif amenity_type in ("hospital", "clinic"):
        category = "hospitals"
    elif amenity_type in ("pharmacy", "chemist"):
        category = "pharmacies"
    elif amenity_type in ("restaurant", "cafe", "fast_food"):
        category = "food"
    elif amenity_type in ("bank", "atm"):
        category = "banks"
    elif amenity_type in ("supermarket", "marketplace", "mall", "department_store"):
        category = "shopping"
    elif amenity_type in ("park", "playground"):
        category = "parks"
    else:
        category = f"{amenity_type}s"

    amenity = {
        "id": f"osm_{element['id']}",
        "name": name,
        "type": amenity_type,
        "rating": mock_rating(element['id']),
        "distance_m": round(dist, 2),
        "lat": lat,
        "lng": lon,
        "source": "osm",
        "address": tags.get("addr:full") or tags.get("addr:street") or tags.get("addr:city"),
    }
    return category, amenity


def fetch_nearby_amenities(
    property_lat: float,
    property_lon: float,
    radius_m: int = 2500,
    amenity_types: List[AmenityType] | None = None,
    max_per_category: int = 10,
) -> Dict[str, List[Dict[str, Any]]]:
    """High-level function to get grouped amenities around a point."""
    if amenity_types is None:
        amenity_types = ["school", "university", "college", "hospital", "clinic", "pharmacy", "supermarket", "mall"]

    query = build_overpass_query(property_lat, property_lon, radius_m, amenity_types)
    data = call_overpass(query)

    elements = data.get("elements", [])
    by_category: Dict[str, List[Dict[str, Any]]] = {}

    for el in elements:
        try:
            category, amenity = normalize_element(el, property_lat, property_lon)
            by_category.setdefault(category, []).append(amenity)
        except Exception:
            continue

    for cat in by_category:
        by_category[cat].sort(key=lambda a: a["distance_m"])
        by_category[cat] = by_category[cat][:max_per_category]

    return by_category


if __name__ == "__main__":
    # Test near F-10 Islamabad
    res = fetch_nearby_amenities(33.693, 73.003, radius_m=2000)
    print(f"Found {sum(len(v) for v in res.values())} total amenities.")
    for k, v in res.items():
        print(f"- {k}: {len(v)}")