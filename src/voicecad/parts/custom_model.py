"""Resize a 3D model the user uploaded. The model is scaled, never edited: its shape stays as it was."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
from guided_intake import Check, Field, Issue, Spec

from .. import checks
from ..geometry import Mesh, on_bed
from ..printer import PrinterProfile
from ..uploads import UploadError
from .base import Built, Part

NAME = "custom_model"
SIZING_FIELDS = ("longest_mm", "percent", "width", "depth", "height")
STRETCH_LIMIT = 1.25   # one side scaled this much more than another visibly distorts holes and walls
THIN_SCALE = 0.6       # below this, every wall gets noticeably thinner
MIN_SIDE = 1.0         # mm; anything thinner than this cannot be printed

Loader = Callable[[str], Mesh]


def scale_factors(extents: tuple[float, float, float], a: dict[str, Any]) -> tuple[float, float, float]:
    """How much to stretch x, y and z, given how the user chose to size the model. Pure arithmetic."""
    mode = a.get("sizing")
    if mode == "longest":
        k = a["longest_mm"] / max(extents)
        return (k, k, k)
    if mode == "percent":
        k = a["percent"] / 100.0
        return (k, k, k)
    if mode == "each":
        return (a["width"] / extents[0], a["depth"] / extents[1], a["height"] / extents[2])
    return (1.0, 1.0, 1.0)


def _blamed(a: dict[str, Any]) -> tuple[str, ...]:
    """The answers a sizing problem comes from, so an assistant knows what to ask again."""
    mode = a.get("sizing")
    names = {"longest": ("longest_mm",), "percent": ("percent",), "each": ("width", "depth", "height")}
    return ("sizing", *names.get(str(mode), ()))


def _model_rules(load: Loader) -> Callable[[dict[str, Any]], list[Issue]]:
    def run(a: dict[str, Any]) -> list[Issue]:
        try:
            extents = tuple(float(v) for v in load(a["upload_id"]).extents)
        except UploadError as err:
            return [Issue("error", str(err), ("upload_id",), "Upload the file again.")]
        biggest = max(extents)
        if biggest > 500:
            return [Issue("warning", f"The model is {biggest:.0f} mm long as uploaded. STL files carry no units, "
                          "so I assumed millimeters. If it was meant to be meters, resize it.", ("upload_id",))]
        if biggest < 5:
            return [Issue("warning", f"The model is only {biggest:.1f} mm long as uploaded. STL files carry no "
                          "units, so I assumed millimeters. If it was in inches or meters, set the size below.",
                          ("upload_id",))]
        return []
    return run


def _size_rules(profile: PrinterProfile, load: Loader) -> Callable[[dict[str, Any]], list[Issue]]:
    def run(a: dict[str, Any]) -> list[Issue]:
        try:
            extents = tuple(float(v) for v in load(a["upload_id"]).extents)
        except UploadError:
            return []   # _model_rules already reports this
        fx, fy, fz = scale_factors((extents[0], extents[1], extents[2]), a)
        sx, sy, sz = extents[0] * fx, extents[1] * fy, extents[2] * fz
        found: list[Issue] = []
        if min(sx, sy, sz) < MIN_SIDE:
            found.append(Issue("error", f"At that size the model would be only {min(sx, sy, sz):.1f} mm thick "
                               "in one direction, which is too thin to print.", _blamed(a),
                               "Pick a larger size."))
        found += checks.bed_issues(profile, sx, sy, sz, "model", _blamed(a))
        factors = (fx, fy, fz)
        if max(factors) / min(factors) > STRETCH_LIMIT:
            found.append(Issue("warning", "The sides are scaled by different amounts, so round holes will turn "
                               "oval and wall thickness will change.", _blamed(a)))
        elif min(factors) < THIN_SCALE:
            found.append(Issue("warning", "Shrinking this much also thins every wall. Check the thin parts "
                               "in your slicer.", _blamed(a)))
        return found
    return run


def make_spec(profile: PrinterProfile, load: Loader) -> Spec:
    size = _size_rules(profile, load)
    needs = {"keep": (), "longest": ("longest_mm",), "percent": ("percent",), "each": ("width", "depth", "height")}

    def when(mode: str) -> Callable[[dict[str, Any]], bool]:
        return lambda a: a.get("sizing") == mode

    def size_for(mode: str) -> Callable[[dict[str, Any]], list[Issue]]:
        return lambda a: size(a) if a.get("sizing") == mode else []

    return Spec(
        name=NAME,
        title="Resized model",
        description=("Resize a 3D model (an STL file) that the user has already uploaded. "
                     "Only choose this when the user says they uploaded a file and gives its id."),
        fields=(
            Field("upload_id", "Which uploaded file should I use?", kind="text",
                  hint="Use the id from the upload message exactly. Never make one up."),
            Field("what_it_is", "What is it, in a few words?", kind="text",
                  hint="For example a desk hook or a cable holder. It is kept as a note on the result."),
            Field("sizing", "Should I keep its size, set its longest side, scale it by a percent, "
                  "or set the width, depth and height separately?", kind="choice",
                  choices=("keep", "longest", "percent", "each")),
            Field("longest_mm", "How long should its longest side be?", unit="mm", minimum=5, maximum=600,
                  active_when=when("longest")),
            Field("percent", "Scale it to what percent? 100 keeps the size and 50 makes it half as big.",
                  unit="percent", minimum=10, maximum=1000, active_when=when("percent")),
            Field("width", "How wide should it be, side to side?", unit="mm", minimum=5, maximum=600,
                  active_when=when("each")),
            Field("depth", "How deep should it be, front to back?", unit="mm", minimum=5, maximum=600,
                  active_when=when("each")),
            Field("height", "How tall should it be?", unit="mm", minimum=5, maximum=600,
                  active_when=when("each")),
        ),
        checks=(
            Check("model_rules", ("upload_id",), _model_rules(load)),
            *(Check(f"size_{mode}", ("upload_id", "sizing", *fields), size_for(mode)) for mode, fields in needs.items()),
        ),
    )


def make_part(load: Loader) -> Part:
    """The part, built around a function that fetches an uploaded model by id (injected, so tests need no disk)."""

    def build(a: dict[str, Any]) -> Built:
        original = load(a["upload_id"])
        ex, ey, ez = (float(v) for v in original.extents)
        fx, fy, fz = scale_factors((ex, ey, ez), a)
        scaled: Mesh = original.copy()
        scaled.apply_transform(np.diag([fx, fy, fz, 1.0]))
        shape = on_bed(scaled)
        sx, sy, sz = (float(v) for v in shape.extents)
        label = str(a.get("what_it_is", "")).strip()
        what = f"Resized {label}" if label else "Resized model"
        notes = [f"{what}: {sx:.0f} by {sy:.0f} by {sz:.0f} mm, from {ex:.0f} by {ey:.0f} by {ez:.0f} mm.",
                 "It is printed in the orientation you uploaded it, flat on the bed."]
        return Built({"model": shape}, tuple(notes))

    return Part(NAME, lambda profile: make_spec(profile, load), build)
