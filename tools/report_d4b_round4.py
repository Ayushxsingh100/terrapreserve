#!/usr/bin/env python3
"""Computed report for D4b review round 4 (every number comes from the repository).

Prints, from the generated scenarios and the docs, never from memory:
  * the operator table (family, operator, variant, edit, mechanism or SEC invariant, designed row);
  * the mechanism table (family x tier x mechanism x count, dev and test split);
  * the before/after of selected scenarios against a reference commit;
  * the A2 and A5 counts (empty vpc_security_group_ids, MIXED, RETAINED-INLINE, non-local routes);
  * per-family and per-tier counts and validation totals;
  * the Status column of every decision row, copied from the docs.

The private test split is read from $TERRAPRESERVE_PRIVATE when set; only counts are printed for it.
Standard library only.
"""

from __future__ import annotations

import collections
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "pool"))
sys.path.insert(0, str(REPO_ROOT / "generator"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import operators  # noqa: E402
import test_d4b_review_round4 as r4  # noqa: E402


def operator_table() -> None:
    print("## Operator table (computed from generator/operators/__init__.py)")
    print("| family | operator | variant | edit | mechanism or SEC invariant | designed §6.4 row |")
    print("|---|---|---|---|---|---|")
    for op in operators.CATALOGUE:
        if "INV-FUNC-001" in op.intent_breaks:
            mech = op.mechanism or "?"
            row = op.designed_row
        elif op.intent_breaks:
            mech = ",".join(op.intent_breaks)
            row = "n/a (INV-FUNC-001 preserved: row 6)"
        else:
            mech = "-"
            row = 6
        print(f"| {op.family} | `{op.name}` | {op.variant} | {op.description} | {mech} | {row} |")
    print()


def _op_of(sc: r4.Sc) -> str | None:
    rows = sc.data["mutation_record"]
    return rows[0]["operator"] if rows else None


def mechanism_table(scs: list[r4.Sc]) -> None:
    by_name = {op.name: op for op in operators.CATALOGUE}
    counts: dict[tuple, collections.Counter] = collections.defaultdict(collections.Counter)
    for sc in scs:
        if sc.cls != "unsafe":
            continue
        name = _op_of(sc)
        op = by_name.get(name or "")
        if op is None:
            label = "(native span edit)"
        elif "INV-FUNC-001" in op.intent_breaks:
            label = op.mechanism or "?"
        else:
            label = ",".join(op.intent_breaks)
        counts[(sc.family, sc.tier, label)][sc.split] += 1
    print("## Mechanism table (unsafe scenarios: family x tier x mechanism or SEC invariant x count)")
    print("| family | tier | mechanism / invariant | dev | test (count only) |")
    print("|---|---|---|---|---|")
    for key in sorted(counts):
        c = counts[key]
        print(f"| {key[0]} | {key[1]} | {key[2]} | {c.get('dev', 0)} | {c.get('test', 0)} |")
    print()


def rule_counts(scs: list[r4.Sc]) -> None:
    print("## A2 / A5 counts (all steps of all loaded scenarios)")
    for split in ("dev", "test"):
        part = [s for s in scs if s.split == split]
        if not part:
            print(f"- {split}: not loaded")
            continue
        steps = sum(len(s.step_dirs()) for s in part)
        print(f"- {split}: {len(part)} scenarios, {steps} steps")
        print(f"  - occurrences of `vpc_security_group_ids = []`: {sum(len(r4.check_empty_sg_list(s)) for s in part)}")
        print(f"  - MIXED groups: {sum(len(r4.check_mixed(s)) for s in part)}")
        print(f"  - RETAINED-INLINE groups: {sum(len(r4.check_retained_inline(s)) for s in part)}")
        print(f"  - non-local routes inside the VPC CIDR: {sum(len(r4.check_nonlocal_routes(s)) for s in part)}")
        print(f"  - egress CIDR violations (test 5): {sum(len(r4.check_egress(s)) for s in part)}")
        print(f"  - INV-FUNC-001 intent mismatches (test 7): {sum(len(r4.check_intent_truth(s)) for s in part)}")
        print(f"  - family mechanism violations (test 6): {sum(len(r4.check_mechanism(s)) for s in part)}")
        print(f"  - SEC intent mismatches (test 10): {sum(len(r4.check_sec_intent(s)) for s in part)}")
    print()


def _git_show(ref: str, path: str) -> str | None:
    p = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True,
                       cwd=REPO_ROOT, encoding="utf-8")
    return p.stdout if p.returncode == 0 else None


def before_after(ids: list[str], ref: str) -> None:
    print(f"## Before ({ref}) and after, evaluator verdict on the last step (generator self-check, not an oracle)")
    for sid in ids:
        sc_dir = REPO_ROOT / "scenarios" / "dev" / sid
        row = [f"- {sid}:"]
        old_json = _git_show(ref, f"scenarios/dev/{sid}/scenario.json")
        for label, loader in (("before", "old"), ("after", "new")):
            try:
                if loader == "old":
                    d = json.loads(old_json) if old_json else None
                    if d is None:
                        row.append(f"{label}: not present at {ref}")
                        continue
                    n = len(d["steps"])
                    mf = "terrapreserve_graft.tf" if d.get("grafted") else "main.tf"
                    text0 = _git_show(ref, f"scenarios/dev/{sid}/step_0/{mf}")
                    textn = _git_show(ref, f"scenarios/dev/{sid}/step_{n - 1}/{mf}")
                else:
                    d = json.loads((sc_dir / "scenario.json").read_text(encoding="utf-8"))
                    n = len(d["steps"])
                    mf = "terrapreserve_graft.tf" if d.get("grafted") else "main.tf"
                    text0 = (sc_dir / "step_0" / mf).read_text(encoding="utf-8")
                    textn = (sc_dir / f"step_{n - 1}" / mf).read_text(encoding="utf-8")
                s_addr, d_addr = r4.endpoints(r4.parse_model(text0))  # type: ignore[arg-type]
                v = r4.evaluate_func(r4.parse_model(textn), s_addr, d_addr)  # type: ignore[arg-type]
                model = r4.parse_model(textn)  # type: ignore[arg-type]
                vpc = next(r.attrs["cidr_block"] for r in model.resources.values() if r.type == "aws_vpc")
                egress = [list(x.cidrs) + [x.protocol, f"{x.from_port}-{x.to_port}"]
                          for g in r4.ref_list(model.resources[s_addr].attrs["vpc_security_group_ids"])
                          for x in r4.rules_of(model, g, "egress")]
                ops = sorted({m["operator"] for m in d["mutation_record"]})
                row.append(f"{label}: class={d['intent']['class']} breaks={d['intent']['breaks']} ops={ops} "
                           f"VPC={vpc} app egress={egress} -> {v.status} (row {v.row})")
            except Exception as exc:  # report, do not hide
                row.append(f"{label}: could not evaluate ({exc!r})")
        print("\n  ".join(row))
    print()


def counts() -> None:
    path = REPO_ROOT / "scenarios" / "ASSEMBLY.json"
    if not path.is_file():
        print("## Counts: scenarios/ASSEMBLY.json missing")
        return
    a = json.loads(path.read_text(encoding="utf-8"))
    print("## Counts (scenarios/ASSEMBLY.json)")
    print(f"- total scenarios: {a['total_scenarios']}; targets: {a['targets']['total']}; reserves: {a['reserves']['total']}")
    print(f"- dev: {a['splits']['dev_total']}; test: {a['splits']['test_total']}")
    fam = a.get("families") or a.get("family_stats") or {}
    for k in sorted(fam):
        print(f"- {k}: total {fam[k]['total']}, safe {fam[k]['safe']}, unsafe {fam[k]['unsafe']}")
    print()


def validation_totals() -> None:
    print("## Validation totals (validate_results.csv)")
    sources = [("dev", REPO_ROOT / "scenarios" / "validate_results.csv")]
    env = os.environ.get(r4.PRIVATE_ENV)
    if env:
        sources.append(("test", Path(env) / "validate_results.csv"))
    for split, path in sources:
        if not path.is_file():
            print(f"- {split}: {path.name} missing")
            continue
        tally: dict[str, collections.Counter] = {"controlled": collections.Counter(), "real_world": collections.Counter()}
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tier = "controlled" if int(row["scenario_id"].split("-")[-1]) <= 208 else "real_world"
                tally[tier][row["status"]] += 1
        for tier, c in tally.items():
            print(f"- {split} / {tier}: {dict(sorted(c.items()))} (steps: {sum(c.values())})")
    print()


def decision_rows() -> None:
    print("## Decision rows (id and Status exactly as written in the docs)")
    for f in ("D4_DECISIONS.md", "D4B_DECISIONS.md"):
        print(f"### docs/{f}")
        for line in (REPO_ROOT / "docs" / f).read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 5 and re.match(r"^(D4b?-\d+|Open( \d)?)$", cells[0]):
                print(f"- {cells[0]}: {cells[2]}")
    print()


def main() -> None:
    scs = r4.load_all()
    operator_table()
    mechanism_table(scs)
    rule_counts(scs)
    before_after(["tp-v1-F7-0365", "tp-v1-F7-0368", "tp-v1-F7-0371"], "48ed76b")
    counts()
    validation_totals()
    decision_rows()


if __name__ == "__main__":
    main()
