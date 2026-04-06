from celery import Celery

from app.config import settings

celery_app = Celery(
    "floxo",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.process_video", "app.tasks.cleanup"],
)

celery_app.conf.task_default_queue = "floxo"
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True
