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
import varvalues
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


# Per cell (D4-04 counts, kept by D4c-04): targets and reserves by split.
DEV_TARGETS, TEST_TARGETS, DEV_RESERVES, TEST_RESERVES = 7, 3, 2, 1
# The D4a side of each position in a cell (targets 0-9 were tpl-01..tpl-10, of which tpl-04, tpl-05 and tpl-07 were
# test; reserves 10-12 were dev, dev, test). D4c keeps it, so no scenario id changes side.
CELL_SIDES = ("dev", "dev", "dev", "test", "test", "dev", "test", "dev", "dev", "dev", "dev", "dev", "test")
D4C_NEW_TEMPLATES = [f"tpl-{i}" for i in range(11, 34)]
D4C_NEW_TEST = 7  # D4c-01: 7 of the 23 new templates join the test side


def d4c_draw() -> dict[str, Any]:
    """D4c-01: the new templates in ``seed.template_shuffle_order`` (master seed); the last 7 are test."""
    order = seed.template_shuffle_order(sorted(D4C_NEW_TEMPLATES))
    return {"order": order, "dev": sorted(order[:-D4C_NEW_TEST]), "test": sorted(order[-D4C_NEW_TEST:])}


def serving(tpl_id: str, family: str, cls: str) -> list[str]:
    """D4c-04: the operators of one family x class cell the template accepts (OperatorNotApplicable excluded)."""
    tpl = templates.TEMPLATES[tpl_id]
    out = []
    for op in operators.CATALOGUE:
        if op.family != family or op.variant != cls:
            continue
        variant = "clean"
        if op.target_kind == "repair":
            variant = {"INV-SEC-001": "sec_001_violated", "INV-SEC-002": "sec_002_violated",
                       "INV-SEC-003": "sec_003_violated"}[op.target_invariant]
        m0, _ = tpl.instantiate(seed.scenario_rng(0), variant=variant)
        try:
            op.apply(m0, seed.scenario_rng(0))
        except operators.OperatorNotApplicable:
            continue
        out.append(op.name)
    return out


def build_scenario_plan() -> list[dict[str, Any]]:
    """Build the deterministic generation plan for all 208 scenarios in stable order (D4c-04).

    Each split's templates are put in ``seed.template_shuffle_order`` (master seed) and walked cyclically
    across the 16 cells in family x class order: a cell takes the next 9 dev templates (7 targets, then 2
    reserves) and the next 4 test templates (3 targets, then 1 reserve) that serve it, each at most once per
    cell. Ids follow D4-09 (family, class, targets, then reserves) and keep the D4a side of each position in a
    cell (``CELL_SIDES``), so no scenario id changes side; within each side, templates are in template-id order."""
    split_info = json.loads((REPO_ROOT / "scenarios" / "split.json").read_text(encoding="utf-8"))
    dev_order = seed.template_shuffle_order(sorted(split_info["dev_templates"]))
    test_order = seed.template_shuffle_order(sorted(split_info["test_templates"]))
    pos = {"dev": 0, "test": 0}

    def take(split: str, order: list[str], n: int, family: str, cls: str) -> list[str]:
        got: list[str] = []
        tried = 0
        while len(got) < n:
            if tried >= len(order):
                raise ValueError(f"not enough {split} templates serve {family} {cls}")
            t = order[pos[split] % len(order)]
            pos[split] += 1
            tried += 1
            if t not in got and serving(t, family, cls):
                got.append(t)
        return got

    plan = []
    global_counter = 1
    for family in FAMILIES:
        for cls in CLASSES:
            dev = take("dev", dev_order, DEV_TARGETS + DEV_RESERVES, family, cls)
            test = take("test", test_order, TEST_TARGETS + TEST_RESERVES, family, cls)
            # Every id keeps the side it had in D4a (D4-03: "a scenario never changes side"): the cell's dev and
            # test templates, each sorted by template id, fill the dev and test positions of the D4a layout.
            dev_sorted = iter(sorted(dev[:DEV_TARGETS]) + sorted(dev[DEV_TARGETS:]))
            test_sorted = iter(sorted(test[:TEST_TARGETS]) + sorted(test[TEST_TARGETS:]))
            slots = [((next(dev_sorted) if side == "dev" else next(test_sorted)), side)
                     for side in CELL_SIDES]
            for idx, ((tpl_id, split), reserve) in enumerate(
                    (x, i >= TARGETS_PER_CELL) for i, x in enumerate(slots)):
                plan.append({
                    "global_id": global_counter,
                    "family": family,
                    "cls": cls,
                    "reserve": reserve,
                    "template_id": tpl_id,
                    "cell_index": idx,
                    "split": split,
                })
                global_counter += 1
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

    # Select operator (deterministically finding first applicable)
    candidate_ops = [op for op in operators.CATALOGUE if op.family == family and op.variant == cls]
    if not candidate_ops:
        raise ValueError(f"No operator found for {family} {cls}")

    start_offset = cell_idx % len(candidate_ops)
    chosen_op = None
    chosen_m0 = None
    chosen_param_meta = None
    chosen_target_info = None
    chosen_step_models = None
    chosen_mutation_records = None

    for offset in range(len(candidate_ops)):
        cand_op = candidate_ops[(start_offset + offset) % len(candidate_ops)]
        if cand_op.target_kind == "repair":
            target_inv = cand_op.target_invariant or (["INV-SEC-001", "INV-SEC-002", "INV-SEC-003"][cell_idx % 3])
            if target_inv == "INV-SEC-001":
                s0_var = "sec_001_violated"
            elif target_inv == "INV-SEC-002":
                s0_var = "sec_002_violated"
            else:
                s0_var = "sec_003_violated"

            t_info = {
                "kind": "repair",
                "invariant_id": target_inv,
                "description": REPAIR_TARGET_DESCRIPTIONS.get(target_inv, f"Repair {target_inv}"),
            }
        else:
            s0_var = "clean"
            t_info = {
                "kind": "change_request",
                "invariant_id": None,
                "description": cand_op.description,
            }

        rng_copy = seed.scenario_rng(global_id)
        m0_candidate, param_meta_candidate = tpl.instantiate(rng_copy, variant=s0_var)

        try:
            step_models, mut_recs = cand_op.apply(m0_candidate, rng_copy)
            chosen_op = cand_op
            chosen_m0 = m0_candidate
            chosen_param_meta = param_meta_candidate
            chosen_target_info = t_info
            chosen_step_models = step_models
            chosen_mutation_records = mut_recs
            break
        except operators.OperatorNotApplicable:
            continue

    if chosen_op is None:
        raise ValueError(f"No applicable operator for {family} {cls} on template {tpl_id}")

    op = chosen_op
    m0 = chosen_m0
    param_meta = chosen_param_meta
    target_info = chosen_target_info
    step_models = chosen_step_models
    mutation_records = chosen_mutation_records

    # All models: [m0, m1, ...]
    all_models = [m0] + step_models

    # Verify mutation records with diff_verify
    for step_num, (prev_m, curr_m, rec) in enumerate(
        zip(all_models[:-1], all_models[1:], mutation_records, strict=True), start=1
    ):
        dv.verify(prev_m, curr_m, rec, step=step_num, operator_name=op.name)

    # Emit step files (the template decides the file layout and value style, D4c-03 axes 5 and 6)
    steps_files: list[dict[str, str]] = []
    steps_meta: list[dict[str, Any]] = []

    prev_files: dict[str, str] | None = None
    for step_idx, model in enumerate(all_models):
        files = tpl.emit_step_files(model)
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

    # D5-10: variable values (rule vv-3), a primary and an alternate set for the whole scenario, from the
    # recorded vv-3 search result; steps are not changed. D5-09: excluded_from_v1 comes from the same result.
    vv_record = varvalues.compute(steps_files, varvalues.search_record(scenario_id, split))

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
        # D5-12: registry 6.1 endpoint binding, from what the template built (never inferred by the oracle).
        "endpoints": tpl.endpoints(),
        "protected_invariants": PROTECTED_INVARIANTS,
        "steps": steps_meta,
        "mutation_record": flat_records,
        **vv_record,
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

    # Clean existing controlled dev scenarios (id <= 208)
    if dev_root.is_dir():
        for item in dev_root.glob("tp-v1-*"):
            if item.is_dir():
                try:
                    num = int(item.name.split("-")[-1])
                    if num <= 208:
                        shutil.rmtree(item)
                except ValueError:
                    pass
    # D4c: the controlled test split is rewritten too (a scenario id may change side or step count).
    for item in private_root.glob("tp-v1-*"):
        if item.is_dir():
            try:
                if int(item.name.split("-")[-1]) <= 208:
                    shutil.rmtree(item)
            except ValueError:
                pass

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

    generated = [generate_scenario(item)[:2] for item in plan]

    # D4c: validate every distinct step content not already known valid, in parallel; each worker has its own
    # harness directory (same Terraform, provider mirror and pins as Harness.default()). Results are identical
    # to validating step by step; only the order of the work changes.
    validated: dict[str, tuple[str, str]] = {}
    todo: dict[str, dict[str, str]] = {}
    for sc_data, steps_files in generated:
        for step_idx, files in enumerate(steps_files):
            chash = sc_data["steps"][step_idx]["content_hash"]
            if not (resume and chash in valid_hash_cache):
                todo.setdefault(chash, files)
    if todo:
        import concurrent.futures as cf
        import threading
        import time

        n_workers = max(1, int(os.environ.get("TP_VALIDATE_WORKERS", "6")))
        base = harness.work.parent / "d4c-tfv"
        pool = [validate.Harness(base / f"w{i}", harness.terraform, Path(harness.env["TF_CLI_CONFIG_FILE"]))
                for i in range(n_workers)]
        free = list(pool)
        lock = threading.Lock()
        print(f"steps to validate: {len(todo)} ({n_workers} workers)", flush=True)

        def one(item: tuple[str, dict[str, str]]) -> tuple[str, tuple[str, str]]:
            chash, files = item
            with lock:
                h = free.pop()
            try:
                res = h.validate(files)
                retries = 0
                while res.status == "error" and retries < 3:
                    retries += 1
                    time.sleep(0.5)
                    res = h.validate(files)
                return chash, (res.status, res.error_class)
            finally:
                with lock:
                    free.append(h)

        for h in pool:  # initialise one at a time (provider from the local mirror)
            h.ensure_ready()
        done = 0
        with cf.ThreadPoolExecutor(max_workers=n_workers) as ex:
            for chash, result in ex.map(one, sorted(todo.items())):
                validated[chash] = result
                done += 1
                if done % 50 == 0:
                    print(f"{done}/{len(todo)} validated", flush=True)

    for sc_data, steps_files in generated:
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
                status, error_class = validated[chash]

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

    # Write scenarios/test_manifest.json (preserving real-world test entries if present)
    manifest_path = REPO_ROOT / "scenarios" / "test_manifest.json"
    rw_test_entries = []
    if manifest_path.is_file():
        # The manifest is a JSON list (writer.canonical_json of the entries). Before D4c this read
        # ``.get("scenarios")`` inside a bare ``except``, which drops the real-world entries when only the
        # controlled tier is regenerated; any read error now stops the run instead.
        existing_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = existing_doc if isinstance(existing_doc, list) else existing_doc.get("scenarios", [])
        rw_test_entries = [e for e in entries if int(e["scenario_id"].split("-")[-1]) > 208]
    all_test_entries = test_manifest_entries + rw_test_entries
    manifest_path.write_text(writer.canonical_json(all_test_entries), encoding="utf-8", newline="\n")

    # Write dev validate_results.csv (preserving real-world rows)
    dev_csv_path = REPO_ROOT / "scenarios" / "validate_results.csv"
    existing_rw_dev = []
    if dev_csv_path.is_file():
        with open(dev_csv_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if int(r["scenario_id"].split("-")[-1]) > 208:
                    existing_rw_dev.append(r)
    with open(dev_csv_path, "w", newline="\n", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "step", "status", "error_class"])
        w.writeheader()
        w.writerows(dev_validation_rows + existing_rw_dev)

    # Write test validate_results.csv in private dir (preserving real-world rows)
    test_csv_path = private_root / "validate_results.csv"
    existing_rw_test = []
    if test_csv_path.is_file():
        with open(test_csv_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if int(r["scenario_id"].split("-")[-1]) > 208:
                    existing_rw_test.append(r)
    with open(test_csv_path, "w", newline="\n", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "step", "status", "error_class"])
        w.writeheader()
        w.writerows(test_validation_rows + existing_rw_test)

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

