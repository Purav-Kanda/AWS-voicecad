import pytest
from guided_intake import SessionStore

from conftest import errors
from voicecad.build import Finisher
from voicecad.parts import electronics_case, laptop_riser

RISER = {"rail_length": 250, "rear_height": 60, "front_height": 15, "rail_width": 30}
PI_CASE = {"board": "pi", "vents": True, "port_side": "front", "component_height": 17.0, "standoff_height": 5.0,
           "screw_hole": 2.7, "board_clearance": 1.0, "wall": 2.0}


def test_riser_is_a_watertight_wedge_with_the_asked_heights():
    built = laptop_riser.build({**RISER, "windows": True})
    rail = built.meshes["rail"]
    assert rail.is_watertight
    assert rail.extents[0] == pytest.approx(250.0, abs=0.01)
    assert rail.extents[2] == pytest.approx(60.0, abs=0.01)
    assert built.copies == {"rail": 2}


def test_riser_windows_remove_material():
    full = laptop_riser.build({**RISER, "windows": False}).meshes["rail"].volume
    open_ = laptop_riser.build({**RISER, "windows": True}).meshes["rail"].volume
    assert open_ < full


def test_riser_rules(fresh):
    low = fresh("laptop_riser", rail_length=250, rear_height=22, front_height=20)
    assert any("higher than the front" in m for m in errors(low))
    steep = fresh("laptop_riser", rail_length=100, rear_height=60)
    assert errors(steep) == [] and any("tilt" in i.message for i in steep.issues())


def test_pi_case_has_standoffs_and_a_port_opening():
    built = electronics_case.build(PI_CASE)
    body, lid = built.meshes["body"], built.meshes["lid"]
    assert body.is_watertight and lid.is_watertight
    # first standoff sits at wall + clearance + inset = 6.5 mm from each edge
    assert body.contains([[6.5 + 2.0, 6.5, 4.0]])[0]           # inside the post, beside its pilot hole
    assert not body.contains([[6.5, 6.5, 4.0]])[0]              # the pilot hole itself
    assert not body.contains([[body.extents[0] / 2, 1.0, 12.0]])[0]   # port opening on the front wall


def test_closed_case_keeps_its_wall_and_lid_without_vents():
    closed = electronics_case.build({**PI_CASE, "port_side": "none", "vents": False})
    assert closed.meshes["body"].contains([[closed.meshes["body"].extents[0] / 2, 1.0, 12.0]])[0]
    vented = electronics_case.build({**PI_CASE, "port_side": "none", "vents": True})
    assert vented.meshes["lid"].volume < closed.meshes["lid"].volume


def test_custom_board_fields_are_only_asked_for_custom(catalog):
    s = SessionStore(catalog.specs()).create("electronics_case")
    s.set_value("board", "pi")
    assert s.next_field().name == "vents"
    other = SessionStore(catalog.specs()).create("electronics_case")
    other.set_value("board", "custom")
    assert other.next_field().name == "board_length"


def test_custom_board_with_holes_off_the_board_is_blocked(fresh):
    s = fresh("electronics_case", board="custom", board_length=40, board_width=30, hole_spacing_x=38,
              hole_spacing_y=20, hole_inset=3.5, vents="no", port_side="none")
    assert any("outside the board" in m for m in errors(s))


def test_case_finishes_end_to_end(catalog, fresh, tmp_path):
    s = fresh("electronics_case", board="pi", vents="yes", port_side="left")
    result = Finisher(catalog, tmp_path)(s)
    assert {p["part"] for p in result["parts"]} == {"body", "lid"}, result
