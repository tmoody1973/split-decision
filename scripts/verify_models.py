"""Day 1 gate, MOO-216: prove each reasoning model answers a real call.

Also validates the model IDs written into CLAUDE.md §2 against the live API.
Exit code 0 only if ALL models verify.

Usage: python scripts/verify_models.py
"""

import sys

from qwen_client import log_cost, make_client

MODELS = ["qwen3.7-plus", "qwen3.7-max", "qwen3.6-flash"]


def verify_model(client, model: str) -> dict:
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        max_tokens=16,
    )
    reply = (completion.choices[0].message.content or "").strip()
    cost = log_cost(completion.model, purpose=f"verify:{model}", usage=completion.usage)
    return {
        "requested": model,
        "echoed_model": completion.model,
        "response_id": completion.id,
        "reply": reply,
        "tokens": cost["total_tokens"],
    }


def main() -> int:
    try:
        client = make_client()
    except RuntimeError as err:
        print(f"BLOCKED: {err}")
        return 2

    failures = []
    for model in MODELS:
        try:
            result = verify_model(client, model)
            print(
                f"✓ {model}: id={result['response_id']} "
                f"echoed={result['echoed_model']} reply={result['reply']!r} "
                f"tokens={result['tokens']}"
            )
        except Exception as err:  # surface the API's own error text — it names valid IDs
            failures.append((model, str(err)))
            print(f"✗ {model}: {err}")

    if failures:
        print(
            f"\n{len(failures)}/{len(MODELS)} models FAILED. If an ID 404'd, correct "
            "CLAUDE.md §0/§2 with the live ID and note it on MOO-216."
        )
        return 1

    print(f"\nAll {len(MODELS)} models verified. Evidence above; usage in costs.jsonl.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
