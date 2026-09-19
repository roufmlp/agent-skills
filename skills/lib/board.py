#!/usr/bin/env python3
"""Draw the tracker as one self-contained page, from the files and nothing else.

    python3 ~/.claude/skills/lib/board.py <issues dir> --out board.html

WHY IT EXISTS. Ruled by the human on 2026-09-13: no external tracker. The files
are the source of truth, and a second copy of them drifts the day after it is
made. So the board is GENERATED, the way `register.md` is generated, and thrown
away the same way. Until this existed there was no picture of any of it: one
project carried 84 open issues with 22 at needs-harden and fan-out zero, a
second carried 641 with 149, and the only way to see the shape was to read the
files.

WHAT IT READS, and none of these readings is written here twice:

    the issue files    `next_batch.load_issues` -- which files are issue files,
                       what a `Status:` is, what counts as a `## Blocked by`
                       bullet, and which severity a `Rows:` line carries
    the run ledgers    `next_batch.load_ledgers`, off `<feature>/runs/<batch>/run.md`
    the header fields  `sweep_parked.header_field`, for `Sentence:` and `Stage:`
    the queue shards   `collect_shards`, off `.scratch/decisions-queue.d/<tree>/`
    the fan-out        `next_batch.fan_out`, issue 01's computation unchanged
    the next batch     `next_batch.schedule`, CALLED rather than re-derived,
                       at `next_batch.IN_MAIN`: what main can build today

Two readers of one tracker that disagreed about what a parked issue is, or about
which batch comes next, would be a fault neither would report. The one field this
file reads for itself is the run half of an `Origin:` line, which nothing else
ranks by, and it reads it with that module's own grammar.

THE COLUMNS are `parked`, `needs-harden`, `ready-for-agent`, held by a run,
`blocked`, `done`, `closed` and `unreadable`. Six are `Status:` values and two are
not. An issue a run holds still READS `ready-for-agent` in its file, because
`Status:` does not change until the run merges, so a board that believed the file
would offer work another session is building; the ledger beats the file, on
`next_batch.LEDGER_HOLDS`. And a file whose header no tool can place lands in
`unreadable`, because the page draws only the columns it is given and a card
without one would be a card nobody sees.

WHAT A CARD CARRIES. The number, the sentence, the stage, the severity, the count
of open issues the issue unblocks, the count of queued questions still waiting on
the human, and the run that holds it. A field no file carries is empty and never a
guess, which is `sweep_parked.py`'s rule and the same reason: a guess on a board
is indistinguishable from a fact on a board.

THE GRAPH draws the same issues as nodes, sized by fan-out, with an edge from each
blocker to the issue it blocks, and outlines the next batch of N. N is a control on
the page, and every batch it can show was computed by calling `next_batch.schedule`
before the page was written. That is what makes the outline and
`next_batch.py --count N` the same list rather than two implementations that agree
today. The control stops at `BATCH_STOPS`, for the reason recorded there.

WHAT IT WILL NOT DO. It writes one file, the one named by `--out`, and nothing else.
The page stores nothing: no cookie, no local storage, no request. Every value
reaches the page through `textContent`, so an issue whose sentence carries markup
is text and never markup. And it refuses rather than drawing a picture that is
wrong: a `Status:` it does not know, a blocker no file carries, a ledger row it
cannot read, and a cycle in the graph. A cycle is the one a board could have drawn
and made to look like a picture.

COLOUR follows the project's own `tokens.css`, beside `issues/`, where it carries
one; otherwise the six in `COLUMN_COLOURS`, one per column. The file is inlined
after this script's own `:root` block, so a project overrides a token by declaring
it and this file needs to know nothing about what is in there. It is not parsed.
It is read for one sequence, `STYLE_END`, and refused where it carries it.

Exit codes: 0 the page was written; 1 the tracker could not be read, reason on
stderr; 2 bad usage.
"""

import argparse
import datetime
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import collect_shards  # noqa: E402
import next_batch  # noqa: E402
import rulings  # noqa: E402
import sweep_parked  # noqa: E402

# `.scratch/decisions-queue.d/<tree>/<prefix>.md`, one shard per writer, the
# layout `collect_shards.py` owns. The issues directory sits at
# `.scratch/<feature>/issues`, so the queue is the feature directory's sibling's
# sibling. `runs/` is found the same way, one level in. A missing directory is
# harmless: a project that has queued nothing has nothing pending.
QUEUE_DIR = collect_shards.QUEUE.shard_dir_name

# The columns, left to right. Five are `Status:` values; `held` is not, and it
# is the reason this list is here rather than `next_batch.KNOWN_STATUSES`. An
# issue a run holds still READS `ready-for-agent` in its file — `Status:` does
# not change until the run merges — so the ledger has to beat the file or the
# board offers work another session is building. `next_batch.py` draws the same
# line with `LEDGER_HOLDS`; this reads it from there rather than restating it.
HELD = "held"
# The eighth column, and not a `Status:` value either. A file whose header no
# tool here can place gets a card in it rather than vanishing: `drawBoard` draws
# only the columns named here, so a card in a column nobody named is a card
# nobody sees. Added 2026-09-18 with `blocked`, on the human's ruling.
UNREADABLE = "unreadable"
COLUMNS = ("parked", "needs-harden", "ready-for-agent", HELD, "blocked",
           "done", "closed", UNREADABLE)

# The fixed set, one per column and in column order, used where the project
# carries no tokens file. Each has a job, and the job is the column's meaning
# rather than decoration: blue for the work that is available, amber for the
# work that is not ready, red for the work a run stopped on, green for what
# landed, and the quiet ones for the states a reader scans past. Values are the
# hue's mid stop; the page derives its light and dark surfaces from them, so a
# project overriding one moves the whole column.
COLUMN_COLOURS = {
    "parked": "#7d8796",          # slate: set aside, not gone
    "needs-harden": "#b3730b",    # amber: a warning, the criteria are not written
    "ready-for-agent": "#2563c9",  # blue: information, this is what a run may take
    HELD: "#7449c4",              # violet: a run has it, hands off
    "blocked": "#b42318",         # red: a run stopped here and left it behind
    "done": "#1f7a4d",            # green: success
    "closed": "#6b7280",          # grey: out of the tracker
    UNREADABLE: "#57534e",        # stone: not a state, a file to repair
}

# A project's own tokens, beside `issues/` in the feature directory. Inlined
# AFTER the script's own `:root` block, so any `--board-*` the project defines
# wins on cascade order alone and the board needs no knowledge of what is in it.
TOKENS_FILE = "tokens.css"

# How many batch stops the graph's control offers. Each stop costs a whole
# `next_batch.schedule` placement here and a whole list of ids on the page, and
# both grow with the tracker: measured 2026-09-14 on a synthetic tracker, an
# uncapped board took 0.1 s and 52 KB at 60 issues, 11.0 s and 0.6 MB at 300,
# and 111.3 s and 2.4 MB at 641 — which is the larger of the two projects'
# counts today, and one of the two measurements this whole set was opened on.
# Nobody runs a batch of 641, and `run-issues` batches have run at five and at
# eight. So the control stops at twelve, or at what the tracker can reach,
# whichever is smaller.
BATCH_STOPS = 12

# The one sequence that ends a `<style>` element. A project's `tokens.css` is
# inlined whole, so a file carrying this closes the element and turns everything
# after it into markup. The board refuses rather than writing that page: it is a
# CSS file, no CSS file needs these characters, and the page's whole claim is
# that it carries no script but its own.
STYLE_END = "</style"

STYLE = r"""
:root {
  color-scheme: light dark;
  --s: 4px;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
          Arial, sans-serif;
  --bg: #f6f7f9;
  --surface: #ffffff;
  --ink: #15191f;
  --ink-quiet: #58616e;
  --line: #dfe3e8;
  --focus: #1a56b8;
  /* The graph's edges are not decoration: an edge IS the blocker relation, so
     it is held at WCAG 2.2 SC 1.4.11's 3:1 and never at `--line`, which is a
     hairline between surfaces. `lib/test_board.py` measures both schemes. */
  --edge: #767e8a;
  --shadow: 0 1px 2px rgba(16, 20, 28, .05), 0 6px 16px rgba(16, 20, 28, .05);
  --tint: 12%;
  --chip-ink-mix: 72%;
  --chip-ink-with: #000000;
__COLUMN_TOKENS__
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #131619;
    --surface: #1b1f24;
    --ink: #e9ebee;
    --ink-quiet: #9aa3b0;
    --line: #2b3138;
    --focus: #7aa7f0;
    --edge: #737c89;
    /* No shadows in the dark: depth comes from a surface lighter than the
       ground. Chips drop saturation and flip their contrast to the text. */
    --shadow: none;
    --tint: 22%;
    --chip-ink-mix: 62%;
    --chip-ink-with: #ffffff;
  }
}

* { box-sizing: border-box; }

/* `hidden` is how this page switches views, and a `display` on a class beats a
   bare attribute selector. Without this the graph's own control drew itself
   over the board, where it outlines nothing. */
[hidden] { display: none !important; }

body {
  margin: 0;
  font: 400 14px/1.5 var(--font);
  background: var(--bg);
  color: var(--ink);
  -webkit-text-size-adjust: 100%;
}

/* Nothing on this page may push the body sideways, and `overflow-x: hidden` is
   NOT how that is reached: it hides the overflow and clips the content, and it
   would make `lib/test_board.py`'s own measurement pass by construction. Wide
   content — the graph — scrolls inside its own container instead, and every
   other box is allowed to shrink. */

.wrap { max-width: 1400px; margin: 0 auto; padding: calc(var(--s) * 6); }

.masthead { padding-bottom: calc(var(--s) * 2); }
.masthead h1 {
  margin: 0 0 calc(var(--s) * 1) 0;
  font-size: 24px;
  line-height: 1.15;
  letter-spacing: -0.02em;
  font-weight: 650;
}
.source {
  margin: 0;
  color: var(--ink-quiet);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.source code { font-size: 12px; }

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: calc(var(--s) * 2);
  align-items: flex-end;
  margin: calc(var(--s) * 6) 0 calc(var(--s) * 4) 0;
  padding-bottom: calc(var(--s) * 4);
  border-bottom: 1px solid var(--line);
}
.field { display: flex; flex-direction: column; gap: calc(var(--s) * 1); }
.field label {
  font-size: 11px;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--ink-quiet);
}
input[type="search"], select {
  font: inherit;
  font-size: 13px;
  min-height: 32px;
  padding: calc(var(--s) * 1) calc(var(--s) * 2);
  color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: calc(var(--s) * 1.5);
}
input[type="search"] { min-width: 200px; }
input[type="range"] { min-height: 32px; accent-color: var(--focus); }

.views { display: flex; gap: calc(var(--s) * 1); }
.views button {
  font: inherit;
  font-size: 13px;
  min-height: 32px;
  padding: calc(var(--s) * 1) calc(var(--s) * 3);
  color: var(--ink-quiet);
  background: transparent;           /* ghost until hover, secondary action */
  border: 1px solid var(--line);
  border-radius: calc(var(--s) * 1.5);
  cursor: pointer;
}
.views button:hover { background: var(--surface); color: var(--ink); }
.views button[aria-pressed="true"] {
  background: var(--surface);
  color: var(--ink);
  border-color: var(--ink-quiet);
  font-weight: 600;
}
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }

.board {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(206px, 1fr));
  gap: calc(var(--s) * 4);
  align-items: start;
}
.column { min-width: 0; }
.column > h2 {
  display: flex;
  gap: calc(var(--s) * 2);
  align-items: baseline;
  margin: 0 0 calc(var(--s) * 2) 0;
  padding-bottom: calc(var(--s) * 1.5);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .02em;
  color: var(--ink-quiet);
  border-bottom: 2px solid var(--col);
}
.column > h2 .tally { margin-left: auto; font-variant-numeric: tabular-nums; }
.stack { display: flex; flex-direction: column; gap: calc(var(--s) * 2); }

.card {
  min-width: 0;
  padding: calc(var(--s) * 3);
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 3px solid var(--col);
  border-radius: calc(var(--s) * 2);
  box-shadow: var(--shadow);
}
.card .no {
  font-size: 13px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}
.card .sentence { margin: calc(var(--s) * 1) 0 0 0; font-size: 14px; }
.card .quiet { margin-top: calc(var(--s) * 1); color: var(--ink-quiet); font-size: 12px; }
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: calc(var(--s) * 1) calc(var(--s) * 2);
  margin-top: calc(var(--s) * 2.5);
  font-size: 12px;
  color: var(--ink-quiet);
}
.meta b { font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
.chip {
  display: inline-block;
  padding: 1px calc(var(--s) * 1.5);
  border-radius: calc(var(--s) * 1);
  font-size: 11px;
  font-weight: 600;
  background: color-mix(in srgb, var(--col) var(--tint), var(--surface));
  color: color-mix(in srgb, var(--col) var(--chip-ink-mix), var(--chip-ink-with));
}

.empty {
  margin: 0;
  padding: calc(var(--s) * 6);
  color: var(--ink-quiet);
  text-align: left;
  background: var(--surface);
  border: 1px dashed var(--line);
  border-radius: calc(var(--s) * 2);
}
.column .empty { padding: calc(var(--s) * 3); font-size: 12px; }

.graph-scroll { overflow-x: auto; padding-bottom: calc(var(--s) * 2); }
.graph-scroll svg { display: block; }
.node { fill: color-mix(in srgb, var(--col) 62%, var(--surface)); }
.node.batch { stroke: var(--ink); stroke-width: 2; }
.edge { stroke: var(--edge); stroke-width: 1.5; fill: none; }
.node-label {
  fill: var(--ink);
  font: 600 11px var(--font);
  font-variant-numeric: tabular-nums;
}
.outline-line { margin: calc(var(--s) * 3) 0 0 0; font-size: 13px; }
.outline-line b { font-variant-numeric: tabular-nums; }

@media (prefers-reduced-motion: no-preference) {
  .card, .views button { transition: border-color .12s ease, background-color .12s ease; }
}
.card:hover { border-color: var(--ink-quiet); }

@media (max-width: 520px) {
  .wrap { padding: calc(var(--s) * 4); }
  .controls { gap: calc(var(--s) * 3); }
  .field, input[type="search"], select { width: 100%; min-width: 0; }
}
"""

SCRIPT = r"""
(function () {
  "use strict";
  var data = JSON.parse(document.getElementById("board-data").textContent);
  var cards = data.cards;
  var batches = data.batches;
  var counts = Object.keys(batches).map(Number).sort(function (a, b) { return a - b; });

  var search = document.getElementById("search");
  var pickStage = document.getElementById("filter-stage");
  var pickStatus = document.getElementById("filter-status");
  var pickRun = document.getElementById("filter-run");
  var count = document.getElementById("batch-count");
  var countOut = document.getElementById("batch-count-out");
  var boardView = document.getElementById("view-board");
  var graphView = document.getElementById("view-graph");

  function options(select, values) {
    values.forEach(function (value) {
      var option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
  }

  function distinct(field) {
    var seen = {};
    cards.forEach(function (card) { if (card[field]) { seen[card[field]] = true; } });
    return Object.keys(seen).sort();
  }

  options(pickStage, distinct("stage"));
  options(pickStatus, distinct("status"));
  options(pickRun, distinct("origin_run"));

  function shown() {
    var term = search.value.trim().toLowerCase();
    return cards.filter(function (card) {
      if (pickStage.value && card.stage !== pickStage.value) { return false; }
      if (pickStatus.value && card.status !== pickStatus.value) { return false; }
      if (pickRun.value && card.origin_run !== pickRun.value) { return false; }
      return !term || card.sentence.toLowerCase().indexOf(term) !== -1;
    });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  function meta(into, label, value) {
    if (value === "" || value === undefined) { return; }
    var span = el("span", null, label + " ");
    span.appendChild(el("b", null, String(value)));
    into.appendChild(span);
  }

  function cardNode(card) {
    var node = el("article", "card");
    node.style.setProperty("--col", "var(--col-" + card.column + ")");
    var head = el("div", "no", card.id);
    if (card.severity) {
      head.appendChild(document.createTextNode(" "));
      head.appendChild(el("span", "chip", card.severity));
    }
    node.appendChild(head);
    node.appendChild(el("p", "sentence", card.sentence || card.file));
    if (card.run) {
      node.appendChild(el("p", "quiet",
        "held by run " + card.run + ", " + card.run_status));
    }
    if (card.unreadable) {
      node.appendChild(el("p", "quiet", card.unreadable));
    }
    var row = el("div", "meta");
    meta(row, "stage", card.stage);
    meta(row, "unblocks", card.fan_out);
    if (card.pending) { meta(row, "waiting on the human", card.pending); }
    if (card.origin_run) { meta(row, "from", card.origin_run); }
    node.appendChild(row);
    return node;
  }

  function drawBoard(visible) {
    boardView.textContent = "";
    if (!visible.length) {
      boardView.appendChild(el("p", "empty",
        "No issue matches these filters. Clear the search, or widen a filter."));
      return;
    }
    var grid = el("div", "board");
    data.columns.forEach(function (name) {
      var inColumn = visible.filter(function (card) { return card.column === name; });
      var column = el("section", "column");
      column.style.setProperty("--col", "var(--col-" + name + ")");
      var head = el("h2", null, name === "held" ? "held by a run" : name);
      head.appendChild(el("span", "tally", String(inColumn.length)));
      column.appendChild(head);
      var stack = el("div", "stack");
      if (!inColumn.length) {
        stack.appendChild(el("p", "empty", "Nothing here."));
      }
      inColumn.forEach(function (card) { stack.appendChild(cardNode(card)); });
      column.appendChild(stack);
      grid.appendChild(column);
    });
    boardView.appendChild(grid);
  }

  var STEP_X = 168;
  var STEP_Y = 64;
  var PAD = 28;

  function layers(visible) {
    var by = {};
    visible.forEach(function (card) { by[card.id] = card; });
    var depth = {};
    function of(id, guard) {
      if (depth[id] !== undefined) { return depth[id]; }
      if (guard[id]) { return 0; }
      guard[id] = true;
      var deepest = 0;
      by[id].blockers.forEach(function (blocker) {
        if (by[blocker]) { deepest = Math.max(deepest, of(blocker, guard) + 1); }
      });
      depth[id] = deepest;
      return deepest;
    }
    visible.forEach(function (card) { of(card.id, {}); });
    var rows = {};
    var placed = {};
    visible.forEach(function (card) {
      var layer = depth[card.id];
      rows[layer] = (rows[layer] || 0) + 1;
      placed[card.id] = {
        card: card,
        x: PAD + layer * STEP_X,
        y: PAD + (rows[layer] - 1) * STEP_Y
      };
    });
    return placed;
  }

  function svgEl(tag, attrs) {
    var node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attrs).forEach(function (key) {
      node.setAttribute(key, String(attrs[key]));
    });
    return node;
  }

  function drawGraph(visible) {
    graphView.textContent = "";
    if (!visible.length) {
      graphView.appendChild(el("p", "empty",
        "No issue matches these filters, so there is no graph to draw."));
      return;
    }
    var placed = layers(visible);
    var outlined = counts.length ? batches[String(count.value)] : [];
    var wide = 0;
    var tall = 0;
    Object.keys(placed).forEach(function (id) {
      wide = Math.max(wide, placed[id].x);
      tall = Math.max(tall, placed[id].y);
    });
    var svg = svgEl("svg", {
      width: wide + PAD * 3, height: tall + PAD * 2,
      viewBox: "0 0 " + (wide + PAD * 3) + " " + (tall + PAD * 2),
      role: "img",
      "aria-label": "Every issue as a node, sized by what it unblocks, "
        + "with an arrow from each blocker to the issue it blocks."
    });
    Object.keys(placed).forEach(function (id) {
      placed[id].card.blockers.forEach(function (blocker) {
        if (!placed[blocker]) { return; }
        svg.appendChild(svgEl("path", {
          "class": "edge",
          d: "M" + placed[blocker].x + " " + placed[blocker].y
            + " C" + (placed[blocker].x + STEP_X / 2) + " " + placed[blocker].y
            + " " + (placed[id].x - STEP_X / 2) + " " + placed[id].y
            + " " + placed[id].x + " " + placed[id].y
        }));
      });
    });
    Object.keys(placed).forEach(function (id) {
      var spot = placed[id];
      var node = svgEl("circle", {
        "class": "node" + (outlined.indexOf(id) !== -1 ? " batch" : ""),
        cx: spot.x, cy: spot.y,
        r: 7 + Math.min(spot.card.fan_out, 14) * 1.4
      });
      node.style.setProperty("--col", "var(--col-" + spot.card.column + ")");
      node.appendChild(svgEl("title", {}));
      node.lastChild.textContent = id + " — " + (spot.card.sentence || spot.card.file)
        + " (unblocks " + spot.card.fan_out + ")";
      svg.appendChild(node);
      var label = svgEl("text", {
        "class": "node-label", x: spot.x, y: spot.y - 14, "text-anchor": "middle"
      });
      label.textContent = id;
      svg.appendChild(label);
    });
    var scroll = el("div", "graph-scroll");
    scroll.appendChild(svg);
    graphView.appendChild(scroll);
    var line = el("p", "outline-line");
    if (!counts.length) {
      line.textContent = "Nothing is reachable, so no batch is outlined.";
    } else {
      line.appendChild(document.createTextNode("Outlined, the next batch of "));
      line.appendChild(el("b", null, String(count.value)));
      line.appendChild(document.createTextNode(": " + outlined.join(" ")));
    }
    graphView.appendChild(line);
  }

  function draw() {
    var visible = shown();
    countOut.textContent = counts.length ? String(count.value) : "none";
    if (graphView.hidden) { drawBoard(visible); } else { drawGraph(visible); }
  }

  document.querySelectorAll("[data-view]").forEach(function (button) {
    button.addEventListener("click", function () {
      var wanted = button.getAttribute("data-view");
      document.querySelectorAll("[data-view]").forEach(function (other) {
        other.setAttribute("aria-pressed",
          other.getAttribute("data-view") === wanted ? "true" : "false");
      });
      boardView.hidden = wanted !== "board";
      graphView.hidden = wanted !== "graph";
      document.getElementById("batch-field").hidden = wanted !== "graph";
      draw();
    });
  });
  [search, pickStage, pickStatus, pickRun, count].forEach(function (control) {
    control.addEventListener("input", draw);
    control.addEventListener("change", draw);
  });

  draw();
  document.documentElement.setAttribute("data-ready", "yes");
}());
"""

# The run half of `Origin: 05/batch-be624c`. `next_batch.origin_issue` reads the
# issue half, which is what it ranks by; the board filters by the run, which no
# other tool here reads. Same normalisation, so the two halves of one line are
# never read by two different rules.
ORIGIN_RUN_RE = re.compile(rf"^(?:{next_batch.ISSUE_ID}|unknown)/(\S+)",
                           re.IGNORECASE)


def origin_run(value: str) -> str:
    """The run half of an `Origin:` line, or "" where it carries none."""
    text = value.replace("*", "").strip().strip("`").strip()
    found = ORIGIN_RUN_RE.match(text)
    return found.group(1) if found else ""


def queue_dir_for(issues_dir: Path) -> Path:
    """`.scratch/decisions-queue.d`, beside the feature directory."""
    return issues_dir.resolve().parent.parent / QUEUE_DIR


def pending_defaults(queue_dir: Path) -> dict:
    """issue id -> how many queued items still wait on the human.

    An item names its issue with the `NN-QN` reference on its heading, the one
    `rulings.py` reads, and is retired when its `q-` id reaches a retirement
    shard: the daily brief's `answered.md`, or an attended session's `ruled.md`.
    Both readings are imported rather than restated, so the board and the
    collector can never disagree about which items are still on the queue.

    Every copy of every shard is read, where `collect_shards.collect` resolves
    which worktree owns each one. The board only counts, and counting is done
    over ids, so a duplicate copy contributes the same id twice and changes
    nothing. Resolving ownership needs `git worktree list`, and a board that
    shelled out to git to draw a count would fail in a tree git cannot answer for.
    """
    counts = {}
    if not queue_dir.is_dir():
        return counts
    shards = [(path.stem, str(path)) for path in sorted(queue_dir.glob("*/*.md"))]
    retired = (collect_shards.answered_ids(shards)
               | collect_shards.ruled_ids(shards))
    for name, path in shards:
        if name in (collect_shards.ANSWERED, collect_shards.RULED):
            continue
        text = Path(path).read_text(encoding="utf-8")
        for section in collect_shards.split_items(text):
            heading = section.split("\n", 1)[0]
            item = collect_shards.item_id(section)
            if not item or item in retired:
                continue
            # Counted once per issue per ITEM. A heading that mentions a
            # second question while asking the first is one question waiting.
            named = {rulings.issue_of(question)
                     for question in rulings.QUESTION_REF.findall(heading)}
            for issue in named - {""}:
                counts[issue] = counts.get(issue, 0) + 1
    return counts


def cards_for(issues_dir: Path, issues: dict, rows, pending=None,
              counts=None) -> list:
    """One card per issue file, in tracker order.

    Every field comes off the files: the sentence and the stage off the header,
    the severity off `Rows:`, the fan-out off `next_batch.fan_out`, and the run
    off the ledger that holds it. A field no file carries is empty, never a
    guess — `sweep_parked.py`'s rule, and the same reason.
    """
    held = next_batch.held_by(rows)
    counts = next_batch.fan_out(issues, rows) if counts is None else counts
    pending = pending or {}
    out = []
    for issue_id in sorted(issues, key=next_batch.sort_key):
        issue = issues[issue_id]
        text = (issues_dir / issue.file).read_text(encoding="utf-8")
        holder = held.get(issue_id)
        out.append({
            "id": issue_id,
            "file": issue.file,
            "status": issue.status,
            "column": (HELD if holder
                       else UNREADABLE if issue.unreadable
                       else issue.status),
            "unreadable": issue.unreadable,
            "run": holder.run if holder else "",
            "run_status": holder.status if holder else "",
            "sentence": sweep_parked.header_field(text, "Sentence"),
            "stage": sweep_parked.header_field(text, "Stage"),
            "severity": issue.severity,
            "origin_run": origin_run(sweep_parked.header_field(text, "Origin")),
            "fan_out": counts[issue_id],
            "pending": pending.get(issue_id, 0),
            "blockers": issue.blockers,
        })
    return out


def batches_for(issues: dict, rows, counts: dict) -> dict:
    """`str(N) -> the batch of N`, for every N the tracker can reach.

    Built by CALLING `next_batch.schedule`, not by re-deriving its order, so
    criterion 3 of the issue holds by construction: the outline on the page is
    the same list the command prints. A count above what is reachable is a
    refusal there, so the page carries no control position that refuses — the
    graph's control has no stop that refuses, and a tracker with nothing
    reachable carries none. `BATCH_STOPS` caps how many it offers, for the
    reason recorded there.
    """
    out = {}
    for count in range(1, BATCH_STOPS + 1):
        try:
            # `IN_MAIN`, the reading a NEW batch must use: an issue finished on
            # an unmerged run's BRANCH is not a satisfied blocker, because a new
            # run branches from main. Passed explicitly from 2026-09-14, when
            # `next_batch.py` separated the two readings; the board draws what a
            # reader can start TODAY, which is what that command now prints.
            plan = next_batch.schedule(issues, count, None, rows,
                                       next_batch.FAN_OUT, counts,
                                       next_batch.IN_MAIN)
        except next_batch.Refusal:
            break
        out[str(count)] = list(plan.order)
    return out


def project_tokens(issues_dir: Path) -> str:
    """The project's own `tokens.css`, or "" where it carries none.

    Refuses a file that carries `</style`, naming the line. Inlining it would
    end the element and hand the rest of the file to the HTML parser, and a
    board that drew that page would still say it carries no script but its own.
    The guard is written against what the HTML parser does with the text, not
    against what the CSS appears to say — `embed` guards the JSON block for the
    same reason and in the same way.
    """
    tokens = issues_dir.resolve().parent / TOKENS_FILE
    if not tokens.is_file():
        return ""
    text = tokens.read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        if STYLE_END in line.lower():
            raise next_batch.Refusal(
                f"{TOKENS_FILE}:{number}: carries `{STYLE_END}`, which ends the "
                "element it would be inlined into; the rest of the file would "
                "become markup on the page")
    return text


def build(issues_dir: Path) -> dict:
    """Everything the page draws, as plain data."""
    issues = next_batch.load_issues(issues_dir)
    cycle = next_batch.find_cycle(issues)
    if cycle:
        raise next_batch.Refusal(
            "the tracker has a cycle and cannot be drawn: "
            + " -> ".join(cycle))
    rows = next_batch.load_ledgers(next_batch.runs_dir_for(issues_dir), issues)
    pending = pending_defaults(queue_dir_for(issues_dir))
    counts = next_batch.fan_out(issues, rows)
    batches = batches_for(issues, rows, counts)
    reach = [int(n) for n in batches] or [1]
    return {"feature": issues_dir.resolve().parent.name,
            "issues_dir": str(issues_dir),
            "generated": datetime.date.today().isoformat(),
            "batch_min": min(reach),
            "batch_max": max(reach),
            "columns": list(COLUMNS),
            "unreadable": [{"file": file, "reason": reason}
                           for file, reason in next_batch.unreadable(issues)],
            "cards": cards_for(issues_dir, issues, rows, pending, counts),
            "batches": batches}


def embed(data: dict) -> str:
    """`data` as JSON safe to sit inside a `<script type="application/json">`.

    The block's content is raw text to the HTML parser until it meets the seven
    characters `</script`, so the guard is written against THAT and not against
    what the JSON appears to say: `<` becomes the JSON escape `\u003c`, which
    every parser reads back as `<`, and the sequence can no longer be formed.
    HTML-escaping the payload instead would corrupt the data — an issue whose
    sentence carries an ampersand would come back holding `&amp;`.
    """
    return (json.dumps(data, indent=1)
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def stylesheet() -> str:
    """The script's own tokens and layout, with the fixed six written in."""
    tokens = "\n".join(f"  --col-{name}: {COLUMN_COLOURS[name]};"
                       for name in COLUMNS)
    return STYLE.replace("__COLUMN_TOKENS__", tokens)


def render(data: dict, tokens: str = "") -> str:
    """The whole page: one file, no network, no library, nothing stored.

    The cards are drawn by the page's own script from the JSON block, which is
    the single copy of the data. Every value reaches the DOM through
    `textContent`, so a sentence carrying markup is text and never markup.
    """
    project = f"<style>\n{tokens}</style>\n" if tokens.strip() else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tracker board — {html.escape(data['feature'])}</title>
<style>{stylesheet()}</style>
{project}</head>
<body>
<div class="wrap">
<header class="masthead">
<h1>{html.escape(data['feature'])}</h1>
<p class="source">Generated {html.escape(data['generated'])} from
<code>{html.escape(data['issues_dir'])}</code>. The files are the tracker; this
page is a copy that is thrown away. Nothing typed here is stored.</p>
</header>

<nav class="controls" aria-label="Views and filters">
<div class="views" role="group" aria-label="View">
<button type="button" data-view="board" aria-pressed="true">Board</button>
<button type="button" data-view="graph" aria-pressed="false">Graph</button>
</div>
<div class="field">
<label for="search">Search the sentence</label>
<input type="search" id="search" placeholder="rounding, rights, VAT">
</div>
<div class="field">
<label for="filter-stage">Stage</label>
<select id="filter-stage"><option value="">Any stage</option></select>
</div>
<div class="field">
<label for="filter-status">Status</label>
<select id="filter-status"><option value="">Any status</option></select>
</div>
<div class="field">
<label for="filter-run">Origin run</label>
<select id="filter-run"><option value="">Any run</option></select>
</div>
<div class="field" id="batch-field" hidden>
<label for="batch-count">Outline the next <span id="batch-count-out">1</span></label>
<input type="range" id="batch-count" min="{data['batch_min']}"
       max="{data['batch_max']}" value="{data['batch_min']}"
       {'disabled' if not data['batches'] else ''}>
</div>
</nav>

<main>
<section id="view-board" aria-label="The tracker by status"></section>
<section id="view-graph" aria-label="The tracker as a graph" hidden></section>
<noscript><p class="empty">This page draws itself with JavaScript. Open it in a
browser with JavaScript on, or read the issue files directly.</p></noscript>
</main>
</div>

<script type="application/json" id="board-data">{embed(data)}</script>
<script>{SCRIPT}</script>
</body>
</html>
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("issues_dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.issues_dir.is_dir():
        parser.error(f"{args.issues_dir} is not a directory")
    # Checked before the tracker is read, so a mistyped path costs nothing and
    # comes back as bad usage rather than as a traceback from the last line.
    if not args.out.parent.is_dir():
        parser.error(f"{args.out.parent} is not a directory, so --out cannot "
                     "be written there")
    try:
        data = build(args.issues_dir)
        page = render(data, project_tokens(args.issues_dir))
    except next_batch.Refusal as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 1
    args.out.write_text(page, encoding="utf-8")
    # One file nobody can place must not cost the tracker, and it must not pass
    # unsaid either. Each is named here and drawn in the `unreadable` column.
    for entry in data["unreadable"]:
        print(f"UNREADABLE {entry['file']}: {entry['reason']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
