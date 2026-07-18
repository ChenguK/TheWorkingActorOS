from datetime import date

from sqlalchemy import CheckConstraint, Column, Date, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


asset_archetypes = Table(
    "asset_archetypes",
    Base.metadata,
    Column(
        "asset_id",
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "archetype_id",
        UUID(as_uuid=True),
        ForeignKey("archetypes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    actor_profile_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    local_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    archetype_names: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    ai_suggested_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    ai_suggested_archetypes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(60), default="pending", nullable=False)
    analysis_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    upload_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_used_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_updated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_warning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    freshness_status: Mapped[str] = mapped_column(String(40), default="Current", nullable=False)

    actor_profile = relationship("ActorProfile", back_populates="assets")
    asset_tags = relationship("AssetTag", back_populates="asset", cascade="all, delete-orphan")
    archetypes = relationship("Archetype", secondary=asset_archetypes, back_populates="assets")

    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('Headshot', 'Reel', 'Slate', 'Resume')", name="ck_assets_type"
        ),
        CheckConstraint(
            "freshness_status IN ('Current', 'Aging', 'Needs Review', 'Outdated')",
            name="ck_assets_freshness_status",
        ),
    )


class Archetype(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "archetypes"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    assets = relationship("Asset", secondary=asset_archetypes, back_populates="archetypes")


class AssetTag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "asset_tags"

    asset_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(120), nullable=False)

    asset = relationship("Asset", back_populates="asset_tags")

    __table_args__ = (UniqueConstraint("asset_id", "tag", name="uq_asset_tags_asset_tag"),)
