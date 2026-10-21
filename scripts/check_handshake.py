"""Talk to a running voicecad server over plain HTTP and print what protocol it speaks.

Usage: python scripts/check_handshake.py [http://127.0.0.1:8000/mcp]
Exits with an error if the server will not agree to MCP protocol 2025-11-25.
"""
import json
import sys

import httpx

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
WANT = "2025-11-25"
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def decode(resp: httpx.Response) -> dict:
    """Streamable HTTP may answer with plain JSON or a single SSE event."""
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise SystemExit(f"no data event in response: {resp.text[:200]}")
    return resp.json()


def rpc(client: httpx.Client, headers: dict, ident: int, method: str, params: dict | None = None) -> dict:
    body = {"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}}
    resp = client.post(URL, headers=headers, json=body)
    resp.raise_for_status()
    return decode(resp)


with httpx.Client(timeout=30) as client:
    init = {"protocolVersion": WANT, "capabilities": {}, "clientInfo": {"name": "handshake-check", "version": "0"}}
    first = client.post(URL, headers=HEADERS, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": init})
    first.raise_for_status()
    reply = decode(first)["result"]
    print("server agreed to protocol:", reply["protocolVersion"])
    print("server name:", reply["serverInfo"]["name"])
    if reply["protocolVersion"] < WANT:
        raise SystemExit(f"server only offers {reply['protocolVersion']}, which is older than {WANT}")

    session = {**HEADERS, "MCP-Protocol-Version": reply["protocolVersion"]}
    if "mcp-session-id" in first.headers:
        session["mcp-session-id"] = first.headers["mcp-session-id"]
    client.post(URL, headers=session, json={"jsonrpc": "2.0", "method": "notifications/initialized"})

    tools = rpc(client, session, 2, "tools/list")["result"]["tools"]
    print("tools:", ", ".join(t["name"] for t in tools))

    started = rpc(client, session, 3, "tools/call", {"name": "start_intake", "arguments": {"spec_name": "box"}})
    payload = started["result"].get("structuredContent") or json.loads(started["result"]["content"][0]["text"])
    print("first question:", payload["next_question"]["question"])
