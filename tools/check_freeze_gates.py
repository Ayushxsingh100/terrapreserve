#!/usr/bin/env python3
"""D6-03: check the D0 Decision 10 freeze gates 1 to 9 over both splits and write ``docs/D6_GATES.md``.

D0 Decision 10: "The dataset is frozen only when **all** of these pass: 1. Independence ... 2. Validity ...
3. Base-state check ... 4. Complete labels ... 5. No secrets ... 6. No leakage ... 7. Balance ... 8. Integrity ...
9. Pinned versions".

Scope (D6-03): gates 3 and 4 decide on the 320 targets and are reported for the reserves; gate 2 runs
``terraform validate`` (pinned harness of ``pool/validate.py``) on every step of every target; gates 5, 6, 8 and 9
cover all 416 scenarios (gate 9: every labelled one). The test split is read from ``$TERRAPRESERVE_PRIVATE`` and
reported as counts only. Exit status 1 when any gate FAILs. Standard library and ``pool/``, ``sources/``,
``generator/`` modules only.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
for sub in ("sources", "sources/terragoat", "pool", "generator"):
    if str(REPO_ROOT / sub) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / sub))

import writer  # noqa: E402

INVS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001")
FAMILIES = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")
OUT = REPO_ROOT / "docs" / "D6_GATES.md"
CACHE = Path.home() / ".terrapreserve-cache" / "d6-validate.json"


def pins() -> dict[str, Any]:
    """Gate 9: the pins as the repository states them (not as the labels say)."""
    from VERSION import VERSION as controlled  # noqa: PLC0415
    import validate  # noqa: PLC0415
    sys.path.insert(0, str(REPO_ROOT))
    from oracle.VERSION import ORACLE_VERSION  # noqa: PLC0415
    rw = next(ln.split('"')[1] for ln in (REPO_ROOT / "generator" / "realworld" / "generate_rw.py").read_text(
        encoding="utf-8").splitlines() if ln.startswith("GENERATOR_VERSION"))
    checkov = next(ln.split("==")[1].strip() for ln in (REPO_ROOT / "requirements-tools.txt").read_text(
        encoding="utf-8").splitlines() if ln.startswith("checkov=="))
    return {"terraform": "1.15.8", "provider_hashicorp_aws": validate.PROVIDER_VERSION, "checkov": checkov,
            "oracle": ORACLE_VERSION, "generator": {"controlled": controlled, "real_world": rw},
            "registry": "registry-v1.0", "value_rule": "vv-3"}


class Sc:
    def __init__(self, split: str, path: Path, data: dict) -> None:
        self.split, self.path, self.data = split, path, data

    @property
    def id(self) -> str:
        return self.data["scenario_id"]

    @property
    def shown(self) -> str:
        return self.id if self.split == "dev" else "<test-split scenario>"

    @property
    def role(self) -> str | None:
        return self.data.get("v1_role")

    def step_files(self, k: int) -> dict[str, str]:
        sd = self.path / f"step_{k}"
        return {f.relative_to(sd).as_posix(): f.read_text(encoding="utf-8") for f in sorted(sd.rglob("*")) if f.is_file()}


def load(dev_root: Path, test_root: Path | None) -> list[Sc]:
    out = []
    for split, root in (("dev", dev_root), ("test", test_root)):
        if root is None:
            continue
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append(Sc(split, p, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


def row(gate: int, name: str, checked: str, count: str, problems: list[str], extra: Any = None) -> dict[str, Any]:
    return {"gate": gate, "name": name, "checked": checked, "count": count, "problems": problems,
            "result": "FAIL" if problems else "PASS", "extra": extra}


# --------------------------------------------------------------------------------------------- gates


def gate1() -> dict[str, Any]:
    r = subprocess.run([sys.executable, "-m", "unittest", "tests.test_independence"], cwd=REPO_ROOT,
                       capture_output=True, text=True)
    ran = next((ln for ln in r.stderr.splitlines() if ln.startswith("Ran ")), "Ran ? tests")
    problems = [] if r.returncode == 0 else [f"tests/test_independence.py: {r.stderr.splitlines()[-1]}"]
    return row(1, "Independence", "`tests/test_independence.py` (no file imports DAIL code or the DAIL package; the "
               "oracle imports no generator, pool, sources, tests or tools code)", ran.split(" in ")[0], problems)


def gate2(scs: list[Sc], validator: Callable[[dict[str, str]], str]) -> dict[str, Any]:
    problems, n = [], 0
    for sc in scs:
        if sc.role != "target":
            continue
        for s in sc.data["steps"]:
            n += 1
            status = validator(sc.step_files(s["step"]))
            if status != "valid":
                problems.append(f"{sc.shown} step {s['step']}: {status}")
    return row(2, "Validity", "`terraform validate` (Terraform 1.15.8, `hashicorp/aws` 6.53.0, pinned harness of "
               "`pool/validate.py`) on every step of every target", f"{n} steps", problems)


def _truth(sc: Sc) -> list[dict[str, str]]:
    return [lab.get("invariant_truth") or {} for lab in (sc.data.get("labels") or [])]


def gate3(scs: list[Sc]) -> dict[str, Any]:
    problems, n, res_bad = [], 0, 0
    for sc in scs:
        if sc.role not in ("target", "reserve"):
            continue
        target = (sc.data.get("target") or {}).get("invariant_id")
        t0 = _truth(sc)[0] if _truth(sc) else {}
        bad = [i for i in INVS if i != target and t0.get(i) != "PASS"]
        if target is not None and t0.get(target) not in ("PASS", "FAIL"):
            bad.append(target)
        if bad:
            if sc.role == "target":
                problems.append(f"{sc.shown}: step 0 {bad}")
            else:
                res_bad += 1
        n += sc.role == "target"
    return row(3, "Base-state check", "step 0 of every target: every protected invariant PASS per the oracle "
               "except the repair target (labels in `scenario.json`)", f"{n} targets (reserves not clean: {res_bad})",
               problems)


def gate4(scs: list[Sc]) -> dict[str, Any]:
    problems, n, res_bad = [], 0, 0
    for sc in scs:
        if sc.role not in ("target", "reserve"):
            continue
        labs = sc.data.get("labels") or []
        bad = len(labs) != len(sc.data["steps"]) or any(
            set(INVS) - set(lab.get("invariant_truth") or {}) or lab.get("step") != k for k, lab in enumerate(labs))
        bad = bad or not sc.data.get("gt_class")
        if bad:
            if sc.role == "target":
                problems.append(f"{sc.shown}: labels incomplete")
            else:
                res_bad += 1
        n += len(sc.data["steps"]) if sc.role == "target" else 0
    return row(4, "Complete labels", "every step of every target has an oracle result for all four protected "
               "invariants, and the scenario has a `gt_class`", f"{n} target steps (reserves incomplete: {res_bad})",
               problems)


def gate5(scs: list[Sc], gitleaks: Path | None) -> dict[str, Any]:
    import redact  # noqa: PLC0415
    problems, n_files = [], 0
    for sc in scs:
        for s in sc.data["steps"]:
            files = {k: v for k, v in sc.step_files(s["step"]).items() if k.endswith(".tf")}
            n_files += len(files)
            for f in redact.inventory_flags(files):
                problems.append(f"{sc.shown} step {s['step']} {f.file}:{f.line} {f.attribute} ({f.kind})")
    scanned = "attribute inventory"
    if gitleaks is not None:
        scanned += " and gitleaks " + redact.GITLEAKS_VERSION
        for sc in scs:
            for rule, fname, line in redact.gitleaks_findings(gitleaks, sc.path):
                problems.append(f"{sc.shown}: gitleaks {rule} in {fname}:{line}")
    else:
        scanned += " (gitleaks not available here)"
    return row(5, "No secrets", f"redaction scan of every scenario directory ({scanned}; `pool/redact.py`, the "
               "scanners of D3)", f"{n_files} .tf files in {len(scs)} scenarios", problems)


def gate6(scs: list[Sc]) -> dict[str, Any]:
    sides: dict[str, set[str]] = collections.defaultdict(set)
    for sc in scs:
        sides[sc.data["source"]["repo_lineage_id"]].add(sc.split)
    both = sorted(lin for lin, s in sides.items() if len(s) > 1)
    return row(6, "No leakage", "`source.repo_lineage_id` of every scenario (controlled: template id; real-world: "
               "TerraDS lineage): no lineage in both dev and test", f"{len(sides)} lineages in {len(scs)} scenarios",
               [f"lineage {x} in both splits" for x in both])


def gate7(scs: list[Sc], tolerance: int = 2, target: int = 20) -> dict[str, Any]:
    c = collections.Counter((sc.data["family"], sc.data.get("gt_class")) for sc in scs if sc.role == "target")
    per = {f: {"safe": c[(f, "safe")], "unsafe": c[(f, "unsafe")]} for f in FAMILIES}
    problems = [f"{f} {cls}: {n} targets (target {target}, tolerance {tolerance})"
                for f, v in per.items() for cls, n in v.items() if abs(n - target) > tolerance]
    return row(7, "Balance", f"targets per family by oracle `gt_class`, each within plus or minus {tolerance} of "
               f"{target}", f"{sum(c.values())} targets", problems, per)


def gate8_steps(scs: list[Sc]) -> dict[str, Any]:
    problems, n = [], 0
    for sc in scs:
        for s in sc.data["steps"]:
            n += 1
            if writer.compute_step_content_hash(sc.step_files(s["step"])) != s["content_hash"]:
                problems.append(f"{sc.shown} step {s['step']}: content hash does not verify")
    return row(8, "Integrity", "every step content hash in `scenario.json`", f"{n} steps", problems)


def gate8(scs: list[Sc]) -> dict[str, Any]:
    r = gate8_steps(scs)
    problems, n = list(r["problems"]), 0
    by_id = {sc.id: sc for sc in scs}
    man = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
    have_test = any(sc.split == "test" for sc in scs)
    for e in man:
        sc = by_id.get(e["scenario_id"])
        if sc is None:
            if have_test:
                problems.append("a test-manifest entry has no withheld scenario")
            continue
        n += 1
        if writer.sha256_text((sc.path / "scenario.json").read_text(encoding="utf-8")) != e["scenario_json_sha256"]:
            problems.append(f"{sc.shown}: scenario.json hash differs from test_manifest.json")
        if [{"step": s["step"], "content_hash": s["content_hash"]} for s in sc.data["steps"]] != e["steps"]:
            problems.append(f"{sc.shown}: step hashes differ from test_manifest.json")
    checked = r["checked"] + f"; `scenarios/test_manifest.json` ({n} entries: `scenario.json` and step hashes)"
    v1 = REPO_ROOT / "scenarios" / "V1_MANIFEST.json"
    if v1.is_file():
        import freeze_v1  # noqa: PLC0415
        bad = freeze_v1.verify_manifests(scs)
        problems += bad
        checked += "; `scenarios/V1_MANIFEST.json`, the private manifest and `scenarios/V1_MANIFEST.sha256`"
    return row(8, "Integrity", checked, r["count"], problems)


def gate9(scs: list[Sc]) -> dict[str, Any]:
    p = pins()
    problems, n = [], 0
    for sc in scs:
        if not sc.data.get("labels"):
            continue
        n += 1
        v = (sc.data.get("oracle") or {}).get("versions") or {}
        want = dict(p, generator=p["generator"][sc.data["source"]["tier"]])
        bad = sorted(k for k in ("terraform", "provider_hashicorp_aws", "checkov", "oracle", "generator", "registry",
                                 "value_rule") if v.get(k) != want[k])
        if bad or sc.data.get("generator_version") != want["generator"]:
            problems.append(f"{sc.shown}: versions {bad or ['generator_version']} not as pinned")
    return row(9, "Pinned versions", "`oracle.versions` of every labelled scenario against the pins: Terraform "
               f"{p['terraform']}, `hashicorp/aws` {p['provider_hashicorp_aws']}, Checkov {p['checkov']}, "
               f"{p['oracle']}, generator {p['generator']['controlled']} (controlled) and "
               f"{p['generator']['real_world']} (real-world), {p['registry']}, value rule {p['value_rule']}",
               f"{n} labelled scenarios", problems)


# --------------------------------------------------------------------------------------------- validation


def terraform_validator(workers: int) -> tuple[Callable[[dict[str, str]], str], Callable[[list[Sc]], None]]:
    """A validator backed by a content-hash cache, and a function that fills the cache in parallel."""
    import validate  # noqa: PLC0415
    cache: dict[str, str] = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.is_file() else {}

    def fill(scs: list[Sc]) -> None:
        todo: dict[str, dict[str, str]] = {}
        for sc in scs:
            if sc.role == "target":
                for s in sc.data["steps"]:
                    if s["content_hash"] not in cache:
                        todo.setdefault(s["content_hash"], sc.step_files(s["step"]))
        if not todo:
            return
        base = validate.Harness.default()
        pool = [validate.Harness(base.work.parent / "d6-tfv" / f"w{i}", base.terraform,
                                 Path(base.env["TF_CLI_CONFIG_FILE"])) for i in range(workers)]
        for h in pool:
            h.ensure_ready()
        free, lock = list(pool), threading.Lock()
        print(f"gate 2: validating {len(todo)} distinct step contents", flush=True)

        def one(item):
            chash, files = item
            with lock:
                h = free.pop()
            try:
                res = h.validate(files)
                for _ in range(3):
                    if res.status != "error":
                        break
                    res = h.validate(files)
                return chash, res.status
            finally:
                with lock:
                    free.append(h)

        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for chash, status in ex.map(one, sorted(todo.items())):
                cache[chash] = status
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, sort_keys=True), encoding="utf-8")

    def validator(files: dict[str, str]) -> str:
        return cache.get(writer.compute_step_content_hash(files), "not validated")

    return validator, fill


# --------------------------------------------------------------------------------------------- report


def write_doc(rows: list[dict[str, Any]], n_dev: int, n_test: int) -> None:
    lines = ["# D6 freeze gates (D0 Decision 10)", "",
             "Written by `tools/check_freeze_gates.py` (D6-03); do not edit by hand. D0 Decision 10: \"The dataset is "
             "frozen only when **all** of these pass\". Scenarios checked: "
             f"{n_dev} dev and {n_test} test (test split: counts only). Gates 3 and 4 decide on the targets and report "
             "the reserves; gate 2 covers every step of every target; gates 5, 6 and 8 cover all scenarios.", "",
             "| Gate | What was checked | Count | Result |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['gate']}. {r['name']} | {r['checked']} | {r['count']} | {r['result']} |")
    g7 = next(r for r in rows if r["gate"] == 7)
    lines += ["", "## Gate 7: targets per family (by oracle `gt_class`)", "", "| Family | safe | unsafe |", "|---|---|---|"]
    lines += [f"| {f} | {v['safe']} | {v['unsafe']} |" for f, v in g7["extra"].items()]
    fails = [r for r in rows if r["problems"]]
    lines += ["", "## Problems", ""]
    if not fails:
        lines.append("None: every gate is PASS.")
    for r in fails:
        lines.append(f"- gate {r['gate']}: {len(r['problems'])} problems")
        lines += [f"  - {p}" for p in r["problems"][:20] if "<test-split" not in p]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    priv = os.environ.get("TERRAPRESERVE_PRIVATE")
    test_root = Path(priv) if priv and Path(priv).is_dir() else None
    if test_root is None:
        raise SystemExit("TERRAPRESERVE_PRIVATE is not set: the gates cover both splits")
    if shutil.which("terraform") is None:
        raise SystemExit("terraform not found: gate 2 runs terraform validate")
    import redact  # noqa: PLC0415
    scs = load(REPO_ROOT / "scenarios" / "dev", test_root)
    validator, fill = terraform_validator(args.workers)
    fill(scs)
    rows = [gate1(), gate2(scs, validator), gate3(scs), gate4(scs), gate5(scs, redact.gitleaks_binary()),
            gate6(scs), gate7(scs), gate8(scs), gate9(scs)]
    for r in rows:
        print(f"gate {r['gate']} {r['name']}: {r['result']} ({r['count']}; problems {len(r['problems'])})", flush=True)
    if not args.no_write:
        write_doc(rows, sum(sc.split == "dev" for sc in scs), sum(sc.split == "test" for sc in scs))
    return 1 if any(r["problems"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
