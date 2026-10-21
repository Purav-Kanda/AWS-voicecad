"""Shaded picture of a mesh, so the user can see what they are about to print.

A tiny z-buffer rasterizer. It avoids the sorting glitches that plotting libraries
show on long, thin triangles, and it only needs numpy and Pillow.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

_BASE = np.array([0.23, 0.48, 0.86])
_BACKGROUND = np.array([0.957, 0.965, 0.980])


def _view_matrix(azimuth: float, elevation: float) -> np.ndarray:
    az, el = np.radians(azimuth), np.radians(elevation)
    spin = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    tilt = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
    return (tilt @ spin).T  # use as: points @ matrix


def render_png(shape: trimesh.Trimesh, out_file: Path, size_px: int = 520,
               azimuth: float = -58.0, elevation: float = 24.0, supersample: int = 2) -> Path:
    from PIL import Image

    n = size_px * supersample
    rot = _view_matrix(azimuth, elevation)
    pts = (np.asarray(shape.vertices, float) - shape.bounds.mean(axis=0)) @ rot
    normals = np.asarray(shape.face_normals, float) @ rot

    # Screen x is pts[:, 0], screen up is pts[:, 2], and pts[:, 1] is depth (smaller is closer).
    scale = (n / 2) * 0.88 / max(float(np.abs(pts[:, [0, 2]]).max()), 1e-9)
    px = n / 2 + pts[:, 0] * scale
    py = n / 2 - pts[:, 2] * scale
    depth = pts[:, 1]

    sun = np.array([-0.40, -0.50, 0.75])
    sun /= np.linalg.norm(sun)
    shade = 0.30 + 0.70 * np.clip(normals @ sun, 0.0, 1.0)

    zbuf = np.full((n, n), np.inf)
    canvas = np.tile(_BACKGROUND, (n, n, 1))

    for k, (ia, ib, ic) in enumerate(shape.faces):
        ax, ay, bx, by, cx, cy = px[ia], py[ia], px[ib], py[ib], px[ic], py[ic]
        x_lo, x_hi = max(int(np.floor(min(ax, bx, cx))), 0), min(int(np.ceil(max(ax, bx, cx))), n - 1)
        y_lo, y_hi = max(int(np.floor(min(ay, by, cy))), 0), min(int(np.ceil(max(ay, by, cy))), n - 1)
        area = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if x_hi < x_lo or y_hi < y_lo or abs(area) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(x_lo, x_hi + 1) + 0.5, np.arange(y_lo, y_hi + 1) + 0.5)
        w1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / area
        w2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / area
        w3 = 1.0 - w1 - w2
        inside = (w1 >= -1e-9) & (w2 >= -1e-9) & (w3 >= -1e-9)
        z = w1 * depth[ia] + w2 * depth[ib] + w3 * depth[ic]
        window = zbuf[y_lo:y_hi + 1, x_lo:x_hi + 1]
        wins = inside & (z < window)
        window[wins] = z[wins]
        canvas[y_lo:y_hi + 1, x_lo:x_hi + 1][wins] = _BASE * shade[k]

    picture = Image.fromarray((canvas * 255).astype(np.uint8))
    if supersample > 1:
        picture = picture.resize((size_px, size_px), Image.LANCZOS)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    picture.save(out_file)
    return out_file
