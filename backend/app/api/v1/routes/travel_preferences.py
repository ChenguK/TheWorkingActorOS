from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import TravelPreference
from app.repositories.travel_preference import TravelPreferenceRepository
from app.schemas.travel_preference import TravelPreferenceCreate, TravelPreferenceRead, TravelPreferenceUpdate

router = APIRouter()


@router.get("/{actor_profile_id}", response_model=TravelPreferenceRead | None)
def get_travel_preference(actor_profile_id: UUID, db: Session = Depends(get_db)):
    return TravelPreferenceRepository(db).get_for_actor(actor_profile_id)


@router.put("", response_model=TravelPreferenceRead)
def upsert_travel_preference(payload: TravelPreferenceCreate, db: Session = Depends(get_db)):
    repo = TravelPreferenceRepository(db)
    existing = repo.get_for_actor(payload.actor_profile_id)
    data = payload.model_dump()
    if existing:
        preference = repo.apply_updates(existing, data)
    else:
        preference = repo.add(TravelPreference(**data))
    db.commit()
    return preference


@router.patch("/{preference_id}", response_model=TravelPreferenceRead)
def update_travel_preference(
    preference_id: UUID, payload: TravelPreferenceUpdate, db: Session = Depends(get_db)
):
    try:
        repo = TravelPreferenceRepository(db)
        preference = repo.get(preference_id)
        data = payload.model_dump(exclude_unset=True)
        next_local = data.get("max_local_drive_time", preference.max_local_drive_time)
        next_extended = data.get("extended_drive_time", preference.extended_drive_time)
        if next_extended < next_local:
            raise ValueError("Extended drive time must be greater than or equal to local drive time")
        preference = repo.apply_updates(preference, data)
        db.commit()
        return preference
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
