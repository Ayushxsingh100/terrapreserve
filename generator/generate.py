"""Controlled tier scenario generation and validation (D4-01, D4-03..D4-09, Step 5).

Generates the 208 controlled scenarios (8 families x 2 classes x 13 scenarios).
Validates every step of every scenario using the pinned Terraform and provider mirror.
Writes dev scenarios to scenarios/dev/, test scenarios to $TERRAPRESERVE_PRIVATE,
and test manifest to scenarios/test_manifest.json.

Standard library, sources/*, pool/*, generator/* only. No DAIL import (D0 gate 1).
"""

from __future__ import annotations

import csv
import json
import os
import random
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "pool"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import diff_verify as dv
import emitter
import operators
import seed
import templates
import validate
import writer
from VERSION import VERSION

DATASET_VERSION = "1.0"
FAMILIES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
CLASSES = ["safe", "unsafe"]
TARGETS_PER_CELL = 10
RESERVES_PER_CELL = 3
TOTAL_PER_CELL = TARGETS_PER_CELL + RESERVES_PER_CELL  # 13
TOTAL_SCENARIOS = len(FAMILIES) * len(CLASSES) * TOTAL_PER_CELL  # 208

PROTECTED_INVARIANTS = [
    {"invariant_id": "INV-SEC-001", "version": "1.0"},
    {"invariant_id": "INV-SEC-002", "version": "1.0"},
    {"invariant_id": "INV-SEC-003", "version": "1.0"},
    {"invariant_id": "INV-FUNC-001", "version": "1.0"},
]

REPAIR_TARGET_DESCRIPTIONS = {
    "INV-SEC-001": "Repair public SSH ingress on port 22",
    "INV-SEC-002": "Repair public database ingress on port 5432",
    "INV-SEC-003": "Repair publicly accessible database instance",
}


def get_private_dir() -> Path:
    env_dir = os.environ.get("TERRAPRESERVE_PRIVATE")
    if env_dir:
        p = Path(env_dir)
    else:
        p = Path.home() / ".terrapreserve-private"
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_scenario_plan() -> list[dict[str, Any]]:
    """Build the deterministic generation plan for all 208 scenarios in stable order."""
    split_info = json.loads((REPO_ROOT / "scenarios" / "split.json").read_text(encoding="utf-8"))
    dev_templates = set(split_info["dev_templates"])
    test_templates = set(split_info["test_templates"])

    all_tpl_ids = sorted(templates.TEMPLATES.keys())
    shuffled_tpl_ids = seed.template_shuffle_order(all_tpl_ids)
    dev_tpl_list = [t for t in shuffled_tpl_ids if t in dev_templates]
    test_tpl_list = [t for t in shuffled_tpl_ids if t in test_templates]

    plan = []
    global_counter = 1
    cell_num = 0

    for family in FAMILIES:
        for cls in CLASSES:
            # 10 target scenarios: one per template tpl-01..tpl-10
            for tpl_idx, tpl_id in enumerate(all_tpl_ids):
                plan.append({
                    "global_id": global_counter,
                    "family": family,
                    "cls": cls,
                    "reserve": False,
                    "template_id": tpl_id,
                    "cell_index": tpl_idx,
                    "split": "dev" if tpl_id in dev_templates else "test",
                })
                global_counter += 1

            # 3 reserve scenarios rotating across all 10 templates (2 dev, 1 test per cell)
            dev_res_0 = dev_tpl_list[(cell_num * 2) % len(dev_tpl_list)]
            dev_res_1 = dev_tpl_list[(cell_num * 2 + 1) % len(dev_tpl_list)]
            test_res_2 = test_tpl_list[cell_num % len(test_tpl_list)]
            cell_res_tpls = [dev_res_0, dev_res_1, test_res_2]

            for res_idx, tpl_id in enumerate(cell_res_tpls):
                plan.append({
                    "global_id": global_counter,
                    "family": family,
                    "cls": cls,
                    "reserve": True,
                    "template_id": tpl_id,
                    "cell_index": TARGETS_PER_CELL + res_idx,
                    "split": "dev" if tpl_id in dev_templates else "test",
                })
                global_counter += 1

            cell_num += 1

    return plan


def generate_scenario(
    item: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]], list[list[dv.MutationRow]]]:
    """Generate scenario descriptor, step files, and mutation records."""
    global_id = item["global_id"]
    family = item["family"]
    cls = item["cls"]
    reserve = item["reserve"]
    tpl_id = item["template_id"]
    split = item["split"]
    cell_idx = item["cell_index"]

    scenario_id = f"tp-v1-{family}-{global_id:04d}"
    rng = seed.scenario_rng(global_id)

    tpl = templates.TEMPLATES[tpl_id]

    # Select operator
    candidate_ops = [op for op in operators.CATALOGUE if op.family == family and op.variant == cls]
    if not candidate_ops:
        raise ValueError(f"No operator found for {family} {cls}")
    op = candidate_ops[cell_idx % len(candidate_ops)]

    # Determine target & S0 variant
    if op.target_kind == "repair":
        target_inv = op.target_invariant or (["INV-SEC-001", "INV-SEC-002", "INV-SEC-003"][cell_idx % 3])
        if target_inv == "INV-SEC-001":
            s0_var = "sec_001_violated"
        elif target_inv == "INV-SEC-002":
            s0_var = "sec_002_violated"
        else:
            s0_var = "sec_003_violated"

        target_info = {
            "kind": "repair",
            "invariant_id": target_inv,
            "description": REPAIR_TARGET_DESCRIPTIONS.get(target_inv, f"Repair {target_inv}"),
        }
    else:
        s0_var = "clean"
        target_info = {
            "kind": "change_request",
            "invariant_id": None,
            "description": op.description,
        }

    # Instantiate base model S0
    m0, param_meta = tpl.instantiate(rng, variant=s0_var)

    # Apply operator to produce steps S1..Sk
    step_models, mutation_records = op.apply(m0, rng)

    # All models: [m0, m1, ...]
    all_models = [m0] + step_models

    # Verify mutation records with diff_verify
    for step_num, (prev_m, curr_m, rec) in enumerate(
        zip(all_models[:-1], all_models[1:], mutation_records, strict=True), start=1
    ):
        dv.verify(prev_m, curr_m, rec, step=step_num, operator_name=op.name)

    # Emit step files
    variables_tf = emitter.emit_db_password_variable()
    versions_tf = emitter.emit_versions()

    steps_files: list[dict[str, str]] = []
    steps_meta: list[dict[str, Any]] = []

    prev_files: dict[str, str] | None = None
    for step_idx, model in enumerate(all_models):
        main_tf = emitter.emit(model)
        files = {
            "main.tf": main_tf,
            "variables.tf": variables_tf,
            "versions.tf": versions_tf,
        }
        steps_files.append(files)

        content_hash = writer.compute_step_content_hash(files)
        diff_from_prev = None
        if step_idx > 0:
            assert prev_files is not None
            diff_from_prev = writer.compute_step_diff(prev_files, files)

        steps_meta.append({
            "step": step_idx,
            "terraform_dir": f"step_{step_idx}",
            "content_hash": content_hash,
            "diff_from_previous": diff_from_prev,
        })
        prev_files = files

    # Flatten mutation records for manifest
    flat_records = []
    for rec_list in mutation_records:
        for r in rec_list:
            flat_records.append({
                "step": r.step,
                "operator": r.operator,
                "target_address": r.target_address,
                "attribute": r.attribute,
                "before": r.before,
                "after": r.after,
            })

    scenario_data = {
        "scenario_id": scenario_id,
        "dataset_version": DATASET_VERSION,
        "generator_version": VERSION,
        "family": family,
        "split": split,
        "gt_class": None,
        "intent": {
            "class": cls,
            "target_kind": op.target_kind,
            "target_invariant": op.target_invariant,
            "breaks": op.intent_breaks,
            "preserves": op.intent_preserves,
        },
        "reserve": reserve,
        "template_id": tpl_id,
        "template_version": tpl.version,
        "seed": global_id,
        "parameters": param_meta,
        "derived": False,
        "grafted": False,
        "source": {
            "tier": "controlled",
            "origin": "terragoat",
            "repo_lineage_id": tpl_id,
            "commit_or_version": f"{VERSION}+{tpl.version}",
            "license": "CC-BY-4.0",
            "grafted": False,
        },
        "target": target_info,
        "protected_invariants": PROTECTED_INVARIANTS,
        "steps": steps_meta,
        "mutation_record": flat_records,
        "labels": None,
        "oracle": None,
    }

    return scenario_data, steps_files, mutation_records


def run_pipeline(resume: bool = True) -> dict[str, Any]:
    plan = build_scenario_plan()
    private_root = get_private_dir()
    dev_root = REPO_ROOT / "scenarios" / "dev"

    valid_hash_cache: dict[str, tuple[str, str]] = {}
    if resume:
        # Load known valid hashes from dev directory and CSV
        dev_csv = REPO_ROOT / "scenarios" / "validate_results.csv"
        if dev_csv.is_file() and dev_root.is_dir():
            csv_lookup: dict[tuple[str, int], tuple[str, str]] = {}
            with open(dev_csv, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    csv_lookup[(r["scenario_id"], int(r["step"]))] = (r["status"], r.get("error_class", ""))
            for sc_dir in dev_root.glob("tp-v1-*"):
                sc_json = sc_dir / "scenario.json"
                if sc_json.is_file():
                    try:
                        d = json.loads(sc_json.read_text(encoding="utf-8"))
                        sc_id = d.get("scenario_id", "")
                        for st in d.get("steps", []):
                            st_num = st.get("step")
                            chash = st.get("content_hash")
                            if chash and csv_lookup.get((sc_id, st_num)) == ("valid", ""):
                                valid_hash_cache[chash] = ("valid", "")
                    except Exception:
                        pass
        # Load from private directory if available
        test_csv = private_root / "validate_results.csv"
        if test_csv.is_file() and private_root.is_dir():
            csv_lookup_test: dict[tuple[str, int], tuple[str, str]] = {}
            with open(test_csv, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    csv_lookup_test[(r["scenario_id"], int(r["step"]))] = (r["status"], r.get("error_class", ""))
            for sc_dir in private_root.glob("tp-v1-*"):
                sc_json = sc_dir / "scenario.json"
                if sc_json.is_file():
                    try:
                        d = json.loads(sc_json.read_text(encoding="utf-8"))
                        sc_id = d.get("scenario_id", "")
                        for st in d.get("steps", []):
                            st_num = st.get("step")
                            chash = st.get("content_hash")
                            if chash and csv_lookup_test.get((sc_id, st_num)) == ("valid", ""):
                                valid_hash_cache[chash] = ("valid", "")
                    except Exception:
                        pass

    # Clean existing dev directory
    if dev_root.is_dir():
        for item in dev_root.glob("tp-v1-*"):
            if item.is_dir():
                shutil.rmtree(item)

    test_manifest_entries = []
    dev_validation_rows = []
    test_validation_rows = []

    harness = validate.Harness.default()

    counts = {
        "total": len(plan),
        "dev": 0,
        "test": 0,
        "reserves": 0,
        "targets": 0,
        "by_family": {},
        "valid_steps": 0,
        "invalid_steps": 0,
        "error_steps": 0,
    }

    for item in plan:
        sc_data, steps_files, _ = generate_scenario(item)
        sc_id = sc_data["scenario_id"]
        split = sc_data["split"]

        if split == "dev":
            counts["dev"] += 1
            writer.write_dev_scenario(dev_root, sc_data, steps_files)
        else:
            counts["test"] += 1
            test_entry = writer.write_test_scenario(private_root, sc_data, steps_files)
            test_manifest_entries.append(test_entry)

        if sc_data["reserve"]:
            counts["reserves"] += 1
        else:
            counts["targets"] += 1

        fam = sc_data["family"]
        counts["by_family"].setdefault(fam, {"safe": 0, "unsafe": 0})
        counts["by_family"][fam][sc_data["intent"]["class"]] += 1

        # Validate every step
        for step_idx, files in enumerate(steps_files):
            chash = sc_data["steps"][step_idx]["content_hash"]
            if resume and chash in valid_hash_cache:
                status, error_class = valid_hash_cache[chash]
            else:
                res = harness.validate(files)
                retries = 0
                while res.status == "error" and retries < 3:
                    retries += 1
                    import time
                    time.sleep(0.5)
                    res = harness.validate(files)
                status = res.status
                error_class = res.error_class
                if status == "valid":
                    valid_hash_cache[chash] = ("valid", "")

            if status == "valid":
                counts["valid_steps"] += 1
            elif status == "invalid":
                counts["invalid_steps"] += 1
            else:
                counts["error_steps"] += 1

            row = {
                "scenario_id": sc_id,
                "step": step_idx,
                "status": status,
                "error_class": error_class,
            }
            if split == "dev":
                dev_validation_rows.append(row)
            else:
                test_validation_rows.append(row)

    # Write scenarios/test_manifest.json
    manifest_path = REPO_ROOT / "scenarios" / "test_manifest.json"
    manifest_path.write_text(writer.canonical_json(test_manifest_entries), encoding="utf-8", newline="\n")

    # Write dev validate_results.csv
    dev_csv_path = REPO_ROOT / "scenarios" / "validate_results.csv"
    with open(dev_csv_path, "w", newline="\n", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "step", "status", "error_class"])
        w.writeheader()
        w.writerows(dev_validation_rows)

    # Write test validate_results.csv in private dir
    test_csv_path = private_root / "validate_results.csv"
    with open(test_csv_path, "w", newline="\n", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "step", "status", "error_class"])
        w.writeheader()
        w.writerows(test_validation_rows)

    return counts


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run controlled tier generator and validation harness.")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume from cached validation results")
    args = parser.parse_args()
    print("Running controlled tier generator and validation harness...")
    summary = run_pipeline(resume=not args.no_resume)
    print("Summary:")
    print(json.dumps(summary, indent=2))
    print("Summary:")
    print(json.dumps(summary, indent=2))

