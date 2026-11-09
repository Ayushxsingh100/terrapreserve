"""Label record writer (D5-02): the D0 Decision 6 ``labels`` and ``oracle`` structures.

D0 Decision 6: ``labels [ { step, invariant_truth { INV-ID: PASS|FAIL|UNKNOWN|UNSUPPORTED }, oracle_affected
[INV-ID], target_safe: bool } ]`` and ``oracle { versions, disagreements[] }``. "Labels are property truth, not
DAIL decisions."

In D5a this module writes a **dry run only**: every truth value is ``null``, ``target_safe`` is ``null`` and
``oracle_affected`` is empty. There is no code path that writes a real label, and nothing is written into
``scenarios/`` or the withheld test split. Standard library only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oracle.VERSION import ORACLE_VERSION
from oracle.inputs import check_destination

INVARIANTS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001")


def dry_run(scenario: dict[str, Any], versions: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """(labels, oracle) for ``scenario`` with null truth values (D0 gate 9 versions recorded)."""
    labels = [
        {"step": s["step"], "invariant_truth": {inv: None for inv in INVARIANTS},
         "oracle_affected": [], "target_safe": None}
        for s in scenario["steps"]
    ]
    oracle_block = {
        "versions": {**versions, "oracle": ORACLE_VERSION, "generator": scenario.get("generator_version")},
        "disagreements": [],
        "dry_run": True,
    }
    return labels, oracle_block


def write_dry_run(scenario: dict[str, Any], out_path: Path, versions: dict[str, str]) -> Path:
    """Write a dry-run record to ``out_path`` (never inside ``scenarios/`` or the private test split)."""
    path = check_destination(out_path)
    labels, oracle_block = dry_run(scenario, versions)
    doc = {"scenario_id": scenario["scenario_id"], "labels": labels, "oracle": oracle_block}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path
