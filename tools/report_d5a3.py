#!/usr/bin/env python3
"""Computed report for D5a-3 (every number comes from the repository and the private test split).

Appends a D5a-3 part to ``docs/D5A_FEASIBILITY.md`` after its marker line, keeping the D5a and D5a-2 parts
byte for byte. Test split: counts only.

  1. decision rows of ``docs/D5_DECISIONS.md`` (id and status as written);
  2. vv-3 effect per split, tier and set: overridden declared defaults (dev ids), candidates taken by kind and index;
  3. the vv-3 search: scenarios that plan or fail per set, plans run;
  4. feasibility under each value set (``docs/d5a3/feasibility_dev_<set>.csv`` and the private test CSVs);
  5. exclusions (D5-09): dev ids with reason, test counts by reason;
  6. yields per family x class x split x tier cell (targets, reserves, excluded, whether the cell can still fill
     its targets from its own reserves; short cells named), checked against ``scenarios/ASSEMBLY.json``;
  7. drift against ``5f71c00`` (dev from git; test from the private split and the copy taken before regeneration,
     ``$TP_PRIVATE_BASELINE``, default ``~/.terrapreserve-private-pre-d5a3``).
Standard library only.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import varvalues  # noqa: E402
from realworld import data_vars  # noqa: E402

DOC = REPO_ROOT / "docs" / "D5A_FEASIBILITY.md"
MARKER = "<!-- D5a-3 results below: written by tools/report_d5a3.py; the D5a and D5a-2 parts above are kept as they were -->"
BASE_COMMIT = "5f71c00"
SETS = (("primary", "variable_values"), ("alternate", "variable_values_alt"))
TIERS = ("controlled", "real_world")
OUT: list[str] = []


def emit(line: str = "") -> None:
    OUT.append(line)
    print(line)


def private_root() -> Path | None:
    env = os.environ.get("TERRAPRESERVE_PRIVATE")
    return Path(env) if env and Path(env).is_dir() else None


def load() -> list[tuple[str, Path, dict]]:
    roots = [("dev", REPO_ROOT / "scenarios" / "dev")]
    if private_root() is not None:
        roots.append(("test", private_root()))
    out = []
    for split, root in roots:
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append((split, p, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


def search_doc(split: str) -> dict:
    path = varvalues.SEARCH_DEV if split == "dev" else private_root() / varvalues.SEARCH_TEST_NAME
    return json.loads(path.read_text(encoding="utf-8"))["scenarios"]


def feas_rows(split: str, vset: str) -> list[dict[str, str]]:
    path = (REPO_ROOT / "docs" / "d5a3" / f"feasibility_dev_{vset}.csv" if split == "dev"
            else private_root() / f"d5a3_feasibility_test_{vset}.csv")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def decisions() -> None:
    emit("### D5a-3.1 Decision rows (as written in `docs/D5_DECISIONS.md`)")
    for line in (REPO_ROOT / "docs" / "D5_DECISIONS.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 3 and re.match(r"^(D5-\d+|Open D5-[A-Z])$", cells[0]):
            emit(f"- {cells[0]}: {cells[2]}")
    emit()


def _leaf_kinds(kt) -> list[str]:
    return sorted(set(varvalues._all_leaves(kt)))


def effect(scs) -> None:
    emit("### D5a-3.2 Effect of vv-3 (D5-10)")
    emit("Overridden declared defaults (rule 1; one override holds in both sets):")
    c = collections.Counter()
    dev_rows = []
    for split, _p, d in scs:
        for name, e in d["variable_values_kinds"].items():
            if "reason" in e:
                c[(split, d["source"]["tier"])] += 1
                if split == "dev":
                    dev_rows.append(f"{d['scenario_id']} `{name}` ({e['reason'][:140]})")
    for split in ("dev", "test"):
        for tier in TIERS:
            emit(f"- {split} {tier}: {c[(split, tier)]}")
    emit("- dev variables overridden: " + ("; ".join(sorted(dev_rows)) or "none"))
    emit()
    emit("Candidates taken (rule 2), per set: variables by the kinds of their leaves and the index taken "
         "(index 0 is the vv-2 value):")
    emit("| split | tier | set | kinds | index | variables |")
    emit("|---|---|---|---|---|---|")
    t = collections.Counter()
    dev_moved = []
    for split, _p, d in scs:
        for vset, _key in SETS:
            for name, idx in d["variable_values_candidates"][vset].items():
                kinds = "+".join(_leaf_kinds(d["variable_values_kinds"][name]["kind"])) or "(no leaf)"
                t[(split, d["source"]["tier"], vset, kinds, idx)] += 1
                if split == "dev" and idx:
                    dev_moved.append(f"{d['scenario_id']} `{name}` {vset} {idx}")
    for key, n in sorted(t.items()):
        emit(f"| {' | '.join(str(k) for k in key)} | {n} |")
    emit()
    emit("- dev variables on a candidate other than 0: " + ("; ".join(sorted(dev_moved)) or "none"))
    emit()


def search_summary(scs) -> None:
    emit("### D5a-3.3 The vv-3 search (`tools/search_vv3.py`)")
    emit("| split | tier | scenarios | plans run | primary plans | primary fails | alternate plans | alternate fails |")
    emit("|---|---|---|---|---|---|---|---|")
    docs = {s: search_doc(s) for s in sorted({s for s, _p, _d in scs})}
    agg = collections.defaultdict(collections.Counter)
    for split, _p, d in scs:
        r = docs[split][d["scenario_id"]]["search"]
        a = agg[(split, d["source"]["tier"])]
        a["n"] += 1
        a["plans"] += r["plans_run"]
        for vset, _k in SETS:
            a[f"{vset} {r[vset]['result']}"] += 1
    for (split, tier), a in sorted(agg.items()):
        emit(f"| {split} | {tier} | {a['n']} | {a['plans']} | {a['primary plans']} | {a['primary fails']} | "
             f"{a['alternate plans']} | {a['alternate fails']} |")
    emit()


def feasibility(scs) -> None:
    emit("### D5a-3.4 Feasibility under each value set (D5-04 offline rules unchanged)")
    tier_of = {d["scenario_id"]: d["source"]["tier"] for _s, _p, d in scs}
    splits = sorted({s for s, _p, _d in scs})
    for vset, key in SETS:
        emit(f"#### Value set: {vset} (`{key}`)")
        emit("| split | tier | steps | plan JSON | data source needs API | provider tried to call AWS | variable error "
             "| other | median wall s | max wall s |")
        emit("|---|---|---|---|---|---|---|---|---|---|")
        causes = collections.Counter()
        for split in splits:
            rows = feas_rows(split, vset)
            for tier in TIERS:
                rs = [r for r in rows if tier_of.get(r["scenario_id"]) == tier]
                cnt = collections.Counter(r["error_class"] for r in rs if r["status"] == "failure")
                wall = [float(r["wall_seconds"]) for r in rs if r["wall_seconds"]]
                emit(f"| {split} | {tier} | {len(rs)} | {sum(r['status'] == 'success' for r in rs)} | "
                     f"{cnt['data source needs API']} | {cnt['provider tried to call AWS']} | {cnt['variable error']} | "
                     f"{cnt['other']} | {statistics.median(wall):.1f} | {max(wall):.1f} |")
            for r in rows:
                if r["status"] != "success":
                    causes[(split, r["error_class"], r["error_cause"])] += 1
        emit()
        emit("Failures by class and cause (steps):")
        for (s, cl, cause), n in sorted(causes.items()):
            emit(f"- {s}: {n} x {cl}: {cause or '(no sub-cause)'}")
        if not causes:
            emit("- none")
        emit()


def exclusions(scs) -> None:
    emit("### D5a-3.5 Exclusions (D5-09)")
    by = collections.Counter()
    dev = []
    for split, _p, d in scs:
        ex = d["excluded_from_v1"]
        if ex is None:
            continue
        what = ex["reason"].split(", ", 2)[-1]
        by[(split, d["source"]["tier"], what)] += 1
        if split == "dev":
            dev.append(f"- {d['scenario_id']}: {ex['reason']}; first error `{ex['first_error'][:160]}`")
    totals = collections.Counter((s, d["source"]["tier"]) for s, _p, d in scs if d["excluded_from_v1"])
    for split in sorted({s for s, _p, _d in scs}):
        for tier in TIERS:
            n_all = sum(1 for s, _p, d in scs if s == split and d["source"]["tier"] == tier)
            emit(f"- {split} {tier}: {totals[(split, tier)]} of {n_all} scenarios excluded")
    emit()
    emit("Excluded scenarios by the class and cause of their first failing step:")
    for (split, tier, what), n in sorted(by.items()):
        emit(f"- {split} {tier}: {n} x {what}")
    emit()
    emit("Dev scenarios excluded:")
    for row in sorted(dev) or ["- none"]:
        emit(row)
    emit()


def yields(scs) -> None:
    emit("### D5a-3.6 Yields per cell (family x class x split x tier)")
    emit("Targets and reserves as assigned in `scenarios/ASSEMBLY.json` (not changed; D6 fills). A cell can fill "
         "its targets when its excluded targets are no more than its reserves that are not excluded; filling "
         "across tiers is not allowed (D5-09).")
    emit()
    cells = collections.defaultdict(collections.Counter)
    for split, _p, d in scs:
        key = (d["family"], d["intent"]["class"], split, d["source"]["tier"])
        role = "reserves" if d["reserve"] else "targets"
        cells[key][role] += 1
        if d["excluded_from_v1"]:
            cells[key][f"excluded {role}"] += 1
    # Check against ASSEMBLY.json (family x class totals; split and tier totals).
    asm = json.loads((REPO_ROOT / "scenarios" / "ASSEMBLY.json").read_text(encoding="utf-8"))
    checks = []
    splits = sorted({s for s, _p, _d in scs})
    if splits == ["dev", "test"]:
        for cname, cell in asm["cells"].items():
            fam, cls = cell["family"], cell["class"]
            for role in ("targets", "reserves"):
                got = sum(c[role] for (f, k, _s, _t), c in cells.items() if (f, k) == (fam, cls))
                checks.append(got == cell[role]["total"])
                for tier in TIERS:
                    got_t = sum(c[role] for (f, k, _s, t), c in cells.items() if (f, k, t) == (fam, cls, tier))
                    checks.append(got_t == cell[role][tier])
    emit(f"Agreement with `ASSEMBLY.json` (per family x class: targets and reserves, total and per tier): "
         f"{sum(checks)} of {len(checks)} figures agree" if checks else
         "Agreement with `ASSEMBLY.json`: not checked (the test split is not available)")
    emit()
    emit("| family | class | split | tier | targets | reserves | excluded targets | excluded reserves | can fill |")
    emit("|---|---|---|---|---|---|---|---|---|")
    short = []
    tot = collections.Counter()
    for key in sorted(cells):
        c = cells[key]
        ok = c["excluded targets"] <= c["reserves"] - c["excluded reserves"]
        if not ok:
            short.append(" x ".join(key) + f" (short by {c['excluded targets'] - (c['reserves'] - c['excluded reserves'])})")
        for k in ("targets", "reserves", "excluded targets", "excluded reserves"):
            tot[(key[2], key[3], k)] += c[k]
        emit(f"| {' | '.join(key)} | {c['targets']} | {c['reserves']} | {c['excluded targets']} | "
             f"{c['excluded reserves']} | {'yes' if ok else 'no'} |")
    emit()
    emit("Totals:")
    for split in splits:
        for tier in TIERS:
            emit(f"- {split} {tier}: targets {tot[(split, tier, 'targets')]}, reserves {tot[(split, tier, 'reserves')]}, "
                 f"excluded targets {tot[(split, tier, 'excluded targets')]}, "
                 f"excluded reserves {tot[(split, tier, 'excluded reserves')]}")
    emit()
    emit("Short cells (cannot fill their targets from their own reserves): " + ("; ".join(short) or "none"))
    emit()


def _tier_dirs(root: Path) -> dict[str, str]:
    out = {}
    for p in root.glob("tp-v1-*"):
        if (p / "scenario.json").is_file():
            out[p.name] = json.loads((p / "scenario.json").read_text(encoding="utf-8"))["source"]["tier"]
    return out


def drift() -> None:
    emit(f"### D5a-3.7 Drift against `{BASE_COMMIT}`")
    tiers = _tier_dirs(REPO_ROOT / "scenarios" / "dev")
    diff = subprocess.run(["git", "diff", "--name-status", BASE_COMMIT, "--", "scenarios"], cwd=REPO_ROOT,
                          capture_output=True, text=True, check=True).stdout.splitlines()
    c = collections.Counter()
    for line in diff:
        status, path = line.split("\t", 1)
        parts = path.split("/")
        if len(parts) >= 3 and parts[1] == "dev":
            kind = "scenario.json" if parts[-1] == "scenario.json" else (
                "terrapreserve_data_variables.tf" if parts[-1] == data_vars.VARIABLES_FILE else "other step file")
            c[("dev", tiers.get(parts[2], "?"), status, kind)] += 1
        else:
            c[("repo", "-", status, path)] += 1
    base = Path(os.environ.get("TP_PRIVATE_BASELINE", Path.home() / ".terrapreserve-private-pre-d5a3"))
    priv = private_root()
    if priv is not None and base.is_dir():
        for sid, tier in _tier_dirs(priv).items():
            new = {f.relative_to(priv / sid).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                   for f in (priv / sid).rglob("*") if f.is_file()}
            old = {f.relative_to(base / sid).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                   for f in (base / sid).rglob("*") if f.is_file()} if (base / sid).is_dir() else {}
            for path in set(new) | set(old):
                if new.get(path) == old.get(path):
                    continue
                status = "A" if path not in old else ("D" if path not in new else "M")
                name = path.rsplit("/", 1)[-1]
                kind = "scenario.json" if name == "scenario.json" else (
                    "terrapreserve_data_variables.tf" if name == data_vars.VARIABLES_FILE else "other step file")
                c[("test", tier, status, kind)] += 1
    for (split, tier, status, kind), n in sorted(c.items()):
        emit(f"- {split} {tier}: {status} {kind}: {n}")
    emit()


def main() -> None:
    scs = load()
    text = DOC.read_text(encoding="utf-8")
    head = text.split(MARKER)[0].rstrip("\n") + "\n"
    emit(MARKER)
    emit()
    emit("## D5a-3 measurements (computed by `tools/report_d5a3.py`)")
    emit()
    emit("Value rule vv-3 (D5-10) and exclusion (D5-09), both value sets (D5-06). Every number below is computed "
         "from the repository and, for the test split, from the withheld directory (counts only). Regenerate with "
         "`python tools/report_d5a3.py` (with `TERRAPRESERVE_PRIVATE` set). The D5a and D5a-2 parts above describe "
         "vv-1 at `e96c017` and vv-2 at `5f71c00` and are kept as they were.")
    emit()
    decisions()
    effect(scs)
    search_summary(scs)
    feasibility(scs)
    exclusions(scs)
    yields(scs)
    drift()
    DOC.write_text(head + "\n" + "\n".join(OUT) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
