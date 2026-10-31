"""Tests for the controlled tier scenario generation and validation (Step 5; A4, A5, A6, D4-04).

Tests:
1. Total controlled scenarios plan = 208 (160 targets + 48 reserves).
2. Exactly 16 cells (8 families x 2 classes), each having 13 scenarios (10 target, 3 reserve).
3. Every template (tpl-01..tpl-10) is instantiated in every cell.
4. Dev split scenarios are committed under scenarios/dev/; no test scenario is under scenarios/dev/.
5. scenarios/validate_results.csv exists, is well-formed, and has zero invalid/error steps.
6. scenarios/test_manifest.json exists and contains ids and hashes only.
7. Total committed size of scenarios/ does not exceed 40 MiB; no single file exceeds 5 MiB.
"""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestControlledTierPlan(unittest.TestCase):
    def _get_gen_module(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "sources"))
        sys.path.insert(0, str(REPO_ROOT / "pool"))
        sys.path.insert(0, str(REPO_ROOT / "generator"))
        import generate
        return generate

    def test_plan_counts_and_cells(self) -> None:
        gen = self._get_gen_module()
        plan = gen.build_scenario_plan()

        self.assertEqual(len(plan), 208)

        # Count targets and reserves
        targets = [p for p in plan if not p["reserve"]]
        reserves = [p for p in plan if p["reserve"]]
        self.assertEqual(len(targets), 160)
        self.assertEqual(len(reserves), 48)

        # Check cells
        cells: dict[tuple[str, str], list[dict]] = {}
        for p in plan:
            cells.setdefault((p["family"], p["cls"]), []).append(p)

        self.assertEqual(len(cells), 16)
        for (fam, cls), items in cells.items():
            with self.subTest(family=fam, cls=cls):
                self.assertEqual(len(items), 13)
                cell_targets = [it for it in items if not it["reserve"]]
                cell_reserves = [it for it in items if it["reserve"]]
                self.assertEqual(len(cell_targets), 10)
                self.assertEqual(len(cell_reserves), 3)

                # All 10 templates must occur in target scenarios
                target_tpls = {it["template_id"] for it in cell_targets}
                self.assertEqual(len(target_tpls), 10)

    def test_reserves_cover_all_ten_templates(self) -> None:
        gen = self._get_gen_module()
        plan = gen.build_scenario_plan()
        reserves = [p for p in plan if p["reserve"]]
        self.assertEqual(len(reserves), 48)

        reserve_tpls = {p["template_id"] for p in reserves}
        all_tpls = {f"tpl-{i:02d}" for i in range(1, 11)}
        self.assertEqual(reserve_tpls, all_tpls, f"Reserves must cover all 10 templates, missing: {all_tpls - reserve_tpls}")

        # Check each template appears in reserves at least 3 times
        tpl_counts = {}
        for p in reserves:
            tpl_counts[p["template_id"]] = tpl_counts.get(p["template_id"], 0) + 1
        for tpl_id in all_tpls:
            self.assertGreaterEqual(tpl_counts.get(tpl_id, 0), 3, f"Template {tpl_id} has only {tpl_counts.get(tpl_id, 0)} reserves")

    def test_every_cell_has_reserves_in_both_splits(self) -> None:
        gen = self._get_gen_module()
        plan = gen.build_scenario_plan()
        cells: dict[tuple[str, str], list[dict]] = {}
        for p in plan:
            cells.setdefault((p["family"], p["cls"]), []).append(p)

        for (fam, cls), items in cells.items():
            cell_reserves = [it for it in items if it["reserve"]]
            with self.subTest(family=fam, cls=cls):
                self.assertEqual(len(cell_reserves), 3)
                dev_res = [r for r in cell_reserves if r["split"] == "dev"]
                test_res = [r for r in cell_reserves if r["split"] == "test"]
                self.assertGreater(len(dev_res), 0, f"Cell ({fam}, {cls}) has no dev reserves")
                self.assertGreater(len(test_res), 0, f"Cell ({fam}, {cls}) has no test reserves")
                # 2 dev and 1 test per cell (about 70/30)
                self.assertEqual(len(dev_res), 2)
                self.assertEqual(len(test_res), 1)

    def test_global_scenario_ids_are_strictly_monotonic_and_stable(self) -> None:
        gen = self._get_gen_module()
        plan = gen.build_scenario_plan()
        ids = [p["global_id"] for p in plan]
        self.assertEqual(ids, list(range(1, 209)))


class TestControlledTierOutput(unittest.TestCase):
    def test_test_manifest_exists_and_clean(self) -> None:
        manifest_path = REPO_ROOT / "scenarios" / "test_manifest.json"
        if not manifest_path.is_file():
            self.skipTest("scenarios/test_manifest.json not yet generated")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertGreater(len(manifest), 0)
        forbidden_keys = {"family", "class", "intent", "template", "template_id", "gt_class", "diff"}
        for entry in manifest:
            self.assertIn("scenario_id", entry)
            self.assertIn("scenario_json_sha256", entry)
            self.assertIn("steps", entry)
            for k in entry:
                self.assertNotIn(k, forbidden_keys)

    def test_dev_directory_holds_only_dev_scenarios(self) -> None:
        dev_dir = REPO_ROOT / "scenarios" / "dev"
        if not dev_dir.is_dir():
            self.skipTest("scenarios/dev/ not yet generated")
        split_info = json.loads((REPO_ROOT / "scenarios" / "split.json").read_text(encoding="utf-8"))
        dev_tpls = set(split_info["dev_templates"])
        test_tpls = set(split_info["test_templates"])

        dev_scenarios = [p for p in dev_dir.glob("tp-v1-*") if int(p.name.split("-")[-1]) <= 208]
        self.assertGreater(len(dev_scenarios), 0)
        for sc_path in dev_scenarios:
            manifest_file = sc_path / "scenario.json"
            self.assertTrue(manifest_file.is_file())
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("split"), "dev")
            self.assertIn(data.get("template_id"), dev_tpls)
            self.assertNotIn(data.get("template_id"), test_tpls)

    def test_validate_results_csv(self) -> None:
        val_csv = REPO_ROOT / "scenarios" / "validate_results.csv"
        if not val_csv.is_file():
            self.skipTest("scenarios/validate_results.csv not yet generated")
        with open(val_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertGreater(len(rows), 0)
        for r in rows:
            self.assertEqual(r["status"], "valid", f"Scenario step failed validation: {r}")

    def test_size_bounds(self) -> None:
        scenarios_dir = REPO_ROOT / "scenarios"
        total_bytes = 0
        max_file_bytes = 5 * 1024 * 1024  # 5 MiB
        for p in scenarios_dir.rglob("*"):
            if p.is_file():
                sz = p.stat().st_size
                self.assertLessEqual(sz, max_file_bytes, f"File {p} exceeds 5 MiB: {sz} bytes")
                total_bytes += sz
        # Total committed size under 40 MiB
        self.assertLessEqual(total_bytes, 40 * 1024 * 1024)

    def test_generator_determinism_two_runs_byte_identical(self) -> None:
        import sys
        sys.path.insert(0, str(REPO_ROOT / "sources"))
        sys.path.insert(0, str(REPO_ROOT / "pool"))
        sys.path.insert(0, str(REPO_ROOT / "generator"))
        import generate
        import writer

        plan = generate.build_scenario_plan()
        # Verify across a representative sample of all 16 cells (one per cell)
        sample_items = [p for p in plan if p["cell_index"] == 0]
        self.assertEqual(len(sample_items), 16)

        for item in sample_items:
            # Run 1
            data1, steps1, records1 = generate.generate_scenario(item)
            json1 = writer.canonical_json(data1)

            # Run 2
            data2, steps2, records2 = generate.generate_scenario(item)
            json2 = writer.canonical_json(data2)

            self.assertEqual(json1, json2, f"Scenario {item['global_id']} JSON not identical across runs")
            self.assertEqual(steps1, steps2, f"Scenario {item['global_id']} step files not identical across runs")
            self.assertEqual(records1, records2, f"Scenario {item['global_id']} mutation records not identical across runs")

    def test_full_dev_tree_determinism_byte_identical_across_runs(self) -> None:
        """A8: Two independent full writes of all 144 dev scenarios produce byte-identical file trees."""
        import tempfile
        import sys
        sys.path.insert(0, str(REPO_ROOT / "sources"))
        sys.path.insert(0, str(REPO_ROOT / "pool"))
        sys.path.insert(0, str(REPO_ROOT / "generator"))
        import generate
        import writer

        plan = generate.build_scenario_plan()
        dev_items = [p for p in plan if p["split"] == "dev"]
        self.assertEqual(len(dev_items), 144)

        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            root1 = Path(tmp1)
            root2 = Path(tmp2)

            for item in dev_items:
                data1, steps1, _ = generate.generate_scenario(item)
                writer.write_dev_scenario(root1, data1, steps1)

                data2, steps2, _ = generate.generate_scenario(item)
                writer.write_dev_scenario(root2, data2, steps2)

            # Compare all files
            files1 = {p.relative_to(root1): p for p in root1.rglob("*") if p.is_file()}
            files2 = {p.relative_to(root2): p for p in root2.rglob("*") if p.is_file()}

            self.assertEqual(set(files1.keys()), set(files2.keys()))
            self.assertEqual(len(files1), 1128)  # Exactly 1128 files across 144 dev scenarios

            for rel_path, path1 in files1.items():
                bytes1 = path1.read_bytes()
                bytes2 = files2[rel_path].read_bytes()
                self.assertEqual(bytes1, bytes2, f"File {rel_path} differed between runs")


if __name__ == "__main__":
    unittest.main()

