"""Clerk agent: case record -> neutral bench memo (qwen3.7-max).

The memo NEVER sees ground_truth — the panel must not be contaminated by the
real outcome, which lives only in the scoreboard's scoring path.
"""

from engine.llm import SENIOR_MODEL, chat

CLERK_SYSTEM = (
    "You are the Clerk of a nine-member deliberative panel. Write a rigorously "
    "neutral bench memo for the case below. Structure: (1) Question presented, "
    "(2) RECORD FACTS — a numbered list of the undisputed facts of record; this "
    "list is authoritative and complete, (3) Procedural posture, (4) The "
    "strongest arguments for REVERSING the judgment below, (5) The strongest "
    "arguments for AFFIRMING it. Give both sides their best case — a jurist "
    "reading only your memo should not be able to tell which side you favor. "
    "You do not know how the real court ruled; never speculate about the "
    "outcome. 450 words maximum."
)


def bench_memo(case: dict) -> str:
    user = (
        f"Case: {case['name']} (docket {case['docket']}, argued {case['date_argued']})\n"
        f"Question presented: {case['question_presented']}\n"
        f"Lower court: {case['lower_court_ruling']}\n"
        f"Facts: {case['facts_summary']}"
    )
    return chat(SENIOR_MODEL, CLERK_SYSTEM, user, purpose=f"clerk:{case['case_id']}").strip()
