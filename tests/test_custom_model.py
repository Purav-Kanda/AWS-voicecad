"""Uploading your own STL and resizing it: the store, the rules, the build and the routes."""
import json

import numpy as np
import pytest
import trimesh
from guided_intake import SessionStore
from starlette.testclient import TestClient

from test_server_e2e import Client, data
from voicecad import web
from voicecad.build import Finisher
from voicecad.catalog import Catalog
from voicecad.config import Settings
from voicecad.offline import OfflineAssistant, pick_part
from voicecad.parts.custom_model import scale_factors
from voicecad.parts.registry import default_parts
from voicecad.printer import DEFAULT_PRINTER
from voicecad.server import create_app
from voicecad.uploads import UploadError, UploadStore


def stl_bytes(x=40.0, y=20.0, z=10.0) -> bytes:
    out = trimesh.creation.box(extents=(x, y, z)).export(file_type="stl")
    return out if isinstance(out, bytes) else out.encode()


@pytest.fixture
def store(tmp_path):
    return UploadStore(tmp_path / "uploads", max_bytes=1024 * 1024)


@pytest.fixture
def uploaded(store):
    return store.save("hook.stl", stl_bytes())


@pytest.fixture
def custom(store):
    catalog = Catalog(default_parts(store.load), DEFAULT_PRINTER)
    sessions = SessionStore(catalog.specs())

    def make(upload_id, **answers):
        session = sessions.create("custom_model")
        results = session.set_many({"upload_id": upload_id, **answers})
        assert all(r.ok for r in results), [r.message for r in results]
        return session
    return catalog, make


def errors(session):
    return [i for i in session.issues() if i.severity == "error"]


def warnings(session):
    return [i.message for i in session.issues() if i.severity == "warning"]


# --- the store ---------------------------------------------------------------------------

def test_a_good_stl_is_saved_and_reports_its_size(store):
    up = store.save("My Hook.STL", stl_bytes(40, 20, 10))
    assert up.name == "My Hook.STL" and up.size_mm == (40.0, 20.0, 10.0)
    assert store.load(up.id).extents.tolist() == pytest.approx([40, 20, 10])


@pytest.mark.parametrize("name,payload,reason", [
    ("model.obj", b"v 0 0 0", "Only .stl"),
    ("model.stl", b"", "empty"),
    ("model.stl", b"this is not a mesh at all", "could not read|no surface"),
])
def test_bad_files_are_refused_with_a_reason(store, name, payload, reason):
    with pytest.raises(UploadError, match=reason):
        store.save(name, payload)


def test_an_oversized_file_is_refused(store):
    # Built inside the test, not as a parameter: pytest copies parameters into an environment variable,
    # and Windows refuses values over 32767 characters.
    with pytest.raises(UploadError, match="larger than"):
        store.save("model.stl", b"x" * (store.max_bytes + 1))


def test_a_flat_model_is_refused(store):
    flat = trimesh.Trimesh(vertices=[(0, 0, 0), (10, 0, 0), (0, 10, 0)], faces=[(0, 1, 2)]).export(file_type="stl")
    with pytest.raises(UploadError):
        store.save("flat.stl", flat)


def test_a_model_with_unfixable_holes_is_refused(store):
    box = trimesh.creation.box(extents=(10, 10, 10))
    box.update_faces(np.arange(len(box.faces)) >= 6)   # drop several faces: too many missing to patch
    with pytest.raises(UploadError, match="holes"):
        store.save("open.stl", box.export(file_type="stl"))


def test_a_small_hole_is_repaired_not_refused(store):
    pytest.importorskip("networkx")   # trimesh needs it to patch holes; it is a declared dependency
    box = trimesh.creation.box(extents=(10, 10, 10))
    box.update_faces(np.arange(len(box.faces)) != 0)   # one missing triangle: a small, patchable hole
    assert store.save("small_hole.stl", box.export(file_type="stl")).size_mm == (10.0, 10.0, 10.0)


def test_a_failing_repair_library_gives_an_answer_not_a_crash(store, monkeypatch):
    def broken(_mesh):
        raise ModuleNotFoundError("No module named 'networkx'")

    monkeypatch.setattr(trimesh.repair, "fill_holes", broken)
    with pytest.raises(UploadError, match="could not check"):
        store.save("cube.stl", stl_bytes())


@pytest.mark.parametrize("bad", ["", "../../etc/passwd", "ABCDEF123456", "abc", "0123456789abc", "0123456789a/"])
def test_ids_that_are_not_ours_never_touch_the_disk(store, bad):
    with pytest.raises(UploadError):
        store.load(bad)


def test_an_unknown_but_well_formed_id_says_to_upload_again(store):
    with pytest.raises(UploadError, match="upload it again"):
        store.load("0123456789ab")


def test_load_returns_a_private_copy(store, uploaded):
    first = store.load(uploaded.id)
    first.apply_scale(5)
    assert store.load(uploaded.id).extents.max() == pytest.approx(40)


def test_old_uploads_are_pruned_when_a_new_one_arrives(tmp_path):
    old = UploadStore(tmp_path, retention_hours=1)
    first = old.save("a.stl", stl_bytes())
    path = tmp_path / f"{first.id}.stl"
    import os
    os.utime(path, (0, 0))
    old.save("b.stl", stl_bytes())
    assert not path.exists()


# --- the sizing arithmetic ---------------------------------------------------------------

@pytest.mark.parametrize("answers,expected", [
    ({"sizing": "keep"}, (1, 1, 1)),
    ({"sizing": "longest", "longest_mm": 80}, (2, 2, 2)),
    ({"sizing": "percent", "percent": 50}, (0.5, 0.5, 0.5)),
    ({"sizing": "each", "width": 80, "depth": 10, "height": 10}, (2, 0.5, 1)),
])
def test_scale_factors(answers, expected):
    assert scale_factors((40, 20, 10), answers) == pytest.approx(expected)


# --- the rules ---------------------------------------------------------------------------

def test_keeping_the_size_is_clean(custom, uploaded):
    _, make = custom
    s = make(uploaded.id, what_it_is="desk hook", sizing="keep")
    assert s.issues() == [] and s.can_finish()


def test_rules_wait_for_the_numbers_of_the_chosen_mode(custom, uploaded):
    _, make = custom
    s = make(uploaded.id, what_it_is="hook", sizing="longest")
    assert s.next_field().name == "longest_mm" and not s.can_finish()
    s.set_value("longest_mm", "80")
    assert s.can_finish()


def test_a_size_too_big_for_the_bed_names_the_answers_to_change(custom, uploaded):
    _, make = custom
    s = make(uploaded.id, what_it_is="hook", sizing="longest", longest_mm="500")
    (issue,) = errors(s)
    assert "does not fit" in issue.message and set(issue.fields) == {"sizing", "longest_mm"}


def test_the_bed_check_uses_the_final_size_not_the_upload_size(custom, store):
    _, make = custom
    big = store.save("big.stl", stl_bytes(300, 100, 20))       # does not fit as uploaded
    assert errors(make(big.id, what_it_is="plate", sizing="keep"))
    assert not errors(make(big.id, what_it_is="plate", sizing="percent", percent="50"))


def test_stretching_one_side_warns_about_distortion(custom, uploaded):
    _, make = custom
    s = make(uploaded.id, what_it_is="hook", sizing="each", width="80", depth="20", height="10")
    assert any("oval" in w for w in warnings(s)) and not errors(s)


def test_even_scaling_does_not_warn_about_distortion(custom, uploaded):
    _, make = custom
    s = make(uploaded.id, what_it_is="hook", sizing="each", width="80", depth="40", height="20")
    assert warnings(s) == []


def test_big_shrinks_warn_about_thin_walls(custom, uploaded):
    _, make = custom
    assert any("thins every wall" in w for w in warnings(make(uploaded.id, what_it_is="x", sizing="percent", percent="50")))


def test_a_side_that_becomes_too_thin_is_an_error(custom, store):
    _, make = custom
    sheet = store.save("sheet.stl", stl_bytes(100, 100, 2))
    s = make(sheet.id, what_it_is="sheet", sizing="percent", percent="10")
    assert any("too thin" in i.message for i in errors(s))


def test_tiny_and_huge_uploads_get_a_units_warning(custom, store):
    _, make = custom
    tiny = store.save("tiny.stl", stl_bytes(1, 1, 1))
    huge = store.save("huge.stl", stl_bytes(900, 900, 900))
    assert any("assumed millimeters" in w for w in warnings(make(tiny.id, what_it_is="x", sizing="keep")))
    assert any("assumed millimeters" in w for w in warnings(make(huge.id, what_it_is="x", sizing="percent", percent="10")))


def test_a_missing_upload_is_an_error_the_assistant_can_speak(custom):
    _, make = custom
    s = make("0123456789ab", what_it_is="hook", sizing="keep")
    (issue,) = errors(s)
    assert "upload it again" in issue.message and issue.fields == ("upload_id",)


# --- the build ---------------------------------------------------------------------------

def test_building_scales_the_real_geometry_and_sits_on_the_bed(custom, uploaded):
    catalog, _ = custom
    built = catalog.build("custom_model", {"upload_id": uploaded.id, "what_it_is": "desk hook",
                                           "sizing": "each", "width": 80.0, "depth": 20.0, "height": 15.0})
    shape = built.meshes["model"]
    assert shape.extents.tolist() == pytest.approx([80, 20, 15])
    assert shape.bounds[0].tolist() == pytest.approx([0, 0, 0])
    assert shape.volume == pytest.approx(80 * 20 * 15)
    assert built.notes[0].startswith("Resized desk hook") and "from 40 by 20 by 10" in built.notes[0]


def test_uniform_scaling_changes_volume_by_the_cube(custom, uploaded):
    catalog, _ = custom
    built = catalog.build("custom_model", {"upload_id": uploaded.id, "what_it_is": "x", "sizing": "percent", "percent": 200.0})
    assert built.meshes["model"].volume == pytest.approx(40 * 20 * 10 * 8)


def test_finish_writes_a_printable_stl(custom, uploaded, tmp_path):
    catalog, make = custom
    s = make(uploaded.id, what_it_is="hook", sizing="longest", longest_mm="80")
    result = Finisher(catalog, tmp_path / "out")(s)
    assert "parts" in result and result["parts"][0]["size_mm"] == [80.0, 40.0, 20.0]
    assert (tmp_path / "out" / result["parts"][0]["file"]).is_file()


def test_the_part_is_not_offered_without_uploads():
    assert "custom_model" not in {p.name for p in default_parts()}


# --- the routes and the assistants -------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    app = web.create_demo_app(Settings(out_dir=tmp_path), offline=True)
    with TestClient(app, base_url="http://127.0.0.1:8000") as http:
        yield http, tmp_path


def test_upload_route_returns_an_id_and_the_size(client):
    http, _ = client
    r = http.post("/upload?name=hook.stl", content=stl_bytes())
    assert r.status_code == 200
    body = r.json()
    assert len(body["id"]) == 12 and body["size_mm"] == [40.0, 20.0, 10.0] and body["name"] == "hook.stl"


@pytest.mark.parametrize("name,payload,status", [
    ("a.stl", b"garbage", 400),
    ("a.txt", b"hello", 400),
    ("a.stl", b"", 400),
])
def test_upload_route_gives_readable_errors(client, name, payload, status):
    http, _ = client
    r = http.post(f"/upload?name={name}", content=payload)
    assert r.status_code == status and r.json()["error"]


def test_upload_route_refuses_huge_files_early(tmp_path):
    app = web.create_demo_app(Settings(out_dir=tmp_path, max_upload_mb=0.0001), offline=True)
    with TestClient(app, base_url="http://127.0.0.1:8000") as http:
        r = http.post("/upload?name=a.stl", content=stl_bytes())
    assert r.status_code == 413


def test_the_offline_assistant_resizes_an_uploaded_model_end_to_end(client):
    http, out = client
    up = http.post("/upload?name=hook.stl", content=stl_bytes()).json()
    message = f"I uploaded a 3D model file called hook.stl. Its id is {up['id']} and it is 40 x 20 x 10 millimeters."
    said = http.post("/chat", json={"session": "s", "message": message}).json()
    assert "few words" in said["reply"]          # the id was read from the message, so it moves on
    http.post("/chat", json={"session": "s", "message": "a desk hook"})
    http.post("/chat", json={"session": "s", "message": "longest"})
    done = http.post("/chat", json={"session": "s", "message": "80 mm"}).json()
    assert done["files"] and done["files"][0]["size_mm"] == [80.0, 40.0, 20.0]
    assert (out / done["files"][0]["stl"].rsplit("/", 1)[1]).is_file()


def test_offline_too_big_asks_again_and_recovers(client):
    http, _ = client
    up = http.post("/upload?name=hook.stl", content=stl_bytes()).json()
    for text in (f"I uploaded a file. Its id is {up['id']}.", "a hook", "longest"):
        http.post("/chat", json={"session": "s", "message": text})
    again = http.post("/chat", json={"session": "s", "message": "500 mm"}).json()
    assert "does not fit" in again["reply"]
    done = http.post("/chat", json={"session": "s", "message": "longest"})
    assert done.status_code == 200
    assert http.post("/chat", json={"session": "s", "message": "100"}).json()["files"]


def test_the_word_uploaded_picks_the_custom_part_before_any_keyword():
    assert pick_part("I uploaded a phone stand file") == "custom_model"


# --- over the real MCP wire format -------------------------------------------------------

def test_mcp_clients_can_resize_an_upload_by_id(tmp_path):
    settings = Settings(out_dir=tmp_path)
    store = UploadStore(settings.upload_dir)
    up = store.save("hook.stl", stl_bytes())
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8000") as http:
        c = Client(http)
        assert "custom_model" in json.dumps(data(c.call("list_specs")))
        sid = data(c.call("start_intake", spec_name="custom_model"))["session_id"]
        c.call("submit_answers", session_id=sid,
               answers={"upload_id": up.id, "what_it_is": "hook", "sizing": "percent", "percent": "150"})
        done = data(c.call("finish", session_id=sid))
    assert done["parts"][0]["size_mm"] == [60.0, 30.0, 15.0]


def test_offline_assistant_catalog_matches_the_real_one(tmp_path):
    store = UploadStore(tmp_path / "u")
    catalog = Catalog(default_parts(store.load), DEFAULT_PRINTER)
    assert OfflineAssistant(catalog, Finisher(catalog, tmp_path)).chat("s", "hello").reply.count("resized model") == 1
