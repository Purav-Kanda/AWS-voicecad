"""Right-angle bracket with two screw holes and an optional corner gusset."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import trimesh
from guided_intake import Check, Field, Issue, Spec

from .. import checks
from ..geometry import block, carve, join, on_bed, tube, wedge
from ..printer import PrinterProfile
from .base import Built, Part

NAME = "bracket"
MIN_GUSSET = 5.0     # a gusset shorter than this is not worth building
EDGE_MARGIN = 3.0    # material kept between a hole and the edge of the bracket


def gusset_leg(a: dict[str, Any]) -> float:
    """How long the gusset can be without covering a screw hole."""
    t, hd = a["thickness"], a["hole_diameter"]
    room = min(a["arm_a"], a["arm_b"]) - t - 2.5 * hd
    return min(0.6 * min(a["arm_a"], a["arm_b"]), room)


def _rules(profile: PrinterProfile) -> Callable[[dict[str, Any]], list[Issue]]:
    def run(a: dict[str, Any]) -> list[Issue]:
        found: list[Issue] = []
        hd, wd, t = a["hole_diameter"], a["width"], a["thickness"]
        if hd + 2 * EDGE_MARGIN > wd:
            found.append(Issue("error", f"A {hd:g} mm screw hole leaves less than {EDGE_MARGIN:g} mm of material at each edge.",
                               ("hole_diameter", "width"), "Make the bracket wider or the hole smaller."))
        for arm in ("arm_a", "arm_b"):
            if a[arm] < t + 3 * hd:
                found.append(Issue("error", f"{arm} is too short to fit a screw hole.", (arm,),
                                   "Make that arm longer or the hole smaller."))
        if t < 3:
            found.append(Issue("warning", "Brackets thinner than 3 mm can flex or snap under load.", ("thickness",)))
        found += checks.bed_issues(profile, a["arm_a"], a["arm_b"], a["width"], "bracket", ("arm_a", "arm_b", "width"))
        return found
    return run


def make_spec(profile: PrinterProfile) -> Spec:
    return Spec(
        name=NAME,
        title="L bracket",
        description="A right-angle bracket with two screw holes and an optional corner gusset, for shelves or mounting.",
        fields=(
            Field("arm_a", "How long should the flat arm be, the one that lies on the shelf?",
                  unit="mm", minimum=20, maximum=200),
            Field("arm_b", "How long should the upright arm be, the one against the wall?",
                  unit="mm", minimum=20, maximum=200),
            Field("width", "How wide should the bracket be, measured along the wall?",
                  unit="mm", minimum=10, maximum=100),
            Field("thickness", "How thick should the plate be?", unit="mm", minimum=2, maximum=12, default=4.0),
            Field("hole_diameter", "How wide should the screw holes be?", unit="mm",
                  minimum=2, maximum=10, default=4.0),
            Field("gusset", "Add a corner gusset for strength?", kind="bool", default=True),
        ),
        checks=(Check("bracket_rules", ("arm_a", "arm_b", "width", "thickness", "hole_diameter"), _rules(profile)),),
    )


def build(a: dict[str, Any]) -> Built:
    arm_a, arm_b, wd, t, hd = a["arm_a"], a["arm_b"], a["width"], a["thickness"], a["hole_diameter"]
    pieces = [block(arm_a, wd, t), block(t, wd, arm_b)]
    notes: list[str] = []

    if a.get("gusset"):
        leg = gusset_leg(a)
        if leg >= MIN_GUSSET:
            thick = max(2.0, wd * 0.3)
            y0 = (wd - thick) / 2
            e = 0.2  # push into both arms so the union is solid
            pieces.append(wedge((t - e, t - e), (t + leg, t - e), (t - e, t + leg), y0, y0 + thick))
        else:
            notes.append("Arms are too short for a gusset next to the screw holes, so I left it out.")

    mid = wd / 2
    frame = carve(join(pieces), [
        tube(hd / 2, t + 2, "z", (arm_a - 1.5 * hd, mid, t / 2)),
        tube(hd / 2, t + 2, "x", (t / 2, mid, arm_b - 1.5 * hd)),
    ])

    # Lay it on its side: the L profile is flat on the bed, so nothing overhangs.
    frame.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, (1, 0, 0)))
    notes.append("Printed lying on its side, no supports needed.")
    return Built({"bracket": on_bed(frame)}, tuple(notes))


PART = Part(NAME, make_spec, build)
