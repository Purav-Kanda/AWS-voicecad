"""What the user's printer can do. Passed into the rules instead of living in constants."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PrinterProfile:
    name: str
    bed_x: float
    bed_y: float
    bed_z: float
    min_wall: float = 1.2   # walls thinner than this get a warning

    def __post_init__(self) -> None:
        if min(self.bed_x, self.bed_y, self.bed_z, self.min_wall) <= 0:
            raise ValueError("printer sizes must be positive")

    def fits(self, size_x: float, size_y: float, size_z: float) -> bool:
        """True if a part fits on the plate, allowing a quarter turn."""
        flat_ok = (size_x <= self.bed_x and size_y <= self.bed_y) or (size_y <= self.bed_x and size_x <= self.bed_y)
        return flat_ok and size_z <= self.bed_z


# Approximate build volumes in millimeters. Check your own printer's spec sheet.
PRESETS: dict[str, PrinterProfile] = {
    "ender3": PrinterProfile("Ender 3 class", 220, 220, 250),
    "prusa_mk4": PrinterProfile("Prusa MK4 class", 250, 210, 220),
    "bambu_256": PrinterProfile("256 mm cube class", 256, 256, 256),
    "small_180": PrinterProfile("180 mm cube class", 180, 180, 180),
}
DEFAULT_PRINTER = PRESETS["ender3"]

_CUSTOM = re.compile(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)")


def parse_printer(text: str) -> PrinterProfile:
    """Accepts a preset name, or sizes written as WIDTHxDEPTHxHEIGHT in millimeters."""
    key = text.strip().lower().replace(" ", "")
    if key in PRESETS:
        return PRESETS[key]
    hit = _CUSTOM.fullmatch(key)
    if hit:
        x, y, z = (float(v) for v in hit.groups())
        return PrinterProfile("custom printer", x, y, z)
    raise ValueError(f"unknown printer '{text}'. Use one of {', '.join(PRESETS)} "
                     "or WIDTHxDEPTHxHEIGHT such as 220x220x250")
