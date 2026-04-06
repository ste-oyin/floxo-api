from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.job import Job
from app.models.video import Video
from app.storage import supabase_storage
from app.tasks.process_video import celery_app

logger = logging.getLogger(__name__)


async def _cleanup() -> int:
    removed = 0
    async with AsyncSessionLocal() as db:
        video_ids = select(Job.video_id).where(Job.status == "complete").distinct()
        q = await db.execute(
            select(Video).where(
                Video.storage_path != "",
                Video.storage_path.isnot(None),
                Video.id.in_(video_ids),
            )
        )
        rows = q.scalars().all()
        for video in rows:
            path = (video.storage_path or "").strip()
            if not path:
                continue
            try:
                supabase_storage.delete_file(settings.supabase_video_bucket, path)
                video.storage_path = ""
                video.status = "processed"
                removed += 1
            except Exception as exc:
                logger.warning("cleanup delete failed for %s: %s", path, exc)
        await db.commit()
    return removed


@celery_app.task(name="cleanup_videos")
def cleanup_videos_task() -> int:
    return asyncio.run(_cleanup())
