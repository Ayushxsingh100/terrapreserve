"""Tests for the D4 decisions record (Step 1).

Checks that D4_DECISIONS.md exists, has the required rows, and is parseable.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS_FILE = REPO_ROOT / "docs" / "D4_DECISIONS.md"

REQUIRED_IDS = [
    "D4-01", "D4-02", "D4-03", "D4-04", "D4-05",
    "D4-06", "D4-07", "D4-08", "D4-09", "D4-10",
    "D4-11", "D4-12",
]
# D4c-02 (user, 10 Nov 2026): the Proposed rows were settled as built; D4-03, D4-04 and D4-05, which describe the
# 10-template tier D4c-01 replaces, are Superseded by D4c rows (user, 10 Nov 2026).
REQUIRED_STATUSES = {"D4-01": "Decided", "D4-02": "Decided", "Open": "Decided",
                     **{f"D4-{n:02d}": "Decided" for n in range(6, 13)},
                     "D4-03": "Superseded", "D4-04": "Superseded", "D4-05": "Superseded"}
PROPOSED_IDS: set[str] = set()
SUPERSEDED_BY = {"D4-03": "Superseded by D4c-01", "D4-04": "Superseded by D4c-04", "D4-05": "Superseded by D4c-03"}
OPEN_TEXT = "F3 and F6"


def _parse_table(text: str) -> dict[str, dict[str, str]]:
    """Parse the markdown table; return {id: {column: value}}."""
    rows: dict[str, dict[str, str]] = {}
    header: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        parts = [p.strip() for p in stripped.strip("|").split("|")]
        if not header:
            header = parts
            in_table = True
            continue
        if re.match(r"^[-:| ]+$", stripped):
            continue  # separator row
        if in_table and header and len(parts) >= 2:
            row_id = parts[0]
            rows[row_id] = {header[i]: parts[i] for i in range(min(len(header), len(parts)))}
    return rows


class TestD4DecisionsFile(unittest.TestCase):
    def setUp(self) -> None:
        self.text = DECISIONS_FILE.read_text(encoding="utf-8")
        self.rows = _parse_table(self.text)

    def test_file_exists(self) -> None:
        self.assertTrue(DECISIONS_FILE.is_file(), "docs/D4_DECISIONS.md must exist")

    def test_all_required_ids_present(self) -> None:
        for id_ in REQUIRED_IDS:
            with self.subTest(id=id_):
                self.assertIn(id_, self.rows, f"Row {id_} missing from D4_DECISIONS.md")

    def test_decided_rows_have_decided_status(self) -> None:
        for id_, expected in REQUIRED_STATUSES.items():
            with self.subTest(id=id_):
                row = self.rows.get(id_, {})
                status = row.get("Status", "")
                self.assertEqual(status, expected, f"Row {id_} status should be {expected!r}, got {status!r}")

    def test_proposed_rows_have_proposed_status(self) -> None:
        for id_ in PROPOSED_IDS:
            with self.subTest(id=id_):
                row = self.rows.get(id_, {})
                status = row.get("Status", "")
                self.assertEqual(status, "Proposed", f"Row {id_} status should be Proposed, got {status!r}")

    def test_open_row_present(self) -> None:
        """The row for F3/F6 target kind is kept (settled as Decided by D4c-02, 10 Nov 2026)."""
        self.assertIn(OPEN_TEXT, self.text, "the F3/F6 target kind row must be present")
        self.assertIn("F3 and F6 are change requests, as generated", self.rows["Open"]["Reason"])
        open_rows = {k: v for k, v in self.rows.items() if v.get("Status", "").lower() == "open"}
        self.assertEqual(open_rows, {}, "no Open row remains (D4c-02)")

    def test_superseded_rows_point_to_d4c_and_keep_their_text(self) -> None:
        for id_, pointer in SUPERSEDED_BY.items():
            with self.subTest(id=id_):
                cell = self.rows[id_]["Decision"]
                self.assertTrue(cell.startswith(pointer), cell[:80])
                self.assertIn("Original text: ", cell)

    def test_no_pipe_in_cells(self) -> None:
        """Cells must not contain pipe characters (mechanical parseability)."""
        for id_, row in self.rows.items():
            for col, val in row.items():
                self.assertNotIn("|", val, f"Row {id_} column {col!r} contains a pipe character")

    def test_lf_only(self) -> None:
        raw = DECISIONS_FILE.read_bytes()
        self.assertNotIn(b"\r\n", raw, "D4_DECISIONS.md must use LF line endings only")

    def test_d4_decisions_is_tracked(self) -> None:
        import subprocess
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "docs/D4_DECISIONS.md"],
            cwd=REPO_ROOT, capture_output=True,
        )
        # If not yet committed, this will fail — that's acceptable at test-write time
        # but the file must exist on disk
        self.assertTrue(DECISIONS_FILE.is_file())


if __name__ == "__main__":
    unittest.main()

