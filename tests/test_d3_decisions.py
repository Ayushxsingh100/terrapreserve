"""docs/D3_DECISIONS.md records D3-01..D3-12 with the status the work package gave them (acceptance A1)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS = REPO_ROOT / "docs" / "D3_DECISIONS.md"

# Written by hand from the work package: 01-03 were decided by the user, 04-12 are proposals.
EXPECTED_STATUS = {f"D3-{n:02d}": "Decided" for n in (1, 2, 3)} | {f"D3-{n:02d}": "Proposed" for n in range(4, 13)}


def parse_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and re.fullmatch(r"D3-\d\d", cells[0]):
            rows[cells[0]] = cells
    return rows


class TestDecisionsRecord(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = parse_rows(DECISIONS.read_text(encoding="utf-8"))

    def test_every_decision_is_present_exactly_once(self) -> None:
        self.assertEqual(sorted(self.rows), sorted(EXPECTED_STATUS))

    def test_status_matches_the_work_package(self) -> None:
        got = {k: v[2] for k, v in self.rows.items()}
        self.assertEqual(got, EXPECTED_STATUS)

    def test_every_row_has_a_reason_and_a_source(self) -> None:
        for key, cells in self.rows.items():
            with self.subTest(decision=key):
                self.assertEqual(len(cells), 5)
                self.assertTrue(cells[3], "reason is empty")
                self.assertTrue(cells[4], "rests-on is empty")

    def test_parser_catches_a_missing_row(self) -> None:
        text = DECISIONS.read_text(encoding="utf-8").replace("| D3-07 |", "| D3-0X |")
        self.assertNotIn("D3-07", parse_rows(text))


if __name__ == "__main__":
    unittest.main()
