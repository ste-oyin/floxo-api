import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.analytics_result import AnalyticsResult
from app.models.floor_plan import FloorPlan
from app.models.job import Job
from app.models.location import Location
from app.models.organization import Organization
from app.models.video import Video

router = APIRouter()


class DashboardStats(BaseModel):
    floor_plans: int
    pending_jobs: int
    completed_analyses: int
    total_videos: int


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
):
    user_id = uuid.UUID(str(current_user["id"]))

    org_result = await db.execute(
        select(Organization.id).where(Organization.owner_user_id == user_id)
    )
    org_ids = [row[0] for row in org_result.all()]
    if not org_ids:
        return DashboardStats(floor_plans=0, pending_jobs=0, completed_analyses=0, total_videos=0)

    loc_result = await db.execute(
        select(Location.id).where(Location.org_id.in_(org_ids))
    )
    loc_ids = [row[0] for row in loc_result.all()]
    if not loc_ids:
        return DashboardStats(floor_plans=0, pending_jobs=0, completed_analyses=0, total_videos=0)

    fp_count = (await db.execute(
        select(func.count(FloorPlan.id)).where(FloorPlan.location_id.in_(loc_ids))
    )).scalar() or 0

    fp_ids_result = await db.execute(
        select(FloorPlan.id).where(FloorPlan.location_id.in_(loc_ids))
    )
    fp_ids = [row[0] for row in fp_ids_result.all()]

    if not fp_ids:
        return DashboardStats(floor_plans=0, pending_jobs=0, completed_analyses=0, total_videos=0)

    video_ids_result = await db.execute(
        select(Video.id).where(Video.floor_plan_id.in_(fp_ids))
    )
    video_ids = [row[0] for row in video_ids_result.all()]

    total_videos = len(video_ids)

    if not video_ids:
        return DashboardStats(floor_plans=fp_count, pending_jobs=0, completed_analyses=0, total_videos=0)

    pending = (await db.execute(
        select(func.count(Job.id)).where(
            Job.video_id.in_(video_ids),
            Job.status.in_(["queued", "processing"]),
        )
    )).scalar() or 0

    completed = (await db.execute(
        select(func.count(AnalyticsResult.id)).where(
            AnalyticsResult.floor_plan_id.in_(fp_ids)
        )
    )).scalar() or 0

    return DashboardStats(
        floor_plans=fp_count,
        pending_jobs=pending,
        completed_analyses=completed,
        total_videos=total_videos,
    )
