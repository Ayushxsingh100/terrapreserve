#!/usr/bin/env python3
"""D4c: show that the rules protecting test-split secrecy, independence and record truthfulness fail when broken.

Each mutation changes one file in place, runs the test that guards the rule, expects it to FAIL, and restores the
file byte for byte (also on error). Refuses to run with uncommitted changes in the files it mutates. Prints one line
per mutation; test-split ids are never printed. Standard library only.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def first_dev_rw_file() -> Path:
    for p in sorted((REPO_ROOT / "scenarios" / "dev").glob("tp-v1-*")):
        if int(p.name.rsplit("-", 1)[1]) > 208:
            return next(f for f in sorted((p / "step_0").glob("*.tf")))
    raise SystemExit("no real-world dev scenario")


def test_id_from_manifest() -> str:
    import json
    m = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
    return m[0]["scenario_id"]


def mutations() -> list[tuple[str, Path, callable, str]]:
    rw = first_dev_rw_file()
    return [
        ("real-world tier byte-identical (A5): one byte appended to a real-world dev step file", rw,
         lambda t: t + "\n", "tests.test_d4c_templates.TestD4cTemplates.test_a5_real_world_tier_byte_identical_to_49837f2"),
        ("feature table generated from code: one axis value edited in FEATURES.md",
         REPO_ROOT / "generator" / "templates" / "FEATURES.md",
         lambda t: t.replace("| tpl-01 | all_separate |", "| tpl-01 | all_inline |", 1),
         "tests.test_d4c_templates.TestD4cTemplates.test_a2_feature_table_is_generated_from_code"),
        ("test-template draw recorded: one drawn test template swapped in split.json",
         REPO_ROOT / "scenarios" / "split.json",
         lambda t: t.replace('"tpl-27"', '"tpl-26"', 1),
         "tests.test_d4c_templates.TestD4cTemplates.test_a2_split_23_dev_10_test_with_the_draw_recorded"),
        ("test-split secrecy: a test-split id written into docs/D4C_DECISIONS.md",
         REPO_ROOT / "docs" / "D4C_DECISIONS.md",
         lambda t: t + "\n" + test_id_from_manifest() + "\n",
         "tests.test_d5b_labels.TestD5bLabels.test_no_test_split_id_in_committed_documents"),
        ("independence: a DAIL import added to the template module",
         REPO_ROOT / "generator" / "templates" / "__init__.py",
         lambda t: t.replace("import emitter\n", "import emitter\nimport dail  # noqa\n", 1),
         "tests.test_independence"),
        ("decision rows settled (A1): a settled row set back to Proposed",
         REPO_ROOT / "docs" / "D5_DECISIONS.md",
         lambda t: t.replace("| Decided | D0 Decision 6 label schema;", "| Proposed | D0 Decision 6 label schema;", 1),
         "tests.test_d4c_templates.TestD4cDecisions.test_a1_rows_settled"),
        ("self-check fix (A6): MIXED read per direction again",
         REPO_ROOT / "generator" / "realworld" / "modread.py",
         lambda t: t.replace('if (has_blocks and gf.rule_targets) or same_dir_empty:',
                             'if same_dir_empty or any(d in gf.rule_targets and getattr(gf, d) == "blocks" for d in ("ingress", "egress")):', 1),
         "tests.test_d4c_templates.TestD4cTemplates.test_a6_fixed_self_checks_flag_the_d5b_cases"),
    ]


def main() -> int:
    ok = True
    for label, path, change, test in mutations():
        rel = path.relative_to(REPO_ROOT).as_posix()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=REPO_ROOT, capture_output=True,
                               text=True).stdout.strip()
        if dirty:
            print(f"SKIP {label}: {rel} has uncommitted changes")
            ok = False
            continue
        before = path.read_bytes()
        text = before.decode("utf-8")
        after = change(text)
        if after == text:
            print(f"ERROR {label}: the mutation changed nothing")
            ok = False
            continue
        try:
            path.write_bytes(after.encode("utf-8"))
            r = subprocess.run([PY, "-m", "unittest", test], cwd=REPO_ROOT, capture_output=True, text=True,
                               env=dict(os.environ))
            failed = r.returncode != 0
            tail = [ln for ln in r.stderr.splitlines() if ln.startswith(("FAILED", "OK", "Ran"))]
            print(f"{'caught' if failed else 'NOT CAUGHT'}: {label} -> {test}: {' / '.join(tail)}")
            ok &= failed
        finally:
            path.write_bytes(before)
    clean = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True).stdout
    print("tree restored:", "yes" if not clean.strip() else "NO")
    return 0 if ok and not clean.strip() else 1


if __name__ == "__main__":
    sys.exit(main())
