#!/usr/bin/env python3
"""Tests for check_finale_stage.py. Run: python3 -m pytest test_check_finale_stage.py -q"""

import check_finale_stage as guard


def test_reads_a_plain_state_line():
    assert guard.read_state("State: finale-board\n") == "finale-board"


def test_reads_a_decorated_state_line():
    """The shape a real ledger carries, decoration and trailing prose included."""
    text = "Started 2026-08-20 03:03. State: **`awaiting-merge`, reached 15:45.** All five done.\n"
    assert guard.read_state(text) == "awaiting-merge"


def test_no_state_line_is_not_a_pass():
    assert guard.read_state("Owner: none\n") is None
    allowed, reason = guard.judge(None, "awaiting-merge")
    assert not allowed and reason.startswith("no-state")


def test_the_recorded_fault_is_refused():
    """The recorded fault: promotion still current, awaiting-merge written."""
    allowed, reason = guard.judge("finale-promotion", "awaiting-merge")
    assert not allowed
    assert reason.startswith("skips-a-step")
    assert "finale-board" in reason


def test_one_step_forward_passes():
    allowed, _ = guard.judge("finale-board", "awaiting-merge")
    assert allowed


def test_re_entering_the_same_stage_passes():
    """A finale killed inside a stage rewrites that stage on resume."""
    allowed, reason = guard.judge("finale-board", "finale-board")
    assert allowed and "re-entering" in reason


def test_going_backwards_is_refused():
    allowed, reason = guard.judge("finale-board", "finale-judgment")
    assert not allowed and reason.startswith("goes-backwards")


def test_an_unknown_target_is_refused():
    allowed, reason = guard.judge("finale-board", "merged")
    assert not allowed and reason.startswith("unknown-state")


def test_every_adjacent_pair_in_the_chain_passes():
    for here, there in zip(guard.CHAIN, guard.CHAIN[1:]):
        allowed, _ = guard.judge(here, there)
        assert allowed, f"{here} -> {there} should pass"
