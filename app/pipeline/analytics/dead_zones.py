from __future__ import annotations

import numpy as np


def compute_dead_zones(
    trajectories: dict[int, list[tuple[int, float, float]]],
    width: int,
    height: int,
    grid_size: int = 10,
    percentile_cutoff: float = 10.0,
) -> dict:
    if grid_size < 1 or width <= 0 or height <= 0:
        return {"dead_zones": [], "grid_size": grid_size}

    counts = np.zeros((grid_size, grid_size), dtype=np.int64)
    cw = width / grid_size
    ch = height / grid_size

    total_hits = 0
    for pts in trajectories.values():
        for _, x, y in pts:
            ix = int(np.clip(x // cw, 0, grid_size - 1))
            iy = int(np.clip(y // ch, 0, grid_size - 1))
            counts[iy, ix] += 1
            total_hits += 1

    if total_hits == 0:
        return {"dead_zones": [], "grid_size": grid_size, "total_hits": 0}

    pct = 100.0 * counts / float(total_hits)
    dead = []
    for iy in range(grid_size):
        for ix in range(grid_size):
            p = float(pct[iy, ix])
            if p < percentile_cutoff:
                cx = (ix + 0.5) * cw
                cy = (iy + 0.5) * ch
                dead.append(
                    {
                        "cell": [ix, iy],
                        "center": [float(cx), float(cy)],
                        "traffic_percent": p,
                    }
                )

    return {"dead_zones": dead, "grid_size": grid_size, "total_hits": int(total_hits)}
