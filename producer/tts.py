"""TTS pass: every utterance -> mp3 in the episode dir, durations recorded.

Endpoint verified live 2026-07-04 (docs/handoffs/producer-handoff.md): the
Voice Design synthesis model on the intl multimodal route. The returned WAV URL
expires in ~24h, so each utterance is downloaded and converted to mp3 in the
same call. Deliberation events -> utt_{index:03d}.mp3, studio -> studio_{index:03d}.mp3.
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

from qwen_client import COSTS_PATH, load_dotenv  # noqa: E402
from producer.episode import (Episode, duration_ms, read_jsonl, speech_text,  # noqa: E402
                              voice_map, write_jsonl)

TTS_MODEL = "qwen3-tts-vd-2026-01-26"
TTS_URL = "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
WORKERS = 4


def log_tts_cost(purpose: str, chars: int) -> None:
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model": TTS_MODEL,
              "purpose": purpose, "tts_chars": chars}
    with COSTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def synthesize(text: str, voice: str, out_mp3: Path, purpose: str, tries: int = 3) -> int:
    """TTS one utterance to mp3; return duration in ms. Skips if mp3 exists."""
    if out_mp3.exists() and out_mp3.stat().st_size > 0:
        return duration_ms(out_mp3)
    load_dotenv()
    last_err: Exception | None = None
    for attempt in range(tries):
        try:
            resp = requests.post(
                TTS_URL,
                headers={"Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}",
                         "Content-Type": "application/json"},
                json={"model": TTS_MODEL, "input": {"text": text, "voice": voice}},
                timeout=120,
            )
            resp.raise_for_status()
            audio_url = resp.json()["output"]["audio"]["url"]
            wav = requests.get(audio_url, timeout=120)
            wav.raise_for_status()
            tmp = out_mp3.with_suffix(".wav")
            tmp.write_bytes(wav.content)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                            "-codec:a", "libmp3lame", "-qscale:a", "4", "-ar", "44100",
                            str(out_mp3)], check=True)
            tmp.unlink()
            log_tts_cost(purpose, len(text))
            return duration_ms(out_mp3)
        except Exception as err:  # noqa: BLE001 — moderation/network both land here
            last_err = err
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"TTS failed for {out_mp3.name}: {last_err}")


def _tts_events(events: list[dict], prefix: str, ep_dir: Path,
                voices: dict[str, str], purpose: str) -> int:
    """Synthesize every speech-bearing event; fill audio_file + dur_ms in the
    list (new dicts, index-stable). Returns count of speech events."""
    jobs = []
    for i, ev in enumerate(events):
        text = speech_text(ev)
        if not text:
            continue
        # foreperson events carry action/agents, not agent (contract §4)
        agent = ev.get("agent") or ("foreperson" if ev.get("type") == "foreperson" else None)
        voice = voices.get(agent or "")
        if not voice:
            raise RuntimeError(f"no voice_id for agent {agent!r} (event {i})")
        # keep an existing assignment: index-based names go stale if the event
        # list is ever edited (e.g. trimming the studio script for length)
        name = ev.get("audio_file") or f"{prefix}_{i:03d}.mp3"
        jobs.append((i, text, voice, ep_dir / name))

    def run(job: tuple[int, str, str, Path]) -> tuple[int, str, int]:
        i, text, voice, out = job
        dur = synthesize(text, voice, out, purpose)
        return i, out.name, dur

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, name, dur in pool.map(run, jobs):
            events[i] = {**events[i], "audio_file": name, "dur_ms": dur}
            print(f"  {name} {dur}ms")
    return len(jobs)


def tts_episode(ep: Episode) -> tuple[list[dict], list[dict]]:
    """TTS both streams; rewrite events.jsonl and studio_events.jsonl with
    audio_file + dur_ms filled. Idempotent: existing mp3s are reused."""
    voices = voice_map()
    events = read_jsonl(ep.events_path)
    n = _tts_events(events, "utt", ep.dir, voices, "producer:tts:deliberation")
    write_jsonl(ep.events_path, events)
    print(f"deliberation: {n} utterances")

    studio = read_jsonl(ep.studio_path)
    n = _tts_events(studio, "studio", ep.dir, voices, "producer:tts:studio")
    write_jsonl(ep.studio_path, studio)
    print(f"studio: {n} utterances")
    return events, studio
