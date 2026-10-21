import pytest

from voicecad.build import Finisher
from voicecad.offline import OfflineAssistant, pick_part


@pytest.fixture
def bot(catalog, tmp_path):
    return OfflineAssistant(catalog, Finisher(catalog, tmp_path)), tmp_path


def say(bot, *lines):
    turn = None
    for line in lines:
        turn = bot.chat("s", line)
    return turn


@pytest.mark.parametrize("text,part", [
    ("I need a phone stand", "phone_stand"),
    ("something to raise my laptop", "laptop_riser"),
    ("a case for my raspberry pi", "electronics_case"),
    ("a shelf bracket please", "bracket"),
    ("a small storage box", "box"),
])
def test_keywords_pick_the_part(text, part):
    assert pick_part(text) == part


def test_unknown_request_lists_the_parts(bot):
    b, _ = bot
    assert "phone stand" in b.chat("s", "make me a unicorn").reply


def test_phone_stand_conversation_ends_in_files(bot):
    b, out = bot
    first = b.chat("s", "I need a phone stand")
    assert "thick" in first.reply
    turn = say(b, "11 mm", "yes")
    assert "ready" in turn.reply and turn.parts
    assert (out / turn.parts[0]["file"]).exists()


def test_bad_number_is_explained_and_asked_again(bot):
    b, _ = bot
    b.chat("s", "a box")
    turn = b.chat("s", "banana")
    assert "How wide" in turn.reply


def test_rule_failure_clears_the_blamed_answers_and_the_user_can_recover(bot):
    b, _ = bot
    b.chat("s", "a box")
    b.chat("s", "300 mm")
    b.chat("s", "250 mm")
    turn = b.chat("s", "40 mm")   # 300 by 250 cannot fit the default bed
    assert "print bed" in turn.reply and "How wide" in turn.reply   # asks the size again, from the start
    done = say(b, "100 mm", "60 mm", "40 mm", "no")
    assert "ready" in done.reply


def test_sessions_do_not_leak_between_browser_tabs(bot):
    b, _ = bot
    b.chat("a", "a box")
    assert "which one" in b.chat("b", "hello").reply.lower()
