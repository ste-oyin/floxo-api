from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalyticsResult(Base):
    __tablename__ = "analytics_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    floor_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("floor_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    heatmap_image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    paths_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    suggestions_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    job: Mapped["Job"] = relationship(back_populates="analytics_results")
    floor_plan: Mapped["FloorPlan"] = relationship(back_populates="analytics_results")
