"""Scoreboard benchmark: conditions A/B/C over the manifest sets (MOO-223).

  A. Solo        one qwen3.7-max prediction            (benchmark_wide + memorization)
  B. Silent jury nine persona votes, no communication  (benchmark_wide + memorization)
  C. Society     full deliberation                     (benchmark sample, via
                                                        episodes/{case_id}/events.jsonl
                                                        produced by deliberate.py)

A and B consume the identical raw case record. Resumable: per-case prediction
files under scoreboard/predictions/ are skipped when already complete.

Usage:
  python scripts/run_benchmark.py            # run A+B for all manifest cases
  python scripts/run_benchmark.py --aggregate  # only recompute results.json
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.llm import JUROR_MODEL, SENIOR_MODEL, chat_json, clamp01  # noqa: E402
from engine.personas import JURIST_IDS, load_personas, render_system  # noqa: E402

MANIFEST = REPO_ROOT / "data" / "benchmark_manifest.json"
CASES_DIR = REPO_ROOT / "data" / "cases"
PRED_DIR = REPO_ROOT / "scoreboard" / "predictions"
RESULTS = REPO_ROOT / "scoreboard" / "results.json"
EPISODES = REPO_ROOT / "episodes"


def case_presentation(case: dict) -> str:
    return (
        f"Case: {case['name']} (docket {case['docket']}, argued {case['date_argued']})\n"
        f"Question presented: {case['question_presented']}\n"
        f"Lower court ruling: {case['lower_court_ruling']}\n"
        f"Facts: {case['facts_summary']}\n"
    )


def condition_a(case: dict) -> dict | None:
    result = chat_json(
        SENIOR_MODEL,
        "You are an expert Supreme Court analyst. Predict the Court's decision.",
        case_presentation(case) +
        '\nDid/will the Court affirm or reverse the judgment below, and with what vote? '
        'Reply ONLY JSON: {"disposition": "affirm"|"reverse", "vote_split": "N-M"}',
        purpose=f"bench:A:{case['case_id']}",
    )
    if result and result.get("disposition") in ("affirm", "reverse"):
        return {"disposition": result["disposition"], "vote_split": result.get("vote_split", "unknown")}
    return None


def condition_b(case: dict, personas: dict) -> dict | None:
    def one_vote(jurist: str) -> str | None:
        result = chat_json(
            JUROR_MODEL,
            render_system(personas[jurist], round_no=1),
            case_presentation(case) +
            "\nCast your private vote per YOUR judicial philosophy. No deliberation occurs. "
            'Reply ONLY JSON: {"position": "affirm"|"reverse", "confidence": 0.0-1.0}',
            purpose=f"bench:B:{case['case_id']}:{jurist}",
        )
        pos = (result or {}).get("position")
        return pos if pos in ("affirm", "reverse") else None

    with ThreadPoolExecutor(max_workers=9) as pool:
        votes = {j: v for j, v in zip(JURIST_IDS, pool.map(one_vote, JURIST_IDS)) if v}
    if len(votes) < 7:  # too many malformed replies to call it a jury
        return None
    counts = {"affirm": 0, "reverse": 0}
    for v in votes.values():
        counts[v] += 1
    disposition = max(counts, key=counts.get)
    return {"disposition": disposition,
            "vote_split": f"{counts[disposition]}-{len(votes) - counts[disposition]}",
            "votes": votes}


def run_predictions() -> None:
    manifest = json.loads(MANIFEST.read_text())
    personas = load_personas()
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    targets = [(e["case_id"], set_name)
               for set_name in ("benchmark_wide", "memorization")
               for e in manifest.get(set_name, [])]
    print(f"{len(targets)} case-condition targets (A+B each)")

    for n, (case_id, set_name) in enumerate(targets, 1):
        pred_path = PRED_DIR / f"{case_id}.json"
        pred = json.loads(pred_path.read_text()) if pred_path.exists() else {"set": set_name}
        if pred.get("A") and pred.get("B"):
            continue
        case = json.loads((CASES_DIR / f"{case_id}.json").read_text())
        for cond, runner in (("A", lambda: condition_a(case)), ("B", lambda: condition_b(case, personas))):
            if pred.get(cond):
                continue
            try:
                pred[cond] = runner()
            except Exception as err:  # moderation blocks etc. — record and move on
                if "data_inspection_failed" in str(err):
                    pred[cond] = {"blocked": "data_inspection_failed"}
                    print(f"  ! {case_id} {cond}: content-moderation block, recorded as skip")
                else:
                    print(f"  ! {case_id} {cond}: {type(err).__name__}: {str(err)[:120]}")
        pred_path.write_text(json.dumps(pred, indent=2) + "\n")
        a, b = pred.get("A") or {}, pred.get("B") or {}
        print(f"[{n}/{len(targets)}] {case_id} A={a.get('disposition') or a.get('blocked')} "
              f"B={b.get('disposition') or b.get('blocked')}")


def _maj(split: str) -> int | None:
    try:
        return max(int(x) for x in split.split("-"))
    except (ValueError, AttributeError):
        return None


def aggregate() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    rows = {}

    def score(set_name: str, tier: str | None = None) -> None:
        entries = [e for e in manifest.get(set_name, []) if tier is None or e.get("tier") == tier]
        for cond in ("A", "B"):
            hits, splits, n = 0, [], 0
            for e in entries:
                pred_path = PRED_DIR / f"{e['case_id']}.json"
                if not pred_path.exists():
                    continue
                pred = (json.loads(pred_path.read_text()) or {}).get(cond)
                gt = json.loads((CASES_DIR / f"{e['case_id']}.json").read_text())["ground_truth"]
                if not (pred and pred.get("disposition") and gt):
                    continue  # missing, malformed, or moderation-blocked
                n += 1
                actual = "affirm" if gt["disposition"] == "affirmed" else "reverse"
                hits += pred["disposition"] == actual
                pm, am = _maj(pred.get("vote_split", "")), _maj(gt["vote_split"])
                if pm and am:
                    splits.append(abs(pm - am))
            label = f"{set_name}{f':{tier}' if tier else ''}:{cond}"
            rows[label] = {"n": n, "accuracy": round(hits / n, 3) if n else None,
                           "mean_split_distance": round(sum(splits) / len(splits), 2) if splits else None}

    score("benchmark_wide")
    score("memorization", tier="famous")
    score("memorization", tier="scdb")

    # Condition C from deliberation episodes (benchmark sample)
    hits, splits, n, flips, rounds = 0, [], 0, 0, []
    for e in manifest.get("benchmark", []):
        ev_path = EPISODES / e["case_id"] / "events.jsonl"
        if not ev_path.exists():
            continue
        events = [json.loads(l) for l in ev_path.read_text().splitlines()]
        verdict = next((x for x in events if x["type"] == "verdict"), None)
        gt = json.loads((CASES_DIR / f"{e['case_id']}.json").read_text())["ground_truth"]
        if not (verdict and gt):
            continue
        n += 1
        actual = "affirm" if gt["disposition"] == "affirmed" else "reverse"
        hits += verdict["position"] == actual
        pm, am = _maj(verdict["vote_split"]), _maj(gt["vote_split"])
        if pm and am:
            splits.append(abs(pm - am))
        flips += sum(1 for x in events if x["type"] == "vote_change")
        rounds.append(max(x.get("round", 0) for x in events))
    rows["benchmark:C"] = {
        "n": n, "accuracy": round(hits / n, 3) if n else None,
        "mean_split_distance": round(sum(splits) / len(splits), 2) if splits else None,
        "total_vote_changes": flips,
        "mean_rounds": round(sum(rounds) / len(rounds), 2) if rounds else None,
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps(rows, indent=2))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate", action="store_true", help="only recompute results.json")
    args = parser.parse_args()
    if not args.aggregate:
        run_predictions()
    aggregate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
