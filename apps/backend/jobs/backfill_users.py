from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# Add parent directory to path to import common and models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import get_settings
from common.db import DatabaseClient
from models.users import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)


async def populate_users(file_path: str, batch_size: int, limit: Optional[int]) -> None:
    """
    Populates the 'users' collection with data from a JSON file.
    """
    settings = get_settings()
    if DatabaseClient.client is None:
        print(f"[POPULATE] Connecting to MongoDB at {settings.MONGODB_URL[:20]}...")
        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    users_collection = db["users"]

    print(f"[POPULATE] Reading users from {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample_users = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Data file not found at: {file_path}")
        return
    except json.JSONDecodeError:
        print(f"[ERROR] Could not decode JSON from file: {file_path}")
        return

    users_to_insert = []
    for user_data in sample_users:
        # Check if user already exists
        existing_user = await users_collection.find_one({"email": user_data["email"]})
        if not existing_user:
            # Prepare a clean dictionary for the User model
            new_user_data = {
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "phone": user_data.get("phone"),
                "role": user_data.get("role"),
                "profile_image": user_data.get("profile_image"),
                "clerk_id": user_data.get("clerk_id"),
            }

            # Hash email as password for demo purposes
            new_user_data["password_hash"] = get_password_hash(user_data["email"][:10])

            user = User(**new_user_data)
            users_to_insert.append(user.model_dump(by_alias=True, exclude=["id"]))
        else:
            print(f"User with email {user_data['email']} already exists. Skipping.")

    if users_to_insert:
        result = await users_collection.insert_many(users_to_insert)
        print(f"[POPULATE] Inserted {len(result.inserted_ids)} new users.")
    else:
        print("[POPULATE] No new users to insert.")


def main() -> None:
    """Main function to run the user population script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        type=str,
        default="../../../data/users.json",
        help="Path to the user data JSON file relative to the jobs directory.",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    # Construct the full path to the data file
    jobs_dir = Path(__file__).resolve().parent
    file_path = (jobs_dir / args.file).resolve()

    asyncio.run(populate_users(str(file_path), args.batch_size, args.limit))


if __name__ == "__main__":
    main()