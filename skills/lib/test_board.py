#!/usr/bin/env python3
"""The tracker board, ruled by the human on 2026-09-13.

One command draws the tracker as a page, from the files and nothing else. The
board is generated the way `register.md` is generated, and thrown away the same
way: no external tracker, because a second copy drifts the day after it is made.

Run: python3 test_board.py
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "board.py"
NEXT_BATCH = HERE / "next_batch.py"
sys.path.insert(0, str(HERE))

import board  # noqa: E402


# Chrome drives criteria 4 and 5. `--headless` clamps its own window to 500 CSS
# pixels wide on macOS, measured 2026-09-14, so 375 is reached by framing the
# page in an iframe of that width and asking the frame for its scroll width.
# `--dump-dom` prints the DOM after the page's scripts have run, which is how a
# measurement taken in the page comes back out.
CHROMES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
)
# Blink's own enum: 0 dark, 1 light. `--force-prefers-color-scheme` is ignored in
# headless (measured 2026-09-14); this flag is not.
SCHEME = {"dark": 0, "light": 1}


CONTRAST_MATHS = """
        function channel(c) {
          return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        }
        // Chrome reports a `color-mix` result as `color(srgb r g b)` with the
        // channels in 0..1, and everything else as `rgb(r, g, b)` in 0..255.
        function luminance(colour) {
          var p = colour.match(/[\\d.]+/g).map(Number);
          var scale = colour.indexOf('color(') === 0 ? 1 : 255;
          return 0.2126 * channel(p[0] / scale)
               + 0.7152 * channel(p[1] / scale)
               + 0.0722 * channel(p[2] / scale);
        }
        function ratio(ink, ground) {
          var a = luminance(ink), b = luminance(ground);
          return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
        }
        """


def chrome() -> str:
    for path in CHROMES:
        if Path(path).exists():
            return path
    raise unittest.SkipTest("no Chrome to render the page in")


def write_issue(root: Path, name: str, status, sentence="something", stage=None,
                rows=None, origin=None, parked=None, blocked_by=None):
    """One issue file in the tracker's shape, the same writer
    `test_sweep_parked.py` uses, with the header fields the board reads."""
    lines = [f"Status: {status}", f"Sentence: {sentence}"]
    for key, value in (("Stage", stage), ("Rows", rows), ("Origin", origin),
                       ("Parked", parked)):
        if value is not None:
            lines.append(f"{key}: {value}")
    lines += ["", "# A title", "", "## What to build", "", "Words.", ""]
    if blocked_by is not None:
        lines += ["## Blocked by", ""] + [f"- {b}" for b in blocked_by] + [""]
    (root / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ledger(feature: Path, run_id: str, rows):
    """One run ledger at `<feature>/runs/<batch>/run.md`, the path
    `next_batch.load_ledgers` reads."""
    ledger = feature / "runs" / run_id
    ledger.mkdir(parents=True, exist_ok=True)
    lines = ["# Run " + run_id, "", "| Issue | Status |", "|---|---|"]
    lines += [f"| {issue} | {status} |" for issue, status in rows]
    (ledger / "run.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_shard(root: Path, tree: str, prefix: str, body: str):
    """One queue shard at `<root>/.scratch/decisions-queue.d/<tree>/<prefix>.md`,
    the layout `collect_shards.py` owns."""
    shard = root / ".scratch" / "decisions-queue.d" / tree
    shard.mkdir(parents=True, exist_ok=True)
    (shard / f"{prefix}.md").write_text(body, encoding="utf-8")


def item(question: str, item_id: str, marker="[reversible]") -> str:
    """One queue item heading in the shape `check_queue_shard.py` demands: the
    `NN-QN` reference that names the issue, and the backticked `q-` id."""
    return (f"## {question}: whether the thing does the thing `{item_id}` "
            f"{marker}\n\nDefault taken: it does.\n\n")


def next_batch_order(issues_dir, count):
    """The Issue column of `next_batch.py --count N`, read back off the command
    itself. The independent source of truth criterion 3 compares against: the
    page is checked against what a reader running that command would be told."""
    result = subprocess.run(
        [sys.executable, str(NEXT_BATCH), str(issues_dir), "--count", str(count)],
        capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    lines = result.stdout.splitlines()
    # From 2026-09-14 the command heads its output with the shape that fired
    # ("SOME CAN START IN PARALLEL...") when a run is live, and prints the table
    # under it. Find the table by its own header rather than by position.
    head = next(i for i, line in enumerate(lines) if line.startswith("Issue "))
    order = []
    for line in lines[head + 1:]:
        if not line.strip():
            break                                 # the table ends at the blank line
        order.append(line.split()[0])
    return order


def run(issues_dir, out, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(issues_dir), "--out", str(out), *args],
        capture_output=True, text=True)


class Base(unittest.TestCase):
    """A tracker under a temporary repository root: `<root>/.scratch/<feature>/`
    holding `issues/` and `runs/`, beside `<root>/.scratch/decisions-queue.d/`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.feature = self.root / ".scratch" / "a-feature"
        self.issues = self.feature / "issues"
        self.issues.mkdir(parents=True)
        self.out = self.root / "board.html"
        self.addCleanup(self._tmp.cleanup)

    def build(self, *args):
        result = run(self.issues, self.out, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.out.read_text(encoding="utf-8")

    def cards(self, page: str) -> dict:
        """The page's own card data, by issue id."""
        return {card["id"]: card for card in json.loads(
            re.search(r'<script type="application/json" id="board-data">(.*?)</script>',
                      page, re.S).group(1))["cards"]}


class EveryFileGetsOneCard(Base):
    def test_the_page_lists_every_issue_file_exactly_once(self):
        write_issue(self.issues, "01-first", "done")
        write_issue(self.issues, "02-second", "ready-for-agent")
        write_issue(self.issues, "03-third", "needs-harden")
        write_issue(self.issues, "04-fourth", "parked", parked="2026-01-01")
        write_issue(self.issues, "05-fifth", "closed")
        cards = self.cards(self.build())
        self.assertEqual(sorted(cards), ["01", "02", "03", "04", "05"])
        self.assertEqual(len(cards), len(list(self.issues.glob("*.md"))))


class TheColumns(Base):
    def test_a_run_holds_an_issue_the_file_still_calls_ready(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        write_ledger(self.feature, "batch-be624c", [("07", "in-progress")])
        card = self.cards(self.build())["07"]
        self.assertEqual(card["column"], "held")
        self.assertEqual(card["run"], "batch-be624c")
        self.assertEqual(card["status"], "ready-for-agent")

    def test_an_issue_no_run_holds_sits_in_its_own_status(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        write_ledger(self.feature, "batch-be624c", [("07", "queued")])
        card = self.cards(self.build())["07"]
        self.assertEqual(card["column"], "ready-for-agent")
        self.assertEqual(card["run"], "")

    def test_the_columns_are_the_eight_the_board_draws(self):
        """Six on 2026-09-14, eight from 2026-09-18: `blocked`, which a run
        writes when it spends a strike cap, and `unreadable`, where a file no
        tool can place is shown instead of refusing the tracker."""
        self.assertEqual(board.COLUMNS,
                         ("parked", "needs-harden", "ready-for-agent", "held",
                          "blocked", "done", "closed", "unreadable"))


class WhatACardCarries(Base):
    def test_it_carries_the_sentence_the_stage_and_the_severity(self):
        write_issue(self.issues, "07-rounding", "needs-harden",
                    sentence="Money rounds the way the contract says",
                    stage="checkout", rows="rv01-6 operator/high; rv01-7 buyer/medium",
                    origin="05/batch-be624c")
        card = self.cards(self.build())["07"]
        self.assertEqual(card["sentence"], "Money rounds the way the contract says")
        self.assertEqual(card["stage"], "checkout")
        self.assertEqual(card["severity"], "high")
        self.assertEqual(card["origin_run"], "batch-be624c")

    def test_a_field_the_file_does_not_carry_is_empty_and_never_a_guess(self):
        write_issue(self.issues, "07-rounding", "needs-harden")
        card = self.cards(self.build())["07"]
        for field in ("stage", "severity", "origin_run"):
            self.assertEqual(card[field], "", field)

    def test_the_fan_out_is_the_count_next_batch_computes(self):
        # A diamond: 01 blocks 02 and 03, both block 04. 01 counts 04 once.
        write_issue(self.issues, "01-first", "ready-for-agent", blocked_by=["None"])
        write_issue(self.issues, "02-second", "ready-for-agent", blocked_by=["01"])
        write_issue(self.issues, "03-third", "ready-for-agent", blocked_by=["01"])
        write_issue(self.issues, "04-fourth", "ready-for-agent",
                    blocked_by=["02", "03"])
        cards = self.cards(self.build())
        self.assertEqual(cards["01"]["fan_out"], 3)
        self.assertEqual(cards["04"]["fan_out"], 0)


class PendingDefaults(Base):
    def test_it_counts_the_queued_items_that_name_the_issue(self):
        write_issue(self.issues, "07-rounding", "needs-harden")
        write_issue(self.issues, "08-vat", "needs-harden")
        write_shard(self.root, "a-tree", "ti07",
                    "# A shard\n\n" + item("07-Q1", "q-ti07-1")
                    + item("07-Q2", "q-ti07-2") + item("08-Q1", "q-ti07-3"))
        cards = self.cards(self.build())
        self.assertEqual(cards["07"]["pending"], 2)
        self.assertEqual(cards["08"]["pending"], 1)

    def test_an_answered_item_is_not_pending(self):
        write_issue(self.issues, "07-rounding", "needs-harden")
        write_shard(self.root, "a-tree", "ti07",
                    "# A shard\n\n" + item("07-Q1", "q-ti07-1")
                    + item("07-Q2", "q-ti07-2"))
        write_shard(self.root, "a-tree", "answered",
                    "# Answered\n\nq-ti07-1  2026-09-13\n")
        self.assertEqual(self.cards(self.build())["07"]["pending"], 1)

    def test_an_item_ruled_at_the_keyboard_is_not_pending_either(self):
        write_issue(self.issues, "07-rounding", "needs-harden")
        write_shard(self.root, "a-tree", "ti07",
                    "# A shard\n\n" + item("07-Q1", "q-ti07-1"))
        write_shard(self.root, "a-tree", "ruled",
                    "# Ruled\n\nq-ti07-1  2026-09-13  .scratch/rulings.md\n")
        self.assertEqual(self.cards(self.build())["07"]["pending"], 0)

    def test_one_item_naming_two_questions_on_one_issue_counts_once(self):
        """The count is of items waiting on the human, and an item is one question
        however many others its heading mentions."""
        write_issue(self.issues, "05-fifth", "needs-harden")
        write_shard(self.root, "a-tree", "ti05",
                    "# A shard\n\n## 05-Q1: whether 05-Q2 belongs here "
                    "`q-ti05-1` [reversible]\n\nDefault taken: yes.\n")
        self.assertEqual(self.cards(self.build())["05"]["pending"], 1)

    def test_a_tracker_with_no_queue_directory_counts_none(self):
        write_issue(self.issues, "07-rounding", "needs-harden")
        self.assertEqual(self.cards(self.build())["07"]["pending"], 0)


class TheOutlinedBatch(Base):
    def a_tracker(self):
        """Four open issues, a chain and a spur, so fan-out and number disagree."""
        write_issue(self.issues, "05-fifth", "ready-for-agent", blocked_by=["None"])
        write_issue(self.issues, "09-ninth", "ready-for-agent", blocked_by=["None"])
        write_issue(self.issues, "10-tenth", "ready-for-agent", blocked_by=["09"])
        write_issue(self.issues, "11-eleventh", "ready-for-agent", blocked_by=["10"])

    def batches(self, page):
        return json.loads(re.search(
            r'<script type="application/json" id="board-data">(.*?)</script>',
            page, re.S).group(1))["batches"]

    def test_the_outlined_batch_equals_the_command_for_the_same_count(self):
        self.a_tracker()
        batches = self.batches(self.build())
        self.assertEqual(sorted(int(n) for n in batches), [1, 2, 3, 4])
        for count in (1, 2, 3, 4):
            self.assertEqual(batches[str(count)],
                             next_batch_order(self.issues, count),
                             f"--count {count}")

    def test_the_page_carries_no_count_a_tracker_cannot_reach(self):
        write_issue(self.issues, "05-fifth", "ready-for-agent", blocked_by=["None"])
        write_issue(self.issues, "06-sixth", "done")
        batches = self.batches(self.build())
        self.assertEqual(sorted(batches), ["1"])

    def test_a_tracker_with_nothing_reachable_carries_no_batch(self):
        write_issue(self.issues, "05-fifth", "done")
        self.assertEqual(self.batches(self.build()), {})

    def test_the_page_stops_at_the_largest_batch_anyone_runs(self):
        """A stop costs a whole `schedule` placement and a whole list on the
        page, and nobody runs a batch of four hundred."""
        for n in range(1, board.BATCH_STOPS + 4):
            write_issue(self.issues, f"{n:03d}-issue", "ready-for-agent",
                        blocked_by=["None"])
        batches = self.batches(self.build())
        self.assertEqual(sorted(int(n) for n in batches),
                         list(range(1, board.BATCH_STOPS + 1)))
        top = str(board.BATCH_STOPS)
        self.assertEqual(batches[top],
                         next_batch_order(self.issues, board.BATCH_STOPS))


class WhatItRefuses(Base):
    def test_a_status_the_tracker_does_not_know_is_NOT_a_refusal(self):
        """Reversed on the human's ruling of 2026-09-18. It was a refusal of the
        whole tracker until that day, when one unknown word blinded four
        instruments across two repositories at once."""
        write_issue(self.issues, "07-rounding", "in-flight")
        result = run(self.issues, self.out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("in-flight", result.stderr)
        self.assertIn("07-rounding.md", result.stderr)
        self.assertTrue(self.out.exists(), "the page was not drawn")

    def test_a_directory_that_is_not_there_is_bad_usage(self):
        result = run(self.root / "nowhere", self.out)
        self.assertEqual(result.returncode, 2)

    def test_a_cycle_is_a_refusal_and_the_page_is_not_drawn(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent", blocked_by=["08"])
        write_issue(self.issues, "08-vat", "ready-for-agent", blocked_by=["07"])
        result = run(self.issues, self.out)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cycle", result.stderr.lower())
        self.assertFalse(self.out.exists(), "a cycle drew a page")

    def test_a_tokens_file_that_closes_the_style_element_is_a_refusal(self):
        """The page's whole claim is that it carries no script but its own. A
        tokens file holding `</style>` ends the element and everything after it
        is markup, so the board refuses rather than writing that page."""
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        (self.feature / board.TOKENS_FILE).write_text(
            ':root { --x: "</style><script>window.x=1</script>"; }\n',
            encoding="utf-8")
        result = run(self.issues, self.out)
        self.assertEqual(result.returncode, 1)
        self.assertIn(board.TOKENS_FILE, result.stderr)
        self.assertIn("</style", result.stderr)
        self.assertFalse(self.out.exists(), "a broken tokens file wrote a page")

    def test_an_output_directory_that_is_not_there_is_bad_usage(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        result = run(self.issues, self.root / "no" / "such" / "board.html")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_a_blocker_no_file_carries_is_a_refusal(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent", blocked_by=["99"])
        result = run(self.issues, self.out)
        self.assertEqual(result.returncode, 1)
        self.assertIn("99", result.stderr)


class WhatItWrites(Base):
    def test_it_writes_nothing_but_the_output_file(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        write_ledger(self.feature, "batch-be624c", [("07", "queued")])
        write_shard(self.root, "a-tree", "ti07",
                    "# A shard\n\n" + item("07-Q1", "q-ti07-1"))
        before = {path: path.read_bytes() for path in sorted(self.root.rglob("*"))
                  if path.is_file()}
        self.build()
        after = {path: path.read_bytes() for path in sorted(self.root.rglob("*"))
                 if path.is_file()}
        self.assertEqual(set(after) - set(before), {self.out})
        for path, content in before.items():
            self.assertEqual(after[path], content, f"{path} was rewritten")

    def test_the_page_stores_nothing_and_loads_nothing(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        page = self.build()
        for forbidden in ("localStorage", "sessionStorage", "indexedDB",
                          "document.cookie", "fetch(", "XMLHttpRequest",
                          "navigator.send", "<script src", "<link rel",
                          "@import", "url("):
            self.assertNotIn(forbidden, page, forbidden)
        # The one `http` on the page is the SVG namespace, which is an
        # identifier and not an address: nothing is fetched from it. Every
        # other occurrence would be a resource the page cannot render without.
        self.assertEqual(set(re.findall(r"https?://[^\s\"'<>)]+", page)),
                         {"http://www.w3.org/2000/svg"})


class InABrowser(Base):
    """Criteria 4 and 5: the page renders with no console message in light and
    dark, and its body never scrolls sideways at 375 CSS pixels."""

    # Enough of a tracker that every column, both views and every filter have
    # something to draw: a chain, a spur, a held issue, a parked one and a
    # closed one.
    def a_tracker(self):
        write_issue(self.issues, "05-fifth", "done", stage="checkout",
                    sentence="Money rounds the way the contract says")
        write_issue(self.issues, "09-ninth", "ready-for-agent", stage="checkout",
                    blocked_by=["05"], rows="rv01-6 operator/high",
                    origin="05/batch-be624c")
        write_issue(self.issues, "10-tenth", "ready-for-agent", stage="rights",
                    blocked_by=["09"])
        write_issue(self.issues, "11-eleventh", "needs-harden", stage="rights",
                    blocked_by=["Unknown until hardened"],
                    rows="rv01-9 buyer/medium", origin="05/batch-be624c")
        write_issue(self.issues, "12-twelfth", "parked", parked="2026-01-01",
                    rows="rv01-4 buyer/low", blocked_by=["Unknown until hardened"])
        write_issue(self.issues, "13-thirteenth", "ready-for-agent",
                    blocked_by=["None"])
        write_issue(self.issues, "14-fourteenth", "closed")
        write_ledger(self.feature, "batch-19ff9f", [("13", "in-progress")])
        write_shard(self.root, "a-tree", "ti09",
                    "# A shard\n\n" + item("09-Q1", "q-ti09-1"))

    def dom(self, page_path: Path, scheme="light"):
        """The DOM Chrome prints after running the page, plus its console log.

        `--incognito` so the run leaves nothing in the profile, `--host-resolver-
        rules` so every host fails to resolve, and `--disable-extensions` so the
        only console messages are the page's own. The resolver rule is half the
        test: a page that needed the network could not render under it.

        The profile is Chrome's own. A `--user-data-dir` of its own would be
        tidier and hangs: a fresh profile starts the component updater, which
        holds the process open past the DOM. Measured 2026-09-14, three flag
        sets, every one over sixty seconds against under a second here.
        """
        result = subprocess.run(
            [chrome(), "--headless", "--disable-gpu", "--no-sandbox",
             "--incognito", "--disable-extensions", "--no-first-run",
             "--no-default-browser-check", "--disable-component-update",
             "--host-resolver-rules=MAP * ~NOTFOUND",
             f"--blink-settings=preferredColorScheme={SCHEME[scheme]}",
             "--allow-file-access-from-files", "--enable-logging=stderr", "--v=1",
             "--virtual-time-budget=5000", "--dump-dom", page_path.as_uri()],
            capture_output=True, text=True, timeout=120)
        (self.root / f"chrome-{scheme}.log").write_text(result.stderr,
                                                        encoding="utf-8")
        console = [line for line in result.stderr.splitlines() if ":CONSOLE:" in line]
        return result.stdout, console

    def driven(self, driver_js: str) -> Path:
        """A copy of the page with a driver appended: test instrumentation, never
        shipped. The driver reports through the title, which `--dump-dom` prints."""
        copy = self.root / "driven.html"
        copy.write_text(self.out.read_text(encoding="utf-8")
                        + f"\n<script>{driver_js}</script>\n", encoding="utf-8")
        return copy

    def title_of(self, dom: str) -> str:
        return re.search(r"<title>(.*?)</title>", dom, re.S).group(1)

    def test_it_renders_with_no_console_message_in_light_and_in_dark(self):
        self.a_tracker()
        self.build()
        for scheme in ("light", "dark"):
            dom, console = self.dom(self.out, scheme)
            self.assertEqual(console, [], f"{scheme}: {console}")
            self.assertIn("data-ready=\"yes\"", dom, scheme)

    def test_driving_every_control_raises_no_console_message(self):
        self.a_tracker()
        self.build()
        driver = """
        (function () {
          function fire(el, type) {
            el.dispatchEvent(new Event(type, {bubbles: true}));
          }
          var steps = 0;
          document.querySelectorAll('[data-view]').forEach(function (button) {
            button.click(); steps += 1;
          });
          var count = document.getElementById('batch-count');
          for (var n = Number(count.min); n <= Number(count.max); n += 1) {
            count.value = String(n); fire(count, 'input'); steps += 1;
          }
          document.querySelectorAll('select').forEach(function (select) {
            for (var i = 0; i < select.options.length; i += 1) {
              select.selectedIndex = i; fire(select, 'change'); steps += 1;
            }
            select.selectedIndex = 0; fire(select, 'change');
          });
          var search = document.getElementById('search');
          ['money', 'zzzz', ''].forEach(function (term) {
            search.value = term; fire(search, 'input'); steps += 1;
          });
          document.title = 'steps=' + steps;
        }());
        """
        dom, console = self.dom(self.driven(driver))
        self.assertEqual(console, [], str(console))
        steps = int(self.title_of(dom).split("=")[1])
        self.assertGreater(steps, 10, "the driver reached almost no control")

    def test_the_outlined_nodes_are_the_batch_for_the_count_on_screen(self):
        self.a_tracker()
        page = self.build()
        driver = """
        (function () {
          document.querySelector('[data-view="graph"]').click();
          var count = document.getElementById('batch-count');
          count.value = count.max;
          count.dispatchEvent(new Event('input', {bubbles: true}));
          var ids = [];
          document.querySelectorAll('circle.batch').forEach(function (node) {
            ids.push(node.querySelector('title').textContent.split(' ')[0]);
          });
          document.title = count.value + '|' + ids.join(',');
        }());
        """
        dom, console = self.dom(self.driven(driver))
        self.assertEqual(console, [], str(console))
        chosen, outlined = self.title_of(dom).split("|")
        expected = json.loads(re.search(
            r'<script type="application/json" id="board-data">(.*?)</script>',
            page, re.S).group(1))["batches"][chosen]
        self.assertEqual(sorted(outlined.split(",")), sorted(expected))
        self.assertEqual(expected, next_batch_order(self.issues, int(chosen)))

    def test_the_batch_control_is_shown_only_with_the_graph_it_outlines(self):
        """A `hidden` attribute loses to any `display` a class sets, so the
        control drew itself over the board, where it outlines nothing."""
        self.a_tracker()
        self.build()
        driver = """
        (function () {
          function shown(id) {
            return getComputedStyle(document.getElementById(id)).display !== 'none';
          }
          var onBoard = shown('batch-field');
          document.querySelector('[data-view="graph"]').click();
          var onGraph = shown('batch-field');
          document.querySelector('[data-view="board"]').click();
          document.title = onBoard + ' ' + onGraph + ' ' + shown('batch-field');
        }());
        """
        dom, console = self.dom(self.driven(driver))
        self.assertEqual(console, [], str(console))
        self.assertEqual(self.title_of(dom), "false true false")

    def test_the_graph_edges_keep_their_contrast_in_both_schemes(self):
        """WCAG 2.2 SC 1.4.11: 3:1 for a part a reader needs to understand the
        picture. A `## Blocked by` edge IS the picture."""
        self.a_tracker()
        self.build()
        driver = CONTRAST_MATHS + """
        (function () {
          document.querySelector('[data-view="graph"]').click();
          var edges = document.querySelectorAll('.edge');
          var ground = getComputedStyle(document.body).backgroundColor;
          var worst = 99;
          edges.forEach(function (edge) {
            worst = Math.min(worst, ratio(getComputedStyle(edge).stroke, ground));
          });
          document.title = worst.toFixed(2) + ' over ' + edges.length;
        }());
        """
        for scheme in ("light", "dark"):
            dom, console = self.dom(self.driven(driver), scheme)
            self.assertEqual(console, [], f"{scheme}: {console}")
            measured = self.title_of(dom)
            self.assertGreater(int(measured.split(" over ")[1]), 1,
                               f"{scheme}: the driver graded almost no edge")
            self.assertGreaterEqual(float(measured.split(" ")[0]), 3.0,
                                    f"{scheme}: {measured}")

    def test_the_text_keeps_its_contrast_in_both_schemes(self):
        """WCAG 2.2 SC 1.4.3: body text at 4.5:1, and the chips are body text."""
        self.a_tracker()
        self.build()
        driver = CONTRAST_MATHS + """
        (function () {
          var worst = 99, where = '', seen = 0;
          document.querySelectorAll('.card, .chip, .meta, .card .quiet, .column > h2')
            .forEach(function (node) {
              seen += 1;
              var style = getComputedStyle(node);
              var ground = style.backgroundColor;
              var behind = node;
              while (/^(rgba\\(0, 0, 0, 0\\)|transparent)$/.test(ground)
                     && behind.parentElement) {
                behind = behind.parentElement;
                ground = getComputedStyle(behind).backgroundColor;
              }
              var found = ratio(style.color, ground);
              if (found < worst) { worst = found; where = node.className; }
            });
          document.title = worst.toFixed(2) + ' at ' + where + ' over ' + seen;
        }());
        """
        for scheme in ("light", "dark"):
            dom, console = self.dom(self.driven(driver), scheme)
            self.assertEqual(console, [], f"{scheme}: {console}")
            measured = self.title_of(dom)
            self.assertGreater(int(measured.split(" over ")[1]), 10,
                               f"{scheme}: the driver graded almost nothing")
            self.assertGreaterEqual(float(measured.split(" ")[0]), 4.5,
                                    f"{scheme}: {measured}")

    def test_every_control_clears_the_touch_target_floor(self):
        """WCAG 2.2 SC 2.5.8: 24 CSS pixels is the floor."""
        self.a_tracker()
        self.build()
        driver = """
        (function () {
          var worst = 999, where = '', seen = 0;
          function grade() {
            document.querySelectorAll('button, select, input').forEach(function (node) {
              var box = node.getBoundingClientRect();
              if (!box.height && !box.width || node.graded) { return; }
              node.graded = true;            // two buttons share id and type
              seen += 1;
              if (box.height < worst) {
                worst = box.height; where = node.id || node.type;
              }
            });
          }
          grade();
          document.querySelector('[data-view="graph"]').click();
          grade();
          document.title = worst.toFixed(1) + ' at ' + where + ' over ' + seen;
        }());
        """
        dom, console = self.dom(self.driven(driver))
        self.assertEqual(console, [], str(console))
        measured = self.title_of(dom)
        self.assertEqual(int(measured.split(" over ")[1]), 7,
                         f"the page does not carry its seven controls: {measured}")
        self.assertGreaterEqual(float(measured.split(" ")[0]), 24.0, measured)

    def test_the_body_does_not_scroll_sideways_at_375_pixels(self):
        self.a_tracker()
        self.build()
        frame = self.root / "at-375.html"
        frame.write_text(
            "<!doctype html><html><head><title>start</title>"
            "<style>body{margin:0}iframe{width:375px;height:812px;border:0}</style>"
            "</head><body><iframe id=\"f\" src=\"board.html\"></iframe><script>"
            "addEventListener('load', function () {"
            "  var f = document.getElementById('f');"
            "  var d = f.contentDocument;"
            "  document.title = d.documentElement.scrollWidth + ' of '"
            "    + d.documentElement.clientWidth + ' in ' + f.offsetWidth;"
            "});</script></body></html>", encoding="utf-8")
        dom, console = self.dom(frame)
        self.assertEqual(console, [], str(console))
        measured = self.title_of(dom)
        scroll, rest = measured.split(" of ")
        client, frame = rest.split(" in ")
        self.assertEqual(int(frame), 375, f"the frame was not 375 wide: {measured}")
        # `clientWidth` is the frame minus its vertical scrollbar, and that is
        # the width the body actually has to fit into.
        self.assertLessEqual(int(scroll), int(client),
                             f"the body scrolls sideways: {measured}")


class TheColour(Base):
    def test_the_fixed_set_names_one_colour_per_column(self):
        self.assertEqual(tuple(board.COLUMN_COLOURS), board.COLUMNS)
        self.assertEqual(len(set(board.COLUMN_COLOURS.values())),
                         len(board.COLUMNS))

    def test_a_project_tokens_file_is_inlined_after_the_scripts_own(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        (self.feature / board.TOKENS_FILE).write_text(
            ":root { --board-ink: #123456; }\n", encoding="utf-8")
        page = self.build()
        self.assertIn("--board-ink: #123456", page)
        self.assertGreater(page.index("--board-ink: #123456"),
                           page.index(board.COLUMN_COLOURS["done"]),
                           "the project's tokens must come last to win")

    def test_a_tracker_with_no_tokens_file_uses_the_fixed_set(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        page = self.build()
        for colour in board.COLUMN_COLOURS.values():
            self.assertIn(colour, page)


class StatusesTheTrackerWrites(Base):
    """The human's ruling of 2026-09-18, both halves.

    A run writes `blocked` when it spends a strike cap. On 2026-09-18 the word
    stopped both boards and both parked sweeps, and 42 parked issues went
    unchecked. So `blocked` becomes a column, and a status no tool knows
    names its file instead of refusing the whole tracker.
    """

    def test_blocked_has_its_own_column(self):
        self.assertIn("blocked", board.COLUMNS)

    def test_a_blocked_issue_is_drawn_in_that_column(self):
        write_issue(self.issues, "139-screens", "blocked")
        cards = self.cards(self.build())
        self.assertEqual(cards["139"]["status"], "blocked")
        self.assertEqual(cards["139"]["column"], "blocked")

    def test_a_status_no_tool_knows_does_not_refuse_the_tracker(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        write_issue(self.issues, "09-assign", "in-progress")
        page = self.build()
        cards = self.cards(page)
        self.assertIn("07", cards)
        self.assertIn("09", cards)

    def test_an_unreadable_issue_is_drawn_where_a_reader_will_see_it(self):
        write_issue(self.issues, "09-assign", "in-progress")
        card = self.cards(self.build())["09"]
        self.assertEqual(card["column"], board.UNREADABLE)
        self.assertIn(board.UNREADABLE, board.COLUMNS)
        self.assertIn("in-progress", card["unreadable"])

    def test_the_command_names_the_file_it_could_not_read(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        write_issue(self.issues, "09-assign", "in-progress")
        out = run(self.issues, self.out)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("09-assign.md", out.stdout + out.stderr)


RUN_ISSUES = HERE.parent / "run-issues"


def statuses_the_runner_writes() -> set:
    """Every ledger status the run-issues skill says its runner writes, read from
    the skill rather than copied, so a status the skill gains is tested the day it
    is written down.

    Two sources. `SKILL.md`'s `Ledger statuses:` sentence names the chain and its
    two side statuses. A `blocked` row carries its reason in brackets, and the
    reasons are written in two shapes: the literal `blocked (criteria)` and
    `blocked (depends on NN)` in `SKILL.md`, and "ledger it `blocked` with the
    reason `light: two attempts spent`" in `check_attempt_cap.py`, which run
    `batch-e2c4ee` wrote to its ledger as `blocked (light: two attempts spent)`.
    """
    skill = (RUN_ISSUES / "SKILL.md").read_text(encoding="utf-8")
    sentence = re.search(r"Ledger statuses:(.*?)\.\s", skill, re.S).group(1)
    found = set()
    for token in re.findall(r"`([^`]+)`", sentence):
        found.update(word.strip() for word in token.split("→"))
    found.update(re.findall(r"`(blocked \([^)`]+\))`", skill))
    for source in sorted(RUN_ISSUES.glob("*.py")) + sorted(RUN_ISSUES.glob("*.md")):
        if source.name.startswith("test_"):
            continue
        text = " ".join(source.read_text(encoding="utf-8").split())
        found.update(f"blocked ({reason})" for reason in re.findall(
            r"`blocked` with the reason `([^`]+)`", text))
    return {status.replace("NN", "11") for status in found}


class LedgerStatusesTheRunnerWrites(Base):
    """Run `batch-e2c4ee` wrote `blocked (light: two attempts spent)` for issue
    281, a light issue that spent its two attempts, and on 2026-09-30 the board
    refused one project's whole tracker over that one cell. A blocked row is not
    held: the run kept the work off its branch and built nothing into main."""

    def test_the_skill_names_every_blocked_form_measured_so_far(self):
        """The collector must find something, or the test below passes on an
        empty set. These are the forms the skill carried on 2026-09-30."""
        self.assertLessEqual(
            {"queued", "in-progress", "gates", "done", "correction", "blocked",
             "blocked (criteria)", "blocked (depends on 11)",
             "blocked (light: two attempts spent)"},
            statuses_the_runner_writes())

    def test_the_board_draws_over_every_status_the_runner_writes(self):
        statuses = sorted(statuses_the_runner_writes())
        rows = []
        for number, status in enumerate(statuses, start=10):
            write_issue(self.issues, f"{number}-issue", "ready-for-agent")
            rows.append((str(number), status))
        write_ledger(self.feature, "batch-e2c4ee", rows)
        out = run(self.issues, self.out)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_a_light_issue_that_spent_its_attempts_is_not_held(self):
        write_issue(self.issues, "281-sheet-asks", "ready-for-agent")
        write_ledger(self.feature, "batch-e2c4ee",
                     [("281", "blocked (light: two attempts spent)")])
        card = self.cards(self.build())["281"]
        self.assertEqual(card["column"], "ready-for-agent")
        self.assertEqual(card["run"], "")

    def test_a_blocked_row_with_a_reason_nobody_wrote_yet_is_not_held(self):
        """The next reason the runner gives a `blocked` row is still `blocked`."""
        write_issue(self.issues, "07-rounding", "ready-for-agent")
        write_ledger(self.feature, "batch-e2c4ee",
                     [("07", "blocked (full: three attempts spent)")])
        card = self.cards(self.build())["07"]
        self.assertEqual(card["column"], "ready-for-agent")
        self.assertEqual(card["run"], "")

    def test_a_status_outside_the_runners_grammar_still_refuses(self):
        for status in ("blocked by 176", "blocked-on-someone", "blocked ()",
                       "blocked (criteria) again", "finished"):
            with self.subTest(status=status):
                write_issue(self.issues, "07-rounding", "ready-for-agent")
                write_ledger(self.feature, "batch-e2c4ee", [("07", status)])
                out = run(self.issues, self.out)
                self.assertNotEqual(out.returncode, 0)
                self.assertIn("does not know", out.stdout + out.stderr)
                self.assertIn(repr(status), out.stdout + out.stderr)


class WhatTheFilesSay(Base):
    def test_a_sentence_that_carries_html_is_escaped_not_run(self):
        write_issue(self.issues, "07-rounding", "ready-for-agent",
                    sentence="Totals use <script>alert(1)</script> & co")
        page = self.build()
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertEqual(self.cards(page)["07"]["sentence"],
                         "Totals use <script>alert(1)</script> & co")


if __name__ == "__main__":
    unittest.main()
