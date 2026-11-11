"""D6 tests: decision rows, the target selection rule (D6-02), v1_role on every scenario, exactly 320 targets,
the freeze-gate checker on planted failures (D6-03), the frozen manifests (D6-04), the evidence archive (D6-05),
and steps and labels unchanged against ``8db6278`` (A5).

Test-split ids are never printed. Fake secrets are built at runtime (CLAUDE.md rule 6). Standard library only;
no DAIL import.
"""

from __future__ import annotations

import collections
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for sub in ("sources", "pool", "generator", "tools"):
    if str(REPO_ROOT / sub) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / sub))

DEV = REPO_ROOT / "scenarios" / "dev"
INVS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001")
FAMILIES = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")

# Digests at 8db6278 (computed there): every file of every scenario directory except scenario.json, and every
# scenario.json without the D6 fields v1_role and v1_role_reason (canonical JSON), dev and withheld test split;
# and every step content hash of scenarios/test_manifest.json.
BASE_DEV_FILES = (3627, "2e5c52e1334114a63888ecab239c6dbd06c57726f301017f9f2c2c96c54b9ce3")
BASE_DEV_JSON = (288, "22bfff27f101c0c649e8c47f03655a08d02294ede354b12dd79caa83cc108102")
BASE_TEST_FILES = (1593, "5823179c6643a092aefeeb4c437c8cfbf854c91d77e9f86213d2fac10eedaecb")
BASE_TEST_JSON = (128, "bbb092b9b0adc78f2ceef12fee99b9ea62e171a6305c4cfda2df9f99395c9702")
BASE_MANIFEST_STEPS = (283, "7749f7f1cc6f9f41fad3441130a63243dbd8a48fca6ed3bf9560d3d3b4637ee6")

# D6-02 worked by hand from the dev records at 8db6278 (excluded real-world targets per cell, the cell's labelled
# reserves in id order, then the lowest-numbered labelled controlled reserve of the same family x class x split).
EXPECTED_DEV_SWAPS = {
    # excluded target -> replacement
    "tp-v1-F1-0228": "tp-v1-F1-0232",
    "tp-v1-F2-0250": "tp-v1-F2-0258", "tp-v1-F2-0252": "tp-v1-F2-0259", "tp-v1-F2-0254": "tp-v1-F2-0050",
    "tp-v1-F3-0263": "tp-v1-F3-0272", "tp-v1-F3-0266": "tp-v1-F3-0063",
    "tp-v1-F5-0327": "tp-v1-F5-0336", "tp-v1-F5-0330": "tp-v1-F5-0128",
    "tp-v1-F6-0342": "tp-v1-F6-0349", "tp-v1-F6-0344": "tp-v1-F6-0350",
    "tp-v1-F7-0369": "tp-v1-F7-0375", "tp-v1-F7-0378": "tp-v1-F7-0388",
    "tp-v1-F8-0393": "tp-v1-F8-0401", "tp-v1-F8-0406": "tp-v1-F8-0414",
}
EXPECTED_DEV_FROM_CONTROLLED = {"tp-v1-F2-0050", "tp-v1-F3-0063", "tp-v1-F5-0128"}  # F2 unsafe, F3 safe, F5 unsafe
EXPECTED_DEV_EXCLUDED_RESERVES = {"tp-v1-F1-0219", "tp-v1-F1-0220", "tp-v1-F3-0271", "tp-v1-F3-0284", "tp-v1-F5-0337"}


def private_root() -> Path | None:
    p = os.environ.get("TERRAPRESERVE_PRIVATE")
    return Path(p) if p and Path(p).is_dir() else None


def scenarios(root: Path) -> list[tuple[Path, dict]]:
    return [(p, json.loads((p / "scenario.json").read_text(encoding="utf-8")))
            for p in sorted(root.glob("tp-v1-*")) if (p / "scenario.json").is_file()]


def digests(root: Path) -> tuple[tuple[int, str], tuple[int, str]]:
    files, jsons = [], []
    for p, d in scenarios(root):
        d = dict(d)
        d.pop("v1_role", None)
        d.pop("v1_role_reason", None)
        jsons.append(f"{p.name}|{hashlib.sha256((json.dumps(d, indent=2, sort_keys=True) + chr(10)).encode()).hexdigest()}")
        for f in sorted(x for x in p.rglob("*") if x.is_file() and x.name != "scenario.json"):
            files.append(f"{f.relative_to(root).as_posix()}|{hashlib.sha256(f.read_bytes()).hexdigest()}")

    def h(r: list[str]) -> tuple[int, str]:
        return len(r), hashlib.sha256("\n".join(r).encode()).hexdigest()
    return h(files), h(jsons)


def rec(sid: str, split: str, tier: str, fam: str, cls: str, reserve: bool, gt: str | None, ex: str | None) -> dict:
    return {"scenario_id": sid, "split": split, "tier": tier, "family": fam, "intent_class": cls,
            "reserve": reserve, "oracle_class": gt, "excluded": ex}


class TestD6Decisions(unittest.TestCase):
    def rows(self, name: str) -> dict[str, str]:
        out = {}
        for line in (REPO_ROOT / "docs" / name).read_text(encoding="utf-8").splitlines():
            if line.startswith("| ") and not line.startswith(("| ID", "|---")):
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                if len(c) == 5:
                    out[c[0]] = c[2]
        return out

    def test_a1_decision_rows(self) -> None:
        d6 = self.rows("D6_DECISIONS.md")
        self.assertEqual({k: d6.get(k) for k in ("D6-01", "D6-02")}, {"D6-01": "Decided", "D6-02": "Decided"})
        rest = {k: v for k, v in d6.items() if k not in ("D6-01", "D6-02")}
        self.assertEqual(sorted(rest), [f"D6-0{i}" for i in range(3, 8)])
        self.assertEqual(set(rest.values()), {"Proposed"})
        d4c = self.rows("D4C_DECISIONS.md")
        self.assertEqual(set(d4c.values()), {"Decided"})
        for f in ("D4_DECISIONS.md", "D4B_DECISIONS.md", "D5_DECISIONS.md", "D4C_DECISIONS.md", "D6_DECISIONS.md"):
            self.assertNotIn("Open", set(self.rows(f).values()), f)


class TestSelectionRule(unittest.TestCase):
    """D6-02 on hand-built cells (no repository data)."""

    def test_rule_on_planted_cells(self) -> None:
        import select_v1
        scs = [
            # real-world dev F2 unsafe: 3 targets (one excluded twice over), 2 reserves (one excluded)
            rec("tp-v1-F2-0301", "dev", "real_world", "F2", "unsafe", False, "unsafe", None),
            rec("tp-v1-F2-0302", "dev", "real_world", "F2", "unsafe", False, None, "s0_not_clean"),
            rec("tp-v1-F2-0303", "dev", "real_world", "F2", "unsafe", False, None, "unplannable"),
            rec("tp-v1-F2-0305", "dev", "real_world", "F2", "unsafe", True, None, "unplannable"),
            rec("tp-v1-F2-0304", "dev", "real_world", "F2", "unsafe", True, "unsafe", None),
            # controlled dev F2 unsafe: 1 target, 2 labelled reserves
            rec("tp-v1-F2-0040", "dev", "controlled", "F2", "unsafe", False, "unsafe", None),
            rec("tp-v1-F2-0042", "dev", "controlled", "F2", "unsafe", True, "unsafe", None),
            rec("tp-v1-F2-0041", "dev", "controlled", "F2", "unsafe", True, "unsafe", None),
            # real-world dev F4 safe: one excluded target and nothing to fill it with (no reserve, no controlled)
            rec("tp-v1-F4-0310", "dev", "real_world", "F4", "safe", False, None, "value_dependent"),
            # a test reserve of another split must never fill a dev cell
            rec("tp-v1-F4-0311", "test", "real_world", "F4", "safe", True, "safe", None),
        ]
        roles, report = select_v1.select(scs)
        role = {k: v["v1_role"] for k, v in roles.items()}
        self.assertEqual(role["tp-v1-F2-0301"], "target")
        self.assertEqual((role["tp-v1-F2-0302"], role["tp-v1-F2-0303"], role["tp-v1-F2-0305"]),
                         ("excluded", "excluded", "excluded"))
        self.assertEqual(role["tp-v1-F2-0304"], "target")  # lowest labelled reserve of the cell
        self.assertEqual(role["tp-v1-F2-0041"], "target")  # step 3: lowest labelled controlled reserve
        self.assertEqual(role["tp-v1-F2-0042"], "reserve")
        self.assertEqual(role["tp-v1-F2-0040"], "target")
        self.assertEqual(role["tp-v1-F4-0311"], "reserve")
        swaps = {s["excluded"]: s["replacement"] for s in report["swaps"]}
        self.assertEqual(swaps, {"tp-v1-F2-0302": "tp-v1-F2-0304", "tp-v1-F2-0303": "tp-v1-F2-0041"})
        self.assertEqual([s["replacement"] for s in report["swaps"] if s["from_controlled"]], ["tp-v1-F2-0041"])
        self.assertEqual([(s["split"], s["tier"], s["family"], s["class"], s["missing"]) for s in report["shortfalls"]],
                         [("dev", "real_world", "F4", "safe", 1)])
        self.assertIn("tp-v1-F2-0302", roles["tp-v1-F2-0304"]["v1_role_reason"])
        self.assertIsNone(roles["tp-v1-F2-0301"]["v1_role_reason"])

    def test_target_whose_class_differs_from_intent_goes_to_its_gt_cell(self) -> None:
        import select_v1
        scs = [rec("tp-v1-F1-0001", "dev", "controlled", "F1", "safe", False, "unsafe", None)]
        roles, _report = select_v1.select(scs)
        self.assertEqual(roles["tp-v1-F1-0001"]["v1_role"], "target")


class TestV1Roles(unittest.TestCase):
    def test_a2_dev_swaps_as_worked_by_hand(self) -> None:
        got = {d["scenario_id"]: d for _p, d in scenarios(DEV)}
        for d in got.values():
            self.assertIn(d.get("v1_role"), ("target", "reserve", "excluded"), d["scenario_id"])
            self.assertIn("v1_role_reason", d, d["scenario_id"])
        for excluded, repl in EXPECTED_DEV_SWAPS.items():
            self.assertEqual(got[excluded]["v1_role"], "excluded", excluded)
            self.assertEqual(got[repl]["v1_role"], "target", repl)
            self.assertTrue(got[repl]["reserve"], repl)
            self.assertIn(excluded, got[repl]["v1_role_reason"] or "", repl)
            self.assertIn(repl, got[excluded]["v1_role_reason"] or "", excluded)
        for sid in EXPECTED_DEV_FROM_CONTROLLED:
            self.assertEqual(got[sid]["source"]["tier"], "controlled")
            self.assertIn("D6-02 step 3", got[sid]["v1_role_reason"])
        for sid in EXPECTED_DEV_EXCLUDED_RESERVES:
            self.assertEqual(got[sid]["v1_role"], "excluded", sid)
        promoted = {s for s, d in got.items() if d["reserve"] and d["v1_role"] == "target"}
        self.assertEqual(promoted, set(EXPECTED_DEV_SWAPS.values()))
        demoted = {s for s, d in got.items() if not d["reserve"] and d["v1_role"] != "target"}
        self.assertEqual(demoted, set(EXPECTED_DEV_SWAPS))
        for s, d in got.items():  # D6-02 (4): no other change
            if s not in promoted and s not in demoted and s not in EXPECTED_DEV_EXCLUDED_RESERVES:
                self.assertEqual(d["v1_role"], "reserve" if d["reserve"] else "target", s)
                self.assertIsNone(d["v1_role_reason"], s)
            if d["v1_role"] == "excluded":
                self.assertIsNotNone(d.get("excluded_from_v1"), s)
            if d["v1_role"] in ("target", "reserve"):
                self.assertIsNotNone(d.get("gt_class"), s)

    def test_a2_exactly_320_targets_and_20_20_per_family(self) -> None:
        man = json.loads((REPO_ROOT / "scenarios" / "V1_MANIFEST.json").read_text(encoding="utf-8"))
        roles = collections.Counter((split, e["v1_role"]) for split in ("dev", "test") for e in man[split])
        self.assertEqual(roles[("dev", "target")] + roles[("test", "target")], 320)
        self.assertEqual((roles[("dev", "target")], roles[("test", "target")]), (224, 96))
        dev = {d["scenario_id"]: d for _p, d in scenarios(DEV)}
        fam = collections.Counter((d["family"], d["gt_class"]) for d in dev.values() if d["v1_role"] == "target")
        for f in FAMILIES:
            self.assertEqual((fam[(f, "safe")], fam[(f, "unsafe")]), (14, 14), f"dev {f}")
        priv = private_root()
        if priv is None:
            self.skipTest("TERRAPRESERVE_PRIVATE not set: the withheld test split is not checked")
        test = [d for _p, d in scenarios(priv)]
        self.assertTrue(all(d.get("v1_role") in ("target", "reserve", "excluded") for d in test))
        tf = collections.Counter((d["family"], d["gt_class"]) for d in test if d["v1_role"] == "target")
        for f in FAMILIES:
            self.assertEqual((tf[(f, "safe")], tf[(f, "unsafe")]), (6, 6), "test family counts (ids withheld)")


class TestGateChecker(unittest.TestCase):
    """D6-03 on planted failures, over copies of two dev scenarios (a controlled and a real-world target)."""

    def setUp(self) -> None:
        import check_freeze_gates as g
        self.g = g
        self.tmp = Path(tempfile.mkdtemp(prefix="tp-d6-"))
        self.dev, self.test = self.tmp / "dev", self.tmp / "test"
        self.dev.mkdir()
        self.test.mkdir()
        for sid in ("tp-v1-F1-0002", "tp-v1-F2-0258"):
            shutil.copytree(DEV / sid, self.dev / sid)
        shutil.copytree(DEV / "tp-v1-F1-0003", self.test / "tp-v1-F1-0003")
        d = self.load(self.test / "tp-v1-F1-0003")
        d["split"] = "test"
        self.save(self.test / "tp-v1-F1-0003", d)
        for p in (self.dev / "tp-v1-F1-0002", self.dev / "tp-v1-F2-0258", self.test / "tp-v1-F1-0003"):
            d = self.load(p)
            d["v1_role"], d["v1_role_reason"] = "target", None
            self.save(p, d)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def load(self, p: Path) -> dict:
        return json.loads((p / "scenario.json").read_text(encoding="utf-8"))

    def save(self, p: Path, d: dict) -> None:
        (p / "scenario.json").write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    def scs(self):
        return self.g.load(self.dev, self.test)

    def test_clean_fixture_passes(self) -> None:
        scs = self.scs()
        for fn in (self.g.gate3, self.g.gate4, self.g.gate6):
            self.assertEqual(fn(scs)["result"], "PASS", fn.__name__)
        self.assertEqual(self.g.gate5(scs, gitleaks=None)["result"], "PASS")
        self.assertEqual(self.g.gate2(scs, validator=lambda files: "valid")["result"], "PASS")
        self.assertEqual(self.g.gate8_steps(scs)["result"], "PASS")

    def test_changed_step_hash_fails_gate8(self) -> None:
        f = next((self.dev / "tp-v1-F1-0002" / "step_0").glob("*.tf"))
        f.write_text(f.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        self.assertEqual(self.g.gate8_steps(self.scs())["result"], "FAIL")

    def test_lineage_in_both_splits_fails_gate6(self) -> None:
        d = self.load(self.test / "tp-v1-F1-0003")
        d["source"]["repo_lineage_id"] = self.load(self.dev / "tp-v1-F2-0258")["source"]["repo_lineage_id"]
        self.save(self.test / "tp-v1-F1-0003", d)
        self.assertEqual(self.g.gate6(self.scs())["result"], "FAIL")

    def test_missing_label_fails_gate4(self) -> None:
        d = self.load(self.dev / "tp-v1-F2-0258")
        del d["labels"][-1]["invariant_truth"]["INV-SEC-002"]
        self.save(self.dev / "tp-v1-F2-0258", d)
        self.assertEqual(self.g.gate4(self.scs())["result"], "FAIL")

    def test_s0_fail_on_target_fails_gate3(self) -> None:
        d = self.load(self.dev / "tp-v1-F1-0002")
        inv = next(i for i in INVS if i != (d["target"] or {}).get("invariant_id"))
        d["labels"][0]["invariant_truth"][inv] = "FAIL"
        self.save(self.dev / "tp-v1-F1-0002", d)
        self.assertEqual(self.g.gate3(self.scs())["result"], "FAIL")

    def test_fake_secret_fails_gate5(self) -> None:
        f = next((self.dev / "tp-v1-F1-0002" / "step_0").glob("*.tf"))
        fake = "".join(chr(c) for c in (104, 117, 110, 116, 101, 114)) + "2-not-a-real-one"  # built at runtime
        f.write_text(f.read_text(encoding="utf-8") + f'\nlocals {{\n  admin_password = "{fake}"\n}}\n',
                     encoding="utf-8", newline="\n")
        self.assertEqual(self.g.gate5(self.scs(), gitleaks=None)["result"], "FAIL")

    def test_invalid_step_fails_gate2(self) -> None:
        self.assertEqual(self.g.gate2(self.scs(), validator=lambda files: "invalid")["result"], "FAIL")

    def test_missing_version_fails_gate9(self) -> None:
        self.assertEqual(self.g.gate9(self.scs())["result"], "PASS")
        d = self.load(self.dev / "tp-v1-F2-0258")
        d["oracle"]["versions"]["checkov"] = None
        self.save(self.dev / "tp-v1-F2-0258", d)
        self.assertEqual(self.g.gate9(self.scs())["result"], "FAIL")

    def test_unbalanced_family_fails_gate7(self) -> None:
        # the fixture holds 3 targets; against a target of 5 per family and class, F3 (0 and 0) is outside +-2
        self.assertEqual(self.g.gate7(self.scs(), tolerance=2, target=5)["result"], "FAIL")
        self.assertEqual(self.g.gate7(self.scs(), tolerance=2, target=1)["result"], "PASS")


class TestManifests(unittest.TestCase):
    def test_a4_v1_manifest_hashes_verify(self) -> None:
        import writer
        mpath = REPO_ROOT / "scenarios" / "V1_MANIFEST.json"
        man = json.loads(mpath.read_text(encoding="utf-8"))
        self.assertEqual(man["dataset_version"], "1.0")
        dev = {p.name: p for p in DEV.glob("tp-v1-*")}
        self.assertEqual({e["scenario_id"] for e in man["dev"]}, set(dev))
        for e in man["dev"]:
            p = dev[e["scenario_id"]]
            text = (p / "scenario.json").read_text(encoding="utf-8")
            self.assertEqual(writer.sha256_text(text), e["scenario_json_sha256"], e["scenario_id"])
            d = json.loads(text)
            self.assertEqual(e["v1_role"], d["v1_role"])
            for s in e["steps"]:
                sd = p / f"step_{s['step']}"
                files = {f.relative_to(sd).as_posix(): f.read_text(encoding="utf-8") for f in sd.rglob("*") if f.is_file()}
                self.assertEqual(writer.compute_step_content_hash(files), s["content_hash"], e["scenario_id"])
        tm = {e["scenario_id"]: e for e in json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))}
        self.assertEqual({e["scenario_id"] for e in man["test"]}, set(tm))
        for e in man["test"]:
            self.assertEqual(set(e), {"scenario_id", "v1_role", "scenario_json_sha256", "steps"})
            self.assertEqual(e["scenario_json_sha256"], tm[e["scenario_id"]]["scenario_json_sha256"])
            self.assertEqual(e["steps"], tm[e["scenario_id"]]["steps"])
        sums = dict(reversed(ln.split("  ", 1)) for ln in
                    (REPO_ROOT / "scenarios" / "V1_MANIFEST.sha256").read_text(encoding="utf-8").splitlines())
        self.assertEqual(sums["V1_MANIFEST.json"], hashlib.sha256(mpath.read_bytes()).hexdigest())
        self.assertIn("V1_MANIFEST_PRIVATE.json", sums)
        priv = private_root()
        if priv is None:
            self.skipTest("TERRAPRESERVE_PRIVATE not set: the private manifest is not checked")
        pm = priv / "V1_MANIFEST_PRIVATE.json"
        self.assertEqual(sums["V1_MANIFEST_PRIVATE.json"], hashlib.sha256(pm.read_bytes()).hexdigest())
        bad = 0
        for e in json.loads(pm.read_text(encoding="utf-8"))["test"]:
            text = (priv / e["scenario_id"] / "scenario.json").read_text(encoding="utf-8")
            bad += writer.sha256_text(text) != e["scenario_json_sha256"] or json.loads(text)["v1_role"] != e["v1_role"]
        self.assertEqual(bad, 0, "private manifest entries that do not verify (ids withheld)")


class TestEvidenceArchive(unittest.TestCase):
    def test_archive_is_deterministic(self) -> None:
        import freeze_v1
        tmp = Path(tempfile.mkdtemp(prefix="tp-d6-ev-"))
        try:
            recs = tmp / "records"
            recs.mkdir()
            for i in (3, 1, 2):
                (recs / f"tp-v1-F1-000{i}.json").write_text(json.dumps({"i": i}), encoding="utf-8")
            a = freeze_v1.build_archive(recs, tmp / "a.tar.gz", "ev")
            os.utime(recs / "tp-v1-F1-0001.json", (1, 1))
            b = freeze_v1.build_archive(recs, tmp / "b.tar.gz", "ev")
            self.assertEqual(a, b)
            self.assertEqual((tmp / "a.tar.gz").read_bytes(), (tmp / "b.tar.gz").read_bytes())
            (recs / "tp-v1-F1-0002.json").write_text(json.dumps({"i": 9}), encoding="utf-8")
            self.assertNotEqual(freeze_v1.build_archive(recs, tmp / "c.tar.gz", "ev")[0], a[0])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a4_dev_archive_recorded_and_rederived(self) -> None:
        import freeze_v1
        doc = (REPO_ROOT / "docs" / "D6_FREEZE.md").read_text(encoding="utf-8")
        m = re.search(r"oracle-evidence-dev-v1\.0\.tar\.gz`?: sha256 `([0-9a-f]{64})`, (\d+) bytes", doc)
        self.assertIsNotNone(m, "dev archive hash and size not recorded in docs/D6_FREEZE.md")
        self.assertRegex(doc, r"oracle-evidence-test-v1\.0\.tar\.gz`?: sha256 `[0-9a-f]{64}`, \d+ bytes")
        tracked = [ln for ln in os.popen(f'git -C "{REPO_ROOT}" ls-files').read().splitlines() if "oracle-evidence" in ln]
        self.assertEqual(tracked, [], "an evidence archive is tracked (D6-05: both kept outside the repository)")
        recs = freeze_v1.RECORDS["dev"]
        if not recs.is_dir():
            self.skipTest("dev run records not present (kept outside the repository)")
        tmp = Path(tempfile.mkdtemp(prefix="tp-d6-ev-"))
        try:
            sha, size = freeze_v1.build_archive(recs, tmp / "dev.tar.gz", "oracle-evidence-dev-v1.0")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual((sha, str(size)), (m.group(1), m.group(2)))
        dev = {d["scenario_id"]: d for _p, d in scenarios(DEV) if d.get("labels")}
        sample = sorted(dev)[:: max(1, len(dev) // 20)][:20]
        self.assertEqual(len(sample), 20)
        for sid in sample:
            r = json.loads((recs / f"{sid}.json").read_text(encoding="utf-8"))
            self.assertEqual(r["per_set"]["primary"]["labels"], dev[sid]["labels"], sid)
            self.assertEqual(r["per_set"]["primary"]["gt_class"], dev[sid]["gt_class"], sid)


class TestUnchangedAgainst8db6278(unittest.TestCase):
    def test_a5_steps_and_labels_unchanged(self) -> None:
        files, jsons = digests(DEV)
        self.assertEqual(files, BASE_DEV_FILES, "a dev step or provenance file changed")
        self.assertEqual(jsons, BASE_DEV_JSON, "a dev scenario.json changed beyond v1_role / v1_role_reason")
        man = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
        rows = sorted(f"{e['scenario_id']}|{s['step']}|{s['content_hash']}" for e in man for s in e["steps"])
        self.assertEqual((len(rows), hashlib.sha256("\n".join(rows).encode()).hexdigest()), BASE_MANIFEST_STEPS)
        priv = private_root()
        if priv is None:
            self.skipTest("TERRAPRESERVE_PRIVATE not set: the withheld test split is not checked")
        files, jsons = digests(priv)
        self.assertEqual(files, BASE_TEST_FILES, "a withheld step file changed (ids withheld)")
        self.assertEqual(jsons, BASE_TEST_JSON, "a withheld scenario.json changed beyond the v1 fields (ids withheld)")


if __name__ == "__main__":
    unittest.main()
