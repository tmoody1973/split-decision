"""Assembly pass: cue sheet -> episode.mp3 (ffmpeg), music bed under studio segments.

Speech track: every cue-sheet mp3 placed at its `t` with adelay (gaps come from
the cue sheet itself). Bed: assets/music/bed.mp3 looped under the episode at a
low base level, ducked a further 14dB whenever anchor speech is active
(deterministic volume-enable ranges derived from the cue sheet — provable,
no sidechain tuning). Bed license: assets/music/LICENSE.md.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from producer.episode import Episode  # noqa: E402

BED_PATH = REPO_ROOT / "assets" / "music" / "bed.mp3"
BED_BASE_DB = -20.0   # bed level in the gaps between segments
DUCK_DB = -14.0       # additional reduction while studio speech is active
TAIL_MS = 1500


def _studio_ranges(cues: list[dict]) -> list[tuple[int, int]]:
    """Merge adjacent studio cue rows into (start_ms, end_ms) speech ranges."""
    ranges: list[tuple[int, int]] = []
    for cue in cues:
        if cue["stream"] != "studio":
            continue
        start, end = cue["t"], cue["t"] + cue["dur_ms"]
        if ranges and start - ranges[-1][1] <= 600:
            ranges[-1] = (ranges[-1][0], end)
        else:
            ranges.append((start, end))
    return ranges


def assemble(ep: Episode) -> Path:
    cues = json.loads(ep.cue_sheet_path.read_text())
    if not cues:
        raise RuntimeError("empty cue sheet")
    total_ms = cues[-1]["t"] + cues[-1]["dur_ms"] + TAIL_MS

    inputs, delays = [], []
    for n, cue in enumerate(cues):
        inputs += ["-i", str(ep.dir / cue["audio_file"])]
        delays.append(f"[{n}:a]adelay={cue['t']}|{cue['t']}[d{n}]")
    speech_mix = "".join(f"[d{n}]" for n in range(len(cues)))
    filters = delays + [
        f"{speech_mix}amix=inputs={len(cues)}:normalize=0[speech]",
    ]

    if BED_PATH.exists():
        bed_idx = len(cues)
        inputs += ["-stream_loop", "-1", "-i", str(BED_PATH)]
        duck = "+".join(f"between(t,{s / 1000:.3f},{e / 1000:.3f})"
                        for s, e in _studio_ranges(cues)) or "0"
        filters += [
            f"[{bed_idx}:a]atrim=0:{total_ms / 1000:.3f},"
            f"volume={BED_BASE_DB}dB,"
            f"volume=volume={DUCK_DB}dB:enable='{duck}',"
            f"afade=t=out:st={(total_ms - TAIL_MS) / 1000:.3f}:d={TAIL_MS / 1000:.1f}[bed]",
            "[speech][bed]amix=inputs=2:normalize=0:duration=first[mix]",
        ]
        out_label = "[mix]"
    else:
        print("  ! no music bed at assets/music/bed.mp3 — speech only")
        out_label = "[speech]"

    filters += [f"{out_label}loudnorm=I=-16:TP=-1.5:LRA=11[out]"]
    cmd = (["ffmpeg", "-y", "-loglevel", "error"] + inputs +
           ["-filter_complex", ";".join(filters), "-map", "[out]",
            "-codec:a", "libmp3lame", "-b:a", "128k", "-ar", "44100",
            "-t", f"{total_ms / 1000:.3f}", str(ep.mp3_path)])
    subprocess.run(cmd, check=True)
    print(f"assembled {ep.mp3_path} ({total_ms / 60000:.1f} min)")
    return ep.mp3_path
