from __future__ import annotations

import json
import logging
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
FLOOR_W, FLOOR_H = 1920, 1080

SAMPLE_VIDEO_URL = "https://example.com/retail_walkthrough.mp4"


def _calibration_points() -> list[dict]:
    return [
        {"camera": [0.0, 0.0], "floor_plan": [0.0, 0.0]},
        {"camera": [1280.0, 0.0], "floor_plan": [float(FLOOR_W), 0.0]},
        {"camera": [1280.0, 720.0], "floor_plan": [float(FLOOR_W), float(FLOOR_H)]},
        {"camera": [0.0, 720.0], "floor_plan": [0.0, float(FLOOR_H)]},
    ]


def _download_video(url: str, dest: Path) -> bool:
    import httpx

    for verify in (True, False):
        try:
            r = httpx.get(url, follow_redirects=True, timeout=120.0, verify=verify)
            r.raise_for_status()
            if len(r.content) < 1024:
                return False
            dest.write_bytes(r.content)
            if not verify:
                logger.warning("Download used verify=False (SSL verification failed earlier).")
            return True
        except Exception as exc:
            last = exc
            if verify:
                continue
            logger.warning("Video download failed: %s", last)
            return False
    return False


def _lerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    return a * (1.0 - t) + b * t


def _segment(
    start: np.ndarray,
    end: np.ndarray,
    start_frame: int,
    n_frames: int,
    noise: float,
) -> list[tuple[int, float, float]]:
    out: list[tuple[int, float, float]] = []
    for i in range(n_frames):
        t = i / max(n_frames - 1, 1)
        p = _lerp(start, end, t) + np.random.normal(0.0, noise, 2)
        p[0] = float(np.clip(p[0], 0.0, FLOOR_W - 1.0))
        p[1] = float(np.clip(p[1], 0.0, FLOOR_H - 1.0))
        out.append((start_frame + i, float(p[0]), float(p[1])))
    return out


def _dwell_segment(
    center: np.ndarray,
    start_frame: int,
    n_frames: int,
    radius: float,
    rng: random.Random,
) -> list[tuple[int, float, float]]:
    out: list[tuple[int, float, float]] = []
    span = max(radius * 0.35, 4.0)
    for i in range(n_frames):
        jx = rng.uniform(-span, span)
        jy = rng.uniform(-span, span)
        p = center + np.array([jx, jy])
        p[0] = float(np.clip(p[0], 0.0, FLOOR_W - 1.0))
        p[1] = float(np.clip(p[1], 0.0, FLOOR_H - 1.0))
        out.append((start_frame + i, float(p[0]), float(p[1])))
    return out


def build_synthetic_trajectories(
    rng: random.Random | None = None,
) -> tuple[dict[int, list[tuple[int, float, float]]], float, float]:
    rng = rng or random.Random(42)
    np.random.seed(rng.randint(1, 10_000_000))

    entrance = np.array([960.0, 1020.0])
    left_aisle = np.array([280.0, 520.0])
    right_aisle = np.array([1640.0, 480.0])
    center_display = np.array([960.0, 420.0])
    checkout = np.array([1760.0, 140.0])
    rear = np.array([960.0, 160.0])

    n_tracks = rng.randint(20, 31)
    trajectories: dict[int, list[tuple[int, float, float]]] = {}
    max_frame = 0

    for tid in range(n_tracks):
        start_f = rng.randint(0, 360)
        pts: list[tuple[int, float, float]] = []
        mode = rng.random()

        gap = 2

        if mode < 0.35:
            seg1 = _segment(entrance, left_aisle, start_f, rng.randint(80, 140), 4.0)
            pts.extend(seg1)
            f = pts[-1][0] + gap
            seg2 = _segment(left_aisle, center_display, f, rng.randint(70, 120), 3.5)
            pts.extend(seg2)
            f = pts[-1][0] + gap
            dwell_n = rng.randint(100, 160)
            pts.extend(_dwell_segment(center_display, f, dwell_n, 12.0, rng))
            f = pts[-1][0] + gap
            pts.extend(_segment(center_display, checkout, f, rng.randint(100, 180), 4.0))
        elif mode < 0.65:
            seg1 = _segment(entrance, right_aisle, start_f, rng.randint(90, 150), 4.0)
            pts.extend(seg1)
            f = pts[-1][0] + gap
            seg2 = _segment(right_aisle, rear, f, rng.randint(60, 100), 3.0)
            pts.extend(seg2)
            f = pts[-1][0] + gap
            pts.extend(_segment(rear, checkout, f, rng.randint(80, 140), 3.5))
        else:
            seg1 = _segment(entrance, center_display, start_f, rng.randint(100, 160), 5.0)
            pts.extend(seg1)
            f = pts[-1][0] + gap
            dwell_n = rng.randint(90, 140)
            pts.extend(_dwell_segment(center_display, f, dwell_n, 10.0, rng))
            f = pts[-1][0] + gap
            seg2 = _segment(center_display, left_aisle, f, rng.randint(70, 110), 3.5)
            pts.extend(seg2)
            f = pts[-1][0] + gap
            pts.extend(_segment(left_aisle, checkout, f, rng.randint(120, 200), 4.5))

        trajectories[tid] = pts
        max_frame = max(max_frame, max(p[0] for p in pts))

    fps = 30.0
    duration = (max_frame + 1) / fps if max_frame >= 0 else 1.0
    return trajectories, fps, duration


def run_analytics_from_trajectories(
    trajectories: dict[int, list[tuple[int, float, float]]],
    floor_plan_width: int,
    floor_plan_height: int,
    fps: float,
    duration: float,
    dwell_threshold: float = 3.0,
):
    from app.pipeline.analytics.congestion import compute_congestion
    from app.pipeline.analytics.dead_zones import compute_dead_zones
    from app.pipeline.analytics.dwell import compute_dwell_zones
    from app.pipeline.analytics.engagement import compute_engagement
    from app.pipeline.analytics.heatmap import generate_heatmap
    from app.pipeline.analytics.paths import extract_paths
    from app.pipeline.analytics.peak_hours import compute_peak_patterns
    from app.pipeline.analytics.queue_time import estimate_queue_time
    from app.pipeline.analytics.traffic_flow import compute_traffic_flow
    from app.pipeline.analytics.transitions import compute_zone_transitions
    from app.pipeline.orchestrator import PipelineResult, _default_zones

    result = PipelineResult()
    zones = _default_zones(floor_plan_width, floor_plan_height)

    result.metrics["dwell_zones"] = compute_dwell_zones(trajectories, fps, dwell_threshold)
    result.metrics["traffic_flow"] = compute_traffic_flow(trajectories)
    result.metrics["congestion"] = compute_congestion(trajectories, fps)
    result.metrics["zone_transitions"] = compute_zone_transitions(trajectories, zones)
    result.metrics["engagement"] = compute_engagement(trajectories, zones, fps)
    result.metrics["dead_zones"] = compute_dead_zones(trajectories, floor_plan_width, floor_plan_height)
    result.metrics["queue_time"] = estimate_queue_time(trajectories, [], fps)
    result.metrics["peak_patterns"] = compute_peak_patterns(trajectories, fps, duration)
    result.paths = extract_paths(trajectories)
    result.metrics["paths"] = result.paths
    result.heatmap_image = generate_heatmap(trajectories, floor_plan_width, floor_plan_height)
    return result


def enrich_metrics_for_suggestions(metrics: dict, fps: float, paths: list) -> dict:
    m = dict(metrics)
    dz = metrics.get("dead_zones") or {}
    gs = int(dz.get("grid_size") or 10)
    dead_list = dz.get("dead_zones") or []
    cells_total = max(gs * gs, 1)
    m["dead_zone_ratio"] = len(dead_list) / float(cells_total)

    cg = metrics.get("congestion") or {}
    gpk = float(cg.get("global_peak_count") or 0)
    m["congestion_score"] = min(1.0, gpk / 18.0)

    m["total_tracks"] = len(paths)
    durs = [float(p["duration_frames"]) / fps for p in paths] if paths else []
    dzones = metrics.get("dwell_zones") or {}
    zlist = dzones.get("zones") or []
    if zlist:
        w = sum(int(z.get("visitor_count") or 0) for z in zlist)
        if w > 0:
            m["mean_dwell_seconds"] = float(
                sum(
                    float(z.get("avg_dwell_time") or 0.0) * int(z.get("visitor_count") or 0)
                    for z in zlist
                )
                / float(w)
            )
        elif durs:
            m["mean_dwell_seconds"] = float(np.mean(durs))
        else:
            m["mean_dwell_seconds"] = 0.0
    elif durs:
        m["mean_dwell_seconds"] = float(np.mean(durs))
    else:
        m["mean_dwell_seconds"] = 0.0

    if durs:
        m["median_dwell_seconds"] = float(np.median(durs))
    else:
        m["median_dwell_seconds"] = 0.0
    return m


def print_report(metrics: dict, suggestions: list) -> None:
    paths = metrics.get("paths") or []
    visitors = int(metrics.get("total_tracks") or len(paths))
    dwell_info = metrics.get("dwell_zones") or {}
    zones = dwell_info.get("zones") or []
    if zones:
        w = sum(int(z.get("visitor_count") or 0) for z in zones)
        if w > 0:
            mean_dw = sum(
                float(z.get("avg_dwell_time") or 0.0) * int(z.get("visitor_count") or 0)
                for z in zones
            ) / float(w)
        else:
            mean_dw = float(metrics.get("mean_dwell_seconds") or 0.0)
    else:
        mean_dw = float(metrics.get("mean_dwell_seconds") or 0.0)

    dz = metrics.get("dead_zones") or {}
    n_dead = len(dz.get("dead_zones") or [])

    cg = metrics.get("congestion") or {}
    cells = cg.get("cells") or []
    ranked = sorted(cells, key=lambda c: int(c.get("congestion_score") or 0), reverse=True)
    hotspots = ranked[:3]

    print()
    print("Floxo demo — summary")
    print("-" * 40)
    print(f"Total visitors detected: {visitors}")
    print(f"Average dwell time: {mean_dw:.1f}s")
    print(f"Dead zones (low-traffic cells): {n_dead}")
    print("Congestion hotspots (top 3 cells by peak occupancy):")
    if not hotspots:
        print("  (none above threshold)")
    for i, h in enumerate(hotspots, 1):
        cell = h.get("cell", [0, 0])
        sc = int(h.get("congestion_score") or 0)
        print(f"  {i}. cell {cell} score={sc}")

    print("Top layout suggestions:")
    for i, s in enumerate(suggestions[:3], 1):
        title = s.get("title", "")
        pri = s.get("priority", "")
        print(f"  {i}. [{pri}] {title}")
    print("-" * 40)


def main() -> None:
    from app.pipeline.orchestrator import _video_meta, run_pipeline
    from app.services.suggestion_service import generate_suggestions

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cal = _calibration_points()
    video_path = OUTPUT_DIR / "sample_input.mp4"

    used_synthetic = False
    if _download_video(SAMPLE_VIDEO_URL, video_path):
        try:
            result = run_pipeline(video_path, cal, FLOOR_W, FLOOR_H)
            fps, _ = _video_meta(video_path)
            if fps <= 0:
                fps = 30.0
        except Exception as exc:
            logger.warning("Pipeline failed on downloaded video, using synthetic data: %s", exc)
            used_synthetic = True
            traj, fps, duration = build_synthetic_trajectories()
            result = run_analytics_from_trajectories(traj, FLOOR_W, FLOOR_H, fps, duration)
    else:
        used_synthetic = True
        logger.info("Using synthetic trajectory data (set SAMPLE_VIDEO_URL to a real MP4 to use video).")
        traj, fps, duration = build_synthetic_trajectories()
        result = run_analytics_from_trajectories(traj, FLOOR_W, FLOOR_H, fps, duration)

    metrics = enrich_metrics_for_suggestions(result.metrics, fps, result.paths)
    suggestions = generate_suggestions(metrics)

    heatmap_path = OUTPUT_DIR / "heatmap.png"
    if result.heatmap_image:
        heatmap_path.write_bytes(result.heatmap_image)

    (OUTPUT_DIR / "paths.json").write_text(
        json.dumps(result.paths, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "metrics.json").write_text(
        json.dumps(metrics, indent=2, default=str),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "suggestions.json").write_text(
        json.dumps({"suggestions": suggestions}, indent=2),
        encoding="utf-8",
    )

    print_report(metrics, suggestions)
    if used_synthetic:
        print()
        print(
            "Note: outputs used synthetic trajectories. "
            "Point SAMPLE_VIDEO_URL at a downloadable MP4 for full detection + tracking."
        )


if __name__ == "__main__":
    main()
