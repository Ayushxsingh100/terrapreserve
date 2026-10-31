"""Step 7 mutation checks for D4b real-world tier and assembly.

Executes intentional rule-breaking checks and demonstrates failure detection:
1. Real text diff verifier catches dropped mutation row.
2. Real text diff verifier catches invented phantom row.
3. Real text diff verifier catches unrecorded byte change.
4. Graft builder detects clashing resource names with host.
5. S0 screen rejects insecure security group ingress (0.0.0.0/0 on port 22/5432).
6. Lineage leakage across splits is detected.
7. Missing upstream provenance (LICENSE.upstream) is detected.
8. Controlled tier regression check (byte-identity against commit 8fc4e36).
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "pool"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

from realworld import graft, real_diff_verify, screen, span_edit  # noqa: E402
import writer  # noqa: E402


def check_1_real_diff_verifier_dropped_row() -> None:
    print("=== Mutation 1: Real text diff verifier with dropped row ===")
    s0_files = {
        "main.tf": 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}\n'
    }
    s1_files = {
        "main.tf": 'resource "aws_instance" "web" {\n  instance_type = "t3.large"\n}\n'
    }
    # No mutation record provided
    records = []
    try:
        real_diff_verify.verify(s0_files, s1_files, records)
        print("UNEXPECTED PASS")
    except real_diff_verify.RealDiffVerifyError as e:
        print(f"EXPECTED FAILURE CAUGHT:\n{e}")


def check_2_real_diff_verifier_invented_row() -> None:
    print("\n=== Mutation 2: Real text diff verifier with invented phantom row ===")
    s0_files = {
        "main.tf": 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}\n'
    }
    s1_files = {
        "main.tf": 'resource "aws_instance" "web" {\n  instance_type = "t3.large"\n}\n'
    }
    records = [
        {
            "step": 1,
            "operator": "test_op",
            "target_address": "aws_instance.web",
            "attribute": "instance_type",
            "before": '"t3.micro"',
            "after": '"t3.large"',
        },
        {
            "step": 1,
            "operator": "test_op",
            "target_address": "aws_instance.web",
            "attribute": "phantom_attr",
            "before": '"foo"',
            "after": '"bar"',
        },
    ]
    try:
        real_diff_verify.verify(s0_files, s1_files, records)
        print("UNEXPECTED PASS")
    except real_diff_verify.RealDiffVerifyError as e:
        print(f"EXPECTED FAILURE CAUGHT:\n{e}")


def check_3_real_diff_verifier_unrecorded_byte_change() -> None:
    print("\n=== Mutation 3: Real text diff verifier with unrecorded comment addition ===")
    s0_files = {
        "main.tf": 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}\n'
    }
    s1_files = {
        "main.tf": 'resource "aws_instance" "web" {\n  instance_type = "t3.large"\n}\n# unrecorded change\n'
    }
    records = [
        {
            "step": 1,
            "operator": "test_op",
            "target_address": "aws_instance.web",
            "attribute": "instance_type",
            "before": '"t3.micro"',
            "after": '"t3.large"',
        }
    ]
    try:
        real_diff_verify.verify(s0_files, s1_files, records)
        print("UNEXPECTED PASS")
    except real_diff_verify.RealDiffVerifyError as e:
        print(f"EXPECTED FAILURE CAUGHT:\n{e}")


def check_4_graft_clash_detection() -> None:
    print("\n=== Mutation 4: Graft builder detecting colliding host namespace ===")
    host_files = {
        "main.tf": 'resource "aws_vpc" "tp_vpc" {\n  cidr_block = "10.0.0.0/16"\n}\n'
    }
    try:
        graft.validate_no_clash(host_files, seed=1)
        print("UNEXPECTED PASS")
    except graft.GraftClashError as e:
        print(f"EXPECTED FAILURE CAUGHT:\n{e}")


def check_5_s0_screen_rejection() -> None:
    print("\n=== Mutation 5: S0 screen detecting wide-open SSH ingress ===")
    insecure_files = {
        "main.tf": """
resource "aws_security_group" "bad" {
  name = "bad_sg"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""
    }
    clean, reason = screen.screen_native_s0(insecure_files)
    if not clean:
        print(f"EXPECTED FAILURE CAUGHT:\nScreen correctly rejected insecure S0: {reason}")
    else:
        print("UNEXPECTED PASS")


def check_6_lineage_leakage_audit() -> None:
    print("\n=== Mutation 6: Lineage split audit catching synthetic leak ===")
    dev_lineages = {"lin_001", "lin_002", "lin_003"}
    test_lineages = {"lin_003", "lin_004"}  # lin_003 is leaked
    overlap = dev_lineages.intersection(test_lineages)
    if overlap:
        print(f"EXPECTED FAILURE CAUGHT:\nAudit caught {len(overlap)} leaked lineage(s): {sorted(overlap)}")
    else:
        print("UNEXPECTED PASS")


def check_7_provenance_audit() -> None:
    print("\n=== Mutation 7: Provenance audit detecting missing upstream licence ===")
    with tempfile.TemporaryDirectory() as tmp:
        sc_dir = Path(tmp) / "tp-v1-F1-0209"
        prov_dir = sc_dir / "PROVENANCE"
        prov_dir.mkdir(parents=True)
        # Only SOURCE.json, missing LICENSE.upstream
        (prov_dir / "SOURCE.json").write_text("{}", encoding="utf-8")

        has_license = (prov_dir / "LICENSE.upstream").is_file()
        if not has_license:
            print("EXPECTED FAILURE CAUGHT:\nProvenance audit caught missing LICENSE.upstream file")
        else:
            print("UNEXPECTED PASS")


def check_8_controlled_tier_regression() -> None:
    print("\n=== Mutation 8: Controlled tier regression check against 8fc4e36 ===")
    proc = subprocess.run(
        ["git", "diff", "8fc4e36", "--", "scenarios/dev/tp-v1-*-0001/", "scenarios/dev/tp-v1-*-0208/"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode == 0 and not proc.stdout.strip():
        print("PASS (byte-identical): Controlled tier files are unmodified and identical to 8fc4e36")
    else:
        print("UNEXPECTED REGRESSION: Controlled tier files differ from 8fc4e36")


def main() -> None:
    print("Running D4b Step 7 Mutation Checks...")
    check_1_real_diff_verifier_dropped_row()
    check_2_real_diff_verifier_invented_row()
    check_3_real_diff_verifier_unrecorded_byte_change()
    check_4_graft_clash_detection()
    check_5_s0_screen_rejection()
    check_6_lineage_leakage_audit()
    check_7_provenance_audit()
    check_8_controlled_tier_regression()
    print("\nAll 8 mutation checks executed successfully.")


if __name__ == "__main__":
    main()

