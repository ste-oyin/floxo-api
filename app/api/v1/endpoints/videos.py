import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client

from app.config import settings
from app.db.session import get_db
from app.dependencies import get_current_user, get_supabase_client
from app.models.floor_plan import FloorPlan
from app.models.video import Video
from app.schemas.requests import VideoRegisterRequest, VideoUploadUrlRequest
from app.schemas.responses import UploadUrlResponse, VideoResponse

router = APIRouter()


@router.post("/upload-url", response_model=UploadUrlResponse, status_code=status.HTTP_200_OK)
async def create_upload_url(
    body: VideoUploadUrlRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_supabase_client)],
):
    fp = await db.get(FloorPlan, body.floor_plan_id)
    if not fp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    storage_path = f"{body.floor_plan_id}/{uuid.uuid4()}_{body.filename}"
    signed = supabase.storage.from_(settings.supabase_video_bucket).create_signed_upload_url(storage_path)
    signed_url = getattr(signed, "signed_url", None) or getattr(signed, "signedUrl", None)
    if not signed_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create signed upload URL",
        )
    token = getattr(signed, "token", None)
    path = getattr(signed, "path", None) or storage_path
    return UploadUrlResponse(signed_url=signed_url, path=str(path), token=token)


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def register_video(
    body: VideoRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    fp = await db.get(FloorPlan, body.floor_plan_id)
    if not fp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    row = Video(
        floor_plan_id=body.floor_plan_id,
        storage_path=body.storage_path,
        duration_seconds=body.duration_seconds,
        status="uploaded",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return VideoResponse.model_validate(row)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
):
    row = await db.get(Video, video_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return VideoResponse.model_validate(row)
