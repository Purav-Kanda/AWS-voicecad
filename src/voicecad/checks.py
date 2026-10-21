"""Print rules that apply to every part. Part-specific rules live next to their part."""
from __future__ import annotations

from guided_intake import Issue

from .geometry import Mesh
from .printer import PrinterProfile


def bed_issues(profile: PrinterProfile, size_x: float, size_y: float, size_z: float, label: str = "part",
               fields: tuple[str, ...] = ()) -> list[Issue]:
    """`fields` names the answers that set the size, so an assistant knows what to ask about again."""
    if profile.fits(size_x, size_y, size_z):
        return []
    return [Issue(
        "error",
        f"The {label} is {size_x:.0f} by {size_y:.0f} by {size_z:.0f} mm, which does not fit a "
        f"{profile.bed_x:.0f} by {profile.bed_y:.0f} mm print bed that is {profile.bed_z:.0f} mm tall "
        f"({profile.name}).",
        fields=fields,
        suggestion="Make it smaller, or split it into pieces.",
    )]


def thin_wall_issues(profile: PrinterProfile, wall: float, field: str = "wall") -> list[Issue]:
    if wall >= profile.min_wall:
        return []
    return [Issue("warning", f"Walls under {profile.min_wall:g} mm are fragile.", (field,))]


def mesh_issues(profile: PrinterProfile, meshes: dict[str, Mesh]) -> list[Issue]:
    """Final guard on the real geometry, after the boolean operations."""
    found: list[Issue] = []
    for name, shape in meshes.items():
        if not shape.is_watertight:
            found.append(Issue("error", f"The {name} model has holes in its surface and may not slice cleanly."))
        elif shape.volume <= 0:
            found.append(Issue("error", f"The {name} model came out empty or inside out."))
        sx, sy, sz = (float(v) for v in shape.extents)
        found.extend(bed_issues(profile, sx, sy, sz, label=name))
    return found
