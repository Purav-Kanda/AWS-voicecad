import pytest
from guided_intake import SessionStore

from voicecad.catalog import Catalog
from voicecad.parts.registry import default_parts
from voicecad.printer import DEFAULT_PRINTER


@pytest.fixture
def catalog():
    return Catalog(default_parts(), DEFAULT_PRINTER)


@pytest.fixture
def fresh(catalog):
    """Start a session for a part and fill in answers, failing loudly if one is rejected."""
    def make(spec_name, **answers):
        session = SessionStore(catalog.specs()).create(spec_name)
        failed = [r.message for r in session.set_many(answers) if not r.ok]
        assert not failed, failed
        return session
    return make


def errors(session):
    return [i.message for i in session.issues() if i.severity == "error"]
