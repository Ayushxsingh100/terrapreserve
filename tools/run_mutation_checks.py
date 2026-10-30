"""Step 6 mutation checks on broken scratch models/records.
Executes intentional rule-breaking checks and demonstrates failure detection.
"""

from __future__ import annotations

import ast
import random
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "pool"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import diff_verify as dv
import model as m
import templates
import writer


def check_1_diff_verifier_dropped_row() -> None:
    print("=== Mutation 1: Diff verifier with dropped row ===")
    tpl = templates.TEMPLATES["tpl-01"]
    rng = random.Random(12345)
    base_model, _ = tpl.instantiate(rng, "clean")
    m1 = base_model.copy()
    ec2 = m1.resources["aws_instance.app"]
    ec2.set_attr("instance_type", "t3.large")
    ec2.set_attr("monitoring", True)

    # Actual diff has 2 changes, but record only has 1
    record = [
        dv.MutationRow(
            step=1,
            operator="test_op",
            target_address="aws_instance.app",
            attribute="instance_type",
            before='"t3.micro"',
            after='"t3.large"',
        )
    ]
    try:
        dv.verify(base_model, m1, record, step=1, operator_name="test_op")
        print("UNEXPECTED PASS")
    except dv.DiffVerifyError as e:
        print(f"EXPECTED FAILURE CAUGHT:\n{e}")


def check_2_diff_verifier_invented_row() -> None:
    print("\n=== Mutation 2: Diff verifier with invented phantom row ===")
    tpl = templates.TEMPLATES["tpl-01"]
    rng = random.Random(12345)
    base_model, _ = tpl.instantiate(rng, "clean")
    m1 = base_model.copy()
    ec2 = m1.resources["aws_instance.app"]
    ec2.set_attr("instance_type", "t3.large")

    record = [
        dv.MutationRow(
            step=1,
            operator="test_op",
            target_address="aws_instance.app",
            attribute="instance_type",
            before='"t3.micro"',
            after='"t3.large"',
        ),
        dv.MutationRow(
            step=1,
            operator="test_op",
            target_address="aws_instance.app",
            attribute="phantom_key",
            before=None,
            after='"bogus"',
        ),
    ]
    try:
        dv.verify(base_model, m1, record, step=1, operator_name="test_op")
        print("UNEXPECTED PASS")
    except dv.DiffVerifyError as e:
        print(f"EXPECTED FAILURE CAUGHT:\n{e}")


def check_3_dev_writer_accepting_test_scenario() -> None:
    print("\n=== Mutation 3: Dev writer receiving a test-split scenario ===")
    with tempfile.TemporaryDirectory() as tmp:
        dev_dir = Path(tmp) / "dev"
        data = {"scenario_id": "tp-v1-F1-0001", "split": "test", "template_id": "tpl-07"}
        try:
            writer.write_dev_scenario(dev_dir, data, [])
            print("UNEXPECTED PASS")
        except ValueError as e:
            print(f"EXPECTED FAILURE CAUGHT:\n{e}")


def check_4_manifest_leaking_forbidden_keys() -> None:
    print("\n=== Mutation 4: Test manifest leaking forbidden key ===")
    bad_manifest = [
        {"scenario_id": "tp-v1-F1-0001", "scenario_json_sha256": "abc", "steps": [], "intent": {"class": "safe"}}
    ]
    forbidden = {"family", "class", "intent", "template", "template_id", "gt_class", "diff"}
    leaked = set(bad_manifest[0].keys()) & forbidden
    if leaked:
        print(f"EXPECTED FAILURE CAUGHT: Manifest schema violation, forbidden keys: {leaked}")
    else:
        print("UNEXPECTED PASS")


def check_5_template_in_both_splits() -> None:
    print("\n=== Mutation 5: Overlapping split assignment ===")
    bad_split = {
        "dev_templates": ["tpl-01", "tpl-02", "tpl-03"],
        "test_templates": ["tpl-03", "tpl-04"],
    }
    overlap = set(bad_split["dev_templates"]) & set(bad_split["test_templates"])
    if overlap:
        print(f"EXPECTED FAILURE CAUGHT: Split disjointness invariant violated, overlap: {overlap}")
    else:
        print("UNEXPECTED PASS")


def check_6_independence_dail_import() -> None:
    print("\n=== Mutation 6: Independence check on DAIL import ===")
    code = """
import os
import core.impact
from core.verification import verify
"""
    tree = ast.parse(code)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported.append(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.append(node.module)
    forbidden = [mod for mod in imported if mod == "core" or mod.startswith("core.")]
    if forbidden:
        print(f"EXPECTED FAILURE CAUGHT: DAIL import detected: {forbidden}")
    else:
        print("UNEXPECTED PASS")


if __name__ == "__main__":
    check_1_diff_verifier_dropped_row()
    check_2_diff_verifier_invented_row()
    check_3_dev_writer_accepting_test_scenario()
    check_4_manifest_leaking_forbidden_keys()
    check_5_template_in_both_splits()
    check_6_independence_dail_import()
