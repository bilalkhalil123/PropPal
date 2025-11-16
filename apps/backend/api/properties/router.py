from __future__ import annotations

from typing import Any, Dict, Union, List

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

# Ensure common module import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.db import get_database


router = APIRouter(prefix="/api/properties", tags=["properties"])


def _normalize(value: Union[Dict[str, Any], List[Any], Any]) -> Union[Dict[str, Any], List[Any], Any]:
    """Recursively convert ObjectId instances to strings in any structure."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    return value


@router.get("/{property_id}", summary="Get full property details by ID")
async def get_property_by_id(
    property_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Fetches a single property document from MongoDB by its ObjectId.
    """
    try:
        _id = ObjectId(property_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property id"
        )

    # Exclude large/unnecessary fields for payload size and cleanliness
    projection = {
        "embeddings": 0,
        "source": 0,
        "metadata.raw": 0,
        "metadata.external_id": 0,
    }
    doc = await db["properties"].find_one({"_id": _id}, projection)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    return _normalize(doc)


