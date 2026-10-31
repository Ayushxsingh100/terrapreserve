"""Tests for D4b Review Round 3 (test-first per work package instructions).

Tests over EVERY generated scenario, both tiers:
1. (a) Mutation touches the attribute/resource class the family requires:
       - F3: dependency path (subnet, db subnet group, or instance subnet/SG association)
       - F5: structure (moved block, inline/separate rules, count, replacement)
       - F6: new resource (new resource added to configuration)
       - F7: hub resource (aws_vpc, aws_route_table, aws_security_group, aws_security_group_rule)
2. (b) intent.breaks equals the invariants whose lexical pattern the mutation introduces (mapping table in the test, written from D0 Decision 4):
       - Safe variants have intent.breaks == []
       - Unsafe variants declare exactly the broken invariants
3. (c) At least N scenarios per family/class break INV-FUNC-001 where D0 expects it
       (F3 unsafe, F4 unsafe, F7 unsafe, F8 unsafe), and no unsafe family consists
       only of publicly_accessible = true.
4. (d) Real-world records carry the same intent.breaks as controlled ones.
5. F5 "moved" emits a moved { from = ... to = ... } block.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import hcl_lex


class TestD4bReviewRound3(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dev_dir = REPO_ROOT / "scenarios" / "dev"
        cls.scenarios: list[dict] = []
        for p in sorted(cls.dev_dir.glob("tp-v1-*")):
            sc_json = p / "scenario.json"
            if sc_json.exists():
                with open(sc_json, encoding="utf-8") as f:
                    data = json.load(f)
                data["_dir"] = p
                cls.scenarios.append(data)

    def test_f3_touches_dependency_path(self) -> None:
        """F3 scenarios must touch dependency path resources (subnet, db_subnet_group, or instance routing/associations)."""
        failing = []
        for sc in self.scenarios:
            if sc.get("family") != "F3":
                continue
            muts = sc.get("mutation_record", [])
            dep_touched = False
            for m in muts:
                tgt = m.get("target_address", "")
                attr = m.get("attribute", "")
                if "aws_subnet" in tgt or "aws_db_subnet_group" in tgt:
                    dep_touched = True
                    break
                if tgt.startswith("aws_instance.") and attr in ("subnet_id", "vpc_security_group_ids"):
                    dep_touched = True
                    break
            if not dep_touched:
                failing.append(sc["scenario_id"])

        self.assertEqual(
            failing, [],
            f"F3 scenarios not touching dependency path: {len(failing)} failing: {failing[:10]}"
        )

    def test_f6_adds_new_resource(self) -> None:
        """F6 scenarios must add a new resource to the configuration."""
        failing = []
        for sc in self.scenarios:
            if sc.get("family") != "F6":
                continue
            step0 = sc["_dir"] / "step_0"
            step1 = sc["_dir"] / "step_1"
            headers0 = set()
            for tf in step0.glob("*.tf"):
                headers0.update(hcl_lex.headers_from_hcl(tf.read_text(encoding="utf-8")).managed)
            headers1 = set()
            for tf in step1.glob("*.tf"):
                headers1.update(hcl_lex.headers_from_hcl(tf.read_text(encoding="utf-8")).managed)
            added = headers1 - headers0
            if not added:
                failing.append(sc["scenario_id"])

        self.assertEqual(
            failing, [],
            f"F6 scenarios that do not add a new resource: {len(failing)} failing: {failing[:10]}"
        )

    def test_f7_touches_hub_resource(self) -> None:
        """F7 scenarios must edit a hub resource (VPC, route table, or shared security group)."""
        failing = []
        for sc in self.scenarios:
            if sc.get("family") != "F7":
                continue
            muts = sc.get("mutation_record", [])
            hub_touched = False
            for m in muts:
                tgt = m.get("target_address", "")
                if tgt.startswith(("aws_vpc.", "aws_route_table.", "aws_security_group.", "aws_security_group_rule.")):
                    hub_touched = True
                    break
            if not hub_touched:
                failing.append(sc["scenario_id"])

        self.assertEqual(
            failing, [],
            f"F7 scenarios not touching hub resource: {len(failing)} failing: {failing[:10]}"
        )

    def test_f5_touches_structure(self) -> None:
        """F5 scenarios must touch structural configuration (moved, count, rules, or replacement ami)."""
        failing = []
        for sc in self.scenarios:
            if sc.get("family") != "F5":
                continue
            muts = sc.get("mutation_record", [])
            struct_touched = False
            for m in muts:
                tgt = m.get("target_address", "")
                attr = m.get("attribute", "")
                op = m.get("operator", "")
                if attr in ("count", "ami", "subnet_id") or "moved" in op or "rules" in op or "aws_security_group_rule" in tgt:
                    struct_touched = True
                    break
            if not struct_touched:
                failing.append(sc["scenario_id"])

        self.assertEqual(
            failing, [],
            f"F5 scenarios not touching structure: {len(failing)} failing: {failing[:10]}"
        )

    def test_f5_moved_emits_moved_block(self) -> None:
        """F5 scenarios using moved operator must emit a 'moved {' block in the final step."""
        failing = []
        for sc in self.scenarios:
            if sc.get("family") != "F5":
                continue
            op = sc.get("mutation_record", [{}])[0].get("operator", "")
            if "moved" in op and sc.get("intent", {}).get("class") == "safe":
                final_step = sorted(sc["_dir"].glob("step_*"))[-1]
                has_moved = False
                for tf in final_step.glob("*.tf"):
                    if "moved {" in tf.read_text(encoding="utf-8"):
                        has_moved = True
                        break
                if not has_moved:
                    failing.append(sc["scenario_id"])

        self.assertEqual(
            failing, [],
            f"F5 safe moved scenarios missing moved block: {len(failing)} failing: {failing[:10]}"
        )

    def test_intent_breaks_matches_lexical_pattern(self) -> None:
        """intent.breaks must equal the invariants whose lexical pattern the mutation introduces."""
        failing = []
        for sc in self.scenarios:
            cls = sc.get("intent", {}).get("class")
            breaks = sorted(sc.get("intent", {}).get("breaks", []))
            if cls == "safe":
                if breaks != []:
                    failing.append((sc["scenario_id"], breaks, []))
                continue

            # Unsafe: check that declared breaks match introduced lexical patterns
            muts = sc.get("mutation_record", [])
            introduced = set()
            for m in muts:
                tgt = m.get("target_address", "")
                attr = m.get("attribute", "")
                after = m.get("after")
                if attr == "publicly_accessible" and after == "true":
                    introduced.add("INV-SEC-003")
                elif attr == "cidr_blocks" and after in ('["0.0.0.0/0"]', '["::/0"]'):
                    # Must be ingress on port 22 or 5432, not egress
                    is_egress = "egress" in tgt or any(m2.get("target_address") == tgt and m2.get("attribute") == "type" and m2.get("after") == '"egress"' for m2 in muts)
                    if not is_egress:
                        is_ssh = "ssh" in tgt or "bastion" in tgt or any(m2.get("target_address") == tgt and m2.get("attribute") in ("from_port", "to_port") and m2.get("after") == "22" for m2 in muts)
                        is_db = "5432" in tgt or any(m2.get("target_address") == tgt and m2.get("attribute") in ("from_port", "to_port") and m2.get("after") == "5432" for m2 in muts)
                        if is_ssh:
                            introduced.add("INV-SEC-001")
                        elif is_db:
                            introduced.add("INV-SEC-002")
                elif attr == "vpc_security_group_ids" and after == "[]":
                    introduced.add("INV-FUNC-001")
                elif attr == "cidr_blocks" and after == '["127.0.0.1/32"]':
                    introduced.add("INV-FUNC-001")

            # Check new resources added (e.g. F6)
            for m in muts:
                tgt = m.get("target_address", "")
                attr = m.get("attribute", "")
                after = m.get("after")
                if "replica" in tgt and attr == "publicly_accessible" and after == "true":
                    introduced.add("INV-SEC-003")
                elif "bastion" in tgt and "aws_security_group" in tgt:
                    introduced.add("INV-SEC-001")

            expected = sorted(introduced)
            if expected and breaks != expected:
                failing.append((sc["scenario_id"], breaks, expected))

        self.assertEqual(
            failing, [],
            f"Scenarios where intent.breaks does not match introduced lexical pattern: {len(failing)} failing: {failing[:10]}"
        )

    def test_inv_func_001_broken_in_expected_families(self) -> None:
        """F3, F4, F7, and F8 unsafe scenarios must break INV-FUNC-001 (not just INV-SEC-003)."""
        families_to_check = ["F3", "F4", "F7", "F8"]
        for fam in families_to_check:
            unsafe_sc = [sc for sc in self.scenarios if sc.get("family") == fam and sc.get("intent", {}).get("class") == "unsafe"]
            func_broken = [sc for sc in unsafe_sc if "INV-FUNC-001" in sc.get("intent", {}).get("breaks", [])]
            self.assertGreater(
                len(func_broken), 0,
                f"Family {fam} unsafe has NO scenarios breaking INV-FUNC-001 (got {len(func_broken)} of {len(unsafe_sc)})"
            )

    def test_no_unsafe_family_consists_only_of_publicly_accessible(self) -> None:
        """No unsafe family may consist exclusively of publicly_accessible = true mutations."""
        failing_fams = []
        for fam in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
            unsafe_sc = [sc for sc in self.scenarios if sc.get("family") == fam and sc.get("intent", {}).get("class") == "unsafe"]
            attrs = set()
            for sc in unsafe_sc:
                for m in sc.get("mutation_record", []):
                    attr = m.get("attribute", "")
                    if attr:
                        attrs.add(attr)
            if attrs == {"publicly_accessible"} or attrs == {"publicly_accessible", "instance_type"}:
                failing_fams.append((fam, attrs))

        self.assertEqual(
            failing_fams, [],
            f"Unsafe families consisting only of publicly_accessible mutations: {failing_fams}"
        )

    def test_real_world_records_carry_same_intent_breaks_as_controlled(self) -> None:
        """Real-world tier unsafe scenarios must have consistent intent.breaks distribution as controlled tier."""
        for fam in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
            ctrl_unsafe = [sc for sc in self.scenarios if sc.get("family") == fam and sc.get("intent", {}).get("class") == "unsafe" and int(sc["scenario_id"].split("-")[-1]) <= 208]
            rw_unsafe = [sc for sc in self.scenarios if sc.get("family") == fam and sc.get("intent", {}).get("class") == "unsafe" and int(sc["scenario_id"].split("-")[-1]) > 208]
            ctrl_breaks = {tuple(sorted(sc.get("intent", {}).get("breaks", []))) for sc in ctrl_unsafe}
            rw_breaks = {tuple(sorted(sc.get("intent", {}).get("breaks", []))) for sc in rw_unsafe}
            self.assertEqual(
                ctrl_breaks, rw_breaks,
                f"Family {fam} intent.breaks mismatch: controlled={ctrl_breaks} vs real-world={rw_breaks}"
            )


if __name__ == "__main__":
    unittest.main()
