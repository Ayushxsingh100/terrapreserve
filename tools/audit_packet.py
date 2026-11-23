#!/usr/bin/env python3
"""TP-V: draw the human-audit sample and write the blinded packet (``docs/AUDIT_PROTOCOL_v1.md``).

``--split test`` (the only split this tool serves):

* refuses unless the private directory (``--private``, default ``$TERRAPRESERVE_PRIVATE``) lies outside the
  repository and its ``V1_MANIFEST_PRIVATE.json`` has the SHA-256 that the frozen ``scenarios/V1_MANIFEST.sha256``
  records (as ``tools/label_llm.py`` does);
* draws one scenario per stratum (family F1..F8, then controlled before real-world, then safe before unsafe; the
  oracle class is the private manifest's ``gt_class``) from the 96 test targets with ``random.Random(20261124)``:
  within a stratum the candidates are sorted by id and one is picked with ``rng.choice``;
* shuffles the 32 with ``random.Random(20261125)`` and names them ``A01``..``A32``;
* checks every sampled ``scenario.json`` and every step against the private manifest's hashes, copies every step
  directory byte for byte and checks the copies' hashes again;
* writes, under ``$TERRAPRESERVE_PRIVATE/audit/v1/`` only: ``packet/<packet id>/`` (the step directories and a
  ``brief.json`` with only the allowed keys), ``audit_labels.csv`` (one row per packet, step and invariant, with
  ``label`` and ``note`` empty) and ``key.json`` (packet id -> scenario id, not part of the packet);
* checks the packet is blinded before it ends, and refuses to run when ``audit/v1`` already exists.

It prints only the number of packets, the number of CSV rows, the SHA-256 of ``key.json`` and the path: no id, no
class. Standard library only; no DAIL import (CLAUDE.md rule 5).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_SUMS = REPO_ROOT / "scenarios" / "V1_MANIFEST.sha256"
PRIVATE_MANIFEST = "V1_MANIFEST_PRIVATE.json"
AUDIT_DIR = Path("audit") / "v1"

SEED_DRAW = 20261124
SEED_ORDER = 20261125
FAMILIES = tuple(f"F{i}" for i in range(1, 9))
TIERS = ("controlled", "real_world")
CLASSES = ("safe", "unsafe")
INVARIANTS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001")
CSV_FIELDS = ("packet_id", "step", "invariant_id", "label", "note")

BRIEF_KEYS = frozenset({"packet_id", "family", "target", "endpoints", "variable_values", "steps"})
TARGET_KEYS = frozenset({"kind", "invariant_id"})
ENDPOINT_KEYS = frozenset({"S", "D"})
# Never in the packet (protocol: labels, gt_class, oracle, intent, mutation_record, target.description,
# v1_role_reason, parameters, the diffs, the alternate value set; plus the label fields of a step).
FORBIDDEN_KEYS = ("labels", "gt_class", "oracle", "intent", "mutation_record", "description", "v1_role_reason",
                  "parameters", "diff_from_previous", "variable_values_alt", "invariant_truth", "oracle_affected",
                  "target_safe", "excluded_from_v1", "v1_role")
LABEL_WORDS = ("PASS", "FAIL", "UNKNOWN", "UNSUPPORTED", "VERIFIER_ERROR", "CANNOT_TELL", "safe", "unsafe")
_KEY_RE = re.compile(r'"(' + "|".join(map(re.escape, FORBIDDEN_KEYS)) + r')"\s*:')
_NEAR_RE = re.compile(r"INV-(?:SEC|FUNC)-\d{3}[^\n]{0,40}?\b(?:" + "|".join(LABEL_WORDS) + r")\b|\b(?:"
                      + "|".join(LABEL_WORDS) + r")\b[^\n]{0,40}?INV-(?:SEC|FUNC)-\d{3}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(directory: Path) -> str:
    """D4-09: SHA-256 of the path-sorted lines ``"<relative POSIX path>:<sha256 of the bytes>"``."""
    files = sorted((p.relative_to(directory).as_posix(), p) for p in directory.rglob("*") if p.is_file())
    return sha256("\n".join(f"{rel}:{sha256(p.read_bytes())}" for rel, p in files).encode("utf-8"))


# --- the draw (protocol: Sample) ---------------------------------------------------------------------------------


def strata() -> list[tuple[str, str, str]]:
    return [(f, t, c) for f in FAMILIES for t in TIERS for c in CLASSES]


def draw(population: list[dict[str, Any]]) -> list[str]:
    """One scenario id per stratum, in stratum order. ``population`` holds ``scenario_id``, ``family``, ``tier``
    and ``oracle_class`` of each target."""
    rng = random.Random(SEED_DRAW)
    out = []
    for f, t, c in strata():
        cands = sorted(p["scenario_id"] for p in population if (p["family"], p["tier"], p["oracle_class"]) == (f, t, c))
        if not cands:
            raise ValueError(f"stratum {f} {t} {c} has no candidate")
        out.append(rng.choice(cands))
    return out


def order(ids: list[str]) -> list[tuple[str, str]]:
    """The packet order: the drawn ids shuffled with ``random.Random(20261125)``, named ``A01``..``A32``."""
    shuffled = list(ids)
    random.Random(SEED_ORDER).shuffle(shuffled)
    return [(f"A{i:02d}", sid) for i, sid in enumerate(shuffled, start=1)]


def population(manifest_test: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The test targets of the private manifest, as draw records."""
    return [{"scenario_id": e["scenario_id"], "family": e["family"], "tier": e["tier"], "oracle_class": e["gt_class"]}
            for e in manifest_test if e.get("v1_role") == "target"]


# --- the blinded packet (protocol: What the auditor receives) ----------------------------------------------------


def brief(packet_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    t = doc.get("target") or {}
    return {"packet_id": packet_id, "family": doc["family"],
            "target": {"kind": t.get("kind"), "invariant_id": t.get("invariant_id")},
            "endpoints": {"S": doc["endpoints"]["S"], "D": doc["endpoints"]["D"]},
            "variable_values": doc.get("variable_values") or {},
            "steps": [s["step"] for s in sorted(doc["steps"], key=lambda s: s["step"])]}


def _json_keys(obj: Any) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | {k for v in obj.values() for k in _json_keys(v)}
    if isinstance(obj, list):
        return {k for v in obj for k in _json_keys(v)}
    return set()


def check_blinded(packet_root: Path, secrets: list[str]) -> list[str]:
    """Problems in a packet: a brief with other keys, a forbidden key in any file, a ``secrets`` string (the target
    descriptions) in any file, or a label word next to an invariant id."""
    problems = []
    for f in sorted(packet_root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(packet_root).as_posix()
        text = f.read_bytes().decode("utf-8", errors="replace")
        if f.name == "brief.json":
            try:
                b = json.loads(text)
            except json.JSONDecodeError:
                problems.append(f"{rel}: not JSON")
                continue
            if set(b) != BRIEF_KEYS or set(b.get("target") or {}) != TARGET_KEYS \
                    or set(b.get("endpoints") or {}) != ENDPOINT_KEYS:
                problems.append(f"{rel}: keys other than the allowed ones")
            # The structure is exact above. The keys inside variable_values are the configuration's own variable
            # attribute names (a real module may name one "description"), which the protocol gives the auditor;
            # every other part of the brief is scanned for forbidden keys.
            rest = {k: v for k, v in b.items() if k != "variable_values"}
            if _json_keys(rest) & set(FORBIDDEN_KEYS):
                problems.append(f"{rel}: a forbidden key")
        elif _KEY_RE.search(text):
            problems.append(f"{rel}: a forbidden key")
        if any(s and s in text for s in secrets):
            problems.append(f"{rel}: the target description")
        if _NEAR_RE.search(text):
            problems.append(f"{rel}: a label word next to an invariant id")
    return problems


# --- the private directory ---------------------------------------------------------------------------------------


def private_manifest_pin() -> str:
    """The SHA-256 of ``V1_MANIFEST_PRIVATE.json`` recorded in the frozen ``scenarios/V1_MANIFEST.sha256``."""
    for line in V1_SUMS.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if name == PRIVATE_MANIFEST:
            return digest
    raise SystemExit(f"{V1_SUMS.name} records no {PRIVATE_MANIFEST}")


def open_private(private: Path, pin: str) -> list[dict[str, Any]]:
    """The private manifest's test entries, after its SHA-256 is checked against ``pin``."""
    path = private / PRIVATE_MANIFEST
    if not path.is_file():
        raise SystemExit(f"the private manifest {PRIVATE_MANIFEST} is missing")
    raw = path.read_bytes()
    if sha256(raw) != pin:
        raise SystemExit(f"the private manifest's sha256 is not the pin {pin}")
    return json.loads(raw)["test"]


def _checked_doc(private: Path, entry: dict[str, Any]) -> dict[str, Any]:
    """A sampled scenario's record, checked against the private manifest (scenario.json and every step)."""
    sid = entry["scenario_id"]
    text = (private / sid / "scenario.json").read_bytes()
    if sha256(text) != entry["scenario_json_sha256"]:
        raise SystemExit("a sampled scenario.json is not the private manifest's (the id is withheld)")
    doc = json.loads(text)
    if doc.get("split") != "test" or doc.get("v1_role") != "target":
        raise SystemExit("a sampled scenario is not a test-split target (the id is withheld)")
    pinned = {s["step"]: s["content_hash"] for s in entry["steps"]}
    for s in doc["steps"]:
        if pinned.get(s["step"]) != s["content_hash"] or content_hash(private / sid / s["terraform_dir"]) != s["content_hash"]:
            raise SystemExit("a sampled step is not the private manifest's (the id is withheld)")
    return doc


def build(private: Path, pin: str) -> dict[str, Any]:
    """Draw, copy, write and check the packet under ``private/audit/v1``; returns counts and the key's SHA-256."""
    private = Path(private).resolve()
    if private == REPO_ROOT or REPO_ROOT in private.parents:
        raise SystemExit("the private directory must lie outside the repository")
    entries = open_private(private, pin)
    out = private / AUDIT_DIR
    if out.exists():
        raise SystemExit(f"{out} exists: the sample is drawn once (protocol v1)")
    by_id = {e["scenario_id"]: e for e in entries}
    chosen = order(draw(population(entries)))
    docs = {sid: _checked_doc(private, by_id[sid]) for _pid, sid in chosen}
    packet = out / "packet"
    rows = []
    try:
        for pid, sid in chosen:
            doc = docs[sid]
            dst = packet / pid
            dst.mkdir(parents=True)
            for s in sorted(doc["steps"], key=lambda s: s["step"]):
                src = private / sid / s["terraform_dir"]
                for f in sorted(p for p in src.rglob("*") if p.is_file()):
                    target = dst / s["terraform_dir"] / f.relative_to(src)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(f, target)
                if content_hash(dst / s["terraform_dir"]) != s["content_hash"]:
                    raise SystemExit("a copied step does not match its content hash (the id is withheld)")
                rows += [{"packet_id": pid, "step": s["step"], "invariant_id": inv, "label": "", "note": ""}
                         for inv in INVARIANTS]
            (dst / "brief.json").write_text(json.dumps(brief(pid, doc), indent=2, sort_keys=True) + "\n",
                                            encoding="utf-8", newline="\n")
        problems = check_blinded(packet, [(docs[sid].get("target") or {}).get("description") or ""
                                          for _pid, sid in chosen])
        if problems:
            raise SystemExit(f"the packet is not blinded: {len(problems)} problems (detail withheld)")
        with open(out / "audit_labels.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        key = (json.dumps({pid: sid for pid, sid in chosen}, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (out / "key.json").write_bytes(key)
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)  # nothing half-written stays behind
        for parent in (out.parent,):  # audit/, when this run created it and left it empty
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        raise
    return {"packets": len(chosen), "csv_rows": len(rows), "key_sha256": sha256(key), "path": str(out)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", choices=("test",), required=True)
    ap.add_argument("--private", help="the private directory (default $TERRAPRESERVE_PRIVATE)")
    args = ap.parse_args(argv)
    raw = args.private or os.environ.get("TERRAPRESERVE_PRIVATE")
    if not raw or not Path(raw).is_dir():
        raise SystemExit("--split test: the private directory (--private or $TERRAPRESERVE_PRIVATE) does not exist")
    summary = build(Path(raw), private_manifest_pin())
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
