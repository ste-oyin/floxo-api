from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_result import AnalyticsResult
from app.services.suggestion_service import generate_suggestions


def _enrich_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested pipeline output into top-level keys for suggestion_service."""
    enriched = dict(metrics)
    dz = metrics.get("dead_zones")
    if isinstance(dz, dict):
        dead_list = dz.get("dead_zones", [])
        total_cells = dz.get("total_cells", 1)
        if isinstance(dead_list, list) and total_cells:
            enriched.setdefault("dead_zone_ratio", len(dead_list) / max(total_cells, 1))

    cg = metrics.get("congestion")
    if isinstance(cg, dict):
        cells = cg.get("cells", [])
        if isinstance(cells, list) and cells:
            scores = [float(c.get("congestion_score", 0)) for c in cells if isinstance(c, dict)]
            if scores:
                enriched.setdefault("congestion_score", max(scores) / 100.0)

    dw = metrics.get("dwell_zones")
    if isinstance(dw, dict):
        zones = dw.get("zones", [])
        if isinstance(zones, list) and zones:
            dwell_vals = [
                float(z.get("mean_dwell_seconds", z.get("avg_dwell", 0)))
                for z in zones if isinstance(z, dict)
            ]
            if dwell_vals:
                enriched.setdefault("mean_dwell_seconds", sum(dwell_vals) / len(dwell_vals))
                sorted_d = sorted(dwell_vals)
                mid = len(sorted_d) // 2
                enriched.setdefault("median_dwell_seconds", sorted_d[mid])

    pp = metrics.get("paths")
    if isinstance(pp, dict):
        enriched.setdefault("total_tracks", len(pp.get("tracks", pp.get("paths", []))))
    elif isinstance(pp, list):
        enriched.setdefault("total_tracks", len(pp))

    return enriched


async def save_results(
    db: AsyncSession,
    job_id: uuid.UUID,
    floor_plan_id: uuid.UUID,
    metrics: dict[str, Any],
    heatmap_path: str | None,
    paths: list[dict[str, Any]] | dict[str, Any],
) -> AnalyticsResult:
    enriched = _enrich_metrics(metrics)
    suggestions = generate_suggestions(enriched)
    paths_payload: dict[str, Any]
    if isinstance(paths, list):
        paths_payload = {"paths": paths}
    else:
        paths_payload = paths

    row = AnalyticsResult(
        job_id=job_id,
        floor_plan_id=floor_plan_id,
        metrics_json=metrics,
        heatmap_image_path=heatmap_path,
        paths_json=paths_payload,
        suggestions_json={"suggestions": suggestions},
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def get_latest_results(db: AsyncSession, floor_plan_id: uuid.UUID) -> AnalyticsResult | None:
    result = await db.execute(
        select(AnalyticsResult)
        .where(AnalyticsResult.floor_plan_id == floor_plan_id)
        .order_by(desc(AnalyticsResult.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_results_history(db: AsyncSession, floor_plan_id: uuid.UUID) -> list[AnalyticsResult]:
    result = await db.execute(
        select(AnalyticsResult)
        .where(AnalyticsResult.floor_plan_id == floor_plan_id)
        .order_by(desc(AnalyticsResult.created_at))
    )
    return list(result.scalars().all())


async def compare_floor_plans(
    db: AsyncSession, floor_plan_ids: list[uuid.UUID]
) -> dict[str, Any]:
    side_by_side: dict[str, dict[str, Any]] = {}
    for fp_id in floor_plan_ids:
        latest = await get_latest_results(db, fp_id)
        key = str(fp_id)
        if latest is None:
            side_by_side[key] = {"metrics": {}, "heatmap_image_path": None, "created_at": None}
        else:
            side_by_side[key] = {
                "metrics": dict(latest.metrics_json or {}),
                "heatmap_image_path": latest.heatmap_image_path,
                "created_at": latest.created_at.isoformat() if latest.created_at else None,
            }

    keys = list(side_by_side.keys())
    comparison: dict[str, Any] = {"metrics_delta": {}}
    if len(keys) >= 2:
        m0 = side_by_side[keys[0]].get("metrics") or {}
        m1 = side_by_side[keys[1]].get("metrics") or {}
        all_k = set(m0) | set(m1)
        for k in all_k:
            v0, v1 = m0.get(k), m1.get(k)
            if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                comparison["metrics_delta"][k] = float(v1) - float(v0)

    return {"floor_plans": side_by_side, "comparison": comparison}
