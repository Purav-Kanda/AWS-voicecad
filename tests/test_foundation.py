import os
import time

import pytest

from voicecad.catalog import Catalog
from voicecad.config import Settings
from voicecad.files import prune_old_files, safe_output_path
from voicecad.parts.base import Part
from voicecad.parts.registry import default_parts
from voicecad.printer import PRESETS, PrinterProfile, parse_printer


def test_printer_parsing_accepts_presets_and_sizes():
    assert parse_printer("ender3") == PRESETS["ender3"]
    custom = parse_printer("200x180x150")
    assert (custom.bed_x, custom.bed_y, custom.bed_z) == (200, 180, 150)


@pytest.mark.parametrize("text", ["nope", "10x10", "0x10x10", "axbxc"])
def test_printer_parsing_rejects_nonsense(text):
    with pytest.raises(ValueError):
        parse_printer(text)


def test_bed_fit_allows_a_quarter_turn():
    p = PrinterProfile("t", 200, 100, 100)
    assert p.fits(100, 200, 50)
    assert not p.fits(201, 50, 50)


def test_settings_read_from_a_plain_mapping():
    s = Settings.from_env({"VOICECAD_PORT": "9001", "VOICECAD_PRINTER": "prusa_mk4", "VOICECAD_OUT": "/tmp/x"})
    assert s.port == 9001 and s.printer.name == PRESETS["prusa_mk4"].name


def test_settings_reject_a_bad_number_with_a_readable_message():
    with pytest.raises(ValueError, match="VOICECAD_PORT"):
        Settings.from_env({"VOICECAD_PORT": "eight"})


@pytest.mark.parametrize("name", ["../secret.stl", "a/b.stl", "a\\b.stl", "x.txt", "missing.stl"])
def test_unsafe_or_missing_file_names_are_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        safe_output_path(tmp_path, name, ".stl")


def test_a_real_file_name_resolves(tmp_path):
    (tmp_path / "ok.stl").write_text("x")
    assert safe_output_path(tmp_path, "ok.stl", ".stl") == (tmp_path / "ok.stl").resolve()


def test_prune_only_touches_old_stl_and_png(tmp_path):
    old, new, other = tmp_path / "a.stl", tmp_path / "b.stl", tmp_path / "keep.txt"
    for f in (old, new, other):
        f.write_text("x")
    past = time.time() - 100 * 3600
    for f in (old, other):
        os.utime(f, (past, past))
    assert prune_old_files(tmp_path, 24) == 1
    assert not old.exists() and new.exists() and other.exists()


def test_catalog_rejects_duplicate_and_mismatched_parts():
    parts = default_parts()
    with pytest.raises(ValueError, match="two parts"):
        Catalog([parts[0], parts[0]], PRESETS["ender3"])
    wrong = Part("other", parts[0].make_spec, parts[0].build)
    with pytest.raises(ValueError, match="names must match"):
        Catalog([wrong], PRESETS["ender3"])


def test_catalog_unknown_part(catalog):
    with pytest.raises(KeyError):
        catalog.build("teapot", {})
