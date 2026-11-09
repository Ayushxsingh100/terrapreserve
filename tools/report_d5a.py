#!/usr/bin/env python3
"""Computed report for D5a (every number comes from the repository and the private test split).

Prints, and writes to ``docs/D5A_FEASIBILITY.md`` (test split: counts only):
  1. baseline: scenarios and steps per split and tier; scenarios with a variable without a default; scenarios
     using data sources, by type; scenarios with module blocks; Terraform and provider versions in validation/;
  2. variable values (D5-01): counts per split and tier, unresolved variables with reasons, and the relevance
     report (placeholders that reach attributes the registry reads);
  3. the Step 4 feasibility table from ``docs/d5a/feasibility_dev.csv`` and the private test CSV;
  4. the Status of every row of ``docs/D5_DECISIONS.md``.
Standard library only.
"""

from __future__ import annotations

import collections
import csv
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

import hcl_lex  # noqa: E402
import varvalues  # noqa: E402
from realworld import modread  # noqa: E402

OUT: list[str] = []


def emit(line: str = "") -> None:
    OUT.append(line)
    print(line)


def roots() -> list[tuple[str, Path]]:
    out = [("dev", REPO_ROOT / "scenarios" / "dev")]
    env = os.environ.get("TERRAPRESERVE_PRIVATE")
    if env and Path(env).is_dir():
        out.append(("test", Path(env)))
    return out


def load() -> list[tuple[str, Path, dict, list[dict[str, str]]]]:
    out = []
    for split, root in roots():
        for p in sorted(root.glob("tp-v1-*")):
            if not (p / "scenario.json").is_file():
                continue
            d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
            steps = [{f.name: f.read_text(encoding="utf-8") for f in sorted(sd.glob("*.tf"))}
                     for sd in sorted((x for x in p.glob("step_*") if x.is_dir()),
                                      key=lambda x: int(x.name.split("_")[1]))]
            out.append((split, p, d, steps))
    return out


def baseline(scs) -> None:
    emit("## 1. Baseline")
    c = collections.Counter()
    ds = collections.Counter()
    for split, _p, d, steps in scs:
        key = (split, d["source"]["tier"])
        c[key + ("scenarios",)] += 1
        c[key + ("steps",)] += len(steps)
        types: set[str] = set()
        modules = False
        no_default = False
        for files in steps:
            for text in files.values():
                h = hcl_lex.headers_from_hcl(text)
                types |= {t for t, _n in h.data}
                modules = modules or bool(h.modules)
            mod = modread.read_module(files)
            no_default = no_default or any("default" not in b.attrs for b in mod.variables.values())
        c[key + ("with a variable without a default",)] += no_default
        c[key + ("with data sources",)] += bool(types)
        c[key + ("with module blocks",)] += modules
        for t in types:
            ds[(split, t)] += 1
    emit("| split | tier | scenarios | steps | with a variable without a default | with data sources | with module blocks |")
    emit("|---|---|---|---|---|---|---|")
    for split in ("dev", "test"):
        for tier in ("controlled", "real_world"):
            k = (split, tier)
            if c[k + ("scenarios",)]:
                emit(f"| {split} | {tier} | {c[k + ('scenarios',)]} | {c[k + ('steps',)]} | "
                     f"{c[k + ('with a variable without a default',)]} | {c[k + ('with data sources',)]} | "
                     f"{c[k + ('with module blocks',)]} |")
    emit()
    emit("Data-source types (number of scenarios using each):")
    for split in ("dev", "test"):
        row = ", ".join(f"`{t}` {n}" for (s, t), n in sorted(ds.items()) if s == split)
        emit(f"- {split}: {row or 'none'}")
    smoke = REPO_ROOT / "validation" / "smoke"
    text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(smoke.glob("*.tf")))
    rv = re.findall(r'required_version\s*=\s*"([^"]+)"', text)
    pv = re.findall(r'version\s*=\s*"([^"]+)"', re.sub(r'required_version\s*=\s*"[^"]+"', "", text))
    tfv = subprocess.run(["terraform", "version", "-json"], capture_output=True, text=True)
    tf_installed = json.loads(tfv.stdout)["terraform_version"] if tfv.returncode == 0 else "not available"
    emit(f"- validation/smoke: required_version {rv}, hashicorp/aws version {pv}; terraform on this machine "
         f"{tf_installed}; provider in the offline mirror: "
         f"{sorted(p.name for p in (Path.home() / '.terrapreserve-cache' / 'tf-mirror' / 'registry.terraform.io' / 'hashicorp' / 'aws').glob('*'))}")
    emit()


def variable_values(scs) -> None:
    emit("## 2. Variable values (D5-01, rule vv-1)")
    c = collections.Counter()
    reasons = collections.Counter()
    dev_unresolved = []
    rel_count = collections.Counter()
    dev_rel = []
    for split, _p, d, steps in scs:
        key = (split, d["source"]["tier"])
        vv = d.get("variable_values") or {}
        un = d.get("variable_values_unresolved") or {}
        c[key + ("scenarios",)] += 1
        c[key + ("rule vv-1",)] += d.get("variable_values_rule") == "vv-1"
        c[key + ("variables valued",)] += len(vv)
        c[key + ("variables unresolved",)] += len(un)
        c[key + ("scenarios with an unresolved variable",)] += bool(un)
        for name, why in un.items():
            reasons[(split, re.sub(r"\[.*?\]|\"[^\"]*\"|\(Error.*\)", "...", why))] += 1
            if split == "dev":
                dev_unresolved.append(f"{d['scenario_id']}: `{name}`: {why}")
        hits = varvalues.relevance(steps, set(vv))
        if hits:
            rel_count[key] += 1
            if split == "dev":
                vars_ = sorted({h[0] for h in hits})
                dev_rel.append(f"{d['scenario_id']}: {len(hits)} reach(es); variables {', '.join(vars_)}; "
                               f"e.g. `{hits[0][0]}` -> `{hits[0][1]}.{hits[0][2]}`")
    emit("| split | tier | scenarios | with rule vv-1 | variables valued | variables unresolved | scenarios with an unresolved variable | scenarios where a placeholder reaches a registry-read attribute |")
    emit("|---|---|---|---|---|---|---|---|")
    for split in ("dev", "test"):
        for tier in ("controlled", "real_world"):
            k = (split, tier)
            if c[k + ("scenarios",)]:
                emit(f"| {split} | {tier} | {c[k + ('scenarios',)]} | {c[k + ('rule vv-1',)]} | "
                     f"{c[k + ('variables valued',)]} | {c[k + ('variables unresolved',)]} | "
                     f"{c[k + ('scenarios with an unresolved variable',)]} | {rel_count[k]} |")
    emit()
    emit("Unresolved reasons (count of variables):")
    for (split, why), n in sorted(reasons.items()):
        emit(f"- {split}: {n} x {why}")
    emit()
    emit(f"Dev unresolved variables ({len(dev_unresolved)}):")
    for line in dev_unresolved:
        emit(f"- {line}")
    emit()
    emit("Relevance report: registry-read attributes are security-group and security-group-rule fields (any), "
         "`vpc_security_group_ids`, `subnet_id`, `security_group_id`, `publicly_accessible`, `port`, `engine`, "
         "`vpc_id`, `cidr_block`, and `count`/`for_each` of any resource holding them (direct or through locals).")
    emit(f"Dev scenarios where a placeholder reaches one ({len(dev_rel)}):")
    for line in dev_rel:
        emit(f"- {line}")
    emit()


def feasibility(scs) -> None:
    emit("## 3. Input-path feasibility (Step 4)")
    data_ids = set()
    for _split, _p, d, steps in scs:
        if any(hcl_lex.headers_from_hcl(t).data for files in steps for t in files.values()):
            data_ids.add(d["scenario_id"])
    causes: collections.Counter = collections.Counter()
    ds_split: collections.Counter = collections.Counter()
    sources = [("dev", REPO_ROOT / "docs" / "d5a" / "feasibility_dev.csv")]
    env = os.environ.get("TERRAPRESERVE_PRIVATE")
    if env:
        sources.append(("test", Path(env) / "d5a_feasibility_test.csv"))
    classes = ("data source needs API", "provider tried to call AWS", "variable error", "other")
    emit("| split | tier | steps | plan JSON produced | failed | " + " | ".join(f"failed: {k}" for k in classes)
         + " | median wall s | max wall s | Checkov ran | Checkov median s | Checkov max s |")
    emit("|---|---|---|---|---|" + "---|" * len(classes) + "---|---|---|---|---|")
    dev_fail = []
    stages = collections.Counter()
    for split, path in sources:
        if not path.is_file():
            emit(f"| {split} | (no results file) |")
            continue
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for tier in ("controlled", "real_world"):
            rs = [r for r in rows if r["tier"] == tier]
            if not rs:
                continue
            ok = [r for r in rs if r["status"] == "success"]
            bad = [r for r in rs if r["status"] != "success"]
            for r in bad:
                stages[(split, r["stage"], r["error_class"])] += 1
            walls = [float(r["wall_seconds"]) for r in rs if r["wall_seconds"]]
            ck = [float(r["checkov_seconds"]) for r in rs if r["checkov_seconds"]]
            emit(f"| {split} | {tier} | {len(rs)} | {len(ok)} | {len(bad)} | "
                 + " | ".join(str(sum(1 for r in bad if r["error_class"] == k)) for k in classes)
                 + f" | {statistics.median(walls):.1f} | {max(walls):.1f} | "
                 f"{sum(1 for r in rs if r['checkov_ran'] == 'yes')} | {statistics.median(ck):.1f} | {max(ck):.1f} |")
            for r in rs:
                ds_split[(split, r["scenario_id"] in data_ids, r["status"] != "success")] += 1
            for r in bad:
                causes[(split, r["error_class"], r.get("error_cause", ""))] += 1
            if split == "dev":
                for r in bad:
                    dev_fail.append(f"{r['scenario_id']}/step_{r['step']} ({r['stage']}, {r['error_class']}; "
                                    f"{r.get('error_cause', '')}): {r['error_first_line']}")
    emit()
    emit("Wall time is init + plan + show for one step, measured with 8 steps running in parallel on one machine; "
         "init reuses the provider already installed for its worker (a seeded lock file), so it does not copy the "
         "provider binary each time. Checkov time is separate.")
    emit()
    rr = REPO_ROOT / "docs" / "d5a" / "feasibility_reruns.json"
    if rr.is_file():
        r = json.loads(rr.read_text(encoding="utf-8"))
        emit(f"Measured twice: {len(r['dev_rows'])} dev steps and {r['test_rows_count']} test steps. {r['reason']}")
        emit()
    emit("Failures by stage and class: " + ", ".join(f"{s}/{st}/{k}: {n}" for (s, st, k), n in sorted(stages.items())))
    emit()
    emit("Failures by class and cause (steps):")
    for (split, k, cause), n in sorted(causes.items()):
        emit(f"- {split}: {k}; {cause or 'no sub-cause'}: {n}")
    emit()
    emit("Failed steps in scenarios that do / do not use `data` sources:")
    for (split, has_data, failed), n in sorted(ds_split.items()):
        emit(f"- {split}: {'with' if has_data else 'without'} data sources, {'failed' if failed else 'planned'}: {n}")
    emit()
    ids = sorted({line.split("/", 1)[0] for line in dev_fail})
    emit(f"Dev scenarios with at least one failed step ({len(ids)}): " + ", ".join(ids))
    emit()
    emit(f"Dev failures ({len(dev_fail)} steps):")
    for line in dev_fail:
        emit(f"- {line}")
    emit()


ROUTES = [
    "Route 1, HCL instead of plan JSON for every step: the oracle parses the configuration itself (like DAIL), "
    "so all steps are readable offline; it gives up the different input path that ADR-010 independence leans on.",
    "Route 2, plan JSON where it plans, HCL elsewhere: two input paths inside one oracle; labels would depend on "
    "which path a step took, and both paths need their own tests.",
    "Route 3, oracle-only data-source substitution: replace each `data` block in the working copy by a fixed local "
    "value; the planned configuration is no longer the scenario's text, and the substituted values become a new "
    "recorded rule like vv-1.",
    "Route 4, a revised value rule (vv-2) with typed placeholders (a valid CIDR, a well-formed id): would remove most "
    "variable errors; it changes `scenario.json` again and is the substance of Open D5-B.",
    "Route 5, plan with a mock provider (`terraform test` `mock_provider`, Terraform 1.7 or later): data sources "
    "return generated values offline; computed values are synthetic, so a label could rest on invented attributes.",
    "Route 6, a local AWS emulator such as LocalStack: excluded by the work package (no emulator); listed only for "
    "completeness.",
    "Route 7, mark failing steps UNKNOWN or UNSUPPORTED under the registry's indeterminacy rules and keep plan "
    "JSON only: no new machinery; D0 gate 4 (every step labelled) still holds, but many real-world steps carry no "
    "PASS or FAIL.",
    "Route 8, drop or replace the scenarios that cannot be planned: reduces the real-world tier; D0 Decision 3 says "
    "yields are reported, never padded.",
]


def routes() -> None:
    emit("## 4. Possible routes for the failing steps (listed, not chosen; Open D5-A and D5-B)")
    for line in ROUTES:
        emit(f"- {line}")
    emit()


def decisions() -> None:
    emit("## 5. Decision rows (docs/D5_DECISIONS.md, id and Status as written)")
    for line in (REPO_ROOT / "docs" / "D5_DECISIONS.md").read_text(encoding="utf-8").splitlines():
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and re.match(r"^(D5-\d+|Open D5-[A-Z])$", cells[0]):
            emit(f"- {cells[0]}: {cells[2]}")
    emit()


def main() -> None:
    scs = load()
    emit("# D5a measurements (computed by `tools/report_d5a.py`)")
    emit()
    emit("Every number below is computed from the repository and, for the test split, from the withheld "
         "directory (counts only). Regenerate with `python tools/report_d5a.py` (with `TERRAPRESERVE_PRIVATE` set).")
    emit()
    baseline(scs)
    variable_values(scs)
    feasibility(scs)
    routes()
    decisions()
    (REPO_ROOT / "docs" / "D5A_FEASIBILITY.md").write_text("\n".join(OUT) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
