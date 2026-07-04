"""Shared LLM access for the engine: chat + JSON helpers, all calls cost-logged."""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from qwen_client import log_cost, make_client  # noqa: E402

JUROR_MODEL = "qwen3.7-plus"
SENIOR_MODEL = "qwen3.7-max"

_client = None


def client():
    global _client
    if _client is None:
        _client = make_client()
    return _client


def chat(model: str, system: str | None, user: str, purpose: str) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    completion = client().chat.completions.create(model=model, messages=messages)
    log_cost(model, purpose, completion.usage)
    return completion.choices[0].message.content or ""


def chat_json(model: str, system: str | None, user: str, purpose: str, tries: int = 3) -> dict | None:
    """chat() that must yield a JSON object; retries on malformed output."""
    for _ in range(tries):
        raw = chat(model, system, user, purpose)
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            continue
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
    return None


def clamp01(value, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default
