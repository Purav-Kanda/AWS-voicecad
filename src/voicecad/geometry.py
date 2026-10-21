"""Mesh helpers shared by every part. Pure functions: no globals, no files, no printer settings.

All lengths are millimeters and z is up.
"""
from __future__ import annotations

from typing import Any, TypeAlias

import numpy as np
import trimesh

Mesh: TypeAlias = Any   # trimesh ships no type information, so this stays honest about it
Point3 = tuple[float, float, float]


def block(sx: float, sy: float, sz: float, at: Point3 = (0, 0, 0)) -> Mesh:
    """Box whose minimum corner sits at `at`."""
    shape = trimesh.creation.box(extents=(sx, sy, sz))
    shape.apply_translation((at[0] + sx / 2, at[1] + sy / 2, at[2] + sz / 2))
    return shape


def join(pieces: list[Mesh]) -> Mesh:
    return trimesh.boolean.union(pieces, engine="manifold")


def carve(solid: Mesh, holes: list[Mesh]) -> Mesh:
    return trimesh.boolean.difference([solid, *holes], engine="manifold")


def on_bed(shape: Mesh) -> Mesh:
    """Slide the part so its lowest corner is at the origin."""
    moved = shape.copy()
    moved.apply_translation(-moved.bounds[0])
    return moved


def wedge(corner_a: tuple[float, float], corner_b: tuple[float, float], corner_c: tuple[float, float],
          y_from: float, y_to: float) -> Mesh:
    """Triangular prism. The triangle is given in (x, z) and extruded along y."""
    tri = [corner_a, corner_b, corner_c]
    points = [(x, y_from, z) for x, z in tri] + [(x, y_to, z) for x, z in tri]
    # Caps face outward along -y and +y. Each side quad is wound to match its cap edge.
    faces = [(0, 1, 2), (3, 5, 4),
             (1, 0, 3), (1, 3, 4),
             (2, 1, 4), (2, 4, 5),
             (0, 2, 5), (0, 5, 3)]
    prism = trimesh.Trimesh(vertices=np.array(points, dtype=float), faces=np.array(faces), process=True)
    if prism.volume < 0:
        prism.invert()
    return prism


def tube(radius: float, length: float, axis: str, centre: Point3) -> Mesh:
    """Cylinder lying along x, y or z, centered on `centre`. Used for holes and posts."""
    if axis not in ("x", "y", "z"):
        raise ValueError(f"axis must be x, y or z, not {axis!r}")
    cyl = trimesh.creation.cylinder(radius=radius, height=length, sections=48)
    if axis == "x":
        cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
    elif axis == "y":
        cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0)))
    cyl.apply_translation(centre)
    return cyl


def post(radius: float, height: float, x: float, y: float, z_base: float) -> Mesh:
    """Upright cylinder standing on `z_base`."""
    return tube(radius, height, "z", (x, y, z_base + height / 2))
