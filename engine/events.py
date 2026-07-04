"""Event log: append engine events (t=null), validate against the contract, write jsonl."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((REPO_ROOT / "contracts" / "events.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)


class EventLog:
    """Ordered deliberation event log. The engine never assigns timestamps —
    every event carries t=null; the Producer fills them after TTS."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def add(self, **payload) -> dict:
        event = {"t": None, **payload}
        errors = [e.message for e in VALIDATOR.iter_errors(event)]
        if errors:
            raise ValueError(f"invalid {payload.get('type')} event: {errors[0]}\n{event}")
        self.events.append(event)
        return event

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for event in self.events:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def of_type(self, event_type: str) -> list[dict]:
        return [e for e in self.events if e["type"] == event_type]
