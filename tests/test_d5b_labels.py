"""D5b Step 6 (A3, D5-17, D5-20, D5-21): the labels written into the scenarios, checked from the records alone.

Runs over ``scenarios/dev`` and, when ``TERRAPRESERVE_PRIVATE`` names an existing directory, over the withheld test
split (ids never printed: failures name only counts). Expected structure from the work package (D0 Decision 6,
D0 gate 9, D5-17, D5-20, D5-21); nothing here recomputes a label. Standard library only.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INVS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001")
RESULTS = {"PASS", "FAIL", "UNKNOWN", "UNSUPPORTED", "VERIFIER_ERROR"}
KINDS = {"unlabelable", "value_dependent", "s0_not_clean"}
VERSION_KEYS = {"terraform", "provider_hashicorp_aws", "checkov", "oracle", "generator", "value_rule", "registry",
                "value_set"}


def roots() -> list[tuple[str, Path]]:
    out = [("dev", REPO_ROOT / "scenarios" / "dev")]
    env = os.environ.get("TERRAPRESERVE_PRIVATE")
    if env and Path(env).is_dir():
        out.append(("test", Path(env)))
    else:
        print("[d5b] TERRAPRESERVE_PRIVATE is not set to an existing directory: test-split checks skipped.")
    return out


def scenarios() -> list[tuple[str, dict]]:
    out = []
    for split, root in roots():
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append((split, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


def shown(split: str, sid: str) -> str:
    return sid if split == "dev" else "(a test scenario)"


class TestD5bLabels(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scs = scenarios()

    def test_a3_every_scenario_is_labelled_or_excluded_with_a_reason(self) -> None:
        bad = []
        for split, d in self.scs:
            sid = shown(split, d["scenario_id"])
            ex = d.get("excluded_from_v1")
            if ex:
                if any(d.get(f) is not None for f in ("labels", "gt_class", "oracle")):
                    bad.append(f"{sid}: excluded but carries ground truth")
                if "kind" in ex and (ex["kind"] not in KINDS or not str(ex.get("reason", "")).strip()):
                    bad.append(f"{sid}: exclusion kind {ex.get('kind')!r} without a reason")
                continue
            if d.get("gt_class") not in ("safe", "unsafe"):
                bad.append(f"{sid}: gt_class {d.get('gt_class')!r}")
            labels = d.get("labels") or []
            if [lab.get("step") for lab in labels] != [s["step"] for s in d["steps"]]:
                bad.append(f"{sid}: labels do not cover every step")
                continue
            for lab in labels:
                if set(lab["invariant_truth"]) != set(INVS) or not set(lab["invariant_truth"].values()) <= RESULTS:
                    bad.append(f"{sid} step {lab['step']}: invariant_truth incomplete")
                if not set(lab["oracle_affected"]) <= set(INVS):
                    bad.append(f"{sid} step {lab['step']}: oracle_affected outside the invariants")
            v = (d.get("oracle") or {}).get("versions") or {}
            if set(v) != VERSION_KEYS or any(v[k] in (None, "") for k in VERSION_KEYS):
                bad.append(f"{sid}: versions {sorted(v)}")
            elif (v["terraform"], v["provider_hashicorp_aws"], v["checkov"], v["oracle"], v["registry"]) != \
                    ("1.15.8", "6.53.0", "3.3.30", "oracle-1.0", "registry-v1.0") \
                    or v["generator"] != d["generator_version"] or v["value_rule"] != d["variable_values_rule"]:
                bad.append(f"{sid}: versions differ from the pins")
            if not isinstance((d.get("oracle") or {}).get("disagreements"), list):
                bad.append(f"{sid}: no oracle.disagreements list")
        self.assertEqual(bad, [], f"{len(bad)} problems, first 10: {bad[:10]}")

    def test_d5_17_target_safe_and_d5_21_s0(self) -> None:
        bad = []
        for split, d in self.scs:
            if not d.get("labels"):
                continue
            sid = shown(split, d["scenario_id"])
            t = d["target"].get("invariant_id") if d["target"].get("kind") == "repair" else None
            labels = d["labels"]
            n = len(labels) - 1
            s0 = labels[0]["invariant_truth"]
            if labels[0]["target_safe"] is not None or labels[0]["oracle_affected"] != []:
                bad.append(f"{sid}: step 0 target_safe or oracle_affected set")
            if any(s0[i] != ("FAIL" if i == t else "PASS") for i in INVS):
                bad.append(f"{sid}: S0 not clean but labelled (D5-21)")
            for lab in labels[1:]:
                k, r = lab["step"], lab["invariant_truth"]
                want = all(r[i] == "PASS" for i in INVS if i != t) and (t is None or r[t] == "PASS" or k < n)
                if lab["target_safe"] is not want:
                    bad.append(f"{sid} step {k}: target_safe {lab['target_safe']}, D5-17 gives {want}")
        self.assertEqual(bad, [], f"{len(bad)} problems, first 10: {bad[:10]}")

    def test_d5_11_gt_class_agrees_with_the_labels(self) -> None:
        bad = []
        for split, d in self.scs:
            if not d.get("labels"):
                continue
            t = d["target"].get("invariant_id") if d["target"].get("kind") == "repair" else None
            r = [lab["invariant_truth"] for lab in d["labels"]]
            n = len(r) - 1
            fail = any(r[k][i] == "FAIL" and not (i == t and k < n) for k in range(1, n + 1) for i in INVS)
            want = "unsafe" if fail or (t is not None and r[n][t] != "PASS") else "safe"
            if d["gt_class"] != want:
                bad.append(f"{shown(split, d['scenario_id'])}: gt_class {d['gt_class']}, D5-11 gives {want}")
        self.assertEqual(bad, [], f"{len(bad)} problems, first 10: {bad[:10]}")

    def test_no_test_split_id_in_committed_documents(self) -> None:
        manifest = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
        ids = {e["scenario_id"] for e in manifest}
        docs = [REPO_ROOT / "docs" / "D5_REPORT.md", REPO_ROOT / "DATASHEET.md", *sorted((REPO_ROOT / "docs" / "d5b").glob("*")),
                # D4c: its decisions, the template feature table and its evidence files
                REPO_ROOT / "docs" / "D4C_DECISIONS.md", REPO_ROOT / "generator" / "templates" / "FEATURES.md",
                REPO_ROOT / "docs" / "D5_CARRYOVER.md", REPO_ROOT / "scenarios" / "README.md",
                *sorted((REPO_ROOT / "docs" / "d4c").glob("*"))]
        hits = [f"{p.name}: {n}" for p in docs if p.is_file() for n in
                [sum(1 for i in ids if i in p.read_text(encoding="utf-8"))] if n]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
