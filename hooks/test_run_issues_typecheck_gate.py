"""Drill for run-issues-typecheck-gate.py."""

import importlib.util
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "run_issues_typecheck_gate",
    os.path.join(HERE, "run-issues-typecheck-gate.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

TREE = "/Users/x/code/p/.claude/worktrees/run-abc123"
OTHER = "/Users/x/code/p/.claude/worktrees/run-def456"
VERIFY = "run-issues-verify-gate"

CLEAN = ""
BROKEN = (
    "src/lib/pos/raise.ts(148,7): error TS2345: Argument of type 'string' is "
    "not assignable to parameter of type 'number'.\n"
    "src/lib/pos/other.ts(9,1): error TS2304: Cannot find name 'foo'.\n")
BROKEN_PRETTY = (
    "src/lib/pos/raise.ts:148:7 - error TS2345: Argument of type 'string' is "
    "not assignable to parameter of type 'number'.\n")


class Spy:
    """A typecheck that records every tree it was asked to run in."""

    def __init__(self, code, output):
        self.code = code
        self.output = output
        self.calls = []

    def __call__(self, tree):
        self.calls.append(tree)
        return self.code, self.output


def run(agent=VERIFY, cwd=TREE, run_trees=(TREE,), code=0, output=CLEAN,
        cache=None, now=1000.0, fingerprint=None, has_typecheck=True, spy=None):
    spy = spy or Spy(code, output)
    verdict = mod.decide(
        {"cwd": cwd, "tool_input": {"subagent_type": agent, "prompt": "issue 570"}},
        run_trees=run_trees,
        fingerprint=fingerprint or (lambda tree: "fp-1"),
        typecheck=spy,
        has_typecheck=lambda tree: has_typecheck,
        cache={} if cache is None else cache,
        now=now)
    return verdict, spy


def test_a_clean_typecheck_lets_the_gate_spawn_through():
    (code, message), spy = run()
    assert code == 0
    assert message == ""
    assert spy.calls == [TREE]


def test_a_failing_typecheck_refuses_the_gate_spawn():
    (code, message), _ = run(code=1, output=BROKEN)
    assert code == 2
    assert "src/lib/pos/raise.ts" in message
    assert "148" in message


def test_the_refusal_names_the_FIRST_failing_file_and_line():
    (_, message), _ = run(code=1, output=BROKEN)
    assert "raise.ts" in message
    # The second fault is not what the gate is sent to fix first.
    assert message.count("other.ts") == 0


def test_the_refusal_reads_the_pretty_format_too():
    (code, message), _ = run(code=1, output=BROKEN_PRETTY)
    assert code == 2
    assert "src/lib/pos/raise.ts" in message
    assert "148" in message


def test_the_refusal_never_waits_for_abdul():
    (_, message), _ = run(code=1, output=BROKEN)
    assert "not a halt" in message.lower()


def test_the_refusal_names_two_roads_and_forbids_the_runners_own_edit():
    (_, message), _ = run(code=1, output=BROKEN)
    lowered = message.lower()
    assert "correction" in lowered
    assert "implementer" in lowered


def test_all_three_gate_types_are_checked():
    for agent in ("run-issues-verify-gate", "run-issues-review-gate",
                  "run-issues-review-gate-critical"):
        (code, _), spy = run(agent=agent, code=1, output=BROKEN)
        assert code == 2, agent
        assert spy.calls == [TREE]


def test_every_non_gate_spawn_passes_and_pays_nothing():
    for agent in ("run-issues-implementer", "run-issues-implementer-escalated",
                  "run-issues-finale", "parallel-hunt-fixer", "promotion",
                  "general-purpose", "", None):
        (code, _), spy = run(agent=agent, code=1, output=BROKEN)
        assert code == 0, agent
        assert spy.calls == [], agent


def test_a_gate_spawned_outside_every_live_run_tree_passes():
    (code, _), spy = run(cwd="/Users/x/code/p", code=1, output=BROKEN)
    assert code == 0
    assert spy.calls == []


def test_the_tree_checked_is_the_one_the_live_ledger_names():
    (code, _), spy = run(cwd=TREE + "/src/lib", run_trees=(OTHER, TREE))
    assert code == 0
    assert spy.calls == [TREE]


def test_a_tree_with_no_typecheck_script_passes():
    (code, _), spy = run(has_typecheck=False, code=1, output=BROKEN)
    assert code == 0
    assert spy.calls == []


def test_the_second_gate_of_a_pair_pays_nothing():
    cache = {}
    first, spy1 = run(cache=cache, now=1000.0)
    second, spy2 = run(agent="run-issues-review-gate", cache=cache, now=1100.0)
    assert first == (0, "")
    assert second == (0, "")
    assert spy1.calls == [TREE]
    assert spy2.calls == [], "the cached verdict was not read"


def test_the_cache_is_keyed_on_the_working_tree_and_re_runs_when_it_moves():
    cache = {}
    run(cache=cache, fingerprint=lambda tree: "fp-1")
    (_, _), spy = run(cache=cache, fingerprint=lambda tree: "fp-2")
    assert spy.calls == [TREE], "a moved tree must be re-checked"


def test_the_cache_is_keyed_on_the_tree_so_two_runs_cannot_answer_for_each_other():
    cache = {}
    run(cache=cache, cwd=TREE, run_trees=(TREE,))
    (_, _), spy = run(cache=cache, cwd=OTHER, run_trees=(OTHER,))
    assert spy.calls == [OTHER]


def test_a_cached_verdict_older_than_the_window_is_re_run():
    cache = {}
    run(cache=cache, now=1000.0)
    (_, _), spy = run(cache=cache, now=1000.0 + mod.CACHE_SECONDS + 1)
    assert spy.calls == [TREE]


def test_only_a_PASS_is_ever_cached():
    # A cached refusal would refuse the same spawn twice with no road between,
    # which is the one shape that could loop. A refusal re-runs instead.
    cache = {}
    run(cache=cache, code=1, output=BROKEN)
    (_, _), spy = run(cache=cache, code=1, output=BROKEN)
    assert spy.calls == [TREE]


def test_a_typecheck_that_cannot_be_run_fails_open():
    def explode(tree):
        raise OSError("npm is not on the path")

    verdict = mod.decide(
        {"cwd": TREE, "tool_input": {"subagent_type": VERIFY, "prompt": "x"}},
        run_trees=(TREE,), fingerprint=lambda t: "fp",
        typecheck=explode, has_typecheck=lambda t: True, cache={},
        now=1000.0)
    assert verdict[0] == 0
    assert "npm is not on the path" in verdict[1]


def test_a_fingerprint_that_cannot_be_read_still_checks_the_tree():
    def explode(tree):
        raise OSError("git hung")

    cache = {}
    spy = Spy(1, BROKEN)
    verdict = mod.decide(
        {"cwd": TREE, "tool_input": {"subagent_type": VERIFY, "prompt": "x"}},
        run_trees=(TREE,), fingerprint=explode, typecheck=spy,
        has_typecheck=lambda t: True, cache=cache, now=1000.0)
    assert verdict[0] == 2, "an unreadable fingerprint must not skip the check"
    assert spy.calls == [TREE]
    assert cache == {}, "nothing may be cached under a fingerprint nobody read"


def test_a_payload_it_cannot_read_passes():
    for payload in ({}, {"tool_input": None}, None):
        assert mod.decide(payload, run_trees=(TREE,),
                          fingerprint=lambda t: "fp",
                          typecheck=Spy(1, BROKEN),
                          has_typecheck=lambda t: True,
                          cache={}, now=1.0)[0] == 0


def test_main_resolves_the_modules_own_callables_and_not_a_bound_default():
    # The first end-to-end drill of this hook silently ran the real compiler,
    # because the three callables were bound as signature defaults and a
    # replacement of the module's own copy could not reach them. This pins that.
    spy = Spy(1, BROKEN)
    real_check, real_script, real_mark = (
        mod.run_typecheck, mod.tree_has_typecheck, mod.tree_fingerprint)
    try:
        mod.run_typecheck = spy
        mod.tree_has_typecheck = lambda tree: True
        mod.tree_fingerprint = lambda tree: "fp-1"
        code, message = mod.decide(
            {"cwd": TREE, "tool_input": {"subagent_type": VERIFY,
                                         "prompt": "issue 570"}},
            run_trees=(TREE,), cache={}, now=1000.0)
    finally:
        mod.run_typecheck, mod.tree_has_typecheck, mod.tree_fingerprint = (
            real_check, real_script, real_mark)
    assert spy.calls == [TREE]
    assert code == 2
    assert "raise.ts:148:7" in message


def test_a_package_file_with_no_typecheck_script_is_read_as_nothing_to_check():
    # A project file exists but declares no `typecheck` script. npm exits 1 on a
    # missing script, so reading the exit code alone would refuse every gate of
    # such a run for ever, with a refusal saying the tree does not typecheck.
    root = tempfile.mkdtemp()
    open(os.path.join(root, "package.json"), "w").write(
        json.dumps({"name": "x", "scripts": {"build": "next build"}}))
    assert mod.tree_has_typecheck(root) is False
    open(os.path.join(root, "package.json"), "w").write(
        json.dumps({"name": "x", "scripts": {"typecheck": "tsc --noEmit"}}))
    assert mod.tree_has_typecheck(root) is True


def test_a_tree_with_no_package_file_at_all_has_nothing_to_check():
    assert mod.tree_has_typecheck(tempfile.mkdtemp()) is False


def test_a_package_file_that_will_not_parse_has_nothing_to_check():
    root = tempfile.mkdtemp()
    open(os.path.join(root, "package.json"), "w").write("{ not json")
    assert mod.tree_has_typecheck(root) is False


def test_the_first_error_reader():
    assert mod.first_error(BROKEN) == "src/lib/pos/raise.ts:148:7"
    assert mod.first_error(BROKEN_PRETTY) == "src/lib/pos/raise.ts:148:7"
    assert mod.first_error("") == ""
    # A fault with no file at all -- a missing tsconfig, a bad flag.
    assert mod.first_error(
        "error TS18003: No inputs were found in config file.") == ""


def test_the_first_error_reader_ignores_a_line_that_only_looks_like_one():
    assert mod.first_error("Debugger listening on ws://127.0.0.1:9229/x\n"
                           "src/a.ts(3,1): error TS2304: Cannot find name.\n"
                           ) == "src/a.ts:3:1"


def test_the_gate_reader():
    assert mod.is_gate_spawn({"subagent_type": VERIFY}) is True
    assert mod.is_gate_spawn({"subagent_type": "run-issues-implementer"}) is False
    assert mod.is_gate_spawn({}) is False
    assert mod.is_gate_spawn(None) is False


def test_the_tree_reader():
    assert mod.tree_of(TREE + "/src/a", (OTHER, TREE)) == TREE
    assert mod.tree_of(TREE, (TREE,)) == TREE
    # A sibling whose name shares a prefix is a different tree.
    assert mod.tree_of(TREE + "-old/src", (TREE,)) == ""
    assert mod.tree_of("", (TREE,)) == ""
    assert mod.tree_of(TREE, ()) == ""


def test_the_cache_file_lives_in_a_temporary_directory():
    # It writes nothing into anybody's repository and nothing that outlives a
    # restart.
    assert mod.cache_path().startswith(tempfile.gettempdir())


def test_the_cache_file_survives_being_unreadable():
    path = os.path.join(tempfile.mkdtemp(), "not-json.json")
    open(path, "w").write("{ this is not json")
    assert mod.load_cache(path) == {}
    mod.save_cache(path, {"a": ["fp", 1.0]})
    assert mod.load_cache(path) == {"a": ["fp", 1.0]}


def test_the_cache_file_from_an_older_shape_is_dropped():
    path = os.path.join(tempfile.mkdtemp(), "old.json")
    open(path, "w").write(json.dumps({"version": mod.STATE_VERSION - 1,
                                      "a": ["fp", 1.0]}))
    assert mod.load_cache(path) == {}


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
