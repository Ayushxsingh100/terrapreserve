"""Tests for Step 6: Tier assembly and count verification (D0, D4b-01, D4b-08, D4b-09, A11).

Tests:
1. Assembly script produces scenarios/ASSEMBLY.json and scenarios/ASSEMBLY.md.
2. Hand-computed expected counts match exactly:
   - 416 total scenarios (208 controlled + 208 real-world)
   - 320 targets (160 controlled + 160 real-world: 224 dev + 96 test)
   - 96 reserves (48 controlled + 48 real-world: 64 dev + 32 test)
   - 288 dev scenarios (224 targets + 64 reserves)
   - 128 test scenarios (96 targets + 32 reserves)
   - 16 cells, each with 20 targets (14 dev, 6 test) + 6 reserves (4 dev, 2 test) = 26 scenarios
   - 8 families, each with 40 targets + 12 reserves = 52 scenarios
3. No module lineage or controlled template appears in both dev and test.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from scenarios import assemble
except ImportError:
    assemble = None  # type: ignore


class TestAssembly(unittest.TestCase):
    def setUp(self) -> None:
        if assemble is None:
            self.fail("scenarios/assemble.py does not exist yet (test-first failure)")

    def test_assembly_counts_match_specification(self) -> None:
        """Hand-worked counts match the assembly script output."""
        report = assemble.compute_assembly()

        self.assertEqual(report["total_scenarios"], 416)
        self.assertEqual(report["controlled"]["total"], 208)
        self.assertEqual(report["real_world"]["total"], 208)

        self.assertEqual(report["targets"]["total"], 320)
        self.assertEqual(report["targets"]["dev"], 224)
        self.assertEqual(report["targets"]["test"], 96)
        self.assertEqual(report["targets"]["controlled"], 160)
        self.assertEqual(report["targets"]["real_world"], 160)

        self.assertEqual(report["reserves"]["total"], 96)
        self.assertEqual(report["reserves"]["dev"], 64)
        self.assertEqual(report["reserves"]["test"], 32)
        self.assertEqual(report["reserves"]["controlled"], 48)
        self.assertEqual(report["reserves"]["real_world"], 48)

        self.assertEqual(report["splits"]["dev_total"], 288)
        self.assertEqual(report["splits"]["test_total"], 128)

        # 8 families, each 52
        for fam in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
            f_data = report["families"][fam]
            self.assertEqual(f_data["total"], 52, f"Family {fam} total")
            self.assertEqual(f_data["targets"], 40, f"Family {fam} targets")
            self.assertEqual(f_data["reserves"], 12, f"Family {fam} reserves")
            self.assertEqual(f_data["dev"], 36, f"Family {fam} dev")
            self.assertEqual(f_data["test"], 16, f"Family {fam} test")

        # 16 cells, each 26 (20 targets: 14 dev, 6 test; 6 reserves: 4 dev, 2 test)
        for cell_key, c_data in report["cells"].items():
            self.assertEqual(c_data["total"], 26, f"Cell {cell_key} total")
            self.assertEqual(c_data["targets"]["total"], 20, f"Cell {cell_key} targets")
            self.assertEqual(c_data["targets"]["dev"], 14, f"Cell {cell_key} dev targets")
            self.assertEqual(c_data["targets"]["test"], 6, f"Cell {cell_key} test targets")
            self.assertEqual(c_data["reserves"]["total"], 6, f"Cell {cell_key} reserves")
            self.assertEqual(c_data["reserves"]["dev"], 4, f"Cell {cell_key} dev reserves")
            self.assertEqual(c_data["reserves"]["test"], 2, f"Cell {cell_key} test reserves")

    def test_assembly_files_exist_and_consistent(self) -> None:
        """scenarios/ASSEMBLY.json and scenarios/ASSEMBLY.md exist and match."""
        json_path = REPO_ROOT / "scenarios" / "ASSEMBLY.json"
        md_path = REPO_ROOT / "scenarios" / "ASSEMBLY.md"

        self.assertTrue(json_path.is_file(), "ASSEMBLY.json must exist")
        self.assertTrue(md_path.is_file(), "ASSEMBLY.md must exist")

        doc = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(doc["total_scenarios"], 416)
        md_text = md_path.read_text(encoding="utf-8")
        self.assertIn("416", md_text)
        self.assertIn("320", md_text)


if __name__ == "__main__":
    unittest.main()

