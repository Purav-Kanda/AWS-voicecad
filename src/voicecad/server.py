"""Composition root: the one place that wires settings, catalog and tools together."""
from __future__ import annotations

from guided_intake import SessionStore
from guided_intake.mcp_tools import register_intake_tools
from mcp.server.mcpserver import Image, MCPServer
from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles

from .build import Finisher
from .catalog import Catalog
from .config import Settings
from .files import safe_output_path
from .instructions import INSTRUCTIONS
from .parts.registry import default_parts
from .preview import render_png
from .uploads import UploadStore


def make_uploads(settings: Settings) -> UploadStore:
    return UploadStore(settings.upload_dir, int(settings.max_upload_mb * 1024 * 1024), settings.retention_hours)


def create_server(settings: Settings | None = None, catalog: Catalog | None = None) -> MCPServer:
    settings = settings or Settings.from_env()
    catalog = catalog or Catalog(default_parts(make_uploads(settings).load), settings.printer)
    out_dir = settings.out_dir

    server = MCPServer("voicecad", instructions=INSTRUCTIONS)
    finisher = Finisher(catalog, out_dir, settings.retention_hours)
    register_intake_tools(server, SessionStore(catalog.specs()), finisher)

    @server.tool()
    def preview_part(file: str) -> Image:
        """Show a picture of a part that finish created. Pass the file name from finish.
        Only call this if the user asks to see the part."""
        import trimesh  # local import keeps server start fast

        path = safe_output_path(out_dir, file, ".stl")
        png = path.with_suffix(".png")
        if not png.exists():
            render_png(trimesh.load_mesh(path), png)
        return Image(data=png.read_bytes(), format="png")

    return server


def create_app(settings: Settings | None = None, catalog: Catalog | None = None) -> Starlette:
    """ASGI app: MCP at /mcp and the generated files at /files."""
    settings = settings or Settings.from_env()
    settings.out_dir.mkdir(parents=True, exist_ok=True)
    app = create_server(settings, catalog).streamable_http_app()
    app.mount("/files", StaticFiles(directory=settings.out_dir), name="files")
    return app


def main() -> None:
    settings = Settings.from_env()
    create_server(settings).run("streamable-http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
