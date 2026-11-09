#!/usr/bin/env python3
"""D5a: show that each D5-03 independence rule fails when broken (scratch copy, failing test, restore).

For each planted violation: copy the Python sources and the dev ``scenario.json`` files into a fresh temporary
directory, plant exactly one violation there, run the real ``tests.test_independence.TestOracleIndependence``
against that copy (``TP_INDEPENDENCE_ROOT``), print the failing assertions, and delete the copy. The real tree
is never modified; the script checks that ``git status`` is the same before and after. Standard library only.
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
COPY_DIRS = ("oracle", "generator", "pool", "sources", "tests", "tools")
SKIP = {"__pycache__", ".terraform", "terrads", "terragoat"}

PLANTS = [
    ("oracle imports the generator's whole-module reader", "oracle/zz_plant.py", "from realworld import modread\n"),
    ("oracle imports a generator module", "oracle/zz_plant.py", "import varvalues\n"),
    ("oracle imports a round-5 self-check evaluator", "oracle/zz_plant.py", "import test_d4b_review_round5\n"),
    ("oracle imports a DAIL package", "oracle/zz_plant.py", "from core.impact import x\n"),
    ("oracle edits sys.path to reach generator/", "oracle/zz_plant.py",
     "import sys\nsys.path.insert(0, 'generator')\n"),
    ("generator writes a non-null label", "generator/zz_plant.py", "def f(sc):\n    sc['labels'] = [{'step': 0}]\n"),
    ("pool writes gt_class in a dict literal", "pool/zz_plant.py", "doc = {'gt_class': 'safe'}\n"),
]


def _copy_tree(dst: Path) -> None:
    for d in COPY_DIRS:
        for dirpath, dirnames, filenames in os.walk(REPO_ROOT / d):
            dirnames[:] = [x for x in dirnames if x not in SKIP]
            for f in filenames:
                if f.endswith(".py"):
                    src = Path(dirpath) / f
                    out = dst / src.relative_to(REPO_ROOT)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, out)
    for p in (REPO_ROOT / "scenarios" / "dev").glob("tp-v1-*/scenario.json"):
        out = dst / p.relative_to(REPO_ROOT)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, out)


def _run(root: Path) -> tuple[int, str]:
    env = dict(os.environ, TP_INDEPENDENCE_ROOT=str(root))
    proc = subprocess.run([sys.executable, "-m", "unittest", "-v", "tests.test_independence.TestOracleIndependence"],
                          cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def _git_status() -> str:
    return subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True).stdout


def main() -> int:
    before = _git_status()
    unexpected = 0
    with tempfile.TemporaryDirectory(prefix="tp-d5a-indep-") as tmp:
        clean = Path(tmp) / "clean"
        _copy_tree(clean)
        rc, out = _run(clean)
        print(f"=== control (unmodified copy): exit {rc} ===")
        print("\n".join(ln for ln in out.splitlines() if ln.endswith((" ... ok", " ... FAIL", " ... ERROR"))))
        if rc != 0:
            unexpected += 1
        cases = list(PLANTS) + [("a committed scenario carries a non-null gt_class", None, None)]
        for i, (label, rel, text) in enumerate(cases):
            root = Path(tmp) / f"plant{i}"
            _copy_tree(root)
            if rel is not None:
                (root / rel).write_text(text, encoding="utf-8")
            else:
                sj = sorted((root / "scenarios" / "dev").glob("tp-v1-*/scenario.json"))[0]
                d = json.loads(sj.read_text(encoding="utf-8"))
                d["gt_class"] = "safe"
                sj.write_text(json.dumps(d), encoding="utf-8")
            rc, out = _run(root)
            print(f"\n=== planted: {label} ===")
            lines = out.splitlines()
            print("\n".join(ln for ln in lines if ln.endswith((" ... FAIL", " ... ERROR"))))
            msgs = [ln for ln in lines if ln.startswith(("AssertionError", "+ ", "- ", "First differing"))]
            print("\n".join(msgs[:6]))
            print("EXPECTED FAILURE CAUGHT" if rc != 0 else "UNEXPECTED PASS: the rule did not catch the plant")
            if rc == 0:
                unexpected += 1
            shutil.rmtree(root)
    after = _git_status()
    print(f"\nreal tree unchanged: {before == after}")
    return 1 if unexpected or before != after else 0


if __name__ == "__main__":
    sys.exit(main())
