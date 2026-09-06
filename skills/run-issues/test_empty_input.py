#!/usr/bin/env python3
"""Drill for empty_input.py, the shared refusal of ruling 6, 2026-09-06.

The helper carries one job: make a checker that parsed nothing say so, in words
that name what it could not parse. These cases pin the two things a caller
depends on — the exit code and the sentence — because both are read by a human
at a finale who is deciding whether a run may proceed.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import empty_input


def test_a_non_zero_count_is_not_refused():
    assert empty_input.refuse_empty(3, "run.md", "status row") is False


def test_a_non_zero_count_prints_nothing():
    buf = io.StringIO()
    empty_input.refuse_empty(1, "run.md", "status row", stream=buf)
    assert buf.getvalue() == ""


def test_zero_is_refused():
    buf = io.StringIO()
    assert empty_input.refuse_empty(0, "run.md", "status row", stream=buf) is True


def test_the_message_names_the_source_and_the_shape():
    buf = io.StringIO()
    empty_input.refuse_empty(0, "run.md", "row recording a commit stamp", stream=buf)
    out = buf.getvalue()
    assert "run.md" in out
    assert "row recording a commit stamp" in out


def test_it_says_a_pass_over_nothing_is_not_a_pass():
    # The whole point. A reader skimming for `ok`/`REFUSED` must not read this
    # as a clean result, which is the failure that cost three runs.
    buf = io.StringIO()
    empty_input.refuse_empty(0, "run.md", "status row", stream=buf)
    assert "NOT a pass" in buf.getvalue()


def test_a_denominator_says_the_file_is_not_empty():
    buf = io.StringIO()
    empty_input.refuse_empty(0, "run.md", "status row", read=40, stream=buf)
    out = buf.getvalue()
    assert "read 40 candidate row(s)" in out
    assert "shape and the file's shape disagree" in out


def test_a_zero_denominator_points_at_the_wrong_file_instead():
    # Zero of zero and zero of forty want different repairs, so they get
    # different sentences.
    buf = io.StringIO()
    empty_input.refuse_empty(0, "run.md", "status row", read=0, stream=buf)
    assert "the wrong file" in buf.getvalue()


def test_no_denominator_asserts_neither():
    buf = io.StringIO()
    empty_input.refuse_empty(0, "run.md", "status row", stream=buf)
    out = buf.getvalue()
    assert "candidate row(s)" not in out
    assert "the wrong file" not in out


def test_the_remedy_is_carried_when_given():
    buf = io.StringIO()
    empty_input.refuse_empty(0, "run.md", "status row",
                             remedy="Check the path.", stream=buf)
    assert "Check the path." in buf.getvalue()


def test_the_exit_code_is_two_not_one():
    # 1 means "read and wrong"; 2 means "could not read, so nothing is
    # asserted". A vacuous pass is the second, and every checker in this
    # directory already spends the codes that way.
    assert empty_input.EXIT_EMPTY == 2


def test_it_defaults_to_stderr():
    # stdout carries `ok` lines that a caller may grep. A refusal on stdout
    # beside them is exactly the confusion this closes.
    held, sys.stderr = sys.stderr, io.StringIO()
    try:
        empty_input.refuse_empty(0, "run.md", "status row")
        assert "REFUSED empty-input" in sys.stderr.getvalue()
    finally:
        sys.stderr = held


def test_empty_refusal_builds_the_string_without_printing():
    text = empty_input.empty_refusal("run.md", "status row")
    assert text.startswith("REFUSED empty-input:")
