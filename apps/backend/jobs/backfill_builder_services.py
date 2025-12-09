from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add parent directory to path to import common and models
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import get_settings
from common.db import DatabaseClient
from models.builder_services import BuilderService
from services.embeddings.service import embed_batch
from services.embeddings.compose import compose_builder_services_text
from services.vector_search.qdrant_service import upsert_builder_service_embedding


async def populate_builder_services(file_path: str) -> None:
    """
    Populates the 'builder_services' collection with data from a JSON file,
    linking services to builders using their company_name.
    """
    settings = get_settings()
    if DatabaseClient.client is None:
        print(f"[POPULATE] Connecting to MongoDB at {settings.MONGODB_URL[:20]}...")
        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    builder_profiles_collection = db["builder_profiles"]
    builder_services_collection = db["builder_services"]

    # 1. Fetch all builder profiles to map company_name to builder_id
    builder_cursor = builder_profiles_collection.find({}, {"_id": 1, "company_name": 1})
    builder_profiles = await builder_cursor.to_list(length=None)
    company_to_builder_id = {profile["company_name"]: profile["_id"] for profile in builder_profiles}

    print(f"[POPULATE] Found {len(company_to_builder_id)} builder profiles.")

    # 2. Read builder services from JSON file
    print(f"[POPULATE] Reading builder services from {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            services_data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Data file not found at: {file_path}")
        return
    except json.JSONDecodeError:
        print(f"[ERROR] Could not decode JSON from file: {file_path}")
        return

    services_to_insert = []

    for service_data in services_data:
        company_name = service_data.get("company_name")
        builder_id = company_to_builder_id.get(company_name)

        if not builder_id:
            print(f"[WARNING] No builder profile found for company_name: {company_name}. Skipping.")
            continue

        # Prepare the service data
        clean_data = service_data.copy()
        clean_data.pop("_id", None)
        clean_data.pop("created_at", None)
        clean_data.pop("updated_at", None)
        
        builder_id_obj = ObjectId(builder_id)
        clean_data["builder_id"] = builder_id_obj
        clean_data["created_at"] = datetime.utcnow()
        clean_data["updated_at"] = datetime.utcnow()

        # Generate embeddings for the service
        text_to_embed = compose_builder_services_text(clean_data)
        embedding_vector = embed_batch([text_to_embed])[0]
        clean_data["embeddings"] = embedding_vector

        # Validate using the BuilderService model
        service = BuilderService(**clean_data)
        
        # Dump the model to a dictionary for insertion
        service_dict = service.model_dump(by_alias=True, exclude=["id"])
        
        # Overwrite the stringified builder_id from model_dump with the original ObjectId
        service_dict["builder_id"] = builder_id_obj
        
        services_to_insert.append((service_dict, embedding_vector, clean_data))

    if services_to_insert:
        # Separate service dicts and embeddings for insertion
        service_dicts = [item[0] for item in services_to_insert]
        result = await builder_services_collection.insert_many(service_dicts)
        print(f"[POPULATE] Inserted {len(result.inserted_ids)} new builder services.")
        
        # Store embeddings in Qdrant
        for idx, (service_dict, embedding_vector, clean_data) in enumerate(services_to_insert):
            service_id = str(result.inserted_ids[idx])
            metadata = {
                "service_name": clean_data.get("service_name", ""),
                "category": clean_data.get("category", ""),
                "builder_id": str(clean_data.get("builder_id", builder_id_obj)),
            }
            await upsert_builder_service_embedding(
                service_id=service_id,
                embedding=embedding_vector,
                metadata=metadata,
            )
        print(f"[POPULATE] Stored {len(services_to_insert)} builder service embeddings in Qdrant.")
    else:
        print("[POPULATE] No new builder services to insert.")


def main() -> None:
    """Main function to run the builder services population script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        type=str,
        default="../../../data/builder_services.json",
        help="Path to the builder services data JSON file relative to the jobs directory.",
    )
    args = parser.parse_args()

    jobs_dir = Path(__file__).resolve().parent
    file_path = (jobs_dir / args.file).resolve()

    asyncio.run(populate_builder_services(str(file_path)))


if __name__ == "__main__":
    main()
