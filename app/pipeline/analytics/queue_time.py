from __future__ import annotations

import cv2
import numpy as np


def _dist_to_zone(x: float, y: float, poly: list) -> float:
    arr = np.array(poly, dtype=np.float32).reshape(-1, 1, 2)
    d = cv2.pointPolygonTest(arr, (float(x), float(y)), True)
    return float(abs(d))


def estimate_queue_time(
    trajectories: dict[int, list[tuple[int, float, float]]],
    checkout_zones: list[dict],
    fps: float,
    proximity: float | None = None,
    stationary_speed: float = 8.0,
) -> dict:
    if fps <= 0:
        fps = 30.0
    if not checkout_zones:
        return {"checkout_zones": []}

    all_xy = []
    for pts in trajectories.values():
        for _, x, y in pts:
            all_xy.append((x, y))
    if not all_xy:
        return {"checkout_zones": []}

    arr = np.array(all_xy, dtype=np.float64)
    span = float(np.mean(np.ptp(arr, axis=0)))
    prox = float(proximity) if proximity is not None else max(span * 0.03, 8.0)

    results = []
    for zone in checkout_zones:
        zid = str(zone.get("id", "unknown"))
        poly = zone.get("polygon")
        if not poly:
            results.append({"zone_id": zid, "avg_wait_seconds": 0.0, "max_wait_seconds": 0.0, "samples": 0})
            continue

        waits: list[float] = []
        for _tid, pts in trajectories.items():
            if len(pts) < 3:
                continue
            ordered = sorted(pts, key=lambda p: p[0])
            near = [
                p
                for p in ordered
                if _dist_to_zone(p[1], p[2], poly) <= prox or cv2.pointPolygonTest(np.array(poly, dtype=np.float32).reshape(-1, 1, 2), (float(p[1]), float(p[2])), False) >= 0
            ]
            if len(near) < 3:
                continue
            xy = np.array([[p[1], p[2]] for p in near], dtype=np.float64)
            path_len = float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1)))
            frames = int(near[-1][0] - near[0][0] + 1)
            dur_s = frames / fps
            speed = path_len / max(dur_s, 1e-6)
            if speed <= stationary_speed and dur_s >= 1.0:
                waits.append(dur_s)

        if waits:
            results.append(
                {
                    "zone_id": zid,
                    "avg_wait_seconds": float(np.mean(waits)),
                    "max_wait_seconds": float(np.max(waits)),
                    "samples": len(waits),
                }
            )
        else:
            results.append({"zone_id": zid, "avg_wait_seconds": 0.0, "max_wait_seconds": 0.0, "samples": 0})

    return {"checkout_zones": results, "proximity_threshold": prox}
