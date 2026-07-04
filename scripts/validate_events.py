"""Validate a .jsonl event stream against contracts/events.schema.json.

The engine and producer call this before writing an episode dir; CI and
humans run it directly.

Usage: python scripts/validate_events.py <path/to/events.jsonl> [...]
Exit 0 only if every line of every file validates.
"""

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "contracts" / "events.schema.json"


def validate_file(validator: Draft202012Validator, path: Path) -> int:
    """Validate one .jsonl file; print per-line errors; return error count."""
    errors = 0
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as err:
            print(f"✗ {path}:{lineno} not valid JSON: {err}")
            errors += 1
            continue
        line_errors = sorted(validator.iter_errors(event), key=lambda e: e.json_path)
        for err in line_errors[:1]:  # oneOf mismatches cascade; first error suffices
            print(f"✗ {path}:{lineno} ({event.get('type', '?')}): {err.message}")
        errors += len(line_errors[:1])
    if errors == 0:
        print(f"✓ {path}: all lines valid")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    total = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"✗ {path}: no such file")
            total += 1
            continue
        total += validate_file(validator, path)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
