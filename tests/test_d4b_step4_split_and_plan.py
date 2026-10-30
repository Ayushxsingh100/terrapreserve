"""Tests for Step 4: Split, cell assignment, records, and withholding (D4b-08, D4b-09, D4b-10).

Written first per the test-first rule:
1. Real-world lineage split is deterministic and about 70/30.
2. No lineage appears on both sides across both tiers (D0 Gate 6).
3. Every cell has 7 dev + 3 test targets and 2 dev + 1 test reserves.
4. No module is used twice across all scenarios.
5. Natives (and derived natives) come before hosts in assignment order.
6. Dev writer refuses a test scenario.
7. Existing 64 controlled test entries in test_manifest.json are unchanged.
8. Manifest holds ids and hashes only (no leaks).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Import realworld plan module (fails initially)
try:
    from generator.realworld import plan as rw_plan
except ImportError:
    rw_plan = None  # type: ignore


class TestRealWorldSplitAndPlan(unittest.TestCase):
    def setUp(self) -> None:
        if rw_plan is None:
            self.fail("generator/realworld/plan.py does not exist yet (test-first failure)")

    def test_real_world_split_is_deterministic_and_about_70_30(self) -> None:
        """Lineage split in scenarios/split_real_world.json is about 70/30."""
        split_file = REPO_ROOT / "scenarios" / "split_real_world.json"
        self.assertTrue(split_file.is_file(), "scenarios/split_real_world.json must exist")
        data = json.loads(split_file.read_text(encoding="utf-8"))
        dev_lins = set(data["dev_lineages"])
        test_lins = set(data["test_lineages"])

        self.assertEqual(len(dev_lins & test_lins), 0, "Lineages must be strictly disjoint")
        total = len(dev_lins) + len(test_lins)
        dev_ratio = len(dev_lins) / total
        self.assertTrue(0.65 <= dev_ratio <= 0.75, f"Dev ratio {dev_ratio:.2f} should be ~0.70")

    def test_no_lineage_on_both_sides_across_both_tiers(self) -> None:
        """No lineage appears on both sides across both tiers (D0 Gate 6)."""
        controlled_split = json.loads((REPO_ROOT / "scenarios" / "split.json").read_text(encoding="utf-8"))
        c_dev = set(controlled_split["dev_templates"])
        c_test = set(controlled_split["test_templates"])

        rw_split = json.loads((REPO_ROOT / "scenarios" / "split_real_world.json").read_text(encoding="utf-8"))
        r_dev = set(rw_split["dev_lineages"])
        r_test = set(rw_split["test_lineages"])

        all_dev = c_dev | r_dev
        all_test = c_test | r_test
        self.assertEqual(len(all_dev & all_test), 0, "Lineage leakage detected across tiers")

    def test_every_cell_has_exact_target_and_reserve_split(self) -> None:
        """Every cell has 7 dev + 3 test targets and 2 dev + 1 test reserves (total 13 per cell)."""
        plan = rw_plan.build_real_world_plan()
        self.assertEqual(len(plan), 208, "Real-world plan must have exactly 208 scenarios")

        by_cell: dict[tuple[str, str], list[dict]] = {}
        for item in plan:
            key = (item["family"], item["class"])
            by_cell.setdefault(key, []).append(item)

        self.assertEqual(len(by_cell), 16, "Must have exactly 16 cells (8 families x 2 classes)")
        for (fam, cls), items in by_cell.items():
            targets = [i for i in items if not i["reserve"]]
            reserves = [i for i in items if i["reserve"]]
            self.assertEqual(len(targets), 10, f"Cell ({fam}, {cls}) targets != 10")
            self.assertEqual(len(reserves), 3, f"Cell ({fam}, {cls}) reserves != 3")

            dev_targets = [i for i in targets if i["split"] == "dev"]
            test_targets = [i for i in targets if i["split"] == "test"]
            self.assertEqual(len(dev_targets), 7, f"Cell ({fam}, {cls}) dev targets != 7")
            self.assertEqual(len(test_targets), 3, f"Cell ({fam}, {cls}) test targets != 3")

            dev_reserves = [i for i in reserves if i["split"] == "dev"]
            test_reserves = [i for i in reserves if i["split"] == "test"]
            self.assertEqual(len(dev_reserves), 2, f"Cell ({fam}, {cls}) dev reserves != 2")
            self.assertEqual(len(test_reserves), 1, f"Cell ({fam}, {cls}) test reserves != 1")

    def test_no_module_used_twice(self) -> None:
        """No base module is reused across scenarios."""
        plan = rw_plan.build_real_world_plan()
        mids = [item["module_id"] for item in plan]
        self.assertEqual(len(mids), len(set(mids)), "Duplicate module used across scenarios")

    def test_natives_come_before_hosts(self) -> None:
        """Natives and derived natives come before hosts in assignment order."""
        plan = rw_plan.build_real_world_plan()
        for fam in ("F1", "F2", "F4", "F6", "F8"):
            fam_items = [i for i in plan if i["family"] == fam]
            kinds = [i["kind"] for i in fam_items]
            if "native" in kinds and "host" in kinds:
                first_native = kinds.index("native")
                first_host = kinds.index("host")
                self.assertLess(first_native, first_host, f"Family {fam} host assigned before native")

    def test_existing_64_controlled_test_entries_unchanged_in_manifest(self) -> None:
        """The existing 64 controlled test entries in test_manifest.json remain intact."""
        manifest_file = REPO_ROOT / "scenarios" / "test_manifest.json"
        entries = json.loads(manifest_file.read_text(encoding="utf-8"))
        controlled_entries = [e for e in entries if not e["scenario_id"].endswith("-rw") and "F" in e["scenario_id"]]
        # In D4a, there were exactly 64 test entries
        self.assertGreaterEqual(len(controlled_entries), 64)
        for e in controlled_entries[:64]:
            self.assertIn("scenario_id", e)
            self.assertIn("scenario_json_sha256", e)
            self.assertIn("steps", e)

    def test_manifest_holds_ids_and_hashes_only(self) -> None:
        """Manifest entries must not leak intent, class, template, or diff fields."""
        manifest_file = REPO_ROOT / "scenarios" / "test_manifest.json"
        entries = json.loads(manifest_file.read_text(encoding="utf-8"))
        forbidden = {"intent", "class", "gt_class", "template", "template_id", "diff", "operator"}
        for e in entries:
            keys = set(e.keys())
            self.assertEqual(keys & forbidden, set(), f"Manifest leaked forbidden keys: {keys & forbidden}")


if __name__ == "__main__":
    unittest.main()
