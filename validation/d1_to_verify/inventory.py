"""Build INVENTORY.md: every "TO VERIFY" marker in the DAIL specification documents.

Usage: python inventory.py <path to a DAIL checkout> <output INVENTORY.md>

Runs ``git grep -n`` in ``docs/`` of the checkout for ``TO VERIFY`` and ``TO-VERIFY`` (case-sensitive, so
ordinary words such as "REVERIFYING" are not matched), extracts every bracketed marker
``[TO VERIFY ...]`` on each hit line, and writes one table row per marker. DAIL's documents are read as
text only; nothing from DAIL is imported.

``ITEM_OF`` assigns each marker to a resolution item. ``V01``..``V14`` are the reviewer's expected items;
``X01``.. are markers the grep found that the expected list did not name. A line that only *defines* the
marker convention is recorded as ``definition`` and needs no resolution.

Standard library only.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REG = "docs/specs/INVARIANT_REGISTRY_v1.md"
AMD = "docs/specs/D0_AMENDMENTS_v1.0.1.md"

# (file, line) -> item id, or "definition" for the two lines that explain the convention.
# Several markers on one line share the line's entry unless OCCURRENCE_ITEM overrides them.
ITEM_OF: dict[tuple[str, int], str] = {
    (AMD, 13): "definition",
    (REG, 14): "definition",
    (REG, 69): "V10",
    (REG, 84): "V08",
    (REG, 88): "V09",
    (REG, 105): "V11",
    (REG, 128): "X01",
    (REG, 130): "V06",
    (REG, 142): "V12",
    (REG, 240): "V04",
    (REG, 252): "V02",
    (REG, 261): "V05",
    (REG, 282): "V03",
    (REG, 299): "X02",
    (REG, 310): "V07",
    (REG, 376): "V13",
    (REG, 378): "V14",
    (REG, 464): "aggregate",
    (AMD, 99): "X03",
    (AMD, 100): "X04",
    (AMD, 111): "V01",
    (AMD, 135): "V02",
    (AMD, 136): "V03",
}

MARKER = re.compile(r"\[TO[ -]VERIFY[^\]]*\]")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    repo, out = Path(argv[1]), Path(argv[2])
    commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    hits: list[tuple[str, int, str]] = []
    for pattern in ("TO VERIFY", "TO-VERIFY"):
        result = subprocess.run(
            ["git", "-C", str(repo), "grep", "-n", "-F", pattern, "--", "docs"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        for raw in result.stdout.splitlines():
            path, line_no, text = raw.split(":", 2)
            hits.append((path, int(line_no), text))
    hits = sorted(set(hits))

    rows = []
    unmapped = []
    for path, line_no, text in hits:
        item = ITEM_OF.get((path, line_no))
        if item is None:
            unmapped.append((path, line_no))
            continue
        markers = MARKER.findall(text)
        if not markers and item != "definition":
            markers = ["(no bracketed marker; see line)"]
        if item == "definition":
            markers = markers or [text.strip()[:140]]
        for index, marker in enumerate(markers, start=1):
            rows.append((item, path, line_no, index, len(markers), marker))
    if unmapped:
        print("UNMAPPED grep hits (add them to ITEM_OF):", unmapped, file=sys.stderr)
        return 1

    order = {"definition": "~0", "aggregate": "~1"}
    rows.sort(key=lambda r: (order.get(r[0], r[0]), r[1], r[2], r[3]))
    lines = [
        "# Inventory of `TO VERIFY` markers",
        "",
        f"Source: DAIL commit `{commit}`, `git grep -n -F \"TO VERIFY\"` and `\"TO-VERIFY\"` in `docs/`",
        "(case-sensitive; the case-insensitive grep also matches the word REVERIFYING in register row C-30, which is not a marker).",
        "Produced by `validation/d1_to_verify/inventory.py`.",
        "",
        "Items `V01`-`V14` are the reviewer's expected set. `X01`-`X04` are markers the grep found that the",
        "expected set did not name. `definition` rows only explain the convention and need no resolution.",
        "`aggregate` is the registry's section 12 heading, which restates items already listed above.",
        "",
        "| Item | File:line | Marker text (exact) |",
        "|---|---|---|",
    ]
    for item, path, line_no, index, count, marker in rows:
        suffix = f" ({index}/{count})" if count > 1 else ""
        lines.append(f"| {item} | `{path}:{line_no}`{suffix} | {marker.replace('|', '\\|')} |")
    items = sorted({r[0] for r in rows if r[0] not in ("definition", "aggregate")})
    lines += [
        "",
        f"Markers found (rows above, excluding definitions): {sum(1 for r in rows if r[0] != 'definition')}",
        f"Resolution items: {len(items)} ({', '.join(items)})",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out}: {len(rows)} rows, items {items}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
