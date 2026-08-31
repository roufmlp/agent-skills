#!/usr/bin/env python3
"""Cases for check_decision_ledger.

Each case is a mutation somebody would actually make: a walk that forgets the
ledger, a walk that writes the heading and no table, a walk that gives reversal
cost but not tokens, a walk that fills a cell with "TBD". The point of the
script is to refuse those, so the point of these cases is to prove it does.

    python3 test_check_decision_ledger.py
"""

from __future__ import annotations

import sys

from check_decision_ledger import check

COMPLETE = """
# Walk

Some prose about what happened.

## Decision ledger

| # | What | Ruling | Cost to reverse | Time | Tokens | Workflow |
|---|---|---|---|---|---|---|
| 1 | The auth finding | 484 absorbs it | one issue file | +0 | ~5k | 485-489 wait on a pass |
| 2 | Ticket 32 | Close it | one line | none | ~2k | one fewer stale ticket |
"""

FAILURES: list[tuple[str, str, str]] = []


def expect(name: str, text: str, want_pass: bool, rulings: int | None = None) -> None:
    problems = check(text, rulings)
    passed = not problems
    if passed != want_pass:
        FAILURES.append((name, "pass" if want_pass else "refusal", "; ".join(problems) or "pass"))


def expect_mentions(name: str, text: str, needle: str) -> None:
    problems = check(text)
    if not any(needle in problem for problem in problems):
        FAILURES.append((name, f"a refusal mentioning {needle!r}", "; ".join(problems) or "pass"))


def main() -> int:
    expect("a complete ledger passes", COMPLETE, True)
    expect("row count matches", COMPLETE, True, 2)
    expect("row count mismatch refuses", COMPLETE, False, 3)

    expect("no ledger at all refuses", "# Walk\n\nWe decided some things.\n", False)

    # Pins the MESSAGE, not just the verdict. A mutant that made find_ledger
    # return an empty table instead of None still refused — on "missing
    # columns", which tells a walker the wrong thing to fix. This case kills it.
    expect_mentions(
        "a missing ledger says so, rather than blaming the columns",
        "# Walk\n\nWe decided some things.\n",
        "No decision ledger found",
    )

    expect(
        "a heading with no table refuses",
        "# Walk\n\n## Decision ledger\n\nWe decided some things.\n",
        False,
    )

    expect_mentions(
        "a missing tokens column is named",
        """## Decision ledger

| # | What | Ruling | Cost to reverse | Time | Workflow |
|---|---|---|---|---|---|
| 1 | A thing | Do it | one line | +0 | clearer |
""",
        "tokens",
    )

    expect(
        "a TBD cell refuses",
        """## Decision ledger

| # | What | Ruling | Cost to reverse | Time | Tokens | Workflow |
|---|---|---|---|---|---|---|
| 1 | A thing | Do it | one line | TBD | ~5k | clearer |
""",
        False,
    )

    expect(
        "an em-dash placeholder refuses",
        """## Decision ledger

| # | What | Ruling | Cost to reverse | Time | Tokens | Workflow |
|---|---|---|---|---|---|---|
| 1 | A thing | Do it | one line | +0 | — | clearer |
""",
        False,
    )

    expect(
        "a header at any depth is found",
        COMPLETE.replace("## Decision ledger", "#### The walk's decision ledger"),
        True,
    )

    expect(
        "alternative column wording is accepted",
        """### Decision ledger

| Item | Ruled | Undo | Clock | Spend | What it buys |
|---|---|---|---|---|---|
| The gate | Adopt | one paragraph | +0 | ~1k | one fewer stray row a run |
""",
        True,
    )

    expect(
        "an empty cell refuses",
        """## Decision ledger

| # | What | Ruling | Cost to reverse | Time | Tokens | Workflow |
|---|---|---|---|---|---|---|
| 1 | A thing | Do it | one line |  | ~5k | clearer |
""",
        False,
    )

    if FAILURES:
        print(f"FAILED {len(FAILURES)} case(s):")
        for name, wanted, got in FAILURES:
            print(f"  - {name}: wanted {wanted}, got {got}")
        return 1

    print("check_decision_ledger: all cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
