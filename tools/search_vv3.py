#!/usr/bin/env python3
"""D5a-3 (D5-10): the vv-3 candidate search, by offline ``terraform plan`` (no evaluator, no label).

For every scenario (dev, and the private test split when ``$TERRAPRESERVE_PRIVATE`` is set), starting from
candidate index 0 everywhere and no override (the vv-2 values):

1. the primary set, then the alternate set: plan every step in order, offline, exactly as D5-04 says (the
   ``tools/run_d5a_feasibility.py`` worker: oracle working copy, empty credential files, no AWS environment
   variables, offline mirror, ``max_retries = 1``);
   A step that times out is planned again, up to ``TIMEOUT_RETRIES`` more times, before its result counts;
2. at the first step that fails with a Terraform error (its first line starts ``Error:``; a timeout or a run
   without an error line moves nothing), the variables of the first error block are found (``attribute``): those it
   names (``var.<name>``, ``variable "<name>"``), those reached through a ``local.<name>`` it names, and those one of
   whose current string values it contains;
3. each such variable with a declared default not yet overridden is overridden (rule 1; it then holds in both
   sets), provided vv-2's kind rules give it a value; each valued one not at its last candidate moves to its next
   candidate (rule 2; in the alternate set, skipping a candidate whose whole value equals the primary's);
4. then every step is planned again from step 0; when no named variable can change, the set's search ends;
5. if the alternate search added an override, both searches run again (the override changes the primary set).

The search is deterministic: the same files give the same plans, the same order and the same candidates. The
result is written to ``generator/vv3/dev.json`` and ``$TERRAPRESERVE_PRIVATE/vv3_test.json`` (which the generator
reads, ``varvalues.search_record``); ``excluded_from_v1`` is filled later from the D5a-3 feasibility measurement
(``tools/mark_d5a3_exclusions.py``) and kept here as it is. Progress is printed as counts only. Partial results are
kept in ``~/.terrapreserve-cache/d5a3-search`` so a run can be resumed. Standard library only.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import copy
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import run_d5a_feasibility as feas  # noqa: E402
import varvalues  # noqa: E402
from realworld import modread  # noqa: E402

SETS = (("primary", "variable_values"), ("alternate", "variable_values_alt"))
CACHE = feas.CACHE / "d5a3-search"
TIMEOUT_RETRIES = 2  # a step that times out (environment, not a value) is planned again up to twice
_VAR = re.compile(r"\bvar\.([A-Za-z_][A-Za-z0-9_-]*)")
_VARDECL = re.compile(r'\bvariable "([A-Za-z_][A-Za-z0-9_-]*)"')
_LOCAL = re.compile(r"\blocal\.([A-Za-z_][A-Za-z0-9_-]*)")


def step_dirs(p: Path) -> list[Path]:
    return sorted((x for x in p.glob("step_*") if x.is_dir()), key=lambda x: int(x.name.split("_")[1]))


def first_error_block(text: str) -> str:
    lines = text.splitlines()
    idx = next((i for i, ln in enumerate(lines) if ln.strip().startswith("Error:")), None)
    if idx is None:
        return ""
    block = [lines[idx]]
    for ln in lines[idx + 1:]:
        if ln.strip().startswith("Error:"):
            break
        block.append(ln)
    return "\n".join(block)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    return []


def attribute(block: str, files: dict[str, str], values: dict[str, Any]) -> list[str]:
    """Variables the first error block points to (sorted)."""
    names = set(_VAR.findall(block)) | set(_VARDECL.findall(block))
    mod = modread.read_module({n: t for n, t in files.items() if n.endswith(".tf")})
    for local in sorted(set(_LOCAL.findall(block))):
        names |= {v for v, _p, _e in varvalues._resolve("local", local, [], mod, {})}
    for name, value in values.items():
        if any(len(s) >= 3 and s in block for s in _strings(value)):
            names.add(name)
    return sorted(names)


def defaulted(steps_files: list[dict[str, str]]) -> set[str]:
    out: set[str] = set()
    for files in steps_files:
        mod = modread.read_module({n: t for n, t in files.items() if n.endswith(".tf")})
        out |= {n for n, b in mod.variables.items() if "default" in b.attrs}
    return out


def _same_ok(rec: dict, name: str) -> bool:
    return "same_in_both_sets" in rec["variable_values_kinds"].get(name, {})


def search_scenario(worker: feas.Worker, p: Path, sc: dict) -> dict[str, Any]:
    sid = sc["scenario_id"]
    tier = sc["source"]["tier"]
    sds = step_dirs(p)
    steps_files = [{f.name: f.read_text(encoding="utf-8") for f in sd.glob("*.tf")} for sd in sds]
    with_default = defaulted(steps_files)
    state: dict[str, Any] = {"candidates": {"primary": {}, "alternate": {}}, "overrides": {}}
    outcome: dict[str, dict[str, Any]] = {}
    moves: list[str] = []
    plans = 0

    def run_set(which: str, key: str) -> dict[str, Any]:
        nonlocal state, plans
        while True:
            rec = varvalues.compute(steps_files, state)
            values = rec[key]
            fail = None
            for k, sd in enumerate(sds):
                for _attempt in range(1 + TIMEOUT_RETRIES):
                    row = worker.step({"scenario_id": sid, "variable_values": values}, sd, tier)
                    plans += 1
                    if row["error_first_line"] != "timeout":
                        break
                if row["status"] != "success":
                    log = feas.RUN_ROOT / "logs" / f"{sid}_step{row['step']}_{row['stage']}.txt"
                    fail = (k, row, log.read_text(encoding="utf-8") if log.is_file() else "")
                    break
            if fail is None:
                return {"result": "plans"}
            k, row, text = fail
            changed = False
            # Only a Terraform error is a rejection; a timeout (or any run without an error line) changes nothing.
            names = attribute(first_error_block(text), steps_files[k], values) if str(
                row["error_first_line"]).startswith("Error:") else []
            for name in names:
                if name in with_default and name not in state["overrides"]:
                    trial = copy.deepcopy(state)
                    trial["overrides"][name] = {"value_set": which, "step": k, "error": row["error_first_line"]}
                    if name in varvalues.compute(steps_files, trial)[key]:
                        state = trial
                        moves.append(f"{which}: override {name}")
                        changed = True
                elif name in values:
                    idx = state["candidates"][which].get(name, 0)
                    count = varvalues.candidate_count(rec["variable_values_kinds"][name]["kind"])
                    nxt = idx + 1
                    while nxt < count and which == "alternate":
                        trial = copy.deepcopy(state)
                        trial["candidates"][which][name] = nxt
                        r2 = varvalues.compute(steps_files, trial)
                        if r2["variable_values_alt"][name] != r2["variable_values"][name] or _same_ok(r2, name):
                            break
                        nxt += 1
                    if nxt < count:
                        state["candidates"][which][name] = nxt
                        moves.append(f"{which}: {name} -> {nxt}")
                        changed = True
            if not changed:
                return {"result": "fails", "step": k, "first_error": row["error_first_line"],
                        "error_class": row["error_class"], "error_cause": row["error_cause"]}

    def separate_alternate() -> None:
        """Before the alternate search: an alternate value equal to the primary moves to its next candidate."""
        nonlocal state
        while True:
            rec = varvalues.compute(steps_files, state)
            name = next((n for n, v in rec["variable_values_alt"].items()
                         if v == rec["variable_values"][n] and not _same_ok(rec, n)
                         and state["candidates"]["alternate"].get(n, 0) + 1
                         < varvalues.candidate_count(rec["variable_values_kinds"][n]["kind"])), None)
            if name is None:
                return
            state["candidates"]["alternate"][name] = state["candidates"]["alternate"].get(name, 0) + 1
            moves.append(f"alternate: {name} -> {state['candidates']['alternate'][name]} (equal to primary)")

    while True:
        n_over = len(state["overrides"])
        outcome["primary"] = run_set("primary", "variable_values")
        separate_alternate()
        outcome["alternate"] = run_set("alternate", "variable_values_alt")
        if len(state["overrides"]) == n_over:
            break
    return {
        "candidates": {w: dict(sorted((n, i) for n, i in state["candidates"][w].items() if i)) for w in
                       ("primary", "alternate")},
        "overrides": dict(sorted(state["overrides"].items())),
        "search": {"plans_run": plans, "moves": moves, **outcome},
        "excluded_from_v1": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="dev,test")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--only", default="", help="comma-separated dev scenario ids (a check run; nothing written)")
    args = ap.parse_args()
    feas.RUN_ROOT = CACHE
    feas.VALUE_KEY = "variable_values"
    feas.RULE_NAME = "vv-3"
    terraform = shutil.which("terraform")
    if terraform is None:
        raise SystemExit("terraform not found")
    splits = args.splits.split(",")
    priv = os.environ.get("TERRAPRESERVE_PRIVATE")
    outs = {"dev": varvalues.SEARCH_DEV}
    if "test" in splits:
        if not priv or not Path(priv).is_dir():
            raise SystemExit("TERRAPRESERVE_PRIVATE is not set to an existing directory")
        outs["test"] = Path(priv) / varvalues.SEARCH_TEST_NAME
    CACHE.mkdir(parents=True, exist_ok=True)
    only = set(filter(None, args.only.split(",")))
    jobs = []
    partial: dict[str, dict[str, Any]] = {}
    for split, p, sc in feas.scenarios(splits):
        if only and sc["scenario_id"] not in only:
            continue
        part = CACHE / f"partial_{split}.jsonl"
        if not only and split not in partial:
            partial[split] = {}
            if part.is_file():
                for ln in part.read_text(encoding="utf-8").splitlines():
                    r = json.loads(ln)
                    partial[split][r["scenario_id"]] = r["result"]
        if not only and sc["scenario_id"] in partial[split]:
            continue
        jobs.append((split, p, sc))
    print(f"scenarios to search: {len(jobs)}", flush=True)
    workers = [feas.Worker(i, terraform) for i in range(args.workers)]
    free = list(workers)
    lock = threading.Lock()
    results: dict[str, dict[str, Any]] = {}

    def run(job):
        split, p, sc = job
        with lock:
            w = free.pop()
        try:
            return split, sc["scenario_id"], search_scenario(w, p, sc)
        finally:
            with lock:
                free.append(w)

    n = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for split, sid, res in ex.map(run, jobs):
            n += 1
            if only:
                results[sid] = res
            else:
                with lock, open(CACHE / f"partial_{split}.jsonl", "a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps({"scenario_id": sid, "result": res}, sort_keys=True) + "\n")
                partial[split][sid] = res
            if n % 25 == 0:
                print(f"{n}/{len(jobs)} searched", flush=True)
    if only:
        print(json.dumps(results, indent=2, sort_keys=True))
        return 0
    for split, path in outs.items():
        if split not in partial:
            continue
        old = json.loads(path.read_text(encoding="utf-8"))["scenarios"] if path.is_file() else {}
        scs = {}
        for sid, res in sorted(partial[split].items()):
            res = dict(res)
            res["excluded_from_v1"] = (old.get(sid) or {}).get("excluded_from_v1")
            scs[sid] = res
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"rule": varvalues.RULE, "decision": "D5-10", "tool": "tools/search_vv3.py", "scenarios": scs}
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(f"{split}: {len(scs)} scenarios written", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
