"""The same MCP client the Bedrock agent uses, talking to a real server over a real socket.

No model is called, so this needs no AWS account. It proves the agent side can reach every tool.
"""
import socket
import threading
import time

import pytest
import uvicorn
from strands.tools.mcp import MCPClient

from voicecad.agent import extract_parts
from voicecad.config import Settings
from voicecad.server import create_app


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_url(tmp_path):
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(Settings(out_dir=tmp_path, port=port)),
                                           host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp", tmp_path
    server.should_exit = True
    thread.join(timeout=5)


def test_agent_side_client_lists_and_calls_the_tools(live_url):
    url, out = live_url
    client = MCPClient(url=url)
    with client:
        tools = client.list_tools_sync()
        names = {t.tool_name for t in tools}
        assert {"start_intake", "submit_answers", "finish", "preview_part"} <= names

        started = client.call_tool_sync("t1", "start_intake", {"spec_name": "phone_stand"})
        assert started["status"] == "success"
        sid = started["structuredContent"]["session_id"] if started.get("structuredContent") else None
        assert sid

        client.call_tool_sync("t2", "submit_answers",
                              {"session_id": sid, "answers": {"device_thickness": "11 mm", "cable_slot": "yes"}})
        done = client.call_tool_sync("t3", "finish", {"session_id": sid})
        parts = extract_parts([{"role": "user", "content": [{"toolResult": done}]}])
        assert parts and (out / parts[0]["file"]).exists()
