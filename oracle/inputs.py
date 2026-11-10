"""The oracle's private working copy of a step (D5-02) and its offline Terraform setup (D5-04).

A working copy is a fresh directory outside the repository's scenario trees. It holds:

* the step's ``.tf`` files, byte for byte;
* ``zz_oracle_provider.tf``, the oracle-only ``provider "aws"`` block (region ``us-east-1``, placeholder keys
  built at run time, the four ``skip_*`` flags);
* ``terraform.tfvars.json``, written from one value set of the scenario (``variable_values`` or
  ``variable_values_alt``, rule vv-3, D5-10).

Nothing is ever written into ``scenarios/`` or into the withheld test split. Terraform runs with
``terraform_env``: no AWS environment variables, empty shared credentials and config files, the instance
metadata service disabled, a CLI configuration that installs ``hashicorp/aws`` only from the local filesystem
mirror (no registry download), and HTTP(S) proxies pointing at a closed local port, so any attempt to reach an
AWS endpoint fails on this machine and is recorded as a failure. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_FILE = "zz_oracle_provider.tf"
TFVARS_FILE = "terraform.tfvars.json"
MIRROR = Path.home() / ".terrapreserve-cache" / "tf-mirror"
DEAD_PROXY = "http://127.0.0.1:9"  # discard port: nothing listens, so a request fails before leaving the machine
_UNALIASED_AWS_PROVIDER = re.compile(r'^\s*provider\s+"aws"\s*\{', re.MULTILINE)


def _forbidden_roots() -> list[Path]:
    roots = [REPO_ROOT / "scenarios"]
    private = os.environ.get("TERRAPRESERVE_PRIVATE")
    roots.append(Path(private) if private else Path.home() / ".terrapreserve-private")
    return [r.resolve() for r in roots]


def check_destination(dest: Path, *, extra: tuple[Path, ...] = ()) -> Path:
    """Refuse a destination inside ``scenarios/``, the private test split, or any of ``extra``."""
    d = dest.resolve()
    for root in [*_forbidden_roots(), *(e.resolve() for e in extra)]:
        if d == root or root in d.parents:
            raise ValueError(f"the oracle never writes into {root}: refused destination {d}")
    return d


def _placeholder(part: str) -> str:
    # Built at run time from plain words: never a real key, and not credential-shaped.
    return "-".join(("tp", "oracle", "offline", part, "placeholder"))


def provider_block() -> str:
    """The oracle-only provider block (D5-04). No literal key is stored in this source file."""
    rows = [
        ("region", json.dumps("us-east-1")),
        ("access_key", json.dumps(_placeholder("access"))),
        ("secret_key", json.dumps(_placeholder("secret"))),
        ("skip_credentials_validation", "true"),
        ("skip_requesting_account_id", "true"),
        ("skip_metadata_api_check", "true"),
        ("skip_region_validation", "true"),
        # Addition to the D5-04 text: an attempted AWS call fails on its first refusal instead of being
        # retried with back-off for about ten minutes. It makes nothing plan that would not plan anyway.
        ("max_retries", "1"),
    ]
    width = max(len(k) for k, _v in rows)
    body = "".join(f"  {k.ljust(width)} = {v}\n" for k, v in rows)
    return '# Oracle-only provider configuration (TerraPreserve D5-04). Not part of the scenario.\n' \
           'provider "aws" {\n' + body + "}\n"


def build_working_copy(step_dir: Path, variable_values: dict[str, Any], dest: Path) -> Path:
    """Create ``dest`` (which must not exist, or be empty) as the oracle's working copy of ``step_dir``."""
    step_dir = step_dir.resolve()
    d = check_destination(dest, extra=(step_dir.parent,))
    if d.exists() and any(d.iterdir()):
        raise ValueError(f"working copy destination is not empty: {d}")
    d.mkdir(parents=True, exist_ok=True)
    tf_files = sorted(p for p in step_dir.glob("*.tf") if p.is_file())
    for p in tf_files:
        if p.name == PROVIDER_FILE:
            raise ValueError(f"step file {p.name} collides with the oracle's provider file name")
        if _UNALIASED_AWS_PROVIDER.search(p.read_text(encoding="utf-8")):
            raise ValueError(f"{p.name} declares its own provider \"aws\" block; the oracle block would duplicate it")
        shutil.copyfile(p, d / p.name)
    (d / PROVIDER_FILE).write_text(provider_block(), encoding="utf-8", newline="\n")
    (d / TFVARS_FILE).write_text(json.dumps(variable_values, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8", newline="\n")
    return d


def cli_config(path: Path, mirror: Path = MIRROR) -> Path:
    """Write a Terraform CLI configuration that installs hashicorp/aws from ``mirror`` and nothing else."""
    path.write_text(
        "provider_installation {\n"
        "  filesystem_mirror {\n"
        f'    path    = "{mirror.as_posix()}"\n'
        '    include = ["registry.terraform.io/hashicorp/aws"]\n'
        "  }\n"
        "}\n",
        encoding="utf-8", newline="\n")
    return path


def terraform_env(run_dir: Path, base: dict[str, str] | None = None, *, data_dir: Path | None = None,
                  cli_config_file: Path | None = None) -> dict[str, str]:
    """Environment for every Terraform command of the oracle: no credentials, no network to AWS."""
    src = dict(os.environ if base is None else base)
    env = {k: v for k, v in src.items()
           if not k.upper().startswith(("AWS_", "TF_VAR_", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY"))}
    run_dir.mkdir(parents=True, exist_ok=True)
    creds = run_dir / "empty_aws_credentials"
    conf = run_dir / "empty_aws_config"
    creds.write_text("", encoding="utf-8")
    conf.write_text("", encoding="utf-8")
    env.update({
        "AWS_SHARED_CREDENTIALS_FILE": str(creds),
        "AWS_CONFIG_FILE": str(conf),
        "AWS_EC2_METADATA_DISABLED": "true",
        "HTTP_PROXY": DEAD_PROXY, "HTTPS_PROXY": DEAD_PROXY, "http_proxy": DEAD_PROXY, "https_proxy": DEAD_PROXY,
        "NO_PROXY": "", "no_proxy": "",
        "TF_IN_AUTOMATION": "1", "TF_INPUT": "0", "CHECKPOINT_DISABLE": "1",
    })
    if data_dir is not None:
        env["TF_DATA_DIR"] = str(data_dir)
    if cli_config_file is not None:
        env["TF_CLI_CONFIG_FILE"] = str(cli_config_file)
    return env
