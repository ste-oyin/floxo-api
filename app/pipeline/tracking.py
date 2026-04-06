from __future__ import annotations

import numpy as np
import supervision as sv


def track_persons(
    detections: list[dict],
    fps: float,
) -> dict[int, list[tuple[int, float, float]]]:
    if fps <= 0:
        fps = 30.0

    tracker = sv.ByteTrack(frame_rate=float(fps))
    trajectories: dict[int, list[tuple[int, float, float]]] = {}

    for frame in sorted(detections, key=lambda f: f["frame_number"]):
        frame_number = int(frame["frame_number"])
        boxes = frame.get("boxes") or []
        confs = frame.get("confidences") or []

        if not boxes:
            empty = sv.Detections(
                xyxy=np.zeros((0, 4), dtype=np.float32),
                confidence=np.zeros((0,), dtype=np.float32),
                class_id=np.zeros((0,), dtype=np.int32),
            )
            tracker.update_with_detections(empty)
            continue

        xyxy = np.array(boxes, dtype=np.float32)
        confidence = np.array(confs, dtype=np.float32) if confs else np.ones(len(boxes), dtype=np.float32)
        class_id = np.zeros(len(boxes), dtype=np.int32)

        dets = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)
        tracked = tracker.update_with_detections(dets)

        if tracked.tracker_id is None or len(tracked) == 0:
            continue

        for i in range(len(tracked)):
            tid = int(tracked.tracker_id[i])
            x1, y1, x2, y2 = tracked.xyxy[i]
            cx = float((x1 + x2) * 0.5)
            cy = float((y1 + y2) * 0.5)
            trajectories.setdefault(tid, []).append((frame_number, cx, cy))

    return trajectories
