import logging
from pathlib import Path

from ultralytics import YOLO

from app.config import settings

logger = logging.getLogger(__name__)


def _resolve_model_path() -> str:
    return settings.yolo_model


def detect_persons(
    video_path: str | Path,
    frame_skip: int = 5,
    confidence: float = 0.3,
) -> list[dict]:
    path = Path(video_path)
    model = YOLO(_resolve_model_path())
    results_iter = model.predict(
        source=str(path),
        stream=True,
        verbose=False,
        conf=confidence,
        classes=[0],
        vid_stride=max(1, int(frame_skip)),
    )

    frame_detections: list[dict] = []
    for frame_idx, result in enumerate(results_iter):
        if not result.boxes or len(result.boxes) == 0:
            frame_detections.append(
                {
                    "frame_number": frame_idx,
                    "boxes": [],
                    "confidences": [],
                }
            )
            continue

        boxes_xyxy = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
        boxes_list = [tuple(map(float, row)) for row in boxes_xyxy]
        frame_detections.append(
            {
                "frame_number": frame_idx,
                "boxes": boxes_list,
                "confidences": [float(c) for c in confs],
            }
        )

    return frame_detections
