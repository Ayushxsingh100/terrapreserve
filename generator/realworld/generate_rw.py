"""Real-world tier generation and validation pipeline (D4b-03..D4b-10, Step 5).

Generates the 208 real-world scenarios:
- 160 target scenarios (112 dev, 48 test)
- 48 reserve scenarios (32 dev, 16 test)
- All steps validated with pinned Terraform 1.15.8 and AWS provider 6.53.0.
- Dev scenarios committed under scenarios/dev/; test scenarios withheld in $TERRAPRESERVE_PRIVATE.
- Provenance files copied to PROVENANCE/ adjacent to steps.
Standard library only.
"""

from __future__ import annotations

import csv
import difflib
import json
import os
import random
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "pool"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import diff_verify as dv
import emitter
import hcl_lex
import operators
import seed
import validate
import writer
from realworld import graft, plan as rw_plan, real_diff_verify, screen, span_edit

DATASET_VERSION = "1.0"
GENERATOR_VERSION = "d4b-1"

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

VERSIONS_TF = """terraform {
  required_version = "1.15.8"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.53.0"
    }
  }
}
"""


def get_private_dir() -> Path:
    env_dir = os.environ.get("TERRAPRESERVE_PRIVATE")
    if env_dir:
        p = Path(env_dir)
    else:
        p = Path.home() / ".terrapreserve-private"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _next_instance_type(old_size: str) -> str:
    cycle = {
        "t3.nano": "t3.micro",
        "t3.micro": "t3.small",
        "t3.small": "t3.medium",
        "t3.medium": "t3.large",
        "t3.large": "t3.xlarge",
        "t2.nano": "t2.micro",
        "t2.micro": "t2.small",
        "t2.small": "t2.medium",
        "t2.medium": "t2.large",
    }
    return cycle.get(old_size, "t3.large" if old_size != "t3.large" else "t3.xlarge")


def generate_real_world_scenario(
    plan_item: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]], list[list[Any]]]:
    """Generate a single real-world scenario (host or native)."""
    global_id = plan_item["global_id"]
    scenario_id = plan_item["scenario_id"]
    family = plan_item["family"]
    cls = plan_item["class"]
    split = plan_item["split"]
    reserve = plan_item["reserve"]
    kind = plan_item["kind"]
    derived = plan_item["derived"]
    module_id = plan_item["module_id"]
    pool_id = plan_item["pool_id"]
    mod_entry = plan_item["module_entry"]

    rng = seed.scenario_rng(global_id)

    # 1. Host module scenario (grafted)
    if kind == "host":
        mod_dir = REPO_ROOT / "pool" / "terrads" / "host" / str(module_id)
        raw_files: dict[str, str] = {}
        for p in sorted(mod_dir.glob("*.tf")):
            raw_files[p.name] = p.read_text(encoding="utf-8", errors="replace")

        # Neutralise host files (strip provider/terraform blocks)
        neutralised_files: dict[str, str] = {}
        transform_records: list[dict[str, Any]] = []
        for fname, content in sorted(raw_files.items()):
            ntext, tlog = graft.neutralise_host_file(fname, content)
            neutralised_files[fname] = ntext
            if tlog["removed_blocks"]:
                transform_records.append(tlog)

        # Validate no clash between host and graft
        graft.validate_no_clash(neutralised_files, seed=global_id)

        # Select D4a operator
        cell_ops = [op for op in operators.CATALOGUE if op.family == family and op.variant == cls]
        assert cell_ops, f"No operators found for cell ({family}, {cls})"
        op = cell_ops[global_id % len(cell_ops)]

        # S0 graft variant
        s0_variant = "clean"
        if op.target_invariant == "INV-SEC-001":
            s0_variant = "sec_001_violated"
        elif op.target_invariant == "INV-SEC-002":
            s0_variant = "sec_002_violated"
        elif op.target_invariant == "INV-SEC-003":
            s0_variant = "sec_003_violated"

        graft_m0 = graft.build_graft_model(seed=global_id, variant=s0_variant)
        graft_files0 = graft.build_graft_files(seed=global_id, variant=s0_variant)

        # Build S0 files
        s0_files = dict(neutralised_files)
        s0_files["terrapreserve_versions.tf"] = VERSIONS_TF
        s0_files["terrapreserve_graft.tf"] = graft_files0["terrapreserve_graft.tf"]
        s0_files["terrapreserve_graft_variables.tf"] = graft_files0["terrapreserve_graft_variables.tf"]

        # Apply operator to graft model
        models, mutation_records = op.apply(graft_m0.copy(), rng)
        all_models = [graft_m0] + models

        # Build step directories
        steps_files: list[dict[str, str]] = []
        steps_meta: list[dict[str, Any]] = []
        prev_files = None
        prev_model = graft_m0

        for step_idx, step_m in enumerate(all_models):
            if step_idx == 0:
                cur_files = dict(s0_files)
            else:
                cur_files = dict(s0_files)
                cur_files["terrapreserve_graft.tf"] = emitter.emit(step_m)
                # Verify mutation record against AST diff on graft model
                step_recs = mutation_records[step_idx - 1]
                dv.verify(prev_model, step_m, step_recs, step=step_idx, operator_name=op.name)
                prev_model = step_m

            steps_files.append(cur_files)

            chash = writer.compute_step_content_hash(cur_files)
            diff_from_prev = None
            if step_idx > 0:
                assert prev_files is not None
                diff_from_prev = writer.compute_step_diff(prev_files, cur_files)

            steps_meta.append({
                "step": step_idx,
                "terraform_dir": f"step_{step_idx}",
                "content_hash": chash,
                "diff_from_previous": diff_from_prev,
            })
            prev_files = cur_files

        scope_addresses = sorted(
            r.type + "." + r.name for r in graft_m0.resources.values()
        )
        s0_screen_status = "eligible (graft core synthesized clean except target)"
        target_info = {
            "kind": op.target_kind,
            "invariant_id": op.target_invariant,
            "description": REPAIR_TARGET_DESCRIPTIONS.get(op.target_invariant, op.description),
        }

    # 2. Native module scenario (un-grafted)
    else:
        if derived:
            mod_dir = REPO_ROOT / "pool" / "terrads" / "derived" / str(module_id)
        else:
            mod_dir = REPO_ROOT / "pool" / "terrads" / "native" / str(module_id)

        raw_files = {}
        for p in sorted(mod_dir.glob("*.tf")):
            raw_files[p.name] = p.read_text(encoding="utf-8", errors="replace")

        s0_files = dict(raw_files)
        s0_files["terrapreserve_versions.tf"] = VERSIONS_TF
        transform_records = []

        # Find in-scope resources
        instance_addrs: list[str] = []
        db_addrs: list[str] = []
        sg_addrs: list[str] = []
        for text in s0_files.values():
            h = hcl_lex.headers_from_hcl(text)
            for rtype, rname in h.managed:
                addr = f"{rtype}.{rname}"
                if rtype == "aws_instance":
                    instance_addrs.append(addr)
                elif rtype == "aws_db_instance":
                    db_addrs.append(addr)
                elif rtype in ("aws_security_group", "aws_security_group_rule"):
                    sg_addrs.append(addr)

        scope_addresses = sorted(set(instance_addrs + db_addrs + sg_addrs))
        ec2_addr = instance_addrs[0] if instance_addrs else "aws_instance.app"
        db_addr = db_addrs[0] if db_addrs else "aws_db_instance.db"

        # Apply span edit operator (e.g. F1 instance_type resize)
        # Find current instance_type in files
        inst_fname = ""
        old_size = "t3.micro"
        for fn, ftext in s0_files.items():
            for a in hcl_lex.attributes_from_hcl(ftext):
                if a.top_level == ec2_addr and a.name == "instance_type":
                    inst_fname = fn
                    lines = ftext.splitlines()[a.line - 1 : a.end_line]
                    if lines and '"' in lines[0]:
                        old_size = lines[0].split('"')[1]
                    break
            if inst_fname:
                break

        if not inst_fname:
            inst_fname = next(iter(s0_files))

        new_size = _next_instance_type(old_size)

        step1_files = dict(s0_files)
        step_records: list[dict[str, Any]] = []

        res = span_edit.apply_span_edit(
            step1_files[inst_fname],
            target_address=ec2_addr,
            target_attribute="instance_type",
            new_value=f'"{new_size}"',
        )
        if res.success:
            step1_files[inst_fname] = res.new_content
            step_records.append({
                "step": 1,
                "operator": f"op_native_{family.lower()}_{cls}",
                "target_address": ec2_addr,
                "attribute": "instance_type",
                "before": f'"{old_size}"',
                "after": f'"{new_size}"',
            })

        if cls == "unsafe" and db_addrs:
            # Side effect: set publicly_accessible = true on RDS
            for db_fn, db_text in step1_files.items():
                if "aws_db_instance" in db_text:
                    db_res = span_edit.apply_span_edit(
                        db_text,
                        target_address=db_addr,
                        target_attribute="publicly_accessible",
                        new_value="true",
                    )
                    if db_res.success:
                        step1_files[db_fn] = db_res.new_content
                        step_records.append({
                            "step": 1,
                            "operator": f"op_native_{family.lower()}_{cls}",
                            "target_address": db_addr,
                            "attribute": "publicly_accessible",
                            "before": "false",
                            "after": "true",
                        })
                        break

        # Verify real text
        real_diff_verify.verify(s0_files, step1_files, step_records)

        steps_files = [s0_files, step1_files]
        steps_meta = []
        for sidx, sfiles in enumerate(steps_files):
            chash = writer.compute_step_content_hash(sfiles)
            diff_p = None
            if sidx > 0:
                diff_p = writer.compute_step_diff(steps_files[sidx - 1], sfiles)
            steps_meta.append({
                "step": sidx,
                "terraform_dir": f"step_{sidx}",
                "content_hash": chash,
                "diff_from_previous": diff_p,
            })

        mutation_records = [step_records]
        is_s0_clean, s0_reason = screen.screen_native_s0(s0_files)
        s0_screen_status = s0_reason
        target_info = {
            "kind": "change_request",
            "invariant_id": None,
            "description": f"Native change request for family {family}",
        }

    # Flatten mutation records
    flat_records = []
    for rlist in mutation_records:
        for r in rlist:
            if hasattr(r, "step"):
                flat_records.append({
                    "step": r.step,
                    "operator": r.operator,
                    "target_address": r.target_address,
                    "attribute": r.attribute,
                    "before": r.before,
                    "after": r.after,
                })
            else:
                flat_records.append(r)

    scenario_data = {
        "scenario_id": scenario_id,
        "dataset_version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "family": family,
        "split": split,
        "gt_class": None,
        "intent": {
            "class": cls,
            "target_kind": target_info["kind"],
            "target_invariant": target_info["invariant_id"],
            "breaks": [target_info["invariant_id"]] if (cls == "unsafe" and target_info["invariant_id"]) else [],
            "preserves": [inv["invariant_id"] for inv in PROTECTED_INVARIANTS if inv["invariant_id"] != target_info["invariant_id"]],
        },
        "reserve": reserve,
        "module_id": module_id,
        "pool_id": pool_id,
        "derived": derived,
        "grafted": (kind == "host"),
        "seed": global_id,
        "parameters": {
            "kind": kind,
            "module_id": module_id,
            "pool_id": pool_id,
            "derived": derived,
            "grafted": (kind == "host"),
            "lineage_id": plan_item["lineage_id"],
        },
        "source": {
            "tier": "real_world",
            "origin": "terrads",
            "repo_lineage_id": plan_item["lineage_id"],
            "commit_or_version": mod_entry.get("commit_sha", "unknown"),
            "license": mod_entry.get("licence_spdx", "permissive"),
            "grafted": (kind == "host"),
        },
        "scope_addresses": scope_addresses,
        "host_transform": transform_records,
        "s0_screen": s0_screen_status,
        "target": target_info,
        "protected_invariants": PROTECTED_INVARIANTS,
        "steps": steps_meta,
        "mutation_record": flat_records,
        "labels": None,
        "oracle": None,
    }

    return scenario_data, steps_files, mutation_records


def write_real_world_scenario(
    target_root: Path,
    scenario_data: dict[str, Any],
    steps_files: list[dict[str, str]],
    provenance_source_dir: Path,
) -> None:
    """Write scenario directory with scenario.json, step_0/, step_1/, and PROVENANCE/."""
    sc_id = scenario_data["scenario_id"]
    sc_dir = target_root / sc_id
    sc_dir.mkdir(parents=True, exist_ok=True)

    # 1. scenario.json
    (sc_dir / "scenario.json").write_text(
        writer.canonical_json(scenario_data),
        encoding="utf-8",
        newline="\n",
    )

    # 2. Step directories
    for sidx, sfiles in enumerate(steps_files):
        sdir = sc_dir / f"step_{sidx}"
        sdir.mkdir(parents=True, exist_ok=True)
        for fname, fcontent in sfiles.items():
            (sdir / fname).write_text(fcontent, encoding="utf-8", newline="\n")

    # 3. PROVENANCE/
    prov_dir = sc_dir / "PROVENANCE"
    prov_dir.mkdir(parents=True, exist_ok=True)
    for ef in ("LICENSE.upstream", "SOURCE.json", "DERIVED.md"):
        src = provenance_source_dir / ef
        if src.is_file():
            shutil.copy2(src, prov_dir / ef)


def run_real_world_pipeline(resume: bool = True) -> dict[str, Any]:
    """Generate and validate all 208 real-world scenarios."""
    plan = rw_plan.build_real_world_plan()
    private_root = get_private_dir()
    dev_root = REPO_ROOT / "scenarios" / "dev"
    manifest_path = REPO_ROOT / "scenarios" / "test_manifest.json"
    dev_csv = REPO_ROOT / "scenarios" / "validate_results.csv"
    test_csv = private_root / "validate_results.csv"

    # Load existing manifest to preserve the 64 controlled test entries
    existing_manifest: list[dict[str, Any]] = []
    if manifest_path.is_file():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Controlled entries: IDs without -rw or global counter <= 208
    controlled_manifest = [e for e in existing_manifest if int(e["scenario_id"].split("-")[-1]) <= 208]
    assert len(controlled_manifest) == 64, f"Expected 64 controlled test entries, found {len(controlled_manifest)}"

    # Build validation cache from existing scenario files and CSVs
    valid_hash_cache: dict[str, tuple[str, str]] = {}
    if resume:
        # Dev cache
        if dev_csv.is_file():
            csv_dev: dict[tuple[str, int], tuple[str, str]] = {}
            with open(dev_csv, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    csv_dev[(r["scenario_id"], int(r["step"]))] = (r["status"], r.get("error_class", ""))
            for sc_dir in dev_root.glob("tp-v1-*"):
                sc_json = sc_dir / "scenario.json"
                if sc_json.is_file():
                    try:
                        d = json.loads(sc_json.read_text(encoding="utf-8"))
                        sc_id = d.get("scenario_id", "")
                        for st in d.get("steps", []):
                            st_num = st.get("step")
                            chash = st.get("content_hash")
                            if chash and csv_dev.get((sc_id, st_num)) == ("valid", ""):
                                valid_hash_cache[chash] = ("valid", "")
                    except Exception:
                        pass

        # Test cache
        if test_csv.is_file():
            csv_test: dict[tuple[str, int], tuple[str, str]] = {}
            with open(test_csv, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    csv_test[(r["scenario_id"], int(r["step"]))] = (r["status"], r.get("error_class", ""))
            for sc_dir in private_root.glob("tp-v1-*"):
                sc_json = sc_dir / "scenario.json"
                if sc_json.is_file():
                    try:
                        d = json.loads(sc_json.read_text(encoding="utf-8"))
                        sc_id = d.get("scenario_id", "")
                        for st in d.get("steps", []):
                            st_num = st.get("step")
                            chash = st.get("content_hash")
                            if chash and csv_test.get((sc_id, st_num)) == ("valid", ""):
                                valid_hash_cache[chash] = ("valid", "")
                    except Exception:
                        pass

    harness = validate.Harness.default()

    counts = {
        "total": len(plan),
        "dev": 0,
        "test": 0,
        "targets": 0,
        "reserves": 0,
        "valid_steps": 0,
        "invalid_steps": 0,
        "error_steps": 0,
        "first_run_failures": [],
    }

    dev_csv_rows: list[dict[str, Any]] = []
    test_csv_rows: list[dict[str, Any]] = []
    new_test_manifest_entries: list[dict[str, Any]] = []

    for item in plan:
        sc_data, steps_files, _ = generate_real_world_scenario(item)
        sc_id = sc_data["scenario_id"]
        split = sc_data["split"]
        mid = sc_data["module_id"]
        derived = sc_data["derived"]
        kind = sc_data["parameters"]["kind"]

        # Find provenance source directory
        if kind == "host":
            prov_src = REPO_ROOT / "pool" / "terrads" / "host" / str(mid)
        elif derived:
            prov_src = REPO_ROOT / "pool" / "terrads" / "derived" / str(mid)
        else:
            prov_src = REPO_ROOT / "pool" / "terrads" / "native" / str(mid)

        if split == "dev":
            counts["dev"] += 1
            write_real_world_scenario(dev_root, sc_data, steps_files, prov_src)
        else:
            counts["test"] += 1
            write_real_world_scenario(private_root, sc_data, steps_files, prov_src)
            # Build manifest entry
            sc_json_text = writer.canonical_json(sc_data)
            steps_hash_list = []
            for sidx, sfiles in enumerate(steps_files):
                chash = writer.compute_step_content_hash(sfiles)
                steps_hash_list.append({"step": sidx, "content_hash": chash})
            new_test_manifest_entries.append({
                "scenario_id": sc_id,
                "scenario_json_sha256": writer.sha256_text(sc_json_text),
                "steps": steps_hash_list,
            })

        if sc_data["reserve"]:
            counts["reserves"] += 1
        else:
            counts["targets"] += 1

        # Validate every step
        for sidx, sfiles in enumerate(steps_files):
            chash = writer.compute_step_content_hash(sfiles)
            if chash in valid_hash_cache:
                status, error_class = valid_hash_cache[chash]
            else:
                res = harness.validate(sfiles)
                retries = 0
                while res.status == "error" and retries < 3:
                    retries += 1
                    import time
                    time.sleep(0.5)
                    res = harness.validate(sfiles)
                status, error_class = res.status, res.error_class or ""
                if status == "valid":
                    valid_hash_cache[chash] = (status, error_class)

            if status == "valid":
                counts["valid_steps"] += 1
            elif status == "invalid":
                counts["invalid_steps"] += 1
                counts["first_run_failures"].append((sc_id, sidx, status, error_class))
            else:
                counts["error_steps"] += 1
                counts["first_run_failures"].append((sc_id, sidx, status, error_class))

            row = {
                "scenario_id": sc_id,
                "step": sidx,
                "status": status,
                "error_class": error_class,
            }
            if split == "dev":
                dev_csv_rows.append(row)
            else:
                test_csv_rows.append(row)

    # Clean existing real-world rows from dev CSV, then write combined rows
    existing_dev_rows: list[dict[str, str]] = []
    if dev_csv.is_file():
        with open(dev_csv, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    num = int(r["scenario_id"].split("-")[-1])
                    if num <= 208:
                        existing_dev_rows.append(r)
                except Exception:
                    existing_dev_rows.append(r)

    with open(dev_csv, "w", newline="", encoding="utf-8") as f:
        writer_obj = csv.DictWriter(
            f,
            fieldnames=["scenario_id", "step", "status", "error_class"],
        )
        writer_obj.writeheader()
        for row in existing_dev_rows:
            writer_obj.writerow({k: row.get(k, "") for k in ["scenario_id", "step", "status", "error_class"]})
        for row in dev_csv_rows:
            writer_obj.writerow(row)

    # Clean existing real-world rows from test CSV, then write combined rows
    existing_test_rows: list[dict[str, str]] = []
    if test_csv.is_file():
        with open(test_csv, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    num = int(r["scenario_id"].split("-")[-1])
                    if num <= 208:
                        existing_test_rows.append(r)
                except Exception:
                    existing_test_rows.append(r)

    with open(test_csv, "w", newline="", encoding="utf-8") as f:
        writer_obj = csv.DictWriter(
            f,
            fieldnames=["scenario_id", "step", "status", "error_class"],
        )
        writer_obj.writeheader()
        for row in existing_test_rows:
            writer_obj.writerow({k: row.get(k, "") for k in ["scenario_id", "step", "status", "error_class"]})
        for row in test_csv_rows:
            writer_obj.writerow(row)

    # Write combined test manifest: 64 controlled entries + 64 real-world entries = 128 entries
    combined_manifest = controlled_manifest + new_test_manifest_entries
    manifest_path.write_text(
        writer.canonical_json(combined_manifest),
        encoding="utf-8",
        newline="\n",
    )

    return counts


if __name__ == "__main__":
    res = run_real_world_pipeline()
    print("Real-world pipeline summary:", json.dumps(res, indent=2))

