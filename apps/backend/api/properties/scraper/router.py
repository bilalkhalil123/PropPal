from __future__ import annotations

import asyncio
import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# Ensure common module import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
import httpx
from bs4 import BeautifulSoup

from common.repositories.property_repository import PropertyRepository, get_property_repository
from common.repositories.user_repository import UserRepository, get_user_repository
from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import delete_embedding, upsert_property_embedding
from common.qdrant import PROPERTIES_COLLECTION


router = APIRouter(prefix="/api/properties/scraper", tags=["properties-scraper"])


class UrlCheckRequest(BaseModel):
	urls: List[str] = Field(..., min_length=1, description="Property listing URLs to check")


class IngestUrlsRequest(BaseModel):
	urls: List[str] = Field(..., min_length=1, description="Property detail URLs to ingest")
	source: str = Field(default="zameen", description="Source label for listings")
	seller_id: Optional[str] = Field(default=None, description="Seller UUID to assign to scraped listings")
	upsert_embeddings: bool = Field(default=True, description="Whether to upsert embeddings to Qdrant")
	max_concurrency: int = Field(default=6, ge=1, le=20)


DEFAULT_CITY_SLUGS = {
	"lahore": "Lahore-1",
	"karachi": "Karachi-2",
	"islamabad": "Islamabad-3",
}

BASE_URL = "https://www.zameen.com"
SCRAPER_HEADERS = {
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
	"Accept-Encoding": "gzip, deflate",
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	"DNT": "1",
	"Connection": "close",
	"Upgrade-Insecure-Requests": "1",
}


class _TextExtractor(HTMLParser):
	def __init__(self) -> None:
		super().__init__()
		self._texts: List[str] = []
		self._title: List[str] = []
		self._in_title = False

	def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
		if tag.lower() == "title":
			self._in_title = True

	def handle_endtag(self, tag: str) -> None:
		if tag.lower() == "title":
			self._in_title = False

	def handle_data(self, data: str) -> None:
		text = data.strip()
		if not text:
			return
		if self._in_title:
			self._title.append(text)
		self._texts.append(text)

	def get_text(self) -> str:
		return " ".join(self._texts)

	def get_title(self) -> str:
		return " ".join(self._title).strip()


SOLD_KEYWORDS = [
	"sold",
	"expired",
	"not available",
	"no longer available",
	"unavailable",
	"off market",
	"removed",
	"withdrawn",
	"listing not found",
	"property not found",
	"page not found",
]

DETAIL_PATTERNS = {
	"price": re.compile(r"\b(pkr|rs\.?|price|usd|\$|£|€)\b", re.IGNORECASE),
	"beds": re.compile(r"\b(bed|beds|bedroom|bedrooms)\b", re.IGNORECASE),
	"baths": re.compile(r"\b(bath|baths|bathroom|bathrooms)\b", re.IGNORECASE),
	"area": re.compile(r"\b(sq\s?ft|square feet|sq\s?m|sqm|sq\s?yd|marla|kanal|area)\b", re.IGNORECASE),
	"type": re.compile(r"\b(apartment|house|flat|plot|villa|commercial|office|shop|warehouse|building|farmhouse)\b", re.IGNORECASE),
	"date": re.compile(r"\b(20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b", re.IGNORECASE),
	"location": re.compile(r"\b(location|city|address|near|area)\b", re.IGNORECASE),
}


def _convert_price(price_str: Optional[str]) -> Optional[float]:
	if not price_str:
		return None
	value = str(price_str).replace(",", "").strip()
	if not value:
		return None
	try:
		if "crore" in value.lower():
			return float(value.lower().replace("crore", "").strip()) * 10_000_000
		if "lakh" in value.lower():
			return float(value.lower().replace("lakh", "").strip()) * 100_000
		if "million" in value.lower():
			return float(value.lower().replace("million", "").strip()) * 1_000_000
		if "arab" in value.lower():
			return float(value.lower().replace("arab", "").strip()) * 1_000_000_000
		if "thousand" in value.lower():
			return float(value.lower().replace("thousand", "").strip()) * 1_000
		return float(re.sub(r"[^\d.]", "", value))
	except Exception:
		return None


def _convert_area(area_str: Optional[str]) -> Optional[float]:
	if not area_str:
		return None
	value = str(area_str).replace(",", "").strip()
	if not value:
		return None
	try:
		if "marla" in value.lower():
			return float(value.lower().replace("marla", "").strip()) * 225
		if "kanal" in value.lower():
			return float(value.lower().replace("kanal", "").strip()) * 4500
		if "sq. yd" in value.lower() or "sq yd" in value.lower():
			return float(re.sub(r"[^\d.]", "", value)) * 9
		return float(re.sub(r"[^\d.]", "", value))
	except Exception:
		return None


def _extract_listing_details(html: str) -> Dict[str, Optional[str]]:
	soup = BeautifulSoup(html, "html.parser")

	details: Dict[str, Optional[str]] = {
		"price": None,
		"beds": None,
		"baths": None,
		"area": None,
		"type": None,
		"date": None,
		"title": None,
		"description": None,
		"location": None,
	}

	price_tag = soup.find("span", attrs={"aria-label": "Price"})
	if not price_tag:
		price_tag = soup.find(string=re.compile(r"PKR|Rs\.|Rupee", re.I))
	price_raw = price_tag.get_text(strip=True) if hasattr(price_tag, "get_text") else (price_tag.strip() if isinstance(price_tag, str) else None)
	price_value = _convert_price(price_raw)
	if price_value is not None:
		details["price"] = str(price_value)

	beds_tag = soup.find("span", attrs={"aria-label": "Beds"}) or soup.find(string=re.compile(r"\b\d+\s*Beds?\b", re.I))
	beds_raw = beds_tag.get_text(strip=True) if hasattr(beds_tag, "get_text") else (beds_tag.strip() if isinstance(beds_tag, str) else None)
	if beds_raw:
		beds_match = re.search(r"(\d+)", beds_raw)
		if beds_match:
			details["beds"] = beds_match.group(1)

	baths_tag = soup.find("span", attrs={"aria-label": "Baths"}) or soup.find(string=re.compile(r"\b\d+\s*Baths?\b", re.I))
	baths_raw = baths_tag.get_text(strip=True) if hasattr(baths_tag, "get_text") else (baths_tag.strip() if isinstance(baths_tag, str) else None)
	if baths_raw:
		baths_match = re.search(r"(\d+)", baths_raw)
		if baths_match:
			details["baths"] = baths_match.group(1)

	area_tag = soup.find("span", attrs={"aria-label": "Area"}) or soup.find(string=re.compile(r"(Kanal|Marla|Sq\.|Square\s*Feet|Sq\s*ft)", re.I))
	area_raw = area_tag.get_text(strip=True) if hasattr(area_tag, "get_text") else (area_tag.strip() if isinstance(area_tag, str) else None)
	area_value = _convert_area(area_raw)
	if area_value is not None:
		details["area"] = str(area_value)

	property_type_tag = soup.find("span", attrs={"aria-label": "Type"}) or soup.find(string=re.compile(r"\bType\b", re.I))
	if property_type_tag:
		if hasattr(property_type_tag, "get_text"):
			details["type"] = property_type_tag.get_text(strip=True)
		elif isinstance(property_type_tag, str):
			details["type"] = property_type_tag.strip()

	creation_date_tag = soup.find("span", attrs={"aria-label": "Creation date"}) or soup.find(string=re.compile(r"Added|Updated", re.I))
	if creation_date_tag:
		if hasattr(creation_date_tag, "get_text"):
			details["date"] = creation_date_tag.get_text(strip=True)
		elif isinstance(creation_date_tag, str):
			details["date"] = creation_date_tag.strip()

	title_tag = soup.find(["h1", "h2"], text=True)
	if title_tag and hasattr(title_tag, "get_text"):
		details["title"] = title_tag.get_text(strip=True)
	elif soup.title and soup.title.get_text(strip=True):
		details["title"] = soup.title.get_text(strip=True)

	desc_heading = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and "description" in (tag.get_text() or "").lower())
	description = None
	if desc_heading:
		parts: List[str] = []
		sibling = desc_heading.find_next_sibling()
		while sibling and sibling.name not in ["h2", "h3", "h4"]:
			parts.append(sibling.get_text(separator=" ", strip=True))
			sibling = sibling.find_next_sibling()
		description = " ".join([p for p in parts if p]).strip() if parts else None
	if not description:
		desc_div = soup.find("div", attrs={"class": re.compile(r"description|desc", re.I)})
		if desc_div:
			description = desc_div.get_text(separator=" ", strip=True)
	if description:
		details["description"] = description

	loc_tag = soup.find(lambda tag: tag.name in ["p", "div", "span"] and re.search(r"\b[A-Za-z]+,\s*[A-Za-z\- ]+,\s*[A-Za-z ]+", (tag.get_text() or "")))
	if loc_tag:
		details["location"] = loc_tag.get_text(strip=True)

	return details


def _convert_relative_date(relative_date_str: Optional[str]) -> Optional[datetime]:
	if not relative_date_str:
		return None
	value = str(relative_date_str).lower().strip()
	now = datetime.utcnow()
	if "just now" in value or "few seconds ago" in value:
		return now
	if "yesterday" in value:
		return now - timedelta(days=1)
	parts = value.split()
	if len(parts) < 2:
		return None
	try:
		amount = int(parts[0])
		unit = parts[1]
	except ValueError:
		return None
	if "minute" in unit:
		return now - timedelta(minutes=amount)
	if "hour" in unit:
		return now - timedelta(hours=amount)
	if "day" in unit:
		return now - timedelta(days=amount)
	if "week" in unit:
		return now - timedelta(weeks=amount)
	if "month" in unit:
		return now - timedelta(days=amount * 30)
	if "year" in unit:
		return now - timedelta(days=amount * 365)
	return None


def _extract_data_layer(html: str) -> Dict[str, Any]:
	pattern = re.compile(r"window\['dataLayer'\]\.push\((\{.*?\})\);", re.DOTALL)
	match = pattern.search(html)
	if not match:
		return {}
	json_str = match.group(1)
	try:
		return json.loads(json_str)
	except json.JSONDecodeError:
		return {}


def _split_location(location: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
	if not location:
		return None, None
	parts = [p.strip() for p in location.split(",") if p.strip()]
	if not parts:
		return None, None
	if len(parts) == 1:
		return parts[0], None
	return ", ".join(parts[:-1]), parts[-1]


def _build_property_payload(html: str, source_url: str, seller_id: str, source: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
	data_layer = _extract_data_layer(html)
	parsed = _extract_listing_details(html)

	price = _convert_price(parsed.get("price"))
	area_sqft = _convert_area(parsed.get("area"))
	bedrooms = int(parsed["beds"]) if parsed.get("beds") and parsed["beds"].isdigit() else None
	bathrooms = int(parsed["baths"]) if parsed.get("baths") and parsed["baths"].isdigit() else None

	property_type = parsed.get("type") or data_layer.get("property_type")
	title = parsed.get("title")
	description = parsed.get("description")
	date_added = _convert_relative_date(parsed.get("date"))

	location_detail = data_layer.get("loc_neighbourhood_name") or data_layer.get("loc_name") or parsed.get("location")
	area, city = _split_location(location_detail)
	city = data_layer.get("loc_city_name") or city

	lat = None
	lng = None
	if data_layer.get("latitude") is not None:
		try:
			lat = float(data_layer.get("latitude"))
		except Exception:
			lat = None
	if data_layer.get("longitude") is not None:
		try:
			lng = float(data_layer.get("longitude"))
		except Exception:
			lng = None

	external_id = data_layer.get("ad_id")

	required_missing = []
	if not title:
		required_missing.append("title")
	if not description:
		required_missing.append("description")
	if price is None:
		required_missing.append("price")
	if area_sqft is None:
		required_missing.append("area_sqft")
	if bedrooms is None:
		required_missing.append("bedrooms")
	if bathrooms is None:
		required_missing.append("bathrooms")
	if not property_type:
		required_missing.append("property_type")
	if not city:
		required_missing.append("city")
	if not area:
		required_missing.append("area")

	if required_missing:
		return None, required_missing

	payload = {
		"seller_id": seller_id,
		"title": title,
		"description": description,
		"price": float(price),
		"property_type": str(property_type).lower(),
		"area_sqft": float(area_sqft),
		"bedrooms": int(bedrooms),
		"bathrooms": int(bathrooms),
		"floors": 1,
		"city": city,
		"area": area,
		"lng": lng,
		"lat": lat,
		"images": [],
		"metadata": {"location_detail": location_detail} if location_detail else {},
		"external_id": str(external_id) if external_id else None,
		"source": source,
		"source_url": source_url,
		"date_added": date_added,
	}
	return payload, []


async def _get_listing_links(page: int, city_slug: str, client: httpx.AsyncClient) -> Optional[List[str]]:
	search_url = f"{BASE_URL}/Homes/{city_slug}-{page}.html"
	try:
		response = await client.get(search_url, headers=SCRAPER_HEADERS, timeout=20.0)
	except httpx.RequestError:
		return []

	if response.status_code == 404:
		return None
	if response.status_code != 200:
		return []

	soup = BeautifulSoup(response.text, "html.parser")
	links: List[str] = []
	for a_tag in soup.find_all("a", attrs={"aria-label": "Listing link"}, href=re.compile(r"/Property/.*\.html")):
		href = a_tag.get("href")
		if not href:
			continue
		full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
		if full_url not in links:
			links.append(full_url)
	return links


async def _collect_city_urls(city_slug: str, limit: int, client: httpx.AsyncClient) -> List[str]:
	collected: List[str] = []
	page = 1
	while len(collected) < limit:
		links = await _get_listing_links(page, city_slug, client)
		if links is None:
			break
		if not links:
			page += 1
			continue
		for url in links:
			if url not in collected:
				collected.append(url)
				if len(collected) >= limit:
					break
		page += 1
	return collected


def _extract_text_and_title(html: str) -> Tuple[str, str]:
	parser = _TextExtractor()
	parser.feed(html)
	return parser.get_text(), parser.get_title()


def _has_sold_keywords(text: str) -> bool:
	lowered = text.lower()
	return any(keyword in lowered for keyword in SOLD_KEYWORDS)


def _has_listing_details(text: str, title: str) -> bool:
	signals = {
		name: bool(pattern.search(text)) for name, pattern in DETAIL_PATTERNS.items()
	}
	signals["title"] = bool(title and len(title) >= 8)
	signals["description"] = len(text.split()) >= 80
	score = sum(1 for value in signals.values() if value)
	return score >= 3


async def _check_listing_status(url: str, client: httpx.AsyncClient) -> Tuple[bool, str]:
	try:
		response = await client.get(url, follow_redirects=True)
	except httpx.RequestError as exc:
		return True, f"request_error: {exc}"

	if response.history:
		original = url.rstrip("/")
		final_url = str(response.url).rstrip("/")
		if final_url != original:
			return True, "redirected"

	if response.status_code >= 400:
		return True, f"http_{response.status_code}"

	text, title = _extract_text_and_title(response.text)
	if _has_sold_keywords(text):
		return True, "sold_keywords"

	listing_details = _extract_listing_details(response.text)
	required_fields = ["price", "beds", "baths", "area", "type", "date", "title", "description", "location"]
	missing_details = [field for field in required_fields if not listing_details.get(field)]

	if missing_details:
		if not _has_listing_details(text, title):
			return True, "missing_details"

	return False, "active"


async def _resolve_seller_id(seller_id: Optional[str], user_repo: UserRepository) -> str:
	if seller_id:
		user = await user_repo.get_by_id(seller_id)
		if user:
			return user.id
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid seller_id")

	sellers = await user_repo.get_users_by_role("seller", limit=1)
	if sellers:
		return sellers[0].id
	raise HTTPException(
		status_code=status.HTTP_400_BAD_REQUEST,
		detail="No seller account available. Provide seller_id to assign scraped listings.",
	)


@router.get("/city-urls", summary="Get first 200 property URLs per city")
async def get_city_urls(
	limit: int = Query(200, ge=1, le=500, description="Max URLs per city"),
	cities: Optional[str] = Query(None, description="Comma-separated city names to include (lahore, karachi, islamabad)"),
):
	city_slugs = DEFAULT_CITY_SLUGS.copy()
	if cities:
		requested = {c.strip().lower() for c in cities.split(",") if c.strip()}
		city_slugs = {k: v for k, v in city_slugs.items() if k in requested}
	if not city_slugs:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid cities provided")

	urls_by_city: Dict[str, List[str]] = {}
	async with httpx.AsyncClient(timeout=20.0) as client:
		for city, slug in city_slugs.items():
			urls_by_city[city] = await _collect_city_urls(slug, limit, client)

	all_urls = [url for urls in urls_by_city.values() for url in urls]
	return {
		"limit": limit,
		"cities": list(urls_by_city.keys()),
		"total_urls": len(all_urls),
		"urls_by_city": urls_by_city,
	}


@router.post("/ingest-urls", summary="Scrape property details and store in database")
async def ingest_property_urls(
	payload: IngestUrlsRequest = Body(...),
	property_repo: PropertyRepository = Depends(get_property_repository),
	user_repo: UserRepository = Depends(get_user_repository),
):
	urls = [url.strip() for url in payload.urls if url and url.strip()]
	if not urls:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No URLs provided")

	seller_id = await _resolve_seller_id(payload.seller_id, user_repo)
	existing = await property_repo.list_existing_source_urls(urls)
	existing_set = set(existing)
	new_urls = [url for url in urls if url not in existing_set]

	if not new_urls:
		return {"submitted": len(urls), "stored": 0, "skipped": len(urls), "errors": []}

	semaphore = asyncio.Semaphore(payload.max_concurrency)
	errors: List[Dict[str, Any]] = []
	stored: List[str] = []

	async with httpx.AsyncClient(timeout=30.0) as client:
		async def _ingest_url(url: str) -> None:
			async with semaphore:
				try:
					response = await client.get(url, headers=SCRAPER_HEADERS, follow_redirects=True)
				except httpx.RequestError as exc:
					errors.append({"url": url, "reason": f"request_error: {exc}"})
					return

				if response.status_code >= 400:
					errors.append({"url": url, "reason": f"http_{response.status_code}"})
					return

				payload_data, missing = _build_property_payload(response.text, url, seller_id, payload.source)
				if not payload_data:
					errors.append({"url": url, "reason": "missing_fields", "missing": missing})
					return

				try:
					row = await property_repo.create(payload_data)
					stored.append(row.id)
					if payload.upsert_embeddings:
						text = f"Property: {row.title}. Description: {row.description}. Location: {row.city}, {row.area}. Type: {row.property_type}."
						try:
							embedding = embed_text(text)
							await upsert_property_embedding(
								property_id=row.id,
								embedding=embedding,
								metadata={
									"title": row.title,
									"city": row.city,
									"area": row.area,
									"property_type": row.property_type,
									"bedrooms": row.bedrooms,
									"bathrooms": row.bathrooms,
									"price": row.price,
								},
							)
						except Exception:
							pass
				except Exception as exc:
					errors.append({"url": url, "reason": f"db_error: {exc}"})

		await asyncio.gather(*[_ingest_url(url) for url in new_urls])

	return {
		"submitted": len(urls),
		"new_urls": len(new_urls),
		"stored": len(stored),
		"skipped": len(urls) - len(new_urls),
		"errors": errors,
	}


@router.post("/cleanup-sold", summary="Remove sold/expired properties from the database")
async def cleanup_sold_properties(
	property_repo: PropertyRepository = Depends(get_property_repository),
):
	"""
	Checks all properties for sold/expired status and removes sold listings.
	A listing is treated as sold when:
	- The URL redirects to a different location
	- Sold/expired keywords are found
	- Listing details cannot be extracted
	"""
	all_properties: List[Dict[str, Any]] = []
	skip = 0
	batch_size = 500
	while True:
		batch = await property_repo.list_all(skip=skip, limit=batch_size)
		if not batch:
			break
		all_properties.extend(batch)
		skip += batch_size

	if not all_properties:
		return {"checked": 0, "removed": 0, "removed_ids": [], "errors": []}

	semaphore = asyncio.Semaphore(8)
	removed_ids: List[str] = []
	errors: List[Dict[str, str]] = []

	async with httpx.AsyncClient(timeout=30.0) as client:
		async def _check_property(item: Dict[str, Any]) -> None:
			url = (item.get("source_url") or "").strip()
			if not url:
				return
			async with semaphore:
				sold, reason = await _check_listing_status(url, client)
			if not sold:
				return
			try:
				deleted = await property_repo.delete(item["id"])
				if deleted:
					removed_ids.append(item["id"])
					try:
						await delete_embedding(collection_name=PROPERTIES_COLLECTION, point_id=item["id"])
					except Exception:
						pass
			except Exception as exc:
				errors.append({"id": item.get("id", ""), "url": url, "reason": str(exc), "status": reason})

		await asyncio.gather(*[_check_property(item) for item in all_properties])

	return {
		"checked": len(all_properties),
		"removed": len(removed_ids),
		"removed_ids": removed_ids,
		"errors": errors,
	}


@router.post("/filter-new-urls", summary="Filter out URLs already present in the database")
async def filter_new_urls(
	payload: UrlCheckRequest = Body(...),
	property_repo: PropertyRepository = Depends(get_property_repository),
):
	"""Return only URLs that are not present in the database."""
	urls = [url.strip() for url in payload.urls if url and url.strip()]
	if not urls:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No URLs provided")
	existing = await property_repo.list_existing_source_urls(urls)
	existing_set = set(existing)
	new_urls = [url for url in urls if url not in existing_set]
	return {
		"submitted": len(urls),
		"existing": len(existing_set),
		"new": len(new_urls),
		"new_urls": new_urls,
	}
