"""Focused regression tests for the firmware modal layout test contract."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_firmware_modal_layouts as checker  # noqa: E402


class FirmwareModalLayoutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = json.loads(checker.FIXTURES.read_text(encoding="utf-8"))
        cls.jc = next(
            entry for entry in cls.fixtures["layouts"] if entry["slug"] == "guition-jc4827w543r"
        )

    def test_jc_coverage_is_complete_for_both_padding_modes(self) -> None:
        coverage = self.jc["coverage"]
        self.assertEqual(coverage["rotations"], ["0", "90", "180", "270"])
        self.assertEqual(coverage["mediaTabCounts"], [1, 2, 3, 4, 5])
        self.assertEqual(coverage["climateTabCounts"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(coverage["standaloneTabCount"], 0)

        generated = "\n".join(checker.cpp_assertions(self.jc, 5))
        self.assertEqual(generated.count("for (int rotation : {0, 90, 180, 270})"), 2)
        self.assertIn('check_coverage(profile, rotated_request, "guition-jc4827w543r normal"', generated)
        self.assertIn('check_coverage(profile, rotated_request, "guition-jc4827w543r compact"', generated)

    def test_jc_coverage_cannot_be_removed(self) -> None:
        fixtures = copy.deepcopy(self.fixtures)
        jc = next(entry for entry in fixtures["layouts"] if entry["slug"] == "guition-jc4827w543r")
        del jc["coverage"]
        with self.assertRaisesRegex(AssertionError, "JC4827 modal fixture coverage is required"):
            checker.check_fixture_schema(fixtures)

    def test_jc_source_evidenced_contract_cannot_be_relaxed(self) -> None:
        mutations = (
            ("coverage", "scrollableMinimumHeight", 0, "source-evidenced 76px"),
            ("panelInsets", "top", 29, "normal panel insets"),
            ("compactPanelInsets", "left", 4, "compact panel insets"),
        )
        for section, key, value, message in mutations:
            with self.subTest(section=section, key=key):
                fixtures = copy.deepcopy(self.fixtures)
                jc = next(entry for entry in fixtures["layouts"] if entry["slug"] == "guition-jc4827w543r")
                jc[section][key] = value
                with self.assertRaisesRegex(AssertionError, message):
                    checker.check_fixture_schema(fixtures)

    def test_mutated_scrollable_contract_is_reported_as_usability_failure(self) -> None:
        fixtures = copy.deepcopy(self.fixtures)
        jc = next(entry for entry in fixtures["layouts"] if entry["slug"] == "guition-jc4827w543r")
        # Deliberately make the contract impossible. This exercises the
        # diagnostic path without depending on any currently known production
        # Back-target or rotated-tab failures remaining unfixed.
        jc["coverage"]["scrollableMinimumHeight"] = 10_000
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = checker.compile_layout_contract(fixtures)

        text = output.getvalue()
        self.assertNotEqual(result, 0)
        self.assertIn(
            "USABILITY FAIL: guition-jc4827w543r normal rotation 0 media speaker content "
            "scrollable row minimum",
            text,
        )
        self.assertIn("USABILITY FAIL", text)

    def test_mutated_snapshot_is_reported_as_snapshot_failure(self) -> None:
        fixtures = copy.deepcopy(self.fixtures)
        jc = next(entry for entry in fixtures["layouts"] if entry["slug"] == "guition-jc4827w543r")
        jc["expected"]["back"]["size"] += 1
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = checker.compile_layout_contract(fixtures)

        text = output.getvalue()
        self.assertNotEqual(result, 0)
        self.assertIn("SNAPSHOT FAIL: guition-jc4827w543r normal rotation 0 snapshot back size", text)
        self.assertIn("SNAPSHOT FAIL", text)


if __name__ == "__main__":
    unittest.main()
