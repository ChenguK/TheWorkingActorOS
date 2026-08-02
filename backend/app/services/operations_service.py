from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.db.models import (
    Asset,
    AuditionCalendarEvent,
    AvailabilityBlock,
    CastingPlatformSubscription,
    DailyPlatformCheckIn,
    ProfessionalEquipmentProfile,
    Submission,
)
from app.schemas.operations import (
    AuditionCalendarEventCreate,
    AuditionCalendarEventUpdate,
    AvailabilityBlockCreate,
    AvailabilityBlockUpdate,
    CastingPlatformSubscriptionCreate,
    CastingPlatformSubscriptionUpdate,
    DailyPlatformCheckInUpdate,
    ProfessionalEquipmentProfileUpdate,
)
from app.services.actor_work_event_service import ActorWorkEventService


CALLBACK_STATUSES = {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"}
DEFAULT_PLATFORMS = ["Actors Access", "Casting Networks", "Casting Frontier", "Backstage", "Other"]


class OperationsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_events(self) -> list[AuditionCalendarEvent]:
        return list(
            self.db.scalars(
                select(AuditionCalendarEvent).order_by(AuditionCalendarEvent.start_datetime.asc())
            )
        )

    def create_event(self, payload: AuditionCalendarEventCreate) -> AuditionCalendarEvent:
        event = AuditionCalendarEvent(**payload.model_dump())
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def update_event(self, event_id: UUID, payload: AuditionCalendarEventUpdate) -> AuditionCalendarEvent:
        event = self.db.get(AuditionCalendarEvent, event_id)
        if not event:
            raise NotFoundError("Calendar event not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(event, key, value)
        self.db.commit()
        self.db.refresh(event)
        return event

    def delete_event(self, event_id: UUID) -> None:
        event = self.db.get(AuditionCalendarEvent, event_id)
        if not event:
            raise NotFoundError("Calendar event not found")
        self.db.delete(event)
        self.db.commit()

    def list_availability(self) -> list[AvailabilityBlock]:
        return list(self.db.scalars(select(AvailabilityBlock).order_by(AvailabilityBlock.start_date.asc())))

    def create_availability(self, payload: AvailabilityBlockCreate) -> AvailabilityBlock:
        block = AvailabilityBlock(**payload.model_dump())
        self.db.add(block)
        self.db.commit()
        self.db.refresh(block)
        return block

    def update_availability(self, block_id: UUID, payload: AvailabilityBlockUpdate) -> AvailabilityBlock:
        block = self.db.get(AvailabilityBlock, block_id)
        if not block:
            raise NotFoundError("Availability block not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(block, key, value)
        self.db.commit()
        self.db.refresh(block)
        return block

    def delete_availability(self, block_id: UUID) -> None:
        block = self.db.get(AvailabilityBlock, block_id)
        if not block:
            raise NotFoundError("Availability block not found")
        self.db.delete(block)
        self.db.commit()

    def get_or_create_equipment_profile(self) -> ProfessionalEquipmentProfile:
        profile = self.db.scalars(select(ProfessionalEquipmentProfile).limit(1)).first()
        if profile:
            return profile
        profile = ProfessionalEquipmentProfile()
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_equipment_profile(self, payload: ProfessionalEquipmentProfileUpdate) -> ProfessionalEquipmentProfile:
        profile = self.get_or_create_equipment_profile()
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def list_platform_subscriptions(self) -> list[CastingPlatformSubscription]:
        self.ensure_default_platform_subscriptions()
        return list(
            self.db.scalars(
                select(CastingPlatformSubscription).order_by(CastingPlatformSubscription.platform_name.asc())
            )
        )

    def create_platform_subscription(
        self, payload: CastingPlatformSubscriptionCreate
    ) -> CastingPlatformSubscription:
        subscription = CastingPlatformSubscription(**payload.model_dump())
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def update_platform_subscription(
        self, subscription_id: UUID, payload: CastingPlatformSubscriptionUpdate
    ) -> CastingPlatformSubscription:
        subscription = self.db.get(CastingPlatformSubscription, subscription_id)
        if not subscription:
            raise NotFoundError("Casting platform subscription not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(subscription, key, value)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def ensure_default_platform_subscriptions(self) -> None:
        existing_rows = list(self.db.scalars(select(CastingPlatformSubscription)))
        existing = {item.platform_name for item in existing_rows}
        changed = False
        for item in existing_rows:
            has_subscription_details = any(
                [
                    bool((item.subscription_level or "").strip()),
                    item.monthly_cost is not None,
                    item.annual_cost is not None,
                    item.renewal_date is not None,
                    bool((item.notes or "").strip()),
                ]
            )
            if not has_subscription_details and item.has_subscription:
                item.has_subscription = False
                changed = True
        for platform in DEFAULT_PLATFORMS:
            if platform in existing:
                continue
            self.db.add(CastingPlatformSubscription(platform_name=platform, has_subscription=False))
            changed = True
        if changed:
            self.db.commit()

    def today_platform_check_ins(self, user_timezone: str = "America/New_York") -> list[dict]:
        self.ensure_default_platform_subscriptions()
        today = self._local_today(user_timezone)
        subscriptions = list(
            self.db.scalars(
                select(CastingPlatformSubscription)
                .where(CastingPlatformSubscription.active.is_(True))
                .where(CastingPlatformSubscription.has_subscription.is_(True))
                .order_by(CastingPlatformSubscription.platform_name.asc())
            )
        )
        rows = []
        changed = False
        for subscription in subscriptions:
            check_in = self._daily_check_in(subscription, today, user_timezone)
            if check_in.id is None:
                changed = True
            rows.append(self._check_in_payload(check_in, subscription))
        if changed:
            self.db.commit()
            for row in rows:
                if not row.get("id"):
                    self.db.refresh(self.db.get(DailyPlatformCheckIn, row["id"]))
        return rows

    def read_today_platform_check_ins(
        self,
        user_timezone: str = "America/New_York",
        *,
        as_of: datetime | None = None,
    ) -> list[dict]:
        today = self._local_date(user_timezone, as_of=as_of)
        rows = self.db.execute(
            select(DailyPlatformCheckIn, CastingPlatformSubscription)
            .join(
                CastingPlatformSubscription,
                CastingPlatformSubscription.id
                == DailyPlatformCheckIn.platform_subscription_id,
            )
            .where(CastingPlatformSubscription.active.is_(True))
            .where(CastingPlatformSubscription.has_subscription.is_(True))
            .where(DailyPlatformCheckIn.check_date == today)
            .where(DailyPlatformCheckIn.timezone == user_timezone)
            .order_by(CastingPlatformSubscription.platform_name.asc())
        ).all()
        return [
            self._check_in_payload(check_in, subscription)
            for check_in, subscription in rows
        ]

    def update_today_platform_check_in(
        self,
        subscription_id: UUID,
        payload: DailyPlatformCheckInUpdate,
        user_timezone: str = "America/New_York",
    ) -> dict:
        subscription = self.db.get(CastingPlatformSubscription, subscription_id)
        if not subscription:
            raise NotFoundError("Casting platform subscription not found")
        timezone_name = payload.timezone or user_timezone
        today = self._local_today(timezone_name)
        check_in = self._daily_check_in(subscription, today, timezone_name)
        data = payload.model_dump(exclude_unset=True)
        if "checked_today" in data:
            check_in.checked_today = bool(data["checked_today"])
            check_in.checked_at = datetime.now(timezone.utc) if check_in.checked_today else None
        if "notes" in data:
            check_in.notes = data["notes"]
        check_in.timezone = timezone_name
        if check_in.checked_today:
            ActorWorkEventService(self.db).platform_check_in(check_in)
        self.db.commit()
        return self._check_in_payload(check_in, subscription)

    def dashboard(self) -> dict:
        self.refresh_freshness()
        return {
            "alerts": self.alerts(),
            "upcoming_events": self.upcoming_events(),
            "cost_dashboard": self.cost_dashboard(),
            "freshness_warnings": self.freshness_warnings(),
        }

    def upcoming_events(self) -> list[AuditionCalendarEvent]:
        now = datetime.now(timezone.utc)
        later = now + timedelta(days=30)
        return list(
            self.db.scalars(
                select(AuditionCalendarEvent)
                .where(AuditionCalendarEvent.start_datetime >= now)
                .where(AuditionCalendarEvent.start_datetime <= later)
                .order_by(AuditionCalendarEvent.start_datetime.asc())
            )
        )

    def alerts(self) -> list[dict]:
        events = self.upcoming_events()
        alerts: list[dict] = []
        now = datetime.now(timezone.utc)
        for event in events:
            start = self._aware(event.start_datetime)
            hours_until = (start - now).total_seconds() / 3600
            if event.event_type == "Self-Tape Due" and hours_until <= 24:
                alerts.append(self._alert("Self-tape due within 24 hours", "High", event))
            elif event.event_type == "Self-Tape Due" and hours_until <= 48:
                alerts.append(self._alert("Self-tape due within 48 hours", "Medium", event))
            if event.event_type == "In-Person Callback":
                opportunity = event.opportunity
                if opportunity and opportunity.audition_drive_time is not None and opportunity.audition_drive_time <= 2:
                    alerts.append(self._alert("In-person audition within 2 hours driving", "Medium", event))
        for event in self._overlapping_events(events):
            alerts.append(self._alert("Overlapping deadline", "High", event))
        return alerts

    def cost_dashboard(self) -> dict:
        submissions = list(
            self.db.scalars(
                select(Submission).options(selectinload(Submission.assets), selectinload(Submission.opportunity))
            )
        )
        submissions = [
            submission
            for submission in submissions
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
        total = sum(float(item.total_cost or 0) for item in submissions)
        submission_fees_total = sum(float(item.submission_fee or 0) for item in submissions)
        media_fees_total = sum(float(item.media_fee or 0) for item in submissions)
        travel_housing_total = sum(
            float(item.travel_cost or 0) + float(item.housing_cost or 0) + float(item.parking_cost or 0)
            for item in submissions
        )
        other_costs_total = sum(float(item.other_cost or 0) for item in submissions)
        subscriptions = [
            item
            for item in self.list_platform_subscriptions()
            if item.active and item.has_subscription
        ]
        monthly_subscription_total = sum(float(item.monthly_cost or 0) for item in subscriptions)
        annual_subscription_total = sum(float(item.annual_cost or 0) for item in subscriptions)
        estimated_monthly_subscription_spend = monthly_subscription_total + annual_subscription_total / 12
        subscriptions_by_platform = {
            item.platform_name: round(float(item.monthly_cost or 0) + float(item.annual_cost or 0) / 12, 2)
            for item in subscriptions
        }
        callbacks = [item for item in submissions if item.current_status in CALLBACK_STATUSES]
        bookings = [item for item in submissions if item.current_status == "Booked"]
        by_platform: dict[str, float] = {}
        by_archetype: dict[str, float] = {}
        for submission in submissions:
            platform = submission.opportunity.source.name if submission.opportunity and submission.opportunity.source else "Manual"
            by_platform[platform] = by_platform.get(platform, 0) + float(submission.total_cost or 0)
            archetypes = {name for asset in submission.assets for name in asset.archetype_names} or {"Uncategorized"}
            for archetype in archetypes:
                by_archetype[archetype] = by_archetype.get(archetype, 0) + float(submission.total_cost or 0)
        return {
            "total_spent": round(total, 2),
            "cost_per_callback": round(total / len(callbacks), 2) if callbacks else 0,
            "cost_per_booking": round(total / len(bookings), 2) if bookings else 0,
            "costs_by_platform": {key: round(value, 2) for key, value in by_platform.items()},
            "costs_by_archetype": {key: round(value, 2) for key, value in by_archetype.items()},
            "subscriptions": subscriptions_by_platform,
            "subscription_monthly_total": round(monthly_subscription_total, 2),
            "subscription_annual_total": round(annual_subscription_total, 2),
            "estimated_monthly_subscription_spend": round(estimated_monthly_subscription_spend, 2),
            "submission_fees_total": round(submission_fees_total, 2),
            "media_fees_total": round(media_fees_total, 2),
            "travel_housing_total": round(travel_housing_total, 2),
            "other_costs_total": round(other_costs_total, 2),
        }

    def freshness_warnings(self) -> list[dict]:
        warnings = []
        for asset in self.db.scalars(select(Asset).order_by(Asset.asset_name.asc())):
            message = self._freshness_message(asset)
            if message:
                warnings.append(
                    {
                        "asset_id": asset.id,
                        "asset_name": asset.asset_name,
                        "asset_type": asset.asset_type,
                        "freshness_status": asset.freshness_status,
                        "message": message,
                    }
                )
        return warnings

    def refresh_freshness(self) -> None:
        changed = False
        for asset in self.db.scalars(select(Asset)):
            current = asset.freshness_status
            self._apply_freshness(asset)
            changed = changed or current != asset.freshness_status
        if changed:
            self.db.commit()

    def _apply_freshness(self, asset: Asset) -> None:
        today = date.today()
        reference = asset.last_updated_date or asset.upload_date or asset.created_at.date()
        age_days = (today - reference).days
        unused_days = (today - asset.last_used_date).days if asset.last_used_date else None
        if asset.asset_type == "Headshot" and age_days >= 18 * 30:
            asset.freshness_status = "Outdated"
        elif asset.asset_type == "Reel" and age_days >= 24 * 30:
            asset.freshness_status = "Outdated"
        elif asset.asset_type == "Resume" and age_days >= 180:
            asset.freshness_status = "Needs Review"
        elif unused_days is not None and unused_days >= 180:
            asset.freshness_status = "Needs Review"
        elif age_days >= 365:
            asset.freshness_status = "Aging"
        else:
            asset.freshness_status = "Current"

    def _freshness_message(self, asset: Asset) -> str | None:
        today = date.today()
        reference = asset.last_updated_date or asset.upload_date or asset.created_at.date()
        age_days = (today - reference).days
        unused_days = (today - asset.last_used_date).days if asset.last_used_date else None
        if asset.asset_type == "Headshot" and age_days >= 18 * 30:
            return "Headshot is older than 18 months."
        if asset.asset_type == "Reel" and age_days >= 24 * 30:
            return "Reel is older than 24 months."
        if asset.asset_type == "Resume" and age_days >= 180:
            return "Resume has not been updated recently."
        if unused_days is not None and unused_days >= 180:
            return "Asset has not been used in 6+ months."
        return None

    def _overlapping_events(self, events: list[AuditionCalendarEvent]) -> list[AuditionCalendarEvent]:
        overlaps = []
        for index, event in enumerate(events):
            event_end = self._aware(event.end_datetime or event.start_datetime)
            for other in events[index + 1 :]:
                other_start = self._aware(other.start_datetime)
                if other_start <= event_end:
                    overlaps.append(event)
                    break
        return overlaps

    def _alert(self, title: str, severity: str, event: AuditionCalendarEvent) -> dict:
        return {
            "alert_type": event.event_type,
            "severity": severity,
            "title": title,
            "message": f"{event.title} starts {event.start_datetime.isoformat()}",
            "related_id": event.id,
        }

    def _aware(self, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _local_today(self, timezone_name: str) -> date:
        return self._local_date(timezone_name)

    def _local_date(
        self, timezone_name: str, *, as_of: datetime | None = None
    ) -> date:
        try:
            tz = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("America/New_York")
        if as_of is None:
            return datetime.now(tz).date()
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        return as_of.astimezone(tz).date()

    def _daily_check_in(
        self,
        subscription: CastingPlatformSubscription,
        check_date: date,
        timezone_name: str,
    ) -> DailyPlatformCheckIn:
        check_in = self.db.scalars(
            select(DailyPlatformCheckIn)
            .where(DailyPlatformCheckIn.platform_subscription_id == subscription.id)
            .where(DailyPlatformCheckIn.check_date == check_date)
            .where(DailyPlatformCheckIn.timezone == timezone_name)
            .limit(1)
        ).first()
        if check_in:
            return check_in
        check_in = DailyPlatformCheckIn(
            platform_subscription_id=subscription.id,
            check_date=check_date,
            timezone=timezone_name,
            checked_today=False,
        )
        self.db.add(check_in)
        self.db.flush()
        return check_in

    def _check_in_payload(
        self,
        check_in: DailyPlatformCheckIn,
        subscription: CastingPlatformSubscription,
    ) -> dict:
        return {
            "id": check_in.id,
            "platform_subscription_id": subscription.id,
            "platform_name": subscription.platform_name,
            "has_subscription": subscription.has_subscription,
            "subscription_level": subscription.subscription_level,
            "active": subscription.active,
            "check_date": check_in.check_date,
            "timezone": check_in.timezone,
            "checked_today": check_in.checked_today,
            "checked_at": check_in.checked_at,
            "notes": check_in.notes,
            "created_at": check_in.created_at,
            "updated_at": check_in.updated_at,
        }
