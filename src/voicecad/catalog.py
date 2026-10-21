"""Everything the server can make, for one printer."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from guided_intake import Spec

from .parts.base import Built, Part
from .printer import PrinterProfile


class Catalog:
    def __init__(self, parts: Iterable[Part], profile: PrinterProfile) -> None:
        self.profile = profile
        self._parts: dict[str, Part] = {}
        self._specs: dict[str, Spec] = {}
        for part in parts:
            if part.name in self._parts:
                raise ValueError(f"two parts are named '{part.name}'")
            spec = part.make_spec(profile)
            if spec.name != part.name:
                raise ValueError(f"part '{part.name}' builds a spec named '{spec.name}'. The names must match")
            self._parts[part.name] = part
            self._specs[part.name] = spec

    def specs(self) -> list[Spec]:
        return list(self._specs.values())

    def build(self, name: str, answers: dict[str, Any]) -> Built:
        try:
            part = self._parts[name]
        except KeyError:
            raise KeyError(f"unknown part '{name}'") from None
        return part.build(answers)
