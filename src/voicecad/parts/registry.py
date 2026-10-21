"""The list of parts the server offers. Adding a part means one module and one line here."""
from __future__ import annotations

from collections.abc import Callable

from ..geometry import Mesh
from . import box, bracket, custom_model, electronics_case, laptop_riser, phone_stand
from .base import Part


def default_parts(load_upload: Callable[[str], Mesh] | None = None) -> list[Part]:
    """The built-in parts. The resize-your-own-model part is only offered when uploads are available."""
    parts = [box.PART, bracket.PART, phone_stand.PART, laptop_riser.PART, electronics_case.PART]
    if load_upload is not None:
        parts.append(custom_model.make_part(load_upload))
    return parts
