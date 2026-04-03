"""
Seller availability repository (recurring weekly windows). IDs are UUID strings.
"""

from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db_session
from db.models import SellerAvailability as SellerAvailabilityModel


class SellerAvailabilityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_dict(self, row: SellerAvailabilityModel) -> Dict[str, Any]:
        return {
            "id": row.id,
            "_id": row.id,
            "seller_id": row.seller_id,
            "property_id": row.property_id,
            "day_of_week": row.day_of_week,
            "start_time": row.start_time,
            "end_time": row.end_time,
        }

    async def list_by_seller_and_property(
        self, seller_id: str, property_id: str
    ) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            select(SellerAvailabilityModel)
            .where(SellerAvailabilityModel.seller_id == seller_id)
            .where(SellerAvailabilityModel.property_id == property_id)
            .order_by(
                SellerAvailabilityModel.day_of_week,
                SellerAvailabilityModel.start_time,
            )
        )
        rows = result.scalars().all()
        return [self._row_to_dict(r) for r in rows]

    async def delete_by_property_id(self, property_id: str) -> int:
        result = await self.session.execute(
            delete(SellerAvailabilityModel).where(
                SellerAvailabilityModel.property_id == property_id
            )
        )
        return result.rowcount or 0

    async def create(self, data: Dict[str, Any]) -> SellerAvailabilityModel:
        row = SellerAvailabilityModel(
            seller_id=data["seller_id"],
            property_id=data["property_id"],
            day_of_week=data["day_of_week"],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def bulk_create(self, rows: List[Dict[str, Any]]) -> int:
        count = 0
        for data in rows:
            await self.create(data)
            count += 1
        return count


async def get_seller_availability_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SellerAvailabilityRepository:
    return SellerAvailabilityRepository(session)
