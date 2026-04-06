from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job


async def create_job(
    db: AsyncSession,
    video_id: uuid.UUID,
    calibration_json: dict[str, Any],
) -> Job:
    job = Job(video_id=video_id, calibration_json=calibration_json)
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def update_job_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    progress_pct: int | None = None,
    error_message: str | None = None,
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise ValueError("job not found")

    job.status = status
    if progress_pct is not None:
        job.progress_pct = max(0, min(100, progress_pct))
    if error_message is not None:
        job.error_message = error_message

    if job.started_at is None and status not in ("queued",):
        job.started_at = datetime.utcnow()
    if status in ("complete", "failed"):
        job.completed_at = datetime.utcnow()

    await db.flush()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await db.execute(
        select(Job).options(selectinload(Job.video)).where(Job.id == job_id)
    )
    return result.scalar_one_or_none()
