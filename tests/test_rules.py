import pytest
from guided_intake import SessionStore

from conftest import errors


def test_box_with_walls_that_eat_the_inside_is_blocked(fresh):
    s = fresh("box", width=25, depth=25, height=40, wall=8, lid="no")
    assert any("space inside" in m for m in errors(s))
    assert not s.can_finish()


def test_box_bigger_than_the_print_bed_is_blocked_with_a_suggestion(fresh):
    s = fresh("box", width=300, depth=250, height=40, lid="no")
    assert any("print bed" in m for m in errors(s))


def test_thin_walls_only_warn(fresh):
    s = fresh("box", width=100, depth=60, height=40, wall=1.0, lid="no")
    assert errors(s) == []
    assert any(i.severity == "warning" for i in s.issues())
    assert s.can_finish()


def test_lid_that_cannot_fit_a_lip_is_blocked(fresh):
    s = fresh("box", width=20, depth=20, height=30, wall=6, lid="yes", lid_fit="snug")
    assert errors(s)


def test_bracket_hole_too_close_to_edge_is_blocked(fresh):
    s = fresh("bracket", arm_a=60, arm_b=80, width=10, hole_diameter=6)
    assert any("edge" in m for m in errors(s))


def test_bracket_defaults_make_a_finishable_spec(fresh):
    s = fresh("bracket", arm_a=60, arm_b=80, width=30)
    assert s.is_complete() and s.can_finish()


def test_stand_asks_only_what_it_needs(catalog):
    s = SessionStore(catalog.specs()).create("phone_stand")
    assert s.next_field().name == "device_thickness"
    s.set_value("device_thickness", "11 mm")
    assert s.next_field().name == "cable_slot"
    s.set_value("cable_slot", "yes")
    assert s.is_complete()  # angle and width have defaults


def _stand_errors(bed):
    from voicecad.catalog import Catalog
    from voicecad.parts.registry import default_parts
    from voicecad.printer import parse_printer

    small = Catalog(default_parts(), parse_printer(bed))
    s = SessionStore(small.specs()).create("phone_stand")
    s.set_many({"device_thickness": 11, "cable_slot": "no"})
    return errors(s)


def test_stand_bed_check_uses_the_computed_depth():
    # The default stand is 85 wide and 59 deep. A 60 mm bed edge fits it and a 58 mm edge does not.
    assert _stand_errors("90x60x100") == []
    assert any("print bed" in m for m in _stand_errors("90x58x100"))


def test_spoken_units_work_end_to_end(fresh):
    s = fresh("box", width="4 inches", depth="6 cm", height="40 millimeters", lid="no")
    assert s.answers()["width"] == pytest.approx(101.6)
    assert s.answers()["depth"] == 60.0
