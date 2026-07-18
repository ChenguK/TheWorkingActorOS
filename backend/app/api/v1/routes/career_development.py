from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.constants import CAREER_TASK_IMPACTS, CAREER_TASK_PRIORITIES, CAREER_TASK_STATUSES
from app.core.errors import NotFoundError
from app.db.models import CareerDevelopmentTask
from app.schemas.agent import (
    CareerDevelopmentTaskCreate,
    CareerDevelopmentTaskRead,
    CareerDevelopmentTaskUpdate,
)
from app.services.actor_work_event_service import ActorWorkEventService

router = APIRouter()

VALID_PRIORITIES = set(CAREER_TASK_PRIORITIES)
VALID_STATUSES = set(CAREER_TASK_STATUSES)
VALID_IMPACTS = set(CAREER_TASK_IMPACTS)


def validate_task_values(data: dict) -> None:
    if data.get("priority") is not None and data["priority"] not in VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail="Priority must be Low, Medium, or High")
    if data.get("status") is not None and data["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Status must be Not Started, In Progress, Partially Completed, or Completed")
    if data.get("estimated_impact") is not None and data["estimated_impact"] not in VALID_IMPACTS:
        raise HTTPException(status_code=422, detail="Estimated impact must be Low, Medium, or High")


@router.get("/tasks", response_model=list[CareerDevelopmentTaskRead])
def list_tasks(
    status: str | None = None,
    archetype: str | None = None,
    priority: str | None = None,
    db: Session = Depends(get_db),
):
    statement = select(CareerDevelopmentTask).order_by(CareerDevelopmentTask.created_at.desc())
    if status:
        statement = statement.where(CareerDevelopmentTask.status == status)
    if archetype:
        statement = statement.where(CareerDevelopmentTask.related_archetype == archetype)
    if priority:
        statement = statement.where(CareerDevelopmentTask.priority == priority)
    return list(db.scalars(statement))


@router.post("/tasks", response_model=CareerDevelopmentTaskRead, status_code=201)
def create_task(payload: CareerDevelopmentTaskCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    validate_task_values(data)
    if data["status"] == "Completed":
        data["completed_at"] = datetime.utcnow()
    task = CareerDevelopmentTask(**data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=CareerDevelopmentTaskRead)
def get_task(task_id: UUID, db: Session = Depends(get_db)):
    task = db.get(CareerDevelopmentTask, task_id)
    if not task:
        raise NotFoundError("Career development task not found")
    return task


@router.patch("/tasks/{task_id}", response_model=CareerDevelopmentTaskRead)
def update_task(task_id: UUID, payload: CareerDevelopmentTaskUpdate, db: Session = Depends(get_db)):
    task = db.get(CareerDevelopmentTask, task_id)
    if not task:
        raise NotFoundError("Career development task not found")
    data = payload.model_dump(exclude_unset=True)
    validate_task_values(data)
    for key, value in data.items():
        setattr(task, key, value)
    if data.get("status") == "Completed" and task.completed_at is None:
        task.completed_at = datetime.utcnow()
        ActorWorkEventService(db).career_task_completed(task)
    if data.get("status") in {"Not Started", "In Progress", "Partially Completed"}:
        task.completed_at = None
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/complete", response_model=CareerDevelopmentTaskRead)
def complete_task(task_id: UUID, db: Session = Depends(get_db)):
    task = db.get(CareerDevelopmentTask, task_id)
    if not task:
        raise NotFoundError("Career development task not found")
    task.status = "Completed"
    task.completed_at = datetime.utcnow()
    ActorWorkEventService(db).career_task_completed(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: UUID, db: Session = Depends(get_db)):
    task = db.get(CareerDevelopmentTask, task_id)
    if not task:
        raise NotFoundError("Career development task not found")
    db.delete(task)
    db.commit()
