#!/usr/bin/env python3
"""Write ``generator/templates/FEATURES.md`` (D4c-03, D4c-04): the template feature table generated from
``generator/templates`` and the per-cell operator coverage generated from ``generator/operators`` (which operators
of each family x class cell a template accepts). ``--check`` compares instead of writing. Standard library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for sub in ("sources", "pool", "generator"):
    if str(REPO_ROOT / sub) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / sub))

import generate  # noqa: E402
import templates  # noqa: E402

OUT = REPO_ROOT / "generator" / "templates" / "FEATURES.md"


def render() -> str:
    lines = [templates.features_table().rstrip("\n"), "", "## Per-cell operator coverage (D4c-04)", "",
             "Number of operators of each family x class cell (s = safe, u = unsafe) that the template accepts "
             "(an operator that raises `OperatorNotApplicable` on the template's step 0 is not counted). A template "
             "with 0 in a cell does not serve that cell and is never assigned to it.", ""]
    cells = [(f, c) for f in generate.FAMILIES for c in generate.CLASSES]
    lines.append("| Template | " + " | ".join(f"{f}{c[0]}" for f, c in cells) + " |")
    lines.append("|---" * (len(cells) + 1) + "|")
    missing = []
    for t in sorted(templates.TEMPLATES):
        counts = []
        for f, c in cells:
            n = len(generate.serving(t, f, c))
            counts.append(str(n))
            if n == 0:
                missing.append(f"- {t} does not serve {f} {c}")
        lines.append(f"| {t} | " + " | ".join(counts) + " |")
    lines += ["", "Templates that do not serve a cell: " + ("none." if not missing else ""), *missing]
    return "\n".join(lines) + "\n"


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        ok = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print("FEATURES.md is current" if ok else "FEATURES.md differs from the code")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
