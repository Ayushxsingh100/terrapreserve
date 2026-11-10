"""Evaluate one step, and a trajectory of steps (D5-14 to D5-16).

* ``load_step``: a plan JSON document (or none, when ``terraform validate`` failed) with the step's ``moved`` blocks.
* ``evaluate_step``: the four invariant results with their 2.10 evidence. A configuration that fails ``terraform
  validate`` gives UNSUPPORTED for every invariant (2.8). Any exception, or a malformed plan JSON document, gives
  VERIFIER_ERROR for the invariant concerned (2.4); nothing else is returned in that case.
* ``evaluate_trajectory``: steps 0..n with the parent of step k being step k - 1 (2.1, D5-15), endpoints followed
  across moves (6.1, 2.3), ``oracle_affected`` (2.9, D5-16) and the completeness check.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from oracle import footprint, func_reach, moves, rules, sec_public_ingress, sec_rds_public
from oracle.common import INVARIANTS, UNSUPPORTED, VERIFIER_ERROR
from oracle.model import Config, build


@dataclass
class Step:
    valid: bool
    config: Config | None
    content_hash: str
    error: str = ""
    moved: list[tuple[str, str]] = field(default_factory=list)


def load_step(plan: Any, valid: bool, moved: list[tuple[str, str]] | None = None) -> Step:
    """``plan``: the parsed plan JSON (ignored when ``valid`` is False)."""
    moved = list(moved or [])
    if not valid:
        return Step(valid=False, config=None, content_hash="", moved=moved)
    try:
        text = json.dumps(plan, sort_keys=True)
        h = hashlib.sha256(json.dumps(plan.get("configuration"), sort_keys=True).encode()).hexdigest()
    except (TypeError, ValueError, AttributeError) as exc:
        return Step(valid=True, config=None, content_hash="", error=f"malformed plan JSON: {exc}", moved=moved)
    _ = text
    try:
        cfg = build(plan, moved)
    except Exception as exc:  # noqa: BLE001  (2.4: any failure of the oracle is VERIFIER_ERROR)
        return Step(valid=True, config=None, content_hash=h, error=f"{type(exc).__name__}: {exc}", moved=moved)
    return Step(valid=True, config=cfg, content_hash=h, moved=moved)


def _error(inv: str, msg: str) -> dict[str, Any]:
    return {"invariant_id": inv, "invariant_version": 1, "result": VERIFIER_ERROR, "error": msg[:500],
            "observations": {}, "assumptions": [], "ambiguities": []}


def parent_map(parent: Step | None, child: Step) -> dict[str, str]:
    if parent is None or parent.config is None or child.config is None:
        return {}
    return moves.parent_to_child_map(child.moved, set(parent.config.instances), set(child.config.instances))


def follow(endpoints: dict[str, str], pmap: dict[str, str]) -> dict[str, str]:
    """Endpoints of the child: the parent's endpoint addresses after following moves (6.1)."""
    return {k: pmap.get(v, v) for k, v in endpoints.items()}


def evaluate_step(step: Step, parent: Step | None, endpoints: dict[str, str]) -> tuple[dict[str, dict], Any]:
    """(results by invariant, the rule set or None). ``endpoints`` are this step's (already followed)."""
    if not step.valid:
        return ({inv: {"invariant_id": inv, "invariant_version": 1, "result": UNSUPPORTED,
                       "observations": {"reason": "terraform validate failed (registry 2.8)"}, "assumptions": [],
                       "ambiguities": []} for inv in INVARIANTS}, None)
    if step.config is None:
        return {inv: _error(inv, step.error) for inv in INVARIANTS}, None
    out: dict[str, dict] = {}
    pmap = parent_map(parent, step)
    try:
        rs = rules.build(step.config, parent.config if parent is not None else None, pmap)
    except Exception as exc:  # noqa: BLE001
        rs = None
        err = f"{type(exc).__name__}: {exc}"
    for inv, fn in (("INV-SEC-001", lambda: sec_public_ingress.evaluate(step.config, rs, 22)),
                    ("INV-SEC-002", lambda: sec_public_ingress.evaluate(step.config, rs, 5432)),
                    ("INV-SEC-003", lambda: sec_rds_public.evaluate(step.config)),
                    ("INV-FUNC-001", lambda: func_reach.evaluate(step.config, rs, endpoints))):
        if rs is None and inv != "INV-SEC-003":
            out[inv] = _error(inv, err)
            continue
        try:
            r = fn()
        except Exception as exc:  # noqa: BLE001
            r = _error(inv, f"{type(exc).__name__}: {exc}")
        r["content_hash"] = step.content_hash
        if rs is not None and inv != "INV-SEC-003":
            r["ambiguities"] = sorted(set(r.get("ambiguities", [])) | set(rs.ambiguities))
            r.setdefault("observations", {})["plan_json_notes"] = rs.notes
        out[inv] = r
    return out, rs


def completeness(parent: dict[str, str], child: dict[str, str], changed: dict[str, list]) -> list[str]:
    """Registry 2.9: a result that differs between parent and candidate with no changed footprint element."""
    return [f"{inv}: result {parent[inv]} -> {child[inv]} with no changed footprint element (registry 2.9 completeness)"
            for inv in INVARIANTS if parent[inv] != child[inv] and not changed.get(inv)]


def evaluate_trajectory(steps: list[Step], endpoints0: dict[str, str]) -> dict[str, Any]:
    """Every step's results, the endpoints per step, oracle_affected per step and completeness defects."""
    results: list[dict[str, dict]] = []
    rulesets: list[Any] = []
    endpoints: list[dict[str, str]] = []
    affected: list[list[str]] = []
    changed: list[dict[str, list]] = []
    defects: list[str] = []
    for k, st in enumerate(steps):
        parent = steps[k - 1] if k else None
        pmap = parent_map(parent, st)
        ep = dict(endpoints0) if k == 0 else follow(endpoints[k - 1], pmap)
        endpoints.append(ep)
        res, rs = evaluate_step(st, parent, ep)
        results.append(res)
        rulesets.append(rs)
        if k == 0:
            affected.append([])
            changed.append({})
            continue
        if rs is None or rulesets[k - 1] is None:
            # A step that could not be read: every footprint is treated as changed (nothing is known to be equal).
            ch = {inv: [("<step not readable>",)] for inv in INVARIANTS}
        else:
            c2p = {c: p for p, c in pmap.items()}
            gp = steps[k - 2] if k >= 2 else None
            p_c2p = {c: p for p, c in parent_map(gp, parent).items()} if gp is not None else {}
            child_side = footprint.Side(st.config, rs, rulesets[k - 1], c2p, ep)
            parent_side = footprint.Side(parent.config, rulesets[k - 1], rulesets[k - 2] if k >= 2 else None,
                                         p_c2p, endpoints[k - 1])
            try:
                ch = footprint.affected(parent_side, child_side, pmap)
            except Exception as exc:  # noqa: BLE001
                ch = {inv: [("<footprint error>", str(exc))] for inv in INVARIANTS}
        changed.append(ch)
        affected.append([inv for inv in INVARIANTS if ch.get(inv)])
        defects.extend(f"step {k} {d}" for d in completeness(
            {inv: results[k - 1][inv]["result"] for inv in INVARIANTS},
            {inv: results[k][inv]["result"] for inv in INVARIANTS}, ch))
    return {"results": results, "endpoints": endpoints, "oracle_affected": affected, "changed": changed,
            "defects": defects}
