#!/usr/bin/env python3
"""D5b labelling run (Steps 5 and 6): plans, oracle evaluation, invariance, S0 gate, gt_class, Checkov, write.

Labels come only from ``oracle/`` (CLAUDE.md rule 7); this tool runs Terraform through ``oracle.plan.Runner``
(offline, D5-04), hands the plan JSON to ``oracle.evaluate`` and ``oracle.label``, and writes what they return.

* ``--dry-run`` (Step 5): 10 dev scenarios chosen by a fixed rule (the lowest-numbered non-excluded scenario of each
  family, plus the next two lowest of F8), both value sets. Writes ``docs/d5b/dry_run.json`` (dev only) and
  nothing into ``scenario.json``. Exit status 3 when an ambiguity or a completeness defect was found (the work
  package stops there).
* ``--scan``: evaluates every non-excluded scenario of the given splits from the cached plans and writes a summary
  (dev: ``docs/d5b/scan_dev.json``; test: counts only, under ``$TERRAPRESERVE_PRIVATE``): ambiguities, completeness
  defects, results and invariance differences. Writes no label (used after the dry run to list every ambiguity the
  authors need to settle before Step 6).
* ``--plans`` (Step 6, first half): plans every step of every non-excluded scenario of the given splits under both
  value sets, cached outside the repository (dev: ``~/.terrapreserve-cache/d5b-plans``; test:
  ``$TERRAPRESERVE_PRIVATE/d5b-plans``), resumable.

Plan JSON of test-split steps is kept only under ``$TERRAPRESERVE_PRIVATE``; test ids are never printed (counts
only). Standard library only.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from oracle import evaluate, label, moves  # noqa: E402
from oracle import plan as oplan  # noqa: E402
from oracle.common import INVARIANTS  # noqa: E402

SETS = {"primary": "variable_values", "alternate": "variable_values_alt"}
CACHE = Path.home() / ".terrapreserve-cache"
DRY_OUT = REPO_ROOT / "docs" / "d5b" / "dry_run.json"


def private_root() -> Path | None:
    p = os.environ.get("TERRAPRESERVE_PRIVATE")
    return Path(p) if p and Path(p).is_dir() else None


def scenarios(splits: list[str]) -> list[tuple[str, Path, dict]]:
    out = []
    roots = []
    if "dev" in splits:
        roots.append(("dev", REPO_ROOT / "scenarios" / "dev"))
    if "test" in splits:
        priv = private_root()
        if priv is None:
            raise SystemExit("TERRAPRESERVE_PRIVATE is not set to an existing directory")
        roots.append(("test", priv))
    for split, root in roots:
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append((split, p, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


def plan_dir(split: str, vset: str, sid: str) -> Path:
    if split == "dev":
        return CACHE / "d5b-plans" / vset / sid
    priv = private_root()
    assert priv is not None
    return priv / "d5b-plans" / vset / sid


def step_dirs(p: Path, sc: dict) -> list[Path]:
    return [p / s["terraform_dir"] for s in sorted(sc["steps"], key=lambda s: s["step"])]


def cached_run(split: str, vset: str, sid: str, k: int) -> dict | None:
    f = plan_dir(split, vset, sid) / f"step_{k}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def save_run(split: str, vset: str, sid: str, k: int, res: dict) -> None:
    d = plan_dir(split, vset, sid)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"step_{k}.json").write_text(json.dumps(res, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def run_plans(jobs: list[tuple[str, Path, dict, str]], workers: int) -> dict[str, int]:
    """Plan every step of each (split, path, scenario, value set) job not yet cached. Counts only are returned."""
    terraform = shutil.which("terraform")
    if terraform is None:
        raise SystemExit("terraform not found")
    tasks = []
    for split, p, sc, vset in jobs:
        for k, sd in enumerate(step_dirs(p, sc)):
            if cached_run(split, vset, sc["scenario_id"], k) is None:
                tasks.append((split, sd, sc, vset, k))
    pool = [oplan.Runner(CACHE / "d5b-runners" / f"w{i}", terraform) for i in range(max(1, workers))]
    free = list(pool)
    lock = threading.Lock()
    counts = {"to run": len(tasks), "planned": 0, "invalid": 0, "failed": 0}
    print(f"steps to plan: {len(tasks)}", flush=True)

    def one(t):
        split, sd, sc, vset, k = t
        with lock:
            r = free.pop()
        try:
            res = r.run(sd, sc.get(SETS[vset]) or {})
        finally:
            with lock:
                free.append(r)
        save_run(split, vset, sc["scenario_id"], k, res)
        return res["status"]

    done = 0
    with cf.ThreadPoolExecutor(max_workers=len(pool)) as ex:
        for status in ex.map(one, tasks):
            counts[status] = counts.get(status, 0) + 1
            done += 1
            if done % 50 == 0:
                print(f"{done}/{len(tasks)} planned", flush=True)
    return counts


def evaluate_scenario(split: str, p: Path, sc: dict, vset: str) -> dict[str, Any]:
    """The oracle's verdict for one scenario under one value set (nothing is written)."""
    sid = sc["scenario_id"]
    steps = []
    plan_status = []
    for k, sd in enumerate(step_dirs(p, sc)):
        res = cached_run(split, vset, sid, k)
        if res is None:
            raise SystemExit(f"no cached plan for a step ({split}); run --plans first")
        plan_status.append(res["status"])
        steps.append(evaluate.load_step(res.get("plan"), res["status"] != "invalid", moves.read_moved(sd))
                     if res["status"] in ("planned", "invalid") else None)
    out: dict[str, Any] = {"value_set": vset, "plan_status": plan_status}
    if any(s is None for s in steps):
        out["unplannable"] = [k for k, s in enumerate(steps) if s is None]
        return out
    ep = sc.get("endpoints")
    s0 = steps[0].config
    if not isinstance(ep, dict) or s0 is None or ep.get("S") not in s0.instances or ep.get("D") not in s0.instances:
        out["unlabelable_binding"] = f"endpoint binding missing or not in S0: {ep}"
        return out
    traj = evaluate.evaluate_trajectory(steps, ep)
    target = label.repair_target(sc)
    results = [{inv: r[inv]["result"] for inv in INVARIANTS} for r in traj["results"]]
    cls, why = label.gt_class(results, target)
    ambiguities = sorted({a for r in traj["results"] for inv in INVARIANTS for a in r[inv].get("ambiguities", [])})
    out.update({
        "results": results, "oracle_affected": traj["oracle_affected"], "endpoints": traj["endpoints"],
        "gt_class": cls, "gt_reason": why, "target": target, "s0_clean": label.s0_clean(results[0], target),
        "labels": label.labels(results, traj["oracle_affected"], target), "defects": traj["defects"],
        "ambiguities": ambiguities,
        "func": [{"row": r["INV-FUNC-001"].get("observations", {}).get("row"),
                  "reason": r["INV-FUNC-001"].get("observations", {}).get("reason")} for r in traj["results"]],
        "evidence": traj["results"],
    })
    return out


def dry_run_choice(all_sc: list[tuple[str, Path, dict]]) -> list[tuple[str, Path, dict]]:
    """Step 5's fixed rule: per family the lowest-numbered non-excluded scenario, plus the next two lowest of F8."""
    dev = [(s, p, d) for s, p, d in all_sc if s == "dev" and d.get("excluded_from_v1") is None]
    dev.sort(key=lambda x: int(x[2]["scenario_id"].rsplit("-", 1)[1]))
    chosen = []
    for fam in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"):
        chosen.append(next(x for x in dev if x[2]["family"] == fam))
    f8 = [x for x in dev if x[2]["family"] == "F8" and x not in chosen]
    chosen.extend(f8[:2])
    return chosen


def scan(splits: list[str]) -> int:
    import collections
    for split in splits:
        summary: dict[str, Any] = {"scenarios": 0, "unplannable": 0, "unlabelable_binding": 0,
                                   "results": collections.Counter(), "gt_class": collections.Counter(),
                                   "ambiguity_kinds": collections.Counter(), "defects": 0, "value_dependent": 0,
                                   "s0_not_clean": 0}
        dev_detail: dict[str, Any] = {}
        for s_, p, d in scenarios([split]):
            if d.get("excluded_from_v1") is not None:
                continue
            summary["scenarios"] += 1
            per = {v: evaluate_scenario(s_, p, d, v) for v in SETS}
            if any("unplannable" in per[v] for v in SETS):
                summary["unplannable"] += 1
                continue
            if any("unlabelable_binding" in per[v] for v in SETS):
                summary["unlabelable_binding"] += 1
                continue
            diffs = label.invariance_differences(per["primary"], per["alternate"])
            summary["value_dependent"] += bool(diffs)
            pr = per["primary"]
            summary["s0_not_clean"] += not pr["s0_clean"][0]
            summary["gt_class"][str(pr["gt_class"])] += 1
            for r in pr["results"]:
                for inv, v in r.items():
                    summary["results"][f"{d['source']['tier']} {inv} {v}"] += 1
            amb = sorted({a for v in SETS for a in per[v]["ambiguities"]})
            defects = sorted({x for v in SETS for x in per[v]["defects"]})
            summary["defects"] += len(defects)
            for a in amb:
                summary["ambiguity_kinds"][_ambiguity_kind(a)] += 1
            flagged = amb or defects or diffs or pr["gt_class"] is None or not pr["s0_clean"][0]
            if split == "dev" and flagged:
                dev_detail[d["scenario_id"]] = {"ambiguities": amb, "defects": defects, "invariance_differences": diffs,
                                                "gt_class": pr["gt_class"], "gt_reason": pr["gt_reason"],
                                                "s0_clean": list(pr["s0_clean"]), "target": pr["target"]}
        summary = {k: (dict(sorted(v.items())) if isinstance(v, collections.Counter) else v) for k, v in summary.items()}
        out = REPO_ROOT / "docs" / "d5b" / "scan_dev.json" if split == "dev" else private_root() / "d5b_scan_test.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        doc = {"summary": summary, "scenarios": dev_detail} if split == "dev" else {"summary": summary}
        out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(split, json.dumps({k: summary[k] for k in summary if k != "results"}, indent=1), flush=True)
    return 0


def _ambiguity_kind(text: str) -> str:
    """The kind of an ambiguity message (its text without addresses), for counts."""
    import re
    t = re.sub(r"^[^:]*: ", "", text, count=1) if text.startswith(("aws_", "module.")) else text
    return re.sub(r"\[[^\]]*\]|'[^']*'|\{[^}]*\}", "", t)[:160]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--plans", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--splits", default="dev,test")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    splits = args.splits.split(",")
    if args.dry_run:
        chosen = dry_run_choice(scenarios(["dev"]))
        print("dry run:", [d["scenario_id"] for _s, _p, d in chosen], flush=True)
        print(run_plans([(s, p, d, v) for s, p, d in chosen for v in SETS], args.workers), flush=True)
        doc = {"rule": "per family the lowest-numbered non-excluded dev scenario, plus the next two lowest of F8",
               "scenarios": {}}
        stop = []
        for s, p, d in chosen:
            per = {v: evaluate_scenario(s, p, d, v) for v in SETS}
            diffs = label.invariance_differences(per["primary"], per["alternate"]) \
                if all("labels" in per[v] for v in SETS) else ["not labelled under both sets"]
            entry = {"family": d["family"], "intent_class": d["intent"]["class"], "tier": d["source"]["tier"],
                     "invariance_differences": diffs}
            for v in SETS:
                e = dict(per[v])
                e.pop("evidence", None)
                entry[v] = e
                stop += [f"{d['scenario_id']} {v}: {a}" for a in e.get("ambiguities", [])]
                stop += [f"{d['scenario_id']} {v}: {x}" for x in e.get("defects", [])]
            doc["scenarios"][d["scenario_id"]] = entry
        doc["stop_findings"] = sorted(set(stop))
        DRY_OUT.parent.mkdir(parents=True, exist_ok=True)
        DRY_OUT.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8", newline="\n")
        print(f"ambiguities and completeness defects: {len(doc['stop_findings'])}", flush=True)
        return 3 if doc["stop_findings"] else 0
    if args.plans:
        jobs = [(s, p, d, v) for s, p, d in scenarios(splits) if d.get("excluded_from_v1") is None for v in SETS]
        print(run_plans(jobs, args.workers), flush=True)
        return 0
    if args.scan:
        return scan(splits)
    ap.error("choose --dry-run, --plans or --scan")
    return 2


if __name__ == "__main__":
    sys.exit(main())
