"""
Weekly property scrape orchestration.

Sequence:
1) Fetch 200 URLs per city (Lahore, Karachi, Islamabad)
2) Remove sold/expired properties
3) Filter already-present URLs
4) Ingest new URLs into the database

Set BACKEND_API_BASE_URL to override base URL (default http://{HOST}:{PORT}).
"""
from __future__ import annotations

import asyncio
import os
from typing import List

import httpx

from common.config import get_settings


async def run_weekly_scrape() -> None:
    settings = get_settings()
    base_url = os.getenv("BACKEND_API_BASE_URL", f"http://{settings.HOST}:{settings.PORT}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("[SCRAPE] Fetching URLs per city...")
        city_urls_response = await client.get(
            f"{base_url}/api/properties/scraper/city-urls",
            params={"limit": 200},
        )
        city_urls_response.raise_for_status()
        city_urls = city_urls_response.json()
        urls_by_city = city_urls.get("urls_by_city", {})
        all_urls: List[str] = [url for urls in urls_by_city.values() for url in urls]
        print(f"[SCRAPE] Collected {len(all_urls)} URLs from {len(urls_by_city)} cities")

        print("[SCRAPE] Removing sold/expired properties...")
        cleanup_response = await client.post(f"{base_url}/api/properties/scraper/cleanup-sold")
        cleanup_response.raise_for_status()
        cleanup_data = cleanup_response.json()
        print(f"[SCRAPE] Removed {cleanup_data.get('removed', 0)} sold properties")

        print("[SCRAPE] Filtering existing URLs...")
        filter_response = await client.post(
            f"{base_url}/api/properties/scraper/filter-new-urls",
            json={"urls": all_urls},
        )
        filter_response.raise_for_status()
        filter_data = filter_response.json()
        new_urls: List[str] = filter_data.get("new_urls", [])
        print(f"[SCRAPE] {len(new_urls)} new URLs remaining")

        if not new_urls:
            print("[SCRAPE] No new URLs to ingest. Done.")
            return

        print("[SCRAPE] Ingesting new URLs...")
        ingest_response = await client.post(
            f"{base_url}/api/properties/scraper/ingest-urls",
            json={
                "urls": new_urls,
                "source": "zameen",
            },
        )
        ingest_response.raise_for_status()
        ingest_data = ingest_response.json()
        print(
            "[SCRAPE] Stored {stored} listings. Errors: {errors}".format(
                stored=ingest_data.get("stored", 0),
                errors=len(ingest_data.get("errors", [])),
            )
        )


def main() -> None:
    asyncio.run(run_weekly_scrape())


if __name__ == "__main__":
    main()
