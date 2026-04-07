import logging
from pathlib import Path

import cv2

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
from app.pipeline.detection import detect_persons
from app.pipeline.tracking import track_persons
from app.pipeline.transform import apply_homography

logger = logging.getLogger(__name__)


class PipelineResult:
    def __init__(self) -> None:
        self.heatmap_image: bytes | None = None
        self.paths: list[dict] = []
        self.metrics: dict = {}


def _video_meta(path: Path) -> tuple[float, float]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        logger.warning("Could not open video %s; using default fps/duration", path)
        return 30.0, 0.0
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    nframes = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
    cap.release()
    duration = nframes / fps if fps > 0 else 0.0
    return fps, duration


def _default_zones(floor_w: int, floor_h: int, cols: int = 2, rows: int = 2) -> list[dict]:
    zones: list[dict] = []
    cw = floor_w / cols
    ch = floor_h / rows
    for j in range(rows):
        for i in range(cols):
            x0, y0 = i * cw, j * ch
            x1, y1 = x0 + cw, y0 + ch
            zid = f"zone_{i}_{j}"
            poly = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            zones.append({"id": zid, "polygon": poly})
    return zones


def _scale_to_floor(
    trajectories_cam: dict[int, list[tuple[int, float, float]]],
    video_path: Path,
    floor_size: tuple[int, int],
) -> dict[int, list[tuple[int, float, float]]]:
    """Linearly scale camera pixel coords to floor plan dimensions."""
    cap = cv2.VideoCapture(str(video_path))
    vw = float(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
    vh = float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
    cap.release()

    fw, fh = float(floor_size[0]), float(floor_size[1])
    sx, sy = fw / max(vw, 1.0), fh / max(vh, 1.0)

    out: dict[int, list[tuple[int, float, float]]] = {}
    for tid, pts in trajectories_cam.items():
        out[tid] = [
            (fr, min(x * sx, fw - 1), min(y * sy, fh - 1)) for fr, x, y in pts
        ]
    return out


def run_pipeline(
    video_path: str | Path,
    calibration_points: list[dict] | dict | None,
    floor_plan_width: int,
    floor_plan_height: int,
    frame_skip: int = 5,
    dwell_threshold: float = 3.0,
) -> PipelineResult:
    result = PipelineResult()
    path = Path(video_path)
    fps, duration = _video_meta(path)
    logger.info("Starting pipeline for %s (fps=%.3f, duration=%.3fs)", path, fps, duration)

    logger.info("Stage: person detection")
    frame_detections = detect_persons(path, frame_skip=frame_skip)
    approx_duration = len(frame_detections) * max(1, frame_skip) / fps if fps > 0 else 0.0
    if duration <= 0 and approx_duration > 0:
        duration = approx_duration

    logger.info("Stage: multi-object tracking (%d frames)", len(frame_detections))
    trajectories_cam = track_persons(frame_detections, fps)

    floor_size = (floor_plan_width, floor_plan_height)
    cal_list = calibration_points if isinstance(calibration_points, list) else []
    if len(cal_list) >= 4:
        logger.info("Stage: homography (%d tracks, %d cal points)", len(trajectories_cam), len(cal_list))
        trajectories = apply_homography(trajectories_cam, cal_list, floor_size)
    else:
        logger.info("Stage: scale-to-floor (%d tracks, no calibration)", len(trajectories_cam))
        trajectories = _scale_to_floor(trajectories_cam, path, floor_size)

    zones = _default_zones(floor_plan_width, floor_plan_height)

    logger.info("Stage: dwell zones")
    result.metrics["dwell_zones"] = compute_dwell_zones(trajectories, fps, dwell_threshold)

    logger.info("Stage: traffic flow")
    result.metrics["traffic_flow"] = compute_traffic_flow(trajectories)

    logger.info("Stage: congestion")
    result.metrics["congestion"] = compute_congestion(trajectories, fps)

    logger.info("Stage: zone transitions")
    result.metrics["zone_transitions"] = compute_zone_transitions(trajectories, zones)

    logger.info("Stage: engagement")
    result.metrics["engagement"] = compute_engagement(trajectories, zones, fps)

    logger.info("Stage: dead zones")
    result.metrics["dead_zones"] = compute_dead_zones(trajectories, floor_plan_width, floor_plan_height)

    logger.info("Stage: queue time")
    result.metrics["queue_time"] = estimate_queue_time(trajectories, [], fps)

    logger.info("Stage: peak patterns")
    result.metrics["peak_patterns"] = compute_peak_patterns(trajectories, fps, duration)

    logger.info("Stage: paths")
    result.paths = extract_paths(trajectories)
    result.metrics["paths"] = result.paths

    logger.info("Stage: heatmap")
    result.heatmap_image = generate_heatmap(trajectories, floor_plan_width, floor_plan_height)

    logger.info("Pipeline finished")
    return result
