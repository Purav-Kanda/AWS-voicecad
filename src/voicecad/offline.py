"""A no-model stand-in for the Bedrock assistant, so the demo page works without AWS.

It is a plain script, not a language model. It matches a few keywords to pick a part, then
treats every reply as the answer to the question it just asked. It exists so that a judge or a
new user can try the intake flow, the rules and the file output with no credentials.
"""
from __future__ import annotations

import re
import threading

from guided_intake import Session, SessionStore

from .agent import Turn
from .build import Finisher
from .catalog import Catalog

UPLOAD_ID = re.compile(r"\bid (?:is )?([0-9a-f]{12})\b")
KEYWORDS = {
    "custom_model": ("uploaded",),
    "electronics_case": ("raspberry", "pi ", "case", "enclosure", "arduino"),
    "phone_stand": ("phone", "stand", "dock"),
    "laptop_riser": ("laptop", "riser", "notebook"),
    "bracket": ("bracket", "shelf"),
    "box": ("box", "tray", "container", "storage"),
}


def pick_part(text: str) -> str | None:
    lowered = f"{text.lower()} "
    for name, words in KEYWORDS.items():
        if any(w in lowered for w in words):
            return name
    return None


class OfflineAssistant:
    def __init__(self, catalog: Catalog, finisher: Finisher) -> None:
        self._catalog = catalog
        self._finisher = finisher
        self._store = SessionStore(catalog.specs())
        self._active: dict[str, Session] = {}
        self._lock = threading.Lock()

    def chat(self, session_id: str, text: str) -> Turn:
        with self._lock:
            session = self._active.get(session_id)
            if session is None:
                return self._start(session_id, text)
            return self._answer(session_id, session, text)

    def _start(self, session_id: str, text: str) -> Turn:
        name = pick_part(text)
        if name is None:
            titles = ", ".join(s.title.lower() for s in self._catalog.specs())
            return Turn(f"I can make these: {titles}. Which one do you want?")
        session = self._store.create(name)
        self._active[session_id] = session
        found = UPLOAD_ID.search(text)
        if name == "custom_model" and found:
            session.set_value("upload_id", found.group(1))   # the page put the id in its message
        first = session.next_field()
        assert first is not None
        return Turn(f"Sure, a {session.spec.title.lower()}. {first.question}")

    def _answer(self, session_id: str, session: Session, text: str) -> Turn:
        field = session.next_field()
        if field is None:   # defensive: a complete session is finished the same turn, so this should not happen
            return self._finish(session_id, session)
        result = session.set_value(field.name, text)
        if not result.ok:
            return Turn(f"{result.message}. {field.question}")

        errors = [i for i in session.issues() if i.severity == "error"]
        if errors:
            # Forget the answers the rule blames, so the user can change them. If it names none that
            # are stored, fall back to the answer just given.
            blamed = [n for n in errors[0].fields if session.clear(n)]
            if not blamed:
                session.clear(field.name)
            fix = f" {errors[0].suggestion}" if errors[0].suggestion else ""
            again = session.next_field()
            question = again.question if again else field.question
            return Turn(f"{errors[0].message}{fix} {question}")

        following = session.next_field()
        if following is not None:
            return Turn(following.question)
        return self._finish(session_id, session)

    def _finish(self, session_id: str, session: Session) -> Turn:
        result = self._finisher(session)
        del self._active[session_id]
        if result.get("ok") is False:
            return Turn(result["error"])
        notes = " ".join(result["notes"])
        return Turn(f"{result['summary']} {notes}".strip(), parts=result["parts"])
