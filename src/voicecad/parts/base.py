"""What every part has to provide. A part is a plain value, not a class hierarchy."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from guided_intake import Spec

from ..geometry import Mesh
from ..printer import PrinterProfile


@dataclass(frozen=True)
class Built:
    """Result of building a part."""

    meshes: dict[str, Mesh]
    notes: tuple[str, ...] = ()
    copies: dict[str, int] = field(default_factory=dict)   # how many of each mesh to print, default 1


@dataclass(frozen=True)
class Part:
    """One kind of part: how to ask for it, and how to build it.

    `make_spec` takes the printer profile because the rules in the spec depend on it.
    `build` takes the finished answers and does no I/O of its own. A part that needs a file is given a
    loader function when it is made, which keeps the part testable without a disk.
    """

    name: str
    make_spec: Callable[[PrinterProfile], Spec]
    build: Callable[[dict[str, Any]], Built]
