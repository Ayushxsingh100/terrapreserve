"""Large raw archives are never committed (CLAUDE.md rule 6)."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 5 * 1024 * 1024
FORBIDDEN_SUFFIXES = (".tar.gz", ".tgz", ".zip", ".sqlite", ".sqlite3", ".db", ".tfstate", ".tfplan")


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return [name for name in result.stdout.decode("utf-8").split("\0") if name]


class TestNoLargeOrRawFiles(unittest.TestCase):
    def test_no_tracked_file_over_5_mb(self) -> None:
        too_big = []
        for name in tracked_files():
            path = REPO_ROOT / name
            if path.is_file() and path.stat().st_size > MAX_BYTES:
                too_big.append(f"{name} ({path.stat().st_size} bytes)")
        self.assertEqual(too_big, [])

    def test_no_tracked_archive_database_or_state_file(self) -> None:
        raw = [n for n in tracked_files() if n.lower().endswith(FORBIDDEN_SUFFIXES)]
        self.assertEqual(raw, [])

    def test_tracked_file_list_is_not_empty(self) -> None:
        self.assertIn("LICENSE", tracked_files())


if __name__ == "__main__":
    unittest.main()
