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

**The test split (TP-L2, ``--split test``; TPL2-01 to TPL2-05).** The same rule, on the test LLM candidates of
DAIL's main run. The private directory (``--private``, default ``$TERRAPRESERVE_PRIVATE``) is accepted only if it
lies outside the repository and its ``V1_MANIFEST_PRIVATE.json`` has the SHA-256 that the frozen
``scenarios/V1_MANIFEST.sha256`` gives it; the export must have the SHA-256 pinned in ``TEST_EXPORT_PINS``. S0
and the value sets are read only from the private directory: each scenario's ``scenario.json`` must have the
manifest's SHA-256 and ``split: test``, its step 0 directory must hash (D4-09) to the manifest's step-0
``content_hash``, and each candidate's S0 ``content_hash`` must be that value. Labels, the candidates' copies and
the plan JSON go under the private directory (``llm_candidates/test/<generation_id>/``, ``tp-l2-plans/``;
S0's D5b plans in ``d5b-plans/`` are reused as for dev); the oracle's transient working copies stay outside it,
as in D5b (``oracle.inputs`` refuses a destination inside it), and are deleted when the run ends (TPL2-05).
Nothing about the labels is printed: no id, no class, no count by class or reason; a refused check prints no
detail and writes it under the private directory.

    python tools/label_llm.py --split test --generation <generation_id> --dail-candidates <DAIL_EXPERIMENT_ROOT>/candidates

Standard library plus ``oracle/``, as ``tools/label_d5b.py``.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
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
# TP-L2 (TPL2-03): the export of DAIL's main run, generation id and SHA-256 as the work package gives them
TEST_EXPORT_PINS = {"40e2052b-b489-552d-8c27-88785414a4b1":
                    "7d008d9d4fa28329d3d3d39ddddec76ea280c5b46b601316ecb06722754f80ff"}
V1_SUMS = SCENARIOS / "V1_MANIFEST.sha256"
PRIVATE_MANIFEST = "V1_MANIFEST_PRIVATE.json"


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


# --- the private test split (TP-L2) ----------------------------------------------------------------------------


def private_manifest_pin() -> str:
    """The SHA-256 of ``V1_MANIFEST_PRIVATE.json`` recorded in the frozen ``scenarios/V1_MANIFEST.sha256``."""
    for line in V1_SUMS.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if name == PRIVATE_MANIFEST:
            return digest
    raise HashMismatch(f"{V1_SUMS.name} records no {PRIVATE_MANIFEST}")


def open_private(private: Path, pin: str) -> dict[str, dict[str, Any]]:
    """The private manifest's test entries by scenario id, after its SHA-256 is checked against ``pin``."""
    path = Path(private) / PRIVATE_MANIFEST
    if not path.is_file():
        raise HashMismatch(f"the private manifest {PRIVATE_MANIFEST} is missing")
    raw = path.read_bytes()
    if sha256(raw) != pin:
        raise HashMismatch(f"the private manifest's sha256 {sha256(raw)} is not the pin {pin}")
    return {e["scenario_id"]: e for e in json.loads(raw)["test"]}


@dataclass(frozen=True)
class Checked:
    scenarios: dict[str, dict[str, Any]]
    candidates: list[tuple[dict[str, Any], Path]]
    counts: dict[str, int]


def _test_scenario(private: Path, sid: str, manifest: dict[str, dict[str, Any]]) -> dict[str, Any]:
    entry = manifest.get(sid)
    if entry is None:
        raise HashMismatch(f"{sid} is not in the private manifest")
    path = Path(private) / sid / "scenario.json"
    if not path.is_file():
        raise HashMismatch(f"{sid}: no scenario.json in the private directory")
    text = path.read_text(encoding="utf-8")
    if sha256(text.encode("utf-8")) != entry["scenario_json_sha256"]:
        raise HashMismatch(f"{sid}: scenario.json is not the private manifest's")
    doc = json.loads(text)
    if doc.get("split") != "test":
        raise HashMismatch(f"{sid} is not a test scenario")
    step = next(s for s in doc["steps"] if s["step"] == 0)
    pinned = next(s["content_hash"] for s in entry["steps"] if s["step"] == 0)
    if step["content_hash"] != pinned or content_hash(Path(private) / sid / step["terraform_dir"]) != pinned:
        raise HashMismatch(f"{sid}: step 0 is not the private manifest's")
    return doc


def check_test_candidates(export: Export, export_dir: Path, private: Path,
                          manifest: dict[str, dict[str, Any]]) -> Checked:
    """Every check of Section 1 for the test split, before anything is labelled; one mismatch stops."""
    scen: dict[str, dict[str, Any]] = {}
    checked: list[tuple[dict[str, Any], Path]] = []
    counts = {"candidates_read": len(export.candidates), "files_and_hashes_verified": 0, "s0_matched": 0}
    for c in export.candidates:
        sid = c["scenario_id"]
        if sid not in scen:
            scen[sid] = _test_scenario(private, sid, manifest)
        s0_hash = next(s["content_hash"] for s in manifest[sid]["steps"] if s["step"] == 0)
        checked.append((c, verify_candidate(export_dir, c, s0_hash)))
        counts["files_and_hashes_verified"] += 1
        counts["s0_matched"] += c["s0_content_hash"] == s0_hash
    return Checked(scen, checked, counts)


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
        invalid = [f"{v}: {per[v]['validate_errors'][1]}" for v in SETS
                   if per[v].get("plan_status", [None, None])[1] == "invalid"]
        if invalid:  # TPL-06 (2)
            why = ("terraform validate failed (registry 2.8: every invariant UNSUPPORTED): "
                   + "; ".join(invalid) + "; " + why)
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
        "validate_errors": [s0.get("validate_error") or None, cand.get("validate_error") or None],
        "results": [{inv: r[inv]["result"] for inv in INVARIANTS} for r in traj["results"]],
        "oracle_affected": traj["oracle_affected"],
        "defects": traj["defects"],
        "ambiguities": sorted({a for r in traj["results"] for inv in INVARIANTS for a in r[inv].get("ambiguities", [])}),
    }


class _Runners:
    def __init__(self, cache: Path, workers: int, name: str = "tp-l1-runners") -> None:
        terraform = shutil.which("terraform")
        if terraform is None:
            raise SystemExit("terraform not found")
        self.terraform = terraform
        self.pool = [oplan.Runner(cache / name / f"w{i}", terraform) for i in range(max(1, workers))]
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

    def clear(self) -> None:
        """Delete every runner's working copy (TPL2-05: test-split files do not stay outside the private dir)."""
        for r in self.pool:
            shutil.rmtree(r.base / "work", ignore_errors=True)


def _s0_run(runners: _Runners, cache: Path, sid: str, vset: str, s0_dir: Path, values: dict, chash: str,
            plans: str = "tp-l1-plans") -> dict:
    d5b = _cached(cache / "d5b-plans" / vset / sid / "step_0.json", chash)
    if d5b is not None:
        return d5b
    own = cache / plans / "s0" / vset / f"{sid}.json"
    return _cached(own, chash) or _save(own, runners.run(s0_dir, values), chash)


def label_generation(*, export_dir: Path, pin: str, out_root: Path | None = None, workers: int = 4,
                     cache: Path = CACHE, scenarios_root: Path = DEV, split: str = "dev",
                     private: Path | None = None, manifest_pin: str | None = None,
                     runner_cache: Path = CACHE, checks: dict[str, int] | None = None) -> dict[str, Any]:
    """Label one generation. ``split="test"`` (TP-L2) reads S0 from ``private`` (its manifest checked against
    ``manifest_pin``) and keeps labels and plans there; ``cache`` and ``scenarios_root`` are then not used."""
    before = scenarios_sha256()
    export = read_export(export_dir, pin)
    if split == "test":
        if private is None or manifest_pin is None:
            raise SystemExit("--split test needs the private directory and its manifest pin")
        manifest = open_private(private, manifest_pin)
        done = check_test_candidates(export, export_dir, private, manifest)
        scen, checked = done.scenarios, done.candidates
        if checks is not None:
            checks.update(done.counts)
        scenarios_root, cache, plans = Path(private), Path(private), "tp-l2-plans"
        gen_out = Path(private) / "llm_candidates" / "test" / export.generation_id
        runners_name = "tp-l2-runners"
    else:
        scen = {}
        checked = []
        for c in export.candidates:  # every check before anything is labelled
            sid = c["scenario_id"]
            if sid not in scen:
                scen[sid] = json.loads((scenarios_root / sid / "scenario.json").read_text(encoding="utf-8"))
                if scen[sid].get("split") != "dev":
                    raise HashMismatch(f"{sid} is not a dev scenario")
            s0_hash = next(s["content_hash"] for s in scen[sid]["steps"] if s["step"] == 0)
            checked.append((c, verify_candidate(export_dir, c, s0_hash)))
        plans, runners_name, runner_cache = "tp-l1-plans", "tp-l1-runners", cache
        gen_out = Path(out_root if out_root is not None else OUT_ROOT) / export.generation_id
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
    runners = _Runners(runner_cache, workers, runners_name)
    terraform_version, providers = runners.versions()

    def one(item: tuple[dict[str, Any], Path]) -> dict[str, Any]:
        c, target = item
        sc = scen[c["scenario_id"]]
        s0_step = next(s for s in sc["steps"] if s["step"] == 0)
        s0_dir = scenarios_root / c["scenario_id"] / s0_step["terraform_dir"]
        per = {}
        for vset, key in SETS.items():
            values = sc.get(key) or {}
            s0 = _s0_run(runners, cache, c["scenario_id"], vset, s0_dir, values, s0_step["content_hash"], plans)
            path = cache / plans / export.generation_id / vset / c["model_key"] / c["scenario_id"] / f"{c['k']}.json"
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
            "validate_errors": {v: (per[v]["validate_errors"][1] if per[v]["status"] == "evaluated" else None)
                                for v in SETS},
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

    try:
        with cf.ThreadPoolExecutor(max_workers=len(runners.pool)) as ex:
            records = list(ex.map(one, copies))
    finally:
        if split == "test":
            runners.clear()
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


def summary(doc: dict[str, Any], checks: dict[str, int], *, split: str, labels_sha256: str, written: int,
            path: Path) -> dict[str, Any]:
    """What a ``--split test`` run prints: the checks and completeness, nothing about the labels (TP-L2 §4)."""
    assert split == "test"
    return {"generation_id": doc["generation_id"], "export_sha256_verified": doc["export_sha256"], **checks,
            "label_json_written": written, "labels_sha256": labels_sha256, "path": str(path)}


def main_test(args: argparse.Namespace) -> int:
    """``--split test``: refuses unless the private directory and the export are the pinned ones (TP-L2)."""
    if args.generation not in TEST_EXPORT_PINS:
        raise SystemExit(f"{args.generation} is not pinned in TEST_EXPORT_PINS")
    raw = args.private or os.environ.get("TERRAPRESERVE_PRIVATE")
    if not raw or not Path(raw).is_dir():
        raise SystemExit("--split test: the private directory (--private or $TERRAPRESERVE_PRIVATE) does not exist")
    private = Path(raw).resolve()
    if private == REPO_ROOT or REPO_ROOT in private.parents:
        raise SystemExit("--split test: the private directory must lie outside the repository")
    pin = private_manifest_pin()
    try:
        open_private(private, pin)
    except HashMismatch as error:
        raise SystemExit(f"--split test: {error}") from None
    export_dir = args.dail_candidates / args.generation / "oracle_export"
    checks: dict[str, int] = {}
    try:
        doc = label_generation(export_dir=export_dir, pin=TEST_EXPORT_PINS[args.generation], split="test",
                               private=private, manifest_pin=pin, workers=args.workers, checks=checks)
    except HashMismatch as error:  # the message may name a test id: kept in the private directory only
        where = private / "llm_candidates" / "test" / f"{args.generation}.refused.txt"
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(f"{error}\n", encoding="utf-8", newline="\n")
        raise SystemExit(f"--split test: a hash check failed; nothing was labelled; the detail is in {where}") \
            from None
    out = private / "llm_candidates" / "test" / doc["generation_id"]
    digest = sha256((out / "labels.json").read_bytes())
    print(json.dumps(summary(doc, checks, split="test", labels_sha256=digest,
                             written=len(list(out.rglob("label.json"))), path=out), indent=1))
    print((out / "labels.sha256").read_text(encoding="utf-8"), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--generation", required=True, help="a generation id pinned in EXPORT_PINS.json")
    ap.add_argument("--dail-candidates", required=True, type=Path, help="DAIL's $DAIL_EXPERIMENT_ROOT/candidates")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--split", choices=("dev", "test"), default="dev")
    ap.add_argument("--private", help="--split test: the private directory (default $TERRAPRESERVE_PRIVATE)")
    args = ap.parse_args(argv)
    if args.split == "test":
        return main_test(args)
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
