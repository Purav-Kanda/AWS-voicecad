"""Open-top storage box with an optional friction-fit lid."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from guided_intake import Check, Field, Issue, Spec

from .. import checks
from ..geometry import block, carve, join, on_bed
from ..printer import PrinterProfile
from .base import Built, Part

NAME = "box"
LID_RING = 1.6          # wall thickness of the lid's inner lip
LID_LIP_HEIGHT = 4.0
LID_CLEARANCE = {"snug": 0.2, "loose": 0.5}   # gap per side between the lip and the box wall
MIN_INSIDE = 10.0       # smallest useful space inside, in mm


def _box_rules(profile: PrinterProfile) -> Callable[[dict[str, Any]], list[Issue]]:
    def run(a: dict[str, Any]) -> list[Issue]:
        found: list[Issue] = []
        inside = min(a["width"], a["depth"]) - 2 * a["wall"]
        if inside < MIN_INSIDE:
            found.append(Issue("error", f"The walls leave only {inside:.0f} mm of space inside.",
                               ("wall", "width", "depth"), "Use thinner walls or make the box wider."))
        if a["height"] < a["wall"] + 10:
            found.append(Issue("error", "The box is too short to hold anything above its floor.",
                               ("height", "wall"), "Make it taller or use a thinner wall."))
        found += checks.thin_wall_issues(profile, a["wall"])
        found += checks.bed_issues(profile, a["width"], a["depth"], a["height"], "box", ("width", "depth", "height"))
        return found
    return run


def _lid_rules(a: dict[str, Any]) -> list[Issue]:
    gap = LID_CLEARANCE[a["lid_fit"]]
    lip_inner = min(a["width"], a["depth"]) - 2 * a["wall"] - 2 * gap - 2 * LID_RING
    if lip_inner < 2:
        return [Issue("error", "The box is too small for a lid lip.", ("lid", "wall"),
                      "Make the box wider or the walls thinner, or skip the lid.")]
    return []


def make_spec(profile: PrinterProfile) -> Spec:
    return Spec(
        name=NAME,
        title="Storage box",
        description="An open-top box with an optional lid, for screws, cables or small parts.",
        fields=(
            Field("width", "How wide should the box be? Millimeters, centimeters or inches all work.",
                  unit="mm", minimum=20, maximum=300),
            Field("depth", "How deep, front to back?", unit="mm", minimum=20, maximum=300),
            Field("height", "How tall?", unit="mm", minimum=15, maximum=250),
            Field("wall", "How thick should the walls be?", unit="mm", minimum=0.8, maximum=10, default=2.0),
            Field("lid", "Do you want a lid?", kind="bool"),
            Field("lid_fit", "Should the lid fit snug or loose?", kind="choice", choices=("snug", "loose"),
                  active_when=lambda a: a.get("lid") is True),
        ),
        checks=(
            Check("box_rules", ("width", "depth", "height", "wall"), _box_rules(profile)),
            Check("box_lid", ("width", "depth", "wall", "lid_fit"), _lid_rules),
        ),
    )


def build(a: dict[str, Any]) -> Built:
    w, d, h, wall = a["width"], a["depth"], a["height"], a["wall"]
    shell = block(w, d, h)
    hollow = block(w - 2 * wall, d - 2 * wall, h, at=(wall, wall, wall))  # sticks out of the top on purpose
    meshes = {"body": on_bed(carve(shell, [hollow]))}
    notes: list[str] = []

    if a.get("lid"):
        gap = LID_CLEARANCE[a["lid_fit"]]
        lip_w, lip_d = w - 2 * wall - 2 * gap, d - 2 * wall - 2 * gap
        x0, y0 = (w - lip_w) / 2, (d - lip_d) / 2
        # Start the lip slightly inside the plate so the two solids really overlap.
        outer = block(lip_w, lip_d, LID_LIP_HEIGHT + 0.5, at=(x0, y0, wall - 0.5))
        inner = block(lip_w - 2 * LID_RING, lip_d - 2 * LID_RING, LID_LIP_HEIGHT + 2,
                      at=(x0 + LID_RING, y0 + LID_RING, wall))
        meshes["lid"] = on_bed(join([block(w, d, wall), carve(outer, [inner])]))
        notes.append(f"Lid fits with {gap} mm of clearance per side.")
    return Built(meshes, tuple(notes))


PART = Part(NAME, make_spec, build)
