#!/usr/bin/env python3
"""Print the session's model and effort, and NAME where each was read.

    python3 read_session_settings.py [--pid <pid>] [--repo <path>]

Written 2026-09-17, after run `batch-26c495` stamped `Session effort at launch:
unmeasured` into a ledger while the session was in fact running at `high`.

WHY THE OLD ROAD MISSED IT. `SKILL.md` said to read both values off the
process's own command line:

    ps -o args= -p "$CLAUDE_PID" | tr ' ' '\\n' | grep -A1 -E '^--(model|effort)$'

That is the road `machine-preflight.py` takes, and for the MODEL it is right --
`--model claude-opus-5` was on the command line and was read correctly. Effort
is not always a flag. It is commonly a setting: `~/.claude/settings.json` on
that machine carried `"effortLevel": "high"`, and no `--effort` appeared on the
command line at all. The instruction's own fallback then fired, honestly, and
wrote `unmeasured` -- a true statement about the road it took and a false
impression of the run.

That matters because `SKILL.md` makes the stamp load-bearing: "a run that does
not stamp its own settings cannot be used as evidence about them". A run stamped
`unmeasured` is dropped from every later comparison, so the blind spot costs the
record of the run rather than one cell of it.

PRECEDENCE, and it is the CLI's own. A command-line flag beats a settings file.
Among settings files the more specific wins: project-local, then project, then
user. Each answer carries the file it came from, so a reader can check it rather
than trust this.

WHAT IT REFUSES: nothing. It prints `unmeasured` for a value it cannot find
anywhere, exactly as the instruction it replaces did, and exits 0 either way. A
launch-time reading that could halt a launch would be worse than the blind spot
it cures.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

# Most specific first. The CLI reads these in this order and a later file's
# value does not override an earlier one here.
SETTINGS_FILES = (
    (".claude/settings.local.json", "project-local settings"),
    (".claude/settings.json", "project settings"),
    ("~/.claude/settings.json", "user settings"),
)

# The settings key for each value, where one exists. There is no settings key
# for the model in the shape this reads -- `model` in settings names a default
# for new sessions rather than what this process is running, so it is not read.
SETTINGS_KEY = {"effort": "effortLevel"}


def from_command_line(pid):
    """`{name: value}` for flags actually on this process's command line."""
    if not pid or not shutil.which("ps"):
        return {}
    try:
        out = subprocess.run(["ps", "-o", "args=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return {}
    tokens = out.split()
    found = {}
    for name in ("model", "effort"):
        flag = f"--{name}"
        for index, token in enumerate(tokens):
            if token == flag and index + 1 < len(tokens):
                found[name] = tokens[index + 1]
                break
            if token.startswith(flag + "="):
                found[name] = token.split("=", 1)[1]
                break
    return found


def from_settings(name, repo, files=SETTINGS_FILES):
    """`(value, source)` for one name, or `(None, None)`.

    `files` is a parameter so a drill can point this at a throwaway tree. The
    default list ends at `~/.claude/settings.json`, which is a real file on this
    machine carrying a real `effortLevel`, so a test that did not override it
    would read the developer's own setting and pass or fail by accident.
    """
    key = SETTINGS_KEY.get(name)
    if not key:
        return None, None
    for relative, label in files:
        path = (os.path.expanduser(relative) if relative.startswith("~")
                else os.path.join(repo, relative))
        try:
            with open(path, encoding="utf-8") as handle:
                value = json.load(handle).get(key)
        except Exception:
            continue
        if value:
            return str(value), f"{label} ({path})"
    return None, None


def read(pid, repo, files=SETTINGS_FILES):
    """`{name: (value, source)}` for `model` and `effort`."""
    flags = from_command_line(pid)
    answer = {}
    for name in ("model", "effort"):
        if name in flags:
            answer[name] = (flags[name], f"the command line (--{name}), pid {pid}")
            continue
        value, source = from_settings(name, repo, files)
        answer[name] = ((value, source) if value
                        else ("unmeasured", "not on the command line and in no "
                                            "settings file this could read"))
    return answer


def lines(answer):
    out = []
    for name, label in (("model", "Session model at launch"),
                        ("effort", "Session effort at launch")):
        value, source = answer[name]
        out.append(f"{label}: {value}")
        out.append(f"  (read from {source})")
    out.append("  Paste both pairs into the ledger header. A value reading "
               "`unmeasured` is a missing measurement and never a default: "
               "write it as it stands and say so in the journal.")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print the session's model and effort with their sources.")
    parser.add_argument("--pid", default=os.environ.get("CLAUDE_PID", ""))
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    for line in lines(read(args.pid, args.repo)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
