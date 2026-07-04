"""Persona registry: load YAMLs, render round-scoped system prompts.

The persona system prompt is re-injected EVERY round with fresh
{round}/{memory_digest}/{position}/{confidence} values — drift resistance.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_DIR = REPO_ROOT / "personas"

JURIST_IDS = [
    "textualist",
    "originalist",
    "living_constitutionalist",
    "pragmatist",
    "precedent_maximalist",
    "federalism_hawk",
    "civil_libertarian",
    "process_formalist",
    "minimalist",
]


def load_personas() -> dict[str, dict]:
    personas = {}
    for path in PERSONAS_DIR.glob("*.yaml"):
        p = yaml.safe_load(path.read_text(encoding="utf-8"))
        personas[p["id"]] = p
    missing = [j for j in JURIST_IDS + ["foreperson"] if j not in personas]
    if missing:
        raise RuntimeError(f"persona YAMLs missing: {missing}")
    return personas


def render_system(persona: dict, round_no: int, digest: str = "",
                  position: str = "undecided", confidence: float = 0.5) -> str:
    template = persona["system_prompt"]
    return (
        template.replace("{round}", str(round_no))
        .replace("{memory_digest}", digest or "(first round — no prior memory)")
        .replace("{position}", position)
        .replace("{confidence}", f"{confidence:.2f}")
    )
