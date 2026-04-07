from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.config import settings
from app.db.session import _resolved_database_url
from app.models.video import Video
from app.pipeline.orchestrator import run_pipeline
from app.services import analytics_service, job_service
from app.storage import supabase_storage

logger = logging.getLogger(__name__)


def _make_session_factory() -> tuple:
    """Create a fresh engine + session factory isolated from the API server's pool."""
    engine = create_async_engine(
        _resolved_database_url(),
        future=True,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        max_overflow=0,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def _fail(job_id: UUID, message: str) -> None:
    engine, Session = _make_session_factory()
    try:
        async with Session() as db:
            await job_service.update_job_status(
                db,
                job_id,
                "failed",
                progress_pct=0,
                error_message=message[:8000],
            )
            await db.commit()
    finally:
        await engine.dispose()


async def _run_pipeline_job(
    job_id: UUID,
    video_storage_path: str,
    calibration_json: dict,
    floor_plan_width: int,
    floor_plan_height: int,
) -> None:
    engine, Session = _make_session_factory()
    tmp_path: str | None = None
    fp_id: UUID | None = None
    video_id: UUID | None = None

    try:
        async with Session() as db:
            job = await job_service.get_job(db, job_id)
            if job is None or job.video is None:
                raise ValueError("job or video not found")
            fp_id = job.video.floor_plan_id
            video_id = job.video.id
            cal = job.calibration_json or calibration_json
            await job_service.update_job_status(db, job_id, "detecting", 10)
            await db.commit()

        raw = supabase_storage.download_file(settings.supabase_video_bucket, video_storage_path)
        suffix = Path(video_storage_path).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        async with Session() as db:
            await job_service.update_job_status(db, job_id, "processing", 30)
            await db.commit()

        assert tmp_path is not None
        result = run_pipeline(
            tmp_path,
            cal,
            floor_plan_width,
            floor_plan_height,
        )
        metrics = result.metrics
        heatmap_png = result.heatmap_image
        paths = result.paths

        async with Session() as db:
            await job_service.update_job_status(db, job_id, "uploading", 80)
            await db.commit()

        heatmap_key = f"heatmaps/{job_id}.png"
        heatmap_ref = supabase_storage.upload_file(
            settings.supabase_results_bucket,
            heatmap_key,
            heatmap_png,
            "image/png",
        )

        assert fp_id is not None and video_id is not None
        async with Session() as db:
            await analytics_service.save_results(
                db,
                job_id,
                fp_id,
                metrics,
                heatmap_ref,
                paths,
            )
            await job_service.update_job_status(db, job_id, "complete", 100)
            await db.commit()

        try:
            supabase_storage.delete_file(settings.supabase_video_bucket, video_storage_path)
        except Exception as exc:
            logger.warning("raw video delete failed: %s", exc)

        async with Session() as db:
            v = await db.get(Video, video_id)
            if v is not None:
                v.storage_path = ""
                v.status = "processed"
            await db.commit()
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
        await engine.dispose()


@celery_app.task(name="process_video_task", bind=True, max_retries=2)
def process_video_task(
    self,
    job_id: str,
    video_storage_path: str,
    calibration_json: dict,
    floor_plan_width: int,
    floor_plan_height: int,
) -> None:
    jid = UUID(job_id)
    try:
        asyncio.run(
            _run_pipeline_job(
                jid,
                video_storage_path,
                calibration_json,
                floor_plan_width,
                floor_plan_height,
            )
        )
    except Exception as exc:
        logger.exception("process_video task failed")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120) from exc
        try:
            asyncio.run(_fail(jid, str(exc)))
        except Exception:
            logger.exception("could not record failure status")
        raise
