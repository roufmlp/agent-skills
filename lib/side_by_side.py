#!/usr/bin/env python3
"""Write the side-by-side page of prototype and MVP screenshots, and check it before it is approved.

    python3 side_by_side.py write --prototype prototype-shots --mvp mvp-shots --out SIDE-BY-SIDE.md
    python3 side_by_side.py check SIDE-BY-SIDE.md

`write` pairs the two folders by file name without extension, `<screen>-<viewport>`, so `home-phone.jpg`
in one folder meets `home-phone.png` in the other. Each screen gets a heading, one pair per viewport and a
differences list the build agent fills in: layout, controls and flow, never data, each one marked intended
with the reason or unintended. A screen with MVP shots and no prototype shots is marked "new". A screen the
prototype had and the MVP does not is listed as missing.

`check` refuses a page that still holds a `<placeholder>`, or lists a missing screen, or has no screen. It is
the step before the person the MVP is for reads the page.

Exit codes: 0 clean, 1 the page or the folders are wrong, 2 nothing could be read.
"""

import argparse
import re
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
PLACEHOLDER = re.compile(r"<[^>\n]+>")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MISSING_HEADING = "## Missing from the MVP"


def shots(folder):
    """Every screenshot in `folder`, as {stem: path}. A stem that appears twice is refused."""
    folder = Path(folder)
    if not folder.is_dir():
        raise SystemExit(f"not a folder: {folder}")
    found = {}
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if path.stem in found:
            raise SystemExit(f"{folder}: {path.name} and {found[path.stem].name} share the name {path.stem}")
        found[path.stem] = path
    if not found:
        raise SystemExit(f"{folder}: holds no screenshot")
    return found


def split(stem):
    """`home-phone` -> ('home', 'phone'). A stem with no dash is one screen at one unnamed viewport."""
    screen, _, viewport = stem.rpartition("-")
    return (screen, viewport) if screen else (stem, "")


def render(prototype, mvp, out):
    """The page's Markdown. Image paths are relative to the page."""
    base = Path(out).resolve().parent

    def rel(path):
        return path.resolve().relative_to(base, walk_up=True).as_posix()

    screens = {}
    for side, found in (("prototype", prototype), ("mvp", mvp)):
        for stem, path in found.items():
            screen, viewport = split(stem)
            screens.setdefault(screen, {}).setdefault(viewport, {})[side] = path

    lines = [
        "# Side by side: prototype and MVP",
        "",
        "Each screen at each viewport, prototype on the left and MVP on the right. Under each pair, every",
        "difference in layout, controls or flow, marked intended with its reason or unintended. Data is never",
        "a difference: the prototype shows fake data and the MVP shows test data. A screen the prototype did",
        "not have is marked new.",
        "",
    ]
    missing = []
    for screen in sorted(screens):
        viewports = screens[screen]
        if all("mvp" not in sides for sides in viewports.values()):
            missing.append(screen)
            continue
        new = all("prototype" not in sides for sides in viewports.values())
        lines += [f"## {screen}" + (" (new)" if new else ""), ""]
        for viewport in sorted(viewports):
            sides = viewports[viewport]
            title = viewport or "one viewport"
            if new:
                lines += [f"**{title}**", "", f"![{screen} {title}, MVP]({rel(sides['mvp'])})", ""]
                continue
            if "mvp" not in sides:
                lines += [f"**{title}**: the MVP has no shot at this viewport; take one or say why in one line: <reason>", ""]
                continue
            if "prototype" not in sides:
                lines += [f"**{title}**: the prototype had no shot at this viewport (new at this width)", "",
                          f"![{screen} {title}, MVP]({rel(sides['mvp'])})", ""]
                continue
            lines += [
                f"**{title}**", "",
                "| Prototype | MVP |", "| --- | --- |",
                f"| ![{screen} {title}, prototype]({rel(sides['prototype'])}) | ![{screen} {title}, MVP]({rel(sides['mvp'])}) |",
                "",
            ]
        if new:
            lines += ["Nobody approved this screen in the prototype review. Say in one line what it does and why it exists: <reason>", ""]
        else:
            lines += ["Differences:", "", "- <none, or one line per difference: what changed; intended because <reason>, or unintended>", ""]
    if missing:
        lines += [MISSING_HEADING, "", "The prototype had these screens and the MVP has no shot of them:", ""]
        lines += [f"- {screen}" for screen in missing] + [""]
    return "\n".join(lines)


def check(text):
    """Every reason the page is not ready for the person who approves it."""
    refused = []
    if not re.search(r"^## ", text, re.M):
        refused.append("the page lists no screen")
    for number, line in enumerate(text.splitlines(), 1):
        # An image's alt text and path are never placeholders; strip every image before reading the line.
        for hit in PLACEHOLDER.findall(IMAGE.sub("", line)):
            refused.append(f"line {number}: placeholder {hit} not filled in")
    if MISSING_HEADING in text:
        refused.append("the page lists screens the MVP has no shot of")
    return refused


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("write")
    w.add_argument("--prototype", required=True)
    w.add_argument("--mvp", required=True)
    w.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("page")
    args = parser.parse_args(argv)

    if args.command == "write":
        page = render(shots(args.prototype), shots(args.mvp), args.out)
        Path(args.out).write_text(page)
        screens = len(re.findall(r"^## (?!Missing)", page, re.M))
        print(f"wrote {args.out}: {screens} screens" + (", some missing from the MVP" if MISSING_HEADING in page else ""))
        return 1 if MISSING_HEADING in page else 0

    path = Path(args.page)
    if not path.is_file():
        print(f"cannot read {path}", file=sys.stderr)
        return 2
    refused = check(path.read_text())
    if refused:
        print(f"{path} is not ready:\n" + "\n".join(f"  {r}" for r in refused), file=sys.stderr)
        return 1
    print(f"{path} is ready for approval")
    return 0


if __name__ == "__main__":
    sys.exit(main())
