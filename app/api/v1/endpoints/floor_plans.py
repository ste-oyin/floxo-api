import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.floor_plan import FloorPlan
from app.models.location import Location
from app.schemas.requests import CreateFloorPlan
from app.schemas.responses import FloorPlanCompareResponse, FloorPlanResponse

router = APIRouter()


@router.get("/compare", response_model=FloorPlanCompareResponse)
async def compare_floor_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
    first_id: uuid.UUID = Query(..., alias="first_id"),
    second_id: uuid.UUID = Query(..., alias="second_id"),
):
    a = await db.get(FloorPlan, first_id)
    b = await db.get(FloorPlan, second_id)
    if not a or not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    return FloorPlanCompareResponse(
        floor_plan_a=FloorPlanResponse.model_validate(a),
        floor_plan_b=FloorPlanResponse.model_validate(b),
        diff_summary={"overlap": 0.0},
    )


@router.get("", response_model=list[FloorPlanResponse])
async def list_floor_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
    location_id: uuid.UUID | None = None,
):
    stmt = select(FloorPlan)
    if location_id is not None:
        stmt = stmt.where(FloorPlan.location_id == location_id)
    result = await db.execute(stmt.order_by(FloorPlan.created_at.desc()))
    rows = result.scalars().all()
    return [FloorPlanResponse.model_validate(r) for r in rows]


@router.post("", response_model=FloorPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_floor_plan(
    body: CreateFloorPlan,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    loc = await db.get(Location, body.location_id)
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    row = FloorPlan(
        location_id=body.location_id,
        name=body.name,
        image_path=body.image_path or "",
        metadata_json=body.metadata_json,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return FloorPlanResponse.model_validate(row)


@router.get("/{floor_plan_id}", response_model=FloorPlanResponse)
async def get_floor_plan(
    floor_plan_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    row = await db.get(FloorPlan, floor_plan_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    return FloorPlanResponse.model_validate(row)


@router.put("/{floor_plan_id}", response_model=FloorPlanResponse)
async def update_floor_plan(
    floor_plan_id: uuid.UUID,
    body: CreateFloorPlan,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    row = await db.get(FloorPlan, floor_plan_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    row.location_id = body.location_id
    row.name = body.name
    row.image_path = body.image_path or ""
    row.metadata_json = body.metadata_json
    await db.commit()
    await db.refresh(row)
    return FloorPlanResponse.model_validate(row)


@router.delete("/{floor_plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_floor_plan(
    floor_plan_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    row = await db.get(FloorPlan, floor_plan_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    await db.delete(row)
    await db.commit()
    return None
