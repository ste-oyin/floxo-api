from __future__ import annotations

import numpy as np


def compute_dwell_zones(
    trajectories: dict[int, list[tuple[int, float, float]]],
    fps: float,
    threshold_seconds: float,
    radius: float | None = None,
    grid_cells: int = 24,
) -> dict:
    if fps <= 0:
        fps = 30.0
    if not trajectories:
        return {"zones": [], "grid_size": grid_cells}

    all_xy = np.concatenate([np.array([[p[1], p[2]] for p in pts], dtype=np.float64) for pts in trajectories.values() if pts])
    if len(all_xy) == 0:
        return {"zones": [], "grid_size": grid_cells}

    span = np.ptp(all_xy, axis=0)
    base = float(min(span[0], span[1])) if span.min() > 1e-6 else 50.0
    r = float(radius) if radius is not None else max(base * 0.02, 5.0)

    dwell_samples: list[tuple[float, float, float]] = []
    thresh_frames = max(1, int(threshold_seconds * fps))

    for pts in trajectories.values():
        if len(pts) < 2:
            continue
        ordered = sorted(pts, key=lambda p: p[0])
        runs: list[list[tuple[int, float, float]]] = []
        cur = [ordered[0]]
        for p in ordered[1:]:
            if p[0] - cur[-1][0] <= 1:
                cur.append(p)
            else:
                runs.append(cur)
                cur = [p]
        runs.append(cur)

        for seg in runs:
            if len(seg) < 2:
                continue
            xy_seg = np.array([[p[1], p[2]] for p in seg], dtype=np.float64)
            spread = float(np.max(np.linalg.norm(xy_seg - xy_seg.mean(axis=0), axis=1)))
            frame_span = int(seg[-1][0] - seg[0][0] + 1)
            if spread <= r and frame_span >= thresh_frames:
                cx, cy = float(xy_seg[:, 0].mean()), float(xy_seg[:, 1].mean())
                dwell_time = frame_span / fps
                dwell_samples.append((cx, cy, dwell_time))

    if not dwell_samples:
        return {"zones": [], "grid_size": grid_cells, "dwell_radius": r}

    xs = np.array([s[0] for s in dwell_samples])
    ys = np.array([s[1] for s in dwell_samples])
    xmin, xmax = float(xs.min()), float(xs.max())
    ymin, ymax = float(ys.min()), float(ys.max())
    gx = max(grid_cells, 1)
    cell_w = (xmax - xmin) / gx + 1e-9
    cell_h = (ymax - ymin) / gx + 1e-9

    buckets: dict[tuple[int, int], list[tuple[float, float, float]]] = {}
    for cx, cy, dt in dwell_samples:
        ix = int(np.clip((cx - xmin) / cell_w, 0, gx - 1))
        iy = int(np.clip((cy - ymin) / cell_h, 0, gx - 1))
        buckets.setdefault((ix, iy), []).append((cx, cy, dt))

    zones = []
    for (ix, iy), items in buckets.items():
        cx = float(np.mean([t[0] for t in items]))
        cy = float(np.mean([t[1] for t in items]))
        avg_dwell = float(np.mean([t[2] for t in items]))
        visitor_count = len(items)
        zones.append(
            {
                "grid_index": [ix, iy],
                "center": [cx, cy],
                "avg_dwell_time": avg_dwell,
                "visitor_count": visitor_count,
            }
        )

    return {"zones": zones, "grid_size": gx, "dwell_radius": r}
