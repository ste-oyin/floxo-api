from __future__ import annotations

import numpy as np


def extract_paths(trajectories: dict[int, list[tuple[int, float, float]]], window: int = 5) -> list[dict]:
    paths: list[dict] = []
    w = max(1, int(window) // 2 * 2 + 1)

    for tracker_id, pts in trajectories.items():
        if len(pts) < 2:
            continue

        pts_sorted = sorted(pts, key=lambda p: p[0])
        frames = np.array([p[0] for p in pts_sorted], dtype=np.float64)
        xy = np.array([[p[1], p[2]] for p in pts_sorted], dtype=np.float64)
        smoothed = _moving_average_2d(xy, w)

        total_distance = float(np.sum(np.linalg.norm(np.diff(smoothed, axis=0), axis=1)))
        duration_frames = int(frames.max() - frames.min() + 1)

        paths.append(
            {
                "tracker_id": int(tracker_id),
                "points": [[float(x), float(y)] for x, y in smoothed],
                "total_distance": total_distance,
                "duration_frames": duration_frames,
            }
        )

    return paths


def _moving_average_2d(xy: np.ndarray, window: int) -> np.ndarray:
    if len(xy) < window:
        return xy.copy()
    pad = window // 2
    kernel = np.ones(window, dtype=np.float64) / window
    padded = np.vstack([np.tile(xy[0], (pad, 1)), xy, np.tile(xy[-1], (pad, 1))])
    out = np.empty_like(xy)
    for d in range(2):
        out[:, d] = np.convolve(padded[:, d], kernel, mode="valid")
    return out
