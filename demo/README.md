# Floxo pipeline demo

This script runs the Floxo video analytics pipeline locally: person detection, tracking, homography onto a 1920×1080 floor plan, heatmap generation, path extraction, and metric computation. It then calls the same suggestion engine used by the API to produce layout recommendations.

By default the sample URL does not serve a real video file, so the script builds synthetic customer trajectories (entrance → aisles → checkout, with dwell segments) and runs the analytics on that data. Replace `SAMPLE_VIDEO_URL` in `run_demo.py` with a direct link to an MP4, or place your own file at `demo/output/sample_input.mp4` after a successful download, to exercise the full YOLO + ByteTrack path.

## Prerequisites

From the repository root (`floxo-api/`):

```bash
pip install -r requirements.txt
```

## Run

```bash
python demo/run_demo.py
```

## Outputs

Files are written under `demo/output/`:

- `heatmap.png` — density heatmap on the floor plan
- `paths.json` — smoothed visitor paths
- `metrics.json` — analytics payload (dwell, congestion, dead zones, traffic flow, etc.)
- `suggestions.json` — ranked layout suggestions

Retail security camera footage aligned with your calibration will produce the most meaningful heatmaps and zone metrics.
