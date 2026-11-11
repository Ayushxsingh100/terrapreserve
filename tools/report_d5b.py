#!/usr/bin/env python3
"""Computed part of ``docs/D5_REPORT.md`` (D5b Steps 6 and 7). Every id, count and status is computed here.

Reads the repository (``scenarios/dev``, ``docs/D5_DECISIONS.md``, ``docs/d5b/``), the oracle's run records
(dev: ``~/.terrapreserve-cache/d5b-records``; test: ``$TERRAPRESERVE_PRIVATE/d5b-records``) and, for the test
split, the withheld directory. Test split: counts only, never an id. Writes the part of ``docs/D5_REPORT.md``
below its marker line, keeping the hand-written part above it.

The generator self-check comparison imports the D4b self-check evaluators (``tests/test_d4b_review_round4.py``
and ``generator/realworld/modread.py``). They are compared with the oracle; they never set a label (D5b Do Not Do),
and ``oracle/`` never imports them (D5-03). Standard library only.
"""

from __future__ import annotations

import collections
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

DOC = REPO_ROOT / "docs" / "D5_REPORT.md"
MARKER = "<!-- computed below by tools/report_d5b.py; the part above is written by hand -->"
CACHE = Path.home() / ".terrapreserve-cache"
INVS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001")
TIERS = ("controlled", "real_world")
CLASSES = ("safe", "unsafe")
OUT: list[str] = []


def emit(line: str = "") -> None:
    OUT.append(line)


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


def record(split: str, sid: str) -> dict | None:
    d = (CACHE / "d5b-records") if split == "dev" else (private_root() / "d5b-records")
    f = d / f"{sid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def kind_of(d: dict) -> str | None:
    ex = d.get("excluded_from_v1")
    if not ex:
        return None
    return ex.get("kind") or "unplannable"


def tier(d: dict) -> str:
    return d["source"]["tier"]


# ---------------------------------------------------------------------------------------------------------------
# Oracle reasons, from the run records (evidence of the primary set)
# ---------------------------------------------------------------------------------------------------------------


def why(ev: dict, inv: str) -> str:
    r = ev[inv]
    o = r.get("observations") or {}
    res = r["result"]
    if inv == "INV-FUNC-001":
        return f"6.4 row {o.get('row')}: {o.get('reason')}"
    if inv == "INV-SEC-003":
        pub = [x["address"] for x in o.get("db_instances", []) if x.get("value") is True]
        unr = [x["address"] for x in o.get("db_instances", []) if "unresolved" in x]
        return {"FAIL": f"5.4: publicly_accessible true on {pub}", "UNKNOWN": f"5.4: unresolved on {unr}"}.get(
            res, "5.4: no publicly accessible aws_db_instance")
    if res == "FAIL":
        return "3.4: violates(g) for " + ", ".join(sorted({v["group"] for v in o.get("violations", [])}))
    if res == "UNSUPPORTED":
        parts = []
        if o.get("mixed_groups"):
            parts.append(f"MIXED {o['mixed_groups']}")
        if o.get("retained_inline_groups"):
            parts.append(f"RETAINED-INLINE {o['retained_inline_groups']}")
        if o.get("unsupported_rules"):
            parts.append("2.5 " + "; ".join(f"{u['rule']}: {u['reason']}" for u in o["unsupported_rules"]))
        if o.get("relevant_unsupported_resources"):
            parts.append(f"2.7 {o['relevant_unsupported_resources']}")
        return "3.4 UNSUPPORTED: " + ("; ".join(parts) or "validate failed (2.8)")
    if res == "UNKNOWN":
        return f"3.4 UNKNOWN: indeterminate rules {o.get('indeterminate_rules')}"
    return "3.4: no group violates"


# ---------------------------------------------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------------------------------------------


def decisions() -> None:
    emit("### Decision rows (`docs/D5_DECISIONS.md`, id and status as written)")
    emit()
    rows = []
    for line in (REPO_ROOT / "docs" / "D5_DECISIONS.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| D5-") or line.startswith("| Open D5-"):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            rows.append(f"{c[0]} {c[2]}")
    emit("; ".join(rows))
    emit()


def versions(scs) -> None:
    emit("### Versions recorded in the labels (D0 gate 9)")
    emit()
    c = collections.Counter()
    for split, _p, d in scs:
        if d.get("oracle"):
            c[(split, json.dumps(d["oracle"]["versions"], sort_keys=True))] += 1
    for (split, v), n in sorted(c.items()):
        emit(f"- {split}: {n} scenarios: `{v}`")
    emit()


def plannable() -> None:
    emit("### A5: plannable set against D5a-3")
    emit()
    emit("D5b run (both tiers; its controlled part is superseded by the D4c relabel below, its real-world part "
         "stands because the real-world tier is unchanged):")
    emit()
    docs = {"dev": json.loads((REPO_ROOT / "docs" / "d5b" / "plannable_dev.json").read_text(encoding="utf-8"))}
    if private_root() is not None and (private_root() / "d5b_plannable_test.json").is_file():
        docs["test"] = json.loads((private_root() / "d5b_plannable_test.json").read_text(encoding="utf-8"))
    for split, doc in docs.items():
        emit(f"- {split}: {doc['counts']}; differences from D5a-3: {doc['differences']}")
    emit()
    c4 = REPO_ROOT / "docs" / "d4c" / "plannable_controlled_dev.json"
    if c4.is_file():
        emit("D4c relabel of the controlled tier (D4c-06; D5a-3 feasibility re-measured for the controlled tier):")
        emit()
        docs = {"dev": json.loads(c4.read_text(encoding="utf-8"))}
        tp = private_root() / "d5b_plannable_controlled_test.json" if private_root() is not None else None
        if tp is not None and tp.is_file():
            docs["test"] = json.loads(tp.read_text(encoding="utf-8"))
        for split, doc in docs.items():
            emit(f"- {split} controlled: {doc['counts']}; differences from D5a-3: {doc['differences']}")
        emit()


def steps_labelled(scs) -> None:
    emit("### Steps labelled (each under both value sets, D5-18)")
    emit()
    emit("| split | tier | scenarios labelled | steps labelled per value set | steps evaluated per value set |")
    emit("|---|---|---|---|---|")
    c = collections.Counter()
    for split, _p, d in scs:
        k = kind_of(d)
        if k is None:
            c[(split, tier(d), "sc")] += 1
            c[(split, tier(d), "lab")] += len(d["steps"])
        if k != "unplannable":
            c[(split, tier(d), "ev")] += len(d["steps"])
    for split in sorted({s for s, _p, _d in scs}):
        for t in TIERS:
            emit(f"| {split} | {t} | {c[(split, t, 'sc')]} | {c[(split, t, 'lab')]} | {c[(split, t, 'ev')]} |")
    emit()


def exclusions(scs) -> None:
    emit("### Exclusions by reason (D5-20; dev ids, test counts)")
    emit()
    by = collections.defaultdict(list)
    for split, _p, d in scs:
        k = kind_of(d)
        if k:
            by[(split, k)].append(d)
    for split in sorted({s for s, _p, _d in scs}):
        for k in ("unplannable", "unlabelable", "value_dependent", "s0_not_clean"):
            ds = by.get((split, k), [])
            if split == "dev":
                ids = ", ".join(f"{d['scenario_id']} ({tier(d)})" for d in ds)
                emit(f"- dev {k}: {len(ds)}" + (f": {ids}" if ids else ""))
                if k != "unplannable":
                    for d in ds:
                        emit(f"  - {d['scenario_id']}: {d['excluded_from_v1']['reason']}")
            else:
                t = collections.Counter(tier(d) for d in ds)
                emit(f"- test {k}: {len(ds)} ({dict(sorted(t.items()))})")
    emit()


def gt_counts(scs) -> None:
    emit("### gt_class per family x intent class x split x tier")
    emit()
    emit("| family | intent class | split | tier | scenarios | gt safe | gt unsafe | excluded |")
    emit("|---|---|---|---|---|---|---|---|")
    c = collections.defaultdict(collections.Counter)
    for split, _p, d in scs:
        key = (d["family"], d["intent"]["class"], split, tier(d))
        c[key]["n"] += 1
        c[key][d["gt_class"] if d.get("gt_class") else "excluded"] += 1
    tot = collections.Counter()
    for key in sorted(c):
        x = c[key]
        for f in ("n", "safe", "unsafe", "excluded"):
            tot[(key[2], f)] += x[f]
        emit(f"| {' | '.join(key)} | {x['n']} | {x['safe']} | {x['unsafe']} | {x['excluded']} |")
    emit()
    for split in sorted({k[2] for k in c}):
        emit(f"- {split} total: {tot[(split, 'n')]} scenarios, gt safe {tot[(split, 'safe')]}, gt unsafe "
             f"{tot[(split, 'unsafe')]}, excluded {tot[(split, 'excluded')]}")
    emit()


def invariance_s0(scs) -> None:
    emit("### Invariance (D5-18) and S0 gate (D5-21)")
    emit()
    for split in sorted({s for s, _p, _d in scs}):
        n_eval = sum(1 for s, _p, d in scs if s == split and kind_of(d) != "unplannable")
        vd = sum(1 for s, _p, d in scs if s == split and kind_of(d) == "value_dependent")
        s0 = sum(1 for s, _p, d in scs if s == split and kind_of(d) == "s0_not_clean")
        emit(f"- {split}: {n_eval} scenarios evaluated under both value sets; value_dependent {vd}; s0_not_clean {s0}")
    emit()


def checkov(scs) -> None:
    emit("### Checkov 3.3.30, advisory (D5-19)")
    emit()
    c = collections.Counter()
    steps = collections.Counter()
    ex = []
    errs = collections.Counter()
    for split, _p, d in scs:
        if not d.get("oracle"):
            continue
        steps[split] += len(d["steps"])
        rec = record(split, d["scenario_id"]) or {}
        errs[split] += len(rec.get("checkov_errors") or [])
        for x in d["oracle"]["disagreements"]:
            c[(split, x["invariant"], x["oracle"], x["checkov"])] += 1
            if split == "dev" and len(ex) < 12:
                ex.append(f"{d['scenario_id']} step {x['step']} {x['invariant']}: oracle {x['oracle']}, Checkov "
                          f"{x['checkov']} (failed resources {x['checkov_failed_resources']})")
    for split in sorted(steps):
        emit(f"- {split}: {steps[split]} labelled steps; Checkov did not run on {errs[split]}")
    if not c:
        emit("- disagreements: none")
    for (split, inv, o, k), n in sorted(c.items()):
        emit(f"- {split} {inv}: oracle {o}, Checkov {k}: {n}")
    if ex:
        emit("- dev examples:")
        for e in ex:
            emit(f"  - {e}")
    emit()


def intent(scs) -> None:
    emit("### Intent comparison (Step 7; the oracle's label stands)")
    emit()
    emit("Per labelled scenario: oracle `gt_class` against `intent.class`, and the invariants FAIL at the last step "
         "(F8: at any step k >= 1, except the repair target before the last step, as in D5-11) against `intent.breaks`. "
         "The reason is the registry condition that fired (3.4, 5.4, "
         "6.4 row) at the step concerned, primary value set.")
    emit()
    cnt = collections.Counter()
    for split, _p, d in scs:
        if not d.get("gt_class"):
            continue
        rec = record(split, d["scenario_id"])
        ev = rec["per_set"]["primary"]["evidence"]
        res = [lab["invariant_truth"] for lab in d["labels"]]
        n = len(res) - 1
        t = d["target"].get("invariant_id") if d["target"].get("kind") == "repair" else None
        if d["family"] == "F8":
            # any step k >= 1, with the D5-11 exception: the repair target may be FAIL at steps 1..n-1
            fails = {inv for k in range(1, n + 1) for inv in INVS
                     if res[k][inv] == "FAIL" and not (inv == t and k < n)}
        else:
            fails = {inv for inv in INVS if res[n][inv] == "FAIL"}
        breaks = set(d["intent"]["breaks"])
        cls_ok = d["gt_class"] == d["intent"]["class"]
        brk_ok = fails == breaks
        cnt[(split, tier(d), "scenarios")] += 1
        if cls_ok and brk_ok:
            continue
        cnt[(split, tier(d), "class differs" if not cls_ok else "breaks differ only")] += 1
        if split == "dev":
            parts = []
            for inv in sorted(fails ^ breaks):
                k = n
                if d["family"] == "F8" and inv in fails:
                    k = next(k for k in range(1, n + 1) if res[k][inv] == "FAIL" and not (inv == t and k < n))
                parts.append(f"{inv} {res[k][inv]} at step {k} ({why(ev[k], inv)})")
            emit(f"- {d['scenario_id']} ({tier(d)}): gt {d['gt_class']}, intent {d['intent']['class']}; FAIL "
                 f"{sorted(fails)}, breaks {sorted(breaks)}: " + "; ".join(parts))
    if not any(k[2] != "scenarios" for k in cnt):
        emit("- disagreements: none (dev and test)")
    emit()
    for key, n in sorted(cnt.items()):
        emit(f"- {' '.join(key)}: {n}")
    emit()


def selfcheck_verdicts(p: Path, d: dict) -> list[dict[str, str]]:
    """The D4b round-4/5 self-check evaluators' result per step and invariant (n/a where they give none)."""
    import test_d4b_review_round4 as r4  # noqa: PLC0415
    from realworld import modread  # noqa: PLC0415
    sc = r4.Sc(split="x", dir=p, data=d)
    out = []
    models = None
    if sc.model_file() is not None:
        try:
            models = sc.models()
            s_addr, d_addr = r4.endpoints(models[0])
        except Exception:  # noqa: BLE001  (UnsupportedForm or a parse error: no FUNC verdict)
            models = None
    for k, sd in enumerate(sc.step_dirs()):
        an = modread.analyse({f.name: f.read_text(encoding="utf-8") for f in sorted(sd.glob("*.tf"))})
        v: dict[str, str] = {}
        for inv in ("INV-SEC-001", "INV-SEC-002"):
            unsup = an.mixed or an.unsupported_types or getattr(an, "unsupported_rules", [])
            v[inv] = ("FAIL" if an.violations.get(inv) else "UNSUPPORTED" if unsup
                      else "UNKNOWN" if an.possible.get(inv) else "PASS")
        v["INV-SEC-003"] = ("FAIL" if an.violations.get("INV-SEC-003") else "UNKNOWN" if an.unresolved_public
                            else "PASS")
        v["INV-FUNC-001"] = "n/a"
        if models is not None:
            try:
                v["INV-FUNC-001"] = r4.evaluate_func(models[k], s_addr, d_addr).status
            except Exception:  # noqa: BLE001
                v["INV-FUNC-001"] = "n/a"
        out.append(v)
    return out


def selfcheck(scs) -> None:
    emit("### Generator self-check comparison (Step 7; `docs/D5_CARRYOVER.md` 5: findings to report)")
    emit()
    emit("The D4b round-4/5 self-check evaluators against the oracle (primary value set), per step and invariant, "
         "over every scenario the oracle evaluated (D5a-3 exclusions left out). Self-check result: "
         "INV-SEC-001/002 from `modread.analyse` over all `.tf` files of the step (a violation is FAIL; a MIXED "
         "group, a TCP rule with from_port > to_port or a relevant-unsupported type is UNSUPPORTED; `possible` is "
         "UNKNOWN; else PASS). Since D4c the reader is the fixed one (D4c-05: registry 2.5 and MIXED in any "
         "direction); in D5b, with the reader of 49837f2, F2-0250, F2-0252 and F3-0263 were self-check misses "
         "at steps 0 and 1 (oracle UNSUPPORTED, self-check PASS). INV-SEC-003 "
         "likewise (unresolved `publicly_accessible` is UNKNOWN); INV-FUNC-001 from `evaluate_func` of round 4 "
         "(controlled and grafted scenarios; n/a elsewhere or when it rejects the form).")
    emit()
    cnt = collections.Counter()
    dev_lines = []
    for split, p, d in scs:
        if kind_of(d) == "unplannable":
            continue
        rec = record(split, d["scenario_id"])
        pr = rec["per_set"]["primary"]
        if "results" not in pr:
            continue
        sv = selfcheck_verdicts(p, d)
        for k, (o, s) in enumerate(zip(pr["results"], sv)):
            for inv in INVS:
                cnt[(split, tier(d), inv, "compared" if s[inv] != "n/a" else "n/a")] += 1
                if s[inv] in ("n/a", o[inv]):
                    continue
                cnt[(split, tier(d), inv, f"oracle {o[inv]} / self-check {s[inv]}")] += 1
                if split == "dev":
                    miss = " (self-check miss at S0: the self-check accepted the host)" if k == 0 and \
                        s[inv] == "PASS" else ""
                    dev_lines.append(f"- {d['scenario_id']} step {k} {inv}: oracle {o[inv]}, self-check {s[inv]}; "
                                     f"oracle: {why(pr['evidence'][k], inv)}{miss}")
    for line in dev_lines:
        emit(line)
    if not dev_lines:
        emit("- dev: no disagreement")
    emit()
    for key, n in sorted(cnt.items()):
        emit(f"- {' '.join(key)}: {n}")
    emit()


def yields(scs) -> None:
    emit("### Yield table (by oracle gt_class) and the D0 Decision 3 fill")
    emit()
    emit("Per family x class x split x tier. *targets*: scenarios assigned as targets (not reserves) with that intent "
         "class; *labelled*: scenarios (targets and reserves) whose oracle `gt_class` is that class; *excluded*: by "
         "reason, by intent class. *short*: targets minus labelled, when positive. *fill*: for a real-world short "
         "cell, the controlled scenarios of the same family x class x split it would need (D0 Decision 3, D5-09 "
         "amended); *controlled surplus*: labelled minus targets of that controlled cell. D6 does the filling.")
    emit()
    emit("| family | class | split | tier | targets | reserves | labelled | excluded (by reason) | short | fill from "
         "controlled | controlled surplus |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")
    cells = collections.defaultdict(collections.Counter)
    for split, _p, d in scs:
        key = (d["family"], d["intent"]["class"], split, tier(d))
        cells[key]["reserves" if d["reserve"] else "targets"] += 1
        k = kind_of(d)
        if k:
            cells[key][f"x:{k}"] += 1
        if d.get("gt_class"):
            cells[(d["family"], d["gt_class"], split, tier(d))]["labelled"] += 1
    tot = collections.Counter()
    for key in sorted(cells):
        fam, cls, split, t = key
        c = cells[key]
        short = max(0, c["targets"] - c["labelled"])
        ctrl = cells.get((fam, cls, split, "controlled"), collections.Counter())
        surplus = ctrl["labelled"] - ctrl["targets"]
        fill = short if t == "real_world" else 0
        xs = ", ".join(f"{k[2:]} {n}" for k, n in sorted(c.items()) if k.startswith("x:")) or "0"
        for f in ("targets", "reserves", "labelled"):
            tot[(split, t, f)] += c[f]
        tot[(split, t, "short")] += short
        emit(f"| {fam} | {cls} | {split} | {t} | {c['targets']} | {c['reserves']} | {c['labelled']} | {xs} | {short} "
             f"| {fill if t == 'real_world' else '-'} | {surplus if t == 'real_world' else '-'} |")
    emit()
    for split in sorted({k[2] for k in cells}):
        for t in TIERS:
            emit(f"- {split} {t}: targets {tot[(split, t, 'targets')]}, reserves {tot[(split, t, 'reserves')]}, "
                 f"labelled {tot[(split, t, 'labelled')]}, short {tot[(split, t, 'short')]}")
    emit()


def controlled_d4c(scs) -> None:
    """D4c: the controlled tier after the relabel (33 templates)."""
    emit("### D4c: controlled tier, 33 templates (D4c-01 to D4c-06)")
    emit()
    ctl = [(s, d) for s, _p, d in scs if tier(d) == "controlled"]
    gens = collections.Counter((s, d["generator_version"], d["template_version"]) for s, d in ctl)
    emit("- generator and template versions: " + "; ".join(f"{s} {g} {t}: {n}" for (s, g, t), n in sorted(gens.items())))
    per = collections.Counter((s, d["template_id"]) for s, d in ctl)
    for split in ("dev", "test"):
        row = [f"{t} {n}" for (s, t), n in sorted(per.items()) if s == split]
        if row:
            emit(f"- {split} scenarios per template: " + ", ".join(row))
    f5 = collections.Counter()
    for split, _p, d in scs:
        if d["family"] == "F5" and any(r["operator"].startswith("op_f5_db_sg_replacement")
                                       for r in d["mutation_record"]):
            f5[(tier(d), split, d["intent"]["class"])] += 1
    emit("- F5 scenarios using the SG-name replacement operator (`op_f5_db_sg_replacement_safe`/`_unsafe`), "
         "by tier, split, intent class: " + ("; ".join(f"{' '.join(k)}: {n}" for k, n in sorted(f5.items())) or "none"))
    ex = collections.Counter((s, kind_of(d) or "labelled") for s, d in ctl)
    emit("- controlled outcome by split: " + "; ".join(f"{s} {k}: {n}" for (s, k), n in sorted(ex.items())))
    emit()


def main() -> None:
    scs = load()
    text = DOC.read_text(encoding="utf-8") if DOC.is_file() else MARKER + "\n"
    head = text.split(MARKER)[0].rstrip("\n") + "\n"
    emit(MARKER)
    emit()
    emit("## Computed results (`tools/report_d5b.py`)")
    emit()
    emit("Regenerate with `python tools/report_d5b.py` with `TERRAPRESERVE_PRIVATE` set and the run records in "
         "place. Test split: counts only." + ("" if private_root() else " (Test split not available: dev only.)"))
    emit()
    decisions()
    versions(scs)
    plannable()
    steps_labelled(scs)
    exclusions(scs)
    gt_counts(scs)
    invariance_s0(scs)
    checkov(scs)
    intent(scs)
    selfcheck(scs)
    yields(scs)
    controlled_d4c(scs)
    DOC.write_text(head + "\n" + "\n".join(OUT) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {DOC} ({len(OUT)} lines)")


if __name__ == "__main__":
    main()
