"""Qwen Cloud client factory + per-call cost logging.

Every module that talks to Qwen Cloud goes through make_client() and logs
usage via log_cost() — costs.jsonl is the audit trail (CLAUDE.md §0.5).
"""

import json
import os
import time
from pathlib import Path

from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[1]
COSTS_PATH = REPO_ROOT / "costs.jsonl"
DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Minimal .env loader. Existing environment variables win over file values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() and value.strip():
            os.environ.setdefault(key.strip(), value.strip())


def make_client() -> OpenAI:
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is not set. Create a key at home.qwencloud.com/api-keys, "
            "then `cp .env.example .env` and paste it in."
        )
    if api_key.startswith("sk-sp-"):
        raise RuntimeError(
            "Token Plan key (sk-sp-*) detected — it 401s against the pay-as-you-go "
            "endpoint. Use a standard sk-* key (docs/Qwen Cloud Proof of Deployment.md)."
        )
    base_url = os.environ.get("DASHSCOPE_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=api_key, base_url=base_url)


def log_cost(model: str, purpose: str, usage) -> dict:
    """Append one usage record to costs.jsonl and return a copy of it."""
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model": model,
        "purpose": purpose,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }
    with COSTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record
