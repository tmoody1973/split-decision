"""The deliberation chamber: CLAUDE.md §7 state machine.

INIT → BRIEFING → [ROUND]* → VERDICT → (REVEAL if decided)
ROUND: PRIVATE_VOTE → STATEMENTS → PAIR_DEBATE → REVOTE → CHECK

Anti-sycophancy machinery lives here and in the persona prompts:
- private scratchpad votes BEFORE public statements each round
- persona system prompt re-injected every round (personas.render_system)
- per-persona flip triggers (in each YAML system_prompt)
- foreperson structurally barred from merits positions (prompt + audit string)
- per-juror memory digest written from its own perspective
"""

from concurrent.futures import ThreadPoolExecutor

from engine.clerk import bench_memo
from engine.events import EventLog
from engine.llm import JUROR_MODEL, SENIOR_MODEL, chat, chat_json, clamp01
from engine.personas import JURIST_IDS, load_personas, render_system

MAX_ROUNDS = 5
SUPERMAJORITY = 7
STATEMENT_WORDS = 110
REBUTTAL_WORDS = 60


class Chamber:
    def __init__(self, case: dict) -> None:
        self.case = case
        self.personas = load_personas()
        self.log = EventLog()
        self.memo = ""
        self.digests: dict[str, str] = {j: "" for j in JURIST_IDS}
        self.positions: dict[str, dict] = {j: {"position": "undecided", "confidence": 0.5} for j in JURIST_IDS}

    # ---------- helpers ----------

    def _sys(self, jurist: str, round_no: int) -> str:
        p = self.positions[jurist]
        return render_system(self.personas[jurist], round_no, self.digests[jurist],
                             p["position"], p["confidence"])

    def _purpose(self, phase: str) -> str:
        return f"deliberate:{self.case['case_id']}:{phase}"

    # ---------- phases ----------

    def private_vote(self, jurist: str, round_no: int, revote: bool) -> dict:
        extra = (
            ' ,"changed": true|false, "influenced_by": ["jurist_id", ...], '
            '"reason": "1-2 sentences in character naming the SPECIFIC argument that moved you '
            '(empty string if unchanged)"'
            if revote else ""
        )
        user = (
            f"BENCH MEMO:\n{self.memo}\n\n"
            f"Private scratchpad vote ({'after' if revote else 'before'} round {round_no} debate). "
            "No other jurist will ever see this. Apply YOUR philosophy and its flip trigger honestly "
            "— do not move toward the majority for its own sake, and do not resist a flip your own "
            "trigger condition demands.\n"
            'Reply ONLY JSON: {"position": "affirm"|"reverse", "confidence": 0.0-1.0' + extra + "}"
        )
        result = chat_json(JUROR_MODEL, self._sys(jurist, round_no), user,
                           self._purpose(f"r{round_no}:{'revote' if revote else 'vote'}:{jurist}"))
        if not result or result.get("position") not in ("affirm", "reverse"):
            result = {"position": self.positions[jurist]["position"], "confidence": 0.5}
            if result["position"] == "undecided":
                result["position"] = "affirm"
        result["confidence"] = clamp01(result.get("confidence"))
        return result

    def all_private_votes(self, round_no: int, revote: bool) -> dict[str, dict]:
        with ThreadPoolExecutor(max_workers=9) as pool:
            futures = {j: pool.submit(self.private_vote, j, round_no, revote) for j in JURIST_IDS}
            return {j: f.result() for j, f in futures.items()}

    def speaking_order(self, round_no: int) -> list[str]:
        stances = {j: self.positions[j]["position"] for j in JURIST_IDS}
        result = chat_json(
            SENIOR_MODEL,
            render_system(self.personas["foreperson"], round_no),
            "Choose the speaking order for this round so that clashing philosophies and stances "
            f"alternate where possible. Jurists and last public stances: {stances}. "
            f'Reply ONLY JSON: {{"order": [all nine jurist ids exactly once]}}',
            self._purpose(f"r{round_no}:order"),
        )
        order = result.get("order") if result else None
        if not order or sorted(order) != sorted(JURIST_IDS):
            order = JURIST_IDS[round_no - 1:] + JURIST_IDS[: round_no - 1]  # deterministic fallback rotation
        return order

    def statement(self, jurist: str, round_no: int, transcript: list[str]) -> str:
        so_far = "\n".join(transcript) or "(you speak first this round)"
        user = (
            f"BENCH MEMO:\n{self.memo}\n\n"
            f"ROUND {round_no} STATEMENTS SO FAR:\n{so_far}\n\n"
            f"Deliver your statement to the panel (max {STATEMENT_WORDS} words), in character. "
            "Advance your strongest argument for your current position and engage the strongest "
            "opposing point made so far — name the colleague you are answering when you do.\n"
            'Reply ONLY JSON: {"text": "your statement"}'
        )
        result = chat_json(JUROR_MODEL, self._sys(jurist, round_no), user,
                           self._purpose(f"r{round_no}:speak:{jurist}"))
        return (result or {}).get("text") or "I rest on my prior statement."

    def pick_debate_pairs(self, round_no: int, statements: dict[str, str]) -> tuple[list[list[str]], str]:
        summary = "\n".join(
            f"{j} ({self.positions[j]['position']}, {self.positions[j]['confidence']:.2f}): {s[:200]}"
            for j, s in statements.items()
        )
        result = chat_json(
            SENIOR_MODEL,
            render_system(self.personas["foreperson"], round_no),
            "Pick the 1 or 2 sharpest direct disagreements from this round's statements for focused "
            "two-on-two debate. Prefer pairs on opposite stances whose arguments actually collide. "
            f"Statements:\n{summary}\n"
            'Reply ONLY JSON: {"pairs": [["jurist_a","jurist_b"], ...], '
            '"text": "1-2 neutral sentences framing WHERE each disagreement lies (never who is right)"}',
            self._purpose(f"r{round_no}:pairing"),
        )
        pairs = [
            p for p in (result or {}).get("pairs", [])
            if isinstance(p, list) and len(p) == 2 and all(j in JURIST_IDS for j in p) and p[0] != p[1]
        ][:2]
        text = (result or {}).get("text") or "The chair pairs the sharpest disagreements for focused exchange."
        return pairs, text

    def rebuttal(self, jurist: str, opponent: str, opponent_text: str, round_no: int) -> str:
        user = (
            f"BENCH MEMO:\n{self.memo}\n\n"
            f"Direct exchange. {self.personas[opponent]['display_name']} ({opponent}) just argued:\n"
            f"\"{opponent_text}\"\n\n"
            f"Rebut directly (max {REBUTTAL_WORDS} words), in character, on the substance.\n"
            'Reply ONLY JSON: {"text": "your rebuttal"}'
        )
        result = chat_json(JUROR_MODEL, self._sys(jurist, round_no), user,
                           self._purpose(f"r{round_no}:debate:{jurist}"))
        return (result or {}).get("text") or "My position stands for the reasons given."

    def update_digest(self, jurist: str, round_no: int, transcript: list[str]) -> str:
        user = (
            f"Your private memory digest so far: {self.digests[jurist] or '(empty)'}\n\n"
            f"Round {round_no} full transcript:\n" + "\n".join(transcript) + "\n\n"
            f"Your current private position: {self.positions[jurist]['position']} "
            f"({self.positions[jurist]['confidence']:.2f}).\n"
            "Rewrite your private memory digest (max 120 words) FROM YOUR OWN PERSPECTIVE: the "
            "strongest arguments heard on each side as YOU weigh them, what could still change "
            "your mind per your flip trigger, and open questions. Plain text only."
        )
        return chat(JUROR_MODEL, self._sys(jurist, round_no), user,
                    self._purpose(f"r{round_no}:digest:{jurist}")).strip()[:1500]

    # ---------- run ----------

    def run(self) -> EventLog:
        case_id = self.case["case_id"]
        print(f"[chamber] {self.case['name']} ({case_id})")
        self.memo = bench_memo(self.case)
        self.log.add(type="session_start", case_id=case_id, round=0)
        self.log.add(type="foreperson", action="open_session",
                     text=f"We are convened on {self.case['name']}. The question presented: "
                          f"{self.case['question_presented'][:300]} Private votes first, then statements.")

        final_votes: dict[str, dict] = {}
        for round_no in range(1, MAX_ROUNDS + 1):
            # 1. PRIVATE_VOTE
            votes = self.all_private_votes(round_no, revote=False)
            for j, v in votes.items():
                self.positions[j] = v
                self.log.add(type="vote", agent=j, round=round_no,
                             position=v["position"], confidence=v["confidence"], public=False)
            tally = self._tally(votes)
            print(f"[round {round_no}] private votes: {tally}")

            # 2. STATEMENTS
            transcript: list[str] = []
            statements: dict[str, str] = {}
            for j in self.speaking_order(round_no):
                text = self.statement(j, round_no, transcript)
                statements[j] = text
                transcript.append(f"{self.personas[j]['display_name']} ({j}): {text}")
                self.log.add(type="speak", agent=j, round=round_no, text=text,
                             stance=self.positions[j]["position"],
                             confidence=self.positions[j]["confidence"])

            # 3. PAIR_DEBATE
            pairs, frame_text = self.pick_debate_pairs(round_no, statements)
            if pairs:
                self.log.add(type="foreperson", action="pair_debate",
                             agents=[j for pair in pairs for j in pair], text=frame_text)
            for a, b in pairs:
                last = {a: statements[a], b: statements[b]}
                for speaker, opponent in ((a, b), (b, a), (a, b), (b, a)):
                    text = self.rebuttal(speaker, opponent, last[opponent], round_no)
                    last[speaker] = text
                    transcript.append(f"{self.personas[speaker]['display_name']} ({speaker}): {text}")
                    self.log.add(type="speak", agent=speaker, round=round_no, text=text,
                                 stance=self.positions[speaker]["position"],
                                 confidence=self.positions[speaker]["confidence"])

            # 4. REVOTE (flips emit vote_change)
            revotes = self.all_private_votes(round_no, revote=True)
            for j, v in revotes.items():
                before = votes[j]["position"]
                if v["position"] != before:
                    influenced = [i for i in v.get("influenced_by", []) if i in JURIST_IDS and i != j] or \
                                 [pairs[0][0] if pairs else "textualist"]
                    self.log.add(type="vote_change", agent=j, round=round_no,
                                 **{"from": before, "to": v["position"]},
                                 influenced_by=influenced,
                                 reason_text=v.get("reason") or "On reflection, the argument carried.")
                    print(f"[round {round_no}] FLIP: {j} {before} -> {v['position']}")
                self.positions[j] = v
                self.log.add(type="vote", agent=j, round=round_no,
                             position=v["position"], confidence=v["confidence"], public=False)
            final_votes = revotes

            # 5. digests + CHECK
            with ThreadPoolExecutor(max_workers=9) as pool:
                futures = {j: pool.submit(self.update_digest, j, round_no, transcript) for j in JURIST_IDS}
                for j, f in futures.items():
                    self.digests[j] = f.result()

            tally = self._tally(revotes)
            print(f"[round {round_no}] revote: {tally}")
            if max(tally.values()) >= SUPERMAJORITY:
                break

        # VERDICT
        counts = self._tally(final_votes)
        position = max(counts, key=counts.get)
        dissenters = [j for j, v in final_votes.items() if v["position"] != position]
        self.log.add(type="verdict", position=position,
                     vote_split=f"{counts[position]}-{9 - counts[position]}",
                     dissenters=dissenters[:4])

        # REVEAL (decided cases only)
        gt = self.case.get("ground_truth")
        if gt:
            actual = "affirm" if gt["disposition"] == "affirmed" else "reverse"
            self.log.add(type="reveal", actual=actual, actual_split=gt["vote_split"],
                         match=(actual == position))
        return self.log

    @staticmethod
    def _tally(votes: dict[str, dict]) -> dict[str, int]:
        counts = {"affirm": 0, "reverse": 0}
        for v in votes.values():
            counts[v["position"]] += 1
        return counts
