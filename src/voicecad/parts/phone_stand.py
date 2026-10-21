"""Desk stand for a phone: a base, a leaning back plate and a low front lip."""
from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import trimesh
from guided_intake import Check, Field, Issue, Spec

from .. import checks
from ..geometry import Mesh, block, carve, join, on_bed
from ..printer import PrinterProfile
from .base import Built, Part

NAME = "phone_stand"
BASE = 8.0        # base plate thickness
LIP = 6.0         # front lip thickness
LIP_H = 14.0      # how far the lip rises above the base
SLAB = 8.0        # thickness of the leaning back plate
TOP = 60.0        # height of the back plate's front-top corner
SINK = 2.0        # how far the back plate is pushed into the base so they fuse
REAR_ROOM = 8.0   # base kept behind the plate so the stand will not tip


def _slab(a: dict[str, Any]) -> tuple[Mesh, float, float]:
    """The leaning plate, plus the gap between lip and plate and where the plate meets the base."""
    lean = math.radians(90.0 - a["viewing_angle"])   # tilt of the plate away from vertical
    gap = (a["device_thickness"] + 1.0) / math.cos(lean)  # 1 mm of play, measured along the base
    y_front = LIP + gap
    z0 = BASE - SINK
    length = (TOP - z0) / math.cos(lean)
    slab = block(a["base_width"], SLAB, length)
    slab.apply_transform(trimesh.transformations.rotation_matrix(-lean, (1, 0, 0)))
    slab.apply_translation((0, y_front - SINK * math.tan(lean), z0))
    return slab, gap, y_front


def _base_depth(slab: Mesh) -> int:
    return math.ceil(float(slab.bounds[1][1]) + REAR_ROOM)


def _rules(profile: PrinterProfile) -> Callable[[dict[str, Any]], list[Issue]]:
    def run(a: dict[str, Any]) -> list[Issue]:
        found: list[Issue] = []
        if a["base_width"] < 40:
            found.append(Issue("error", "The base is too narrow to hold a phone steadily.", ("base_width",),
                               "Use at least 40 mm."))
        if a["device_thickness"] > 25:
            found.append(Issue("warning", "That is thick for a phone. A tablet needs a different design.",
                               ("device_thickness",)))
        slab, _, _ = _slab(a)
        found += checks.bed_issues(profile, a["base_width"], _base_depth(slab), TOP, "stand", ("base_width", "viewing_angle"))
        return found
    return run


def make_spec(profile: PrinterProfile) -> Spec:
    return Spec(
        name=NAME,
        title="Phone stand",
        description="A desk stand with a tilted back plate and a low front lip, with an optional charging cable hole.",
        fields=(
            Field("device_thickness", "How thick is your phone with its case on? About 10 to 12 millimeters is typical.",
                  unit="mm", minimum=5, maximum=25),
            Field("cable_slot", "Do you want a hole for a charging cable?", kind="bool"),
            Field("viewing_angle", "How steep should it lean, in degrees from flat? 65 is a good default.",
                  unit="deg", minimum=50, maximum=80, default=65.0,
                  hint="Below 50 degrees the back plate would overhang too much to print without supports."),
            Field("base_width", "How wide should the base be?", unit="mm", minimum=40, maximum=200, default=85.0),
        ),
        checks=(Check("stand_rules", ("device_thickness", "base_width", "viewing_angle"), _rules(profile)),),
    )


def build(a: dict[str, Any]) -> Built:
    w = a["base_width"]
    slab, gap, y_front = _slab(a)
    depth = _base_depth(slab)
    stand = join([block(w, depth, BASE), block(w, LIP, LIP_H + 0.5, at=(0, 0, BASE - 0.5)), slab])
    notes = [f"Base is {w:.0f} by {depth} mm, sized so the stand will not tip back."]

    if a.get("cable_slot"):
        mid_x = w / 2
        y_mid = LIP + gap / 2
        port = block(16.0, gap, BASE + 0.5, at=(mid_x - 8.0, LIP, -0.5))
        run = block(10.0, depth - y_mid + 1.0, 5.0, at=(mid_x - 5.0, y_mid, -0.5))
        stand = carve(stand, [port, run])
        notes.append("Cable hole under the charging port, with a groove under the base to the back.")

    return Built({"stand": on_bed(stand)}, tuple(notes))


PART = Part(NAME, make_spec, build)
