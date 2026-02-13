from __future__ import annotations

import asyncio
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

# Ensure common module import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
import httpx
from bs4 import BeautifulSoup

from common.repositories.property_repository import PropertyRepository, get_property_repository
from services.vector_search.qdrant_service import delete_embedding
from common.qdrant import PROPERTIES_COLLECTION


router = APIRouter(prefix="/api/properties/scraper", tags=["properties-scraper"])


class UrlCheckRequest(BaseModel):
	urls: List[str] = Field(..., min_length=1, description="Property listing URLs to check")


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
