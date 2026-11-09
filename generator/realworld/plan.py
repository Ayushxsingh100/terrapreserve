"""Plan builder for real-world tier scenarios (D4b-08, D4b-09).

Builds the 208 real-world benchmark scenarios across 16 cells (8 families x 2 classes):
- 160 targets (112 dev, 48 test: 7 dev + 3 test per cell)
- 48 reserves (32 dev, 16 test: 2 dev + 1 test per cell)
- Slot layout as in D4b-09 (natives first, then hosts in sorted order), then D4b-14 and D4b-15:
  derived natives are out of v1.0, and a module that fails the whole-module S0 screen is replaced by
  an unused, screen-passing host of the same side of the split. A slot with no such host is left
  short and reported, never padded.
- Exactly one base module per scenario (never reused).
Standard library only.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))
import hcl_lex
from realworld import graft, screen

SPLIT_REAL_WORLD = REPO_ROOT / "scenarios" / "split_real_world.json"
POOL_JSON = REPO_ROOT / "pool" / "pool.json"
DERIVED_JSON = REPO_ROOT / "pool" / "derived.json"

FAMILIES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
CLASSES = ["safe", "unsafe"]


def is_eligible_native(mod: dict[str, Any]) -> bool:
    """Precondition check: native module must have an aws_instance with a literal instance_type (D4b-05)."""
    mod_id = mod["module_id"]
    derived = mod.get("derived", False)
    mod_dir = REPO_ROOT / "pool" / "terrads" / ("derived" if derived else "native") / str(mod_id)
    for p in mod_dir.glob("*.tf"):
        text = p.read_text(encoding="utf-8", errors="replace")
        for a in hcl_lex.attributes_from_hcl(text):
            if a.top_level.startswith("aws_instance.") and a.name == "instance_type" and a.value_kind == "literal":
                return True
    return False


def load_pool_modules() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Load hosts, natives, and derived natives from committed pool files."""
    with open(POOL_JSON, encoding="utf-8") as f:
        pool_doc = json.load(f)
    hosts = [e for e in pool_doc["entries"] if e.get("kind") == "host"]
    natives = [e for e in pool_doc["entries"] if e.get("kind") == "native"]

    derived: list[dict[str, Any]] = []
    if DERIVED_JSON.is_file():
        with open(DERIVED_JSON, encoding="utf-8") as f:
            derived = json.load(f)

    return hosts, natives, derived


def load_split() -> tuple[set[str], set[str]]:
    """Load dev and test lineage sets from scenarios/split_real_world.json."""
    data = json.loads(SPLIT_REAL_WORLD.read_text(encoding="utf-8"))
    return set(data["dev_lineages"]), set(data["test_lineages"])


# D4b-14: the derived natives (pool/derived.json, kept for v1.1) are not used in v1.0.
DERIVED_IN_V1_0 = False


def _module_dir(mod: dict[str, Any]) -> Path:
    kind = "derived" if mod.get("derived") else ("host" if mod["kind"] == "host" else "native")
    return REPO_ROOT / "pool" / "terrads" / kind / str(mod["module_id"])


def screen_entry(mod: dict[str, Any]) -> screen.ScreenResult:
    """Whole-module S0 screen of one pool entry (hosts are neutralised exactly as the generator does)."""
    files: dict[str, str] = {}
    for p in sorted(_module_dir(mod).glob("*.tf")):
        text = p.read_text(encoding="utf-8", errors="replace")
        if mod["kind"] == "host":
            text, _log = graft.neutralise_host_file(p.name, text)
        files[p.name] = text
    return screen.screen_module(files, is_native=(mod["kind"] != "host"))


def build_plan_with_report() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build the plan and a report: screen statistics, replacements and shortfalls."""
    hosts, natives, derived = load_pool_modules()
    dev_lins, test_lins = load_split()

    def tag(entries: list[dict[str, Any]], kind: str, is_derived: bool) -> list[dict[str, Any]]:
        out = []
        for e in entries:
            entry = dict(e)
            entry["kind"] = kind
            entry["derived"] = is_derived
            out.append(entry)
        return out

    all_natives = tag(natives, "native", False) + tag(derived, "native", True)
    all_hosts = tag(hosts, "host", False)
    all_natives.sort(key=lambda m: m["module_id"])
    all_hosts.sort(key=lambda m: m["module_id"])

    def side(m: dict[str, Any]) -> str:
        return "dev" if m["lineage_id"] in dev_lins else "test"

    # Pass 1: the layout of D4b-09 (natives first, then hosts in sorted order), exactly as d4b-4.
    pools = {
        "dev": {"native": [m for m in all_natives if m["lineage_id"] in dev_lins and is_eligible_native(m)],
                "host": [m for m in all_hosts if m["lineage_id"] in dev_lins]},
        "test": {"native": [m for m in all_natives if m["lineage_id"] in test_lins and is_eligible_native(m)],
                 "host": [m for m in all_hosts if m["lineage_id"] in test_lins]},
    }
    layout: list[dict[str, Any]] = []
    counter = 209  # continues from the controlled tier (1..208)
    for fam in FAMILIES:
        for cls in CLASSES:
            for split, reserve, n in (("dev", False, 7), ("test", False, 3), ("dev", True, 2), ("test", True, 1)):
                for _ in range(n):
                    pl = pools[split]
                    mod = pl["native"].pop(0) if pl["native"] else pl["host"].pop(0)
                    layout.append({"global_id": counter, "family": fam, "class": cls, "split": split,
                                   "reserve": reserve, "mod": mod})
                    counter += 1
    used_ids = {slot["mod"]["module_id"] for slot in layout}

    # Screen every host of the pool once (statistics) and every module of the layout.
    screen_cache: dict[tuple[bool, int], screen.ScreenResult] = {}

    def screened(m: dict[str, Any]) -> screen.ScreenResult:
        key = (bool(m["derived"]), m["module_id"])
        if key not in screen_cache:
            screen_cache[key] = screen_entry(m)
        return screen_cache[key]

    spare: dict[str, list[dict[str, Any]]] = {"dev": [], "test": []}
    for m in all_hosts:
        if m["module_id"] not in used_ids and screened(m).accepted:
            spare[side(m)].append(m)

    plan: list[dict[str, Any]] = []
    replacements: list[dict[str, Any]] = []
    shortfalls: list[dict[str, Any]] = []
    for slot in layout:
        mod = slot["mod"]
        keep = (not mod["derived"] or DERIVED_IN_V1_0) and screened(mod).accepted
        old = mod
        if not keep:
            reason = "derived native (D4b-14)" if mod["derived"] else screened(mod).primary
            if spare[slot["split"]]:
                mod = spare[slot["split"]].pop(0)
                replacements.append({"scenario_id": f"tp-v1-{slot['family']}-{slot['global_id']:04d}",
                                     "split": slot["split"], "old_module_id": old["module_id"],
                                     "old_kind": "derived native" if old["derived"] else old["kind"],
                                     "reason": reason, "new_module_id": mod["module_id"]})
            else:
                shortfalls.append({"scenario_id": f"tp-v1-{slot['family']}-{slot['global_id']:04d}",
                                   "family": slot["family"], "class": slot["class"], "split": slot["split"],
                                   "reserve": slot["reserve"], "old_module_id": old["module_id"],
                                   "reason": reason})
                continue
        plan.append({
            "global_id": slot["global_id"],
            "scenario_id": f"tp-v1-{slot['family']}-{slot['global_id']:04d}",
            "family": slot["family"],
            "class": slot["class"],
            "split": slot["split"],
            "reserve": slot["reserve"],
            "module_id": mod["module_id"],
            "pool_id": mod["pool_id"],
            "lineage_id": mod["lineage_id"],
            "kind": mod["kind"],
            "derived": mod["derived"],
            "grafted": (mod["kind"] == "host"),
            "module_entry": mod,
        })

    stats: dict[str, dict[str, Any]] = {"dev": {}, "test": {}}
    for split in ("dev", "test"):
        examined = [m for m in all_hosts if side(m) == split]
        primary: dict[str, int] = {}
        anycode: dict[str, int] = {}
        for m in examined:
            r = screened(m)
            primary[r.primary] = primary.get(r.primary, 0) + 1
            for c in r.codes:
                anycode[c] = anycode.get(c, 0) + 1
        stats[split] = {"hosts_examined": len(examined), "accepted": primary.get("accepted", 0),
                        "rejected": len(examined) - primary.get("accepted", 0),
                        "by_primary_code": dict(sorted(primary.items())),
                        "by_any_code": dict(sorted(anycode.items()))}
    report = {"stats": stats, "replacements": replacements, "shortfalls": shortfalls,
              "slots": len(layout), "planned": len(plan)}
    return plan, report


def build_real_world_plan() -> list[dict[str, Any]]:
    """Build the deterministic plan for the real-world scenarios (cells short of clean hosts are omitted)."""
    return build_plan_with_report()[0]
