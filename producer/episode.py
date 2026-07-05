"""Episode directory access: events, case record, personas, paths."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODES_DIR = REPO_ROOT / "episodes"
PERSONAS_DIR = REPO_ROOT / "personas"
CASES_DIR = REPO_ROOT / "data" / "cases"

GAP_MS = 300  # silence between utterances, everywhere (CLAUDE.md §9.4)

# Event types that carry speech, and the field holding it (both streams).
SPEECH_FIELDS = {"speak": "text", "vote_change": "reason_text", "foreperson": "text",
                 "studio": "text"}


@dataclass(frozen=True)
class Episode:
    case_id: str
    dir: Path
    events: list[dict]
    case: dict

    @property
    def events_path(self) -> Path:
        return self.dir / "events.jsonl"

    @property
    def studio_path(self) -> Path:
        return self.dir / "studio_events.jsonl"

    @property
    def clip_manifest_path(self) -> Path:
        return self.dir / "clip_manifest.json"

    @property
    def cue_sheet_path(self) -> Path:
        return self.dir / "cue_sheet.json"

    @property
    def mp3_path(self) -> Path:
        return self.dir / "episode.mp3"


def load_episode(case_id: str) -> Episode:
    ep_dir = EPISODES_DIR / case_id
    events_path = ep_dir / "events.jsonl"
    if not events_path.exists():
        raise FileNotFoundError(f"no events.jsonl for {case_id} in {ep_dir}")
    events = read_jsonl(events_path)
    case_path = CASES_DIR / f"{case_id}.json"
    case = json.loads(case_path.read_text()) if case_path.exists() else {}
    return Episode(case_id=case_id, dir=ep_dir, events=events, case=case)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def speech_text(event: dict) -> str | None:
    """Verbatim speech carried by a deliberation event, or None."""
    field = SPEECH_FIELDS.get(event.get("type", ""))
    text = event.get(field) if field else None
    return text if isinstance(text, str) and text.strip() else None


def duration_ms(path: Path) -> int:
    """Audio duration in ms via ffprobe (shared by TTS and RSS passes)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True,
                         check=True)
    return int(float(out.stdout.strip()) * 1000)


def voice_map() -> dict[str, str]:
    """persona id -> locked voice_id, from personas/*.yaml."""
    voices: dict[str, str] = {}
    for path in sorted(PERSONAS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if data.get("voice_id"):
            voices[data["id"]] = data["voice_id"]
    return voices
