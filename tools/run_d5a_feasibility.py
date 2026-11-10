#!/usr/bin/env python3
"""Input-path feasibility (measure only; no evaluator, no label): D5a Step 4 and D5a-2 Step 4.

For every step of every scenario (dev, and the private test split when ``$TERRAPRESERVE_PRIVATE`` is set):

1. build the oracle working copy (``oracle.inputs``, D5-04): step ``.tf`` files, oracle provider block,
   ``terraform.tfvars.json`` from one value set (``--value-set primary``: ``variable_values``;
   ``--value-set alternate``: ``variable_values_alt``, D5-06/D5-07);
2. ``terraform init -backend=false`` (offline mirror only), ``terraform plan -input=false -refresh=false
   -lock=false -out=plan.bin``, ``terraform show -json plan.bin``;
3. with ``--checkov`` (the D5a run), Checkov 3.3.30 on a pristine copy of the step directory with only the
   invariant-relevant checks (``CHECKOV_CHECKS``); only whether it ran and its run time are recorded.

Per step it records the result, for a failure the stage, the first error's class and first line, and wall time.
D5a-3 (default ``--run d5a3``, rule vv-3) writes ``docs/d5a3/`` and ``d5a3_feasibility_test_<set>.csv`` the same
way. D5a-2 (``--run d5a2``): dev rows go to ``docs/d5a2/feasibility_dev_<set>.csv``, test rows to
``$TERRAPRESERVE_PRIVATE/d5a2_feasibility_test_<set>.csv``. The D5a run (``--run d5a``, vv-1, commit
``e96c017``) wrote ``docs/d5a/feasibility_dev.csv`` and ``$TERRAPRESERVE_PRIVATE/d5a_feasibility_test.csv``;
those files are kept as they were. Test rows never enter the repository. Rows are appended as they finish, so a
run can be resumed. No AWS credential is used: see ``oracle/inputs.py``.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from oracle import inputs  # noqa: E402

# Checkov 3.3.30 policy index, docs/5.Policy Index/terraform.md at tag 3.3.30
# (https://github.com/bridgecrewio/checkov/blob/3.3.30/docs/5.Policy%20Index/terraform.md):
#   CKV_AWS_24  "Ensure no security groups allow ingress from 0.0.0.0:0 to port 22"   (INV-SEC-001)
#   CKV_AWS_277 "Ensure no security groups allow ingress from 0.0.0.0:0 to port -1"   (all ports: SEC-001, SEC-002)
#   CKV_AWS_17  "Ensure all data stored in RDS is not publicly accessible"            (INV-SEC-003)
# The index lists no check for TCP 5432 and none for EC2 to RDS connectivity (INV-FUNC-001).
CHECKOV_CHECKS = ("CKV_AWS_24", "CKV_AWS_277", "CKV_AWS_17")
VENV_BIN = REPO_ROOT / ".venv-tools" / ("Scripts" if os.name == "nt" else "bin")
CHECKOV = VENV_BIN / "checkov"  # a Python entry script: run it with the venv interpreter
VENV_PYTHON = VENV_BIN / ("python.exe" if os.name == "nt" else "python")
CACHE = Path.home() / ".terrapreserve-cache"
RUN_ROOT = CACHE / "d5a-feasibility"  # set by configure()
VALUE_KEY = "variable_values"  # set by configure()
OUT: dict[str, Path | None] = {"dev": REPO_ROOT / "docs" / "d5a" / "feasibility_dev.csv", "test": None}
_VV_LITERAL = re.compile(r"tp-placeholder|tp-primary|tp-alt|tp-secret-primary|tp-secret-alt|tpprimary|tpalt|"
                         r"\btpp\b|\btpa\b")
RULE_NAME = "vv-2"  # the value rule named in the causes; set by configure()


def configure(run: str, value_set: str) -> None:
    """Output paths and the value set of one measurement run."""
    global RUN_ROOT, VALUE_KEY
    priv = os.environ.get("TERRAPRESERVE_PRIVATE")
    if run == "d5a":
        if value_set != "primary":
            raise SystemExit("the D5a run had one value set (vv-1)")
        RUN_ROOT = CACHE / "d5a-feasibility"
        VALUE_KEY = "variable_values"
        OUT["dev"] = REPO_ROOT / "docs" / "d5a" / "feasibility_dev.csv"
        OUT["test"] = Path(priv) / "d5a_feasibility_test.csv" if priv else None
        return
    global RULE_NAME
    RULE_NAME = {"d5a2": "vv-2", "d5a3": "vv-3"}[run]
    RUN_ROOT = CACHE / f"{run}-feasibility-{value_set}"
    VALUE_KEY = {"primary": "variable_values", "alternate": "variable_values_alt"}[value_set]
    OUT["dev"] = REPO_ROOT / "docs" / run / f"feasibility_dev_{value_set}.csv"
    OUT["test"] = Path(priv) / f"{run}_feasibility_test_{value_set}.csv" if priv else None
FIELDS = ["scenario_id", "tier", "step", "status", "stage", "error_class", "error_cause", "error_first_line",
          "wall_seconds", "plan_json_bytes", "checkov_ran", "checkov_seconds"]
CLASSES = ("data source needs API", "provider tried to call AWS", "variable error", "other")
_AWS_CALL = re.compile(r"127\.0\.0\.1:9|proxyconnect|request send failed|amazonaws\.com|https response error|"
                       r"operation error|EC2 IMDS|no valid credential", re.I)
_VAR_IN_DETAIL = re.compile(r"var\.[A-Za-z_][A-Za-z0-9_-]*(\[[^\]]*\]|\.[A-Za-z_][A-Za-z0-9_]*)* (is|will be) ")


def classify(text: str, valued: set[str] | None = None) -> tuple[str, str, str]:
    """(error class, cause, first error line) of the first error in Terraform output.

    Classes (work package Step 4): "data source needs API" (the first error is raised while reading a
    ``data`` block); "provider tried to call AWS" (an AWS request was attempted and refused by the proxy
    guard, outside a data block); "variable error" (a required variable has no value, or Terraform reports a
    value set by the rule in the failing expression, or a variable's declared default is rejected); "other". The
    cause is a short sub-class for the authors. ``valued`` is the set of variables that have a vv-2 value in this
    scenario; with it, an expression error is attributed to a vv-2 value or to a declared default.
    """
    lines = text.splitlines()
    idx = next((i for i, ln in enumerate(lines) if ln.strip().startswith("Error:")), None)
    if idx is None:
        return "other", "no error line", (next((ln.strip() for ln in lines if ln.strip()), "no output"))[:300]
    first = lines[idx].strip()
    block = []
    for ln in lines[idx:]:
        if block and ln.strip().startswith("Error:"):
            break
        block.append(ln)
    body = "\n".join(block)
    data = re.search(r"^\s*with data\.([A-Za-z0-9_]+)\.", body, re.M)
    if not data and not re.search(r"^\s*(with |on \S+ line \d+)", body, re.M):
        # An error with no "with" line (for example the S3 client of terraform_remote_state): attribute it to
        # the data source Terraform was reading just before, if any.
        data = re.search(r"^data\.([A-Za-z0-9_]+)\.\S+: Reading\.\.\.$", text, re.M)
    if data:
        if re.search(r"credential", body, re.I):
            what = "AWS credential lookup failed (no credential is available)"
        elif _AWS_CALL.search(body):
            what = "AWS request refused"
        else:
            what = "no AWS request"
        return "data source needs API", f"{data.group(1)}: {what}", first[:300]
    if _AWS_CALL.search(body):
        return "provider tried to call AWS", "AWS request refused", first[:300]
    if re.search(r"No value for required variable", first):
        return "variable error", "unresolved variable has no value", first[:300]
    if re.search(r"Invalid value for (input )?variable", first):
        return "variable error", f"{RULE_NAME} value rejected by the variable's type or validation", first[:300]
    # Which variables does the failing expression read? (source snippet lines and value details)
    snippet_vars = set(re.findall(r"\bvar\.([A-Za-z_][A-Za-z0-9_-]*)", body))
    if _VV_LITERAL.search(body) or (snippet_vars and valued is not None and snippet_vars & valued) \
            or (valued is None and _VAR_IN_DETAIL.search(body)):
        return "variable error", f"{RULE_NAME} value rejected in an expression or by the provider", first[:300]
    if snippet_vars and valued is not None:
        return "variable error", f"a declared default (not set by {RULE_NAME}) rejected in an expression or by the provider", \
            first[:300]
    if re.search(r"Failed to query available provider packages|Failed to install provider|"
                 r"provider registry|could not find", body, re.I):
        return "other", "provider not in the offline mirror", first[:300]
    return "other", "", first[:300]


def run_killing_tree(cmd: list[str], *, env: dict[str, str], timeout: int,
                     cwd: str | None = None) -> subprocess.CompletedProcess:
    """subprocess.run that, on timeout, kills the whole process tree (Terraform's provider child included)."""
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace", env=env, cwd=cwd, creationflags=flags,
                            start_new_session=os.name != "nt")
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(proc.pid, 9)
        out, err = proc.communicate()
        raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err) from None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def scenarios(splits: list[str]) -> list[tuple[str, Path, dict]]:
    roots = []
    if "dev" in splits:
        roots.append(("dev", REPO_ROOT / "scenarios" / "dev"))
    priv = os.environ.get("TERRAPRESERVE_PRIVATE")
    if "test" in splits:
        if not priv or not Path(priv).is_dir():
            raise SystemExit("TERRAPRESERVE_PRIVATE is not set to an existing directory")
        roots.append(("test", Path(priv)))
    out = []
    for split, root in roots:
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append((split, p, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


class Worker:
    def __init__(self, n: int, terraform: str) -> None:
        self.base = RUN_ROOT / f"worker{n}"
        self.base.mkdir(parents=True, exist_ok=True)
        self.data = self.base / "tf-data"
        self.rc = inputs.cli_config(self.base / "oracle.tfrc")
        self.env = inputs.terraform_env(self.base / "env", data_dir=self.data, cli_config_file=self.rc)
        self.terraform = terraform
        # Seed: init the oracle provider block alone, once per worker, from the offline mirror. Its lock file
        # is copied into every working copy, so each step's init reuses the provider already installed in
        # this worker's TF_DATA_DIR instead of copying the 841 MB binary again (measured: 8.8 s -> 1.2 s).
        # A step that needs any other provider still has to install it, and fails offline (a measured result).
        seed = self.base / "seed"
        if seed.exists():
            shutil.rmtree(seed)
        seed.mkdir(parents=True)
        (seed / inputs.PROVIDER_FILE).write_text(inputs.provider_block(), encoding="utf-8", newline="\n")
        proc = self.tf(seed, "init", "-backend=false", "-input=false", "-no-color")
        if proc.returncode != 0:
            raise SystemExit(f"seed init failed: {proc.stderr or proc.stdout}")
        self.lock = (seed / ".terraform.lock.hcl").read_bytes()

    def tf(self, work: Path, *args: str, timeout: int = 600) -> subprocess.CompletedProcess:
        return run_killing_tree([self.terraform, f"-chdir={work}", *args], env=self.env, timeout=timeout)

    def keep_log(self, row: dict, text: str) -> None:
        """Full Terraform output of a failed step, kept outside the repository for audit."""
        logs = RUN_ROOT / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / f"{row['scenario_id']}_step{row['step']}_{row['stage']}.txt").write_text(text, encoding="utf-8")

    def step(self, sc: dict, step_dir: Path, tier: str, checkov: bool = False) -> dict:
        row = {"scenario_id": sc["scenario_id"], "tier": tier, "step": int(step_dir.name.split("_")[1]),
               "status": "", "stage": "", "error_class": "", "error_cause": "", "error_first_line": "",
               "wall_seconds": "",
               "plan_json_bytes": "", "checkov_ran": "", "checkov_seconds": ""}
        work = self.base / "work"
        if work.exists():
            shutil.rmtree(work)
        t0 = time.monotonic()
        try:
            inputs.build_working_copy(step_dir, sc.get(VALUE_KEY) or {}, work)
        except ValueError as exc:
            row.update(status="failure", stage="working copy", error_class="other",
                       error_first_line=str(exc).splitlines()[0][:300], wall_seconds=f"{time.monotonic() - t0:.2f}")
            return row
        (work / ".terraform.lock.hcl").write_bytes(self.lock)
        for stage, args in (("init", ("init", "-backend=false", "-input=false", "-no-color")),
                            ("plan", ("plan", "-input=false", "-refresh=false", "-lock=false", "-no-color",
                                      "-out=plan.bin")),
                            ("show", ("show", "-json", "-no-color", "plan.bin"))):
            try:
                proc = self.tf(work, *args)
            except subprocess.TimeoutExpired as exc:
                text = f"{exc.stderr or ''}\n{exc.output or ''}"
                cls, cause, _first = classify(text, set(sc.get(VALUE_KEY) or {}))
                row.update(status="failure", stage=stage, error_class=cls if cause else "other",
                           error_cause=f"timeout after {exc.timeout} s" + (f"; {cause}" if cause else ""),
                           error_first_line="timeout")
                self.keep_log(row, text)
                break
            if proc.returncode != 0:
                text = (proc.stderr or "") + "\n" + (proc.stdout or "")
                cls, cause, first = classify(text, set(sc.get(VALUE_KEY) or {}))
                row.update(status="failure", stage=stage, error_class=cls, error_cause=cause,
                           error_first_line=first.replace(str(work), "<work>"))
                self.keep_log(row, text)
                break
            if stage == "show":
                json.loads(proc.stdout)  # must be valid plan JSON
                row.update(status="success", plan_json_bytes=len(proc.stdout.encode("utf-8")))
        row["wall_seconds"] = f"{time.monotonic() - t0:.2f}"
        if not checkov:
            return row
        # Checkov on a pristine copy of the step (the scenario directory is never written).
        with tempfile.TemporaryDirectory(prefix="tp-ckv-", dir=self.base) as tmp:
            for f in step_dir.glob("*.tf"):
                shutil.copyfile(f, Path(tmp) / f.name)
            t1 = time.monotonic()
            try:
                ck = subprocess.run([str(VENV_PYTHON), str(CHECKOV), "-d", tmp, "--framework", "terraform", "--check",
                                     ",".join(CHECKOV_CHECKS), "--skip-download", "--quiet", "--compact",
                                     "-o", "json"], capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", env=dict(self.env, PYTHONUTF8="1"), timeout=600, cwd=tmp)
                ran = ck.returncode in (0, 1) and ck.stdout.strip().startswith(("{", "["))
            except subprocess.TimeoutExpired:
                ran = False
            row.update(checkov_ran="yes" if ran else "no", checkov_seconds=f"{time.monotonic() - t1:.2f}")
        return row


def _csv_paths(splits: list[str]) -> list[Path]:
    return [p for s in ("dev", "test") if s in splits and (p := OUT[s]) is not None]


def _rewrite(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["scenario_id"], int(r["step"]))))


def drop_rows(splits: list[str], keys: set[tuple[str, str]]) -> None:
    for path in _csv_paths(splits):
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        kept = [r for r in rows if (r["scenario_id"], r["step"]) not in keys]
        print(f"{path.name}: dropping {len(rows) - len(kept)} rows to measure again", flush=True)
        _rewrite(path, kept)


def reclassify(splits: list[str]) -> int:
    values = {d["scenario_id"]: set(d.get(VALUE_KEY) or {}) for _s, _p, d in scenarios(splits)}
    for path in _csv_paths(splits):
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        changed = 0
        for r in rows:
            log = RUN_ROOT / "logs" / f"{r['scenario_id']}_step{r['step']}_{r['stage']}.txt"
            if r["status"] != "failure" or r["error_first_line"] == "timeout" or not log.is_file():
                continue
            cls, cause, _first = classify(log.read_text(encoding="utf-8"), values[r["scenario_id"]])
            if (cls, cause) != (r["error_class"], r["error_cause"]):
                changed += 1
                r["error_class"], r["error_cause"] = cls, cause
        _rewrite(path, rows)
        print(f"{path.name}: {changed} rows reclassified", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="dev,test")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="only the first N steps (for a smoke run)")
    ap.add_argument("--reclassify", action="store_true",
                    help="recompute error_class and error_cause of failed rows from the saved logs, then exit")
    ap.add_argument("--rerun", default="",
                    help="comma-separated scenario_id:step rows to drop and measure again (reported as reruns)")
    ap.add_argument("--run", choices=("d5a", "d5a2", "d5a3"), default="d5a3")
    ap.add_argument("--value-set", choices=("primary", "alternate"), default="primary")
    ap.add_argument("--checkov", action="store_true", help="also time Checkov (the D5a run did)")
    args = ap.parse_args()
    configure(args.run, args.value_set)
    if args.reclassify:
        return reclassify(args.splits.split(","))
    if args.rerun:
        drop_rows(args.splits.split(","), {tuple(x.rsplit(":", 1)) for x in args.rerun.split(",")})
    terraform = shutil.which("terraform")
    if terraform is None:
        raise SystemExit("terraform not found")
    if args.checkov and (not CHECKOV.exists() or not VENV_PYTHON.exists()):
        raise SystemExit(f"checkov not found at {CHECKOV}")
    splits = args.splits.split(",")
    if "test" in splits and OUT["test"] is None:
        raise SystemExit("TERRAPRESERVE_PRIVATE is not set to an existing directory")
    out_paths = {s: OUT[s] for s in ("dev", "test") if s in splits}
    done: set[tuple[str, int]] = set()
    for split, path in out_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                done |= {(r["scenario_id"], int(r["step"])) for r in csv.DictReader(f)}
        else:
            with open(path, "w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n").writeheader()
    jobs = []
    for split, p, sc in scenarios(splits):
        for sd in sorted((x for x in p.glob("step_*") if x.is_dir()), key=lambda x: int(x.name.split("_")[1])):
            if (sc["scenario_id"], int(sd.name.split("_")[1])) not in done:
                jobs.append((split, sc, sd))
    if args.limit:
        jobs = jobs[: args.limit]
    print(f"steps to run: {len(jobs)} (already done: {len(done)})", flush=True)
    workers = [Worker(i, terraform) for i in range(args.workers)]
    free = list(workers)
    lock = threading.Lock()

    def run(job):
        split, sc, sd = job
        with lock:
            w = free.pop()
        try:
            return split, w.step(sc, sd, sc["source"]["tier"], args.checkov)
        finally:
            with lock:
                free.append(w)

    n = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for split, row in ex.map(run, jobs):
            with lock, open(out_paths[split], "a", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n").writerow(row)
            n += 1
            if n % 50 == 0:
                print(f"{n}/{len(jobs)} done", flush=True)
    # Sort the files for a stable, reviewable result.
    for path in out_paths.values():
        with open(path, encoding="utf-8") as f:
            rows = sorted(csv.DictReader(f), key=lambda r: (r["scenario_id"], int(r["step"])))
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
