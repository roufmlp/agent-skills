#!/usr/bin/env python3
"""Refuse a Bash command that starts Chrome without the keychain and media flags.

PreToolUse hook on Bash, registered in ~/.claude/settings.json.

Ruled by Abdul on 2026-09-30, in the session that asked why macOS kept showing
"Keychain Not Found: A keychain cannot be found to store Chrome", and why
Apple Music kept opening.

WHAT HAPPENED. His login keychain was sound and was the default. The dialog
came from agents. Sessions had run the Chrome binary directly, as
`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new
--dump-dom ...`, to screenshot or read a page. Chrome asks the keychain for its
"Chrome Safe Storage" key at start. From inside the Claude Code sandbox the
keychain cannot be reached, so macOS asks the human. Puppeteer never caused it:
it adds `--use-mock-keychain` and `--password-store=basic` itself.

WHY A HOOK AND NOT A LINE IN A BRIEF. `~/.claude/CLAUDE.md` sorts every
proposal by whether it can refuse. This can. A brief that says "pass the mock
keychain flag" is a reminder, and an agent reaching for a quick screenshot does
not read briefs.

WHAT IS COLLECTED. Every reference in the command to a binary inside a
Chrome-family app bundle: any `<name>.app/Contents/MacOS/` whose name holds
Chrome or Chromium. That covers Google Chrome, Canary, Chromium and Playwright's
"Google Chrome for Testing", in quotes, with escaped spaces, in an assignment
(`CH="..."; "$CH" --headless`) and inside a heredoc of Python that shells out.

The forms measured on 2026-09-30, by reading every Bash `tool_use` in
`~/.claude/projects/*/**.jsonl` that named Chrome and carried `--headless`,
`--dump-dom`, `--screenshot`, `--print-to-pdf` or `--remote-debugging`: 47 were
the literal bundle path followed by flags, 12 put the bundle path in a variable
or a Python list, and none used `open -a`, a bare `chrome` command, or the
headless shell. Every launching form holds the bundle path, so the path is what
this guard reads.

WHAT PASSES. A command whose every Chrome reference is accompanied by all four
of the flags in `REQUIRED`, and any command that uses
`~/.claude/bin/headless-chrome`, which holds no bundle path. Nothing else is
read: a command that never names a Chrome binary is none of this hook's business.

A command that only LOOKS at the binary (`ls`, `grep` on `ps`) is refused too.
That is deliberate and rare: the refusal says to check the bundle directory
instead, which carries no `/Contents/MacOS/`.
"""

import json
import re
import sys

# A binary inside an app bundle whose name holds Chrome or Chromium. The name
# class takes letters, digits, spaces, dots, dashes and the backslash of an
# escaped space.
_CHROME_BINARY = re.compile(
    r"[\w .\\-]*Chrom(?:e|ium)[\w .\\-]*\.app/Contents/MacOS/", re.IGNORECASE)

# The flags `~/.claude/bin/headless-chrome` adds. The first two are the measured
# cause of the keychain dialog; the second two are the probable cause of Music.
REQUIRED = (
    "--use-mock-keychain",
    "--password-store=basic",
    "--mute-audio",
    "HardwareMediaKeyHandling",
)

WRAPPER = "~/.claude/bin/headless-chrome"


def verdict(command):
    """The refusal text for this command, or None."""
    if not command:
        return None
    if not _CHROME_BINARY.search(command):
        return None
    missing = [flag for flag in REQUIRED if flag not in command]
    if not missing:
        return None
    return (
        "REFUSED: this command runs the Chrome binary without "
        + ", ".join(f"`{flag}`" for flag in missing) + ".\n"
        "Chrome started that way asks the macOS keychain for its key. From the "
        "sandbox the keychain cannot be reached, and macOS puts a \"Keychain Not "
        "Found\" dialog in front of Abdul. On 2026-09-30 he asked why it kept "
        "appearing, and why Apple Music kept opening.\n"
        f"Use the wrapper, which adds every flag and `--headless=new`:\n"
        f"    {WRAPPER} --dump-dom \"file://$PWD/page.html\"\n"
        f"    {WRAPPER} --screenshot=/tmp/shot.png --window-size=1280,900 <url>\n"
        "From code, call that path as the executable. To check Chrome is "
        "installed, test the bundle: `ls \"/Applications/Google Chrome.app\"`.")


GUARDED_TOOLS = ("Bash",)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # Never break the session over a malformed payload.
    try:
        if str(payload.get("tool_name") or "") not in GUARDED_TOOLS:
            return 0
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return 0
        reason = verdict(str(tool_input.get("command") or ""))
        if reason is None:
            return 0
        print(reason, file=sys.stderr)
        return 2
    except Exception:
        return 0  # A stack trace at a PreToolUse boundary is this hook's fault.


if __name__ == "__main__":
    sys.exit(main())
