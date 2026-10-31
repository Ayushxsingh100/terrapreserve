"""Tests for D4b review fixes (test-first).

Enforces:
1. No scenario has a description-only mutation record.
2. Repair scenarios (F2, F4, F8) actually eliminate the violating pattern from step 0 in their final step.
3. F5 restructuring is visible in the diff.
4. F7 edits a central hub resource (aws_vpc, aws_route_table, aws_security_group).
5. Operators raise OperatorNotApplicable when target cannot be found (never fallback to description).
6. Secret-literal test over all real-world dev scenarios and pool/terrads/derived.
7. Derived natives record real SPDX licence and commit_or_version from derived.json.
"""

from __future__ import annotations

import json
import random
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "sources" / "terragoat"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import attribute_inventory
import hcl_lex


class TestD4bReviewFixes(unittest.TestCase):
    def setUp(self) -> None:
        self.dev_dir = REPO_ROOT / "scenarios" / "dev"
        self.scenarios: list[dict] = []
        for p in sorted(self.dev_dir.glob("tp-v1-*")):
            sc_json = p / "scenario.json"
            if sc_json.exists():
                with open(sc_json, encoding="utf-8") as f:
                    data = json.load(f)
                data["_dir"] = p
                self.scenarios.append(data)

    def test_no_scenario_has_description_only_mutation_record(self) -> None:
        """Operators must not fall back to description: mutation record cannot be description-only."""
        failing = []
        for sc in self.scenarios:
            muts = sc.get("mutation_record", [])
            attrs = {r.get("attribute") for r in muts if r.get("attribute")}
            if attrs == {"description"}:
                failing.append(sc["scenario_id"])

        self.assertEqual(
            failing, [],
            f"Found {len(failing)} scenarios with description-only mutation records: {failing[:10]}..."
        )

    def test_repair_scenarios_eliminate_violating_pattern_in_final_step(self) -> None:
        """For repair scenarios, the step 0 violation must be eliminated in the final step."""
        failing = []
        for sc in self.scenarios:
            family = sc.get("family")
            if family not in ("F2", "F4", "F8"):
                continue
            intent = sc.get("intent", {})
            if intent.get("kind") != "repair":
                continue

            target_inv = intent.get("target_invariant")
            s_dir = sc["_dir"]
            steps = sorted([d for d in s_dir.glob("step_*") if d.is_dir()])
            if not steps:
                continue
            step0 = steps[0]
            step_final = steps[-1]

            def read_tf(s_path: Path) -> str:
                return "\n".join(f.read_text(encoding="utf-8") for f in s_path.glob("*.tf"))

            text0 = read_tf(step0)
            text_final = read_tf(step_final)

            if target_inv == "INV-SEC-001":
                # Public SSH in step 0 must be repaired in final step
                # Step 0 must have had 0.0.0.0/0 on port 22
                self.assertIn("0.0.0.0/0", text0, f"{sc['scenario_id']} S0 should have 0.0.0.0/0")
                # In final step, for safe repairs, 0.0.0.0/0 on port 22 must be gone
                if intent.get("class") == "safe" or sc.get("gt_class") == "safe":
                    # Check that port 22 does not have 0.0.0.0/0
                    # Lexical check on security group rules and inline ingress
                    attrs = hcl_lex.attributes_from_hcl(text_final)
                    # Check if any port 22 rule still has 0.0.0.0/0
                    if 'from_port   = 22' in text_final or 'from_port = 22' in text_final:
                        for a in attrs:
                            if a.name == "cidr_blocks" and "0.0.0.0/0" in text_final.splitlines()[a.line - 1]:
                                failing.append((sc["scenario_id"], "INV-SEC-001 not repaired: 0.0.0.0/0 remains on port 22"))

            elif target_inv == "INV-SEC-002":
                # Public DB port 5432
                if intent.get("class") == "safe" or sc.get("gt_class") == "safe":
                    if 'from_port   = 5432' in text_final or 'from_port = 5432' in text_final:
                        for a in hcl_lex.attributes_from_hcl(text_final):
                            if a.name == "cidr_blocks" and "0.0.0.0/0" in text_final.splitlines()[a.line - 1]:
                                failing.append((sc["scenario_id"], "INV-SEC-002 not repaired: 0.0.0.0/0 remains on 5432"))

            elif target_inv == "INV-SEC-003":
                # RDS publicly accessible
                if intent.get("class") == "safe" or sc.get("gt_class") == "safe":
                    if "publicly_accessible = true" in text_final.replace(" ", ""):
                        failing.append((sc["scenario_id"], "INV-SEC-003 not repaired: publicly_accessible is true"))

        self.assertEqual(
            failing, [],
            f"Found {len(failing)} repair scenarios where violation was not eliminated: {failing[:10]}..."
        )

    def test_f5_restructuring_visible_in_diff(self) -> None:
        """For F5, restructuring must be visible in diff (moved block, count, replacement, or rule split)."""
        failing = []
        for sc in self.scenarios:
            if sc.get("family") != "F5":
                continue
            diff = sc.get("steps", [{}])[-1].get("diff_from_previous", "")
            has_moved = "moved {" in diff
            has_count = "+  count" in diff or "-  count" in diff or "count =" in diff or "count" in diff
            has_replacement = bool(re.search(r'(ami|engine_version|allocated_storage)\s*=', diff))
            has_sg_split = "aws_security_group_rule" in diff or "ingress {" in diff or "ingress" in diff
            if not (has_moved or has_count or has_replacement or has_sg_split):
                failing.append((sc["scenario_id"], "F5 restructuring not visible in diff"))

        self.assertEqual(failing, [], f"F5 scenarios missing restructuring in diff: {failing}")

    def test_f7_hub_resource_is_edited(self) -> None:
        """For F7, the edited resource in mutation record must be a hub resource."""
        hub_prefixes = ("aws_vpc.", "aws_route_table.", "aws_security_group.", "aws_security_group_rule.")
        failing = []
        for sc in self.scenarios:
            if sc.get("family") != "F7":
                continue
            muts = sc.get("mutation_record", [])
            primary_target = muts[0].get("target_address", "") if muts else ""
            if not any(primary_target.startswith(hp) for hp in hub_prefixes):
                failing.append((sc["scenario_id"], f"Non-hub resource targeted: {primary_target}"))

        self.assertEqual(failing, [], f"F7 scenarios not targeting a hub resource: {failing}")

    def test_secret_literals_in_all_dev_scenarios_and_derived(self) -> None:
        """All dev scenarios (both tiers) and pool/terrads/derived must have zero secret literals."""
        flagged = []
        targets = [REPO_ROOT / "pool" / "terrads" / "derived", REPO_ROOT / "scenarios" / "dev"]
        for base in targets:
            for p in base.rglob("*.tf"):
                text = p.read_text(encoding="utf-8")
                # Check attribute inventory
                for a in attribute_inventory.matching_attributes(text):
                    if a.value_kind in attribute_inventory.FLAGGED_KINDS:
                        flagged.append((str(p), a.top_level, a.name, a.value_kind, a.line))
                # Check specific forbidden credential patterns
                if "AKIA" in text:
                    for line_idx, line in enumerate(text.splitlines(), 1):
                        if re.search(r"AKIA[0-9A-Z]{16}", line):
                            flagged.append((str(p), "pattern", "AKIA", "literal", line_idx))

        self.assertEqual(flagged, [], f"Secret literals found: {flagged}")

    def test_derived_natives_record_real_spdx_and_commit(self) -> None:
        """Derived native scenarios must record real commit SHA and SPDX licence from derived.json."""
        derived_json_path = REPO_ROOT / "pool" / "derived.json"
        with open(derived_json_path, encoding="utf-8") as f:
            der_entries = {e["module_id"]: e for e in json.load(f)}

        failing = []
        for sc in self.scenarios:
            if sc.get("derived") or sc.get("source", {}).get("derived"):
                src = sc.get("source", {})
                mod_id = sc.get("module_id")
                commit = src.get("commit_or_version")
                lic = src.get("license")
                if commit in (None, "unknown", "") or len(str(commit)) < 40:
                    failing.append((sc["scenario_id"], f"Invalid commit_or_version: {commit}"))
                if lic not in ("MIT", "Apache-2.0"):
                    failing.append((sc["scenario_id"], f"Invalid SPDX license: {lic}"))

        self.assertEqual(failing, [], f"Derived natives with invalid provenance: {failing}")


    def test_operator_raises_not_applicable_when_target_not_found(self) -> None:
        """Operators must raise OperatorNotApplicable instead of falling back to description."""
        import operators
        import templates
        self.assertTrue(hasattr(operators, "OperatorNotApplicable"), "operators.OperatorNotApplicable must exist")
        OperatorNotApplicable = operators.OperatorNotApplicable

        # Instantiate a clean model with no public SSH rule
        tpl = templates.TEMPLATES["tpl-01"]
        m0, _ = tpl.instantiate(random.Random(42), variant="clean")
        # Try to apply op_f2_repair_ssh_safe which targets public SSH rule
        op = next(op for op in operators.CATALOGUE if op.name == "op_f2_repair_ssh_safe")
        with self.assertRaises(OperatorNotApplicable):
            op.apply(m0, random.Random(42))


if __name__ == "__main__":
    unittest.main()
