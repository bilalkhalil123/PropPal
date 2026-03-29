"""
SQLAlchemy declarative models for Neon PostgreSQL.

One table per former MongoDB collection. UUID primary keys; FKs as UUID.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


def uuid_default() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    profile_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clerk_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    seller_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    property_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    area_sqft: Mapped[float] = mapped_column(Float, nullable=False)
    bedrooms: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bathrooms: Mapped[int] = mapped_column(Integer, nullable=False)
    floors: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(100), nullable=False)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    images: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_added: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Amenity data: raw JSON from Overpass API and Groq-generated summary text
    nearby_amenities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    amenity_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_properties_price", "price"),
        Index("ix_properties_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# Builder profiles
# ---------------------------------------------------------------------------


class BuilderProfile(Base):
    __tablename__ = "builder_profiles"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialization: Mapped[list] = mapped_column(ARRAY(Text), default=list, nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False)
    portfolio_images: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {city, latitude, longitude}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Builder services
# ---------------------------------------------------------------------------


class BuilderService(Base):
    __tablename__ = "builder_services"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    builder_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("builder_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    price_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    estimated_duration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    service_features: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    service_images: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# User projects
# ---------------------------------------------------------------------------


class UserProject(Base):
    __tablename__ = "user_projects"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[str] = mapped_column(String(100), nullable=False)
    budget_min: Mapped[float] = mapped_column(Float, nullable=False)
    budget_max: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Builder bids
# ---------------------------------------------------------------------------


class BuilderBid(Base):
    __tablename__ = "builder_bids"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    project_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("user_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    builder_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("builder_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal_title: Mapped[str] = mapped_column(String(200), nullable=False)
    proposal_details: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_duration: Mapped[str] = mapped_column(String(100), nullable=False)
    attachments: Mapped[list] = mapped_column(ARRAY(Text), default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Chat histories
# ---------------------------------------------------------------------------


class ChatHistory(Base):
    __tablename__ = "chat_histories"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    messages: Mapped[dict] = mapped_column(JSONB, default=lambda: [], nullable=False)  # list of {role, content, timestamp}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Availability (property/seller slots)
# ---------------------------------------------------------------------------


class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    property_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    seller_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    slots: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


# ---------------------------------------------------------------------------
# Visits
# ---------------------------------------------------------------------------


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, default=uuid_default
    )
    buyer_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    builder_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("builder_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    proposed_time_slots: Mapped[list] = mapped_column(ARRAY(Text), default=list, nullable=False)
    confirmed_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    agent_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
