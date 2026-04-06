from __future__ import annotations

import numpy as np


def compute_congestion(
    trajectories: dict[int, list[tuple[int, float, float]]],
    fps: float,
    grid_size: int = 10,
    window_seconds: float = 2.0,
    threshold_ratio: float = 0.65,
) -> dict:
    if fps <= 0:
        fps = 30.0
    if grid_size < 1:
        grid_size = 1

    events: list[tuple[int, float, float]] = []
    for pts in trajectories.values():
        for fr, x, y in pts:
            events.append((int(fr), float(x), float(y)))

    if not events:
        return {"cells": [], "window_frames": int(window_seconds * fps), "threshold_ratio": threshold_ratio}

    events.sort(key=lambda e: e[0])
    frames = np.array([e[0] for e in events], dtype=np.int32)
    xy = np.array([[e[1], e[2]] for e in events], dtype=np.float64)
    xmin, ymin = float(xy[:, 0].min()), float(xy[:, 1].min())
    xmax, ymax = float(xy[:, 0].max()), float(xy[:, 1].max())
    cw = (xmax - xmin) / grid_size + 1e-9
    ch = (ymax - ymin) / grid_size + 1e-9

    win = max(1, int(window_seconds * fps))
    fmin, fmax = int(frames.min()), int(frames.max())
    max_per_window = np.zeros((grid_size, grid_size), dtype=np.int32)
    peak_frame = np.zeros((grid_size, grid_size), dtype=np.int32)

    for start in range(fmin, fmax + 1, max(1, win // 2)):
        end = start + win
        mask = (frames >= start) & (frames < end)
        if not np.any(mask):
            continue
        sub = xy[mask]
        counts = np.zeros((grid_size, grid_size), dtype=np.int32)
        for x, y in sub:
            ix = int(np.clip((x - xmin) / cw, 0, grid_size - 1))
            iy = int(np.clip((y - ymin) / ch, 0, grid_size - 1))
            counts[iy, ix] += 1
        over = counts > max_per_window
        max_per_window = np.maximum(max_per_window, counts)
        peak_frame = np.where(over, start, peak_frame)

    global_max = int(max_per_window.max()) if max_per_window.size else 0
    cutoff = max(1, int(threshold_ratio * max(global_max, 1)))

    cells = []
    for iy in range(grid_size):
        for ix in range(grid_size):
            score = int(max_per_window[iy, ix])
            if score >= cutoff and score > 0:
                cells.append(
                    {
                        "cell": [ix, iy],
                        "congestion_score": score,
                        "peak_window_start_frame": int(peak_frame[iy, ix]),
                    }
                )

    return {
        "cells": cells,
        "window_frames": win,
        "threshold_ratio": threshold_ratio,
        "global_peak_count": global_max,
        "bounds": {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax},
    }
