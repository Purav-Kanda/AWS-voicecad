"""Demo app: a simulated voice assistant in the browser, backed by the voicecad MCP server.

One process serves everything: MCP at /mcp, the chat page at /, the chat API at /chat,
and generated files at /files.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import trimesh
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse

from .agent import Assistant
from .build import Finisher
from .catalog import Catalog
from .config import Settings
from .offline import OfflineAssistant
from .parts.registry import default_parts
from .preview import render_png
from .server import create_app, make_uploads
from .uploads import UploadError

STATIC = Path(__file__).parent / "static"
log = logging.getLogger("voicecad")


def plain_error(err: Exception) -> str:
    name = type(err).__name__
    text = str(err)
    if "NoCredentials" in name or "Unable to locate credentials" in text:
        return "No AWS credentials found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or run aws configure."
    if "UnrecognizedClient" in text or "ExpiredToken" in text or "security token" in text:
        return "AWS rejected the credentials. They may be wrong, expired, or missing a session token."
    if "AccessDenied" in text or "not authorized" in text:
        # Show AWS's own words: the cause (key policy, model, region, use case form) is only in there.
        return f"AWS refused the Bedrock call. AWS said: {text[:400]}"
    return f"{name}: {text[:300]}"


def create_demo_app(settings: Settings | None = None, mcp_url: str | None = None,
                    offline: bool | None = None) -> Starlette:
    settings = settings or Settings.from_env()
    target = settings.out_dir
    if offline is None:
        offline = os.environ.get("VOICECAD_OFFLINE") == "1"
    uploads = make_uploads(settings)
    catalog = Catalog(default_parts(uploads.load), settings.printer)
    app = create_app(settings, catalog)
    if offline:
        assistant: Assistant | OfflineAssistant = OfflineAssistant(
            catalog, Finisher(catalog, target, settings.retention_hours))
    else:
        assistant = Assistant(mcp_url or os.environ.get("VOICECAD_MCP_URL") or f"http://127.0.0.1:{settings.port}/mcp")

    async def index(_: Request) -> FileResponse:
        return FileResponse(STATIC / "index.html")

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    def describe(part: dict) -> dict:
        stl = target / Path(part["file"]).name   # only ever look inside the output folder
        png = stl.with_suffix(".png")
        if stl.exists() and not png.exists():
            render_png(trimesh.load(stl), png)
        return {"part": part.get("part"), "size_mm": part.get("size_mm"),
                "stl": f"/files/{stl.name}", "png": f"/files/{png.name}"}

    async def chat(request: Request) -> JSONResponse:
        try:
            body = await request.json()
            text = str(body.get("message", "")).strip()
            session_id = str(body.get("session", "default"))[:64]
        except Exception:
            return JSONResponse({"error": "That request was not valid JSON."}, status_code=400)
        if not text:
            return JSONResponse({"error": "Say or type something first."}, status_code=400)
        try:
            turn = await run_in_threadpool(assistant.chat, session_id, text)
            files = await run_in_threadpool(lambda: [describe(p) for p in turn.parts])
        except Exception as err:  # most often missing AWS credentials or model access
            log.exception("chat turn failed")
            return JSONResponse({"error": plain_error(err)}, status_code=502)
        return JSONResponse({"reply": turn.reply, "files": files})

    async def upload(request: Request) -> JSONResponse:
        """Raw file bytes in the body, the file name in ?name=. No form library needed."""
        name = request.query_params.get("name", "model.stl")
        try:
            if int(request.headers.get("content-length", "0")) > uploads.max_bytes:
                raise UploadError("That file is too large.")
            data = bytearray()
            async for chunk in request.stream():
                data += chunk
                if len(data) > uploads.max_bytes:
                    raise UploadError("That file is too large.")
            saved = await run_in_threadpool(uploads.save, name, bytes(data))
        except ValueError as err:   # UploadError is a ValueError; so is a bad content-length header
            message = str(err) if isinstance(err, UploadError) else "That upload request was not valid."
            return JSONResponse({"error": message}, status_code=413 if "too large" in message else 400)
        return JSONResponse({"id": saved.id, "name": saved.name, "size_mm": list(saved.size_mm)})

    app.add_route("/", index)
    app.add_route("/health", health)
    app.add_route("/chat", chat, methods=["POST"])
    app.add_route("/upload", upload, methods=["POST"])
    return app
