"""Drive the real demo page in a headless browser. Skipped if Playwright or its browser is missing."""
import threading
import time

import pytest
import uvicorn

from voicecad.config import Settings
from voicecad.web import create_demo_app

sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def page_url(tmp_path):
    from test_strands_link import free_port

    port = free_port()
    app = create_demo_app(Settings(out_dir=tmp_path, port=port), offline=True)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/"
    server.should_exit = True
    thread.join(timeout=5)


def test_a_user_can_finish_a_part_in_the_browser(page_url):
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as err:
            pytest.skip(f"no browser available: {err}")
        page = browser.new_page()
        problems = []
        page.on("pageerror", lambda e: problems.append(str(e)))
        page.goto(page_url)
        page.uncheck("#speak")
        for line in ("I need a phone stand", "11 mm", "yes"):
            page.fill("#text", line)
            page.press("#text", "Enter")
        page.wait_for_selector("a[href$='.stl']", timeout=15000)
        assert "ready" in page.inner_text("#log")
        assert problems == []
        browser.close()


def test_a_user_can_upload_a_model_and_get_it_resized(page_url, tmp_path):
    import trimesh

    sample = tmp_path / "hook.stl"
    sample.write_bytes(trimesh.creation.box(extents=(40, 20, 10)).export(file_type="stl"))
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as err:
            pytest.skip(f"no browser available: {err}")
        page = browser.new_page()
        problems = []
        page.on("pageerror", lambda e: problems.append(str(e)))
        page.goto(page_url)
        page.uncheck("#speak")
        page.set_input_files("#file", str(sample))
        page.wait_for_selector("text=few words", timeout=15000)   # the assistant read the id and moved on
        assert "Uploaded hook.stl (40 x 20 x 10 mm)" in page.inner_text("#log")
        for line in ("a desk hook", "longest", "80 mm"):
            page.fill("#text", line)
            page.press("#text", "Enter")
        page.wait_for_selector("a[href$='.stl']", timeout=15000)
        assert "80 x 40 x 20 mm" in page.inner_text("#log")
        assert problems == []
        browser.close()
