from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import require_admin

router = APIRouter()


@router.get("/health")
async def system_health(
    _: Annotated[dict, Depends(require_admin)],
):
    supabase_ok = bool(settings.supabase_url and settings.supabase_service_role_key)
    return {
        "api": "ok",
        "supabase_configured": supabase_ok,
        "environment": "development" if settings.debug else "production",
    }


@router.get("/metrics")
async def system_metrics(_: Annotated[dict, Depends(require_admin)]) -> dict[str, Any]:
    return {
        "queues": {"floxo": {"active": 0, "pending": 0}},
        "workers": 0,
        "processing": {
            "yolo_model": settings.yolo_model,
            "frame_skip": settings.frame_skip,
            "dwell_threshold_seconds": settings.dwell_threshold_seconds,
        },
    }
