#!/usr/bin/env python3
"""Drill for side_by_side.py: pairing, the new and missing cases, and the check before approval.

    python3 test_side_by_side.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import side_by_side as mod


def folder(root, name, files):
    d = Path(root) / name
    d.mkdir()
    for f in files:
        (d / f).write_bytes(b"img")
    return d


class Write(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / "SIDE-BY-SIDE.md"

    def tearDown(self):
        self.tmp.cleanup()

    def page(self, prototype, mvp):
        self.count = getattr(self, "count", 0) + 1
        p = folder(self.root, f"prototype-shots-{self.count}", prototype)
        m = folder(self.root, f"mvp-shots-{self.count}", mvp)
        return mod.render(mod.shots(p), mod.shots(m), self.out)

    def test_a_screen_shot_on_both_sides_is_paired_by_name_across_extensions(self):
        page = self.page(["home-phone.jpg", "home-desktop.jpg"], ["home-phone.png", "home-desktop.png"])
        self.assertIn("## home\n", page)
        self.assertIn("| ![home phone, prototype](prototype-shots-1/home-phone.jpg) | ![home phone, MVP](mvp-shots-1/home-phone.png) |", page)
        self.assertIn("**desktop**", page)
        self.assertIn("Differences:", page)

    def test_a_screen_only_the_mvp_has_is_marked_new(self):
        page = self.page(["home-phone.jpg"], ["home-phone.png", "thanks-phone.png"])
        self.assertIn("## thanks (new)", page)
        self.assertIn("Nobody approved this screen", page)
        self.assertNotIn("## home (new)", page)

    def test_a_screen_only_the_prototype_has_is_listed_as_missing(self):
        page = self.page(["home-phone.jpg", "about-phone.jpg"], ["home-phone.png"])
        self.assertIn(mod.MISSING_HEADING, page)
        self.assertIn("- about", page)
        self.assertNotIn("## about", page)

    def test_a_viewport_only_one_side_has_is_named_on_that_screen(self):
        page = self.page(["home-phone.jpg", "home-desktop.jpg"], ["home-phone.png"])
        self.assertIn("**desktop**: the MVP has no shot at this viewport", page)
        page = self.page(["home-phone.jpg"], ["home-phone.png", "home-desktop.png"])
        self.assertIn("**desktop**: the prototype had no shot at this viewport", page)

    def test_screens_are_sorted_and_non_images_are_ignored(self):
        p = folder(self.root, "p", ["zeta-phone.jpg", "alpha-phone.jpg", "notes.txt"])
        m = folder(self.root, "m", ["zeta-phone.png", "alpha-phone.png"])
        page = mod.render(mod.shots(p), mod.shots(m), self.out)
        self.assertLess(page.index("## alpha"), page.index("## zeta"))
        self.assertNotIn("notes", page)

    def test_two_files_with_one_name_are_refused(self):
        p = folder(self.root, "p", ["home-phone.jpg", "home-phone.png"])
        with self.assertRaises(SystemExit):
            mod.shots(p)

    def test_an_empty_folder_is_refused(self):
        p = folder(self.root, "p", [])
        with self.assertRaises(SystemExit):
            mod.shots(p)

    def test_main_writes_the_page_and_reports_missing_screens_in_its_exit_code(self):
        folder(self.root, "p", ["home-phone.jpg"])
        folder(self.root, "m", ["home-phone.png"])
        code = mod.main(["write", "--prototype", str(self.root / "p"), "--mvp", str(self.root / "m"), "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertTrue(self.out.exists())
        folder(self.root, "p2", ["home-phone.jpg", "about-phone.jpg"])
        code = mod.main(["write", "--prototype", str(self.root / "p2"), "--mvp", str(self.root / "m"), "--out", str(self.out)])
        self.assertEqual(code, 1)


class Check(unittest.TestCase):
    FILLED = "# Side by side\n\n## home\n\n**phone**\n\n| Prototype | MVP |\n| --- | --- |\n| ![a](p/a.jpg) | ![b](m/b.png) |\n\nDifferences:\n\n- none\n"

    def test_a_filled_page_is_ready(self):
        self.assertEqual(mod.check(self.FILLED), [])

    def test_a_placeholder_left_in_is_refused_with_its_line(self):
        refused = mod.check(self.FILLED.replace("- none", "- <none, or one line per difference>"))
        self.assertEqual(len(refused), 1)
        self.assertIn("line 13", refused[0])
        self.assertIn("placeholder", refused[0])

    def test_an_image_line_is_never_read_as_a_placeholder(self):
        self.assertEqual(mod.check(self.FILLED.replace("![a](p/a.jpg)", "![home <phone>](p/<x>.jpg)")), [])
        self.assertEqual(mod.check(self.FILLED.replace("| ![a](p/a.jpg) | ![b](m/b.png) |", "![home <phone>](p/a.jpg)")), [])

    def test_a_page_with_no_screen_is_refused(self):
        self.assertIn("lists no screen", mod.check("# Side by side\n")[0])

    def test_a_page_listing_missing_screens_is_refused(self):
        refused = mod.check(self.FILLED + f"\n{mod.MISSING_HEADING}\n\n- about\n")
        self.assertTrue(any("no shot of" in r for r in refused))

    def test_main_check_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.md"
            page.write_text(self.FILLED)
            self.assertEqual(mod.main(["check", str(page)]), 0)
            page.write_text(self.FILLED.replace("- none", "- <fill>"))
            self.assertEqual(mod.main(["check", str(page)]), 1)
            self.assertEqual(mod.main(["check", str(Path(tmp) / "none.md")]), 2)


if __name__ == "__main__":
    unittest.main()
