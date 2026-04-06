from __future__ import annotations

import cv2
import numpy as np


def _zone_at(x: float, y: float, zones: list[dict]) -> str | None:
    for z in zones:
        poly = z.get("polygon")
        zid = z.get("id")
        if poly is None or zid is None:
            continue
        arr = np.array(poly, dtype=np.float32).reshape(-1, 1, 2)
        if cv2.pointPolygonTest(arr, (float(x), float(y)), False) >= 0:
            return str(zid)
    return None


def compute_engagement(
    trajectories: dict[int, list[tuple[int, float, float]]],
    zones: list[dict],
    fps: float,
    speed_threshold: float = 5.0,
) -> dict:
    if fps <= 0:
        fps = 30.0
    if not zones:
        return {"zones": []}

    zone_ids = [str(z["id"]) for z in zones if "id" in z]
    stopped = {z: 0 for z in zone_ids}
    passed = {z: 0 for z in zone_ids}
    visitors = {z: set() for z in zone_ids}

    for tid, pts in trajectories.items():
        if len(pts) < 2:
            continue
        ordered = sorted(pts, key=lambda p: p[0])
        i = 0
        while i < len(ordered):
            z = _zone_at(ordered[i][1], ordered[i][2], zones)
            if z is None:
                i += 1
                continue
            j = i + 1
            while j < len(ordered):
                z2 = _zone_at(ordered[j][1], ordered[j][2], zones)
                if z2 != z:
                    break
                j += 1
            seg = ordered[i:j]
            if z in visitors:
                visitors[z].add(int(tid))
            xy = np.array([[p[1], p[2]] for p in seg], dtype=np.float64)
            path_len = float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1))) if len(seg) >= 2 else 0.0
            frames = int(seg[-1][0] - seg[0][0] + 1)
            duration_s = frames / fps
            speed = path_len / max(duration_s, 1e-6)
            if speed < speed_threshold or duration_s >= 3.0:
                stopped[z] += 1
            else:
                passed[z] += 1
            i = j

    out = []
    for zid in zone_ids:
        s, p = stopped[zid], passed[zid]
        total = s + p
        rate = float(s / total) if total > 0 else 0.0
        out.append(
            {
                "zone_id": zid,
                "stopped_events": s,
                "pass_through_events": p,
                "engagement_rate": rate,
                "unique_visitors": len(visitors[zid]),
            }
        )

    return {"zones": out}
