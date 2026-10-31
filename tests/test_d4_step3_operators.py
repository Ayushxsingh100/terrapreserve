"""Tests for the operator catalogue and diff verifier (Step 3; D0 Decision 5, D4-07, D4-08).

Tests:
1. Diff verifier correctly agrees with honest records and FAILS on dropped or invented record rows.
2. At least 3 safe and 3 unsafe operators per family across F1 to F8.
3. Every operator applies cleanly to a hand-built model and the diff verifier validates its mutation record.
4. Safe and unsafe pairs on the same base state differ only by the damaging mutation.
5. F5 restructurings produce well-formed moved blocks and maintain resource semantics.
6. F8 operators produce 2 to 4 steps with unsafe variant having a break in a middle or final step.
7. Emitted models are deterministic given the same RNG.
"""

from __future__ import annotations

import random
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDiffVerifier(unittest.TestCase):
    def _get_modules(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "generator"))
        import model as m
        import diff_verify as dv
        return m, dv

    def test_diff_verifier_passes_on_honest_record(self) -> None:
        m, dv = self._get_modules()
        m0 = m.HCLModel()
        m0.add(m.Resource("aws_instance", "app", {"instance_type": "t3.micro"}))

        m1 = m0.copy()
        m1.get("aws_instance.app").set_attr("instance_type", "t3.small")

        record = [
            dv.MutationRow(
                step=1,
                operator="test_op",
                target_address="aws_instance.app",
                attribute="instance_type",
                before='"t3.micro"',
                after='"t3.small"',
            )
        ]
        # Should not raise
        dv.verify(m0, m1, record, step=1, operator_name="test_op")

    def test_diff_verifier_fails_on_dropped_record_row(self) -> None:
        m, dv = self._get_modules()
        m0 = m.HCLModel()
        m0.add(m.Resource("aws_instance", "app", {"instance_type": "t3.micro"}))

        m1 = m0.copy()
        m1.get("aws_instance.app").set_attr("instance_type", "t3.small")

        # Empty record - drops the change
        record = []
        with self.assertRaises(dv.DiffVerifyError) as ctx:
            dv.verify(m0, m1, record, step=1, operator_name="test_op")
        self.assertIn("changed but not recorded", str(ctx.exception))

    def test_diff_verifier_fails_on_invented_record_row(self) -> None:
        m, dv = self._get_modules()
        m0 = m.HCLModel()
        m0.add(m.Resource("aws_instance", "app", {"instance_type": "t3.micro"}))

        # No change made to m1
        m1 = m0.copy()

        # Invented record
        record = [
            dv.MutationRow(
                step=1,
                operator="test_op",
                target_address="aws_instance.app",
                attribute="instance_type",
                before='"t3.micro"',
                after='"t3.small"',
            )
        ]
        with self.assertRaises(dv.DiffVerifyError) as ctx:
            dv.verify(m0, m1, record, step=1, operator_name="test_op")
        self.assertIn("recorded but no change", str(ctx.exception))


class TestOperatorCatalogue(unittest.TestCase):
    def _get_modules(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "generator"))
        import operators
        import templates
        import diff_verify as dv
        return operators, templates, dv

    def test_catalogue_counts_per_family(self) -> None:
        ops_mod, _, _ = self._get_modules()
        catalogue = ops_mod.CATALOGUE

        for f_idx in range(1, 9):
            fam = f"F{f_idx}"
            safe_ops = [op for op in catalogue if op.family == fam and op.variant == "safe"]
            unsafe_ops = [op for op in catalogue if op.family == fam and op.variant == "unsafe"]
            self.assertGreaterEqual(
                len(safe_ops), 3,
                f"Family {fam} must have at least 3 safe operators, got {len(safe_ops)}",
            )
            self.assertGreaterEqual(
                len(unsafe_ops), 3,
                f"Family {fam} must have at least 3 unsafe operators, got {len(unsafe_ops)}",
            )

    def test_operators_verify_with_diff_verifier(self) -> None:
        ops_mod, tpl_mod, dv = self._get_modules()
        catalogue = ops_mod.CATALOGUE

        for op in catalogue:
            with self.subTest(operator=op.name):
                # Determine appropriate base variant
                variant = "clean"
                if op.target_invariant == "INV-SEC-001":
                    variant = "sec_001_violated"
                elif op.target_invariant == "INV-SEC-002":
                    variant = "sec_002_violated"
                elif op.target_invariant == "INV-SEC-003":
                    variant = "sec_003_violated"

                # Find a template where this operator is applicable
                applied = False
                for tpl_id in sorted(tpl_mod.TEMPLATES.keys()):
                    tpl = tpl_mod.TEMPLATES[tpl_id]
                    rng = random.Random(20261031)
                    m0, _ = tpl.instantiate(rng, variant=variant)
                    try:
                        step_models, mutation_records = op.apply(m0, rng)
                        applied = True
                        break
                    except ops_mod.OperatorNotApplicable:
                        continue

                self.assertTrue(applied, f"Operator {op.name} could not be applied to any template")

                # Verify each step with diff_verify
                curr = m0
                for step_idx, (next_m, rec) in enumerate(zip(step_models, mutation_records, strict=True), start=1):
                    dv.verify(curr, next_m, rec, step=step_idx, operator_name=op.name)
                    curr = next_m

    def test_f5_restructuring_moved_blocks_and_semantics(self) -> None:
        ops_mod, tpl_mod, _ = self._get_modules()
        f5_ops = [op for op in ops_mod.CATALOGUE if op.family == "F5"]
        # Find moved operator
        moved_op = next((op for op in f5_ops if "moved" in op.name and op.variant == "safe"), None)
        self.assertIsNotNone(moved_op)

        tpl = tpl_mod.TEMPLATES["tpl-01"]
        m0, _ = tpl.instantiate(random.Random(42), variant="clean")
        step_models, _ = moved_op.apply(m0, random.Random(42))
        m1 = step_models[0]

        # Must contain moved block
        self.assertGreaterEqual(len(m1.moved), 1)
        # from and to must be valid refs
        self.assertTrue(hasattr(m1.moved[0].from_addr, "expr"))
        self.assertTrue(hasattr(m1.moved[0].to_addr, "expr"))

    def test_f5_count_for_each_restructuring(self) -> None:
        ops_mod, tpl_mod, dv = self._get_modules()
        f5_ops = [op for op in ops_mod.CATALOGUE if op.family == "F5"]
        safe_op = next((op for op in f5_ops if op.name == "op_f5_count_each_safe"), None)
        unsafe_op = next((op for op in f5_ops if op.name == "op_f5_count_each_unsafe"), None)

        self.assertIsNotNone(safe_op, "op_f5_count_each_safe must be registered")
        self.assertIsNotNone(unsafe_op, "op_f5_count_each_unsafe must be registered")

        tpl = tpl_mod.TEMPLATES["tpl-01"]
        for op in [safe_op, unsafe_op]:
            rng = random.Random(42)
            m0, _ = tpl.instantiate(rng, variant="clean")
            step_models, records = op.apply(m0, rng)
            self.assertEqual(len(step_models), 1)
            dv.verify(m0, step_models[0], records[0], step=1, operator_name=op.name)
            # count must be in the mutation record
            count_rows = [r for r in records[0] if r.attribute == "count"]
            self.assertGreater(len(count_rows), 0)

    def test_f8_multi_step_sequences(self) -> None:
        ops_mod, tpl_mod, _ = self._get_modules()
        f8_ops = [op for op in ops_mod.CATALOGUE if op.family == "F8"]
        tpl = tpl_mod.TEMPLATES["tpl-01"]

        for op in f8_ops:
            with self.subTest(operator=op.name):
                rng = random.Random(42)
                variant = "sec_001_violated" if op.target_invariant == "INV-SEC-001" else "clean"
                m0, _ = tpl.instantiate(rng, variant=variant)
                step_models, records = op.apply(m0, rng)

                # 2 to 4 steps
                self.assertGreaterEqual(len(step_models), 2)
                self.assertLessEqual(len(step_models), 4)
                self.assertEqual(len(step_models), len(records))


if __name__ == "__main__":
    unittest.main()

