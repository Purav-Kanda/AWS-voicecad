"""Seeded random designs. Whatever the rules accept must build into a clean, printable mesh."""
import random

import pytest
from guided_intake import SessionStore

from voicecad.build import Finisher
from voicecad.catalog import Catalog
from voicecad.parts.registry import default_parts
from voicecad.printer import parse_printer

PER_PART = 20


def random_answers(spec, rng):
    answers = {}
    for f in spec.fields:
        if f.kind == "number":
            answers[f.name] = str(round(rng.uniform(f.minimum, f.maximum), 1))
        elif f.kind == "bool":
            answers[f.name] = rng.choice(["yes", "no"])
        elif f.kind == "choice":
            answers[f.name] = rng.choice(f.choices)
    return answers


@pytest.mark.parametrize("part_name", [p.name for p in default_parts()])
def test_every_accepted_design_builds(part_name, tmp_path):
    catalog = Catalog(default_parts(), parse_printer("400x400x400"))   # big bed, so size rules do not hide bugs
    store = SessionStore(catalog.specs())
    finisher = Finisher(catalog, tmp_path)
    spec = next(s for s in catalog.specs() if s.name == part_name)
    rng = random.Random(7)

    built = 0
    for _ in range(PER_PART):
        session = store.create(part_name)
        session.set_many(random_answers(spec, rng))
        if not session.can_finish():
            continue
        result = finisher(session)
        assert result.get("ok") is not False, (session.answers(), result)
        built += 1
    assert built >= PER_PART // 2, "rules blocked most random designs, so this test checks too little"
