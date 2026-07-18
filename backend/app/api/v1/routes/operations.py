from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.operations import (
    AuditionCalendarEventCreate,
    AuditionCalendarEventRead,
    AuditionCalendarEventUpdate,
    AvailabilityBlockCreate,
    AvailabilityBlockRead,
    AvailabilityBlockUpdate,
    CastingPlatformSubscriptionCreate,
    CastingPlatformSubscriptionRead,
    CastingPlatformSubscriptionUpdate,
    DailyPlatformCheckInRead,
    DailyPlatformCheckInUpdate,
    OperationsDashboardRead,
    ProfessionalEquipmentProfileRead,
    ProfessionalEquipmentProfileUpdate,
)
from app.services.operations_service import OperationsService

router = APIRouter()


@router.get("/dashboard", response_model=OperationsDashboardRead)
def get_operations_dashboard(db: Session = Depends(get_db)):
    return OperationsService(db).dashboard()


@router.get("/calendar/events", response_model=list[AuditionCalendarEventRead])
def list_calendar_events(db: Session = Depends(get_db)):
    return OperationsService(db).list_events()


@router.post("/calendar/events", response_model=AuditionCalendarEventRead, status_code=201)
def create_calendar_event(payload: AuditionCalendarEventCreate, db: Session = Depends(get_db)):
    return OperationsService(db).create_event(payload)


@router.patch("/calendar/events/{event_id}", response_model=AuditionCalendarEventRead)
def update_calendar_event(
    event_id: UUID, payload: AuditionCalendarEventUpdate, db: Session = Depends(get_db)
):
    return OperationsService(db).update_event(event_id, payload)


@router.delete("/calendar/events/{event_id}", status_code=204)
def delete_calendar_event(event_id: UUID, db: Session = Depends(get_db)):
    OperationsService(db).delete_event(event_id)


@router.get("/availability", response_model=list[AvailabilityBlockRead])
def list_availability(db: Session = Depends(get_db)):
    return OperationsService(db).list_availability()


@router.post("/availability", response_model=AvailabilityBlockRead, status_code=201)
def create_availability(payload: AvailabilityBlockCreate, db: Session = Depends(get_db)):
    return OperationsService(db).create_availability(payload)


@router.patch("/availability/{block_id}", response_model=AvailabilityBlockRead)
def update_availability(block_id: UUID, payload: AvailabilityBlockUpdate, db: Session = Depends(get_db)):
    return OperationsService(db).update_availability(block_id, payload)


@router.delete("/availability/{block_id}", status_code=204)
def delete_availability(block_id: UUID, db: Session = Depends(get_db)):
    OperationsService(db).delete_availability(block_id)


@router.get("/equipment-profile", response_model=ProfessionalEquipmentProfileRead)
def get_equipment_profile(db: Session = Depends(get_db)):
    return OperationsService(db).get_or_create_equipment_profile()


@router.put("/equipment-profile", response_model=ProfessionalEquipmentProfileRead)
def update_equipment_profile(payload: ProfessionalEquipmentProfileUpdate, db: Session = Depends(get_db)):
    return OperationsService(db).update_equipment_profile(payload)


@router.get("/platform-subscriptions", response_model=list[CastingPlatformSubscriptionRead])
def list_platform_subscriptions(db: Session = Depends(get_db)):
    return OperationsService(db).list_platform_subscriptions()


@router.post("/platform-subscriptions", response_model=CastingPlatformSubscriptionRead, status_code=201)
def create_platform_subscription(
    payload: CastingPlatformSubscriptionCreate,
    db: Session = Depends(get_db),
):
    return OperationsService(db).create_platform_subscription(payload)


@router.patch("/platform-subscriptions/{subscription_id}", response_model=CastingPlatformSubscriptionRead)
def update_platform_subscription(
    subscription_id: UUID,
    payload: CastingPlatformSubscriptionUpdate,
    db: Session = Depends(get_db),
):
    return OperationsService(db).update_platform_subscription(subscription_id, payload)


@router.get("/platform-check-ins/today", response_model=list[DailyPlatformCheckInRead])
def list_today_platform_check_ins(
    timezone: str = "America/New_York",
    db: Session = Depends(get_db),
):
    return OperationsService(db).today_platform_check_ins(timezone)


@router.patch(
    "/platform-check-ins/today/{subscription_id}",
    response_model=DailyPlatformCheckInRead,
)
def update_today_platform_check_in(
    subscription_id: UUID,
    payload: DailyPlatformCheckInUpdate,
    timezone: str = "America/New_York",
    db: Session = Depends(get_db),
):
    return OperationsService(db).update_today_platform_check_in(subscription_id, payload, timezone)
