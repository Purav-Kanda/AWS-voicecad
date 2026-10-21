"""The demo page's routes, with the Bedrock assistant replaced by a stub."""
import pytest
from starlette.testclient import TestClient

from voicecad import web
from voicecad.agent import Turn
from voicecad.build import Finisher
from voicecad.config import Settings


class StubAssistant:
    def __init__(self, url):
        self.url, self.fail, self.parts = url, None, []

    def chat(self, session_id, text):
        if self.fail:
            raise self.fail
        return Turn(reply=f"you said {text}", parts=self.parts)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "Assistant", StubAssistant)
    app = web.create_demo_app(Settings(out_dir=tmp_path), mcp_url="http://unused")
    with TestClient(app, base_url="http://127.0.0.1:8000") as http:
        yield http, tmp_path


def test_page_and_health(client):
    http, _ = client
    assert "<html" in http.get("/").text.lower()
    assert http.get("/health").json() == {"ok": True}


def test_chat_returns_the_reply(client):
    http, _ = client
    body = http.post("/chat", json={"message": "hello", "session": "s1"}).json()
    assert body == {"reply": "you said hello", "files": []}


@pytest.mark.parametrize("payload", [b"not json", b'{"message": "   "}'])
def test_chat_rejects_bad_requests_with_a_readable_message(client, payload):
    http, _ = client
    r = http.post("/chat", content=payload, headers={"content-type": "application/json"})
    assert r.status_code == 400 and r.json()["error"]


def test_aws_problems_become_plain_messages(client, monkeypatch):
    http, _ = client

    class NoCredentialsError(Exception):
        pass

    monkeypatch.setattr(StubAssistant, "chat", lambda self, s, t: (_ for _ in ()).throw(
        NoCredentialsError("Unable to locate credentials")))
    r = http.post("/chat", json={"message": "hi"})
    assert r.status_code == 502 and "AWS credentials" in r.json()["error"]


def test_finished_part_gets_a_preview_and_download_links(client, monkeypatch, catalog, fresh):
    http, out = client
    result = Finisher(catalog, out)(fresh("box", width=100, depth=60, height=40, lid="no"))
    monkeypatch.setattr(StubAssistant, "chat", lambda self, s, t: Turn("done", result["parts"]))
    files = http.post("/chat", json={"message": "finish"}).json()["files"]
    assert files[0]["stl"].startswith("/files/") and (out / files[0]["png"].split("/")[-1]).exists()
    assert http.get(files[0]["stl"]).status_code == 200
    assert http.get(files[0]["png"]).headers["content-type"] == "image/png"


def test_part_names_cannot_point_outside_the_output_folder(client, monkeypatch):
    http, out = client
    evil = [{"part": "x", "file": "../../etc/passwd", "size_mm": [1, 1, 1]}]
    monkeypatch.setattr(StubAssistant, "chat", lambda self, s, t: Turn("done", evil))
    files = http.post("/chat", json={"message": "x"}).json()["files"]
    assert files[0]["stl"] == "/files/passwd"   # reduced to a bare name inside the folder
    assert not (out / "passwd").exists()
