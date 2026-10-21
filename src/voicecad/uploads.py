"""Where uploaded 3D models live, and the checks a file must pass before the rest of the app sees it.

The app only ever works with an upload through its id. An id is twelve hex digits made by this
module, so a name that arrives from outside (an assistant, a URL) can never point anywhere else.
"""
from __future__ import annotations

import io
import logging
import re
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh

from .files import prune_old_files
from .geometry import Mesh

log = logging.getLogger("voicecad")
_ID = re.compile(r"^[0-9a-f]{12}$")
MAX_FACES = 300_000
CACHE_SIZE = 8


class UploadError(ValueError):
    """The upload is not usable. The message is written to be shown to the user."""


@dataclass(frozen=True)
class Upload:
    id: str
    name: str
    size_mm: tuple[float, float, float]


class UploadStore:
    def __init__(self, folder: Path, max_bytes: int = 10 * 1024 * 1024, retention_hours: float = 24.0) -> None:
        self._folder = folder
        self.max_bytes = max_bytes
        self._retention_hours = retention_hours
        self._cache: OrderedDict[str, Mesh] = OrderedDict()
        self._lock = threading.Lock()

    def save(self, filename: str, data: bytes) -> Upload:
        """Check an uploaded STL and keep it. Raises UploadError with a plain reason if it is not usable."""
        if not filename.lower().endswith(".stl"):
            raise UploadError("Only .stl files are supported for now.")
        if not data:
            raise UploadError("That file is empty.")
        if len(data) > self.max_bytes:
            raise UploadError(f"That file is larger than {self.max_bytes // (1024 * 1024)} MB.")
        mesh = self._parse(data)
        upload_id = uuid.uuid4().hex[:12]
        self._folder.mkdir(parents=True, exist_ok=True)
        prune_old_files(self._folder, self._retention_hours)
        (self._folder / f"{upload_id}.stl").write_bytes(data)
        sx, sy, sz = (round(float(v), 1) for v in mesh.extents)
        return Upload(upload_id, Path(filename).name[:80], (sx, sy, sz))

    def load(self, upload_id: str) -> Mesh:
        """A private copy of a stored model, or UploadError if there is no such upload."""
        if not _ID.match(upload_id or ""):
            raise UploadError("That is not a valid upload id.")
        with self._lock:
            if upload_id in self._cache:
                self._cache.move_to_end(upload_id)
                return self._cache[upload_id].copy()
        path = self._folder / f"{upload_id}.stl"
        if not path.is_file():
            raise UploadError("I cannot find that upload. It may have expired, so please upload it again.")
        mesh = self._parse(path.read_bytes())
        with self._lock:
            self._cache[upload_id] = mesh
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
        return mesh.copy()

    @staticmethod
    def _parse(data: bytes) -> Mesh:
        try:
            mesh = trimesh.load(io.BytesIO(data), file_type="stl", force="mesh")
        except Exception:
            raise UploadError("I could not read that file as an STL model.") from None
        if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
            raise UploadError("That STL has no surface in it.")
        if len(mesh.faces) > MAX_FACES:
            raise UploadError(f"That model has more than {MAX_FACES:,} triangles. Simplify it and try again.")
        if not np.isfinite(mesh.vertices).all():
            raise UploadError("That model has broken coordinates in it.")
        if min(float(v) for v in mesh.extents) <= 0:
            raise UploadError("That model is completely flat, so it has no thickness to print.")
        try:
            trimesh.repair.fix_normals(mesh)
            trimesh.repair.fill_holes(mesh)
        except Exception:
            # trimesh's repair helpers lean on optional libraries. A failure here must be an answer, not a crash.
            log.exception("could not repair an uploaded model")
            raise UploadError("I could not check that model for holes. Repair it in your slicer or CAD program "
                              "and upload it again.") from None
        if not mesh.is_watertight or mesh.volume <= 0:
            raise UploadError("That model has holes in its surface that I could not repair. "
                              "Repair it in your slicer or CAD program and upload it again.")
        return mesh
