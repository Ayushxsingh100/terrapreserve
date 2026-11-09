"""Tests for D4b review round 5: clean real-world start states (D4b-14, D4b-15). Written test-first.

Every test runs over all of ``scenarios/dev/`` and, when ``TERRAPRESERVE_PRIVATE`` names an existing
directory, over all of that directory (the withheld test split). Without it the private part is skipped
and the reason is printed.

Registry v1.0 C-64 puts every security group of the configuration in scope, attached or not, so the
security invariants are read over the WHOLE module of a step: all ``.tf`` files of the step directory
(verbatim host files, the graft, versions and variables). The reader is ``generator/realworld/modread.py``.
It is a generator self-check, NOT the oracle, and it is not a label.

Tests:
1. Whole-module SEC at S0: no group, alone or together per port, covers 0.0.0.0/0 or ::/0 on TCP 22
   (INV-SEC-001) or TCP 5432 (INV-SEC-002). The repair target is exempt only for its own invariant at S0;
   host files (everything except the graft) are never exempt.
2. SEC-003 at S0: no ``aws_db_instance`` has ``publicly_accessible = true`` unless it is the repair target;
   a value that does not resolve to a literal fails the test.
3. No relevant-unsupported type (registry 2.7) in any step.
4. No MIXED group and no RETAINED-INLINE group in any step, host groups included.
5. Registry indeterminacy (3.3, 3.4, 5.4, 6.4 row 7), in every step: no group (configured or pseudo) has
   possible4 or possible6 for TCP 22 or 5432; no aws_db_instance has an unresolved publicly_accessible;
   no indeterminate rule that could permit TCP/5432 belongs to a group in SG(S) or SG(D) or to a
   pseudo-group. An unresolved value that cannot affect any of the four results never fails the test.
6. INV-FUNC-001 at S0 is PASS (E2 included, both endpoints bound to non-empty vpc_security_group_ids).
7. Final-step intent over the whole module: INV-SEC-00x in intent.breaks <=> violated at the last step;
   every SEC invariant in intent.preserves holds at every step (the repair target is exempt before the last step).
8. No derived natives in v1.0: no scenario has ``derived: true``.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import test_d4b_review_round4 as r4  # noqa: E402  (module import: its TestCase is not re-collected)
from realworld import modread  # noqa: E402

SEC_INVS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003")
GRAFT_PREFIXES = ("aws_security_group.tp_", "aws_db_instance.tp_")
FIRST_PARTY_FILES = ("terrapreserve_graft.tf", "terrapreserve_graft_variables.tf", "terrapreserve_versions.tf")

_MOVED_RE = re.compile(r"moved\s*\{[^}]*?from\s*=\s*(\S+)[^}]*?to\s*=\s*(\S+)[^}]*?\}", re.S)


def step_files(step_dir: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(step_dir.glob("*.tf"))}


def whole(sc: r4.Sc, k: int) -> modread.Analysis:
    return modread.analyse(step_files(sc.step_dirs()[k]))


def host_only(sc: r4.Sc, k: int) -> modread.Analysis:
    files = {n: t for n, t in step_files(sc.step_dirs()[k]).items() if n not in FIRST_PARTY_FILES}
    return modread.analyse(files)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_sec_s0(sc: r4.Sc) -> list[str]:
    out: list[str] = []
    target = sc.data["target"].get("invariant_id")
    an = whole(sc, 0)
    for inv in ("INV-SEC-001", "INV-SEC-002"):
        if inv == target:
            continue
        for where in an.violations.get(inv, []):
            out.append(f"{sc.id}/step_0: {inv} violated by {where}")
    if sc.data.get("grafted"):
        for inv, wheres in host_only(sc, 0).violations.items():
            if inv in ("INV-SEC-001", "INV-SEC-002"):
                for where in wheres:
                    out.append(f"{sc.id}/step_0: host file {where} violates {inv} (hosts are never exempt)")
    return out


def check_sec003_s0(sc: r4.Sc) -> list[str]:
    out: list[str] = []
    target = sc.data["target"].get("invariant_id")
    an = whole(sc, 0)
    if target != "INV-SEC-003":
        for where in an.violations.get("INV-SEC-003", []):
            out.append(f"{sc.id}/step_0: INV-SEC-003 violated by {where}")
    for u in an.unresolved_public:
        out.append(f"{sc.id}/step_0: {u}")
    if sc.data.get("grafted"):
        for where in host_only(sc, 0).violations.get("INV-SEC-003", []):
            out.append(f"{sc.id}/step_0: host file {where} is publicly accessible (hosts are never exempt)")
    return out


def check_unsupported_types(sc: r4.Sc) -> list[str]:
    out: list[str] = []
    for k in range(len(sc.step_dirs())):
        for addr in whole(sc, k).unsupported_types:
            out.append(f"{sc.id}/step_{k}: relevant-unsupported type {addr}")
    return out


def check_mixed_whole(sc: r4.Sc) -> list[str]:
    out: list[str] = []
    for k in range(len(sc.step_dirs())):
        for g in whole(sc, k).mixed:
            out.append(f"{sc.id}/step_{k}: MIXED group {g}")
    return out


def check_retained_inline_whole(sc: r4.Sc) -> list[str]:
    out: list[str] = []
    steps = sc.step_dirs()
    prev = modread.forms_of(step_files(steps[0]))
    for k in range(1, len(steps)):
        files = step_files(steps[k])
        cur = modread.forms_of(files)
        rename: dict[str, str] = {}
        for text in files.values():
            for frm, to in _MOVED_RE.findall(text):
                rename[frm] = to
        for addr, (p_in, p_out) in prev.items():
            new = rename.get(addr, addr)
            if new not in cur:
                continue
            c_in, c_out = cur[new]
            for d, before, after in (("ingress", p_in, c_in), ("egress", p_out, c_out)):
                if before == "blocks" and after == "absent":
                    out.append(f"{sc.id}/step_{k}: {new} {d} was blocks and is now absent (RETAINED-INLINE)")
        prev = cur
    return out


def _endpoint_groups(sc: r4.Sc, k: int) -> set[str]:
    """SG(S) and SG(D) of step k, from the first-party model; empty when the scenario has none."""
    if sc.model_file() is None:
        return set()
    m0 = sc.model(0)
    mk = sc.model(k)
    try:
        s_addr, d_addr = r4.endpoints(m0)  # type: ignore[arg-type]
        out: set[str] = set()
        for a in (s_addr, d_addr):
            res = mk.resources.get(a)  # type: ignore[union-attr]
            if res is not None and "vpc_security_group_ids" in res.attrs:
                out.update(r4.ref_list(res.attrs["vpc_security_group_ids"]))
        return out
    except r4.UnsupportedForm:
        return set()


def check_indeterminacy(sc: r4.Sc) -> list[str]:
    out: list[str] = []
    for k in range(len(sc.step_dirs())):
        an = whole(sc, k)
        for inv, wheres in sorted(an.possible.items()):
            for w in wheres:
                out.append(f"{sc.id}/step_{k}: {inv} possible (registry 3.3, UNKNOWN) for {w}")
        out += [f"{sc.id}/step_{k}: {u}" for u in an.unresolved_public]
        for holder in an.indeterminate_5432(_endpoint_groups(sc, k)):
            out.append(f"{sc.id}/step_{k}: indeterminate rule {holder} could permit TCP/5432 in SG(S), SG(D) "
                       "or a pseudo-group (registry 6.4 row 7)")
    return out


def check_func_s0(sc: r4.Sc) -> list[str]:
    if sc.model_file() is not None:
        model = sc.model(0)
        try:
            s_addr, d_addr = r4.endpoints(model)  # type: ignore[arg-type]
            v = r4.evaluate_func(model, s_addr, d_addr)  # type: ignore[arg-type]
        except r4.UnsupportedForm as exc:
            return [f"{sc.id}/step_0: INV-FUNC-001 not evaluable: {exc}"]
        return [] if v.status == "PASS" else [f"{sc.id}/step_0: INV-FUNC-001 is {v.status} (row {v.row}): {v.why}"]
    # No graft and no first-party model: a native module. E2 to E4 are read from the real text;
    # E5 and E6 are not evaluated for natives, so a native is never shown to be PASS.
    status, row, why = modread.native_func_precheck(step_files(sc.step_dirs()[0]))
    if status != "PASS?":
        return [f"{sc.id}/step_0: INV-FUNC-001 is {status} (row {row}): {why}"]
    return [f"{sc.id}/step_0: INV-FUNC-001 cannot be shown PASS for a native module (E5 and E6 not evaluated)"]


def check_intent_whole(sc: r4.Sc) -> list[str]:
    out: list[str] = []
    n = len(sc.step_dirs())
    per_step = [whole(sc, k).violations for k in range(n)]
    last = per_step[-1]
    for inv in SEC_INVS:
        if (inv in sc.breaks) != bool(last.get(inv)):
            state = "violated" if last.get(inv) else "not violated"
            out.append(f"{sc.id}: {inv} is {state} at the last step but "
                       f"{'is' if inv in sc.breaks else 'is not'} in intent.breaks")
        if inv in sc.preserves:
            target = sc.data["target"].get("invariant_id")
            for k, v in enumerate(per_step):
                if k < n - 1 and inv == target:
                    continue  # the repair target is violated from S0 until the repair step, by design
                if v.get(inv):
                    out.append(f"{sc.id}/step_{k}: intent preserves {inv} but it is violated by {v[inv][:2]}")
                    break
    return out


def check_not_derived(sc: r4.Sc) -> list[str]:
    return [f"{sc.id}: derived: true"] if sc.data.get("derived") else []


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

_CACHE: dict[str, list[r4.Sc]] = {}


def scenarios() -> list[r4.Sc]:
    if "all" not in _CACHE:
        _CACHE["all"] = r4.load_all()
        if not any(s == "test" for s, _ in r4.scenario_roots()):
            print(f"\n[round5] {r4.PRIVATE_ENV} is not set to an existing directory: "
                  "private test-split checks are skipped.", file=sys.stderr)
    return _CACHE["all"]


def _collect(fn: Callable[[r4.Sc], list[str]]) -> list[str]:
    out: list[str] = []
    for sc in scenarios():
        out.extend(fn(sc))
    return out


class TestD4bReviewRound5(unittest.TestCase):
    def assertNoViolations(self, found: list[str], label: str) -> None:
        self.assertGreater(len(scenarios()), 0, "no scenarios loaded")
        self.assertEqual(found, [], f"{label}: {len(found)} violation(s), first 10: {found[:10]}")

    def test_01_whole_module_sec_at_s0(self) -> None:
        """Rule: no group in the whole module covers 0.0.0.0/0 or ::/0 on TCP 22 or 5432 at S0 (C-64)."""
        self.assertNoViolations(_collect(check_sec_s0), "whole-module SEC-001/002 at S0")

    def test_02_sec003_at_s0(self) -> None:
        """Rule: no aws_db_instance is publicly_accessible at S0 (target exempt); unresolved values fail."""
        self.assertNoViolations(_collect(check_sec003_s0), "SEC-003 at S0")

    def test_03_no_relevant_unsupported_types(self) -> None:
        """Rule: no registry 2.7 relevant-unsupported type anywhere in any step."""
        self.assertNoViolations(_collect(check_unsupported_types), "relevant-unsupported types")

    def test_04_no_mixed_or_retained_inline_in_module(self) -> None:
        """Rule: no MIXED and no RETAINED-INLINE group anywhere in the module, host groups included."""
        self.assertNoViolations(_collect(check_mixed_whole) + _collect(check_retained_inline_whole),
                                "MIXED or RETAINED-INLINE groups")

    def test_05_registry_indeterminacy(self) -> None:
        """Rule: no possible4/possible6 for 22 or 5432, no unresolved publicly_accessible, no FUNC row 7 risk."""
        self.assertNoViolations(_collect(check_indeterminacy), "registry indeterminacy")

    def test_06_func_at_s0(self) -> None:
        """Rule: INV-FUNC-001 is PASS at S0 for every scenario (E2 included, both endpoints bound)."""
        self.assertNoViolations(_collect(check_func_s0), "INV-FUNC-001 at S0")

    def test_07_final_step_intent_whole_module(self) -> None:
        """Rule: SEC invariants in intent.breaks <=> violated at the last step, over the whole module."""
        self.assertNoViolations(_collect(check_intent_whole), "final-step SEC intent (whole module)")

    def test_08_no_derived_natives(self) -> None:
        """Rule (D4b-14): no scenario of v1.0 has derived: true."""
        self.assertNoViolations(_collect(check_not_derived), "derived natives")


if __name__ == "__main__":
    unittest.main()
