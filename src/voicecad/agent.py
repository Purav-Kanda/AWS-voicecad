"""The assistant's brain: a Strands agent on Amazon Bedrock that drives the voicecad MCP tools."""
from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

from .instructions import INSTRUCTIONS

PERSONA = (
    "You are a friendly voice assistant on a smart speaker, helping someone design a 3D-printable part. "
    "Everything you write is spoken aloud, so use short plain sentences, no lists, no markdown, no emojis. "
    "Ask one question at a time. "
) + INSTRUCTIONS


FINISH_NUDGE = (
    "Reminder from the system: every question is answered, but finish has not succeeded yet. "
    "Call finish now, then tell the user the summary and notes."
)


@dataclass
class Turn:
    reply: str
    parts: list[dict[str, Any]] = field(default_factory=list)


def make_model() -> BedrockModel:
    """Bedrock model. The library default is used unless VOICECAD_MODEL_ID is set."""
    options: dict[str, Any] = {}
    if os.environ.get("VOICECAD_MODEL_ID"):
        options["model_id"] = os.environ["VOICECAD_MODEL_ID"]
    return BedrockModel(region_name=os.environ.get("AWS_REGION") or None, **options)


def tool_payloads(messages: list[Any]) -> Iterator[dict[str, Any]]:
    """Every JSON object a tool returned during an agent turn, in order."""
    for message in messages:
        blocks = message.get("content", []) if isinstance(message, dict) else []
        for block in blocks:
            result = block.get("toolResult") if isinstance(block, dict) else None
            if not result:
                continue
            for item in result.get("content", []):
                data = item.get("json")
                if data is None and isinstance(item.get("text"), str):
                    try:
                        data = json.loads(item["text"])
                    except ValueError:
                        continue
                if isinstance(data, dict):
                    yield data


def extract_parts(messages: list[Any]) -> list[dict[str, Any]]:
    """Find generated files in the tool results of an agent turn."""
    found: list[dict[str, Any]] = []
    for data in tool_payloads(messages):
        if isinstance(data.get("parts"), list):
            found.extend(p for p in data["parts"] if isinstance(p, dict) and "file" in p)
    return found


def needs_finish(messages: list[Any]) -> bool:
    """True when every question is answered and no rule blocks it, but finish never succeeded.

    This is the case where a model says "your part is ready" without making the file.
    """
    ready = False
    for data in tool_payloads(messages):
        if "complete" in data:   # a progress report from start_intake, submit_answers or review
            blocked = any(i.get("severity") == "error" for i in data.get("issues", []) if isinstance(i, dict))
            ready = bool(data["complete"]) and not blocked
        elif data.get("ok") is True and isinstance(data.get("parts"), list):   # finish succeeded
            ready = False
    return ready


class Assistant:
    """One shared MCP connection, one conversation (Agent) per browser session."""

    def __init__(self, mcp_url: str) -> None:
        self._client = MCPClient(url=mcp_url)
        self._model: BedrockModel | None = None
        self._tools: list[Any] = []
        self._agents: dict[str, Agent] = {}
        self._lock = threading.Lock()
        self._ready = False

    def _ensure_ready(self) -> None:
        with self._lock:
            if self._ready:
                return
            self._client.start()
            self._tools = self._client.list_tools_sync()
            self._model = make_model()
            self._ready = True

    def chat(self, session_id: str, text: str) -> Turn:
        self._ensure_ready()
        with self._lock:
            agent = self._agents.get(session_id)
            if agent is None:
                agent = Agent(model=self._model, tools=self._tools, system_prompt=PERSONA, callback_handler=None)
                self._agents[session_id] = agent
        seen = len(agent.messages)
        outcome = agent(text)
        if needs_finish(agent.messages[seen:]):
            # The model announced a result without calling finish. Ask once, so no file is ever promised and missing.
            outcome = agent(FINISH_NUDGE)
        return Turn(reply=str(outcome).strip(), parts=extract_parts(agent.messages[seen:]))
