#!/usr/bin/env python3
"""Computed report for D5a-2 (every number comes from the repository and the private test split).

Appends a D5a-2 part to ``docs/D5A_FEASIBILITY.md`` after the marker line, keeping the D5a part (written by
``tools/report_d5a.py`` at ``e96c017``) byte for byte. Test split: counts only.

  1. decision rows of ``docs/D5_DECISIONS.md`` (id and status as written);
  2. vv-2 summary per split and tier: variables by kind and by evidence, validation candidates taken,
     ``unresolved`` and ``conflict`` counts with reasons (dev ids);
  3. the D5-08 data-source transform: blocks removed by type, variables created, scenarios affected;
  4. the whole-module S0 screen re-run on every real-world scenario (before and after the transform);
  5. feasibility under each value set (``docs/d5a2/feasibility_dev_<set>.csv`` and the private test CSVs);
  6. drift against ``e96c017``: changed files per tier (dev from git; test from the private split and the copy
     taken before regeneration, ``$TP_PRIVATE_BASELINE``, default ``~/.terrapreserve-private-pre-d5a2-regen``).
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
from realworld import data_vars, graft, screen  # noqa: E402

DOC = REPO_ROOT / "docs" / "D5A_FEASIBILITY.md"
MARKER = "<!-- D5a-2 results below: written by tools/report_d5a2.py; the D5a part above is kept as it was -->"
BASE_COMMIT = "e96c017"
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


def ids(rows: list[str]) -> str:
    return ", ".join(sorted(set(rows))) or "none"


def decisions() -> None:
    emit("### D5a-2.1 Decision rows (as written in `docs/D5_DECISIONS.md`)")
    for line in (REPO_ROOT / "docs" / "D5_DECISIONS.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 3 and re.match(r"^(D5-\d+|Open D5-[A-Z])$", cells[0]):
            emit(f"- {cells[0]}: {cells[2]}")
    emit()


def _leaves(kt) -> list[str]:
    if isinstance(kt, str):
        return [kt]
    out: list[str] = []
    for key in ("list", "set", "map"):
        if key in kt:
            out += _leaves(kt[key])
    for v in kt.get("object", {}).values():
        out += _leaves(v)
    for v in kt.get("tuple", []):
        out += _leaves(v)
    return out


def _evidence_class(e: str) -> str:
    return e.split(":", 1)[0] if ":" in e else e.split(" at ")[0]


def value_sets(scs) -> None:
    emit("### D5a-2.2 Variable values, rule vv-2 (D5-07)")
    c = collections.Counter()
    kinds = collections.Counter()
    evid = collections.Counter()
    reasons = collections.Counter()
    dev_un: list[str] = []
    cand = collections.Counter()
    same = collections.Counter()
    for split, _p, d in scs:
        key = (split, d["source"]["tier"])
        c[key + ("scenarios",)] += 1
        c[key + ("vv-2",)] += d.get("variable_values_rule") == "vv-2"
        c[key + ("valued",)] += len(d.get("variable_values") or {})
        c[key + ("tp_ds valued",)] += sum(1 for n in d.get("variable_values") or {} if n.startswith("tp_ds_"))
        for name, ent in (d.get("variable_values_kinds") or {}).items():
            for leaf in _leaves(ent["kind"]):
                kinds[(split, d["source"]["tier"], leaf)] += 1
            for cls in {_evidence_class(e) for e in ent.get("evidence", [])}:
                evid[(split, d["source"]["tier"], cls)] += 1
            if "validation" in ent:
                got = (ent["validation"]["primary"], ent["validation"]["alternate"])
                kind = ent["kind"]
                if not isinstance(kind, str) or got == varvalues.KIND_VALUES[kind]:
                    taken = "the kind's value in both sets (first candidate)"
                else:
                    taken = f"a later candidate: primary {got[0]!r}, alternate {got[1]!r}"
                cand[(split, d["source"]["tier"], taken)] += 1
            if "same_in_both_sets" in ent:
                same[(split, d["source"]["tier"], ent["same_in_both_sets"])] += 1
        for name, ent in (d.get("variable_values_unresolved") or {}).items():
            c[key + (ent["status"],)] += 1
            reason = re.sub(r"usage:[^;]+", "usage:...", ent["reason"])
            reasons[(split, ent["status"], reason[:200])] += 1
            if split == "dev":
                dev_un.append(f"{d['scenario_id']} `{name}` ({ent['status']}: {ent['reason'][:220]})")
    emit("| split | tier | scenarios | with rule vv-2 | variables valued (both sets) | of which tp_ds_* | unresolved | conflict |")
    emit("|---|---|---|---|---|---|---|---|")
    for split in ("dev", "test"):
        for tier in ("controlled", "real_world"):
            k = (split, tier)
            if c[k + ("scenarios",)]:
                emit(f"| {split} | {tier} | {c[k + ('scenarios',)]} | {c[k + ('vv-2',)]} | {c[k + ('valued',)]} | "
                     f"{c[k + ('tp_ds valued',)]} | {c[k + ('unresolved',)]} | {c[k + ('conflict',)]} |")
    emit()
    emit("Leaves by kind (a leaf is one scalar position of a value; per split and tier):")
    for split in ("dev", "test"):
        for tier in ("controlled", "real_world"):
            row = ", ".join(f"`{k}` {n}" for (s, t, k), n in sorted(kinds.items()) if (s, t) == (split, tier))
            if row:
                emit(f"- {split} {tier}: {row}")
    emit()
    emit("Variables by evidence class (a variable counts once per class it records):")
    for split in ("dev", "test"):
        for tier in ("controlled", "real_world"):
            row = ", ".join(f"`{k}` {n}" for (s, t, k), n in sorted(evid.items()) if (s, t) == (split, tier))
            if row:
                emit(f"- {split} {tier}: {row}")
    emit()
    emit("Validation candidates taken (variables with a validation block):")
    for (s, t, taken), n in sorted(cand.items()):
        emit(f"- {s} {t}: {n} x {taken}")
    emit()
    emit("Values equal in both sets (recorded exceptions):")
    for (s, t, why), n in sorted(same.items()):
        emit(f"- {s} {t}: {n} x {why}")
    if not same:
        emit("- none")
    emit()
    emit("Unresolved and conflict reasons (count of variables):")
    for (s, st, r), n in sorted(reasons.items()):
        emit(f"- {s}: {n} x {st}: {r}")
    if not reasons:
        emit("- none")
    emit()
    emit("Dev variables without a value:")
    for row in sorted(dev_un):
        emit(f"- {row}")
    if not dev_un:
        emit("- none")
    emit()


def transform(scs) -> None:
    emit("### D5a-2.3 Data-source transform (D5-08)")
    by_type = collections.Counter()
    n_vars = collections.Counter()
    affected: dict[str, list[str]] = collections.defaultdict(list)
    for split, _p, d in scs:
        ents = [e for e in d.get("host_transform") or [] if e.get("kind") == "data_source_to_variable"]
        for e in ents:
            by_type[(split, e["data_type"])] += 1
            n_vars[split] += 1
        if ents:
            affected[split].append(d["scenario_id"])
    for split in ("dev", "test"):
        if split == "test" and private_root() is None:
            continue
        row = ", ".join(f"`{t}` {n}" for (s, t), n in sorted(by_type.items()) if s == split)
        emit(f"- {split}: blocks removed by type: {row or 'none'}; variables created: {n_vars[split]}; "
             f"scenarios affected: {len(affected[split])}")
    emit(f"- dev scenarios affected: {ids(affected['dev'])}")
    emit()


def screen_rerun(scs) -> None:
    emit("### D5a-2.4 Whole-module S0 screen, re-run after the transform")
    c = collections.Counter()
    stop: list[str] = []
    for split, _p, d in scs:
        if d["source"]["tier"] != "real_world":
            continue
        kind = d["parameters"]["kind"]
        sub = "host" if kind == "host" else ("derived" if d["derived"] else "native")
        mod_dir = REPO_ROOT / "pool" / "terrads" / sub / str(d["module_id"])
        raw = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in sorted(mod_dir.glob("*.tf"))}
        if kind == "host":
            before = {n: graft.neutralise_host_file(n, t)[0] for n, t in sorted(raw.items())}
            after, _r = data_vars.transform(before)
            rb, ra = screen.screen_module(before), screen.screen_module(after)
            res_b, res_a = rb.primary, ra.primary
        else:
            after, _r = data_vars.transform(dict(raw))
            res_b = screen.screen_module(raw, is_native=True).primary
            res_a = screen.screen_module(after, is_native=True).primary
        c[(split, kind, "same" if res_b == res_a else "changed")] += 1
        c[(split, kind, f"after: {res_a}")] += 1
        if kind == "host" and res_a != "accepted":
            stop.append(d["scenario_id"] if split == "dev" else "<test-split scenario>")
    for split in ("dev", "test"):
        for kind in ("host", "native"):
            parts = [f"{k.split(': ')[-1]} {n}" for (s, kd, k), n in sorted(c.items())
                     if s == split and kd == kind and k.startswith("after: ")]
            if parts:
                emit(f"- {split} {kind}: result after the transform: {', '.join(parts)}; same result as before the "
                     f"transform: {c[(split, kind, 'same')]}, changed: {c[(split, kind, 'changed')]}")
    emit("- natives are rejected by design (RW-S0-FUNC, D4b-15); they are not re-selected either.")
    emit(f"- stop list (hosts that fail the screen after the transform): {len(stop)}"
         + (f" ({ids([s for s in stop if s.startswith('tp-')])})" if stop else ""))
    emit()


def _rows(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def feasibility(scs) -> None:
    emit("### D5a-2.5 Feasibility under each value set (D5-04 offline rules unchanged)")
    tier_of = {d["scenario_id"]: d["source"]["tier"] for _s, _p, d in scs}
    priv = private_root()
    for vset in ("primary", "alternate"):
        emit(f"#### Value set: {vset} (`{'variable_values' if vset == 'primary' else 'variable_values_alt'}`)")
        emit("| split | tier | steps | plan JSON | data source needs API | provider tried to call AWS | variable error "
             "| other | median wall s | max wall s |")
        emit("|---|---|---|---|---|---|---|---|---|---|")
        sources = {"dev": REPO_ROOT / "docs" / "d5a2" / f"feasibility_dev_{vset}.csv",
                   "test": priv / f"d5a2_feasibility_test_{vset}.csv" if priv else None}
        causes = collections.Counter()
        dev_fail: list[str] = []
        for split, path in sources.items():
            rows = _rows(path)
            for tier in ("controlled", "real_world"):
                rs = [r for r in rows if tier_of.get(r["scenario_id"]) == tier]
                if not rs:
                    continue
                cnt = collections.Counter(r["error_class"] for r in rs if r["status"] == "failure")
                wall = [float(r["wall_seconds"]) for r in rs if r["wall_seconds"]]
                emit(f"| {split} | {tier} | {len(rs)} | {sum(r['status'] == 'success' for r in rs)} | "
                     f"{cnt['data source needs API']} | {cnt['provider tried to call AWS']} | {cnt['variable error']} | "
                     f"{cnt['other']} | {statistics.median(wall):.1f} | {max(wall):.1f} |")
            for r in rows:
                if r["status"] == "failure":
                    causes[(split, r["error_class"], r["error_cause"])] += 1
                    if split == "dev":
                        dev_fail.append(f"{r['scenario_id']} step {r['step']}: {r['error_class']}; "
                                        f"{r['error_cause']}; `{r['error_first_line'][:160]}`")
        emit()
        emit("Failures by class and cause:")
        for (s, cl, cause), n in sorted(causes.items()):
            emit(f"- {s}: {n} x {cl}: {cause or '(no sub-cause)'}")
        if not causes:
            emit("- none")
        emit()
        emit("Dev failures (first error):")
        for row in sorted(dev_fail):
            emit(f"- {row}")
        if not dev_fail:
            emit("- none")
        emit()
    failed: dict[str, set[tuple[str, str]]] = {"dev": set(), "test": set()}
    for vset in ("primary", "alternate"):
        for split, path in (("dev", REPO_ROOT / "docs" / "d5a2" / f"feasibility_dev_{vset}.csv"),
                            ("test", priv / f"d5a2_feasibility_test_{vset}.csv" if priv else None)):
            failed[split] |= {(r["scenario_id"], r["step"]) for r in _rows(path) if r["status"] == "failure"}
    n_steps = sum(len(v) for v in failed.values())
    n_scen = sum(len({s for s, _ in v}) for v in failed.values())
    emit("#### Step 4 outcome")
    if n_steps:
        emit(f"- Not every step plans offline: {n_steps} steps in {n_scen} scenarios fail under at least one value set "
             f"(dev {len(failed['dev'])} steps, test {len(failed['test'])} steps). As the work package requires, D5a-2 "
             "stopped here: the first error, class and sub-cause are recorded above, and no step was fixed, dropped "
             "or given a fallback. Open D5-C in `docs/D5_DECISIONS.md` records the decision this needs.")
    else:
        emit("- Every step plans offline under both value sets.")
    emit()


def _tier_dirs(root: Path) -> dict[str, str]:
    out = {}
    for p in root.glob("tp-v1-*"):
        if (p / "scenario.json").is_file():
            out[p.name] = json.loads((p / "scenario.json").read_text(encoding="utf-8"))["source"]["tier"]
    return out


def drift() -> None:
    emit(f"### D5a-2.6 Drift against `{BASE_COMMIT}`")
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
    base = Path(os.environ.get("TP_PRIVATE_BASELINE", Path.home() / ".terrapreserve-private-pre-d5a2-regen"))
    priv = private_root()
    if priv is not None and base.is_dir():
        ptiers = _tier_dirs(priv)
        for sid, tier in ptiers.items():
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
    if any(d.get("variable_values_rule") != "vv-2" for _s, _p, d in scs):
        # D5a-3 (D5-10) replaced vv-2 by vv-3: the D5a-2 part of the document describes the records at 5f71c00
        # and is kept as it was; tools/report_d5a3.py writes the D5a-3 part.
        raise SystemExit("the records are no longer vv-2: the D5a-2 part of docs/D5A_FEASIBILITY.md is frozen "
                         "(see tools/report_d5a3.py)")
    head = DOC.read_text(encoding="utf-8")
    head = head.split(MARKER)[0].rstrip("\n") + "\n"
    emit(MARKER)
    emit()
    emit("## D5a-2 measurements (computed by `tools/report_d5a2.py`)")
    emit()
    emit("Value rule vv-2 (D5-07), data-source variables (D5-08), both value sets (D5-06). Every number below is "
         "computed from the repository and, for the test split, from the withheld directory (counts only). "
         "Regenerate with `python tools/report_d5a2.py` (with `TERRAPRESERVE_PRIVATE` set). The D5a part above "
         "describes vv-1 at `e96c017` and is kept as it was.")
    emit()
    decisions()
    value_sets(scs)
    transform(scs)
    screen_rerun(scs)
    feasibility(scs)
    drift()
    DOC.write_text(head + "\n" + "\n".join(OUT) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
