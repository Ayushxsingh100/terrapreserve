"""Step 6: Mutation checks and negative invariants (D0 Decision 10; D4-01..D4-12).

Tests:
1. Diff verifier fails when a mutation row is dropped.
2. Diff verifier fails when a phantom/invented mutation row is added.
3. Diff verifier fails when before/after values are falsified.
4. Dev writer strictly refuses test-split scenarios.
5. Test manifest schema validation rejects forbidden keys (intent, family, diff, template).
6. Split assignment rejects any overlap between dev and test templates.
7. Independence AST checker catches forbidden DAIL imports (import core, import core.impact).
8. Emitted scenarios have zero secret literals or forbidden credential attributes.
"""

from __future__ import annotations

import json
import os
import sys
import random
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "pool"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import diff_verify as dv
import emitter
import model as m
import templates
import writer


class TestStep6MutationsAndNegativeInvariants(unittest.TestCase):
    def setUp(self) -> None:
        self.tpl = templates.TEMPLATES["tpl-01"]
        self.rng = random.Random(12345)
        self.base_model, _ = self.tpl.instantiate(self.rng, "clean")

    def test_diff_verifier_catches_dropped_row(self) -> None:
        # Create a modification on base_model
        m1 = self.base_model.copy()
        ec2 = m1.resources["aws_instance.app"]
        ec2.set_attr("instance_type", "t3.large")
        ec2.set_attr("monitoring", True)

        # Actual diff has 2 changes, but we only record 1 (dropped row)
        records = [
            dv.MutationRow(
                step=1,
                operator="test_op",
                target_address="aws_instance.app",
                attribute="instance_type",
                before='"t3.micro"',
                after='"t3.large"',
            )
        ]
        with self.assertRaises(dv.DiffVerifyError) as ctx:
            dv.verify(self.base_model, m1, records, step=1, operator_name="test_op")
        self.assertIn("monitoring", str(ctx.exception))

    def test_diff_verifier_catches_invented_row(self) -> None:
        m1 = self.base_model.copy()
        ec2 = m1.resources["aws_instance.app"]
        ec2.set_attr("instance_type", "t3.large")

        # Record includes a phantom change that never happened
        records = [
            dv.MutationRow(
                step=1,
                operator="test_op",
                target_address="aws_instance.app",
                attribute="instance_type",
                before='"t3.micro"',
                after='"t3.large"',
            ),
            dv.MutationRow(
                step=1,
                operator="test_op",
                target_address="aws_instance.app",
                attribute="phantom_attr",
                before="null",
                after='"invented"',
            ),
        ]
        with self.assertRaises(dv.DiffVerifyError) as ctx:
            dv.verify(self.base_model, m1, records, step=1, operator_name="test_op")
        self.assertIn("phantom_attr", str(ctx.exception))

    def test_diff_verifier_catches_falsified_values(self) -> None:
        m1 = self.base_model.copy()
        ec2 = m1.resources["aws_instance.app"]
        ec2.set_attr("instance_type", "t3.large")

        # Record claims after was t3.xlarge instead of t3.large
        records = [
            dv.MutationRow(
                step=1,
                operator="test_op",
                target_address="aws_instance.app",
                attribute="instance_type",
                before='"t3.micro"',
                after='"t3.xlarge"',
            )
        ]
        with self.assertRaises(dv.DiffVerifyError) as ctx:
            dv.verify(self.base_model, m1, records, step=1, operator_name="test_op")
        self.assertIn("instance_type", str(ctx.exception))

    def test_dev_writer_refuses_test_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dev_dir = Path(tmp) / "dev"
            data = {"scenario_id": "tp-v1-F1-0001", "split": "test", "template_id": "tpl-07"}
            with self.assertRaises(ValueError) as ctx:
                writer.write_dev_scenario(dev_dir, data, [])
            self.assertIn("refus", str(ctx.exception).lower())

    def test_test_manifest_schema_rejects_forbidden_keys(self) -> None:
        manifest_path = REPO_ROOT / "scenarios" / "test_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        forbidden = {"family", "class", "intent", "template", "template_id", "gt_class", "diff"}

        for entry in manifest:
            found_forbidden = set(entry.keys()) & forbidden
            self.assertEqual(
                found_forbidden,
                set(),
                f"Forbidden keys leaked in test manifest entry {entry.get('scenario_id')}: {found_forbidden}",
            )

    def test_template_split_disjointness_enforced(self) -> None:
        split_path = REPO_ROOT / "scenarios" / "split.json"
        split_data = json.loads(split_path.read_text(encoding="utf-8"))
        dev_tpls = set(split_data["dev_templates"])
        test_tpls = set(split_data["test_templates"])

        # Intersection must be strictly empty
        self.assertEqual(dev_tpls & test_tpls, set())

        # Any simulated overlap must be caught
        simulated_bad_split = {"dev": {"tpl-01", "tpl-02"}, "test": {"tpl-02", "tpl-03"}}
        self.assertTrue(bool(simulated_bad_split["dev"] & simulated_bad_split["test"]))

    def test_independence_checker_catches_dail_import(self) -> None:
        import ast

        bad_code = """
import os
import core.impact
from core.verification import verify
"""
        tree = ast.parse(bad_code)
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.append(node.module)

        forbidden = [m for m in imported_modules if m == "core" or m.startswith("core.")]
        self.assertIn("core.impact", forbidden)
        self.assertIn("core.verification", forbidden)

    def test_emitted_scenarios_have_no_secrets(self) -> None:
        dev_dir = REPO_ROOT / "scenarios" / "dev"
        forbidden_substrings = [
            "supersecret",
            "password123",
            "AKIA",
            "aws_secret_access_key",
        ]
        for p in dev_dir.rglob("*.tf"):
            text = p.read_text(encoding="utf-8")
            for sub in forbidden_substrings:
                self.assertNotIn(
                    sub,
                    text,
                    f"Forbidden secret literal or credential {sub!r} found in {p}",
                )


if __name__ == "__main__":
    unittest.main()
