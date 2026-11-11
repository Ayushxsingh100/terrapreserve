"""D4c Step 2 tests: 33 controlled templates, the 23/10 split, per-cell coverage, unchanged counts, the real-world
tier byte-identical to ``49837f2``, the fixed generator self-checks (D4c-01 to D4c-05) and the settled decision
rows (D4c-02).

Test-split ids are never printed (``<test-split scenario>``). Standard library only; no DAIL import.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for sub in ("sources", "pool", "generator", "tests"):
    if str(REPO_ROOT / sub) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / sub))

DEV = REPO_ROOT / "scenarios" / "dev"
FAMILIES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
CLASSES = ["safe", "unsafe"]
OLD_TEST_TEMPLATES = {"tpl-04", "tpl-05", "tpl-07"}
OLD_DEV_TEMPLATES = {"tpl-01", "tpl-02", "tpl-03", "tpl-06", "tpl-08", "tpl-09", "tpl-10"}

# The real-world tier at 49837f2 (measured there): every file of every real-world scenario directory (dev in the
# repository, test in the private split), the real-world test-manifest entries, validation rows and vv-3 search
# entries.
RW_DEV_FILES = (2492, "7e348756a0c7300dd399213e835a992d27ba2122634bd6d92468f1bd03f2a7a7")
RW_PRIVATE_FILES = (1132, "6e5a7c936502df48b2adb79124cb0b126b94e24471815d102749d456c6fb674c")
# Real-world test-manifest entries at 49837f2 without scenario_json_sha256 (D6 changes that hash: v1_role is added
# to each scenario.json; the withheld records themselves are checked by rw_digest with the v1 fields removed).
RW_MANIFEST = (64, "9ede53c5e4370d4a8f30e4e731dbcc763a422d550a5eaecc5ec5165c2e6bc4b4")
RW_VALIDATE_ROWS = (324, "f16a997b8ed4eca407d19cb59255c2fa839518ccac1f9fe24a0d013a88a21498")
RW_VV3_DEV = (144, "7c0eaa7e74fc9790f3d8dd9cc3276f2d99862cbc94969fa26a28a3cfdad19b91")

# The D5b cases the oracle found UNSUPPORTED at step 0 that the screen of 49837f2 accepted.
# The 64 controlled test-split ids at 49837f2 (sorted, newline-joined, sha256): D4c keeps every id on its side.
CONTROLLED_TEST_IDS_49837F2 = (64, "7e7dcfa76a959b1bfe56fb1d7bed7a0dee67cdabc096a6cdc3458bd7942a4429")

D5B_MISSES = {"tp-v1-F2-0250": "unsupported_rules", "tp-v1-F2-0252": "mixed", "tp-v1-F3-0263": "mixed"}


def private_root() -> Path | None:
    p = os.environ.get("TERRAPRESERVE_PRIVATE")
    return Path(p) if p and Path(p).is_dir() else None


def num(sid: str) -> int:
    return int(sid.rsplit("-", 1)[1])


def rw_digest(root: Path) -> tuple[int, str]:
    rows = []
    for p in sorted(root.glob("tp-v1-*")):
        if num(p.name) <= 208:
            continue
        for f in sorted(x for x in p.rglob("*") if x.is_file()):
            data = f.read_bytes()
            if f.name == "scenario.json":
                # D6 adds only v1_role and v1_role_reason (D6-02); without them the record is the 49837f2 bytes
                d = json.loads(data)
                d.pop("v1_role", None)
                d.pop("v1_role_reason", None)
                data = (json.dumps(d, indent=2, sort_keys=True) + "\n").encode()
            rows.append(f"{f.relative_to(root).as_posix()}|{hashlib.sha256(data).hexdigest()}")
    return len(rows), hashlib.sha256("\n".join(rows).encode()).hexdigest()


def controlled(split_roots: bool = True) -> list[tuple[str, Path, dict]]:
    roots = [("dev", DEV)]
    if split_roots and private_root() is not None:
        roots.append(("test", private_root()))
    out = []
    for split, root in roots:
        for p in sorted(root.glob("tp-v1-*")):
            if num(p.name) <= 208 and (p / "scenario.json").is_file():
                out.append((split, p, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


def shown(split: str, sid: str) -> str:
    return sid if split == "dev" else "<test-split scenario>"


def step_text(sd: Path) -> str:
    parts = ["main.tf"] if (sd / "main.tf").is_file() else ["network.tf", "compute.tf", "database.tf"]
    return "\n".join((sd / f).read_text(encoding="utf-8") for f in parts if (sd / f).is_file())


def model_problems(model) -> list[str]:
    """Registry 2.6 MIXED (any direction) and 2.5 TCP from_port > to_port, on a generator model."""
    out = []
    targets: dict[str, set[str]] = {}
    rules = []
    for addr, res in model.resources.items():
        if res.type == "aws_security_group_rule":
            g = str(res.attrs.get("security_group_id", ""))
            targets.setdefault(g[:-3] if g.endswith(".id") else g, set()).add(str(res.attrs.get("type")))
            rules.append((addr, res.attrs))
        elif res.type == "aws_security_group":
            rules += [(f"{addr}#{b.label}", b.attrs) for b in res.blocks if b.label in ("ingress", "egress")]
    for addr, res in model.resources.items():
        if res.type == "aws_security_group" and any(b.label in ("ingress", "egress") for b in res.blocks) \
                and targets.get(addr):
            out.append(f"MIXED {addr}")
    for where, attrs in rules:
        if str(attrs.get("protocol")).lower() in ("tcp", "6") and isinstance(attrs.get("from_port"), int) \
                and isinstance(attrs.get("to_port"), int) and attrs["from_port"] > attrs["to_port"]:
            out.append(f"from_port > to_port {where}")
    return out


class TestD4cTemplates(unittest.TestCase):
    def test_a2_33_templates_and_versions(self) -> None:
        import templates
        from VERSION import VERSION
        self.assertEqual(sorted(templates.TEMPLATES), [f"tpl-{i:02d}" for i in range(1, 34)])
        self.assertEqual(templates.TEMPLATE_VERSION, "tpl-v2.0")
        self.assertTrue(all(t.version == "tpl-v2.0" for t in templates.TEMPLATES.values()))
        self.assertEqual(VERSION, "d4a-9")

    def test_a2_pairwise_axis_distance_at_least_two(self) -> None:
        import templates
        self.assertEqual(len(templates.AXES), 8)
        ids = sorted(templates.TEMPLATES)
        close = []
        for i, a in enumerate(ids):
            ta = templates.TEMPLATES[a]
            for ax, values in templates.AXES.items():
                self.assertIn(getattr(ta, ax), values, f"{a} {ax}")
            for b in ids[i + 1:]:
                if templates.axis_distance(ta, templates.TEMPLATES[b]) < 2:
                    close.append(f"{a}/{b}")
        self.assertEqual(close, [], "template pairs that differ on fewer than 2 axes")
        for ax, values in templates.AXES.items():
            used = {getattr(t, ax) for t in templates.TEMPLATES.values()}
            self.assertEqual(used, set(values), f"axis {ax}: every value is used")
        self.assertFalse(any(t.egress == "db_only" and t.sg_style == "all_inline"
                             for t in templates.TEMPLATES.values()))

    def test_a2_feature_table_is_generated_from_code(self) -> None:
        import templates
        f = REPO_ROOT / "generator" / "templates" / "FEATURES.md"
        self.assertTrue(f.is_file(), "generator/templates/FEATURES.md is missing")
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import make_template_features  # noqa: PLC0415
        self.assertEqual(f.read_text(encoding="utf-8"), make_template_features.render())
        self.assertIn(templates.features_table().splitlines()[0], f.read_text(encoding="utf-8"))

    def test_no_mixed_group_and_no_reversed_ports_in_any_template(self) -> None:
        import templates
        bad = []
        for tid, t in sorted(templates.TEMPLATES.items()):
            for v in ("clean", "sec_001_violated", "sec_002_violated", "sec_003_violated"):
                m, _ = t.instantiate(random.Random(7), variant=v)
                bad += [f"{tid} {v}: {x}" for x in model_problems(m)]
        self.assertEqual(bad, [])

    def test_no_mixed_group_and_no_reversed_ports_in_any_controlled_step(self) -> None:
        import test_d4b_review_round4 as r4  # noqa: PLC0415
        bad, n = [], 0
        for split, p, d in controlled():
            for sd in sorted(p.glob("step_*")):
                n += 1
                m = r4.parse_model(step_text(sd))
                bad += [f"{shown(split, d['scenario_id'])}/{sd.name}: MIXED {g}" for g in r4.mixed_groups(m)]
                bad += [f"{shown(split, d['scenario_id'])}/{sd.name}: {r.holder} from_port > to_port"
                        for r in r4.all_rules(m) if r.protocol in ("tcp", "6") and r.from_port > r.to_port]
        self.assertGreater(n, 0)
        self.assertEqual(bad, [], f"{len(bad)} problems: {bad[:10]}")

    def test_a2_split_23_dev_10_test_with_the_draw_recorded(self) -> None:
        import seed
        import templates
        s = json.loads((REPO_ROOT / "scenarios" / "split.json").read_text(encoding="utf-8"))
        dev, test = set(s["dev_templates"]), set(s["test_templates"])
        self.assertEqual((len(dev), len(test)), (23, 10))
        self.assertFalse(dev & test)
        self.assertEqual(dev | test, set(templates.TEMPLATES))
        self.assertTrue(OLD_TEST_TEMPLATES <= test and OLD_DEV_TEMPLATES <= dev)
        draw = s["d4c_draw"]
        new = [f"tpl-{i}" for i in range(11, 34)]
        order = seed.template_shuffle_order(sorted(new))
        self.assertEqual(draw["candidates"], new)
        self.assertEqual(draw["order"], order)
        self.assertEqual(draw["test"], sorted(order[-7:]))
        self.assertEqual(draw["dev"], sorted(order[:-7]))
        self.assertEqual(test - OLD_TEST_TEMPLATES, set(draw["test"]))
        self.assertEqual(s["seed"], seed.MASTER_SEED)

    def test_a3_per_cell_coverage_and_balance(self) -> None:
        import generate
        import templates
        plan = generate.build_scenario_plan()
        self.assertEqual(len(plan), 208)
        not_serving = [(t, f, c) for t in sorted(templates.TEMPLATES) for f in FAMILIES for c in CLASSES
                       if not generate.serving(t, f, c)]
        feats = (REPO_ROOT / "generator" / "templates" / "FEATURES.md").read_text(encoding="utf-8")
        for t, f, c in not_serving:
            self.assertIn(f"{t} does not serve {f} {c}", feats)
        per_cell = collections.defaultdict(list)
        for it in plan:
            per_cell[(it["family"], it["cls"])].append(it)
            self.assertNotIn((it["template_id"], it["family"], it["cls"]), not_serving)
        for cell, items in per_cell.items():
            tpls = [i["template_id"] for i in items]
            self.assertEqual(len(tpls), len(set(tpls)), f"{cell}: a template used twice in one cell")
        s = json.loads((REPO_ROOT / "scenarios" / "split.json").read_text(encoding="utf-8"))
        for split, key in (("dev", "dev_templates"), ("test", "test_templates")):
            counts = collections.Counter(i["template_id"] for i in plan if i["split"] == split)
            self.assertEqual(set(counts), set(s[key]), f"{split}: every template is used")
            self.assertLessEqual(max(counts.values()) - min(counts.values()), 1, f"{split}: per-template balance")

    def test_a3_controlled_counts_unchanged(self) -> None:
        import generate
        plan = generate.build_scenario_plan()
        want = {"dev target": 7, "test target": 3, "dev reserve": 2, "test reserve": 1}
        for f in FAMILIES:
            for c in CLASSES:
                got = collections.Counter(f"{i['split']} {'reserve' if i['reserve'] else 'target'}"
                                          for i in plan if i["family"] == f and i["cls"] == c)
                self.assertEqual(dict(got), want, f"{f} {c}")
        ids = [i["global_id"] for i in plan]
        self.assertEqual(ids, list(range(1, 209)))
        test_ids = sorted(f"tp-v1-{i['family']}-{i['global_id']:04d}" for i in plan if i["split"] == "test")
        self.assertEqual((len(test_ids), hashlib.sha256("\n".join(test_ids).encode()).hexdigest()),
                         CONTROLLED_TEST_IDS_49837F2, "a controlled id changed side")
        # the committed tier matches the plan (dev: whole records; test: ids in the manifest only)
        dev = {num(d["scenario_id"]): d for _s, _p, d in controlled(split_roots=False)}
        man = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
        test_ids = {num(e["scenario_id"]) for e in man if num(e["scenario_id"]) <= 208}
        for it in plan:
            sid = f"tp-v1-{it['family']}-{it['global_id']:04d}"
            if it["split"] == "dev":
                self.assertIn(it["global_id"], dev, sid)
                d = dev[it["global_id"]]
                self.assertEqual((d["scenario_id"], d["template_id"], d["reserve"], d["intent"]["class"]),
                                 (sid, it["template_id"], it["reserve"], it["cls"]))
            else:
                self.assertIn(it["global_id"], test_ids, "a test-split scenario is missing from the manifest")
        self.assertEqual(len(dev) + len(test_ids), 208)

    def test_controlled_records_carry_the_d4c_versions_and_features(self) -> None:
        import templates
        bad = []
        for split, _p, d in controlled():
            t = templates.TEMPLATES.get(d["template_id"])
            if t is None or d["template_version"] != "tpl-v2.0" or d["generator_version"] != "d4a-9" \
                    or d["parameters"].get("features") != t.features() or d["split"] != split:
                bad.append(shown(split, d["scenario_id"]))
        self.assertEqual(bad, [])

    def test_a5_real_world_tier_byte_identical_to_49837f2(self) -> None:
        self.assertEqual(rw_digest(DEV), RW_DEV_FILES)
        man = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
        rw = [{k: v for k, v in e.items() if k != "scenario_json_sha256"} for e in man if num(e["scenario_id"]) > 208]
        self.assertEqual((len(rw), hashlib.sha256(json.dumps(rw, sort_keys=True).encode()).hexdigest()), RW_MANIFEST)
        with open(REPO_ROOT / "scenarios" / "validate_results.csv", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if num(r["scenario_id"]) > 208]
        self.assertEqual((len(rows), hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()),
                         RW_VALIDATE_ROWS)
        vv = json.loads((REPO_ROOT / "generator" / "vv3" / "dev.json").read_text(encoding="utf-8"))["scenarios"]
        rv = {k: v for k, v in vv.items() if num(k) > 208}
        self.assertEqual((len(rv), hashlib.sha256(json.dumps(rv, sort_keys=True).encode()).hexdigest()), RW_VV3_DEV)
        priv = private_root()
        if priv is None:
            self.skipTest("TERRAPRESERVE_PRIVATE not set: the withheld real-world test split is not checked")
        self.assertEqual(rw_digest(priv), RW_PRIVATE_FILES, "withheld real-world split changed (ids withheld)")

    def test_a6_fixed_self_checks_flag_the_d5b_cases(self) -> None:
        from realworld import modread
        for sid, field in D5B_MISSES.items():
            sd = DEV / sid / "step_0"
            an = modread.analyse({f.name: f.read_text(encoding="utf-8") for f in sd.glob("*.tf")})
            self.assertTrue(getattr(an, field, None), f"{sid}: {field} not flagged")
        base = ('resource "aws_security_group" "g" {\n  name = "g"\n\n  egress {\n    cidr_blocks = ["0.0.0.0/0"]\n'
                '    from_port   = 0\n    protocol    = "-1"\n    to_port     = 0\n  }\n}\n')
        def rule(fp: int, tp: int, g: str) -> str:
            return ('resource "aws_security_group_rule" "r" {\n  cidr_blocks       = ["10.0.0.0/8"]\n'
                    f'  from_port         = {fp}\n  protocol          = "tcp"\n'
                    f'  security_group_id = aws_security_group.{g}.id\n  to_port           = {tp}\n'
                    '  type              = "ingress"\n}\n')
        mixed = modread.analyse({"main.tf": base + rule(22, 22, "g")})
        self.assertEqual(mixed.mixed, ["aws_security_group.g"], "inline egress + separate ingress is MIXED (2.6)")
        self.assertIn("RW-S0-MIXED", mixed.codes)
        sep = 'resource "aws_security_group" "h" {\n  name = "h"\n}\n'
        rev = modread.analyse({"main.tf": sep + rule(443, 22, "h")})
        self.assertTrue(rev.unsupported_rules, "TCP from_port > to_port is UNSUPPORTED (2.5)")
        self.assertIn("RW-S0-UNSUP-RULE", rev.codes)
        ok = modread.analyse({"main.tf": sep + rule(22, 443, "h")})
        self.assertEqual((ok.mixed, ok.unsupported_rules), ([], []))


class TestD4cDecisions(unittest.TestCase):
    def rows(self, name: str) -> dict[str, str]:
        out = {}
        for line in (REPO_ROOT / "docs" / name).read_text(encoding="utf-8").splitlines():
            if line.startswith("| ") and not line.startswith(("| ID", "|---")):
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                if len(c) == 5:
                    out[c[0]] = c[2]
        return out

    def test_a1_rows_settled(self) -> None:
        superseded = {"D4-03", "D4-04", "D4-05"}  # by D4c-01, D4c-03, D4c-04 (user, 10 Nov 2026)
        for f in ("D4_DECISIONS.md", "D4B_DECISIONS.md", "D5_DECISIONS.md"):
            rows = self.rows(f)
            self.assertFalse([r for r, s in rows.items() if s == "Open"], f)
            self.assertFalse([r for r, s in rows.items() if s == "Proposed"], f)
            if f == "D4_DECISIONS.md":
                self.assertEqual({r for r, s in rows.items() if s == "Superseded"}, superseded)
        d4c = self.rows("D4C_DECISIONS.md")
        self.assertEqual({k: v for k, v in d4c.items() if k in ("D4c-01", "D4c-02")},
                         {"D4c-01": "Decided", "D4c-02": "Decided"})
        rest = {k: v for k, v in d4c.items() if k not in ("D4c-01", "D4c-02")}
        # D4c-03 to D4c-06 were Proposed until D6-01 (user, 11 Nov 2026) settled them as built
        self.assertTrue(rest and set(rest.values()) == {"Decided"})


if __name__ == "__main__":
    unittest.main()
