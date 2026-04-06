import uuid
from typing import Any

from pydantic import BaseModel, Field


class CreateOrganization(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class CreateLocation(BaseModel):
    org_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    address: str = ""


class CreateFloorPlan(BaseModel):
    location_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    image_path: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class VideoUploadUrlRequest(BaseModel):
    floor_plan_id: uuid.UUID
    filename: str = Field(..., min_length=1)
    content_type: str | None = None


class VideoRegisterRequest(BaseModel):
    floor_plan_id: uuid.UUID
    storage_path: str
    duration_seconds: float | None = None


class CreateJob(BaseModel):
    video_id: uuid.UUID
    calibration_json: dict[str, Any] = Field(default_factory=dict)


class AdminUserUpdate(BaseModel):
    email: str | None = None
    role: str | None = None
