"""Turn a finished intake session into STL files."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from guided_intake import Session

from .catalog import Catalog
from .checks import mesh_issues
from .files import prune_old_files

log = logging.getLogger("voicecad")


class Finisher:
    """The `finish` action for the intake tools. It owns no state beyond its three settings."""

    def __init__(self, catalog: Catalog, out_dir: Path, retention_hours: float = 24.0) -> None:
        self._catalog = catalog
        self._out_dir = out_dir
        self._retention_hours = retention_hours

    def __call__(self, session: Session) -> dict[str, Any]:
        try:
            built = self._catalog.build(session.spec.name, session.answers())
        except Exception:
            # A geometry failure is a tool result the assistant can speak, not a crashed server.
            log.exception("build failed for %s", session.spec.name)
            return {"ok": False, "error": "I could not build that shape. Try slightly different dimensions."}

        problems = [i for i in mesh_issues(self._catalog.profile, built.meshes) if i.severity == "error"]
        if problems:
            return {"ok": False, "error": "the model did not pass the final check",
                    "issues": [i.to_dict() for i in problems]}

        self._out_dir.mkdir(parents=True, exist_ok=True)
        prune_old_files(self._out_dir, self._retention_hours)

        made: list[dict[str, Any]] = []
        for name, shape in built.meshes.items():
            filename = f"{session.spec.name}-{session.session_id}-{name}.stl"
            shape.export(self._out_dir / filename)
            sx, sy, sz = (round(float(v), 1) for v in shape.extents)
            made.append({
                "part": name,
                "file": filename,
                "size_mm": [sx, sy, sz],
                "triangles": int(len(shape.faces)),
                "volume_cm3": round(float(shape.volume) / 1000.0, 1),
                "print_count": built.copies.get(name, 1),
            })

        listing = ", ".join(
            f"the {m['part']} at {m['size_mm'][0]:g} by {m['size_mm'][1]:g} by {m['size_mm'][2]:g} millimeters"
            + (f", printed {m['print_count']} times" if m["print_count"] > 1 else "")
            for m in made)
        warnings = [i.message for i in session.issues() if i.severity == "warning"]
        return {
            "summary": f"The {session.spec.title.lower()} is ready: {listing}.",
            "parts": made,
            "notes": list(built.notes) + warnings,
        }
