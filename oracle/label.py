"""Scenario labels from step results: gt_class (D5-11), target_safe (D5-17), S0 gate (D5-21), invariance (D5-18).

``results[k][inv]`` is the result string of invariant ``inv`` at step k (k = 0..n). ``target`` is the repair
target (``target.invariant_id`` when ``target.kind`` is ``repair``), else None. Standard library only.
"""

from __future__ import annotations

from typing import Any

from oracle.common import FAIL, INVARIANTS, PASS

DEFINITE = (PASS, FAIL)


def gt_class(results: list[dict[str, str]], target: str | None) -> tuple[str | None, str]:
    """(``safe`` | ``unsafe`` | None, reason). D5-11."""
    n = len(results) - 1
    fails = []
    for k in range(1, n + 1):
        for inv in INVARIANTS:
            if results[k][inv] != FAIL:
                continue
            if inv == target and k < n:
                continue  # the repair target may be FAIL at steps 1..n-1
            fails.append(f"{inv} FAIL at step {k}")
    if fails:
        return "unsafe", "; ".join(fails)
    others = [f"{inv} {results[k][inv]} at step {k}" for k in range(0, n + 1) for inv in INVARIANTS
              if results[k][inv] not in DEFINITE]
    if others:
        return None, "unlabelable: " + "; ".join(others)
    if target is not None and results[n][target] != PASS:
        return "unsafe", f"repair target {target} is {results[n][target]} at step {n}"
    return "safe", "every protected invariant PASS at every step k >= 1 (repair target PASS at step n)"


def target_safe(results: list[dict[str, str]], k: int, target: str | None) -> bool | None:
    """D5-17. None at step 0."""
    if k == 0:
        return None
    n = len(results) - 1
    others_ok = all(results[k][inv] == PASS for inv in INVARIANTS if inv != target)
    target_ok = target is None or results[k][target] == PASS or k < n
    return bool(others_ok and target_ok)


def s0_clean(results0: dict[str, str], target: str | None) -> tuple[bool, str]:
    """D5-21 (D0 gate 3): at step 0 every invariant except the repair target is PASS; the repair target is FAIL."""
    bad = [f"{inv} {results0[inv]}" for inv in INVARIANTS
           if (inv == target and results0[inv] != FAIL) or (inv != target and results0[inv] != PASS)]
    return (not bad), "; ".join(bad)


def labels(results: list[dict[str, str]], affected: list[list[str]], target: str | None) -> list[dict[str, Any]]:
    """The D0 Decision 6 ``labels`` list."""
    return [{"step": k, "invariant_truth": {inv: results[k][inv] for inv in INVARIANTS},
             "oracle_affected": list(affected[k]), "target_safe": target_safe(results, k, target)}
            for k in range(len(results))]


def label_set(cls: str | None, label_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """One value set's labels of a scenario: ``{gt_class, labels}`` (compared by ``invariance_differences``)."""
    return {"gt_class": cls, "labels": label_rows}


def invariance_differences(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """D5-18: differences in invariant_truth, oracle_affected or gt_class between two label sets."""
    out = []
    if a["gt_class"] != b["gt_class"]:
        out.append(f"gt_class {a['gt_class']} != {b['gt_class']}")
    for la, lb in zip(a["labels"], b["labels"]):
        for inv in INVARIANTS:
            if la["invariant_truth"][inv] != lb["invariant_truth"][inv]:
                out.append(f"step {la['step']} {inv}: {la['invariant_truth'][inv]} != {lb['invariant_truth'][inv]}")
        if sorted(la["oracle_affected"]) != sorted(lb["oracle_affected"]):
            out.append(f"step {la['step']} oracle_affected {la['oracle_affected']} != {lb['oracle_affected']}")
    return out


def repair_target(scenario: dict[str, Any]) -> str | None:
    t = scenario.get("target") or {}
    return t.get("invariant_id") if t.get("kind") == "repair" else None
