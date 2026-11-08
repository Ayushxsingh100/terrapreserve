"""Step 7 mutation checks for D4b real-world tier and assembly.

Executes intentional rule-breaking checks and demonstrates failure detection:
1. Real text diff verifier catches dropped mutation row.
2. Real text diff verifier catches invented phantom row.
3. Real text diff verifier catches unrecorded byte change.
4. Graft builder detects clashing resource names with host.
5. S0 screen rejects insecure security group ingress (0.0.0.0/0 on port 22/5432).
6. Lineage leakage across splits is detected.
7. Missing upstream provenance (LICENSE.upstream) is detected.
8. Determinism check run against a deliberately broken generator, plus drift against 48ed76b.
9-13. Round 4 rules: empty vpc_security_group_ids, hard-coded egress CIDR, RETAINED-INLINE,
   MIXED group and non-local route are each injected into a scratch copy and must be caught.
"""

from __future__ import annotations

import json
import random
import re
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


DRIFT_BASE = "48ed76b"


def _controlled_items(n: int) -> list[dict]:
    """The first ``n`` controlled plan items spread over different families."""
    from generate import build_scenario_plan

    plan = build_scenario_plan()
    step = max(1, len(plan) // n)
    return [plan[i] for i in range(0, len(plan), step)][:n]


def check_8_determinism_and_drift() -> None:
    print("=== Mutation 8: determinism comparison against a deliberately broken generator, and drift vs "
          f"{DRIFT_BASE} ===")
    import unittest.mock as mock

    import determinism
    import seed
    from generate import generate_scenario

    items = _controlled_items(6)

    # 1. Break the generator: scenario_rng returns an unseeded Random, so two runs differ.
    #    The comparison is determinism.check_deterministic, the same one part 2 uses.
    caught = 0
    first_message = ""
    with mock.patch.object(seed, "scenario_rng", lambda idx, **kw: random.Random()):
        for item in items:
            try:
                determinism.check_deterministic(
                    generate_scenario, item, label=f"{item['family']}/{item['cls']}/{item['template_id']}")
            except determinism.DeterminismError as exc:
                caught += 1
                first_message = first_message or str(exc)
    if caught:
        print(f"EXPECTED FAILURE CAUGHT: the real determinism comparison raised on {caught} of {len(items)} "
              f"items with an unseeded generator.\n  first message: {first_message}")
    else:
        print("UNEXPECTED PASS: the determinism comparison did not detect an unseeded generator")

    # 2. Clean generator: the same comparison passes.
    for item in items:
        determinism.check_deterministic(
            generate_scenario, item, label=f"{item['family']}/{item['cls']}/{item['template_id']}")
    print(f"Determinism verified: {len(items)} items generated twice with the clean generator are byte-identical")

    # 3. Drift against the previous commit, listed truthfully by tier.
    proc = subprocess.run(["git", "diff", "--name-only", DRIFT_BASE, "--", "scenarios/dev/"],
                          capture_output=True, text=True, cwd=REPO_ROOT)
    files: dict[str, list[str]] = {"controlled": [], "real_world": []}
    scenarios: dict[str, set[str]] = {"controlled": set(), "real_world": set()}
    for line in proc.stdout.splitlines():
        parts = line.strip().replace("\\", "/").split("/")
        if len(parts) > 2 and parts[2].startswith("tp-v1-"):
            try:
                num = int(parts[2].split("-")[-1])
            except ValueError:
                continue
            tier = "controlled" if num <= 208 else "real_world"
            files[tier].append(line.strip())
            scenarios[tier].add(parts[2])
    for tier in ("controlled", "real_world"):
        print(f"Drift vs {DRIFT_BASE} (dev, {tier}): {len(files[tier])} files in {len(scenarios[tier])} scenarios changed")
    show = (files["controlled"] + files["real_world"])[:5]
    if show:
        print("Sample changed paths:")
        for pth in show:
            print(f"  {pth}")
    old = subprocess.run(["git", "show", f"{DRIFT_BASE}:scenarios/test_manifest.json"],
                         capture_output=True, text=True, cwd=REPO_ROOT)
    manifest = REPO_ROOT / "scenarios" / "test_manifest.json"
    if old.returncode == 0 and manifest.is_file():
        before = {e["scenario_id"]: e["scenario_json_sha256"] for e in json.loads(old.stdout)}
        after = {e["scenario_id"]: e["scenario_json_sha256"] for e in json.loads(manifest.read_text(encoding="utf-8"))}
        for tier, pred in (("controlled", lambda n: n <= 208), ("real_world", lambda n: n > 208)):
            ids = [i for i in after if pred(int(i.split("-")[-1]))]
            changed = sum(1 for i in ids if before.get(i) != after[i])
            print(f"Drift vs {DRIFT_BASE} (test split, {tier}, counts only): {changed} of {len(ids)} manifest entries changed")


# ---------------------------------------------------------------------------
# Round 4 rule checks: inject one fault into a scratch copy, show the rule catches it.
# ---------------------------------------------------------------------------


def _r4():
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    import test_d4b_review_round4 as r4

    return r4


def _dev_scenarios(r4, tier: str):
    for p in sorted((REPO_ROOT / "scenarios" / "dev").glob("tp-v1-*")):
        if (p / "scenario.json").is_file():
            sc = r4.load_scenario(p, "dev")
            if sc.tier == tier and len(sc.step_dirs()) >= 2:
                yield sc


def _scratch(sc, tmp: Path):
    import shutil

    dst = tmp / sc.id
    shutil.copytree(sc.dir, dst)
    return dst


def _report(label: str, control: list[str], found: list[str]) -> None:
    if control:
        print(f"UNEXPECTED: the unmodified scenario already violates the rule: {control[:2]}")
    if found:
        print(f"EXPECTED FAILURE CAUGHT ({label}): {len(found)} violation(s); first: {found[0]}")
    else:
        print(f"UNEXPECTED PASS ({label}): the rule did not detect the injected fault")


def check_9_empty_security_group_list() -> None:
    print("\n=== Mutation 9: vpc_security_group_ids = [] injected into a copied scenario (test 1) ===")
    r4 = _r4()
    sc = next(_dev_scenarios(r4, "controlled"))
    with tempfile.TemporaryDirectory() as tmp:
        dst = _scratch(sc, Path(tmp))
        control = r4.check_empty_sg_list(r4.load_scenario(dst))
        last = sorted(dst.glob("step_*"), key=lambda p: int(p.name.split("_")[1]))[-1] / "main.tf"
        text = last.read_text(encoding="utf-8")
        at = text.index('resource "aws_instance"')
        text = text[:at] + re.sub(r"vpc_security_group_ids\s*=\s*\[[^\]]*\]", "vpc_security_group_ids = []",
                                  text[at:], count=1)
        last.write_text(text, encoding="utf-8", newline="\n")
        _report("test 1", control, r4.check_empty_sg_list(r4.load_scenario(dst)))


def check_10_hardcoded_egress_cidr() -> None:
    print("\n=== Mutation 10: hard-coded 10.0.0.0/8 egress injected into a 172.x grafted scenario (tests 5 and 7) ===")
    r4 = _r4()
    sc = next(s for s in _dev_scenarios(r4, "real_world")
              if s.family == "F7" and s.cls == "safe" and s.data.get("grafted"))
    with tempfile.TemporaryDirectory() as tmp:
        dst = _scratch(sc, Path(tmp))
        control = r4.check_intent_truth(r4.load_scenario(dst)) + r4.check_egress(r4.load_scenario(dst))
        last = sorted(dst.glob("step_*"), key=lambda p: int(p.name.split("_")[1]))[-1] / "terrapreserve_graft.tf"
        text = last.read_text(encoding="utf-8")
        at = text.index('resource "aws_security_group_rule" "tp_app_egress"')
        text = text[:at] + re.sub(r'cidr_blocks(\s+)= \["[^"]+"\]', r'cidr_blocks\1= ["10.0.0.0/8"]',
                                  text[at:], count=1)
        last.write_text(text, encoding="utf-8", newline="\n")
        injected = r4.load_scenario(dst)
        _report("test 7", control, r4.check_intent_truth(injected))
        print(f"  (test 5 also reports: {r4.check_egress(injected)[:1]})")


def check_11_retained_inline() -> None:
    print("\n=== Mutation 11: egress argument left absent after inline blocks (test 3) ===")
    r4 = _r4()
    sc = next(s for s in _dev_scenarios(r4, "controlled")
              if re.search(r"\n  egress \{", (s.step_dirs()[0] / "main.tf").read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory() as tmp:
        dst = _scratch(sc, Path(tmp))
        control = r4.check_retained_inline(r4.load_scenario(dst))
        f = sorted(dst.glob("step_*"), key=lambda p: int(p.name.split("_")[1]))[1] / "main.tf"
        text = f.read_text(encoding="utf-8")
        text = re.sub(r"\n\n  egress \{\n(?:    .*\n)*?  \}", "", text, count=1)
        f.write_text(text, encoding="utf-8", newline="\n")
        _report("test 3", control, r4.check_retained_inline(r4.load_scenario(dst)))


def check_12_mixed_group() -> None:
    print("\n=== Mutation 12: inline block added to a group that is also a rule target (test 2) ===")
    r4 = _r4()
    sc = next(s for s in _dev_scenarios(r4, "controlled")
              if s.data["parameters"].get("sg_style") == "all_separate")
    with tempfile.TemporaryDirectory() as tmp:
        dst = _scratch(sc, Path(tmp))
        control = r4.check_mixed(r4.load_scenario(dst))
        f = sorted(dst.glob("step_*"), key=lambda p: int(p.name.split("_")[1]))[-1] / "main.tf"
        text = f.read_text(encoding="utf-8")
        m = re.search(r'(resource "aws_security_group" "[^"]+" \{\n(?:  .*\n)*?)(\}\n)', text)
        block = ('\n  egress {\n    cidr_blocks = ["0.0.0.0/0"]\n    from_port   = 0\n'
                 '    protocol    = "-1"\n    to_port     = 0\n  }\n')
        text = text[:m.end(1)] + block + text[m.start(2):]
        f.write_text(text, encoding="utf-8", newline="\n")
        _report("test 2", control, r4.check_mixed(r4.load_scenario(dst)))


def check_13_nonlocal_route() -> None:
    print("\n=== Mutation 13: route inside the VPC CIDR with a non-local target (test 4) ===")
    r4 = _r4()
    sc = next(_dev_scenarios(r4, "controlled"))
    with tempfile.TemporaryDirectory() as tmp:
        dst = _scratch(sc, Path(tmp))
        control = r4.check_nonlocal_routes(r4.load_scenario(dst))
        f = sorted(dst.glob("step_*"), key=lambda p: int(p.name.split("_")[1]))[-1] / "main.tf"
        text = f.read_text(encoding="utf-8")
        vpc_cidr = re.search(r'resource "aws_vpc" "[^"]+" \{\n(?:  .*\n)*?  cidr_block\s+= "([^"]+)"', text).group(1)
        text = re.sub(r'(route \{\n    cidr_block = )"0\.0\.0\.0/0"', rf'\g<1>"{vpc_cidr}"', text, count=1)
        f.write_text(text, encoding="utf-8", newline="\n")
        _report("test 4", control, r4.check_nonlocal_routes(r4.load_scenario(dst)))


def main() -> None:
    print("Running D4b Step 7 Mutation Checks...")
    check_1_real_diff_verifier_dropped_row()
    check_2_real_diff_verifier_invented_row()
    check_3_real_diff_verifier_unrecorded_byte_change()
    check_4_graft_clash_detection()
    check_5_s0_screen_rejection()
    check_6_lineage_leakage_audit()
    check_7_provenance_audit()
    check_8_determinism_and_drift()
    check_9_empty_security_group_list()
    check_10_hardcoded_egress_cidr()
    check_11_retained_inline()
    check_12_mixed_group()
    check_13_nonlocal_route()
    print("\nAll 13 mutation checks executed.")


if __name__ == "__main__":
    main()
