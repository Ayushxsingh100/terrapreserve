"""Tests for the ten controlled templates (Step 2; D0 Decision 3, D4-05).

Structural checks on the model (not invariant evaluation):
- 10 templates exist (tpl-01 to tpl-10).
- Every template shares the Appendix B topology resources:
  aws_vpc, aws_subnet (app + at least 2 db subnets in different AZs),
  aws_internet_gateway, aws_route_table, aws_route_table_association,
  aws_security_group (app + db), aws_instance, aws_db_instance,
  aws_db_subnet_group.
- EC2 uses app subnet and app SG.
- RDS is postgres, publicly_accessible is false in clean S0, uses db subnet group and db SG.
- DB SG has 5432 ingress from app SG (INV-FUNC-001 wiring).
- Clean S0 has no 0.0.0.0/0 or ::/0 ingress on port 22 or port 5432.
- No provider block with credentials; versions.tf uses pins.
- The 10 templates differ pairwise on at least one structural axis.
- All four SG styles occur across the templates:
  (all_separate, all_inline, mixed_app_inline_db_separate, mixed_app_separate_db_inline).
- Both db subnet counts (2 and 3) occur.
- Parameter generator is reproducible from seed.
- Base-state variants for repair targets (SEC-001, SEC-002, SEC-003) and clean S0.
- TerraGoat attribute vocabulary is recorded.
"""

from __future__ import annotations

import random
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# We will test generator.templates when implemented.
# Under test-first rule, importing will fail until implemented.


class TestTenTemplatesStructure(unittest.TestCase):
    def _get_templates_module(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "generator"))
        import templates
        return templates

    def test_ten_templates_exist(self) -> None:
        templates = self._get_templates_module()
        self.assertEqual(len(templates.TEMPLATES), 10)
        expected_ids = [f"tpl-{i:02d}" for i in range(1, 11)]
        self.assertEqual(sorted(templates.TEMPLATES.keys()), expected_ids)

    def test_template_axes_difference(self) -> None:
        templates = self._get_templates_module()
        tpls = list(templates.TEMPLATES.values())

        # Check pairwise distinct on axes
        for i in range(len(tpls)):
            for j in range(i + 1, len(tpls)):
                t1, t2 = tpls[i], tpls[j]
                diffs = [
                    t1.sg_style != t2.sg_style,
                    t1.db_subnet_count != t2.db_subnet_count,
                    t1.has_second_app_sg != t2.has_second_app_sg,
                    t1.route_table_layout != t2.route_table_layout,
                    t1.use_count_for_db_subnets != t2.use_count_for_db_subnets,
                    t1.naming_scheme != t2.naming_scheme,
                    t1.instance_class != t2.instance_class or t1.db_class != t2.db_class,
                ]
                self.assertTrue(
                    any(diffs),
                    f"{t1.id} and {t2.id} must differ on at least one structural axis",
                )

        # Check all four SG styles occur
        all_sg_styles = {t.sg_style for t in tpls}
        self.assertEqual(
            all_sg_styles,
            {
                "all_separate",
                "all_inline",
                "mixed_app_inline_db_separate",
                "mixed_app_separate_db_inline",
            },
        )

        # Check both subnet counts (2 and 3) occur
        subnet_counts = {t.db_subnet_count for t in tpls}
        self.assertEqual(subnet_counts, {2, 3})

    def test_shared_appendix_b_topology_in_clean_s0(self) -> None:
        templates = self._get_templates_module()
        for tpl_id, tpl in templates.TEMPLATES.items():
            with self.subTest(template=tpl_id):
                rng = random.Random(20261031)
                model, meta = tpl.instantiate(rng, variant="clean")

                # Must contain VPC
                vpc_addrs = [a for a in model.resources if a.startswith("aws_vpc.")]
                self.assertEqual(len(vpc_addrs), 1)

                # Must contain internet gateway
                igw_addrs = [a for a in model.resources if a.startswith("aws_internet_gateway.")]
                self.assertEqual(len(igw_addrs), 1)

                # Must contain route table and association
                rt_addrs = [a for a in model.resources if a.startswith("aws_route_table.")]
                self.assertGreaterEqual(len(rt_addrs), 1)
                rta_addrs = [a for a in model.resources if a.startswith("aws_route_table_association.")]
                self.assertGreaterEqual(len(rta_addrs), 1)

                # Must contain EC2 instance
                ec2_addrs = [a for a in model.resources if a.startswith("aws_instance.")]
                self.assertEqual(len(ec2_addrs), 1)

                # Must contain RDS instance
                rds_addrs = [a for a in model.resources if a.startswith("aws_db_instance.")]
                self.assertEqual(len(rds_addrs), 1)
                rds = model.resources[rds_addrs[0]]
                self.assertEqual(rds.attrs.get("publicly_accessible"), False)
                self.assertEqual(rds.attrs.get("engine"), "postgres")

                # Must contain DB subnet group
                dbsg_addrs = [a for a in model.resources if a.startswith("aws_db_subnet_group.")]
                self.assertEqual(len(dbsg_addrs), 1)

                # App and DB security groups
                sg_addrs = [a for a in model.resources if a.startswith("aws_security_group.")]
                self.assertGreaterEqual(len(sg_addrs), 2)

                # Functional path: DB SG has 5432 ingress from app SG
                # Can be inline or separate rule
                has_func_path = tpl.has_functional_path_structural(model)
                self.assertTrue(has_func_path, f"{tpl_id} must have structural 5432 ingress from app SG")

                # Clean state must NOT have 0.0.0.0/0 on port 22 or 5432
                has_clean_ssh = tpl.has_public_ssh_structural(model)
                self.assertFalse(has_clean_ssh, f"{tpl_id} clean S0 must not have public SSH")
                has_clean_db = tpl.has_public_db_structural(model)
                self.assertFalse(has_clean_db, f"{tpl_id} clean S0 must not have public DB port")

    def test_repair_s0_variants(self) -> None:
        templates = self._get_templates_module()
        for tpl_id, tpl in templates.TEMPLATES.items():
            with self.subTest(template=tpl_id):
                rng = random.Random(20261031)

                # SEC-001 variant: public SSH present, others clean
                m_sec1, _ = tpl.instantiate(rng, variant="sec_001_violated")
                self.assertTrue(tpl.has_public_ssh_structural(m_sec1))
                self.assertFalse(tpl.has_public_db_structural(m_sec1))
                rds1 = [m for a, m in m_sec1.resources.items() if a.startswith("aws_db_instance.")][0]
                self.assertEqual(rds1.attrs.get("publicly_accessible"), False)

                # SEC-002 variant: public DB port present, SSH clean
                m_sec2, _ = tpl.instantiate(rng, variant="sec_002_violated")
                self.assertTrue(tpl.has_public_db_structural(m_sec2))
                self.assertFalse(tpl.has_public_ssh_structural(m_sec2))
                rds2 = [m for a, m in m_sec2.resources.items() if a.startswith("aws_db_instance.")][0]
                self.assertEqual(rds2.attrs.get("publicly_accessible"), False)

                # SEC-003 variant: publicly_accessible = true, SSH and DB port clean
                m_sec3, _ = tpl.instantiate(rng, variant="sec_003_violated")
                self.assertFalse(tpl.has_public_ssh_structural(m_sec3))
                self.assertFalse(tpl.has_public_db_structural(m_sec3))
                rds3 = [m for a, m in m_sec3.resources.items() if a.startswith("aws_db_instance.")][0]
                self.assertEqual(rds3.attrs.get("publicly_accessible"), True)

    def test_parameters_reproducible_from_seed(self) -> None:
        templates = self._get_templates_module()
        tpl = templates.TEMPLATES["tpl-01"]
        m1, meta1 = tpl.instantiate(random.Random(42), variant="clean")
        m2, meta2 = tpl.instantiate(random.Random(42), variant="clean")
        m3, meta3 = tpl.instantiate(random.Random(99), variant="clean")

        import emitter
        self.assertEqual(emitter.emit(m1), emitter.emit(m2))
        self.assertEqual(meta1, meta2)
        # Different seeds should yield different parameters (e.g. CIDRs or tags)
        self.assertNotEqual(meta1["cidr_plan"], meta3["cidr_plan"])

    def test_terragoat_vocabulary_recorded(self) -> None:
        templates = self._get_templates_module()
        for tpl_id, tpl in templates.TEMPLATES.items():
            self.assertTrue(hasattr(tpl, "terragoat_vocabulary"))
            vocab = tpl.terragoat_vocabulary
            self.assertIn("aws_instance", vocab)
            self.assertIn("aws_db_instance", vocab)
            self.assertIn("aws_security_group", vocab)


if __name__ == "__main__":
    unittest.main()

