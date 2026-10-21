"""Settings, read once at the edge of the program and passed inward."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .printer import DEFAULT_PRINTER, PrinterProfile, parse_printer


@dataclass(frozen=True)
class Settings:
    out_dir: Path
    host: str = "127.0.0.1"
    port: int = 8000
    printer: PrinterProfile = DEFAULT_PRINTER
    retention_hours: float = 24.0   # generated files older than this are deleted
    max_upload_mb: float = 10.0     # largest STL accepted from the upload button

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        return cls(
            out_dir=Path(source.get("VOICECAD_OUT", "out")).resolve(),
            host=source.get("VOICECAD_HOST", "127.0.0.1"),
            port=int(_number(source, "VOICECAD_PORT", "8000", int)),
            printer=parse_printer(source.get("VOICECAD_PRINTER", "ender3")),
            retention_hours=_number(source, "VOICECAD_RETENTION_HOURS", "24", float),
            max_upload_mb=_number(source, "VOICECAD_MAX_UPLOAD_MB", "10", float),
        )

    @property
    def upload_dir(self) -> Path:
        return self.out_dir / "uploads"


def _number(source: Mapping[str, str], key: str, default: str, kind: type) -> float:
    raw = source.get(key, default)
    try:
        return kind(raw)
    except ValueError:
        raise ValueError(f"{key} must be a number, not {raw!r}") from None
