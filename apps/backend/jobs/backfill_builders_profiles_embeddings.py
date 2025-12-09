from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne
from bson import ObjectId  # Import ObjectId

# Add parent directory to path to import common and models
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import get_settings
from common.db import DatabaseClient
from models.builder_profiles import BuilderProfile, Location
from services.embeddings.compose import compose_builder_profile_text
from services.embeddings.service import embed_batch
from services.vector_search.qdrant_service import upsert_builder_profile_embedding


async def populate_builder_profiles(
    file_path: str, batch_size: int, limit: Optional[int]
) -> None:
    """
    Populates the 'builder_profiles' collection with data from a JSON file,
    links them to users, and generates embeddings.
    """
    settings = get_settings()
    if DatabaseClient.client is None:
        print(f"[POPULATE] Connecting to MongoDB at {settings.MONGODB_URL[:20]}...")
        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    users_collection = db["users"]
    builder_profiles_collection = db["builder_profiles"]

    # 1. Fetch all users to assign profiles to
    user_cursor = users_collection.find({}, {"_id": 1})
    user_ids = [user["_id"] for user in await user_cursor.to_list(length=None)]

    if not user_ids:
        print("[ERROR] No users found in the database. Cannot create profiles.")
        return

    print(f"[POPULATE] Found {len(user_ids)} users to assign profiles to.")

    # 2. Read builder profiles from JSON file
    print(f"[POPULATE] Reading builder profiles from {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample_profiles = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Data file not found at: {file_path}")
        return
    except json.JSONDecodeError:
        print(f"[ERROR] Could not decode JSON from file: {file_path}")
        return

    profiles_to_insert = []
    # random.shuffle(user_ids)

    for i, profile_data in enumerate(sample_profiles):
        if i >= len(user_ids):
            print("[WARNING] Not enough users to assign to all profiles. Stopping.")
            break

        user_id = user_ids[i]  # This is a correct ObjectId

        # Check if a profile for this user already exists
        existing_profile = await builder_profiles_collection.find_one({"user_id": user_id})
        if not existing_profile:
            # 3. Prepare a clean dictionary for the BuilderProfile model
            clean_data = profile_data.copy()
            clean_data.pop("_id", None)
            clean_data.pop("created_at", None)
            clean_data.pop("updated_at", None)
            clean_data.pop("user_id", None)  # Remove placeholder user_id from JSON

            # Assign the correct user_id ObjectId
            clean_data["user_id"] = user_id

            # 4. Generate embeddings
            text_to_embed = compose_builder_profile_text(clean_data)
            embedding_vector = embed_batch([text_to_embed])[0]
            clean_data["embeddings"] = embedding_vector

            # Create Pydantic model instance for validation
            # This step likely converts user_id (ObjectId) to a string based on your model's definition
            profile = BuilderProfile(**clean_data)
            
            # Dump the model to a dictionary
            profile_dict = profile.model_dump(by_alias=True, exclude=["id"])
            
            # ✨ KEY CHANGE: Ensure user_id is an ObjectId before inserting
            # Overwrite the stringified user_id from model_dump with the original ObjectId
            profile_dict["user_id"] = user_id
            
            profiles_to_insert.append((profile_dict, embedding_vector, clean_data))
        else:
            print(f"Builder profile for user_id {user_id} already exists. Skipping.")

    if profiles_to_insert:
        # Separate profile dicts and embeddings for insertion
        profile_dicts = [item[0] for item in profiles_to_insert]
        result = await builder_profiles_collection.insert_many(profile_dicts)
        print(f"[POPULATE] Inserted {len(result.inserted_ids)} new builder profiles.")
        
        # Store embeddings in Qdrant
        for idx, (profile_dict, embedding_vector, clean_data) in enumerate(profiles_to_insert):
            profile_id = str(result.inserted_ids[idx])
            metadata = {
                "company_name": clean_data.get("company_name", ""),
                "city": clean_data.get("location", {}).get("city", "") if isinstance(clean_data.get("location"), dict) else "",
            }
            await upsert_builder_profile_embedding(
                profile_id=profile_id,
                embedding=embedding_vector,
                metadata=metadata,
            )
        print(f"[POPULATE] Stored {len(profiles_to_insert)} builder profile embeddings in Qdrant.")
    else:
        print("[POPULATE] No new builder profiles to insert.")


def main() -> None:
    """Main function to run the builder profile population script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        type=str,
        default="../../../data/builder_profiles.json",
        help="Path to the builder profiles data JSON file relative to the jobs directory.",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    jobs_dir = Path(__file__).resolve().parent
    file_path = (jobs_dir / args.file).resolve()

    asyncio.run(populate_builder_profiles(str(file_path), args.batch_size, args.limit))


if __name__ == "__main__":
    main()