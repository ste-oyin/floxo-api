import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID
    plan_tier: str
    created_at: datetime


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    address: str
    created_at: datetime


class FloorPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    location_id: uuid.UUID
    name: str
    image_path: str
    metadata_json: dict[str, Any]
    created_at: datetime


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    floor_plan_id: uuid.UUID
    storage_path: str
    duration_seconds: float | None
    status: str
    uploaded_at: datetime


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    calibration_json: dict[str, Any]
    status: str
    progress_pct: int
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime


class AnalyticsResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    floor_plan_id: uuid.UUID
    metrics_json: dict[str, Any]
    heatmap_image_path: str | None
    paths_json: dict[str, Any] | None
    suggestions_json: dict[str, Any] | None
    created_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    created_at: datetime


class AuthVerifyResponse(BaseModel):
    user: UserResponse
    token_valid: bool = True


class UploadUrlResponse(BaseModel):
    signed_url: str
    path: str
    token: str | None = None


class FloorPlanCompareResponse(BaseModel):
    floor_plan_a: FloorPlanResponse
    floor_plan_b: FloorPlanResponse
    diff_summary: dict[str, Any] = Field(default_factory=dict)


class SuggestionsResponse(BaseModel):
    floor_plan_id: uuid.UUID
    suggestions: dict[str, Any] | list[Any] | None = None
