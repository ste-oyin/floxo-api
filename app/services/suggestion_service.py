from __future__ import annotations

from typing import Any


def _priority_rank(p: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(p.lower(), 3)


def generate_suggestions(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    dead = float(metrics.get("dead_zone_ratio") or 0.0)
    if dead > 0.2:
        out.append(
            {
                "title": "Rebalance layout for underused areas",
                "description": (
                    "A large share of the floor shows very low traffic relative to peak zones. "
                    "Consider repositioning fixtures or signage to draw visitors into dead zones."
                ),
                "priority": "high",
                "metric_source": "dead_zone_ratio",
                "expected_impact": "Higher utilization of low-traffic regions",
            }
        )
    elif dead >= 0.05:
        out.append(
            {
                "title": "Test alternate placements in quiet zones",
                "description": (
                    "Some areas register under 5% of peak traffic density. "
                    "Experiment with product placement or displays in these spots."
                ),
                "priority": "medium",
                "metric_source": "dead_zone_ratio",
                "expected_impact": "Moderate lift in zone engagement",
            }
        )

    congestion = float(metrics.get("congestion_score") or 0.0)
    if congestion >= 0.55:
        out.append(
            {
                "title": "Ease pinch points and widen primary paths",
                "description": (
                    "Traffic is highly concentrated in a few areas, increasing wait risk. "
                    "Widen aisles, stagger fixtures, or add secondary routes."
                ),
                "priority": "high",
                "metric_source": "congestion_score",
                "expected_impact": "Reduced crowding and smoother flow",
            }
        )
    elif congestion >= 0.35:
        out.append(
            {
                "title": "Smooth flow at busy junctions",
                "description": (
                    "Moderate congestion suggests occasional bottlenecks. "
                    "Review signage and shelf protrusions at the busiest intersections."
                ),
                "priority": "medium",
                "metric_source": "congestion_score",
                "expected_impact": "More even distribution of visitors",
            }
        )

    mean_dwell = float(metrics.get("mean_dwell_seconds") or 0.0)
    median_dwell = float(metrics.get("median_dwell_seconds") or 0.0)
    if mean_dwell < 2.0 and median_dwell < 2.0 and float(metrics.get("total_tracks") or 0) > 5:
        out.append(
            {
                "title": "Increase engagement in key zones",
                "description": (
                    "Dwell time is very short relative to traffic volume. "
                    "Add interactive displays, focal lighting, or promotional content to slow movement."
                ),
                "priority": "medium",
                "metric_source": "mean_dwell_seconds",
                "expected_impact": "Longer consideration time in priority zones",
            }
        )

    tracks = int(metrics.get("total_tracks") or 0)
    if tracks < 3:
        out.append(
            {
                "title": "Collect more footage for reliable insights",
                "description": (
                    "Very few distinct visitor tracks were observed. "
                    "Extend recording duration or adjust camera framing for better coverage."
                ),
                "priority": "low",
                "metric_source": "total_tracks",
                "expected_impact": "More stable metrics and suggestions",
            }
        )

    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for s in out:
        key = (s["title"], s["metric_source"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)

    unique.sort(key=lambda x: (_priority_rank(str(x.get("priority", "low"))), x["title"]))

    if len(unique) < 3:
        unique.append(
            {
                "title": "Schedule a follow-up capture",
                "description": (
                    "Re-run analysis after layout changes to validate impact on traffic and dwell time."
                ),
                "priority": "low",
                "metric_source": "pipeline",
                "expected_impact": "Measurable before/after comparison",
            }
        )
    if len(unique) < 3:
        unique.append(
            {
                "title": "Align camera calibration",
                "description": (
                    "Ensure calibration points match stable floor landmarks so heatmaps align with the plan."
                ),
                "priority": "medium",
                "metric_source": "pipeline",
                "expected_impact": "More accurate zone-level metrics",
            }
        )

    unique.sort(key=lambda x: (_priority_rank(str(x.get("priority", "low"))), x["title"]))
    dedup: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for s in unique:
        t = str(s.get("title", ""))
        if t in seen_titles:
            continue
        seen_titles.add(t)
        dedup.append(s)

    return dedup[:5] if len(dedup) > 5 else dedup
