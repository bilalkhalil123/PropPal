"""
Property repository (PostgreSQL/Neon). IDs are UUID strings.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import Property as PropertyModel


class PropertyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: PropertyModel) -> Dict[str, Any]:
        """Map SQLAlchemy row to API-friendly dict (id and seller_id as string)."""
        return {
            "id": row.id,
            "_id": row.id,
            "seller_id": row.seller_id,
            "title": row.title,
            "description": row.description,
            "price": row.price,
            "property_type": row.property_type,
            "area_sqft": row.area_sqft,
            "bedrooms": row.bedrooms,
            "bathrooms": row.bathrooms,
            "floors": row.floors,
            "city": row.city,
            "area": row.area,
            "lng": row.lng,
            "lat": row.lat,
            "images": row.images or [],
            "metadata": row.metadata_ or {},
            "external_id": row.external_id,
            "source": row.source,
            "source_url": row.source_url,
            "date_added": row.date_added,
            "last_indexed_at": row.last_indexed_at,
            "last_checked": row.last_checked,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def get_by_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            select(PropertyModel).where(PropertyModel.id == property_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None

    async def get_by_seller_id(self, seller_id: str) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            select(PropertyModel)
            .where(PropertyModel.seller_id == seller_id)
            .order_by(PropertyModel.created_at.desc())
            .limit(100)
        )
        return [self._row_to_dict(r) for r in result.scalars().all()]

    async def create(self, data: Dict[str, Any]) -> PropertyModel:
        row = PropertyModel(
            seller_id=data["seller_id"],
            title=data["title"],
            description=data["description"],
            price=data["price"],
            property_type=data["property_type"],
            area_sqft=data["area_sqft"],
            bedrooms=data["bedrooms"],
            bathrooms=data["bathrooms"],
            floors=data.get("floors", 1),
            city=data["city"],
            area=data["area"],
            lng=data.get("lng"),
            lat=data.get("lat"),
            images=data.get("images") or [],
            metadata_=data.get("metadata") or data.get("metadata_"),
            external_id=data.get("external_id"),
            source=data.get("source"),
            source_url=data.get("source_url"),
            date_added=data.get("date_added"),
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def delete(self, property_id: str) -> bool:
        result = await self.session.execute(
            select(PropertyModel).where(PropertyModel.id == property_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def update_last_checked(self, property_id: str, timestamp: datetime) -> bool:
        result = await self.session.execute(
            select(PropertyModel).where(PropertyModel.id == property_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.last_checked = timestamp
        await self.session.flush()
        return True

    async def list_recent(self, limit: int = 12) -> List[Dict[str, Any]]:
        """List most recent properties (for popular/fallback)."""
        result = await self.session.execute(
            select(PropertyModel)
            .order_by(PropertyModel.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_all(self, skip: int = 0, limit: int = 5000) -> List[Dict[str, Any]]:
        """List all properties with pagination (for embedding backfill)."""
        result = await self.session.execute(
            select(PropertyModel)
            .order_by(PropertyModel.id)
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_all_ordered_by_last_checked(self, skip: int = 0, limit: int = 500) -> List[Dict[str, Any]]:
        """List properties ordered by last_checked (NULLs first), then updated_at (oldest first)."""
        result = await self.session.execute(
            select(PropertyModel)
            .order_by(
                PropertyModel.last_checked.is_(None),
                PropertyModel.last_checked.asc().nullsfirst(),
                PropertyModel.updated_at.asc(),
                PropertyModel.id,
            )
            .offset(skip)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def list_by_ids(self, property_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch multiple properties by UUID list (e.g. for search results). Preserves order where possible."""
        if not property_ids:
            return []
        result = await self.session.execute(
            select(PropertyModel).where(PropertyModel.id.in_(property_ids))
        )
        rows = result.scalars().all()
        by_id = {r.id: self._row_to_dict(r) for r in rows}
        return [by_id[pid] for pid in property_ids if pid in by_id]

    async def list_existing_source_urls(self, urls: List[str]) -> List[str]:
        """Return the subset of source URLs that already exist in the database."""
        if not urls:
            return []
        result = await self.session.execute(
            select(PropertyModel.source_url).where(PropertyModel.source_url.in_(urls))
        )
        return [row[0] for row in result.all() if row[0]]

    async def bulk_update_last_checked(self, ids: List[str], timestamp: datetime) -> None:
        if not ids:
            return
        await self.session.execute(
            update(PropertyModel)
            .where(PropertyModel.id.in_(ids))
            .values(last_checked=timestamp)
        )

    async def bulk_delete_by_ids(self, ids: List[str]) -> int:
        if not ids:
            return 0
        result = await self.session.execute(
            delete(PropertyModel).where(PropertyModel.id.in_(ids))
        )
        return result.rowcount or 0

    async def list_ids_with_filters(
        self,
        city: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        bedrooms: Optional[int] = None,
        bedrooms_min: Optional[int] = None,
        bedrooms_max: Optional[int] = None,
        bathrooms_min: Optional[int] = None,
        bathrooms_max: Optional[int] = None,
        area_sqft_min: Optional[float] = None,
        area_sqft_max: Optional[float] = None,
        area: Optional[str] = None,
        property_type: Optional[str] = None,
        limit: int = 1000,
    ) -> List[str]:
        """Return list of property IDs matching filters (for search/agent)."""
        from sqlalchemy import func
        q = select(PropertyModel.id)
        if city:
            q = q.where(func.lower(PropertyModel.city) == city.strip().lower())
        if area:
            q = q.where(PropertyModel.area.ilike(f"%{area.strip()}%"))
        if property_type:
            q = q.where(func.lower(PropertyModel.property_type) == property_type.strip().lower())
        if price_min is not None:
            q = q.where(PropertyModel.price >= price_min)
        if price_max is not None:
            q = q.where(PropertyModel.price <= price_max)
        if bedrooms is not None:
            q = q.where(PropertyModel.bedrooms == bedrooms)
        if bedrooms_min is not None:
            q = q.where(PropertyModel.bedrooms >= bedrooms_min)
        if bedrooms_max is not None:
            q = q.where(PropertyModel.bedrooms <= bedrooms_max)
        if bathrooms_min is not None:
            q = q.where(PropertyModel.bathrooms >= bathrooms_min)
        if bathrooms_max is not None:
            q = q.where(PropertyModel.bathrooms <= bathrooms_max)
        if area_sqft_min is not None:
            q = q.where(PropertyModel.area_sqft >= area_sqft_min)
        if area_sqft_max is not None:
            q = q.where(PropertyModel.area_sqft <= area_sqft_max)
        q = q.limit(limit)
        result = await self.session.execute(q)
        return list(result.scalars().all())


async def get_property_repository(session: AsyncSession = Depends(get_db_session)) -> PropertyRepository:
    return PropertyRepository(session)
