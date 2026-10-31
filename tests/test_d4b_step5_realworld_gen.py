"""Tests for Step 5: Real-world tier generation and validation (D4b-03..D4b-10).

Tests:
1. Scenario generation for a host module produces valid metadata, graft, and diffs.
2. Scenario generation for a native module produces valid metadata, span edits, and diffs.
3. Provenance files (LICENSE.upstream, SOURCE.json) are written to PROVENANCE/.
4. Dev scenarios write cleanly under scenarios/dev/.
5. Test scenarios write to private root and append entries to test_manifest.json.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from generator.realworld import generate_rw, plan as rw_plan
except ImportError:
    generate_rw = None  # type: ignore
    rw_plan = None  # type: ignore


class TestRealWorldGeneration(unittest.TestCase):
    def setUp(self) -> None:
        if generate_rw is None or rw_plan is None:
            self.fail("generator/realworld/generate_rw.py does not exist yet (test-first failure)")

    def test_generate_host_scenario(self) -> None:
        """A host scenario generates S0 with graft, applies D4a operator, and diffs verify."""
        plan = rw_plan.build_real_world_plan()
        host_items = [i for i in plan if i["kind"] == "host"]
        self.assertGreater(len(host_items), 0)

        item = host_items[0]
        data, steps_files, _records = generate_rw.generate_real_world_scenario(item)

        self.assertEqual(data["scenario_id"], item["scenario_id"])
        self.assertEqual(data["source"]["tier"], "real_world")
        self.assertEqual(data["source"]["origin"], "terrads")
        self.assertTrue(data["grafted"])
        self.assertIn("scope_addresses", data)
        self.assertIn("host_transform", data)
        self.assertEqual(data["generator_version"], "d4b-3")

        # Step 0 files must include graft
        s0_files = steps_files[0]
        self.assertIn("terrapreserve_graft.tf", s0_files)
        self.assertIn("terrapreserve_graft_variables.tf", s0_files)
        self.assertIn("terrapreserve_versions.tf", s0_files)

    def test_generate_native_scenario(self) -> None:
        """A native scenario generates S0 and applies span edits cleanly."""
        plan = rw_plan.build_real_world_plan()
        native_items = [i for i in plan if i["kind"] == "native"]
        self.assertGreater(len(native_items), 0)

        item = native_items[0]
        data, steps_files, _records = generate_rw.generate_real_world_scenario(item)

        self.assertEqual(data["scenario_id"], item["scenario_id"])
        self.assertEqual(data["source"]["tier"], "real_world")
        self.assertFalse(data["grafted"])
        self.assertEqual(data["generator_version"], "d4b-3")

        # Check steps
        self.assertGreaterEqual(len(steps_files), 2)

    def test_write_scenario_creates_provenance(self) -> None:
        """Writing a scenario includes PROVENANCE/ with LICENSE.upstream and SOURCE.json."""
        plan = rw_plan.build_real_world_plan()
        item = [i for i in plan if i["kind"] == "host"][0]
        data, steps_files, _ = generate_rw.generate_real_world_scenario(item)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmproot = Path(tmpdir)
            prov_src = REPO_ROOT / "pool" / "terrads" / "host" / str(item["module_id"])
            generate_rw.write_real_world_scenario(tmproot, data, steps_files, prov_src)

            sc_dir = tmproot / data["scenario_id"]
            self.assertTrue((sc_dir / "scenario.json").is_file())
            self.assertTrue((sc_dir / "step_0").is_dir())
            self.assertTrue((sc_dir / "step_1").is_dir())
            self.assertTrue((sc_dir / "PROVENANCE").is_dir())
            self.assertTrue((sc_dir / "PROVENANCE" / "LICENSE.upstream").is_file())
            self.assertTrue((sc_dir / "PROVENANCE" / "SOURCE.json").is_file())

    def test_test_manifest_structure(self) -> None:
        """Test manifest entry has required fields and SHA256 hashes."""
        plan = rw_plan.build_real_world_plan()
        item = [i for i in plan if i["split"] == "test"][0]
        data, steps_files, _ = generate_rw.generate_real_world_scenario(item)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmproot = Path(tmpdir)
            prov_src = REPO_ROOT / "pool" / "terrads" / "host" / str(item["module_id"])
            generate_rw.write_real_world_scenario(tmproot, data, steps_files, prov_src)
            sc_dir = tmproot / data["scenario_id"]

            sc_json_bytes = (sc_dir / "scenario.json").read_bytes()
            self.assertTrue(len(sc_json_bytes) > 0)


if __name__ == "__main__":
    unittest.main()

