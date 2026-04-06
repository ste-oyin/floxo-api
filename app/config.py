import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Floxo API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return json.loads(v)
        return v

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_video_bucket: str = "videos"
    supabase_results_bucket: str = "results"
    supabase_signed_upload_expires_seconds: int = 3600

    redis_url: str = "redis://localhost:6379/0"

    yolo_model: str = "yolov8n.pt"
    frame_skip: int = 5
    dwell_threshold_seconds: float = 3.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
