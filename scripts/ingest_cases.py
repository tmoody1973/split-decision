"""Ingest the case corpus (MOO-219).

Three sets, one manifest:
  benchmark    25 decided post-2025-06-01 SCOTUS cases (contamination-guarded)
  memorization 50 historical SCDB cases (famous welcome; A/B conditions only)
  pending      argued-but-undecided cases from Oyez (the falsifiable bet)

Ground truth for recent cases is EXTRACTED from the official syllabus text by
qwen3.7-plus (extraction, not prediction — the syllabus states the outcome);
low-confidence extractions are excluded. Famous-name contamination filtering
uses qwen3.6-flash. Every record validates against contracts/case.schema.json.

Usage: python scripts/ingest_cases.py
"""

import csv
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import requests
from jsonschema import Draft202012Validator

from qwen_client import load_dotenv, log_cost, make_client

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "data" / "cases"
SCDB_DIR = REPO_ROOT / "data" / "scdb"
MANIFEST_PATH = REPO_ROOT / "data" / "benchmark_manifest.json"
SCHEMA = json.loads((REPO_ROOT / "contracts" / "case.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)

CL_BASE = "https://www.courtlistener.com/api/rest/v4"
SCDB_ZIP_URL = "http://scdb.wustl.edu/_brickFiles/2025_01/SCDB_2025_01_caseCentered_Citation.csv.zip"
CUTOFF = "2025-06-02"
BENCHMARK_N = 25
MEMORIZATION_SCDB_N = 25   # ordinary historical spread (tier: scdb)
MEMORIZATION_FAMOUS_N = 25  # landmark cases (tier: famous)
PENDING_MAX = 3
LANDMARKS_PATH = REPO_ROOT / "data" / "precedents" / "landmark_cases.json"

# SCDB caseDisposition codes -> our binary outcome
SCDB_DISPOSITION = {"2": "affirmed", "3": "reversed", "4": "reversed", "5": "reversed", "8": "reversed"}


def strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def first_words(text: str, n: int = 400) -> str:
    words = text.split()
    return " ".join(words[:n])


# ---------- CourtListener ----------

def cl_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = f"Token {token}"
    return s


def get_with_retry(s: requests.Session, url: str, params: dict | None, tries: int = 5) -> requests.Response:
    """Cluster pages are slow and CourtListener rate-limits; back off politely."""
    import time
    for attempt in range(1, tries + 1):
        try:
            r = s.get(url, params=params, timeout=180)
            if r.status_code == 429:
                wait = max(int(r.headers.get("Retry-After", 0) or 0), 30 * attempt)
                print(f"  429 rate-limited; sleeping {wait}s (attempt {attempt}/{tries})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as err:
            if attempt == tries:
                raise
            print(f"  retry {attempt}/{tries - 1} after {type(err).__name__}")
            time.sleep(10 * attempt)
    raise RuntimeError(f"gave up after {tries} attempts: {url}")


def fetch_clusters(s: requests.Session, want: int) -> list[dict]:
    """Newest decided SCOTUS clusters after the cutoff, with a syllabus.

    Pages are cached to data/cache/ so reruns never refetch or re-trip
    the rate limit.
    """
    import time
    cache_dir = REPO_ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out, url, page = [], f"{CL_BASE}/clusters/", 1
    params = {
        "docket__court": "scotus",
        "date_filed__gte": CUTOFF,
        "order_by": "-date_filed",
        "precedential_status": "Published",
        "page_size": 10,
    }
    while url and len(out) < want:
        cache_path = cache_dir / f"clusters_page_{page}.json"
        if cache_path.exists():
            body = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            body = get_with_retry(s, url, params).json()
            cache_path.write_text(json.dumps(body), encoding="utf-8")
            time.sleep(2)  # pacing between uncached pages
        for c in body["results"]:
            if c.get("sub_opinions"):  # recent clusters carry text only via opinions
                out.append(c)
        url, params, page = body.get("next"), None, page + 1
    return out


def cl_cached_json(s: requests.Session, url: str, cache_key: str) -> dict:
    """Fetch a CL resource with disk cache + pacing (rate-limit hygiene)."""
    import time
    cache_dir = REPO_ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{cache_key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    body = get_with_retry(s, url, None).json()
    path.write_text(json.dumps(body), encoding="utf-8")
    time.sleep(2)
    return body


def fetch_opinion_text(s: requests.Session, cluster: dict) -> str:
    """Lead opinion text — the slip opinion opens with the official syllabus."""
    url = cluster["sub_opinions"][0]
    op_id = url.rstrip("/").rsplit("/", 1)[-1]
    op = cl_cached_json(s, url, f"opinion_{op_id}")
    for field in ("plain_text", "html_with_citations", "html", "xml_harvard"):
        text = strip_html(op.get(field) or "")
        if len(text) > 500:
            return text
    return ""


def fetch_docket(s: requests.Session, cluster: dict) -> dict:
    return cl_cached_json(s, cluster["docket"], f"docket_{cluster['docket_id']}")


# ---------- Oyez ----------

def oyez_term(date_argued: str) -> str:
    year, month = int(date_argued[:4]), int(date_argued[5:7])
    return str(year if month >= 10 else year - 1)


def oyez_case(term: str, docket: str) -> dict | None:
    try:
        r = requests.get(f"https://api.oyez.org/cases/{term}/{docket}", timeout=30)
        if r.status_code != 200:
            return None
        body = r.json()
        return body if isinstance(body, dict) and body.get("name") else None
    except requests.RequestException:
        return None


def fetch_pending_from_oyez(term: str = "2025") -> list[dict]:
    """Cases argued in the term with no Decided timeline event."""
    r = requests.get(f"https://api.oyez.org/cases?filter=term:{term}&per_page=0", timeout=60)
    r.raise_for_status()
    pending = []
    for c in r.json():
        events = {e.get("event") for e in (c.get("timeline") or [])}
        if "Argued" in events and "Decided" not in events:
            pending.append(c)
    return pending


# ---------- LLM passes ----------

def famous_names(client, names: list[str]) -> set[str]:
    """Flash calls (chunked): which case names would a 1L recognize as landmarks?"""
    famous: set[str] = set()
    for start in range(0, len(names), 50):
        chunk = names[start : start + 50]
        numbered = "\n".join(f"{i}. {n}" for i, n in enumerate(chunk, 1))
        completion = client.chat.completions.create(
            model="qwen3.6-flash",
            messages=[{
                "role": "user",
                "content": (
                    "For each numbered US Supreme Court case below, answer whether a "
                    "first-year US law student would likely recognize the case name as "
                    "famous/landmark. Reply with ONLY a JSON array of the numbers that "
                    f"are famous, e.g. [2,7]. Cases:\n{numbered}"
                ),
            }],
        )
        log_cost("qwen3.6-flash", "ingest:famous_filter", completion.usage)
        match = re.search(r"\[[0-9,\s]*\]", completion.choices[0].message.content or "[]")
        indices = json.loads(match.group(0)) if match else []
        famous |= {chunk[i - 1] for i in indices if 1 <= i <= len(chunk)}
    return famous


def extract_ground_truth(client, name: str, syllabus: str, cache_key: str | None = None) -> dict | None:
    """Extract disposition + vote split from the official syllabus text.

    Results are disk-cached (they're deterministic extractions from fixed
    text) so reruns don't re-spend tokens.
    """
    cache_path = (REPO_ROOT / "data" / "cache" / f"gt_{cache_key}.json") if cache_key else None
    if cache_path and cache_path.exists():
        cached = json.loads(cache_path.read_text())
        return cached or None
    completion = client.chat.completions.create(
        model="qwen3.7-plus",
        messages=[{
            "role": "user",
            "content": (
                "Below is the official syllabus of a decided US Supreme Court case. "
                "Extract the outcome. Reply with ONLY JSON: "
                '{"disposition": "affirmed"|"reversed"|"mixed"|"unclear", '
                '"vote_split": "N-M"|"unknown"} '
                "(treat vacated/reversed-and-remanded as reversed; use mixed for "
                "affirmed-in-part; count the vote from the justice lineup if stated).\n\n"
                f"Case: {name}\nSyllabus: {syllabus[:6000]}"
            ),
        }],
    )
    log_cost("qwen3.7-plus", "ingest:ground_truth", completion.usage)
    match = re.search(r"\{.*\}", completion.choices[0].message.content or "", re.S)
    if not match:
        return None
    try:
        gt = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if gt.get("disposition") not in ("affirmed", "reversed"):
        gt = None
    # Disposition is the primary ground truth; a missing lineup is not a reason
    # to discard the case — the split-distance metric skips unknowns.
    elif not re.fullmatch(r"[0-9]-[0-9]", gt.get("vote_split", "")):
        gt["vote_split"] = "unknown"
    if cache_path:
        cache_path.write_text(json.dumps(gt))
    return gt


# ---------- SCDB historical ----------

def load_scdb_rows() -> list[dict]:
    SCDB_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = SCDB_DIR / "SCDB_2025_01_caseCentered_Citation.csv.zip"
    if not zip_path.exists():
        zip_path.write_bytes(requests.get(SCDB_ZIP_URL, timeout=300).content)
    with zipfile.ZipFile(zip_path) as z:
        raw = z.read(z.namelist()[0]).decode("latin-1")
    return list(csv.DictReader(io.StringIO(raw)))


def historical_records(rows: list[dict], n: int) -> list[dict]:
    clean = [
        r for r in rows
        if SCDB_DISPOSITION.get(r.get("caseDisposition", ""))
        and r.get("majVotes") and r.get("minVotes")
        and r.get("caseName") and r.get("dateDecision")
    ]
    clean.sort(key=lambda r: r["dateDecision"])
    step = max(1, len(clean) // n)
    picked = clean[::step][:n]
    records = []
    for r in picked:
        m, d, y = r["dateDecision"].split("/")  # SCDB uses M/D/YYYY
        decided = f"{y}-{int(m):02d}-{int(d):02d}"
        records.append({
            "case_id": f"scdb-{r['caseId']}",
            "name": r["caseName"],
            "docket": r.get("docket") or "n/a",
            "date_argued": decided,  # SCDB argument dates are spotty; decision date stands in
            "date_decided": decided,
            "question_presented": (
                f"Memorization-check set: predict the Supreme Court's disposition in "
                f"{r['caseName']} ({r.get('usCite') or 'US cite n/a'}, {r['term']} Term)."
            ),
            "facts_summary": (
                "Historical case in the memorization-check arm. By design, only the "
                "case name, citation, and term are provided — this arm measures "
                "recall of memorized outcomes, not reasoning."
            ),
            "lower_court_ruling": "not provided (memorization-check arm)",
            "opinion_excerpt_urls": [],
            "ground_truth": {
                "disposition": SCDB_DISPOSITION[r["caseDisposition"]],
                "vote_split": f"{r['majVotes']}-{r['minVotes']}",
                "scdb_id": r["caseId"],
            },
            "status": "decided",
        })
    return records


def extract_landmark_disposition(client, name: str, holding: str) -> str | None:
    """Map a landmark holding to affirmed/reversed; None if it doesn't fit."""
    completion = client.chat.completions.create(
        model="qwen3.7-plus",
        messages=[{
            "role": "user",
            "content": (
                "Did the US Supreme Court's decision below AFFIRM or REVERSE the "
                "judgment under review? Treat vacate/reverse-and-remand as reverse. "
                "If the case does not fit that frame (original jurisdiction, "
                "affirmed-in-part, no lower judgment), reply unclear. "
                'Reply with ONLY one word: affirmed, reversed, or unclear.\n\n'
                f"Case: {name}\nHolding: {holding[:2000]}"
            ),
        }],
    )
    log_cost("qwen3.7-plus", "ingest:landmark_disposition", completion.usage)
    word = (completion.choices[0].message.content or "").strip().lower()
    return word if word in ("affirmed", "reversed") else None


def famous_records(client, n: int) -> list[dict]:
    """Famous tier of the memorization set, from data/precedents/landmark_cases.json.

    Same minimal-information treatment as the SCDB tier (name + citation + term
    only), so fame is the only variable between tiers.
    """
    import datetime
    items = json.loads(LANDMARKS_PATH.read_text(encoding="utf-8"))
    records = []
    for item in items:
        if len(records) >= n:
            break
        vote = (item.get("vote") or "").strip()
        if not re.fullmatch(r"[0-9]-[0-9]", vote):
            continue
        try:
            decided = datetime.datetime.strptime(item["decided_date"], "%B %d, %Y").strftime("%Y-%m-%d")
        except (KeyError, ValueError):
            continue
        disposition = extract_landmark_disposition(client, item["case_name"], item.get("holding", ""))
        if not disposition:
            continue
        records.append({
            "case_id": f"landmark-{item['id']}",
            "name": item["case_name"],
            "docket": "n/a",
            "date_argued": decided,
            "date_decided": decided,
            "question_presented": (
                f"Memorization-check set: predict the Supreme Court's disposition in "
                f"{item['case_name']} ({item.get('citation', 'cite n/a')}, {item['year']})."
            ),
            "facts_summary": (
                "Historical case in the memorization-check arm (famous tier). By "
                "design, only the case name, citation, and year are provided — this "
                "arm measures recall of memorized outcomes, not reasoning."
            ),
            "lower_court_ruling": "not provided (memorization-check arm)",
            "opinion_excerpt_urls": [],
            "ground_truth": {"disposition": disposition, "vote_split": vote, "scdb_id": None},
            "status": "decided",
        })
    return records


# ---------- assembly ----------

def build_benchmark_record(cluster: dict, docket: dict, gt: dict, oyez: dict | None, syllabus: str) -> dict:
    facts = strip_html((oyez or {}).get("facts_of_the_case") or "") or syllabus
    question = strip_html((oyez or {}).get("question") or "")
    lower = ((oyez or {}).get("lower_court") or {}).get("name") if oyez else None
    return {
        "case_id": f"cl-cluster-{cluster['id']}",
        "name": cluster["case_name"],
        "docket": docket.get("docket_number") or "n/a",
        "date_argued": docket.get("date_argued") or cluster["date_filed"],
        "date_decided": cluster["date_filed"],
        "question_presented": question or first_words(syllabus, 120),
        "facts_summary": first_words(facts, 400),
        "lower_court_ruling": lower or "see syllabus",
        "opinion_excerpt_urls": [f"https://www.courtlistener.com{cluster['absolute_url']}"],
        "ground_truth": {
            "disposition": gt["disposition"],
            "vote_split": gt["vote_split"],
            "scdb_id": cluster.get("scdb_id") or None,
        },
        "status": "decided",
    }


def build_pending_record(oyez_list_item: dict) -> dict | None:
    detail = oyez_case(oyez_list_item["term"], oyez_list_item["docket_number"])
    if not detail:
        return None
    facts = strip_html(detail.get("facts_of_the_case") or "")
    question = strip_html(detail.get("question") or "")
    argued = next(
        (e["dates"][0] for e in (detail.get("timeline") or []) if e.get("event") == "Argued"),
        None,
    )
    if not (facts and question and argued):
        return None
    import datetime
    date_argued = datetime.datetime.fromtimestamp(argued, datetime.UTC).strftime("%Y-%m-%d")
    lower = (detail.get("lower_court") or {}).get("name")
    return {
        "case_id": f"oyez-{detail['ID']}",
        "name": detail["name"],
        "docket": detail["docket_number"],
        "date_argued": date_argued,
        "date_decided": None,
        "question_presented": question,
        "facts_summary": first_words(facts, 400),
        "lower_court_ruling": lower or "see docket",
        "opinion_excerpt_urls": [],
        "ground_truth": None,
        "status": "pending",
    }


def validate_and_write(record: dict) -> list[str]:
    errors = [e.message for e in VALIDATOR.iter_errors(record)]
    if not errors:
        CASES_DIR.mkdir(parents=True, exist_ok=True)
        (CASES_DIR / f"{record['case_id']}.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
    return errors


def main() -> int:
    load_dotenv()
    import os
    token = os.environ.get("COURTLISTENER_TOKEN")
    if not token:
        print("BLOCKED: COURTLISTENER_TOKEN not set")
        return 2
    client = make_client()
    s = cl_session(token)
    manifest = {
        "cutoff": CUTOFF, "created": "2026-07-04",
        "benchmark": [], "benchmark_wide": [], "memorization": [], "pending": [], "excluded": [],
    }

    # --- benchmark sets ---
    # benchmark      : 25-case deliberation sample (condition C), Oyez-enriched
    # benchmark_wide : ALL post-cutoff cases with clean ground truth (conditions A/B)
    print("Fetching decided clusters (full post-cutoff population)...")
    clusters = fetch_clusters(s, want=500)
    print(f"  {len(clusters)} candidates with opinions")
    famous = famous_names(client, [c["case_name"] for c in clusters])
    print(f"  famous-name exclusions: {sorted(famous) or 'none'}")

    seen_names: set[str] = set()
    for cluster in clusters:
        name = cluster["case_name"]
        # CL posts revised opinions as new clusters — dedupe on normalized name,
        # keeping the first (newest, since we iterate newest-first).
        norm = re.sub(r"\s*Revisions?:.*$", "", name).strip().casefold()
        if norm in seen_names:
            manifest["excluded"].append({"name": name, "reason": "duplicate cluster (revision)"})
            continue
        seen_names.add(norm)
        if name in famous:
            manifest["excluded"].append({"name": name, "reason": "famous-name contamination filter"})
            continue
        syllabus = fetch_opinion_text(s, cluster)
        if len(syllabus) < 500:
            manifest["excluded"].append({"name": name, "reason": "no usable opinion text"})
            continue
        gt = extract_ground_truth(client, name, syllabus, cache_key=str(cluster["id"]))
        if not gt:
            manifest["excluded"].append({"name": name, "reason": "ground truth not cleanly extractable (mixed/unclear)"})
            continue

        in_sample = len(manifest["benchmark"]) < BENCHMARK_N
        if in_sample:  # full enrichment for the deliberation sample
            docket = fetch_docket(s, cluster)
            oyez = None
            if docket.get("date_argued") and docket.get("docket_number"):
                oyez = oyez_case(oyez_term(docket["date_argued"]), docket["docket_number"])
        else:  # light path for the wide A/B population
            docket, oyez = {"docket_number": "n/a", "date_argued": cluster["date_filed"]}, None

        record = build_benchmark_record(cluster, docket, gt, oyez, syllabus)
        errors = validate_and_write(record)
        if errors:
            manifest["excluded"].append({"name": name, "reason": f"schema: {errors[0]}"})
            continue
        entry = {
            "case_id": record["case_id"], "name": name,
            "rationale": f"decided {record['date_decided']} (post-cutoff); ground truth extracted from syllabus ({gt['disposition']} {gt['vote_split']}); oyez={'yes' if oyez else 'no'}",
        }
        manifest["benchmark_wide"].append(entry)
        if in_sample:
            manifest["benchmark"].append(entry)
            print(f"  ✓ benchmark[C-sample]: {name} -> {gt['disposition']} {gt['vote_split']}")
    print(f"  wide A/B population: {len(manifest['benchmark_wide'])} cases")

    # --- memorization set (two tiers) ---
    print("\nBuilding memorization set — famous tier (landmarks)...")
    for record in famous_records(client, MEMORIZATION_FAMOUS_N):
        errors = validate_and_write(record)
        if errors:
            manifest["excluded"].append({"name": record["name"], "reason": f"schema: {errors[0]}"})
            continue
        manifest["memorization"].append({
            "case_id": record["case_id"], "name": record["name"], "tier": "famous",
            "rationale": "landmark case, maximally memorized; memorization-check arm (conditions A/B only)",
        })
    famous_count = len(manifest["memorization"])
    print(f"  {famous_count} famous-tier cases written")

    print("Building memorization set — SCDB spread tier...")
    for record in historical_records(load_scdb_rows(), MEMORIZATION_SCDB_N):
        errors = validate_and_write(record)
        if errors:
            manifest["excluded"].append({"name": record["name"], "reason": f"schema: {errors[0]}"})
            continue
        manifest["memorization"].append({
            "case_id": record["case_id"], "name": record["name"], "tier": "scdb",
            "rationale": "ordinary pre-cutoff SCDB case (era spread); memorization-check arm (conditions A/B only)",
        })
    print(f"  {len(manifest['memorization']) - famous_count} scdb-tier cases written")

    # --- pending set ---
    print("\nSearching Oyez for argued-but-undecided cases (term 2025)...")
    for item in fetch_pending_from_oyez("2025")[: PENDING_MAX * 3]:
        if len(manifest["pending"]) >= PENDING_MAX:
            break
        record = build_pending_record(item)
        if not record:
            continue
        errors = validate_and_write(record)
        if errors:
            continue
        manifest["pending"].append({
            "case_id": record["case_id"], "name": record["name"],
            "rationale": f"argued {record['date_argued']}, undecided as of ingestion; uncontaminatable by definition",
        })
        print(f"  ✓ pending: {record['name']} (argued {record['date_argued']})")

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"\nManifest: benchmark={len(manifest['benchmark'])} "
        f"wide={len(manifest['benchmark_wide'])} "
        f"memorization={len(manifest['memorization'])} pending={len(manifest['pending'])} "
        f"excluded={len(manifest['excluded'])}"
    )
    ok = (
        len(manifest["benchmark"]) >= 12
        and len(manifest["memorization"]) >= (MEMORIZATION_SCDB_N + MEMORIZATION_FAMOUS_N) * 0.8
        and len(manifest["pending"]) >= 1
    )
    print("RESULT:", "OK" if ok else "BELOW TARGETS — see manifest")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
