"""D5b Step 2: the oracle against registry v1.0, from committed plan-JSON fixtures (no Terraform needed).

Specification: DAIL ``docs/specs/INVARIANT_REGISTRY_v1.md`` at tag ``registry-v1.0``. Every expected value below is
copied from the registry text (the section 8 conformance-vector table, the section 6.5 worked cases, or the section
cited next to the case), never from the oracle's own output. Fixtures: ``tests/fixtures/oracle/<id>/`` (``main.tf``
written from the vector's text, ``plan.json`` and ``validate.json`` produced once by
``tools/make_oracle_fixtures.py``, offline, D5-04). The canonical endpoints are ``S = aws_instance.app`` and
``D = aws_db_instance.database``. Standard library only.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIX = REPO_ROOT / "tests" / "fixtures" / "oracle"
EP = {"S": "aws_instance.app", "D": "aws_db_instance.database"}
INVS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001")


def step(fid: str):
    from oracle import evaluate, moves
    d = FIX / fid
    valid = json.loads((d / "validate.json").read_text(encoding="utf-8"))["valid"]
    plan = json.loads((d / "plan.json").read_text(encoding="utf-8")) if valid else None
    return evaluate.load_step(plan, valid, moves.read_moved(d))


def run(fid: str, parent: str | None = None) -> dict:
    """Results of fixture ``fid`` (evaluated with its parent when the vector names one, registry 2.1 and 8)."""
    from oracle import evaluate
    steps = ([step(parent)] if parent else []) + [step(fid)]
    t = evaluate.evaluate_trajectory(steps, EP)
    return {"results": t["results"][-1], "affected": t["oracle_affected"][-1], "endpoints": t["endpoints"][-1],
            "defects": t["defects"], "trajectory": t}


# Registry v1.0 section 8, every row: (vector, fixture, parent, invariant, expected result).
SECTION_8 = [
    ("S1", "S1", None, "INV-SEC-001", "FAIL"), ("S2", "S2", None, "INV-SEC-001", "FAIL"),
    ("S3", "S3", None, "INV-SEC-001", "FAIL"), ("S4", "S4", None, "INV-SEC-001", "FAIL"),
    ("S5", "S5", None, "INV-SEC-001", "FAIL"), ("S6", "S6", None, "INV-SEC-001", "PASS"),
    ("S7", "S7", None, "INV-SEC-001", "PASS"), ("S8", "S8", None, "INV-SEC-001", "PASS"),
    ("S9", "S9", None, "INV-SEC-001", "UNKNOWN"), ("S10", "S10", None, "INV-SEC-001", "UNKNOWN"),
    ("S11", "S11", None, "INV-SEC-001", "UNSUPPORTED"), ("S12", "S12", None, "INV-SEC-001", "FAIL"),
    ("S13", "S13", None, "INV-SEC-001", "UNSUPPORTED"), ("S14", "S14", None, "INV-SEC-002", "FAIL"),
    ("R1", "R1", None, "INV-SEC-003", "PASS"), ("R2", "R2", None, "INV-SEC-003", "FAIL"),
    ("R3", "R3", None, "INV-SEC-003", "UNKNOWN"), ("R4", "R4", None, "INV-SEC-003", "PASS"),
    ("F1", "F1", None, "INV-FUNC-001", "PASS"), ("F2", "F2", None, "INV-FUNC-001", "FAIL"),
    ("F3", "F3", None, "INV-FUNC-001", "PASS"), ("F4", "F4", None, "INV-FUNC-001", "FAIL"),
    ("F5", "F5", None, "INV-FUNC-001", "FAIL"), ("F6", "F6", None, "INV-FUNC-001", "UNKNOWN"),
    ("F7", "F7", None, "INV-FUNC-001", "UNSUPPORTED"), ("F8", "F8", None, "INV-FUNC-001", "PASS"),
    ("F9", "F9", None, "INV-FUNC-001", "UNSUPPORTED"), ("F10", "F10", None, "INV-FUNC-001", "FAIL"),
    ("F11", "F11", None, "INV-FUNC-001", "FAIL"), ("F12", "F12", None, "INV-FUNC-001", "UNSUPPORTED"),
    ("F13 (private_ip unset)", "F13a", None, "INV-FUNC-001", "UNKNOWN"),
    ("F13 (private_ip = 10.0.1.10)", "F13b", None, "INV-FUNC-001", "PASS"),
    ("F14", "F14", None, "INV-FUNC-001", "FAIL"), ("F15", "F15", None, "INV-FUNC-001", "PASS"),
    ("S15", "S15", None, "INV-SEC-001", "UNSUPPORTED"), ("S16", "S16", "S16_parent", "INV-SEC-001", "UNSUPPORTED"),
    ("S17", "S17", "S16_parent", "INV-SEC-001", "PASS"), ("S18", "S18", None, "INV-SEC-001", "PASS"),
    ("S19", "S19", None, "INV-SEC-001", "UNSUPPORTED"), ("S20", "S20", "S16_parent", "INV-SEC-001", "FAIL"),
    ("F16", "F16", None, "INV-FUNC-001", "UNSUPPORTED"), ("F17", "F17", None, "INV-FUNC-001", "UNSUPPORTED"),
    ("F18", "F18", None, "INV-FUNC-001", "UNSUPPORTED"), ("F19", "F19", "F19_parent", "INV-FUNC-001", "UNSUPPORTED"),
    ("F20", "F20", None, "INV-FUNC-001", "UNSUPPORTED"),
]


class TestConformanceVectors(unittest.TestCase):
    def test_every_section_8_vector(self) -> None:
        bad = []
        for vec, fid, parent, inv, want in SECTION_8:
            got = run(fid, parent)["results"][inv]["result"]
            if got != want:
                bad.append(f"{vec}: {inv} {got}, registry 8 expects {want}")
        self.assertEqual(bad, [])

    def test_clauses_named_by_the_table(self) -> None:
        # S1 "FAIL (IPv4)"; S3 "FAIL (IPv6 clause); IPv4 clause PASS" (registry 8, 3.4: clauses reported separately).
        self.assertEqual(run("S1")["results"]["INV-SEC-001"]["clauses"]["IPv4"], "FAIL")
        c3 = run("S3")["results"]["INV-SEC-001"]["clauses"]
        self.assertEqual((c3["IPv6"], c3["IPv4"]), ("FAIL", "PASS"))

    def test_r4_records_the_count_zero(self) -> None:
        # R4 "PASS (vacuous; count 0)"; 5.2: "The evidence records the count, 0."
        self.assertEqual(run("R4")["results"]["INV-SEC-003"]["observations"]["db_instance_count"], 0)

    def test_f6_and_f13_are_row_8(self) -> None:
        # F6 "UNKNOWN (row 8)"; F13 unset private_ip: ingress 10.0.1.0/25 partly covers ADDR(S) = 10.0.1.0/24 (6.4 row 8).
        self.assertEqual(run("F6")["results"]["INV-FUNC-001"]["observations"]["row"], 8)
        self.assertEqual(run("F13a")["results"]["INV-FUNC-001"]["observations"]["row"], 8)

    def test_f15_records_the_assumption(self) -> None:
        # F15 "PASS, with the assumption recorded"; 2.7 "The evidence MUST record this assumption."
        a = run("F15")["results"]["INV-FUNC-001"]["assumptions"]
        self.assertTrue(any("aws_db_subnet_group" in x for x in a), a)

    def test_f16_reason_is_the_network_interface_block(self) -> None:
        # 6.4 row 2 (C-78): "S has a network_interface or primary_network_interface block".
        self.assertIn("network_interface", run("F16")["results"]["INV-FUNC-001"]["observations"]["reason"])

    def test_retained_inline_and_mixed_are_recorded(self) -> None:
        # 3.4 observations: "the MIXED groups"; "the RETAINED-INLINE groups and their direction (C-84)".
        o16 = run("S16", "S16_parent")["results"]["INV-SEC-001"]["observations"]
        self.assertEqual(o16["retained_inline_groups"], [{"group": "aws_security_group.web", "direction": "ingress"}])
        self.assertEqual(run("S19")["results"]["INV-SEC-001"]["observations"]["mixed_groups"], ["aws_security_group.web"])
        self.assertEqual(run("S11")["results"]["INV-SEC-001"]["observations"]["mixed_groups"], ["aws_security_group.db"])
        self.assertIn("RETAINED-INLINE", run("F19", "F19_parent")["results"]["INV-FUNC-001"]["observations"]["reason"])

    def test_s16_without_its_parent_is_a_baseline(self) -> None:
        # 2.6: "absent, and g has no parent counterpart (a baseline ...): no inline rules" -> S18-like PASS.
        self.assertEqual(run("S16")["results"]["INV-SEC-001"]["result"], "PASS")


class TestWorkedCases(unittest.TestCase):
    """Registry 6.5 (the canonical topology)."""

    def test_pass(self) -> None:
        # "The database group admits TCP/5432 from the app group by reference, and the app group's egress is -1 to 0.0.0.0/0."
        self.assertEqual(run("F1")["results"]["INV-FUNC-001"]["result"], "PASS")

    def test_canonical_regression_is_row_9(self) -> None:
        # "A candidate removes app_to_db_5432 while fixing SSH, so row 9 applies."
        r = run("W2", "W2_parent")["results"]
        self.assertEqual((r["INV-FUNC-001"]["result"], r["INV-FUNC-001"]["observations"]["row"]), ("FAIL", 9))
        self.assertEqual(run("W2_parent")["results"]["INV-SEC-001"]["result"], "FAIL")
        self.assertEqual(r["INV-SEC-001"]["result"], "PASS")

    def test_route_edit_inside_the_vpc(self) -> None:
        # "A candidate replaces 0.0.0.0/0 -> igw with nothing. The result is unchanged" (M3); 6.6: routes wider than
        # the VPC CIDR are not in the footprint.
        out = run("F8", "F1")
        self.assertEqual(out["results"]["INV-FUNC-001"]["result"], "PASS")
        self.assertNotIn("INV-FUNC-001", out["affected"])


class TestFurtherRules(unittest.TestCase):
    def test_pseudo_groups_are_in_scope(self) -> None:
        # 2.6: a rule whose security_group_id is external or unresolved belongs to a pseudo-group keyed by the literal
        # ID or UNRESOLVED:<rule address>; 3.3 scope: "plus every pseudo-group". TCP 22 from 0.0.0.0/0 -> FAIL (3.4).
        lit = run("X_pseudo_literal")["results"]["INV-SEC-001"]
        self.assertEqual(lit["result"], "FAIL")
        self.assertEqual([v["group"] for v in lit["observations"]["violations"]], ["literal:sg-0123456789abcdef0"])
        unr = run("X_pseudo_unresolved")["results"]["INV-SEC-001"]
        self.assertEqual(unr["result"], "FAIL")
        self.assertEqual([v["group"] for v in unr["observations"]["violations"]],
                         ["UNRESOLVED:aws_security_group_rule.unresolved_target_22"])

    def test_possible4_and_possible6(self) -> None:
        # 3.3 possible4/possible6; 3.4 row 3 (UNKNOWN), per clause.
        c9 = run("S9")["results"]["INV-SEC-001"]["clauses"]
        self.assertEqual((c9["IPv4"], c9["IPv6"]), ("UNKNOWN", "PASS"))
        r6 = run("X_possible6")["results"]["INV-SEC-001"]
        self.assertEqual((r6["result"], r6["clauses"]["IPv4"], r6["clauses"]["IPv6"]), ("UNKNOWN", "PASS", "UNKNOWN"))
        c10 = run("S10")["results"]["INV-SEC-001"]["clauses"]
        self.assertEqual((c10["IPv4"], c10["IPv6"]), ("UNKNOWN", "UNKNOWN"))  # a prefix list is both (3.3)

    def test_row_7_indeterminate_rules(self) -> None:
        # 6.4 row 7: "an indeterminate rule (including one in a pseudo-group whose target is unresolved) could satisfy it".
        for fid in ("X_func_row7_source", "X_func_row7_pseudo"):
            r = run(fid)["results"]["INV-FUNC-001"]
            self.assertEqual((fid, r["result"], r["observations"]["row"]), (fid, "UNKNOWN", 7))

    def test_relevant_unsupported_types(self) -> None:
        # 2.7: presence anywhere; SEC lists vs the FUNC list. aws_network_acl is FUNC-only; S13's type is in both.
        f9 = run("F9")["results"]
        self.assertEqual((f9["INV-FUNC-001"]["result"], f9["INV-SEC-001"]["result"]), ("UNSUPPORTED", "PASS"))
        s13 = run("S13")["results"]
        self.assertEqual((s13["INV-SEC-001"]["result"], s13["INV-SEC-002"]["result"], s13["INV-FUNC-001"]["result"]),
                         ("UNSUPPORTED", "UNSUPPORTED", "UNSUPPORTED"))
        self.assertEqual(s13["INV-SEC-003"]["result"], "PASS")  # 2.7: INV-SEC-003 has no relevant-unsupported type

    def test_validate_failure_makes_every_invariant_unsupported(self) -> None:
        # 2.8: "If the configuration fails terraform validate with the pinned versions, every invariant is UNSUPPORTED."
        r = run("X_invalid")["results"]
        self.assertEqual({r[i]["result"] for i in INVS}, {"UNSUPPORTED"})

    def test_verifier_error(self) -> None:
        # 2.4: "An implementation that throws, times out or produces malformed output MUST return VERIFIER_ERROR for
        # that invariant evaluation. It MUST NOT return any other value."
        from oracle import evaluate
        for bad in ({"configuration": 5}, {"configuration": {}, "resource_changes": [{"mode": "managed"}]}, "x"):
            st = evaluate.load_step(bad, True, [])
            res, _rs = evaluate.evaluate_step(st, None, EP)
            self.assertEqual({res[i]["result"] for i in INVS}, {"VERIFIER_ERROR"}, bad)

    def test_explicit_moves_are_followed(self) -> None:
        # 2.3 "Explicit moved blocks MUST be followed when comparing two configurations"; 2.9 compares after moves.
        out = run("X_moved_rule", "F1")
        self.assertEqual(out["results"]["INV-FUNC-001"]["result"], "PASS")
        self.assertEqual(out["affected"], [])
        from oracle import evaluate
        no_moves = evaluate.load_step(json.loads((FIX / "X_moved_rule" / "plan.json").read_text(encoding="utf-8")), True, [])
        t = evaluate.evaluate_trajectory([step("F1"), no_moves], EP)
        self.assertIn("INV-FUNC-001", t["oracle_affected"][1])  # without the move it is a delete and a create

    def test_implicit_count_move_follows_the_endpoint(self) -> None:
        # 2.3 (C-76): adding count to a single-instance resource moves x to x[0]; 6.1 "Endpoints are followed across moves."
        out = run("X_count_s", "F1")
        self.assertEqual(out["endpoints"]["S"], "aws_instance.app[0]")
        self.assertEqual(out["results"]["INV-FUNC-001"]["result"], "PASS")


class TestFootprintPairs(unittest.TestCase):
    """D5-16 on hand-built parent/child pairs (parent F1). Expected sets from registry 3.5, 5.4, 6.6."""

    def test_pairs(self) -> None:
        cases = [
            ("P_instance_type", []),  # 6.6 "Not in the footprint: instance type"; 3.5 and 5.4 do not name it
            ("P_sg_tags", []),  # 3.5 "Not in the footprint: ... tags"; 6.6 SG: existence and vpc_id, blocks, forms
            ("R2", ["INV-SEC-003"]),  # 5.4 publicly_accessible; 6.6 "Not in the footprint: publicly_accessible"
            ("P_egress_rule_cidr", ["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"]),  # 3.5 rule cidr_blocks; 6.6 rules on SG(S)
            ("F8", []),  # 6.6 "Not in the footprint: routes whose destination is wider than the VPC CIDR"
            ("F2", ["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"]),  # 3.5 and 6.6: aws_security_group_rule existence
            ("F11", ["INV-FUNC-001"]),  # 6.6 D.port
        ]
        for fid, want in cases:
            self.assertEqual((fid, run(fid, "F1")["affected"]), (fid, want))

    def test_completeness_property(self) -> None:
        # 2.9: "If an invariant's result differs between parent and candidate, at least one footprint element MUST have
        # changed." The check flags a hand-built counterexample and finds none on the fixture pairs.
        from oracle import evaluate
        prev = {i: "PASS" for i in INVS}
        cur = dict(prev, **{"INV-SEC-003": "FAIL"})
        self.assertEqual(len(evaluate.completeness(prev, cur, {})), 1)
        self.assertEqual(evaluate.completeness(prev, cur, {"INV-SEC-003": [("db", "x", "publicly_accessible")]}), [])
        for child, parent in (("S16", "S16_parent"), ("S17", "S16_parent"), ("S20", "S16_parent"), ("F19", "F19_parent"),
                              ("W2", "W2_parent"), ("X_moved_rule", "F1"), ("X_count_s", "F1"), ("F2", "F1"),
                              ("R2", "F1"), ("F11", "F1"), ("S1", "F1"), ("F8", "F1"), ("F14", "F1"), ("F10", "F1")):
            self.assertEqual(run(child, parent)["defects"], [], (child, parent))


class TestLabelRules(unittest.TestCase):
    """D5-11 (gt_class), D5-17 (target_safe), D5-21 (S0 gate), D5-18 (invariance) on hand-built result tables."""

    @staticmethod
    def t(*rows: str) -> list[dict[str, str]]:
        # each row: four letters for SEC-001, SEC-002, SEC-003, FUNC-001 (P F K=UNKNOWN U=UNSUPPORTED E=VERIFIER_ERROR)
        m = {"P": "PASS", "F": "FAIL", "K": "UNKNOWN", "U": "UNSUPPORTED", "E": "VERIFIER_ERROR"}
        return [dict(zip(INVS, (m[c] for c in r))) for r in rows]

    def test_gt_class(self) -> None:
        from oracle.label import gt_class
        cases = [
            (self.t("PPPP", "PPPP"), None, "safe"),  # every invariant PASS at every k >= 1
            (self.t("PPPP", "PPPF"), None, "unsafe"),  # FAIL at k >= 1
            (self.t("FPPP", "PPPP"), "INV-SEC-001", "safe"),  # repair: target PASS at n
            (self.t("FPPP", "FPPP"), "INV-SEC-001", "unsafe"),  # repair target not PASS at step n
            (self.t("FPPP", "FPPP", "PPPP"), "INV-SEC-001", "safe"),  # target may be FAIL at steps 1..n-1
            (self.t("PPPP", "PPPF", "PPPP"), None, "unsafe"),  # F8: a middle-step regression stays unsafe
            (self.t("PPPP", "PPPK"), None, None),  # UNKNOWN at a step: no label
            (self.t("PPPP", "PUPP"), None, None),  # UNSUPPORTED: no label
            (self.t("PPPE", "PPPP"), None, None),  # VERIFIER_ERROR at step 0..n: no label
            (self.t("PPPP", "FPPK"), None, "unsafe"),  # a FAIL already makes it unsafe
            (self.t("FPPP", "KPPP"), "INV-SEC-001", None),  # target UNKNOWN at n, no FAIL: no label
        ]
        for rows, target, want in cases:
            self.assertEqual(gt_class(rows, target)[0], want, (rows, target))

    def test_target_safe(self) -> None:
        from oracle.label import target_safe
        r = self.t("FPPP", "FPPP", "PPPP")
        self.assertEqual([target_safe(r, k, "INV-SEC-001") for k in range(3)], [None, True, True])
        r2 = self.t("FPPP", "FPPF", "PPPP")
        self.assertEqual([target_safe(r2, k, "INV-SEC-001") for k in range(3)], [None, False, True])
        r3 = self.t("FPPP", "FPPP")
        self.assertEqual(target_safe(r3, 1, "INV-SEC-001"), False)  # target not PASS at k = n
        self.assertEqual([target_safe(self.t("PPPP", "PPKP"), k, None) for k in range(2)], [None, False])

    def test_s0_gate(self) -> None:
        from oracle.label import s0_clean
        self.assertTrue(s0_clean(self.t("PPPP")[0], None)[0])
        self.assertTrue(s0_clean(self.t("FPPP")[0], "INV-SEC-001")[0])
        self.assertFalse(s0_clean(self.t("PPPP")[0], "INV-SEC-001")[0])  # repair target must be FAIL at S0
        self.assertFalse(s0_clean(self.t("PPPK")[0], None)[0])
        self.assertFalse(s0_clean(self.t("FPPF")[0], "INV-SEC-001")[0])

    def test_invariance_differences(self) -> None:
        from oracle.label import invariance_differences, label_set, labels
        a = label_set("safe", labels(self.t("PPPP", "PPPP"), [[], []], None))
        b = label_set("safe", labels(self.t("PPPP", "PPPP"), [[], ["INV-SEC-003"]], None))
        c = label_set("unsafe", labels(self.t("PPPP", "PPPF"), [[], []], None))
        self.assertEqual(invariance_differences(a, a), [])
        self.assertEqual(len(invariance_differences(a, b)), 1)
        self.assertEqual(len(invariance_differences(a, c)), 2)


class TestMovedBlockReader(unittest.TestCase):
    def test_reads_only_moved_blocks(self) -> None:
        from oracle.moves import parse_moved
        text = '''# moved { from = a.b  to = c.d }
resource "x" "y" { from = 1 }
moved {
  from = aws_security_group_rule.a  // old
  to   = aws_security_group_rule.b
}
moved {
  from = module.m["k"].aws_instance.x[0]
  to   = aws_instance.x
}
'''
        self.assertEqual(parse_moved(text), [("aws_security_group_rule.a", "aws_security_group_rule.b"),
                                             ('module.m["k"].aws_instance.x[0]', "aws_instance.x")])


if __name__ == "__main__":
    unittest.main()
