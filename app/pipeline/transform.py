from __future__ import annotations

import cv2
import numpy as np


def apply_homography(
    trajectories: dict[int, list[tuple[int, float, float]]],
    calibration_points: list[dict],
    floor_plan_size: tuple[int, int],
) -> dict[int, list[tuple[int, float, float]]]:
    if len(calibration_points) < 4:
        raise ValueError("At least four calibration point pairs are required for homography")

    src = np.array([p["camera"] for p in calibration_points], dtype=np.float32)
    dst = np.array([p["floor_plan"] for p in calibration_points], dtype=np.float32)
    h_mat, _ = cv2.findHomography(src, dst, method=cv2.RANSAC)
    if h_mat is None:
        raise ValueError("Homography estimation failed")

    w, h = floor_plan_size
    out: dict[int, list[tuple[int, float, float]]] = {}

    for tid, pts in trajectories.items():
        transformed: list[tuple[int, float, float]] = []
        for fr, x, y in pts:
            p = cv2.perspectiveTransform(np.array([[[x, y]]], dtype=np.float32), h_mat)[0, 0]
            fx = float(np.clip(p[0], 0.0, float(w - 1)))
            fy = float(np.clip(p[1], 0.0, float(h - 1)))
            transformed.append((int(fr), fx, fy))
        out[tid] = transformed

    return out
