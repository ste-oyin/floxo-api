import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.analytics_result import AnalyticsResult
from app.models.floor_plan import FloorPlan
from app.schemas.responses import AnalyticsResultResponse, SuggestionsResponse

router = APIRouter()
suggestions_router = APIRouter(prefix="/suggestions")


@router.get("/{floor_plan_id}", response_model=AnalyticsResultResponse)
async def get_latest_analytics(
    floor_plan_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    fp = await db.get(FloorPlan, floor_plan_id)
    if not fp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    stmt = (
        select(AnalyticsResult)
        .where(AnalyticsResult.floor_plan_id == floor_plan_id)
        .order_by(AnalyticsResult.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analytics yet")
    return AnalyticsResultResponse.model_validate(row)


@router.get("/{floor_plan_id}/history", response_model=list[AnalyticsResultResponse])
async def get_analytics_history(
    floor_plan_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    fp = await db.get(FloorPlan, floor_plan_id)
    if not fp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    stmt = (
        select(AnalyticsResult)
        .where(AnalyticsResult.floor_plan_id == floor_plan_id)
        .order_by(AnalyticsResult.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [AnalyticsResultResponse.model_validate(r) for r in rows]


@suggestions_router.get("/{floor_plan_id}", response_model=SuggestionsResponse)
async def get_suggestions(
    floor_plan_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    fp = await db.get(FloorPlan, floor_plan_id)
    if not fp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    stmt = (
        select(AnalyticsResult)
        .where(AnalyticsResult.floor_plan_id == floor_plan_id)
        .order_by(AnalyticsResult.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row or row.suggestions_json is None:
        return SuggestionsResponse(floor_plan_id=floor_plan_id, suggestions=[])
    return SuggestionsResponse(floor_plan_id=floor_plan_id, suggestions=row.suggestions_json)
