import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.analytics_result import AnalyticsResult
from app.models.floor_plan import FloorPlan
from app.models.job import Job
from app.models.video import Video
from app.schemas.requests import CreateJob
from app.schemas.responses import AnalyticsResultResponse, JobResponse
from app.tasks.process_video import process_video_task

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: CreateJob,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    video = await db.get(Video, body.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    floor_plan = await db.get(FloorPlan, video.floor_plan_id)
    if not floor_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    meta = floor_plan.metadata_json or {}
    canvas = meta.get("canvas") or {}
    width = int(meta.get("width") or canvas.get("width") or 1920)
    height = int(meta.get("height") or canvas.get("height") or 1080)
    row = Job(
        video_id=body.video_id,
        calibration_json=body.calibration_json,
        status="queued",
        progress_pct=0,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    process_video_task.delay(
        str(row.id),
        video.storage_path,
        body.calibration_json,
        width,
        height,
    )
    return JobResponse.model_validate(row)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    row = await db.get(Job, job_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_validate(row)


@router.get("/{job_id}/results", response_model=list[AnalyticsResultResponse])
async def get_job_results(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    result = await db.execute(select(AnalyticsResult).where(AnalyticsResult.job_id == job_id))
    rows = result.scalars().all()
    return [AnalyticsResultResponse.model_validate(r) for r in rows]
