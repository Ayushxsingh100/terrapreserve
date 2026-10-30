"""The terraform validate harness (E12) and the neutralisation it needs (D3-09).

``neutralise`` is the deterministic transformation that D4 must reproduce when it builds scenarios: every
top-level ``terraform`` and ``provider`` block is removed from every file, and one extra file pins Terraform
``~> 1.15.0`` and ``hashicorp/aws`` exactly 6.53.0 (CLAUDE.md rule 3). The pin file is named
``terrapreserve_versions.tf`` and not ``versions.tf``, because a module may already own a ``versions.tf``.
The committed pool files stay verbatim; only the copy that Terraform reads is neutralised.

``Harness`` runs ``terraform init -backend=false`` once against a **local filesystem mirror** of the 6.53.0
provider (no registry traffic), then ``terraform validate -json`` per module in the same working directory.
Nothing here runs ``plan``, ``apply`` or ``destroy``, and no credentials are involved.
Standard library and ``sources/*`` only.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import acquire
import hcl_lex

PIN_FILE_NAME = "terrapreserve_versions.tf"
PROVIDER_VERSION = "6.53.0"
TERRAFORM_SERIES = "1.15."
# Identical to validation/smoke/versions.tf (tests/test_validate.py checks it).
PINS_TF = """terraform {
  required_version = "~> 1.15.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.53.0"
    }
  }
}
"""
REMOVED_BLOCKS = ("terraform", "provider")
ERROR_CLASS_LIMIT = 200
VALIDATE_TIMEOUT_SECONDS = 180


class HarnessError(RuntimeError):
    """Terraform or the provider mirror is unusable. The run must stop; nothing is skipped silently."""


@dataclass(frozen=True)
class Result:
    status: str  # valid | invalid | error
    terraform_version: str
    provider_version: str
    error_class: str


def neutralise(files: dict[str, str]) -> dict[str, str]:
    """Copy of ``files`` (``.tf`` only) without top-level terraform and provider blocks, plus the pin file."""
    out = {
        name: hcl_lex.remove_top_level_blocks(text, REMOVED_BLOCKS)
        for name, text in files.items()
        if name.endswith(".tf")
    }
    out[PIN_FILE_NAME] = PINS_TF
    return out


def parse_result(stdout: str, returncode: int) -> tuple[str, str]:
    """(status, error class) from ``terraform validate -json``. The class is the first error's summary,
    at most 200 characters; the detail text, which may quote values, is never read."""
    try:
        doc = json.loads(stdout)
    except ValueError:
        return "error", "terraform output was not JSON"
    if not isinstance(doc, dict) or "valid" not in doc:
        return "error", "terraform output was not JSON"
    if doc["valid"]:
        return "valid", ""
    for diagnostic in doc.get("diagnostics") or []:
        if isinstance(diagnostic, dict) and diagnostic.get("severity") == "error":
            return "invalid", str(diagnostic.get("summary", ""))[:ERROR_CLASS_LIMIT]
    return "invalid", "no error diagnostic"


def rc_file(cache: Path | None = None) -> Path:
    return (cache or acquire.cache_root()) / "terraformrc"


def mirror_dir(cache: Path | None = None) -> Path:
    return (cache or acquire.cache_root()) / "tf-mirror"


def write_rc(path: Path, mirror: Path) -> None:
    """CLI configuration that installs hashicorp/aws from ``mirror`` only (never from the registry)."""
    path.write_text(
        'provider_installation {\n'
        f'  filesystem_mirror {{\n    path    = "{mirror.as_posix()}"\n    include = ["registry.terraform.io/hashicorp/aws"]\n  }}\n'
        '  direct {\n    exclude = ["registry.terraform.io/hashicorp/aws"]\n  }\n}\n',
        encoding="utf-8", newline="\n",
    )


def unavailable_reason() -> str | None:
    """Why the harness cannot run here, or ``None`` if it can."""
    terraform = shutil.which("terraform")
    if terraform is None:
        return "terraform is not on PATH"
    try:
        out = subprocess.run([terraform, "version", "-json"], capture_output=True, text=True, timeout=60,
                             env={**os.environ, "CHECKPOINT_DISABLE": "1"}, check=False)
        version = json.loads(out.stdout)["terraform_version"]
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        return f"terraform version could not be read ({type(exc).__name__})"
    if not version.startswith(TERRAFORM_SERIES):
        return f"terraform is {version}, the pin is {TERRAFORM_SERIES}x"
    try:
        cache = acquire.cache_root()
    except acquire.AcquireError as exc:
        return str(exc)
    if not rc_file(cache).is_file():
        return f"no provider-mirror CLI configuration at {rc_file(cache)}"
    if not (mirror_dir(cache) / "registry.terraform.io" / "hashicorp" / "aws" / PROVIDER_VERSION).is_dir():
        return f"the mirror at {mirror_dir(cache)} has no hashicorp/aws {PROVIDER_VERSION}"
    return None


class Harness:
    def __init__(self, work: Path, terraform: str, rc: Path) -> None:
        self.work = work
        self.terraform = terraform
        self.env = {
            **os.environ,
            "TF_CLI_CONFIG_FILE": str(rc),
            "TF_DATA_DIR": str(work / "data"),
            "TF_IN_AUTOMATION": "1",
            "TF_INPUT": "0",
            "CHECKPOINT_DISABLE": "1",
        }
        self._versions: tuple[str, str] | None = None

    @classmethod
    def default(cls) -> "Harness":
        reason = unavailable_reason()
        if reason:
            raise HarnessError(reason)
        return cls(acquire.cache_root() / "d3-work" / "tfv", shutil.which("terraform"), rc_file())

    def _run(self, *args: str, timeout: int = VALIDATE_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
        return subprocess.run([self.terraform, f"-chdir={self.work}", *args], capture_output=True, text=True,
                              encoding="utf-8", env=self.env, timeout=timeout, check=False)

    def _clear(self) -> None:
        for path in self.work.glob("*.tf"):
            path.unlink()

    def ensure_ready(self) -> None:
        """Initialise the working directory once (``init -backend=false``, provider from the local mirror)."""
        self.work.mkdir(parents=True, exist_ok=True)
        self._clear()
        (self.work / PIN_FILE_NAME).write_text(PINS_TF, encoding="utf-8", newline="\n")
        init = self._run("init", "-backend=false", "-input=false", "-no-color", timeout=900)
        if init.returncode != 0:
            raise HarnessError(f"terraform init failed: {(init.stdout + init.stderr)[-600:]}")
        info = json.loads(self._run("version", "-json").stdout)
        provider = info.get("provider_selections", {}).get("registry.terraform.io/hashicorp/aws", "")
        self._versions = (info["terraform_version"], provider)
        if provider != PROVIDER_VERSION:
            raise HarnessError(f"initialised provider is {provider!r}, the pin is {PROVIDER_VERSION}")

    def validate(self, files: dict[str, str]) -> Result:
        if self._versions is None:
            self.ensure_ready()
        assert self._versions is not None
        terraform_version, provider_version = self._versions
        self._clear()
        for name, text in neutralise(files).items():
            (self.work / name).write_text(text, encoding="utf-8", newline="\n")
        try:
            proc = self._run("validate", "-json", "-no-color")
            status, klass = parse_result(proc.stdout, proc.returncode)
        except subprocess.TimeoutExpired:
            status, klass = "error", f"timeout after {VALIDATE_TIMEOUT_SECONDS} s"
        finally:
            self._clear()
        return Result(status, terraform_version, provider_version, klass)
