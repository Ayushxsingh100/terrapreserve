#!/usr/bin/env python3
"""Computed report for D4b review round 5 (every number comes from the repository).

Prints, from the pool, the plan, the generated scenarios and the docs, never from memory:
  * screen statistics per split (hosts examined, accepted, rejected per exclusion code);
  * replacements (dev: old module -> new module; test: scenario ids only) and shortfalls per family and split;
  * per-family and per-split counts from scenarios/ASSEMBLY.json;
  * round-5 rule counts over all loaded scenarios (whole-module SEC, SEC-003, types, MIXED, indeterminacy,
    FUNC at S0, derived);
  * drift against a reference commit (changed files per tier);
  * validation totals and the Status of every decision row (reused from the round-4 report).

The private test split is read from $TERRAPRESERVE_PRIVATE when set; only counts and ids are printed for it.
Standard library only.
"""

from __future__ import annotations

import collections
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "pool"))
sys.path.insert(0, str(REPO_ROOT / "generator"))
sys.path.insert(0, str(REPO_ROOT / "tests"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from realworld import plan as rw_plan  # noqa: E402
import report_d4b_round4 as rr  # noqa: E402
import test_d4b_review_round4 as r4  # noqa: E402
import test_d4b_review_round5 as r5  # noqa: E402


def screen_and_replacements() -> dict:
    plan, rep = rw_plan.build_plan_with_report()
    print("## Screen statistics (whole-module S0 screen, D4b-15; hosts only, derived natives are out of v1.0)")
    for split in ("dev", "test"):
        st = rep["stats"][split]
        print(f"- {split}: hosts examined {st['hosts_examined']}, accepted {st['accepted']}, rejected {st['rejected']}")
        print(f"  - by primary code (first code in priority order): {st['by_primary_code']}")
        print(f"  - by any code triggered: {st['by_any_code']}")
    print(f"- slots {rep['slots']}, planned {rep['planned']}, shortfalls {len(rep['shortfalls'])}")
    print()
    print("## Replaced scenarios")
    dev = [r for r in rep["replacements"] if r["split"] == "dev"]
    test = [r for r in rep["replacements"] if r["split"] == "test"]
    print(f"### dev ({len(dev)}): scenario: old module (kind) -> new module, reason")
    for r in dev:
        print(f"- {r['scenario_id']}: {r['old_module_id']} ({r['old_kind']}) -> {r['new_module_id']}, {r['reason']}")
    print(f"### test ({len(test)}): scenario ids only, as they appear in scenarios/test_manifest.json")
    print("- " + ", ".join(r["scenario_id"] for r in test))
    print(f"### by split and reason: {dict(collections.Counter((r['split'], r['reason']) for r in rep['replacements']))}")
    print()
    print("## Shortfalls")
    if not rep["shortfalls"]:
        print("- none: every slot is filled")
    c = collections.Counter((s["family"], s["split"], "reserve" if s["reserve"] else "target")
                            for s in rep["shortfalls"])
    for k in sorted(c):
        print(f"- {k}: {c[k]}")
    print()
    return rep


def family_split_counts() -> None:
    a = json.loads((REPO_ROOT / "scenarios" / "ASSEMBLY.json").read_text(encoding="utf-8"))
    print("## Per-family, per-split counts (scenarios/ASSEMBLY.json)")
    print(f"- total {a['total_scenarios']}; targets {a['targets']['total']}; reserves {a['reserves']['total']}; "
          f"dev {a['splits']['dev_total']}; test {a['splits']['test_total']}")
    for k in sorted(a["families"]):
        f = a["families"][k]
        print(f"- {k}: total {f['total']} (dev {f['dev']}, test {f['test']}; safe {f['safe']}, unsafe {f['unsafe']}; "
              f"targets {f['targets']}, reserves {f['reserves']})")
    print(f"- real-world composition: {a['real_world']['composition']}")
    print()


def rule_counts(scs: list) -> None:
    checks = [
        ("whole-module SEC-001/002 at S0 (test 1)", r5.check_sec_s0),
        ("SEC-003 at S0 (test 2)", r5.check_sec003_s0),
        ("relevant-unsupported types (test 3)", r5.check_unsupported_types),
        ("MIXED groups, whole module (test 4)", r5.check_mixed_whole),
        ("RETAINED-INLINE groups, whole module (test 4)", r5.check_retained_inline_whole),
        ("registry indeterminacy (test 5)", r5.check_indeterminacy),
        ("INV-FUNC-001 at S0 (test 6)", r5.check_func_s0),
        ("final-step SEC intent, whole module (test 7)", r5.check_intent_whole),
        ("derived natives (test 8)", r5.check_not_derived),
    ]
    print("## Round-5 rule counts (violations found; 0 means the rule holds)")
    for split in ("dev", "test"):
        part = [s for s in scs if s.split == split]
        if not part:
            print(f"- {split}: not loaded")
            continue
        steps = sum(len(s.step_dirs()) for s in part)
        print(f"- {split}: {len(part)} scenarios, {steps} steps")
        for label, fn in checks:
            print(f"  - {label}: {sum(len(fn(s)) for s in part)}")
    print()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO_ROOT, encoding="utf-8").stdout


def drift(ref: str) -> None:
    print(f"## Drift against {ref}")
    out = _git("diff", "--name-status", ref, "--", "scenarios/dev")
    status = collections.Counter()
    scen: dict[str, set[str]] = collections.defaultdict(set)
    for line in out.splitlines():
        st, path = line.split("\t", 1)
        parts = path.split("/")
        sid = parts[2]
        num = int(sid.split("-")[-1])
        tier = "controlled" if num <= 208 else "real_world"
        status[(tier, st[0])] += 1
        scen[tier].add(sid)
    for tier in ("controlled", "real_world"):
        print(f"- dev {tier}: scenarios touched {len(scen[tier])}; files "
              f"{ {k[1]: v for k, v in status.items() if k[0] == tier} } (A added, D deleted, M modified)")
    # also untracked new files
    untracked = [ln for ln in _git("ls-files", "--others", "--exclude-standard", "scenarios/dev").splitlines()]
    print(f"- dev untracked new files: {len(untracked)}")
    old = json.loads(_git("show", f"{ref}:scenarios/test_manifest.json"))
    new = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
    om = {e["scenario_id"]: e for e in old}
    nm = {e["scenario_id"]: e for e in new}
    for tier, pred in (("controlled", lambda n: n <= 208), ("real_world", lambda n: n > 208)):
        ids = [i for i in nm if pred(int(i.split("-")[-1]))]
        changed = [i for i in ids if om.get(i) != nm[i]]
        steps_changed = [i for i in changed if om.get(i, {}).get("steps") != nm[i]["steps"]]
        print(f"- test manifest {tier}: {len(ids)} entries, {len(changed)} changed "
              f"({len(steps_changed)} with a changed step hash)")
    print()


def main() -> None:
    ref = sys.argv[1] if len(sys.argv) > 1 else "47a2781"
    screen_and_replacements()
    scs = r4.load_all()
    rule_counts(scs)
    family_split_counts()
    drift(ref)
    rr.validation_totals()
    rr.decision_rows()


if __name__ == "__main__":
    main()
