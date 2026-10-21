"""Pair of sloped rails that lift a laptop's back edge for airflow and typing comfort."""
from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from guided_intake import Check, Field, Issue, Spec

from .. import checks
from ..geometry import block, carve, join, on_bed, wedge
from ..printer import PrinterProfile
from .base import Built, Part

NAME = "laptop_riser"
LIP_THICKNESS = 3.0   # front stop that keeps the laptop from sliding off
LIP_RISE = 8.0        # how far the stop stands above the front of the slope
MIN_RISE = 5.0        # smallest difference between rear and front that is worth building
MAX_TILT_DEG = 15.0   # steeper than this makes typing uncomfortable
FLOOR = 4.0           # solid bottom kept under the lightening windows
RIB = 6.0             # material kept between two windows
WINDOW_MARGIN = 8.0   # solid end kept at each end of the rail
MIN_WINDOW_FRONT = 14.0   # below this front height there is no room for windows


def tilt_degrees(a: dict[str, Any]) -> float:
    return math.degrees(math.atan2(a["rear_height"] - a["front_height"], a["rail_length"]))


def _rules(profile: PrinterProfile) -> Callable[[dict[str, Any]], list[Issue]]:
    def run(a: dict[str, Any]) -> list[Issue]:
        found: list[Issue] = []
        if a["rear_height"] < a["front_height"] + MIN_RISE:
            found.append(Issue("error", f"The rear must be at least {MIN_RISE:g} mm higher than the front.",
                               ("rear_height", "front_height"), "Raise the rear or lower the front."))
        elif tilt_degrees(a) > MAX_TILT_DEG:
            found.append(Issue("warning", f"That is a {tilt_degrees(a):.0f} degree tilt. Above {MAX_TILT_DEG:.0f} degrees "
                                          "typing gets uncomfortable.", ("rear_height", "rail_length")))
        found += checks.bed_issues(profile, a["rail_length"], a["rail_width"], a["rear_height"], "rail",
                                    ("rail_length", "rear_height", "rail_width"))
        return found
    return run


def make_spec(profile: PrinterProfile) -> Spec:
    return Spec(
        name=NAME,
        title="Laptop riser",
        description="Two sloped rails that raise the back of a laptop. Print the rail twice.",
        fields=(
            Field("rail_length", "How long should each rail be, front to back? The laptop's depth is a good guide.",
                  unit="mm", minimum=80, maximum=300),
            Field("rear_height", "How high should the back of the laptop be raised?",
                  unit="mm", minimum=20, maximum=120),
            Field("front_height", "How high should the front of the rail be?",
                  unit="mm", minimum=10, maximum=40, default=15.0),
            Field("rail_width", "How wide should each rail be?", unit="mm", minimum=15, maximum=60, default=30.0),
            Field("windows", "Cut openings to save plastic and print time?", kind="bool", default=True),
        ),
        checks=(Check("riser_rules", ("rail_length", "rear_height", "front_height", "rail_width"), _rules(profile)),),
    )


def build(a: dict[str, Any]) -> Built:
    length, rear, front, width = a["rail_length"], a["rear_height"], a["front_height"], a["rail_width"]
    overlap = 0.2  # push the slope into the base so the union is solid
    pieces = [
        block(length, width, front),
        wedge((0, front - overlap), (length, front - overlap), (length, rear), 0, width),
        block(LIP_THICKNESS, width, front + LIP_RISE),
    ]
    rail = join(pieces)
    notes = [f"Tilt is {tilt_degrees(a):.1f} degrees."]

    if a.get("windows") and front >= MIN_WINDOW_FRONT:
        x0, x1 = LIP_THICKNESS + WINDOW_MARGIN, length - WINDOW_MARGIN
        count = max(1, int((x1 - x0 + RIB) // (RIB + 20)))   # windows about 20 mm wide
        slot = (x1 - x0 - RIB * (count - 1)) / count
        holes = [block(slot, width + 2, front - 2 * FLOOR, at=(x0 + i * (slot + RIB), -1, FLOOR))
                 for i in range(count)]
        rail = carve(rail, holes)
        notes.append(f"{count} openings cut through each rail.")

    notes.append("Print the rail twice, flat on its base, no supports needed.")
    return Built({"rail": on_bed(rail)}, tuple(notes), {"rail": 2})


PART = Part(NAME, make_spec, build)
