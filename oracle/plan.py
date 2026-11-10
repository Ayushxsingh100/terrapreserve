"""Offline Terraform runs of one step (D5-04, D5-13): validate, plan, ``terraform show -json``.

The oracle's only Terraform input is the plan JSON of its private working copy (D5-05), plus the result of
``terraform validate`` (registry 2.8: a configuration that fails validation makes every invariant UNSUPPORTED).
A ``Runner`` owns one Terraform data directory and CLI configuration (offline mirror only) and runs one step at a
time:

1. build the working copy (``oracle.inputs.build_working_copy``) from the step's ``.tf`` files and one value set;
2. ``terraform init -backend=false`` (the provider comes from the offline mirror; the lock file of a seed
   directory is reused, so the 841 MB provider is not copied again per step);
3. ``terraform validate -json``;
4. ``terraform plan -refresh=false -lock=false -out=plan.bin`` and ``terraform show -json plan.bin``.

Nothing is written into ``scenarios/`` or the withheld test split. No AWS credential is used (``inputs.terraform_env``).
Standard library only.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from oracle import inputs

TIMEOUT_SECONDS = 600


def run_killing_tree(cmd: list[str], *, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess:
    """subprocess.run that, on timeout, kills the whole process tree (Terraform's provider child included)."""
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace", env=env, creationflags=flags, start_new_session=os.name != "nt")
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


def first_error_line(text: str) -> str:
    for ln in text.splitlines():
        if ln.strip().startswith("Error:"):
            return ln.strip()[:300]
    return next((ln.strip() for ln in text.splitlines() if ln.strip()), "no output")[:300]


class Runner:
    """One offline Terraform environment (its own data directory, CLI configuration and empty AWS files)."""

    def __init__(self, base: Path, terraform: str) -> None:
        self.base = inputs.check_destination(base)
        self.base.mkdir(parents=True, exist_ok=True)
        self.terraform = terraform
        rc = inputs.cli_config(self.base / "oracle.tfrc")
        self.env = inputs.terraform_env(self.base / "env", data_dir=self.base / "tf-data", cli_config_file=rc)
        seed = self.base / "seed"
        if seed.exists():
            shutil.rmtree(seed)
        seed.mkdir(parents=True)
        (seed / inputs.PROVIDER_FILE).write_text(inputs.provider_block(), encoding="utf-8", newline="\n")
        proc = self._tf(seed, "init", "-backend=false", "-input=false", "-no-color")
        if proc.returncode != 0:
            raise RuntimeError(f"seed init failed: {first_error_line(proc.stderr + proc.stdout)}")
        self.lock = (seed / ".terraform.lock.hcl").read_bytes()

    def _tf(self, work: Path, *args: str) -> subprocess.CompletedProcess:
        return run_killing_tree([self.terraform, f"-chdir={work}", *args], env=self.env, timeout=TIMEOUT_SECONDS)

    def run(self, step_dir: Path, values: dict[str, Any]) -> dict[str, Any]:
        """Run one step. Returns ``{status, stage, validate_ok, validate_error, plan, error_first_line, wall_seconds}``.

        ``status`` is ``planned`` (``plan`` holds the plan JSON), ``invalid`` (``terraform validate`` failed;
        registry 2.8) or ``failed`` (a stage failed or timed out; no plan JSON)."""
        out: dict[str, Any] = {"status": "failed", "stage": "", "validate_ok": None, "validate_error": "",
                               "plan": None, "error_first_line": "", "wall_seconds": 0.0}
        t0 = time.monotonic()
        work = self.base / "work"
        if work.exists():
            shutil.rmtree(work)
        try:
            inputs.build_working_copy(step_dir, values, work)
        except ValueError as exc:
            out.update(stage="working copy", error_first_line=str(exc).splitlines()[0][:300])
            return self._done(out, t0)
        (work / ".terraform.lock.hcl").write_bytes(self.lock)
        stages = (("init", ("init", "-backend=false", "-input=false", "-no-color")),
                  ("validate", ("validate", "-json", "-no-color")),
                  ("plan", ("plan", "-input=false", "-refresh=false", "-lock=false", "-no-color", "-out=plan.bin")),
                  ("show", ("show", "-json", "-no-color", "plan.bin")))
        for stage, args in stages:
            out["stage"] = stage
            try:
                proc = self._tf(work, *args)
            except subprocess.TimeoutExpired:
                out.update(error_first_line="timeout")
                return self._done(out, t0)
            if stage == "validate":
                try:
                    doc = json.loads(proc.stdout)
                except ValueError:
                    out.update(error_first_line=first_error_line(proc.stderr + proc.stdout))
                    return self._done(out, t0)
                out["validate_ok"] = bool(doc.get("valid"))
                if not out["validate_ok"]:
                    errs = [d for d in doc.get("diagnostics", []) if d.get("severity") == "error"]
                    out["validate_error"] = ("Error: " + errs[0].get("summary", "")) if errs else "Error: invalid"
                    out.update(status="invalid")
                    return self._done(out, t0)
                continue
            if proc.returncode != 0:
                out.update(error_first_line=first_error_line(proc.stderr + "\n" + proc.stdout).replace(str(work), "<work>"))
                return self._done(out, t0)
            if stage == "show":
                out.update(status="planned", plan=json.loads(proc.stdout))
        return self._done(out, t0)

    @staticmethod
    def _done(out: dict[str, Any], t0: float) -> dict[str, Any]:
        out["wall_seconds"] = round(time.monotonic() - t0, 2)
        return out
