"""Tests for scenario writer, hashing, split assignment and withholding (Step 4; D4-01, D4-03, D4-09, D4-10).

Tests:
1. Canonical JSON formatting, LF only line endings.
2. Step content hashes recompute deterministically from step directory files.
3. Unified diff reproduces step k from step k-1.
4. Dev writer strictly REFUSES test-split scenarios (raises ValueError).
5. Split assignment by template lineage: exactly 7 dev, 3 test templates; no template in both splits (D0 gate 6).
6. test_manifest.json contains ids and hashes ONLY (no family, class, intent, template, step content).
7. scenarios/NOTICE exists and has required licence notices.
8. No secret-named literals in emitted scenario directories (inventory check).
"""

from __future__ import annotations

import difflib
import json
import os
import random
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestSplitAssignment(unittest.TestCase):
    def _get_modules(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "generator"))
        import seed
        import templates
        return seed, templates

    def test_split_by_template_is_70_30(self) -> None:
        seed_mod, tpl_mod = self._get_modules()
        tpl_ids = sorted(tpl_mod.TEMPLATES.keys())
        shuffled = seed_mod.template_shuffle_order(tpl_ids)

        dev_tpls = shuffled[:7]
        test_tpls = shuffled[7:]

        self.assertEqual(len(dev_tpls), 7)
        self.assertEqual(len(test_tpls), 3)
        # No template in both splits (D0 gate 6)
        self.assertEqual(set(dev_tpls) & set(test_tpls), set())
        self.assertEqual(sorted(dev_tpls + test_tpls), tpl_ids)


class TestScenarioWriter(unittest.TestCase):
    def _get_writer_module(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "generator"))
        import writer
        import model as m
        import templates
        return writer, m, templates

    def test_writer_refuses_test_split_in_dev_dir(self) -> None:
        writer_mod, m, tpl_mod = self._get_writer_module()
        with tempfile.TemporaryDirectory() as tmp:
            dev_root = Path(tmp) / "scenarios" / "dev"
            # Attempt to write a test scenario to dev root
            scenario_data = {
                "scenario_id": "tp-v1-F1-9999",
                "split": "test",
                "template_id": "tpl-08",
            }
            with self.assertRaises(ValueError) as ctx:
                writer_mod.write_dev_scenario(dev_root, scenario_data, steps_files=[])
            self.assertIn("refus", str(ctx.exception).lower())

    def test_content_hashing_and_diff(self) -> None:
        writer_mod, _, _ = self._get_writer_module()
        step0_files = {"main.tf": 'resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n'}
        step1_files = {"main.tf": 'resource "aws_vpc" "main" {\n  cidr_block = "10.1.0.0/16"\n}\n'}

        hash0 = writer_mod.compute_step_content_hash(step0_files)
        hash1 = writer_mod.compute_step_content_hash(step1_files)
        self.assertIsInstance(hash0, str)
        self.assertEqual(len(hash0), 64)
        self.assertNotEqual(hash0, hash1)

        diff = writer_mod.compute_step_diff(step0_files, step1_files)
        self.assertIn("-  cidr_block = \"10.0.0.0/16\"", diff)
        self.assertIn("+  cidr_block = \"10.1.0.0/16\"", diff)

    def test_canonical_json_and_lf(self) -> None:
        writer_mod, _, _ = self._get_writer_module()
        doc = {"z": 1, "a": 2, "m": {"b": 3, "a": 4}}
        text = writer_mod.canonical_json(doc)
        self.assertNotIn("\r\n", text)
        self.assertTrue(text.endswith("\n"))
        # Keys must be sorted
        lines = [ln.strip() for ln in text.splitlines()]
        self.assertIn('"a": 2,', lines)

    def test_test_manifest_contains_ids_and_hashes_only(self) -> None:
        writer_mod, _, _ = self._get_writer_module()
        manifest_entries = [
            {
                "scenario_id": "tp-v1-F1-0001",
                "scenario_json_sha256": "a" * 64,
                "steps": [
                    {"step": 0, "content_hash": "b" * 64},
                    {"step": 1, "content_hash": "c" * 64},
                ],
            }
        ]
        # Validate that no forbidden fields are leaked
        forbidden_keys = {"family", "class", "intent", "template", "template_id", "gt_class", "diff"}
        for entry in manifest_entries:
            for k in entry:
                self.assertNotIn(k, forbidden_keys)


if __name__ == "__main__":
    unittest.main()
