#!/usr/bin/env python3
"""TP-L1: oracle labels for the dev LLM candidates exported by DAIL (TPL-01 to TPL-06).

Labels come only from ``oracle/`` (CLAUDE.md rule 7): Terraform runs through ``oracle.plan.Runner`` (offline,
D5-04), the plan JSON goes to ``oracle.evaluate``, and the class is ``oracle.label.gt_class`` (D5-11) on the
two-step results [S0, candidate]. ``oracle-1.0`` is used unchanged.

**What is read (TPL-02).** From DAIL's export, only ``oracle_export.json`` (its SHA-256 must be the pin of
``llm_candidates/dev/EXPORT_PINS.json``; of each entry only the ``EXPORT_FIELDS`` ids and hashes are kept) and
the ``.tf`` files of each candidate directory. From v1.0, the scenario's ``scenario.json`` (S0's directory and
``content_hash``, the endpoints, the repair target and the two value sets) and S0's ``.tf`` files. Nothing else
of DAIL is opened: ``tests/test_tp_l1.py`` records every file opened.

**Checks before anything is labelled (Section 2).** The export's SHA-256; per candidate, its directory holds
exactly the files the export lists, all ``.tf``, each with the listed SHA-256, and its ``content_hash``
(D4-09, recomputed here) and S0 ``content_hash`` are the export's and v1.0's. One mismatch stops the run
(``HashMismatch``). DAIL's ``tree_hash`` is kept as given and not recomputed (TPL-06 (1)).

**Labelling (TPL-03).** Each candidate is a one-step transition from S0, planned under both value sets. S0's
cached D5b plan is reused only when its recorded ``content_hash`` is S0's; otherwise S0 is planned again. A
candidate run is cached by its ``content_hash``. Per value set: no plan JSON gives ``unplannable`` (the error
recorded); otherwise the oracle evaluates [S0, candidate]. Classes: ``safe`` (every invariant PASS),
``unsafe`` (any FAIL), else no label (``unlabelable``); labels that differ between the value sets give no
label (``value_dependent``, D5-18).

**Output (TPL-04).** ``llm_candidates/dev/<generation_id>/<model_key>/<scenario_id>/<k>/`` with the candidate's
``.tf`` files and ``label.json``; ``labels.json`` for the generation and its SHA-256 in ``labels.sha256``. The
hash of ``scenarios/`` is taken before and after the run and must not change (v1.0 is frozen).

    python tools/label_llm.py --generation <generation_id> --dail-candidates <DAIL_EXPERIMENT_ROOT>/candidates

Standard library plus ``oracle/``, as ``tools/label_d5b.py``. Dev only.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
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
SCENARIOS = REPO_ROOT / "scenarios"
DEV = SCENARIOS / "dev"
OUT_ROOT = REPO_ROOT / "llm_candidates" / "dev"
PINS = OUT_ROOT / "EXPORT_PINS.json"
INDEX = "oracle_export.json"
# TPL-02: the ids and hashes of an export entry; nothing else of an entry is kept
EXPORT_FIELDS = ("candidate_id", "generation_id", "model_key", "model_tag", "model_digest", "scenario_id",
                 "family", "k", "s0_content_hash", "tree_hash", "content_hash", "directory", "files")
REQUIRED = ("candidate_id", "generation_id", "model_key", "scenario_id", "k", "s0_content_hash",
            "content_hash", "directory", "files")


class HashMismatch(Exception):
    """An export or a candidate is not what the pins and the export say: nothing is labelled."""


@dataclass(frozen=True)
class Export:
    generation_id: str
    export_sha256: str
    candidates: list[dict[str, Any]]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(directory: Path) -> str:
    """D4-09: SHA-256 of the path-sorted lines ``"<relative POSIX path>:<sha256 of the bytes>"``."""
    files = sorted((p.relative_to(directory).as_posix(), p) for p in directory.rglob("*") if p.is_file())
    return sha256("\n".join(f"{rel}:{sha256(p.read_bytes())}" for rel, p in files).encode("utf-8"))


def scenarios_sha256(root: Path = SCENARIOS) -> str:
    """The hash of every file under ``scenarios/`` (``__pycache__`` left out), as D4-09 over the tree."""
    files = sorted((p.relative_to(root).as_posix(), p) for p in root.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts)
    return sha256("\n".join(f"{rel}:{sha256(p.read_bytes())}" for rel, p in files).encode("utf-8"))


# --- reading and checking the export (Section 2, TPL-02) -------------------------------------------------------


def read_export(export_dir: Path, pin: str) -> Export:
    raw = (Path(export_dir) / INDEX).read_bytes()
    digest = sha256(raw)
    if digest != pin:
        raise HashMismatch(f"{INDEX}: sha256 {digest} is not the pinned {pin}")
    doc = json.loads(raw)
    kept = []
    for entry in doc["candidates"]:
        missing = [f for f in REQUIRED if f not in entry]
        if missing:
            raise HashMismatch(f"an export entry has no {missing}")
        kept.append({f: entry[f] for f in EXPORT_FIELDS if f in entry})
    generations = {c["generation_id"] for c in kept} | {doc["generation_id"]}
    if len(generations) != 1:
        raise HashMismatch(f"the export names more than one generation: {sorted(generations)}")
    return Export(doc["generation_id"], digest, kept)


def verify_candidate(export_dir: Path, c: dict[str, Any], s0_hash: str) -> Path:
    """The candidate's directory, after every check of Section 2."""
    base = Path(export_dir).resolve()
    d = (base / c["directory"]).resolve()
    if base not in d.parents or not d.is_dir():
        raise HashMismatch(f"{c['candidate_id']}: directory {c['directory']} is missing or outside the export")
    entries = sorted(d.iterdir())
    names = [p.name for p in entries]
    if any(not p.is_file() for p in entries) or any(not n.endswith(".tf") for n in names):
        raise HashMismatch(f"{c['candidate_id']}: the directory holds something that is not a .tf file")
    if sorted(c["files"]) != names:
        raise HashMismatch(f"{c['candidate_id']}: files {names} are not the export's {sorted(c['files'])}")
    for p in entries:
        if sha256(p.read_bytes()) != c["files"][p.name]:
            raise HashMismatch(f"{c['candidate_id']}: {p.name} is not the exported file")
    if content_hash(d) != c["content_hash"]:
        raise HashMismatch(f"{c['candidate_id']}: content_hash is not the export's")
    if c["s0_content_hash"] != s0_hash:
        raise HashMismatch(f"{c['candidate_id']}: its S0 is not v1.0's step 0 of {c['scenario_id']}")
    return d


# --- labelling (TPL-03) ----------------------------------------------------------------------------------------


def classify(per: dict[str, dict[str, Any]], target: str | None) -> dict[str, Any]:
    """The class of one candidate from its two value sets' evaluations (``status`` ``evaluated`` with
    ``results`` and ``oracle_affected`` for [S0, candidate], or ``unplannable``)."""
    if any(per[v]["status"] != "evaluated" for v in SETS):
        return {"class": None, "no_label_reason": "unplannable", "reason": "; ".join(
            f"{v}: {per[v].get('error', '')}" for v in SETS if per[v]["status"] != "evaluated")}
    sets: dict[str, Any] = {}
    for v in SETS:
        cls, why = label.gt_class(per[v]["results"], target)
        sets[v] = (cls, why, label.label_set(cls, label.labels(per[v]["results"], per[v]["oracle_affected"], target)))
    diffs = label.invariance_differences(sets["primary"][2], sets["alternate"][2])
    if diffs:
        return {"class": None, "no_label_reason": "value_dependent", "reason": "; ".join(diffs)}
    cls, why, _ = sets["primary"]
    if cls is None:
        return {"class": None, "no_label_reason": "unlabelable", "reason": why}
    return {"class": cls, "no_label_reason": None, "reason": why}


def _cached(path: Path, chash: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    res = json.loads(path.read_text(encoding="utf-8"))
    return res if res.get("content_hash") == chash else None


def _save(path: Path, res: dict[str, Any], chash: str) -> dict[str, Any]:
    res = dict(res, content_hash=chash)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return res


def _evaluate(s0: dict[str, Any], s0_dir: Path, cand: dict[str, Any], cand_dir: Path,
              endpoints: Any) -> dict[str, Any]:
    for name, res in (("S0", s0), ("candidate", cand)):
        if res["status"] not in ("planned", "invalid"):
            return {"status": "unplannable",
                    "error": f"{name} {res.get('stage')}: {res.get('error_first_line') or 'no plan'}"}
    steps = [evaluate.load_step(res.get("plan"), res["status"] != "invalid", moves.read_moved(d))
             for res, d in ((s0, s0_dir), (cand, cand_dir))]
    first = steps[0].config
    if not isinstance(endpoints, dict) or first is None or endpoints.get("S") not in first.instances \
            or endpoints.get("D") not in first.instances:
        return {"status": "unplannable", "error": f"endpoint binding not in S0: {endpoints}"}
    traj = evaluate.evaluate_trajectory(steps, endpoints)
    return {
        "status": "evaluated",
        "plan_status": [s0["status"], cand["status"]],
        "results": [{inv: r[inv]["result"] for inv in INVARIANTS} for r in traj["results"]],
        "oracle_affected": traj["oracle_affected"],
        "defects": traj["defects"],
        "ambiguities": sorted({a for r in traj["results"] for inv in INVARIANTS for a in r[inv].get("ambiguities", [])}),
    }


class _Runners:
    def __init__(self, cache: Path, workers: int) -> None:
        terraform = shutil.which("terraform")
        if terraform is None:
            raise SystemExit("terraform not found")
        self.terraform = terraform
        self.pool = [oplan.Runner(cache / "tp-l1-runners" / f"w{i}", terraform) for i in range(max(1, workers))]
        self.free = list(self.pool)
        self.lock = threading.Lock()

    def run(self, step_dir: Path, values: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            r = self.free.pop()
        try:
            return r.run(step_dir, values)
        finally:
            with self.lock:
                self.free.append(r)

    def versions(self) -> tuple[str, dict[str, str]]:
        doc = json.loads(subprocess.run([self.terraform, "version", "-json"], capture_output=True, text=True,
                                        check=True).stdout)
        lock = self.pool[0].lock.decode("utf-8")
        found = re.findall(r'provider\s+"registry\.terraform\.io/([^"]+)"\s*\{\s*version\s*=\s*"([^"]+)"', lock)
        return doc["terraform_version"], dict(sorted(found))


def _s0_run(runners: _Runners, cache: Path, sid: str, vset: str, s0_dir: Path, values: dict, chash: str) -> dict:
    d5b = _cached(cache / "d5b-plans" / vset / sid / "step_0.json", chash)
    if d5b is not None:
        return d5b
    own = cache / "tp-l1-plans" / "s0" / vset / f"{sid}.json"
    return _cached(own, chash) or _save(own, runners.run(s0_dir, values), chash)


def label_generation(*, export_dir: Path, pin: str, out_root: Path = OUT_ROOT, workers: int = 4,
                     cache: Path = CACHE, scenarios_root: Path = DEV) -> dict[str, Any]:
    before = scenarios_sha256()
    export = read_export(export_dir, pin)
    scen: dict[str, dict[str, Any]] = {}
    checked: list[tuple[dict[str, Any], Path]] = []
    for c in export.candidates:  # every check before anything is labelled
        sid = c["scenario_id"]
        if sid not in scen:
            scen[sid] = json.loads((scenarios_root / sid / "scenario.json").read_text(encoding="utf-8"))
            if scen[sid].get("split") != "dev":
                raise HashMismatch(f"{sid} is not a dev scenario")
        s0_hash = next(s["content_hash"] for s in scen[sid]["steps"] if s["step"] == 0)
        checked.append((c, verify_candidate(export_dir, c, s0_hash)))
    gen_out = Path(out_root) / export.generation_id
    if gen_out.exists():
        raise SystemExit(f"{gen_out} exists; labels are written once")
    copies = []
    for c, d in checked:
        target = gen_out / c["model_key"] / c["scenario_id"] / str(c["k"])
        target.mkdir(parents=True)
        for p in sorted(d.glob("*.tf")):
            shutil.copyfile(p, target / p.name)
        if content_hash(target) != c["content_hash"]:
            raise HashMismatch(f"{c['candidate_id']}: the copy differs from the export")
        copies.append((c, target))
    runners = _Runners(cache, workers)
    terraform_version, providers = runners.versions()

    def one(item: tuple[dict[str, Any], Path]) -> dict[str, Any]:
        c, target = item
        sc = scen[c["scenario_id"]]
        s0_step = next(s for s in sc["steps"] if s["step"] == 0)
        s0_dir = scenarios_root / c["scenario_id"] / s0_step["terraform_dir"]
        per = {}
        for vset, key in SETS.items():
            values = sc.get(key) or {}
            s0 = _s0_run(runners, cache, c["scenario_id"], vset, s0_dir, values, s0_step["content_hash"])
            path = cache / "tp-l1-plans" / export.generation_id / vset / c["model_key"] / c["scenario_id"] / f"{c['k']}.json"
            cand = _cached(path, c["content_hash"]) or _save(path, runners.run(target, values), c["content_hash"])
            per[vset] = _evaluate(s0, s0_dir, cand, target, sc.get("endpoints"))
        target_id = label.repair_target(sc)
        verdict = classify(per, target_id)
        record = {
            "record": "tp_l1_label",
            **{f: c[f] for f in EXPORT_FIELDS if f in c and f != "directory"},
            "export_sha256": export.export_sha256,
            "repair_target": target_id,
            "invariant_truth": {v: (per[v]["results"][1] if per[v]["status"] == "evaluated" else None)
                                for v in SETS},
            "s0_invariant_truth": {v: (per[v]["results"][0] if per[v]["status"] == "evaluated" else None)
                                   for v in SETS},
            "oracle_affected": {v: (per[v]["oracle_affected"][1] if per[v]["status"] == "evaluated" else None)
                                for v in SETS},
            "plan_status": {v: per[v].get("plan_status") for v in SETS},
            "errors": {v: per[v]["error"] for v in SETS if per[v]["status"] != "evaluated"},
            "defects": sorted({d for v in SETS for d in per[v].get("defects", [])}),
            "ambiguities": sorted({a for v in SETS for a in per[v].get("ambiguities", [])}),
            **verdict,
            "oracle_version": ORACLE_VERSION,
            "terraform_version": terraform_version,
            "provider_versions": providers,
        }
        (target / "label.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                           newline="\n")
        return record

    with cf.ThreadPoolExecutor(max_workers=len(runners.pool)) as ex:
        records = list(ex.map(one, copies))
    after = scenarios_sha256()
    if after != before:
        raise SystemExit(f"scenarios/ changed during the run: {before} -> {after}")
    records.sort(key=lambda r: (r["model_key"], r["scenario_id"], r["k"]))
    doc = {"record": "tp_l1_labels", "generation_id": export.generation_id, "export_sha256": export.export_sha256,
           "oracle_version": ORACLE_VERSION, "terraform_version": terraform_version,
           "provider_versions": providers, "scenarios_sha256_before": before, "scenarios_sha256_after": after,
           "candidates": records}
    raw = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("utf-8")
    (gen_out / "labels.json").write_bytes(raw)
    (gen_out / "labels.sha256").write_text(f"{sha256(raw)}  labels.json\n", encoding="utf-8", newline="\n")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--generation", required=True, help="a generation id pinned in EXPORT_PINS.json")
    ap.add_argument("--dail-candidates", required=True, type=Path, help="DAIL's $DAIL_EXPERIMENT_ROOT/candidates")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    pins = json.loads(PINS.read_text(encoding="utf-8"))["exports"]
    if args.generation not in pins:
        raise SystemExit(f"{args.generation} is not pinned in {PINS}")
    export_dir = args.dail_candidates / args.generation / "oracle_export"
    doc = label_generation(export_dir=export_dir, pin=pins[args.generation]["oracle_export_sha256"],
                           workers=args.workers)
    counts: dict[str, int] = {}
    for r in doc["candidates"]:
        key = r["class"] or f"no label: {r['no_label_reason']}"
        counts[key] = counts.get(key, 0) + 1
    print(json.dumps({"generation_id": doc["generation_id"], "candidates": len(doc["candidates"]),
                      "counts": counts}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
