#!/usr/bin/env python3
"""TP-V: score the human audit against the oracle (``docs/AUDIT_PROTOCOL_v1.md``, Scoring). Run in V3 only.

* ``--record-hash`` stores the SHA-256 of the completed ``audit_labels.csv`` in ``audit_labels.sha256`` (before
  any scoring).
* ``--score`` first checks that hash (it refuses when the file changed or no hash was recorded), checks the private
  directory against the pinned private manifest, validates the CSV (every pre-filled row present once; ``label``
  one of ``PASS``, ``FAIL``, ``CANNOT_TELL``; a ``note`` for every ``CANNOT_TELL``), and then reports:
  Cohen's kappa and percent agreement per invariant and overall, over the cells where both the auditor and the
  oracle say ``PASS`` or ``FAIL``; the ``CANNOT_TELL`` cells and the oracle's non-``PASS``/``FAIL`` cells, counted
  apart; per scenario, the auditor's class by the oracle's own rule (D5-11, ``oracle.label.gt_class``; a
  ``CANNOT_TELL`` counts as a non-definite result) against the oracle's class; every disagreement.

Everything is written under ``$TERRAPRESERVE_PRIVATE/audit/v1/`` (``report.json``, ``report.md``); nothing is
printed about the labels. No label is changed. Standard library and ``oracle.label`` only; no DAIL import.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import audit_packet as ap  # noqa: E402
from oracle import label as oracle_label  # noqa: E402

CHOICES = ("PASS", "FAIL", "CANNOT_TELL")
DEFINITE = ("PASS", "FAIL")
HASH_FILE = "audit_labels.sha256"


def kappa(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """Cohen's kappa and percent agreement over (auditor, oracle) pairs of PASS/FAIL. ``kappa`` is None when the
    chance agreement is 1 (both raters used one category only), and the pair count is 0 or not."""
    n = len(pairs)
    if n == 0:
        return {"n": 0, "agreement": None, "kappa": None}
    po = sum(a == o for a, o in pairs) / n
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(o == c for _, o in pairs) / n) for c in DEFINITE)
    return {"n": n, "agreement": po, "kappa": None if pe == 1 else (po - pe) / (1 - pe)}


def auditor_class(results: list[dict[str, str]], target: str | None) -> str | None:
    """The auditor's class by D5-11 (the oracle's rule); a CANNOT_TELL is a non-definite result."""
    mapped = [{inv: ("UNKNOWN" if r[inv] == "CANNOT_TELL" else r[inv]) for inv in ap.INVARIANTS} for r in results]
    return oracle_label.gt_class(mapped, target)[0]


def audit_dir(private: Path) -> Path:
    return Path(private) / ap.AUDIT_DIR


def record_hash(private: Path) -> str:
    d = audit_dir(private)
    digest = ap.sha256((d / "audit_labels.csv").read_bytes())
    (d / HASH_FILE).write_text(f"{digest}  audit_labels.csv\n", encoding="utf-8", newline="\n")
    return digest


def check_hash(private: Path) -> str:
    d = audit_dir(private)
    if not (d / HASH_FILE).is_file():
        raise SystemExit("no recorded SHA-256 of audit_labels.csv: run --record-hash first")
    recorded = (d / HASH_FILE).read_text(encoding="utf-8").split()[0]
    actual = ap.sha256((d / "audit_labels.csv").read_bytes())
    if recorded != actual:
        raise SystemExit("audit_labels.csv does not match its recorded SHA-256: refusing to score")
    return actual


def read_rows(path: Path, expected: set[tuple[str, int, str]]) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    seen: set[tuple[str, int, str]] = set()
    problems = []
    for r in rows:
        k = (r["packet_id"], int(r["step"]), r["invariant_id"])
        if k in seen or k not in expected:
            problems.append(f"row {k}: duplicate or not a packet cell")
        seen.add(k)
        if r["label"] not in CHOICES:
            problems.append(f"row {k}: label {r['label']!r} is not one of {CHOICES}")
        if r["label"] == "CANNOT_TELL" and not (r.get("note") or "").strip():
            problems.append(f"row {k}: CANNOT_TELL without a note")
    if seen != expected:
        problems.append(f"{len(expected - seen)} cells missing")
    if problems:
        raise SystemExit(f"audit_labels.csv is not complete or valid: {len(problems)} problems; first: {problems[0]}")
    return rows


def score(rows: list[dict[str, Any]], truth: dict[str, list[dict[str, str]]], targets: dict[str, str | None],
          oracle_classes: dict[str, str | None]) -> dict[str, Any]:
    """The report from the auditor's rows and the oracle's per-step results, by packet id."""
    cells = {"total": len(rows), "compared": 0, "agreed": 0, "cannot_tell": 0, "oracle_not_definite": 0}
    pairs: dict[str, list[tuple[str, str]]] = {inv: [] for inv in ap.INVARIANTS}
    disagreements = []
    auditor: dict[str, list[dict[str, str]]] = {pid: [{} for _ in steps] for pid, steps in truth.items()}
    for r in sorted(rows, key=lambda r: (r["packet_id"], int(r["step"]), ap.INVARIANTS.index(r["invariant_id"]))):
        pid, k, inv, a = r["packet_id"], int(r["step"]), r["invariant_id"], r["label"]
        o = truth[pid][k][inv]
        auditor[pid][k][inv] = a
        if a == "CANNOT_TELL":
            cells["cannot_tell"] += 1
            continue
        if o not in DEFINITE:
            cells["oracle_not_definite"] += 1
            continue
        cells["compared"] += 1
        cells["agreed"] += a == o
        pairs[inv].append((a, o))
        if a != o:
            disagreements.append({"packet_id": pid, "step": k, "invariant_id": inv, "auditor": a, "oracle": o,
                                  "note": r.get("note") or ""})
    scenarios = []
    for pid in sorted(truth):
        ac = auditor_class(auditor[pid], targets[pid])
        scenarios.append({"packet_id": pid, "auditor_class": ac, "oracle_class": oracle_classes[pid],
                          "agree": ac == oracle_classes[pid]})
    return {"protocol": "docs/AUDIT_PROTOCOL_v1.md", "cells": cells,
            "per_invariant": {inv: kappa(p) for inv, p in pairs.items()},
            "overall": kappa([x for p in pairs.values() for x in p]),
            "scenarios": scenarios, "scenario_class_agreement": sum(s["agree"] for s in scenarios),
            "disagreements": disagreements}


def report_md(rep: dict[str, Any], csv_sha256: str) -> str:
    def f(x: Any) -> str:
        return "undefined" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))
    lines = ["# Human label audit v1: scoring (private)", "",
             f"Protocol: `docs/AUDIT_PROTOCOL_v1.md`. `audit_labels.csv` SHA-256 `{csv_sha256}` (checked before "
             "scoring).", "", "## Cells", ""]
    lines += [f"- {k}: {v}" for k, v in rep["cells"].items()]
    lines += ["", "## Agreement (cells where both say PASS or FAIL)", "", "| Invariant | n | agreement | kappa |",
              "|---|---|---|---|"]
    for inv, k in list(rep["per_invariant"].items()) + [("overall", rep["overall"])]:
        lines.append(f"| {inv} | {k['n']} | {f(k['agreement'])} | {f(k['kappa'])} |")
    lines += ["", f"## Scenario class (D5-11): {rep['scenario_class_agreement']} of {len(rep['scenarios'])} agree",
              "", "| Packet | auditor | oracle |", "|---|---|---|"]
    lines += [f"| {s['packet_id']} | {s['auditor_class']} | {s['oracle_class']} |" for s in rep["scenarios"]]
    lines += ["", f"## Disagreements ({len(rep['disagreements'])}; the cause is assigned afterwards by both authors)",
              "", "| Packet | step | invariant | auditor | oracle | note |", "|---|---|---|---|---|---|"]
    lines += [f"| {d['packet_id']} | {d['step']} | {d['invariant_id']} | {d['auditor']} | {d['oracle']} | "
              f"{d['note'].replace('|', '/')} |" for d in rep["disagreements"]]
    return "\n".join(lines) + "\n"


def run_score(private: Path, pin: str) -> dict[str, Any]:
    private = Path(private).resolve()
    if private == REPO_ROOT or REPO_ROOT in private.parents:
        raise SystemExit("the private directory must lie outside the repository")
    csv_sha = check_hash(private)
    entries = {e["scenario_id"]: e for e in ap.open_private(private, pin)}
    d = audit_dir(private)
    key = json.loads((d / "key.json").read_text(encoding="utf-8"))
    truth, targets, classes = {}, {}, {}
    expected: set[tuple[str, int, str]] = set()
    for pid, sid in key.items():
        doc = ap._checked_doc(private, entries[sid])
        steps = sorted(doc["steps"], key=lambda s: s["step"])
        truth[pid] = [doc["labels"][s["step"]]["invariant_truth"] for s in steps]
        targets[pid] = oracle_label.repair_target(doc)
        classes[pid] = doc.get("gt_class")
        expected |= {(pid, s["step"], inv) for s in steps for inv in ap.INVARIANTS}
    rows = read_rows(d / "audit_labels.csv", expected)
    rep = score(rows, truth, targets, classes)
    rep["audit_labels_sha256"] = csv_sha
    (d / "report.json").write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (d / "report.md").write_text(report_md(rep, csv_sha), encoding="utf-8", newline="\n")
    return rep


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--record-hash", action="store_true")
    g.add_argument("--score", action="store_true")
    p.add_argument("--private", help="the private directory (default $TERRAPRESERVE_PRIVATE)")
    args = p.parse_args(argv)
    raw = args.private or os.environ.get("TERRAPRESERVE_PRIVATE")
    if not raw or not Path(raw).is_dir():
        raise SystemExit("the private directory (--private or $TERRAPRESERVE_PRIVATE) does not exist")
    if args.record_hash:
        print(f"recorded: {record_hash(Path(raw))}  audit_labels.csv")
        return 0
    run_score(Path(raw), ap.private_manifest_pin())
    print(f"written: {audit_dir(Path(raw)) / 'report.json'} and report.md (no result is printed here)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
