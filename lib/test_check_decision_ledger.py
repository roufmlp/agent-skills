#!/usr/bin/env python3
"""Cases for check_decision_ledger.

Each case is a mutation somebody would actually make: a walk that forgets the
ledger, a walk that writes the heading and no table, a walk that gives reversal
cost but not tokens, a walk that fills a cell with "TBD". The point of the
script is to refuse those, so the point of these cases is to prove it does.

    python3 test_check_decision_ledger.py
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

from check_decision_ledger import check, find_ledger, headings_in

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


def expect(name: str, text: str, want_pass: bool, rulings: int | None = None,
           heading: str | None = None) -> None:
    problems = check(text, rulings, heading=heading)
    passed = not problems
    if passed != want_pass:
        FAILURES.append((name, "pass" if want_pass else "refusal", "; ".join(problems) or "pass"))


def expect_mentions(name: str, text: str, needle: str) -> None:
    problems = check(text)
    if not any(needle in problem for problem in problems):
        FAILURES.append((name, f"a refusal mentioning {needle!r}", "; ".join(problems) or "pass"))



THREE_LEDGERS = """
## Decision ledger, costs

| What | Ruling | Cost to reverse | Time | Tokens | Workflow |
|---|---|---|---|---|---|
| Shape | JSON lines | An hour | None | None | Generated |
| History | All kept | Nil | Nil | Nil | Marked |

### Decision ledger, sitting 1

| What | Ruling | Cost to reverse | Time | Tokens | Workflow |
|---|---|---|---|---|---|
| Origin | Its own column | Minutes | None | None | Seven briefs |

### Decision ledger, sitting 2

| What | Ruling | Cost to reverse | Time | Tokens | Workflow |
|---|---|---|---|---|---|
| Counts | Written null | Ten minutes | None | None | Sitting 3 fills |
| Notes | History kept | Minutes | None | None | Cap binds new |
| Hunt | Shares the file | Minutes | None | None | Kind field |
"""


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


    # --- More than one ledger in one file -------------------------------
    #
    # A ticket file collects one ledger per sitting, so these files hold
    # several. Before `--heading`, `find_ledger` took the FIRST heading and
    # stopped, so it graded another sitting's table.
    #
    # Measured on 2026-09-06 on the two live files. Ticket 37 holds three
    # ledgers; the checker graded the 8-row grilling table at line 253 and
    # never saw sitting 2's at line 432, so asked for 6 rulings it refused,
    # naming 8. Ticket 39 holds two and it graded sitting 4's, never
    # sitting 3's.
    #
    # Both directions are real. It refuses a correct new ledger, and it can
    # answer `ok` while the new ledger is absent or short, because it graded
    # an old table instead. The second is silent, and it is the same `ok` on
    # a table nobody could read that ticket 37 sitting 1 met.

    expect(
        "with no heading named, the first ledger is still the one graded",
        THREE_LEDGERS, True, rulings=2,
    )

    expect(
        "a named heading grades that ledger and not the first",
        THREE_LEDGERS, True, rulings=3, heading="sitting 2",
    )

    expect(
        "the first ledger's row count no longer decides a named one",
        THREE_LEDGERS, False, rulings=3,
    )

    expect(
        "a named heading matches whatever its case",
        THREE_LEDGERS, True, rulings=1, heading="SITTING 1",
    )

    expect(
        "a heading matching nothing refuses rather than falling back",
        THREE_LEDGERS, False, rulings=3, heading="sitting 9",
    )

    expect(
        "a named heading with no table under it is not a pass",
        THREE_LEDGERS + "\n### Decision ledger, sitting 3\n\nnot a table\n",
        False, rulings=1, heading="sitting 3",
    )

    if find_ledger(THREE_LEDGERS.splitlines(), heading="sitting 2") is None:
        FAILURES.append(("find_ledger reaches the named ledger", True, False))
    if headings_in(THREE_LEDGERS.splitlines()) != [
            "Decision ledger, costs", "Decision ledger, sitting 1",
            "Decision ledger, sitting 2"]:
        FAILURES.append(("every heading is listed for the refusal", True, False))


    # The pass line must always carry the caveat. `~/.claude/questionrules.md`
    # says this checker's pass may never be reported as more than "the ledger
    # is complete", and on 2026-09-06 an inline conditional detached the
    # sentence from the --heading branch, so that branch printed a bare `ok`.
    import io, contextlib
    from check_decision_ledger import main as _main
    _tmp = pathlib.Path(tempfile.mkdtemp()) / "walk.md"
    _tmp.write_text(THREE_LEDGERS, encoding="utf-8")
    for _args in ([str(_tmp), "--rulings", "2"],
                  [str(_tmp), "--rulings", "3", "--heading", "sitting 2"]):
        _out = io.StringIO()
        with contextlib.redirect_stdout(_out):
            _main(_args)
        if "COMPLETE, which is not the same as correct" not in _out.getvalue():
            FAILURES.append((f"the pass line keeps its caveat: {_args}",
                             "the caveat", _out.getvalue().strip()))

    if FAILURES:
        print(f"FAILED {len(FAILURES)} case(s):")
        for name, wanted, got in FAILURES:
            print(f"  - {name}: wanted {wanted}, got {got}")
        return 1

    print("check_decision_ledger: all cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

