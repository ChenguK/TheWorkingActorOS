from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.actor_profile import ActorProfileBase, ActorProfileCreate, ActorProfileUpdate
from app.services.actor_profile_service import ActorProfileService

router = APIRouter()


@router.get("", response_model=ActorProfileBase | None)
def get_actor_profile(db: Session = Depends(get_db)):
    return ActorProfileService(db).get_or_none()


@router.put("", response_model=ActorProfileBase)
def upsert_actor_profile(payload: ActorProfileCreate, db: Session = Depends(get_db)):
    try:
        return ActorProfileService(db).create_or_replace(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("", response_model=ActorProfileBase)
def update_actor_profile(payload: ActorProfileUpdate, db: Session = Depends(get_db)):
    try:
        return ActorProfileService(db).update(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

