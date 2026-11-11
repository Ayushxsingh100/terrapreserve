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
from oracle.VERSION import ORACLE_VERSION  # noqa: E402

SETS = {"primary": "variable_values", "alternate": "variable_values_alt"}
CACHE = Path.home() / ".terrapreserve-cache"
DRY_OUT = REPO_ROOT / "docs" / "d5b" / "dry_run.json"


def private_root() -> Path | None:
    p = os.environ.get("TERRAPRESERVE_PRIVATE")
    return Path(p) if p and Path(p).is_dir() else None


TIER: list[str | None] = [None]  # --tier: restrict to one tier (D4c-06)


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
                d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
                if TIER[0] is None or d["source"]["tier"] == TIER[0]:
                    out.append((split, p, d))
    return out


def plan_dir(split: str, vset: str, sid: str) -> Path:
    if split == "dev":
        return CACHE / "d5b-plans" / vset / sid
    priv = private_root()
    assert priv is not None
    return priv / "d5b-plans" / vset / sid


def step_dirs(p: Path, sc: dict) -> list[Path]:
    return [p / s["terraform_dir"] for s in sorted(sc["steps"], key=lambda s: s["step"])]


def step_hash(sc: dict, k: int) -> str | None:
    return next((s.get("content_hash") for s in sc["steps"] if s["step"] == k), None)


def hash_for(sc: dict, k: int) -> str | None:
    """The content hash a cached run must match: always for the controlled tier (regenerated in D4c), never for the
    real-world tier (its D5b runs carry no hash and its steps are unchanged)."""
    return step_hash(sc, k) if sc["source"]["tier"] == "controlled" else None


def cached_run(split: str, vset: str, sid: str, k: int, chash: str | None = None) -> dict | None:
    """The cached plan run of a step. D4c-06: with ``chash`` given, only a run that recorded that content hash is
    used (a run made before D4c, which records none, is planned again)."""
    f = plan_dir(split, vset, sid) / f"step_{k}.json"
    if not f.is_file():
        return None
    res = json.loads(f.read_text(encoding="utf-8"))
    if chash is not None and res.get("content_hash") != chash:
        return None
    return res


def save_run(split: str, vset: str, sid: str, k: int, res: dict, chash: str | None = None) -> None:
    d = plan_dir(split, vset, sid)
    d.mkdir(parents=True, exist_ok=True)
    if chash is not None:
        res = dict(res, content_hash=chash)
    (d / f"step_{k}.json").write_text(json.dumps(res, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def run_plans(jobs: list[tuple[str, Path, dict, str]], workers: int) -> dict[str, int]:
    """Plan every step of each (split, path, scenario, value set) job not yet cached. Counts only are returned."""
    terraform = shutil.which("terraform")
    if terraform is None:
        raise SystemExit("terraform not found")
    tasks = []
    for split, p, sc, vset in jobs:
        for k, sd in enumerate(step_dirs(p, sc)):
            if cached_run(split, vset, sc["scenario_id"], k, hash_for(sc, k)) is None:
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
        save_run(split, vset, sc["scenario_id"], k, res, hash_for(sc, k))
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
        res = cached_run(split, vset, sid, k, hash_for(sc, k))
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


# ---------------------------------------------------------------------------------------------------------------
# Step 6: the full labelling run
# ---------------------------------------------------------------------------------------------------------------

REGISTRY_TAG = "registry-v1.0"
CHECKOV_CHECKS = ("CKV_AWS_24", "CKV_AWS_277", "CKV_AWS_17")  # D5-19: the checks D5a recorded
CHECKOV_FOR = {"INV-SEC-001": ("CKV_AWS_24", "CKV_AWS_277"), "INV-SEC-003": ("CKV_AWS_17",)}
VENV_BIN = REPO_ROOT / ".venv-tools" / ("Scripts" if os.name == "nt" else "bin")
D5B_KINDS = ("unlabelable", "value_dependent", "s0_not_clean")  # D5-20 reasons this run adds


def d5a3_status(split: str, vset: str) -> dict[tuple[str, int], str]:
    """D5a-3's measured status per (scenario, step): ``success`` or ``failure`` (A5)."""
    import csv
    f = (REPO_ROOT / "docs" / "d5a3" / f"feasibility_dev_{vset}.csv" if split == "dev"
         else private_root() / f"d5a3_feasibility_test_{vset}.csv")
    with open(f, encoding="utf-8", newline="") as fh:
        return {(r["scenario_id"], int(r["step"])): r["status"] for r in csv.DictReader(fh)}


def plannable_comparison(splits: list[str]) -> dict[str, Any]:
    """A5: for every step of every scenario and both value sets, the oracle's plan status against D5a-3's."""
    out: dict[str, Any] = {}
    for split in splits:
        diffs: list[str] = []
        counts: dict[str, int] = {}
        for vset in SETS:
            ref = d5a3_status(split, vset)
            seen = set()
            for _s, p, sc in scenarios([split]):
                for k, _sd in enumerate(step_dirs(p, sc)):
                    key = (sc["scenario_id"], k)
                    seen.add(key)
                    res = cached_run(split, vset, sc["scenario_id"], k, hash_for(sc, k))
                    now = "missing" if res is None else ("success" if res["status"] == "planned" else "failure")
                    then = ref.get(key, "not measured")
                    counts[f"{vset} {now}"] = counts.get(f"{vset} {now}", 0) + 1
                    if now != then:
                        diffs.append(f"{sc['scenario_id']} step {k} {vset}: D5a-3 {then}, now {now}")
            diffs += [f"{sid} step {k} {vset}: measured by D5a-3, not a step now" for sid, k in sorted(set(ref) - seen)
                      if TIER[0] is None or (TIER[0] == "controlled") == (int(sid.rsplit("-", 1)[1]) <= 208)]
        out[split] = {"counts": dict(sorted(counts.items())), "differences": len(diffs),
                      "difference_list": diffs if split == "dev" else None}
    return out


def checkov_dir(split: str) -> Path:
    return (CACHE / "d5b-checkov") if split == "dev" else (private_root() / "d5b-checkov")


def run_checkov(jobs: list[tuple[str, str, int, Path]], workers: int) -> dict[str, int]:
    """D5-19: Checkov 3.3.30 on a pristine copy of each step's ``.tf`` files (as in D5a), cached and resumable."""
    import subprocess
    import tempfile
    import time
    exe, py = VENV_BIN / "checkov", VENV_BIN / ("python.exe" if os.name == "nt" else "python")
    if not exe.exists():
        raise SystemExit(f"checkov not found at {exe}")
    def cached(j) -> bool:
        f = checkov_dir(j[0]) / j[1] / f"step_{j[2]}.json"
        if not f.is_file():
            return False
        return len(j) < 5 or j[4] is None or json.loads(f.read_text(encoding="utf-8")).get("content_hash") == j[4]

    todo = [j for j in jobs if not cached(j)]
    print(f"checkov steps to run: {len(todo)}", flush=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}
    env.update(PYTHONUTF8="1", AWS_SHARED_CREDENTIALS_FILE=os.devnull, AWS_CONFIG_FILE=os.devnull)
    work = CACHE / "d5b-checkov-work"
    work.mkdir(parents=True, exist_ok=True)

    def one(j):
        split, sid, k, sd = j[:4]
        t0 = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="tp-ckv-", dir=work) as tmp:
            for f in sd.glob("*.tf"):
                shutil.copyfile(f, Path(tmp) / f.name)
            try:
                ck = subprocess.run([str(py), str(exe), "-d", tmp, "--framework", "terraform", "--check",
                                     ",".join(CHECKOV_CHECKS), "--skip-download", "--quiet", "--compact", "-o", "json"],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                                    timeout=900, cwd=tmp)
                out, rc = ck.stdout, ck.returncode
            except subprocess.TimeoutExpired:
                out, rc = "", -1
        rec: dict[str, Any] = {"ran": False, "failed": [], "passed": [], "seconds": round(time.monotonic() - t0, 2)}
        if len(j) > 4 and j[4] is not None:
            rec["content_hash"] = j[4]
        try:
            doc = json.loads(out) if out.strip() else None
        except json.JSONDecodeError:
            doc = None
        if rc in (0, 1) and doc is not None:
            docs = doc if isinstance(doc, list) else [doc]
            rec["ran"] = True
            for dd in docs:
                res = (dd or {}).get("results") or {}
                for kind in ("failed", "passed"):
                    for c in res.get(f"{kind}_checks") or []:
                        rec[kind].append({"check_id": c.get("check_id"), "resource": c.get("resource")})
        else:
            rec["error"] = f"exit {rc}"
        d = checkov_dir(split) / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"step_{k}.json").write_text(json.dumps(rec, sort_keys=True), encoding="utf-8")
        return rec["ran"]

    counts = {"ran": 0, "not ran": 0}
    done = 0
    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for ok in ex.map(one, todo):
            counts["ran" if ok else "not ran"] += 1
            done += 1
            if done % 50 == 0:
                print(f"checkov {done}/{len(todo)}", flush=True)
    return counts


def checkov_disagreements(split: str, sid: str, results: list[dict[str, str]]) -> tuple[list[dict], list[str]]:
    """D5-19: per labelled step, Checkov's verdict for INV-SEC-001 (CKV_AWS_24, CKV_AWS_277) and INV-SEC-003
    (CKV_AWS_17) against the oracle's result. Advisory only: nothing here changes a label."""
    dis, errors = [], []
    for k, r in enumerate(results):
        f = checkov_dir(split) / sid / f"step_{k}.json"
        rec = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {"ran": False, "error": "not run"}
        if not rec["ran"]:
            errors.append(f"step {k}: {rec.get('error')}")
            continue
        for inv, checks in CHECKOV_FOR.items():
            failed = sorted({c["resource"] for c in rec["failed"] if c["check_id"] in checks})
            ck = "FAIL" if failed else "PASS"
            if ck != r[inv]:
                dis.append({"step": k, "invariant": inv, "oracle": r[inv], "checkov": ck,
                            "checkov_checks": list(checks), "checkov_failed_resources": failed})
    return dis, errors


def decide(split: str, p: Path, sc: dict) -> dict[str, Any]:
    """D5-18, D5-21, D5-11 in the package's order, for a scenario D5a-3 did not exclude. Both value sets."""
    per = {v: evaluate_scenario(split, p, sc, v) for v in SETS}
    out: dict[str, Any] = {"per_set": per}
    if any("unplannable" in per[v] for v in SETS):
        out["stop"] = "a step did not plan (A5)"
        return out
    if any("unlabelable_binding" in per[v] for v in SETS):
        out["exclude"] = ("unlabelable", per["primary"].get("unlabelable_binding")
                          or per["alternate"]["unlabelable_binding"])
        return out
    defects = sorted({x for v in SETS for x in per[v]["defects"]})
    ambiguities = sorted({a for v in SETS for a in per[v]["ambiguities"]})
    if defects or ambiguities:
        out["stop"] = f"{len(defects)} completeness defects, {len(ambiguities)} ambiguities"
        out["defects"], out["ambiguities"] = defects, ambiguities
        return out
    diffs = label.invariance_differences(per["primary"], per["alternate"])
    out["invariance_differences"] = diffs
    pr = per["primary"]
    if diffs:
        out["exclude"] = ("value_dependent", f"{len(diffs)} differences between the value sets; first: {diffs[0]}")
    elif not pr["s0_clean"][0]:
        out["exclude"] = ("s0_not_clean", f"step 0: {pr['s0_clean'][1]}")
    elif pr["gt_class"] is None:
        out["exclude"] = ("unlabelable", pr["gt_reason"])
    return out


def versions(sc: dict, plan_doc: dict | None) -> dict[str, Any]:
    """D0 gate 9 versions, as measured: Terraform from the plan JSON, the provider from the runner's lock file,
    Checkov from ``checkov --version``."""
    return {"terraform": (plan_doc or {}).get("terraform_version"), "provider_hashicorp_aws": PROVIDER_VERSION[0],
            "checkov": CHECKOV_VERSION[0], "oracle": ORACLE_VERSION, "generator": sc.get("generator_version"),
            "value_rule": sc.get("variable_values_rule"), "registry": REGISTRY_TAG, "value_set": "primary"}


PROVIDER_VERSION: list[str | None] = [None]
CHECKOV_VERSION: list[str | None] = [None]


def measure_tool_versions() -> None:
    import re
    import subprocess
    lock = next((CACHE / "d5b-runners").glob("w*/seed/.terraform.lock.hcl"), None)
    if lock is not None:
        m = re.search(r'provider "registry\.terraform\.io/hashicorp/aws" \{\s*version\s*=\s*"([^"]+)"',
                      lock.read_text(encoding="utf-8"))
        PROVIDER_VERSION[0] = m.group(1) if m else None
    py = VENV_BIN / ("python.exe" if os.name == "nt" else "python")
    r = subprocess.run([str(py), str(VENV_BIN / "checkov"), "--version"], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONUTF8="1"), timeout=300)
    CHECKOV_VERSION[0] = r.stdout.strip() or None


def records_dir(split: str) -> Path:
    return (CACHE / "d5b-records") if split == "dev" else (private_root() / "d5b-records")


def label_run(splits: list[str], workers: int, write: bool) -> int:
    """Step 6. Stops (exit 4) on any plannable-set difference, completeness defect or ambiguity, before writing."""
    sys.path.insert(0, str(REPO_ROOT / "generator"))
    import writer  # noqa: PLC0415  (canonical scenario.json format and the test-manifest hashes)

    cmp_ = plannable_comparison(splits)
    print("A5 plannable set:", json.dumps({s: {k: v for k, v in c.items() if k != "difference_list"}
                                          for s, c in cmp_.items()}), flush=True)
    if any(c["differences"] for c in cmp_.values()):
        print("plannable set differs from D5a-3: stop", flush=True)
        return 4
    decided: list[tuple[str, Path, dict, dict]] = []
    stops = []
    for split, p, sc in scenarios(splits):
        if sc.get("excluded_from_v1") is not None and sc["excluded_from_v1"].get("kind") not in D5B_KINDS:
            continue  # D5a-3 exclusion (unplannable): kept as it is
        dec = decide(split, p, sc)
        decided.append((split, p, sc, dec))
        if "stop" in dec:
            stops.append(sc["scenario_id"] if split == "dev" else "(test)")
    if stops:
        print(f"stop before writing: {len(stops)} scenarios; dev: {[s for s in stops if s != '(test)']}", flush=True)
        return 4
    measure_tool_versions()
    ck_jobs = [(split, sc["scenario_id"], k, sd, hash_for(sc, k)) for split, p, sc, dec in decided
               if "exclude" not in dec for k, sd in enumerate(step_dirs(p, sc))]
    print("checkov:", run_checkov(ck_jobs, workers), flush=True)
    if not write:
        return 0
    manifest_updates: dict[str, str] = {}
    summary: dict[str, dict[str, Any]] = {}
    for split, p, sc, dec in decided:
        sid = sc["scenario_id"]
        pr = dec["per_set"]["primary"]
        rec = {"scenario_id": sid, "oracle_version": ORACLE_VERSION, "decision": dec.get("exclude"),
               "invariance_differences": dec.get("invariance_differences"),
               "per_set": dec["per_set"]}
        if "exclude" in dec:
            kind, why = dec["exclude"]
            sc["labels"], sc["gt_class"], sc["oracle"] = None, None, None
            sc["excluded_from_v1"] = {"kind": kind, "reason": why, "by": ORACLE_VERSION}
        else:
            plan0 = cached_run(split, "primary", sid, 0, hash_for(sc, 0))
            dis, errs = checkov_disagreements(split, sid, pr["results"])
            sc["labels"], sc["gt_class"] = pr["labels"], pr["gt_class"]
            sc["oracle"] = {"versions": versions(sc, (plan0 or {}).get("plan")), "disagreements": dis}
            sc["excluded_from_v1"] = None
            rec["checkov_errors"] = errs
        text = writer.canonical_json(sc)
        (p / "scenario.json").write_text(text, encoding="utf-8", newline="\n")
        if split == "test":
            manifest_updates[sid] = writer.sha256_text(text)
        rd = records_dir(split)
        rd.mkdir(parents=True, exist_ok=True)
        (rd / f"{sid}.json").write_text(json.dumps(rec, sort_keys=True, default=str), encoding="utf-8")
        s = summary.setdefault(split, {})
        s[sid] = {"gt_class": sc["gt_class"], "excluded": sc["excluded_from_v1"],
                  "checkov_disagreements": len((sc["oracle"] or {}).get("disagreements") or [])}
    if manifest_updates:
        mp = REPO_ROOT / "scenarios" / "test_manifest.json"
        man = json.loads(mp.read_text(encoding="utf-8"))
        for e in man:
            if e["scenario_id"] in manifest_updates:
                e["scenario_json_sha256"] = manifest_updates.pop(e["scenario_id"])
        if manifest_updates:
            raise SystemExit(f"{len(manifest_updates)} test scenarios missing from test_manifest.json")
        mp.write_text(writer.canonical_json(man), encoding="utf-8", newline="\n")
    tag = "" if TIER[0] is None else f"_{TIER[0]}"
    out_dev = REPO_ROOT / "docs" / ("d5b" if TIER[0] is None else "d4c") / f"plannable{tag}_dev.json"
    out_dev.parent.mkdir(parents=True, exist_ok=True)
    out_dev.write_text(json.dumps(cmp_.get("dev"), indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    if "test" in cmp_:
        (private_root() / f"d5b_plannable{tag}_test.json").write_text(
            json.dumps(cmp_["test"], indent=1, sort_keys=True), encoding="utf-8")
    print("written:", {k: len(v) for k, v in summary.items()}, flush=True)
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
    ap.add_argument("--label", action="store_true", help="Step 6: A5 comparison, decisions, Checkov")
    ap.add_argument("--write", action="store_true", help="with --label: write labels (D5-20)")
    ap.add_argument("--splits", default="dev,test")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--tier", choices=("controlled", "real_world"), default=None,
                    help="D4c-06: restrict planning, labelling and writing to one tier")
    ap.add_argument("--include-excluded", action="store_true",
                    help="with --plans: also plan the scenarios D5a-3 excluded (for the A5 plannable-set comparison)")
    args = ap.parse_args()
    TIER[0] = args.tier
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
        jobs = [(s, p, d, v) for s, p, d in scenarios(splits)
                if args.include_excluded or d.get("excluded_from_v1") is None for v in SETS]
        print(run_plans(jobs, args.workers), flush=True)
        return 0
    if args.scan:
        return scan(splits)
    if args.label:
        return label_run(splits, args.workers, args.write)
    ap.error("choose --dry-run, --plans, --scan or --label")
    return 2


if __name__ == "__main__":
    sys.exit(main())
