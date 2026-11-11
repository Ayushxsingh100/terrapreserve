#!/usr/bin/env python3
"""D6: show that the rules protecting test-split secrecy, independence, label provenance and hash integrity fail when
broken.

Each mutation changes one file in place, runs the test that guards the rule, expects it to FAIL, and restores the
file byte for byte (also on error). Refuses to run with uncommitted changes in the files it mutates. Prints one line
per mutation; test-split ids are never printed. Standard library only.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
NL = chr(10)


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
    dev_json = REPO_ROOT / "scenarios" / "dev" / "tp-v1-F2-0258" / "scenario.json"
    return [
        ("hash integrity: one step content hash changed in V1_MANIFEST.json",
         REPO_ROOT / "scenarios" / "V1_MANIFEST.json",
         lambda t: re.sub(r'"content_hash": "([0-9a-f])', lambda m: '"content_hash": "' + ("0" if m.group(1) != "0" else "1"), t, count=1),
         "tests.test_d6_freeze.TestManifests.test_a4_v1_manifest_hashes_verify"),
        ("hash integrity: V1_MANIFEST.sha256 no longer matches the manifest",
         REPO_ROOT / "scenarios" / "V1_MANIFEST.sha256",
         lambda t: ("0" if t[0] != "0" else "1") + t[1:],
         "tests.test_d6_freeze.TestManifests.test_a4_v1_manifest_hashes_verify"),
        ("steps unchanged (A5): one byte appended to a real-world dev step file", rw,
         lambda t: t + NL, "tests.test_d6_freeze.TestUnchangedAgainst8db6278.test_a5_steps_and_labels_unchanged"),
        ("label provenance: a gt_class changed by hand in a dev scenario.json", dev_json,
         lambda t: t.replace('"gt_class": "unsafe"', '"gt_class": "safe"', 1),
         "tests.test_d6_freeze.TestUnchangedAgainst8db6278.test_a5_steps_and_labels_unchanged"),
        ("label provenance: a module outside oracle/ and tools/ writes gt_class",
         REPO_ROOT / "generator" / "writer.py",
         lambda t: t + NL + NL + "def _planted(d):" + NL + '    d["gt_class"] = "safe"' + NL,
         "tests.test_independence"),
        ("test-split secrecy: a test-split id written into docs/D6_FREEZE.md",
         REPO_ROOT / "docs" / "D6_FREEZE.md",
         lambda t: t + NL + test_id_from_manifest() + NL,
         "tests.test_d5b_labels.TestD5bLabels.test_no_test_split_id_in_committed_documents"),
        ("independence: a DAIL import added to tools/select_v1.py",
         REPO_ROOT / "tools" / "select_v1.py",
         lambda t: t.replace("import argparse" + NL, "import argparse" + NL + "import dail  # noqa" + NL, 1),
         "tests.test_independence"),
        ("v1 roles (D6-02): a promoted reserve set back to reserve", dev_json,
         lambda t: t.replace('"v1_role": "target"', '"v1_role": "reserve"', 1),
         "tests.test_d6_freeze.TestV1Roles.test_a2_dev_swaps_as_worked_by_hand"),
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
