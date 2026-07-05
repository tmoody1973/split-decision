"""Render the demo video narration with ElevenLabs (MOO-227).

Extracts the `> VO-n:` blockquote blocks from docs/video/demo-script.md (the
single source of truth for the script) and synthesizes one MP3 per cue into
video/vo/vo_n.mp3, printing durations for the Hyperframes timeline.

Usage: .venv/bin/python scripts/make_demo_vo.py [--voice VOICE_ID]
Env:   ELEVENLABS_API_KEY (required), ELEVENLABS_VOICE_ID (optional)
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from qwen_client import load_dotenv  # noqa: E402

SCRIPT_DOC = REPO_ROOT / "docs" / "video" / "demo-script.md"
OUT_DIR = REPO_ROOT / "video" / "vo"
DEFAULT_VOICE = "onwK4e9ZLuTAKqWW03F9"  # ElevenLabs "Daniel" — deep documentary read
MODEL = "eleven_multilingual_v2"


def extract_cues(md: str) -> list[tuple[int, str]]:
    """Pull `> VO-n: ...` blockquotes (possibly spanning multiple `> ` lines)."""
    cues: list[tuple[int, str]] = []
    for match in re.finditer(r"^> VO-(\d+):((?:.*\n)(?:^>.*\n)*)", md, re.M):
        n = int(match.group(1))
        text = " ".join(
            line.lstrip("> ").strip() for line in match.group(2).splitlines()
        ).strip()
        cues.append((n, text))
    return sorted(cues)


def synthesize(text: str, voice: str, api_key: str, out: Path) -> float:
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.35},
        },
        timeout=120,
    )
    resp.raise_for_status()
    out.write_bytes(resp.content)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    )
    return float(probe.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", default=os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE))
    args = parser.parse_args()

    load_dotenv()
    load_dotenv(Path.home() / ".claude" / ".env")
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY not set")

    cues = extract_cues(SCRIPT_DOC.read_text())
    if not cues:
        raise SystemExit("no VO-n blocks found in the script doc")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total = 0.0
    for n, text in cues:
        out = OUT_DIR / f"vo_{n}.mp3"
        dur = synthesize(text, args.voice, api_key, out)
        total += dur
        print(f"  VO-{n}: {dur:5.1f}s  {out.relative_to(REPO_ROOT)}  ({len(text.split())} words)")
    print(f"\ntotal narration: {total:.1f}s across {len(cues)} cues (voice {args.voice})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
