#!/usr/bin/env python3
"""D6-02: select the v1.0 targets and write ``v1_role`` / ``v1_role_reason`` into every ``scenario.json``.

The rule (decided by the user on 11 Nov 2026), deterministic:

1. every scenario marked target (``reserve: false``) with an oracle ``gt_class`` stays a target;
2. a target that is excluded (``excluded_from_v1``, any reason) is replaced by the lowest-numbered labelled
   reserve of the same cell (tier x split x family x class; a reserve's class is its oracle ``gt_class``, an
   excluded target's class is its intent class);
3. if a real-world cell still lacks targets, the lowest-numbered labelled controlled reserve of the same
   family x class x split is taken (D0 Decision 3); it keeps ``source.tier = "controlled"``;
4. no other target changes; a cell that cannot be filled is reported as a shortfall, never padded.

``--write`` writes the fields (dev into ``scenarios/dev``; test only under ``$TERRAPRESERVE_PRIVATE``) and updates
the ``scenario_json_sha256`` of ``scenarios/test_manifest.json``. Without it the outcome is printed (dev ids;
test counts only). Labels, steps and every other field are untouched. Standard library only.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "generator"))

import writer  # noqa: E402  (canonical scenario.json format and its sha256)


def num(sid: str) -> int:
    return int(sid.rsplit("-", 1)[1])


def facts(d: dict, split: str) -> dict[str, Any]:
    """The fields of one scenario.json the rule reads."""
    ex = d.get("excluded_from_v1")
    return {"scenario_id": d["scenario_id"], "split": split, "tier": d["source"]["tier"], "family": d["family"],
            "intent_class": d["intent"]["class"], "reserve": bool(d["reserve"]), "oracle_class": d.get("gt_class"),
            "excluded": (ex.get("kind") or "unplannable") if ex else None}


def select(scs: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Apply D6-02. Returns ({id: {v1_role, v1_role_reason}}, report with ``swaps`` and ``shortfalls``)."""
    roles: dict[str, dict[str, Any]] = {}
    for s in scs:
        if s["excluded"] is not None:
            roles[s["scenario_id"]] = {"v1_role": "excluded", "v1_role_reason": f"excluded_from_v1: {s['excluded']}"}
        else:
            roles[s["scenario_id"]] = {"v1_role": "reserve" if s["reserve"] else "target", "v1_role_reason": None}

    def cell_class(s: dict) -> str:
        return s["oracle_class"] if s["oracle_class"] is not None else s["intent_class"]

    def key(s: dict) -> tuple[str, str, str, str]:
        return (s["tier"], s["split"], s["family"], cell_class(s))

    cells: dict[tuple, list[dict]] = collections.defaultdict(list)
    for s in scs:
        cells[key(s)].append(s)
    free = {k: sorted((s for s in v if s["reserve"] and s["excluded"] is None and s["oracle_class"] is not None),
                      key=lambda s: num(s["scenario_id"])) for k, v in cells.items()}
    report: dict[str, list[dict[str, Any]]] = {"swaps": [], "shortfalls": []}
    for k in sorted(cells, key=lambda k: (k[1], k[2], k[3], k[0] != "controlled", k[0])):
        tier, split, fam, cls = k
        gone = sorted((s for s in cells[k] if not s["reserve"] and s["excluded"] is not None),
                      key=lambda s: num(s["scenario_id"]))
        missing = 0
        for ex in gone:
            step, pool = 2, free[k]
            if not pool and tier == "real_world":
                step, pool = 3, free.get(("controlled", split, fam, cls), [])
            if not pool:
                missing += 1
                roles[ex["scenario_id"]]["v1_role_reason"] += "; not replaced (shortfall)"
                continue
            r = pool.pop(0)
            rid, eid = r["scenario_id"], ex["scenario_id"]
            if step == 2:
                why = f"D6-02 step 2: lowest-numbered labelled reserve of the cell; replaces excluded target {eid}"
            else:
                why = (f"D6-02 step 3: lowest-numbered labelled controlled reserve of {fam} {cls} {split}; fills the "
                       f"real-world cell of excluded target {eid} (counted as controlled)")
            roles[rid] = {"v1_role": "target", "v1_role_reason": why}
            roles[eid]["v1_role_reason"] += f"; replaced by {rid}"
            report["swaps"].append({"excluded": eid, "excluded_reason": ex["excluded"], "replacement": rid,
                                    "from_controlled": step == 3, "split": split, "tier": tier, "family": fam,
                                    "class": cls})
        if missing:
            report["shortfalls"].append({"split": split, "tier": tier, "family": fam, "class": cls, "missing": missing})
    return roles, report


def private_root() -> Path | None:
    p = os.environ.get("TERRAPRESERVE_PRIVATE")
    return Path(p) if p and Path(p).is_dir() else None


def load(splits: list[str]) -> list[tuple[str, Path, dict]]:
    out = []
    roots = [("dev", REPO_ROOT / "scenarios" / "dev")]
    if "test" in splits:
        priv = private_root()
        if priv is None:
            raise SystemExit("TERRAPRESERVE_PRIVATE is not set to an existing directory")
        roots.append(("test", priv))
    for split, root in roots:
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append((split, p, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="dev,test")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.splits != "dev,test":
        raise SystemExit("the rule is applied to both splits together (--splits dev,test)")
    scs = load(args.splits.split(","))
    roles, report = select([facts(d, split) for split, _p, d in scs])
    split_of = {d["scenario_id"]: split for split, _p, d in scs}
    shown = [{k: (v if split_of[s["excluded"]] == "dev" or k not in ("excluded", "replacement") else "(test)")
              for k, v in s.items()} for s in report["swaps"]]
    print("swaps (dev ids, test withheld):")
    for s in shown:
        print("  ", json.dumps(s, sort_keys=True))
    print("shortfalls:", json.dumps(report["shortfalls"]))
    c = collections.Counter((split_of[sid], r["v1_role"]) for sid, r in roles.items())
    print("roles:", dict(sorted(c.items())))
    if not args.write:
        return 0
    updates: dict[str, str] = {}
    for split, p, d in scs:
        d.update(roles[d["scenario_id"]])
        text = writer.canonical_json(d)
        (p / "scenario.json").write_text(text, encoding="utf-8", newline="\n")
        if split == "test":
            updates[d["scenario_id"]] = writer.sha256_text(text)
    mp = REPO_ROOT / "scenarios" / "test_manifest.json"
    man = json.loads(mp.read_text(encoding="utf-8"))
    for e in man:
        e["scenario_json_sha256"] = updates.pop(e["scenario_id"])
    if updates:
        raise SystemExit(f"{len(updates)} test scenarios missing from test_manifest.json")
    mp.write_text(writer.canonical_json(man), encoding="utf-8", newline="\n")
    print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
