#!/usr/bin/env python3
"""D5a-3 (D5-09): mark the scenarios excluded from v1.0 from the D5a-3 feasibility measurement.

A scenario is excluded when any of its steps did not produce plan JSON under either value set in the D5a-3
feasibility results (``docs/d5a3/feasibility_dev_<set>.csv``; the test split's in
``$TERRAPRESERVE_PRIVATE/d5a3_feasibility_test_<set>.csv``). Its ``excluded_from_v1`` becomes
``{reason, failing_steps, first_error}``: ``failing_steps`` lists every failing (value set, step), primary first;
``first_error`` and the class and cause in ``reason`` are those of the first of them. Every other scenario gets
``null``. The value is written into the vv-3 search result (``generator/vv3/dev.json``,
``$TERRAPRESERVE_PRIVATE/vv3_test.json``), from which the generator copies it into ``scenario.json``; the
generator must be run again afterwards. Nothing else in the search result changes. Counts only are printed.
Standard library only.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import varvalues  # noqa: E402

SETS = ("primary", "alternate")


def rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"missing feasibility results: {path.name}")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def exclusion(failures: list[tuple[str, dict[str, str]]]) -> dict | None:
    if not failures:
        return None
    vset, first = failures[0]
    what = "; ".join(x for x in (first["error_class"], first["error_cause"]) if x)
    return {
        "reason": f"{len(failures)} step run(s) without plan JSON under vv-3 (D5-09); first: {vset} set, "
                  f"step {first['step']}, {what}",
        "failing_steps": [{"value_set": s, "step": int(r["step"])} for s, r in failures],
        "first_error": first["error_first_line"],
    }


def main() -> int:
    priv = os.environ.get("TERRAPRESERVE_PRIVATE")
    targets = [("dev", varvalues.SEARCH_DEV, REPO_ROOT / "docs" / "d5a3", "feasibility_dev_{}.csv")]
    if priv and Path(priv).is_dir():
        targets.append(("test", Path(priv) / varvalues.SEARCH_TEST_NAME, Path(priv), "d5a3_feasibility_test_{}.csv"))
    else:
        print("TERRAPRESERVE_PRIVATE not set: the test split is not marked")
    for split, search_path, feas_dir, pattern in targets:
        doc = json.loads(search_path.read_text(encoding="utf-8"))
        fails: dict[str, list[tuple[str, dict[str, str]]]] = {}
        measured: set[str] = set()
        for vset in SETS:
            for r in sorted(rows(feas_dir / pattern.format(vset)), key=lambda r: (r["scenario_id"], int(r["step"]))):
                measured.add(r["scenario_id"])
                if r["status"] != "success":
                    fails.setdefault(r["scenario_id"], []).append((vset, r))
        missing = set(doc["scenarios"]) - measured
        if missing:
            raise SystemExit(f"{split}: {len(missing)} scenarios have no feasibility rows")
        n = 0
        for sid, rec in doc["scenarios"].items():
            rec["excluded_from_v1"] = exclusion(fails.get(sid, []))
            n += rec["excluded_from_v1"] is not None
        search_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(f"{split}: {n} of {len(doc['scenarios'])} scenarios excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
