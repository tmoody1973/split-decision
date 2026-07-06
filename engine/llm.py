"""Shared LLM access for the engine: chat + JSON helpers, all calls cost-logged.

Transient failures (429 / 5xx / timeouts / connection drops) retry with
exponential backoff so one mid-round blip can't kill an episode. 4xx errors —
including content-moderation blocks (data_inspection_failed) — are NEVER
retried: retrying a moderation block just re-submits the same blocked content.
"""

import json
import re
import sys
import time
from pathlib import Path

from openai import (APIConnectionError, APITimeoutError, BadRequestError,
                    InternalServerError, RateLimitError)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from qwen_client import log_cost, make_client  # noqa: E402

JUROR_MODEL = "qwen3.7-plus"
SENIOR_MODEL = "qwen3.7-max"

TRANSIENT_ERRORS = (RateLimitError, InternalServerError, APITimeoutError, APIConnectionError)
MAX_ATTEMPTS = 3

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
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            completion = client().chat.completions.create(model=model, messages=messages)
            break
        except BadRequestError as err:
            if "data_inspection_failed" in str(err).lower():
                raise RuntimeError(
                    f"content-moderation block (data_inspection_failed) on {purpose} — "
                    "not retryable; rephrase the prompt (describe the scene, not the crime)"
                ) from err
            raise
        except TRANSIENT_ERRORS as err:
            if attempt == MAX_ATTEMPTS:
                raise
            wait = 2 ** attempt
            print(f"[llm] {type(err).__name__} on {purpose} — retry {attempt}/{MAX_ATTEMPTS - 1} in {wait}s")
            time.sleep(wait)
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
