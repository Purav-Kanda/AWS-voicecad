"""Safe access to the output folder."""
from __future__ import annotations

import time
from pathlib import Path


def safe_output_path(out_dir: Path, name: str, suffix: str) -> Path:
    """Resolve a file name from outside (an agent, a URL) to a file inside `out_dir`.

    Raises ValueError for anything that is not a plain file name with the expected
    suffix, or that does not exist. This is the only way outside names reach the disk.
    """
    root = out_dir.resolve()
    if not name or "/" in name or "\\" in name or Path(name).name != name or not name.lower().endswith(suffix):
        raise ValueError(f"'{name}' is not a valid {suffix} file name")
    path = (root / name).resolve()
    if path.parent != root or not path.is_file():
        raise ValueError(f"there is no file named '{name}'")
    return path


def prune_old_files(out_dir: Path, max_age_hours: float, now: float | None = None) -> int:
    """Delete generated .stl and .png files older than the limit. Returns how many were removed."""
    if max_age_hours <= 0 or not out_dir.is_dir():
        return 0
    cutoff = (time.time() if now is None else now) - max_age_hours * 3600
    removed = 0
    for path in out_dir.iterdir():
        if path.is_file() and path.suffix.lower() in (".stl", ".png") and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed
