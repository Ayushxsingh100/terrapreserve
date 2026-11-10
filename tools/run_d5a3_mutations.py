#!/usr/bin/env python3
"""D5a-3: show that each vv-3 rule (record truthfulness, value-set integrity, test-split secrecy) fails when broken.

For each planted violation: copy ``generator/``, ``pool/``, ``sources/``, ``tests/``, ``scenarios/`` and
``docs/`` into a fresh temporary directory, plant exactly one violation there, run the real test of
``tests/test_d5a3_vv3.py`` from that copy (its ``REPO_ROOT`` is the copy), print the failing assertion, and delete
the copy. Dev split only (``TERRAPRESERVE_PRIVATE`` is unset for the runs, so no test-split id can be printed).
An unmodified copy must pass every test used. The real tree is never modified; the script checks that
``git status`` is the same before and after. Standard library only.
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
COPY_DIRS = ("generator", "pool", "sources", "tests", "scenarios", "docs")
SKIP = {"__pycache__", ".terraform"}
T = "tests.test_d5a3_vv3.TestVv3."


def _sj(root: Path, sid: str) -> Path:
    return root / "scenarios" / "dev" / sid / "scenario.json"


def _edit_json(path: Path, fn) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    fn(d)
    path.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _first(root: Path, pred) -> str:
    """The first dev scenario id (sorted) whose record satisfies ``pred``."""
    for p in sorted((root / "scenarios" / "dev").glob("tp-v1-*")):
        d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
        if pred(d):
            return d["scenario_id"]
    raise SystemExit("no scenario for this plant")


def _overridden(d) -> list[str]:
    return sorted(n for n, e in d["variable_values_kinds"].items() if "reason" in e)


def plant_override_dropped_from_search(root: Path) -> None:
    sid = _first(root, lambda d: _overridden(d))
    name = _overridden(json.loads(_sj(root, sid).read_text(encoding="utf-8")))[0]
    _edit_json(root / "generator" / "vv3" / "dev.json", lambda doc: doc["scenarios"][sid]["overrides"].pop(name))


def plant_reason_removed(root: Path) -> None:
    sid = _first(root, lambda d: _overridden(d))

    def fn(d):
        del d["variable_values_kinds"][_overridden(d)[0]]["reason"]
    _edit_json(_sj(root, sid), fn)


def plant_value_off_list(root: Path) -> None:
    def fn(d):
        d["variable_values"]["ami_id"] = "ami-0aaaaaaaaaaaaaaaa"
    _edit_json(_sj(root, "tp-v1-F7-0388"), fn)


def plant_index_missing(root: Path) -> None:
    def fn(d):
        del d["variable_values_candidates"]["primary"]["ami_id"]
    _edit_json(_sj(root, "tp-v1-F7-0388"), fn)


def plant_equal_sets(root: Path) -> None:
    def fn(d):
        d["variable_values_alt"]["ami_id"] = d["variable_values"]["ami_id"]
    _edit_json(_sj(root, "tp-v1-F7-0388"), fn)


def plant_whole_internet(root: Path) -> None:
    def fn(d):
        d["variable_values"]["vpc_config"]["cidr_block"] = "0.0.0.0/0"
    _edit_json(_sj(root, "tp-v1-F1-0225"), fn)


def plant_unexcluded_failure(root: Path) -> None:
    sid = _first(root, lambda d: d["excluded_from_v1"] is not None)
    _edit_json(_sj(root, sid), lambda d: d.__setitem__("excluded_from_v1", None))


def plant_excluded_without_failure(root: Path) -> None:
    sid = _first(root, lambda d: d["excluded_from_v1"] is None and d["source"]["tier"] == "real_world")
    _edit_json(_sj(root, sid), lambda d: d.__setitem__(
        "excluded_from_v1", {"reason": "planted", "failing_steps": [{"value_set": "primary", "step": 0}],
                             "first_error": "Error: planted"}))


def plant_record_off_search(root: Path) -> None:
    def fn(d):
        d["variable_values_candidates"]["alternate"]["ami_id"] = 1
        d["variable_values_alt"]["ami_id"] = "ami-07777777"
    _edit_json(_sj(root, "tp-v1-F7-0388"), fn)


def plant_controlled_byte(root: Path) -> None:
    f = root / "scenarios" / "dev" / "tp-v1-F1-0001" / "step_0" / "main.tf"
    f.write_bytes(f.read_bytes() + b"\n")


def plant_test_id_in_search(root: Path) -> None:
    manifest = json.loads((root / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
    tid = manifest[0]["scenario_id"]
    _edit_json(root / "generator" / "vv3" / "dev.json",
               lambda doc: doc["scenarios"].__setitem__(tid, {"candidates": {}, "overrides": {}}))


PLANTS = [
    ("(a) an overridden default whose override the search did not record", plant_override_dropped_from_search,
     "test_a_declared_defaults_that_plan_are_never_overridden"),
    ("(b) an overridden default without its reason", plant_reason_removed,
     "test_b_every_override_carries_the_rejection_reason"),
    ("(c) a value that is on no candidate list", plant_value_off_list,
     "test_c_values_come_from_the_fixed_lists_with_the_index_recorded"),
    ("(c) a valued variable without a recorded index", plant_index_missing,
     "test_c_values_come_from_the_fixed_lists_with_the_index_recorded"),
    ("(d) an alternate value equal to the primary without a recorded reason", plant_equal_sets,
     "test_d_the_two_sets_differ_except_where_recorded"),
    ("(e) an ipv4_cidr value of 0.0.0.0/0", plant_whole_internet, "test_e_no_ipv4_candidate_covers_the_whole_internet"),
    ("(f) a scenario with a failing step not excluded", plant_unexcluded_failure,
     "test_f_every_non_excluded_scenario_plans_under_both_sets"),
    ("(g) a scenario excluded although every step planned", plant_excluded_without_failure,
     "test_g_every_excluded_scenario_has_a_reason_and_a_failing_step"),
    ("(h) a record whose index and value differ from the search result", plant_record_off_search,
     "test_h_record_equals_a_fresh_vv3_computation"),
    ("(i) one byte added to a controlled step file", plant_controlled_byte,
     "test_i_controlled_steps_byte_identical_to_5f71c00"),
    ("(j) a test-split id in the dev search result", plant_test_id_in_search, "test_j_test_split_only_in_private_dir"),
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
    with tempfile.TemporaryDirectory(prefix="tp-d5a3-mut-") as tmp:
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
