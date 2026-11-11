#!/usr/bin/env python3
"""D4c-05: re-run the whole-module screen (``generator/realworld/modread.py``) on the unchanged real-world tier,
with the reader at ``49837f2`` (before the D4c fixes) and with the fixed reader, over every step of every
real-world scenario. Prints, per split, the steps whose screen codes differ between the two readers (dev: ids;
test: counts only). Nothing is written and no scenario changes. Standard library only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

from realworld import modread as new_reader  # noqa: E402

BASE = "49837f2"


def old_reader():
    text = subprocess.run(["git", "show", f"{BASE}:generator/realworld/modread.py"], cwd=REPO_ROOT,
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout
    tmp = Path(tempfile.mkdtemp(prefix="tp-modread-")) / "modread_49837f2.py"
    tmp.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("modread_49837f2", tmp)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["modread_49837f2"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def main() -> int:
    old = old_reader()
    roots = [("dev", REPO_ROOT / "scenarios" / "dev")]
    priv = os.environ.get("TERRAPRESERVE_PRIVATE")
    if priv and Path(priv).is_dir():
        roots.append(("test", Path(priv)))
    out = {}
    for split, root in roots:
        steps = 0
        changed: dict[str, list[str]] = {}
        for p in sorted(root.glob("tp-v1-*")):
            d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
            if d["source"]["tier"] != "real_world":
                continue
            for s in sorted(d["steps"], key=lambda x: x["step"]):
                files = {f.name: f.read_text(encoding="utf-8") for f in (p / s["terraform_dir"]).glob("*.tf")}
                steps += 1
                a, b = old.analyse(files).codes, new_reader.analyse(files).codes
                if a != b:
                    added = [c for c in b if c not in a]
                    changed.setdefault(d["scenario_id"], []).append(f"step {s['step']}: +{added}")
        out[split] = {"steps": steps, "scenarios_changed": len(changed),
                      "detail": changed if split == "dev" else None}
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
