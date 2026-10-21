import json

from voicecad.agent import extract_parts

PART = {"part": "body", "file": "box-abc-body.stl", "size_mm": [100.0, 60.0, 40.0]}


def tool_message(item):
    return {"role": "user", "content": [{"toolResult": {"toolUseId": "t1", "status": "success", "content": [item]}}]}


def test_finds_parts_in_json_tool_results():
    assert extract_parts([tool_message({"json": {"ok": True, "parts": [PART]}})]) == [PART]


def test_finds_parts_in_text_tool_results():
    text = json.dumps({"ok": True, "parts": [PART]})
    assert extract_parts([tool_message({"text": text})]) == [PART]


def test_ignores_everything_else():
    messages = [
        {"role": "assistant", "content": [{"text": "hello"}]},
        tool_message({"text": "not json at all"}),
        tool_message({"json": {"ok": True, "next_question": {}}}),
        tool_message({"json": {"parts": [{"no_file_key": 1}]}}),
        "garbage",
    ]
    assert extract_parts(messages) == []


from voicecad.agent import FINISH_NUDGE, Assistant, needs_finish  # noqa: E402


def done(**extra):
    return tool_message({"json": {"ok": True, "complete": True, "issues": [], **extra}})


def test_needs_finish_when_complete_but_never_finished():
    assert needs_finish([done()])


def test_no_nudge_after_a_successful_finish():
    assert not needs_finish([done(), tool_message({"json": {"ok": True, "parts": [PART]}})])


def test_no_nudge_while_questions_are_open_or_a_rule_blocks():
    assert not needs_finish([tool_message({"json": {"ok": True, "complete": False, "issues": []}})])
    blocked = {"ok": True, "complete": True, "issues": [{"severity": "error"}]}
    assert not needs_finish([tool_message({"json": blocked})])


def test_a_new_intake_after_a_finished_one_is_tracked_separately():
    messages = [done(), tool_message({"json": {"ok": True, "parts": [PART]}}),
                tool_message({"json": {"ok": True, "complete": False, "issues": []}}), done()]
    assert needs_finish(messages)


class FakeAgent:
    """Stands in for a Strands agent. The first call skips finish, the second one does it."""

    def __init__(self):
        self.messages = []
        self.prompts = []

    def __call__(self, text):
        self.prompts.append(text)
        self.messages.append(done())
        if text == FINISH_NUDGE:
            self.messages.append(tool_message({"json": {"ok": True, "parts": [PART]}}))
        return "Your box is ready."


def test_assistant_asks_the_model_to_finish_when_it_skips_finish():
    assistant = Assistant("http://unused")
    assistant._ensure_ready = lambda: None   # no MCP connection in this test
    fake = FakeAgent()
    assistant._agents["s"] = fake
    turn = assistant.chat("s", "no lid")
    assert fake.prompts == ["no lid", FINISH_NUDGE]
    assert turn.parts == [PART]
