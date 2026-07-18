from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PlatformProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_profiles"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="SET NULL"), nullable=True
    )
    platform_name: Mapped[str] = mapped_column(String(120), nullable=False)
    profile_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    import_method: Mapped[str] = mapped_column(String(80), nullable=False)
    raw_import_text: Mapped[str] = mapped_column(Text, nullable=False)
    import_status: Mapped[str] = mapped_column(String(60), default="Draft", nullable=False)
    user_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parsed_profile: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    actor_profile = relationship("ActorProfile")

    __table_args__ = (
        CheckConstraint(
            "platform_name IN ('Actors Access', 'Casting Networks', 'Casting Frontier', 'Other')",
            name="ck_platform_profiles_platform_name",
        ),
        CheckConstraint(
            "import_method IN ('Manual Copy/Paste', 'Uploaded PDF', 'Uploaded Screenshot', "
            "'Uploaded CSV', 'User-Provided Text', 'Manual Guided Form')",
            name="ck_platform_profiles_import_method",
        ),
        CheckConstraint(
            "import_status IN ('Draft', 'Needs Review', 'Approved', 'Rejected')",
            name="ck_platform_profiles_import_status",
        ),
    )


class PlatformAssetMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_asset_mappings"

    platform_name: Mapped[str] = mapped_column(String(120), nullable=False)
    platform_asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    local_asset_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    archetypes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    local_asset = relationship("Asset")

    __table_args__ = (
        CheckConstraint(
            "platform_name IN ('Actors Access', 'Casting Networks', 'Casting Frontier', 'Other')",
            name="ck_platform_asset_mappings_platform_name",
        ),
        CheckConstraint(
            "asset_type IN ('Headshot', 'Reel', 'Slate', 'Resume', 'Other')",
            name="ck_platform_asset_mappings_asset_type",
        ),
    )


class PublicProfileImport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "public_profile_imports"

    platform_name: Mapped[str] = mapped_column(String(120), nullable=False)
    profile_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    import_method: Mapped[str] = mapped_column(String(80), default="Public/shareable profile URL", nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_visible_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parsed_data_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    import_status: Mapped[str] = mapped_column(String(60), default="Draft", nullable=False)
    user_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "platform_name IN ('Actors Access', 'Casting Networks', 'Casting Frontier', 'Other')",
            name="ck_public_profile_imports_platform_name",
        ),
        CheckConstraint(
            "import_method = 'Public/shareable profile URL'",
            name="ck_public_profile_imports_import_method",
        ),
        CheckConstraint(
            "import_status IN ('Draft', 'Needs Review', 'Approved', 'Rejected', 'Blocked')",
            name="ck_public_profile_imports_import_status",
        ),
    )


class SupervisedBreakdownImport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supervised_breakdown_imports"

    actor_profile_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actor_profiles.id", ondelete="SET NULL"), nullable=True
    )
    approved_opportunity_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True
    )
    platform_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_visible_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parsed_data_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    import_status: Mapped[str] = mapped_column(String(60), default="Draft", nullable=False)
    user_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_profile = relationship("ActorProfile")
    approved_opportunity = relationship("Opportunity")

    __table_args__ = (
        CheckConstraint(
            "platform_name IN ('Actors Access', 'Casting Networks', 'Casting Frontier')",
            name="ck_supervised_breakdown_imports_platform_name",
        ),
        CheckConstraint(
            "import_status IN ('Draft', 'Approved', 'Rejected', 'Needs Review', 'Blocked')",
            name="ck_supervised_breakdown_imports_import_status",
        ),
    )
