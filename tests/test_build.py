import math

import pytest
import trimesh

from voicecad.build import Finisher
from voicecad.geometry import wedge
from voicecad.parts import box, bracket, phone_stand


def test_wedge_is_a_valid_solid_with_the_right_volume():
    w = wedge((0, 0), (10, 0), (0, 10), 0, 4)
    assert w.is_watertight and w.is_winding_consistent
    assert w.volume == pytest.approx(200.0)


def test_box_volume_matches_walls_and_floor():
    built = box.build({"width": 100, "depth": 60, "height": 40, "wall": 2.0, "lid": False})
    expected = 100 * 60 * 40 - 96 * 56 * 38  # open top, floor as thick as a wall
    assert built.meshes["body"].volume == pytest.approx(expected)
    assert set(built.meshes) == {"body"}


def test_box_lid_is_a_separate_printable_part():
    built = box.build({"width": 100, "depth": 60, "height": 40, "wall": 2.0, "lid": True, "lid_fit": "snug"})
    assert {"body", "lid"} == set(built.meshes)
    assert all(p.is_watertight for p in built.meshes.values())


def test_bracket_is_one_watertight_part_lying_flat():
    built = bracket.build({"arm_a": 60, "arm_b": 80, "width": 30, "thickness": 4.0,
                           "hole_diameter": 4.0, "gusset": True})
    part = built.meshes["bracket"]
    assert part.is_watertight
    assert sorted(float(v) for v in part.extents) == pytest.approx([30.0, 60.0, 80.0], abs=0.01)
    assert part.extents[2] == pytest.approx(30.0, abs=0.01)  # width is the height on the bed
    assert any("lying on its side" in n for n in built.notes)


def test_bracket_with_gusset_has_more_material_than_without():
    base = {"arm_a": 60, "arm_b": 80, "width": 30, "thickness": 4.0, "hole_diameter": 4.0}
    with_g = bracket.build({**base, "gusset": True}).meshes["bracket"].volume
    without = bracket.build({**base, "gusset": False}).meshes["bracket"].volume
    assert with_g > without


def test_bracket_skips_gusset_when_it_would_cover_a_hole():
    built = bracket.build({"arm_a": 18, "arm_b": 18, "width": 20, "thickness": 4.0,
                           "hole_diameter": 4.0, "gusset": True})
    assert any("left it out" in n for n in built.notes)
    assert built.meshes["bracket"].is_watertight


STAND = {"device_thickness": 11.0, "viewing_angle": 65.0, "base_width": 85.0}


def test_stand_has_lip_and_leaning_plate():
    stand = phone_stand.build({**STAND, "cable_slot": False}).meshes["stand"]
    assert stand.is_watertight
    assert stand.extents[0] == pytest.approx(85.0)
    assert stand.extents[2] == pytest.approx(60.0, abs=0.5)


def test_cable_hole_really_goes_through_the_base():
    solid = phone_stand.build({**STAND, "cable_slot": False}).meshes["stand"]
    holed = phone_stand.build({**STAND, "cable_slot": True}).meshes["stand"]
    gap = 12.0 / math.cos(math.radians(25))
    probe = [[42.5, 6.0 + gap / 2, 4.0]]  # middle of the base, between the lip and the plate
    assert solid.contains(probe)[0]
    assert not holed.contains(probe)[0]
    assert holed.is_watertight


def test_finisher_writes_stl_files_that_load_back(catalog, fresh, tmp_path):
    session = fresh("box", width="10 cm", depth="6 cm", height="40", lid="yes", lid_fit="snug")
    result = Finisher(catalog, tmp_path)(session)
    assert {p["part"] for p in result["parts"]} == {"body", "lid"}
    for part in result["parts"]:
        assert trimesh.load(tmp_path / part["file"]).is_watertight
        assert part["volume_cm3"] > 0 and part["print_count"] == 1
    assert result["parts"][0]["size_mm"] == [100.0, 60.0, 40.0]
    assert result["summary"].startswith("The storage box is ready")


def test_finisher_turns_a_crashing_builder_into_a_spoken_error(catalog, fresh, tmp_path, monkeypatch):
    session = fresh("box", width=100, depth=60, height=40, lid="no")

    def boom(name, answers):
        raise RuntimeError("manifold exploded")

    monkeypatch.setattr(catalog, "build", boom)
    result = Finisher(catalog, tmp_path)(session)
    assert result["ok"] is False and "could not build" in result["error"]
    assert list(tmp_path.iterdir()) == []


def test_finisher_removes_stale_files(catalog, fresh, tmp_path):
    import os
    import time
    old = tmp_path / "old.stl"
    old.write_text("x")
    long_ago = time.time() - 72 * 3600
    os.utime(old, (long_ago, long_ago))
    Finisher(catalog, tmp_path, retention_hours=24)(fresh("box", width=100, depth=60, height=40, lid="no"))
    assert not old.exists()
