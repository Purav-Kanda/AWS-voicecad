"""Render one example of every part into docs/images, for the README and the Devpost gallery."""
from pathlib import Path

from voicecad.parts.electronics_case import PI
from voicecad.parts.registry import default_parts
from voicecad.preview import render_png

EXAMPLES = {
    "box": {"width": 100, "depth": 60, "height": 40, "wall": 2.0, "lid": True, "lid_fit": "snug"},
    "bracket": {"arm_a": 60, "arm_b": 80, "width": 30, "thickness": 4.0, "hole_diameter": 4.0, "gusset": True},
    "phone_stand": {"device_thickness": 11.0, "cable_slot": True, "viewing_angle": 65.0, "base_width": 85.0},
    "laptop_riser": {"rail_length": 250, "rear_height": 60, "front_height": 15, "rail_width": 30, "windows": True},
    "electronics_case": {"board": "pi", "vents": True, "port_side": "front", "component_height": 17.0,
                         "standoff_height": 5.0, "screw_hole": 2.7, "board_clearance": 1.0, "wall": 2.0, **PI},
}
OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)
for part in default_parts():
    for name, mesh in part.build(EXAMPLES[part.name]).meshes.items():
        target = OUT / f"{part.name}-{name}.png"
        render_png(mesh, target, elevation=45 if part.name == "electronics_case" else 24)
        print("wrote", target.name)
