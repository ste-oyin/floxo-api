from __future__ import annotations

import numpy as np


def compute_traffic_flow(
    trajectories: dict[int, list[tuple[int, float, float]]],
    grid_size: int = 10,
) -> dict:
    if grid_size < 1:
        grid_size = 1

    all_pts = []
    for pts in trajectories.values():
        all_pts.extend([(p[1], p[2]) for p in pts])
    if not all_pts:
        return {"grid": [], "cols": grid_size, "rows": grid_size}

    arr = np.array(all_pts, dtype=np.float64)
    xmin, ymin = float(arr[:, 0].min()), float(arr[:, 1].min())
    xmax, ymax = float(arr[:, 0].max()), float(arr[:, 1].max())
    cw = (xmax - xmin) / grid_size + 1e-9
    ch = (ymax - ymin) / grid_size + 1e-9

    vec_sum = np.zeros((grid_size, grid_size, 2), dtype=np.float64)
    counts = np.zeros((grid_size, grid_size), dtype=np.int32)

    for pts in trajectories.values():
        if len(pts) < 2:
            continue
        ordered = sorted(pts, key=lambda p: p[0])
        for a, b in zip(ordered[:-1], ordered[1:]):
            mx = (a[1] + b[1]) * 0.5
            my = (a[2] + b[2]) * 0.5
            ix = int(np.clip((mx - xmin) / cw, 0, grid_size - 1))
            iy = int(np.clip((my - ymin) / ch, 0, grid_size - 1))
            dx, dy = b[1] - a[1], b[2] - a[2]
            vec_sum[iy, ix, 0] += dx
            vec_sum[iy, ix, 1] += dy
            counts[iy, ix] += 1

    grid = []
    for iy in range(grid_size):
        for ix in range(grid_size):
            n = int(counts[iy, ix])
            if n == 0:
                vx, vy, mag = 0.0, 0.0, 0.0
            else:
                vx = float(vec_sum[iy, ix, 0] / n)
                vy = float(vec_sum[iy, ix, 1] / n)
                mag = float(np.hypot(vx, vy))
            grid.append(
                {
                    "cell": [ix, iy],
                    "direction": [vx, vy],
                    "magnitude": mag,
                    "sample_count": n,
                }
            )

    return {
        "grid": grid,
        "cols": grid_size,
        "rows": grid_size,
        "bounds": {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax},
    }
