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


def compute_zone_transitions(trajectories: dict[int, list[tuple[int, float, float]]], zones: list[dict]) -> dict:
    if not zones:
        return {"records": [], "matrix": {}}

    pair_counts: dict[tuple[str, str], int] = {}

    for pts in trajectories.values():
        if len(pts) < 2:
            continue
        ordered = sorted(pts, key=lambda p: p[0])
        for i in range(len(ordered) - 1):
            z0 = _zone_at(ordered[i][1], ordered[i][2], zones)
            z1 = _zone_at(ordered[i + 1][1], ordered[i + 1][2], zones)
            if z0 is not None and z1 is not None and z0 != z1:
                key = (z0, z1)
                pair_counts[key] = pair_counts.get(key, 0) + 1

    records = [
        {"zone_from": a, "zone_to": b, "count": c}
        for (a, b), c in sorted(pair_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    matrix = {f"{a}->{b}": c for (a, b), c in pair_counts.items()}

    return {"records": records, "matrix": matrix}
