"""Drive the real ASGI app over the MCP wire format, in process."""
import base64
import json

import pytest
from starlette.testclient import TestClient

from voicecad.config import Settings
from voicecad.server import create_app

HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


def parse(response):
    """Streamable HTTP may answer with plain JSON or a one-event stream."""
    if response.headers["content-type"].startswith("text/event-stream"):
        data = [line[5:].strip() for line in response.text.splitlines() if line.startswith("data:")]
        return json.loads(data[-1])
    return response.json()


class Client:
    def __init__(self, http):
        self.http, self.next_id, self.headers = http, 1, dict(HEADERS)
        reply = self.http.post("/mcp", headers=self.headers, json={
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                       "clientInfo": {"name": "t", "version": "1"}}})
        self.init = parse(reply)["result"]
        if "mcp-session-id" in reply.headers:
            self.headers["mcp-session-id"] = reply.headers["mcp-session-id"]
        self.http.post("/mcp", headers=self.headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, name, **arguments):
        self.next_id += 1
        body = {"jsonrpc": "2.0", "id": self.next_id, "method": "tools/call",
                "params": {"name": name, "arguments": arguments}}
        return parse(self.http.post("/mcp", headers=self.headers, json=body))["result"]

    def tools(self):
        self.next_id += 1
        body = {"jsonrpc": "2.0", "id": self.next_id, "method": "tools/list"}
        return parse(self.http.post("/mcp", headers=self.headers, json=body))["result"]["tools"]


def data(result):
    if result.get("structuredContent"):
        return result["structuredContent"]
    return json.loads(result["content"][0]["text"])


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(out_dir=tmp_path))
    with TestClient(app, base_url="http://127.0.0.1:8000") as http:
        yield Client(http), tmp_path


def test_server_negotiates_the_protocol_version_alexa_needs(client):
    c, _ = client
    assert c.init["protocolVersion"] == "2025-11-25"


def test_all_tools_are_listed(client):
    c, _ = client
    names = {t["name"] for t in c.tools()}
    assert {"list_specs", "start_intake", "submit_answers", "review", "finish", "preview_part"} <= names


def test_a_whole_conversation_ends_in_files_and_a_preview(client):
    c, out = client
    specs = data(c.call("list_specs"))
    assert "electronics_case" in json.dumps(specs) and "laptop_riser" in json.dumps(specs)

    started = data(c.call("start_intake", spec_name="box"))
    sid = started["session_id"]
    assert started["next_question"]["name"] == "width"

    c.call("submit_answers", session_id=sid, answers={"width": "10 cm", "depth": "6 cm", "height": "40", "lid": "no"})
    done = data(c.call("finish", session_id=sid))
    assert done["parts"][0]["size_mm"] == [100.0, 60.0, 40.0]
    assert (out / done["parts"][0]["file"]).exists()

    picture = c.call("preview_part", file=done["parts"][0]["file"])
    assert picture["content"][0]["type"] == "image"
    assert base64.b64decode(picture["content"][0]["data"]).startswith(b"\x89PNG")


def test_preview_refuses_paths_outside_the_output_folder(client):
    c, _ = client
    result = c.call("preview_part", file="../../etc/passwd")
    assert result.get("isError") is True


def test_blocked_design_cannot_finish(client):
    c, out = client
    sid = data(c.call("start_intake", spec_name="box"))["session_id"]
    c.call("submit_answers", session_id=sid, answers={"width": "300", "depth": "250", "height": "40", "lid": "no"})
    result = c.call("finish", session_id=sid)
    assert "print bed" in json.dumps(result)
    assert list(out.glob("*.stl")) == []
