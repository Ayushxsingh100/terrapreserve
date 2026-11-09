#!/usr/bin/env python3
"""Format checker for TerraPreserve (D4b review fix).

Checks that first-party Terraform code passes ``terraform fmt -check``:
- validation/
- generator/ (if any .tf files exist)
- controlled tier scenarios (id <= 208)
- graft files in real-world scenarios (terrapreserve_graft*.tf)

Excludes verbatim third-party files:
- pool/
- verbatim host files in real-world scenarios (id > 208)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def collect_targets() -> list[Path]:
    targets: list[Path] = []

    # 1. validation/
    val_dir = REPO_ROOT / "validation"
    if val_dir.exists():
        targets.extend(val_dir.rglob("*.tf"))

    # 2. generator/
    gen_dir = REPO_ROOT / "generator"
    if gen_dir.exists():
        targets.extend(gen_dir.rglob("*.tf"))

    # 3. Controlled scenarios (dev) and graft files (dev)
    dev_dir = REPO_ROOT / "scenarios" / "dev"
    if dev_dir.exists():
        for d in sorted(dev_dir.glob("tp-v1-*")):
            try:
                num = int(d.name.split("-")[-1])
            except ValueError:
                continue
            if num <= 208:
                targets.extend(d.rglob("*.tf"))
            else:
                for p in d.rglob("*.tf"):
                    if "graft" in p.name:
                        targets.append(p)

    # 4. If private test split directory exists
    private_root = os.environ.get("TERRAPRESERVE_PRIVATE")
    if private_root:
        priv_dir = Path(private_root)
        if priv_dir.exists():
            for d in sorted(priv_dir.glob("tp-v1-*")):
                try:
                    num = int(d.name.split("-")[-1])
                except ValueError:
                    continue
                if num <= 208:
                    targets.extend(d.rglob("*.tf"))
                else:
                    for p in d.rglob("*.tf"):
                        if "graft" in p.name:
                            targets.append(p)

    return sorted(set(targets))


def main() -> int:
    tf = shutil.which("terraform")
    if not tf:
        print("ERROR: terraform executable not found in PATH", file=sys.stderr)
        return 1

    targets = collect_targets()
    print(f"Checking terraform fmt across {len(targets)} files...")

    failed_files: list[str] = []
    batch_size = 50
    for i in range(0, len(targets), batch_size):
        batch = [str(p) for p in targets[i : i + batch_size]]
        res = subprocess.run(
            [tf, "fmt", "-check"] + batch,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
            failed_files.extend(lines)

    if failed_files:
        print(f"FAILED: {len(failed_files)} files require reformatting:", file=sys.stderr)
        for f in failed_files:
            print(f"  {f}", file=sys.stderr)
        return 1

    print(f"PASS: all {len(targets)} files conform to terraform fmt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
