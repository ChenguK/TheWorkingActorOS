from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.capability_service import CapabilityService

router = APIRouter()


@router.get("/capabilities")
def capabilities(db: Session = Depends(get_db)):
    return CapabilityService(db).system_capabilities()
