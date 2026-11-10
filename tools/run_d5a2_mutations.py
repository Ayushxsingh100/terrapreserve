#!/usr/bin/env python3
"""D5a-2: show that each value-set integrity rule fails when broken (scratch copy, failing test, restore).

For each planted violation: copy ``generator/``, ``pool/``, ``sources/``, ``tests/`` and ``scenarios/`` into a fresh
temporary directory, plant exactly one violation there, run the real test of
``tests/test_d5a2_value_sets.py`` from that copy (its ``REPO_ROOT`` is the copy), print the failing assertion,
and delete the copy. Dev split only (``TERRAPRESERVE_PRIVATE`` is unset for the runs, so no test-split id can
be printed). The real tree is never modified; the script checks that ``git status`` is the same before and after.
Standard library only.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COPY_DIRS = ("generator", "pool", "sources", "tests", "scenarios")
SKIP = {"__pycache__", ".terraform"}
T = "tests.test_d5a2_value_sets.TestValueSets."


def _sj(root: Path, sid: str) -> Path:
    return root / "scenarios" / "dev" / sid / "scenario.json"


def _edit_json(root: Path, sid: str, fn) -> None:
    p = _sj(root, sid)
    d = json.loads(p.read_text(encoding="utf-8"))
    fn(d)
    p.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def plant_same_alt(root: Path) -> None:
    def fn(d):
        d["variable_values_alt"]["ami_id"] = d["variable_values"]["ami_id"]
    _edit_json(root, "tp-v1-F7-0388", fn)


def plant_missing_alt(root: Path) -> None:
    def fn(d):
        del d["variable_values_alt"]["vpc_id"]
    _edit_json(root, "tp-v1-F7-0388", fn)


def plant_unlisted_variable(root: Path) -> None:
    def fn(d):
        del d["variable_values"]["subnet_id"], d["variable_values_alt"]["subnet_id"]
        del d["variable_values_kinds"]["subnet_id"]
    _edit_json(root, "tp-v1-F7-0388", fn)


def plant_value_off_rule(root: Path) -> None:
    def fn(d):
        d["variable_values"]["tp_ds_aws_ami_ubuntu"] = {"id": "ami-0aaaaaaaaaaaaaaaa"}
    _edit_json(root, "tp-v1-F1-0227", fn)


def plant_transform_sha(root: Path) -> None:
    def fn(d):
        for e in d["host_transform"]:
            if e.get("kind") == "data_source_to_variable":
                e["block_sha256"] = "0" * 64
                break
    _edit_json(root, "tp-v1-F1-0227", fn)


def plant_data_block(root: Path) -> None:
    f = root / "scenarios" / "dev" / "tp-v1-F1-0227" / "step_0" / "servers.tf"
    f.write_text(f.read_text(encoding="utf-8") + '\ndata "aws_region" "planted" {}\n', encoding="utf-8",
                 newline="\n")


def plant_controlled_byte(root: Path) -> None:
    f = root / "scenarios" / "dev" / "tp-v1-F1-0001" / "step_0" / "main.tf"
    f.write_bytes(f.read_bytes() + b"\n")


def plant_test_id_dir(root: Path) -> None:
    manifest = json.loads((root / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
    (root / "scenarios" / "dev" / manifest[0]["scenario_id"]).mkdir()


PLANTS = [
    ("(b) alternate value equal to the primary without a recorded exception", plant_same_alt, "test_b_the_two_sets_differ_except_where_recorded"),
    ("(b) a valued variable without an alternate value", plant_missing_alt, "test_b_the_two_sets_differ_except_where_recorded"),
    ("(a) a variable without a default left out of both sets", plant_unlisted_variable, "test_a_every_variable_has_both_values_or_a_reason"),
    ("(h) a stored value that the rule does not give", plant_value_off_rule, "test_h_record_equals_a_fresh_computation"),
    ("(e) a transform record whose sha256 matches no removed block", plant_transform_sha, "test_e_every_transform_matches_a_removed_block"),
    ("(d) a data block in a step", plant_data_block, "test_d_no_data_block_or_reference_in_any_step"),
    ("(f) one byte added to a controlled step file", plant_controlled_byte, "test_f_controlled_steps_byte_identical_to_e96c017"),
    ("(g) a test-split id directory inside the repository", plant_test_id_dir, "test_g_test_split_only_in_private_dir"),
]


def _copy_tree(dst: Path) -> None:
    for d in COPY_DIRS:
        shutil.copytree(REPO_ROOT / d, dst / d, ignore=shutil.ignore_patterns(*SKIP))


def _run(root: Path, test: str) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k != "TERRAPRESERVE_PRIVATE"}
    proc = subprocess.run([sys.executable, "-m", "unittest", T + test], cwd=root, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def _git_status() -> str:
    return subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True).stdout


def main() -> int:
    before = _git_status()
    unexpected = 0
    with tempfile.TemporaryDirectory(prefix="tp-d5a2-mut-") as tmp:
        clean = Path(tmp) / "clean"
        _copy_tree(clean)
        print("=== control (unmodified copy) ===")
        for test in sorted({p[2] for p in PLANTS}):
            rc, _out = _run(clean, test)
            print(f"{test}: {'ok' if rc == 0 else 'FAIL'}")
            unexpected += rc != 0
        shutil.rmtree(clean)
        for i, (label, plant, test) in enumerate(PLANTS):
            root = Path(tmp) / f"plant{i}"
            _copy_tree(root)
            plant(root)
            rc, out = _run(root, test)
            print(f"\n=== planted: {label} -> {test} ===")
            msgs = [ln for ln in out.splitlines() if ln.startswith("AssertionError")]
            print("\n".join(m[:300] for m in msgs[:2]))
            print("EXPECTED FAILURE CAUGHT" if rc != 0 else "UNEXPECTED PASS: the rule did not catch the plant")
            unexpected += rc == 0
            shutil.rmtree(root)
    after = _git_status()
    print(f"\nreal tree unchanged: {before == after}")
    return 1 if unexpected or before != after else 0


if __name__ == "__main__":
    sys.exit(main())
