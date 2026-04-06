from __future__ import annotations

import numpy as np


def compute_peak_patterns(
    trajectories: dict[int, list[tuple[int, float, float]]],
    fps: float,
    video_duration: float,
    interval_seconds: float = 60.0,
) -> dict:
    if fps <= 0:
        fps = 30.0
    if video_duration <= 0:
        video_duration = 1.0

    max_frame = 0
    for pts in trajectories.values():
        for p in pts:
            max_frame = max(max_frame, int(p[0]))
    if max_frame == 0 and not trajectories:
        return {"intervals": [], "interval_seconds": interval_seconds}

    duration_frames = max(max_frame + 1, int(video_duration * fps))
    interval_frames = max(1, int(interval_seconds * fps))
    num_bins = max(1, int(np.ceil(duration_frames / interval_frames)))

    active_per_bin = np.zeros(num_bins, dtype=np.int32)
    present: dict[int, set[int]] = {}

    for tid, pts in trajectories.items():
        tid_i = int(tid)
        for fr, _, _ in pts:
            b = min(int(fr) // interval_frames, num_bins - 1)
            present.setdefault(b, set()).add(tid_i)

    for b, ids in present.items():
        active_per_bin[b] = len(ids)

    intervals = []
    peak_idx = int(np.argmax(active_per_bin)) if num_bins else 0
    for b in range(num_bins):
        t0 = b * interval_seconds
        t1 = min((b + 1) * interval_seconds, video_duration)
        intervals.append(
            {
                "index": b,
                "time_start_seconds": float(t0),
                "time_end_seconds": float(t1),
                "active_persons": int(active_per_bin[b]),
            }
        )

    peak = intervals[peak_idx] if intervals else None

    return {
        "intervals": intervals,
        "interval_seconds": interval_seconds,
        "peak_interval": peak,
        "video_duration_seconds": float(video_duration),
    }
