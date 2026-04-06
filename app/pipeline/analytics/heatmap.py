from __future__ import annotations

import io

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def generate_heatmap(
    trajectories: dict[int, list[tuple[int, float, float]]],
    width: int,
    height: int,
) -> bytes:
    if width <= 0 or height <= 0:
        return _png_from_array(np.zeros((1, 1, 3), dtype=np.uint8))

    acc = np.zeros((height, width), dtype=np.float64)
    for pts in trajectories.values():
        for _, x, y in pts:
            xi = int(np.clip(round(x), 0, width - 1))
            yi = int(np.clip(round(y), 0, height - 1))
            acc[yi, xi] += 1.0

    if acc.max() > 0:
        acc = gaussian_filter(acc, sigma=min(width, height) * 0.02 + 1.0)
        acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-9)
    else:
        acc = np.zeros_like(acc)

    rgb = _apply_jet_colormap(acc)
    return _png_from_array(rgb)


def _apply_jet_colormap(norm01: np.ndarray) -> np.ndarray:
    try:
        from matplotlib import colormaps

        cmap = colormaps["jet"]
    except Exception:
        from matplotlib.cm import get_cmap

        cmap = get_cmap("jet")

    rgba = cmap(np.clip(norm01.astype(np.float64), 0.0, 1.0))
    rgb = (rgba[..., :3] * 255.0).astype(np.uint8)
    return rgb


def _png_from_array(rgb: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG")
    return buf.getvalue()
