"""Create one Voice Design voice per persona and lock the ids (MOO-217).

Idempotent: personas whose YAML already has a non-null voice_id are skipped,
so reruns never burn creation quota (10 free, then $0.20 each).

For each persona missing a voice_id:
  qwen-voice-design create(voice_prompt) -> voice id + preview WAV
  -> preview saved to assets/voice_previews/{id}.wav
  -> voice_id written back to personas/{id}.yaml

Usage: python scripts/create_voices.py
"""

import base64
import os
import sys
from pathlib import Path

import requests
import yaml

from qwen_client import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_DIR = REPO_ROOT / "personas"
PREVIEWS_DIR = REPO_ROOT / "assets" / "voice_previews"
CUSTOMIZATION_URL = (
    "https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization"
)
TARGET_MODEL = "qwen3-tts-vd-2026-01-26"


def create_voice(api_key: str, persona: dict) -> tuple[str, bytes]:
    """Call Voice Design; return (voice_id, preview_wav_bytes)."""
    resp = requests.post(
        CUSTOMIZATION_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "qwen-voice-design",
            "input": {
                "action": "create",
                "target_model": TARGET_MODEL,
                "preferred_name": persona["id"].replace("_", "")[:16],
                "voice_prompt": persona["voice_design_prompt"].strip(),
                "preview_text": persona["preview_text"].strip(),
            },
        },
        timeout=300,
    )
    body = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"{body.get('code')}: {body.get('message')}")
    output = body["output"]
    return output["voice"], base64.b64decode(output["preview_audio"]["data"])


def main() -> int:
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("BLOCKED: DASHSCOPE_API_KEY is not set (see .env.example).")
        return 2

    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    yaml_paths = sorted(PERSONAS_DIR.glob("*.yaml"))
    if not yaml_paths:
        print(f"BLOCKED: no persona YAMLs found in {PERSONAS_DIR}")
        return 2

    created, skipped, failed = [], [], []
    for path in yaml_paths:
        persona = yaml.safe_load(path.read_text(encoding="utf-8"))
        if persona.get("voice_id"):
            skipped.append(persona["id"])
            continue
        try:
            voice_id, preview = create_voice(api_key, persona)
        except (RuntimeError, requests.RequestException, KeyError) as err:
            failed.append((persona["id"], str(err)))
            print(f"✗ {persona['id']}: {err}")
            continue

        preview_path = PREVIEWS_DIR / f"{persona['id']}.wav"
        preview_path.write_bytes(preview)

        # Surgical write-back: replace only the voice_id line, keep formatting.
        text = path.read_text(encoding="utf-8")
        text = text.replace("voice_id: null", f"voice_id: {voice_id}", 1)
        path.write_text(text, encoding="utf-8")

        created.append(persona["id"])
        print(f"✓ {persona['id']}: {voice_id} ({len(preview)} bytes preview)")

    print(
        f"\ncreated={len(created)} skipped={len(skipped)} failed={len(failed)} "
        f"(skipped: {', '.join(skipped) or 'none'})"
    )
    if failed:
        return 1
    print(f"Previews in {PREVIEWS_DIR} — LISTEN to all of them before proceeding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
