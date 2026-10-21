"""Enclosure for a small circuit board, with screw standoffs, optional vents and one open port side."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from guided_intake import Check, Field, Issue, Spec

from .. import checks
from ..geometry import block, carve, join, post, tube
from ..printer import PrinterProfile
from . import box
from .base import Built, Part

NAME = "electronics_case"
PCB_THICKNESS = 1.6
HEADROOM = 2.0          # air above the tallest component
STANDOFF_RADIUS = 3.0
VENT_WIDTH = 2.0
VENT_PITCH = 5.0
PORT_BAND = 0.6         # share of a side that the port opening covers
SIDES = ("none", "front", "back", "left", "right")

# Raspberry Pi 3 and 4 size and hole pattern, from the published mechanical drawing.
# This is a preset, not a promise: boards differ, so the assistant tells the user to measure.
PI = {"board_length": 85.0, "board_width": 56.0, "hole_spacing_x": 58.0, "hole_spacing_y": 49.0, "hole_inset": 3.5}
CUSTOM_KEYS = tuple(PI)


def board_of(a: dict[str, Any]) -> dict[str, float] | None:
    """The board size and hole pattern, or None while a custom board is still being described."""
    if a["board"] == "pi":
        return dict(PI)
    if all(k in a for k in CUSTOM_KEYS):
        return {k: float(a[k]) for k in CUSTOM_KEYS}
    return None


def case_size(a: dict[str, Any], b: dict[str, float]) -> tuple[float, float, float]:
    pad = a["wall"] + a["board_clearance"]
    height = a["wall"] + a["standoff_height"] + PCB_THICKNESS + a["component_height"] + HEADROOM
    return b["board_length"] + 2 * pad, b["board_width"] + 2 * pad, height


def _board_rules(a: dict[str, Any]) -> list[Issue]:
    b = board_of(a)
    assert b is not None   # the check only runs once every custom field has a value
    found: list[Issue] = []
    if b["hole_spacing_x"] + 2 * b["hole_inset"] > b["board_length"] or \
            b["hole_spacing_y"] + 2 * b["hole_inset"] > b["board_width"]:
        found.append(Issue("error", "The mounting holes would be outside the board.",
                           CUSTOM_KEYS, "Check the hole spacing and the distance from the edge."))
    return found


def _case_rules(profile: PrinterProfile) -> Callable[[dict[str, Any]], list[Issue]]:
    def run(a: dict[str, Any]) -> list[Issue]:
        b = board_of(a)
        if b is None:
            return []
        found = checks.thin_wall_issues(profile, a["wall"])
        sx, sy, sz = case_size(a, b)
        found += checks.bed_issues(profile, sx, sy, sz, "case")
        if a["screw_hole"] + 2 * 1.2 > 2 * STANDOFF_RADIUS:
            found.append(Issue("error", "That screw hole is too wide for the standoff.", ("screw_hole",),
                               "Use a smaller screw hole."))
        return found
    return run


def make_spec(profile: PrinterProfile) -> Spec:
    custom = lambda a: a.get("board") == "custom"  # noqa: E731
    return Spec(
        name=NAME,
        title="Electronics case",
        description="A case with a snap-on lid for a small circuit board such as a Raspberry Pi, with screw standoffs.",
        fields=(
            Field("board", "Which board is it for? Say Raspberry Pi, or custom to give me the measurements.",
                  kind="choice", choices=("pi", "custom"),
                  hint="The Pi preset uses the standard 85 by 56 millimeter board with holes 58 by 49 millimeters apart. "
                       "Tell the user to check this against their own board before printing."),
            Field("board_length", "How long is the board?", unit="mm", minimum=20, maximum=200, active_when=custom),
            Field("board_width", "How wide is the board?", unit="mm", minimum=20, maximum=150, active_when=custom),
            Field("hole_spacing_x", "How far apart are the mounting holes along the length?",
                  unit="mm", minimum=10, maximum=190, active_when=custom),
            Field("hole_spacing_y", "How far apart are the mounting holes along the width?",
                  unit="mm", minimum=10, maximum=140, active_when=custom),
            Field("hole_inset", "How far is the first hole from the board edge?", unit="mm", minimum=1, maximum=15,
                  default=3.5, active_when=custom),
            Field("vents", "Do you want vent slots in the lid?", kind="bool"),
            Field("port_side", "Which side should have the opening for the ports? Front, back, left, right, or none.",
                  kind="choice", choices=SIDES,
                  hint="Left and right are seen from above with the front toward the user."),
            Field("component_height", "How tall is the tallest part on the board?", unit="mm",
                  minimum=3, maximum=60, default=17.0),
            Field("standoff_height", "How high should the board sit off the floor?", unit="mm",
                  minimum=3, maximum=15, default=5.0),
            Field("screw_hole", "How wide is the screw hole?", unit="mm", minimum=1.5, maximum=4, default=2.7),
            Field("board_clearance", "How much gap around the board?", unit="mm", minimum=0.5, maximum=5, default=1.0),
            Field("wall", "How thick should the walls be?", unit="mm", minimum=1.2, maximum=5, default=2.0),
        ),
        checks=(
            Check("board_holes", CUSTOM_KEYS, _board_rules),
            Check("case_rules", ("board", "wall", "standoff_height", "component_height", "board_clearance", "screw_hole"),
                  _case_rules(profile)),
        ),
    )


def _port_opening(side: str, a: dict[str, Any], size: tuple[float, float, float]) -> Any:
    """A cutter that goes through the wall on the chosen side."""
    sx, sy, _ = size
    z0 = a["wall"] + a["standoff_height"]
    z_len = min(a["component_height"], 14.0) + PCB_THICKNESS
    cut = a["wall"] + 2   # starts outside the case and ends inside it
    if side in ("front", "back"):
        span = sx * PORT_BAND
        y0 = -1 if side == "front" else sy - a["wall"] - 1
        return block(span, cut, z_len, at=((sx - span) / 2, y0, z0))
    span = sy * PORT_BAND
    x0 = -1 if side == "left" else sx - a["wall"] - 1
    return block(cut, span, z_len, at=(x0, (sy - span) / 2, z0))


def build(a: dict[str, Any]) -> Built:
    b = board_of(a)
    assert b is not None
    sx, sy, sz = case_size(a, b)
    wall, standoff = a["wall"], a["standoff_height"]

    shell = box.build({"width": sx, "depth": sy, "height": sz, "wall": wall, "lid": True, "lid_fit": "snug"})
    body, lid = shell.meshes["body"], shell.meshes["lid"]

    ox = oy = wall + a["board_clearance"] + b["hole_inset"]
    spots = [(ox + dx, oy + dy) for dx in (0, b["hole_spacing_x"]) for dy in (0, b["hole_spacing_y"])]
    posts = [post(STANDOFF_RADIUS, standoff + 0.5, x, y, wall - 0.5) for x, y in spots]  # sunk into the floor
    body = join([body, *posts])
    pilots = [tube(a["screw_hole"] / 2, standoff + 1.0, "z", (x, y, wall + (standoff + 1.0) / 2)) for x, y in spots]
    cuts = list(pilots)
    notes = ["Four standoffs hold the board. Use small screws sized for the pilot holes."]

    if a["port_side"] != "none":
        cuts.append(_port_opening(a["port_side"], a, (sx, sy, sz)))
        notes.append(f"Open side for ports: {a['port_side']}.")
    body = carve(body, cuts)

    if a.get("vents"):
        count = max(1, int((sx - 4 * wall) // VENT_PITCH))
        run_len = sy * 0.5
        start = (sx - (count * VENT_PITCH - (VENT_PITCH - VENT_WIDTH))) / 2
        slots = [block(VENT_WIDTH, run_len, wall + 2, at=(start + i * VENT_PITCH, (sy - run_len) / 2, -1))
                 for i in range(count)]
        lid = carve(lid, slots)
        notes.append(f"{count} vent slots in the lid.")

    notes.append("Print the body open side up and the lid flat.")
    return Built({"body": body, "lid": lid}, tuple(notes))


PART = Part(NAME, make_spec, build)
