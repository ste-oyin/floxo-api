import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.dependencies import require_admin
from app.models.floor_plan import FloorPlan
from app.models.job import Job
from app.schemas.responses import JobResponse
from app.tasks.process_video import process_video_task

router = APIRouter()


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(require_admin)],
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(Job).order_by(Job.created_at.desc())
    if status_filter:
        stmt = stmt.where(Job.status == status_filter)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [JobResponse.model_validate(r) for r in rows]


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(require_admin)],
):
    result = await db.execute(select(Job).options(selectinload(Job.video)).where(Job.id == job_id))
    row = result.scalar_one_or_none()
    if not row or not row.video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not row.video.storage_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Video has no storage path")
    floor_plan = await db.get(FloorPlan, row.video.floor_plan_id)
    if not floor_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    meta = floor_plan.metadata_json or {}
    width = int(meta.get("width", 1920))
    height = int(meta.get("height", 1080))
    row.status = "queued"
    row.progress_pct = 0
    row.error_message = None
    row.started_at = None
    row.completed_at = None
    await db.commit()
    await db.refresh(row)
    process_video_task.delay(
        str(row.id),
        row.video.storage_path,
        row.calibration_json or {},
        width,
        height,
    )
    return JobResponse.model_validate(row)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(require_admin)],
):
    row = await db.get(Job, job_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    row.status = "cancelled"
    await db.commit()
    await db.refresh(row)
    return JobResponse.model_validate(row)
