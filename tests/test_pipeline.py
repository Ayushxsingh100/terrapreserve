"""pool/cascade.py: processing plan (E10, sampling), the E09 -> E11 -> E12 loop with its stop rules and resume,
and the ledger arithmetic (D3-10, acceptance A3/A4). Fake steps only; nothing here touches the network or Terraform.
"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pool import cascade, licence, redact, validate  # noqa: E402

CLEAN = redact.SecretsResult(0, 0, (), ())


class FakeSteps:
    """Scripted outcomes per module id; records which steps ran."""

    def __init__(self, secrets=(), licence_bad=(), invalid=(), errors=()) -> None:
        self.secret_ids, self.licence_bad, self.invalid, self.errors = set(secrets), set(licence_bad), set(invalid), set(errors)
        self.calls: list[tuple[str, int]] = []

    def secrets(self, mid: int) -> redact.SecretsResult:
        self.calls.append(("E09", mid))
        return redact.SecretsResult(1, 0, ("aws-access-token",), ()) if mid in self.secret_ids else CLEAN

    def licence(self, mid: int) -> licence.Check:
        self.calls.append(("E11", mid))
        outcome = "mismatch" if mid in self.licence_bad else "found"
        return licence.Check(mid, "o/r", "a" * 40, "LICENSE", 200, 10, "0" * 64, "MIT", "MIT", outcome, "")

    def validate(self, mid: int) -> validate.Result:
        self.calls.append(("E12", mid))
        if mid in self.errors:
            return validate.Result("error", "1.15.8", "6.53.0", "timeout after 180 s")
        if mid in self.invalid:
            return validate.Result("invalid", "1.15.8", "6.53.0", "Unsupported argument")
        return validate.Result("valid", "1.15.8", "6.53.0", "")


def run(plan: cascade.Plan, steps: FakeSteps, records=None, **kw):
    records = {} if records is None else records
    appended: list[dict] = []
    cascade.process_all(plan, steps, records, appended.append, **kw)
    return records, appended


class TestPlan(unittest.TestCase):
    def test_natives_all_kept_hosts_one_per_lineage_smallest_id(self) -> None:
        lineage_of = {1: "L1", 2: "L1", 10: "LA", 11: "LA", 12: "LB", 13: "LC", 14: "LC", 15: "L1"}
        plan = cascade.make_plan([1, 2], [10, 11, 12, 13, 14, 15], lineage_of)
        self.assertEqual(plan.natives, [1, 2])
        self.assertEqual(sorted(plan.hosts), [10, 12, 13, 15])
        self.assertEqual(plan.e10, {11: 10, 14: 13})
        # a host shares a lineage with natives (L1): it is still the only host of that lineage, so it stays

    def test_no_two_planned_hosts_share_a_lineage(self) -> None:
        lineage_of = {i: f"L{i % 7}" for i in range(100, 200)}
        plan = cascade.make_plan([], list(range(100, 200)), lineage_of)
        self.assertEqual(len({lineage_of[i] for i in plan.hosts}), len(plan.hosts))
        self.assertEqual(len(plan.hosts), 7)

    def test_order_is_the_seeded_shuffle_of_the_sorted_ids(self) -> None:
        ids = list(range(500, 540))
        lineage_of = {i: f"L{i}" for i in ids}
        expected = sorted(ids)
        random.Random(20261030).shuffle(expected)
        self.assertEqual(cascade.make_plan([], ids[::-1], lineage_of).hosts, expected)
        self.assertEqual(cascade.SEED, 20261030)
        self.assertEqual((cascade.HOST_ACCEPT_TARGET, cascade.HOST_PROCESS_CAP), (400, 1500))

    def test_native_order_is_by_id(self) -> None:
        plan = cascade.make_plan([9, 3, 5], [], {9: "a", 3: "b", 5: "c"})
        self.assertEqual(plan.natives, [3, 5, 9])


def plan_of(natives=(), hosts=()) -> cascade.Plan:
    return cascade.Plan(list(natives), list(hosts), {})


class TestLoop(unittest.TestCase):
    def test_first_failing_code_is_recorded_and_later_steps_do_not_run(self) -> None:
        steps = FakeSteps(secrets=[1], licence_bad=[2], invalid=[3])
        records, _ = run(plan_of(natives=[1, 2, 3, 4]), steps)
        self.assertEqual({m: r["code"] for m, r in records.items()},
                         {1: "E09_SECRET_FOUND", 2: "E11_LICENCE_UNVERIFIED", 3: "E12_INVALID_UNDER_PIN", 4: None})
        self.assertEqual([c for c in steps.calls if c[1] == 1], [("E09", 1)])
        self.assertEqual([c for c in steps.calls if c[1] == 2], [("E09", 2), ("E11", 2)])
        self.assertEqual([c for c in steps.calls if c[1] == 3], [("E09", 3), ("E11", 3), ("E12", 3)])

    def test_a_terraform_error_is_not_an_acceptance(self) -> None:
        records, _ = run(plan_of(natives=[7]), FakeSteps(errors=[7]))
        self.assertEqual(records[7]["code"], "E12_INVALID_UNDER_PIN")
        self.assertIn("error", records[7]["detail"])

    def test_records_carry_the_facts_the_pool_needs(self) -> None:
        records, appended = run(plan_of(natives=[4]), FakeSteps())
        r = records[4]
        self.assertEqual((r["kind"], r["code"]), ("native", None))
        self.assertEqual(r["secrets"]["gitleaks_findings"], 0)
        self.assertEqual(r["secrets"]["inventory_flagged"], 0)
        self.assertEqual(r["licence"]["outcome"], "found")
        self.assertEqual((r["validate"]["status"], r["validate"]["terraform_version"], r["validate"]["provider_version"]),
                         ("valid", "1.15.8", "6.53.0"))
        self.assertEqual(appended, [r])

    def test_natives_all_go_through_whatever_happens(self) -> None:
        steps = FakeSteps(secrets=list(range(1, 11)))
        records, _ = run(plan_of(natives=range(1, 11)), steps, accept_target=1, process_cap=1)
        self.assertEqual(sorted(records), list(range(1, 11)))

    def test_hosts_stop_when_the_accept_target_is_reached(self) -> None:
        steps = FakeSteps(secrets=[11, 13])
        records, _ = run(plan_of(hosts=range(10, 30)), steps, accept_target=3, process_cap=100)
        # 10 ok, 11 fail, 12 ok, 13 fail, 14 ok -> third acceptance
        self.assertEqual(sorted(records), [10, 11, 12, 13, 14])
        self.assertEqual(sum(1 for r in records.values() if r["code"] is None), 3)

    def test_hosts_stop_at_the_processing_cap_even_below_the_target(self) -> None:
        steps = FakeSteps(secrets=range(10, 30))
        records, _ = run(plan_of(hosts=range(10, 30)), steps, accept_target=3, process_cap=6)
        self.assertEqual(sorted(records), [10, 11, 12, 13, 14, 15])
        self.assertTrue(all(r["code"] == "E09_SECRET_FOUND" for r in records.values()))

    def test_hosts_follow_the_plan_order_not_id_order(self) -> None:
        records, _ = run(plan_of(hosts=[30, 10, 20, 40]), FakeSteps(), accept_target=2, process_cap=100)
        self.assertEqual(sorted(records), [10, 30])

    def test_resume_skips_finished_modules_and_counts_them(self) -> None:
        done = {10: {"module_id": 10, "kind": "host", "code": None}, 11: {"module_id": 11, "kind": "host", "code": "E09_SECRET_FOUND"}}
        steps = FakeSteps()
        records, appended = run(plan_of(hosts=[10, 11, 12, 13, 14]), steps, records=dict(done), accept_target=3, process_cap=100)
        self.assertEqual([m for _, m in steps.calls if _ == "E09"], [12, 13])
        self.assertEqual([r["module_id"] for r in appended], [12, 13])
        self.assertEqual(sorted(records), [10, 11, 12, 13])  # 10, 12, 13 accepted: target met

    def test_a_rerun_of_a_finished_plan_does_nothing(self) -> None:
        first, _ = run(plan_of(natives=[1], hosts=[10, 11]), FakeSteps(), accept_target=2, process_cap=9)
        steps = FakeSteps()
        _, appended = run(plan_of(natives=[1], hosts=[10, 11]), steps, records=dict(first), accept_target=2, process_cap=9)
        self.assertEqual((steps.calls, appended), ([], []))


class TestChecksFromRecords(unittest.TestCase):
    def test_a_check_is_rebuilt_from_the_saved_record_and_the_candidate(self) -> None:
        c = cascade.Candidate(5, 50, ".", "o/r", "a" * 40, "MIT", "host", False, 0, frozenset())
        record = {"module_id": 5, "kind": "host", "code": None, "licence": {
            "repo_id": 50, "file_name": "LICENSE", "http_status": 200, "bytes": 11, "sha256": "ab" * 32,
            "detected_spdx": "MIT", "terrads_spdx": "MIT", "outcome": "found", "detail": ""}}
        got = cascade.licence_checks_from_records({5: record}, {5: c})
        self.assertEqual(got, {50: licence.Check(50, "o/r", "a" * 40, "LICENSE", 200, 11, "ab" * 32, "MIT", "MIT", "found", "")})

    def test_records_without_a_licence_step_give_no_check(self) -> None:
        c = cascade.Candidate(5, 50, ".", "o/r", "a" * 40, "MIT", "host", False, 0, frozenset())
        record = {"module_id": 5, "kind": "host", "code": "E09_SECRET_FOUND", "licence": None}
        self.assertEqual(cascade.licence_checks_from_records({5: record}, {5: c}), {})

    def test_a_malformed_commit_is_not_copied_into_the_check(self) -> None:
        bad = "warning: x" + chr(10) + "a" * 40
        c = cascade.Candidate(5, 50, ".", "o/r", bad, "MIT", "host", False, 0, frozenset())
        record = {"module_id": 5, "kind": "host", "code": "E11_LICENCE_UNVERIFIED", "licence": {
            "repo_id": 50, "file_name": "", "http_status": 0, "bytes": 0, "sha256": "", "detected_spdx": "",
            "terrads_spdx": "MIT", "outcome": "error", "detail": "x"}}
        got = cascade.licence_checks_from_records({5: record}, {5: c})
        self.assertEqual(got[50].commit_sha, licence.MALFORMED)


class TestLedger(unittest.TestCase):
    @staticmethod
    def cands(kind: str, ids) -> list[cascade.Candidate]:
        return [cascade.Candidate(i, 100 + i, ".", f"o/r{i}", "c" * 40, "MIT", kind, False, 0, frozenset()) for i in ids]

    def test_every_candidate_is_accepted_excluded_or_not_processed_exactly_once(self) -> None:
        natives = self.cands("native", [1, 2, 3])
        hosts = self.cands("host", [10, 11, 12, 13, 14, 15])
        cheap = {2: ("E06_MODULE_CALLS", "1 module block(s)", "module call")}
        plan = cascade.Plan([1, 3], [10, 12, 13, 14, 15], {11: 10})
        records = {
            1: {"module_id": 1, "kind": "native", "code": None, "detail": "", "group": ""},
            3: {"module_id": 3, "kind": "native", "code": "E12_INVALID_UNDER_PIN", "detail": "invalid: x", "group": "x"},
            10: {"module_id": 10, "kind": "host", "code": None, "detail": "", "group": ""},
            12: {"module_id": 12, "kind": "host", "code": "E11_LICENCE_UNVERIFIED", "detail": "missing", "group": "missing"},
        }
        rows = cascade.ledger(natives + hosts, cheap, plan, records)
        self.assertEqual(len(rows), 9)
        self.assertEqual(len({r["module_id"] for r in rows}), 9)
        by = {r["module_id"]: (r["status"], r["code"]) for r in rows}
        self.assertEqual(by, {
            1: ("accepted", ""), 2: ("excluded", "E06_MODULE_CALLS"), 3: ("excluded", "E12_INVALID_UNDER_PIN"),
            10: ("accepted", ""), 11: ("excluded", "E10_LINEAGE_DUPLICATE"), 12: ("excluded", "E11_LICENCE_UNVERIFIED"),
            13: ("not_processed", "NOT_PROCESSED"), 14: ("not_processed", "NOT_PROCESSED"), 15: ("not_processed", "NOT_PROCESSED"),
        })

    def test_counts_add_up_per_kind(self) -> None:
        natives = self.cands("native", [1, 2])
        hosts = self.cands("host", [10, 11, 12])
        rows = cascade.ledger(natives + hosts, {}, cascade.Plan([1, 2], [10, 11, 12], {}),
                              {1: {"kind": "native", "code": None}, 2: {"kind": "native", "code": "E09_SECRET_FOUND", "detail": "", "group": ""},
                               10: {"kind": "host", "code": None}})
        counts = cascade.ledger_counts(rows, {"native": 2, "host": 3})
        self.assertEqual(counts["native"], {"considered": 2, "accepted": 1, "excluded": 1, "not_processed": 0})
        self.assertEqual(counts["host"], {"considered": 3, "accepted": 1, "excluded": 0, "not_processed": 2})

    def test_counts_refuse_to_balance_when_a_row_is_missing(self) -> None:
        rows = cascade.ledger(self.cands("native", [1, 2]), {}, cascade.Plan([1, 2], [], {}),
                              {1: {"kind": "native", "code": None}, 2: {"kind": "native", "code": None}})
        with self.assertRaises(AssertionError):
            cascade.ledger_counts(rows[:1], {"native": 2, "host": 0})

    def test_known_codes(self) -> None:
        self.assertEqual(cascade.LEDGER_CODES, cascade.CODES + ("NOT_PROCESSED",))


if __name__ == "__main__":
    unittest.main()
