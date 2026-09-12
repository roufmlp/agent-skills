"""Drill for run-issues-brief-cap.py."""

import importlib.util
import io
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "run_issues_brief_cap", os.path.join(HERE, "run-issues-brief-cap.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

IMPLEMENTER = "run-issues-implementer"


def decide(prompt, agent="run-issues-implementer"):
    return mod.decide({"tool_input": {"subagent_type": agent, "prompt": prompt}})


def words(n, head="Implement issue 570, attempt 1, on run `batch-207704`."):
    """A prompt of exactly `n` words, opening the way a real brief opens."""
    filler = ["road"] * max(0, n - len(head.split()))
    return head + " " + " ".join(filler)


def test_a_first_attempt_brief_over_the_cap_is_refused():
    code, message = decide(words(900))
    assert code == 2
    assert "900" in message


def test_the_widest_permitted_part_measured_on_a_real_run_passes():
    # The cap is a ceiling, not a cut. On run `batch-207704` the widest issue
    # line plus road settlements came to 381 words. If this check ever fails, the
    # cap has become a cut and the human's 2026-09-08 revision has been undone.
    assert decide(words(381))[0] == 0


def test_a_first_attempt_brief_at_the_cap_passes():
    assert decide(words(mod.CAP_WORDS))[0] == 0


def test_a_first_attempt_brief_one_word_over_is_refused():
    assert decide(words(mod.CAP_WORDS + 1))[0] == 2


def test_a_lean_first_attempt_brief_passes():
    assert decide(words(120))[0] == 0


def test_the_refusal_names_the_four_things_a_brief_carries():
    message = decide(words(900))[1]
    lowered = message.lower()
    assert "issue" in lowered and "path" in lowered
    assert "attempt" in lowered
    assert "road" in lowered
    assert "owed" in lowered or "rejection" in lowered


def test_the_refusal_names_the_count_and_the_cap():
    message = decide(words(1267))[1]
    assert "1267" in message
    assert str(mod.CAP_WORDS) in message


def test_the_refusal_never_waits_for_abdul():
    message = decide(words(900))[1]
    assert "not a halt" in message.lower()


def test_a_second_attempt_is_exempt_at_any_length():
    prompt = words(1600, "Implement issue 561, **attempt 2**, on this run.")
    assert decide(prompt)[0] == 0


def test_a_third_attempt_is_exempt():
    prompt = words(1600, "Implement issue 572b, attempt 3, on this run.")
    assert decide(prompt)[0] == 0


def test_a_tenth_attempt_is_exempt():
    # The exemption is "an attempt after the first", not three literal numbers.
    prompt = words(1600, "Implement issue 572b, attempt 10, on this run.")
    assert decide(prompt)[0] == 0


def test_attempt_one_is_not_an_exemption():
    prompt = words(1600, "Implement issue 570, attempt 1, on this run.")
    assert decide(prompt)[0] == 2


def test_a_brief_naming_no_attempt_is_read_as_a_first_attempt():
    # Measured on run `batch-207704`: every implementer spawn named its attempt.
    # A brief that names none is capped, because the cap is the default and an
    # exemption has to be earned by a marker the runner writes.
    assert decide(words(1600, "Implement issue 570 on this run."))[0] == 2


def test_the_correction_marker_is_exempt():
    prompt = words(1600, "**CORRECTION ROUND** for issue 571 on this run.")
    assert decide(prompt)[0] == 0


def test_the_correction_marker_is_read_in_any_case():
    for head in ("**Correction round** for issue 571.",
                 "correction round for issue 571.",
                 "This is a CORRECTION ROUND for issue 571."):
        assert decide(words(1600, head))[0] == 0


def test_a_correction_named_deep_in_the_brief_does_not_exempt():
    # Ticket 36 ruling 11, 2026-09-07: an override word the runner can type
    # anywhere covers one fault and then nothing. The marker is read in the
    # OPENING of the prompt, which is where all four measured correction briefs
    # of run `batch-207704` carry it, and the refusal says so.
    prompt = ("Implement issue 570, attempt 1, on this run. " + "road " * 400
              + "There is no correction round owed here.")
    assert decide(prompt)[0] == 2


def test_the_refusal_names_where_the_correction_marker_is_read():
    message = decide(words(900))[1]
    assert "correction round" in message.lower()
    assert str(mod.OPENING_CHARS) in message


def test_the_attempt_marker_is_read_from_the_first_match():
    # An attempt-2 brief goes on to say "a previous gate rejected attempt 1".
    # Reading the LAST match would cap a lawful retry. The shape is copied from
    # `run-issues-parallel-gates.py:ATTEMPT`, which reads the first match for
    # this same reason.
    prompt = words(1600, "Implement issue 561, **attempt 2**, on this run. A "
                         "previous review gate rejected attempt 1.")
    assert decide(prompt)[0] == 0
    assert mod.attempt_of("issue 561, attempt 2. ... rejected attempt 1.") == 2
    assert mod.attempt_of("issue 570, attempt 1.") == 1
    assert mod.attempt_of("issue 570.") == 1


def test_every_other_agent_type_passes_at_any_length():
    for agent in ("run-issues-verify-gate", "run-issues-review-gate",
                  "run-issues-implementer-escalated", "parallel-hunt-fixer",
                  "general-purpose", "", None):
        assert decide(words(2000), agent)[0] == 0


def test_a_payload_with_no_prompt_passes():
    assert mod.decide({"tool_input": {"subagent_type": IMPLEMENTER}})[0] == 0
    assert mod.decide({"tool_input": {"subagent_type": IMPLEMENTER,
                                      "prompt": ""}})[0] == 0


def test_a_payload_it_cannot_read_passes():
    assert mod.decide({})[0] == 0
    assert mod.decide({"tool_input": None})[0] == 0
    assert mod.decide({"tool_input": {"subagent_type": IMPLEMENTER,
                                      "prompt": 17}})[0] == 0


def test_the_word_count_is_whitespace_separated():
    assert mod.count_words("one two  three\nfour\t five") == 5
    assert mod.count_words("") == 0
    assert mod.count_words(None) == 0


def test_the_measured_briefs_of_the_run_that_set_the_cap_are_all_refused():
    # Fifteen genuine first-attempt briefs on run `batch-207704`, measured
    # 2026-09-08. The leanest was 606 words and the widest 1,609.
    for measured in (606, 851, 1050, 1187, 1197, 1220, 1258, 1270, 1282, 1322,
                     1369, 1383, 1506, 1528, 1609):
        assert decide(words(measured))[0] == 2, measured


# ---------------------------------------------------------------------------
# Ruling 16, ticket 40 of the pilot-delivery map, the runner's turn growth
# ticket, 2026-09-08: the cap records when it fires, so a later change to the
# number has evidence rather than an opinion.


def observe(prompt, code, agent=IMPLEMENTER, cwd="/tmp/tree"):
    payload = {"cwd": cwd,
               "tool_input": {"subagent_type": agent, "prompt": prompt}}
    return mod.observation(payload, code)


def test_a_refusal_is_observed_with_its_count():
    seen = observe(words(900), 2)
    assert seen["outcome"] == "refused"
    assert seen["words"] == 900
    assert seen["cap"] == mod.CAP_WORDS


def test_a_pass_is_observed_too_because_it_is_what_the_runner_then_removed():
    # "How often refused" alone cannot answer what the runner cut to. The brief
    # it re-issues is another first attempt, so recording passes is what makes
    # the second half of ruling 16 answerable.
    seen = observe(words(310), 0)
    assert seen["outcome"] == "passed"
    assert seen["words"] == 310


def test_a_retry_is_observed_as_an_exemption():
    # An exemption used is the one road past the cap, so it is recorded by name.
    seen = observe(words(900, head="Implement issue 570, attempt 2."), 0)
    assert seen["outcome"] == "exempt-retry"


def test_a_correction_round_is_observed_as_its_own_exemption():
    seen = observe("CORRECTION ROUND for issue 571. " + words(900), 0)
    assert seen["outcome"] == "exempt-correction"


def test_the_observation_carries_the_tree_it_was_spawned_from():
    assert observe(words(310), 0, cwd="/tmp/run-tree")["cwd"] == "/tmp/run-tree"


def test_the_observation_carries_a_time():
    assert observe(words(310), 0)["at"] > 0


def test_every_other_agent_type_is_observed_not_at_all():
    assert observe(words(900), 0, agent="run-issues-verify-gate") is None


def test_a_payload_it_cannot_read_is_observed_not_at_all():
    assert mod.observation("not a dict", 0) is None
    assert mod.observation({"tool_input": None}, 0) is None


def test_a_spawn_with_no_prompt_is_observed_not_at_all():
    assert observe("", 0) is None


def test_the_record_and_the_refusal_read_the_same_exemption_rule():
    """The record says what the cap DID. A second copy of the exemption rules
    could grant one the hook never granted, and the evidence would be a story."""
    for prompt in (words(900),
                   words(900, head="Implement issue 570, attempt 2."),
                   "CORRECTION ROUND for issue 571. " + words(900)):
        code, _ = decide(prompt)
        seen = observe(prompt, code)
        assert (code == 0) == (seen["outcome"] != "refused")
        assert seen["outcome"].startswith("exempt-") == bool(
            mod.exemption(prompt))


def test_the_record_is_one_json_line_per_spawn(tmp_path):
    path = str(tmp_path / "record.jsonl")
    mod.append_record(path, {"outcome": "refused", "words": 900})
    mod.append_record(path, {"outcome": "passed", "words": 310})
    lines = open(path).read().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["outcome"] == "refused"
    assert json.loads(lines[1])["words"] == 310


def test_a_record_that_cannot_be_written_never_reaches_the_caller(tmp_path):
    # A guard that cannot keep its diary must still answer the spawn. The record
    # is evidence for a later decision; the refusal is the run's business.
    mod.append_record(str(tmp_path / "no" / "such" / "dir" / "r.jsonl"),
                      {"outcome": "passed"})


def test_the_record_lives_in_a_temporary_directory():
    # Scrub rule H6 of ~/code/agent-skills/MANIFEST.md: a published hook writes
    # nothing outside a temporary directory. This is the road that keeps it
    # publishable, and the reason the finale reads a file that may be gone.
    assert mod.record_path().startswith(tempfile.gettempdir())


def test_main_writes_the_record_and_still_refuses(tmp_path, monkeypatch):
    """End to end, through `main`, with only the path replaced.

    Sitting 1's typecheck gate bound its side-effecting callables as signature
    defaults, so its first drill silently ran the real compiler. This drives the
    real writer and moves the destination instead.
    """
    path = str(tmp_path / "record.jsonl")
    monkeypatch.setattr(mod, "record_path", lambda: path)
    monkeypatch.setattr(mod.sys, "stdin", io.StringIO(json.dumps(
        {"cwd": "/tmp/tree",
         "tool_input": {"subagent_type": IMPLEMENTER, "prompt": words(900)}})))
    assert mod.main() == 2
    written = json.loads(open(path).read().splitlines()[0])
    assert written["outcome"] == "refused"
    assert written["words"] == 900


def test_main_writes_nothing_for_a_spawn_it_does_not_judge(tmp_path, monkeypatch):
    path = str(tmp_path / "record.jsonl")
    monkeypatch.setattr(mod, "record_path", lambda: path)
    monkeypatch.setattr(mod.sys, "stdin", io.StringIO(json.dumps(
        {"cwd": "/tmp/tree",
         "tool_input": {"subagent_type": "run-issues-finale",
                        "prompt": words(900)}})))
    assert mod.main() == 0
    assert not os.path.exists(path)


if __name__ == "__main__":
    # These are pytest checks, and no `python3` on this machine imports pytest.
    # The ritual runs every suite as `python3 <file>`, so the block finds pytest
    # through `uv` when the import fails, and REFUSES when neither road exists.
    # Exiting 0 here without running them is the silence this block closes.
    import subprocess
    import sys as _sys
    try:
        import pytest
    except ImportError:
        try:
            raise SystemExit(subprocess.call(
                ["uv", "run", "--with", "pytest", "pytest", "-q", __file__]))
        except FileNotFoundError:
            print("REFUSED silent-suite: this file holds pytest checks and this "
                  "machine has neither an importable pytest nor `uv` to fetch "
                  "one.\n  Nothing ran. This is not a pass.", file=_sys.stderr)
            raise SystemExit(2)
    raise SystemExit(pytest.main([__file__, "-q"]))
