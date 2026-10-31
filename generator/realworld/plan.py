"""Plan builder for real-world tier scenarios (D4b-08, D4b-09).

Builds the 208 real-world benchmark scenarios across 16 cells (8 families x 2 classes):
- 160 targets (112 dev, 48 test: 7 dev + 3 test per cell)
- 48 reserves (32 dev, 16 test: 2 dev + 1 test per cell)
- Natives and derived natives assigned first, hosts fill remaining slots.
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
import hcl_lex

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


def build_real_world_plan() -> list[dict[str, Any]]:
    """Build the deterministic plan for the 208 real-world scenarios."""
    hosts, natives, derived = load_pool_modules()
    dev_lins, test_lins = load_split()

    # Tag entries with native/derived/host flags
    all_natives = []
    for n in natives:
        entry = dict(n)
        entry["kind"] = "native"
        entry["derived"] = False
        all_natives.append(entry)

    for d in derived:
        entry = dict(d)
        entry["kind"] = "native"
        entry["derived"] = True
        all_natives.append(entry)

    all_hosts = []
    for h in hosts:
        entry = dict(h)
        entry["kind"] = "host"
        entry["derived"] = False
        all_hosts.append(entry)

    # Sort deterministically
    all_natives.sort(key=lambda m: (m["module_id"]))
    all_hosts.sort(key=lambda m: (m["module_id"]))

    dev_native_pool = [m for m in all_natives if m["lineage_id"] in dev_lins and is_eligible_native(m)]
    test_native_pool = [m for m in all_natives if m["lineage_id"] in test_lins and is_eligible_native(m)]
    dev_host_pool = [m for m in all_hosts if m["lineage_id"] in dev_lins]
    test_host_pool = [m for m in all_hosts if m["lineage_id"] in test_lins]

    plan: list[dict[str, Any]] = []
    global_counter = 209  # Continues from D4a controlled tier (1..208)

    for fam in FAMILIES:
        for cls in CLASSES:
            # 1. 10 Targets: 7 dev, 3 test
            # Dev targets
            for _ in range(7):
                if dev_native_pool:
                    mod = dev_native_pool.pop(0)
                else:
                    mod = dev_host_pool.pop(0)

                plan.append({
                    "global_id": global_counter,
                    "scenario_id": f"tp-v1-{fam}-{global_counter:04d}",
                    "family": fam,
                    "class": cls,
                    "split": "dev",
                    "reserve": False,
                    "module_id": mod["module_id"],
                    "pool_id": mod["pool_id"],
                    "lineage_id": mod["lineage_id"],
                    "kind": mod["kind"],
                    "derived": mod["derived"],
                    "grafted": (mod["kind"] == "host"),
                    "module_entry": mod,
                })
                global_counter += 1

            # Test targets
            for _ in range(3):
                if test_native_pool:
                    mod = test_native_pool.pop(0)
                else:
                    mod = test_host_pool.pop(0)

                plan.append({
                    "global_id": global_counter,
                    "scenario_id": f"tp-v1-{fam}-{global_counter:04d}",
                    "family": fam,
                    "class": cls,
                    "split": "test",
                    "reserve": False,
                    "module_id": mod["module_id"],
                    "pool_id": mod["pool_id"],
                    "lineage_id": mod["lineage_id"],
                    "kind": mod["kind"],
                    "derived": mod["derived"],
                    "grafted": (mod["kind"] == "host"),
                    "module_entry": mod,
                })
                global_counter += 1

            # 2. 3 Reserves: 2 dev, 1 test
            # Dev reserves
            for _ in range(2):
                if dev_native_pool:
                    mod = dev_native_pool.pop(0)
                else:
                    mod = dev_host_pool.pop(0)

                plan.append({
                    "global_id": global_counter,
                    "scenario_id": f"tp-v1-{fam}-{global_counter:04d}",
                    "family": fam,
                    "class": cls,
                    "split": "dev",
                    "reserve": True,
                    "module_id": mod["module_id"],
                    "pool_id": mod["pool_id"],
                    "lineage_id": mod["lineage_id"],
                    "kind": mod["kind"],
                    "derived": mod["derived"],
                    "grafted": (mod["kind"] == "host"),
                    "module_entry": mod,
                })
                global_counter += 1

            # Test reserve
            for _ in range(1):
                if test_native_pool:
                    mod = test_native_pool.pop(0)
                else:
                    mod = test_host_pool.pop(0)

                plan.append({
                    "global_id": global_counter,
                    "scenario_id": f"tp-v1-{fam}-{global_counter:04d}",
                    "family": fam,
                    "class": cls,
                    "split": "test",
                    "reserve": True,
                    "module_id": mod["module_id"],
                    "pool_id": mod["pool_id"],
                    "lineage_id": mod["lineage_id"],
                    "kind": mod["kind"],
                    "derived": mod["derived"],
                    "grafted": (mod["kind"] == "host"),
                    "module_entry": mod,
                })
                global_counter += 1

    return plan
