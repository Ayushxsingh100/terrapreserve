"""Tests for the D4b decisions record (Step 1).

Checks that docs/D4B_DECISIONS.md exists, has the required rows, statuses, and parseable table.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS_FILE = REPO_ROOT / "docs" / "D4B_DECISIONS.md"

REQUIRED_IDS = [
    "D4-01", "D4-02",
    "D4b-01", "D4b-02", "D4b-03", "D4b-04", "D4b-05", "D4b-06",
    "D4b-07", "D4b-08", "D4b-09", "D4b-10", "D4b-11", "D4b-12",
]
DECIDED_IDS = {"D4-01", "D4-02"}
PROPOSED_IDS = {
    "D4b-01", "D4b-02", "D4b-03", "D4b-04", "D4b-05", "D4b-06",
    "D4b-07", "D4b-08", "D4b-09", "D4b-10", "D4b-11", "D4b-12",
}


def _parse_table(text: str) -> dict[str, dict[str, str]]:
    """Parse markdown tables; return {id: {column: value}} for decision rows."""
    rows: dict[str, dict[str, str]] = {}
    header: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            header = []
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


class TestD4bDecisionsFile(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DECISIONS_FILE.is_file(), "docs/D4B_DECISIONS.md must exist")
        self.text = DECISIONS_FILE.read_text(encoding="utf-8")
        self.rows = _parse_table(self.text)

    def test_all_required_ids_present(self) -> None:
        for id_ in REQUIRED_IDS:
            with self.subTest(id=id_):
                self.assertIn(id_, self.rows, f"Row {id_} missing from D4B_DECISIONS.md")

    def test_decided_rows_have_decided_status(self) -> None:
        for id_ in DECIDED_IDS:
            with self.subTest(id=id_):
                row = self.rows.get(id_, {})
                status = row.get("Status", "")
                self.assertEqual(status, "Decided", f"Row {id_} status should be 'Decided', got {status!r}")

    def test_proposed_rows_have_proposed_status(self) -> None:
        for id_ in PROPOSED_IDS:
            with self.subTest(id=id_):
                row = self.rows.get(id_, {})
                status = row.get("Status", "")
                self.assertEqual(status, "Proposed", f"Row {id_} status should be 'Proposed', got {status!r}")

    def test_no_other_rows_are_decided(self) -> None:
        """Only user-decided items D4-01 and D4-02 may carry 'Decided'."""
        for id_, row in self.rows.items():
            if row.get("Status", "").lower() == "decided":
                self.assertIn(id_, DECIDED_IDS, f"Row {id_} cannot be Decided; not a user decision")

    def test_open_rows_present(self) -> None:
        """There must be at least two Open rows (Graft attachment and Invariant scope)."""
        open_rows = {k: v for k, v in self.rows.items() if v.get("Status", "").lower() == "open"}
        self.assertGreaterEqual(len(open_rows), 2, "At least two Open rows must exist")
        open_keys = " ".join(open_rows.keys())
        self.assertTrue("Open 1" in open_keys or "open" in open_keys.lower())

    def test_measured_at_start_table_present(self) -> None:
        """The document must contain a 'Measured at start' table with baseline metrics."""
        self.assertIn("Measured at start", self.text)
        self.assertIn("400", self.text)  # 400 hosts
        self.assertIn("402", self.text)  # 402 entries
        self.assertIn("120", self.text)  # 120 E09

    def test_no_pipe_in_cells(self) -> None:
        """Cells must not contain pipe characters (mechanical parseability)."""
        for id_, row in self.rows.items():
            for col, val in row.items():
                self.assertNotIn("|", val, f"Row {id_} column {col!r} contains an unescaped pipe character")

    def test_lf_only(self) -> None:
        raw = DECISIONS_FILE.read_bytes()
        self.assertNotIn(b"\r\n", raw, "D4B_DECISIONS.md must use LF line endings only")


if __name__ == "__main__":
    unittest.main()
