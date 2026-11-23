"""TP-V: the human label audit (``docs/AUDIT_PROTOCOL_v1.md``): the draw, the blinded packet, private writes,
the refusal of an unpinned private directory, the scoring tool, and the independence check of both tools.

Every fixture is built at test time. The private "test split" here is a set of committed dev targets copied into a
temporary directory and marked ``split: test``; their labels are the oracle's own (nothing here writes a label).
The real test split is never read. Standard library only; no DAIL import.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for sub in ("tools", "tests"):
    if str(REPO_ROOT / sub) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / sub))

FAMILIES = [f"F{i}" for i in range(1, 9)]
TIERS = ["controlled", "real_world"]
CLASSES = ["safe", "unsafe"]
INVS = ["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"]
FORBIDDEN = ["labels", "gt_class", "oracle", "intent", "mutation_record", "v1_role_reason", "parameters",
             "variable_values_alt", "diff_from_previous"]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def synthetic_population() -> list[dict]:
    """96 records, 3 per stratum (family x tier x class), with ids that do not sort in stratum order."""
    out = []
    n = 1
    for c in CLASSES:
        for t in TIERS:
            for f in FAMILIES:
                for _ in range(3):
                    out.append({"scenario_id": f"tp-v1-{f}-{(n * 37) % 1000:04d}", "family": f, "tier": t,
                                "oracle_class": c})
                    n += 1
    return out


def protocol_draw(pop: list[dict]) -> list[str]:
    """The protocol's draw, written out independently of the tool."""
    rng = random.Random(20261124)
    ids = []
    for f in FAMILIES:
        for t in TIERS:
            for c in CLASSES:
                cands = sorted(p["scenario_id"] for p in pop
                               if (p["family"], p["tier"], p["oracle_class"]) == (f, t, c))
                ids.append(rng.choice(cands))
    return ids


def step_hash(d: Path) -> str:
    files = sorted((p.relative_to(d).as_posix(), p) for p in d.rglob("*") if p.is_file())
    return sha256("\n".join(f"{r}:{sha256(p.read_bytes())}" for r, p in files).encode("utf-8"))


_FIXTURE: dict[str, object] = {}


def private_fixture() -> tuple[Path, str]:
    """A private directory outside the repository: 96 dev targets (3 per stratum, oracle labels as committed)
    copied and marked as the test split, with a V1_MANIFEST_PRIVATE.json and its pin. Built once per run."""
    if "root" in _FIXTURE:
        return _FIXTURE["root"], _FIXTURE["pin"]  # type: ignore[return-value]
    root = Path(tempfile.mkdtemp(prefix="tp-v-private-"))
    by: dict[tuple, list[tuple[Path, dict]]] = collections.defaultdict(list)
    for p in sorted((REPO_ROOT / "scenarios" / "dev").glob("tp-v1-*")):
        d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
        if d.get("v1_role") == "target":
            by[(d["family"], d["source"]["tier"], d.get("gt_class"))].append((p, d))
    entries = []
    keep = ("scenario_id", "v1_role", "v1_role_reason", "family", "gt_class")
    for key in [(f, t, c) for f in FAMILIES for t in TIERS for c in CLASSES]:
        for p, d in by[key][:3]:
            dst = root / p.name
            shutil.copytree(p, dst)
            d["split"] = "test"
            text = json.dumps(d, indent=2, sort_keys=True) + "\n"
            (dst / "scenario.json").write_text(text, encoding="utf-8", newline="\n")
            e = {k: d.get(k) for k in keep}
            e.update(intent_class=d["intent"]["class"], tier=d["source"]["tier"],
                     scenario_json_sha256=sha256(text.encode("utf-8")),
                     steps=[{"step": s["step"], "content_hash": s["content_hash"]} for s in d["steps"]])
            entries.append(e)
    raw = (json.dumps({"dataset_version": "1.0", "test": entries}, indent=2, sort_keys=True) + "\n").encode()
    (root / "V1_MANIFEST_PRIVATE.json").write_bytes(raw)
    _FIXTURE.update(root=root, pin=sha256(raw))
    return root, sha256(raw)


def fresh_private() -> tuple[Path, str]:
    """A copy of the fixture with no audit directory yet (the packet is written once per directory)."""
    src, pin = private_fixture()
    dst = Path(tempfile.mkdtemp(prefix="tp-v-run-")) / "private"
    shutil.copytree(src, dst)
    return dst, pin


def git_status() -> str:
    return subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=REPO_ROOT,
                          capture_output=True, text=True, check=True).stdout


class TestDraw(unittest.TestCase):
    def test_draw_is_reproducible_one_per_stratum(self) -> None:
        import audit_packet as ap
        pop = synthetic_population()
        a = ap.draw(pop)
        self.assertEqual(a, ap.draw(list(reversed(pop))))
        self.assertEqual(a, protocol_draw(pop))
        self.assertEqual(len(a), 32)
        strata = collections.Counter((p["family"], p["tier"], p["oracle_class"]) for p in pop
                                     if p["scenario_id"] in a)
        self.assertEqual(len(strata), 32)
        self.assertEqual(set(strata.values()), {1})

    def test_shuffled_order_follows_the_protocol(self) -> None:
        import audit_packet as ap
        ids = ap.draw(synthetic_population())
        want = list(ids)
        random.Random(20261125).shuffle(want)
        got = ap.order(ids)
        self.assertEqual([pid for pid, _ in got], [f"A{i:02d}" for i in range(1, 33)])
        self.assertEqual([sid for _, sid in got], want)

    def test_a_missing_stratum_is_refused(self) -> None:
        import audit_packet as ap
        pop = [p for p in synthetic_population() if (p["family"], p["tier"]) != ("F3", "real_world")]
        with self.assertRaises(ValueError):
            ap.draw(pop)


class TestPacket(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import audit_packet as ap
        cls.ap = ap
        cls.before = git_status()
        cls.private, cls.pin = fresh_private()
        cls.summary = ap.build(cls.private, cls.pin)
        cls.after = git_status()
        cls.audit = cls.private / "audit" / "v1"
        cls.key = json.loads((cls.audit / "key.json").read_text(encoding="utf-8"))

    def test_counts_and_csv_rows(self) -> None:
        self.assertEqual(self.summary["packets"], 32)
        with open(self.audit / "audit_labels.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(list(rows[0]), ["packet_id", "step", "invariant_id", "label", "note"])
        self.assertEqual(self.summary["csv_rows"], len(rows))
        want = 0
        for pid, sid in self.key.items():
            n = len(json.loads((self.private / sid / "scenario.json").read_text(encoding="utf-8"))["steps"])
            want += 4 * n
        self.assertEqual(len(rows), want)
        self.assertTrue(all(r["label"] == "" and r["note"] == "" for r in rows))
        self.assertEqual({r["invariant_id"] for r in rows}, set(INVS))
        self.assertEqual(self.summary["key_sha256"], sha256((self.audit / "key.json").read_bytes()))

    def test_brief_has_exactly_the_allowed_keys(self) -> None:
        for pid, sid in self.key.items():
            b = json.loads((self.audit / "packet" / pid / "brief.json").read_text(encoding="utf-8"))
            self.assertEqual(set(b), {"packet_id", "family", "target", "endpoints", "variable_values", "steps"})
            self.assertEqual(set(b["target"]), {"kind", "invariant_id"})
            self.assertEqual(set(b["endpoints"]), {"S", "D"})
            d = json.loads((self.private / sid / "scenario.json").read_text(encoding="utf-8"))
            self.assertEqual(b["packet_id"], pid)
            self.assertEqual(b["variable_values"], d["variable_values"])
            self.assertEqual(b["steps"], [s["step"] for s in d["steps"]])

    def test_no_forbidden_key_no_description_no_label_words(self) -> None:
        descriptions = []
        for sid in self.key.values():
            d = json.loads((self.private / sid / "scenario.json").read_text(encoding="utf-8"))
            descriptions.append(d["target"]["description"])
        self.assertEqual(self.ap.check_blinded(self.audit / "packet", descriptions), [])
        for f in (self.audit / "packet").rglob("*"):
            if f.is_file():
                text = f.read_text(encoding="utf-8")
                for k in FORBIDDEN:
                    self.assertNotIn(f'"{k}"', text, f"{f.name}: {k}")
                for desc in descriptions:
                    self.assertNotIn(desc, text, f.name)

    def test_a_planted_label_is_caught(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="tp-v-plant-"))
        try:
            shutil.copytree(self.audit / "packet", tmp / "packet")
            pid = sorted(self.key)[0]
            f = next((tmp / "packet" / pid / "step_0").glob("*.tf"))
            f.write_text(f.read_text(encoding="utf-8") + '\n# INV-SEC-001: PASS\n', encoding="utf-8")
            self.assertTrue(self.ap.check_blinded(tmp / "packet", []))
            shutil.rmtree(tmp / "packet")
            shutil.copytree(self.audit / "packet", tmp / "packet")
            b = tmp / "packet" / pid / "brief.json"
            doc = json.loads(b.read_text(encoding="utf-8"))
            doc["intent"] = {"class": "safe"}
            b.write_text(json.dumps(doc), encoding="utf-8")
            self.assertTrue(self.ap.check_blinded(tmp / "packet", []))
            shutil.rmtree(tmp / "packet")
            shutil.copytree(self.audit / "packet", tmp / "packet")
            desc = "Repair public SSH ingress on port 22"
            (tmp / "packet" / pid / "notes.txt").write_text(desc, encoding="utf-8")
            self.assertTrue(self.ap.check_blinded(tmp / "packet", [desc]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_variable_attribute_names_are_not_forbidden_keys(self) -> None:
        """A module's own variable may have an attribute called description (the primary values are allowed);
        the same key anywhere else in the brief is caught."""
        tmp = Path(tempfile.mkdtemp(prefix="tp-v-vars-"))
        try:
            shutil.copytree(self.audit / "packet", tmp / "packet")
            b = tmp / "packet" / sorted(self.key)[0] / "brief.json"
            doc = json.loads(b.read_text(encoding="utf-8"))
            doc["variable_values"]["tp_ds_aws_vpc_main"] = {"description": "a module's own text", "id": "vpc-1"}
            b.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
            self.assertEqual(self.ap.check_blinded(tmp / "packet", []), [])
            doc["target"]["description"] = "Repair public SSH ingress on port 22"
            b.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
            self.assertTrue(self.ap.check_blinded(tmp / "packet", []))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_files_copied_byte_for_byte(self) -> None:
        for pid, sid in self.key.items():
            d = json.loads((self.private / sid / "scenario.json").read_text(encoding="utf-8"))
            for s in d["steps"]:
                src = self.private / sid / s["terraform_dir"]
                dst = self.audit / "packet" / pid / s["terraform_dir"]
                self.assertEqual(step_hash(dst), step_hash(src), f"{pid} {s['terraform_dir']}")
                self.assertEqual(step_hash(dst), s["content_hash"])
            names = {p.name for p in (self.audit / "packet" / pid).iterdir()}
            self.assertEqual(names, {"brief.json"} | {s["terraform_dir"] for s in d["steps"]})

    def test_writes_stay_private(self) -> None:
        self.assertEqual(self.before, self.after, "the repository changed during the run")
        new = {p.relative_to(self.private).parts[:3] for p in self.private.rglob("*") if p.is_file()
               and "audit" in p.relative_to(self.private).parts[:1]}
        self.assertEqual(new, {("audit", "v1", "packet"), ("audit", "v1", "audit_labels.csv"),
                               ("audit", "v1", "key.json")})

    def test_a_second_run_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            self.ap.build(self.private, self.pin)


class TestRefusals(unittest.TestCase):
    def test_unpinned_private_manifest_is_refused(self) -> None:
        import audit_packet as ap
        private, pin = fresh_private()
        with self.assertRaises(SystemExit):
            ap.build(private, "0" * 64)
        with self.assertRaises(SystemExit):  # the CLI pins the frozen V1_MANIFEST.sha256 value, not the fixture's
            ap.main(["--split", "test", "--private", str(private)])
        self.assertFalse((private / "audit").exists())

    def test_a_packet_that_fails_the_blinding_check_leaves_nothing(self) -> None:
        import audit_packet as ap
        private, pin = fresh_private()
        orig = ap.check_blinded
        ap.check_blinded = lambda root, secrets: ["planted problem"]
        try:
            with self.assertRaises(SystemExit):
                ap.build(private, pin)
        finally:
            ap.check_blinded = orig
        self.assertFalse((private / "audit").exists())

    def test_private_inside_the_repository_is_refused(self) -> None:
        import audit_packet as ap
        with self.assertRaises(SystemExit):
            ap.main(["--split", "test", "--private", str(REPO_ROOT / "scenarios")])

    def test_a_changed_scenario_is_refused(self) -> None:
        import audit_packet as ap
        private, pin = fresh_private()
        manifest = json.loads((private / "V1_MANIFEST_PRIVATE.json").read_text(encoding="utf-8"))["test"]
        drawn = ap.draw(ap.population(manifest))  # change a scenario the protocol samples (glob order is not)
        f = sorted((private / drawn[0] / "step_0").glob("*.tf"))[0]
        f.write_text(f.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            ap.build(private, pin)


class TestScore(unittest.TestCase):
    def test_kappa_hand_computed(self) -> None:
        import audit_score as sc
        pairs = [("PASS", "PASS")] * 4 + [("FAIL", "FAIL")] * 3 + [("PASS", "FAIL")] * 2 + [("FAIL", "PASS")]
        # p_o = 7/10; auditor PASS 6/10, oracle PASS 5/10: p_e = 0.6*0.5 + 0.4*0.5 = 0.5; kappa = 0.2/0.5 = 0.4
        k = sc.kappa(pairs)
        self.assertAlmostEqual(k["kappa"], 0.4)
        self.assertAlmostEqual(k["agreement"], 0.7)
        self.assertEqual(k["n"], 10)
        self.assertIsNone(sc.kappa([("PASS", "PASS")] * 3)["kappa"])  # p_e = 1: undefined, reported as such

    def test_scenario_class_by_d5_11(self) -> None:
        import audit_score as sc
        p = {i: "PASS" for i in INVS}
        self.assertEqual(sc.auditor_class([p, p], None), "safe")
        self.assertEqual(sc.auditor_class([p, dict(p, **{"INV-FUNC-001": "FAIL"})], None), "unsafe")
        tgt = "INV-SEC-001"
        self.assertEqual(sc.auditor_class([dict(p, **{tgt: "FAIL"}), dict(p, **{tgt: "FAIL"}), p], tgt), "safe")
        self.assertEqual(sc.auditor_class([dict(p, **{tgt: "FAIL"}), dict(p, **{tgt: "FAIL"})], tgt), "unsafe")
        self.assertIsNone(sc.auditor_class([p, dict(p, **{"INV-SEC-002": "CANNOT_TELL"})], None))

    def _filled(self) -> tuple[Path, str, list[dict], dict, dict]:
        import audit_packet as ap
        private, pin = fresh_private()
        ap.build(private, pin)
        audit = private / "audit" / "v1"
        key = json.loads((audit / "key.json").read_text(encoding="utf-8"))
        truth = {}
        for pid, sid in key.items():
            d = json.loads((private / sid / "scenario.json").read_text(encoding="utf-8"))
            truth[pid] = [lab["invariant_truth"] for lab in d["labels"]]
        with open(audit / "audit_labels.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            r["label"] = truth[r["packet_id"]][int(r["step"])][r["invariant_id"]]
        flip = next(r for r in rows if r["packet_id"] == "A01" and r["step"] == "1")
        flip["label"] = "FAIL" if flip["label"] == "PASS" else "PASS"
        ct = next(r for r in rows if r["packet_id"] == "A02" and r["step"] == "0")
        ct["label"], ct["note"] = "CANNOT_TELL", "the CIDR comes from a variable I could not resolve"
        with open(audit / "audit_labels.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["packet_id", "step", "invariant_id", "label", "note"], lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        return private, pin, rows, flip, ct

    def test_score_end_to_end_on_a_fixture(self) -> None:
        import audit_score as sc
        private, pin, rows, flip, ct = self._filled()
        with self.assertRaises(SystemExit):  # no recorded hash yet
            sc.run_score(private, pin)
        sc.record_hash(private)
        rep = sc.run_score(private, pin)
        self.assertEqual(rep["cells"]["cannot_tell"], 1)
        self.assertEqual(rep["cells"]["compared"], len(rows) - 1)
        dis = rep["disagreements"]
        self.assertEqual([(d["packet_id"], d["step"], d["invariant_id"]) for d in dis],
                         [(flip["packet_id"], int(flip["step"]), flip["invariant_id"])])
        self.assertEqual(rep["cells"]["agreed"], len(rows) - 2)
        self.assertTrue((private / "audit" / "v1" / "report.json").is_file())
        self.assertTrue((private / "audit" / "v1" / "report.md").is_file())
        per = {s["packet_id"]: s for s in rep["scenarios"]}
        self.assertEqual(len(per), 32)
        for pid, s in per.items():
            if pid not in ("A01", "A02"):
                self.assertEqual(s["auditor_class"], s["oracle_class"], pid)
        self.assertIsNone(per["A02"]["auditor_class"])  # a CANNOT_TELL cell and no FAIL deciding it

    def test_score_refuses_a_changed_csv(self) -> None:
        import audit_score as sc
        private, pin, *_ = self._filled()
        sc.record_hash(private)
        f = private / "audit" / "v1" / "audit_labels.csv"
        f.write_text(f.read_text(encoding="utf-8").replace("PASS", "FAIL", 1), encoding="utf-8", newline="")
        with self.assertRaises(SystemExit):
            sc.run_score(private, pin)

    def test_cannot_tell_needs_a_note_and_labels_are_checked(self) -> None:
        import audit_score as sc
        private, pin, rows, flip, ct = self._filled()
        f = private / "audit" / "v1" / "audit_labels.csv"
        f.write_text(f.read_text(encoding="utf-8").replace(ct["note"], ""), encoding="utf-8", newline="")
        sc.record_hash(private)
        with self.assertRaises(SystemExit):
            sc.run_score(private, pin)


class TestIndependenceCoversTheTools(unittest.TestCase):
    def test_both_tools_are_walked_and_a_dail_import_would_be_caught(self) -> None:
        import test_independence as ti
        walked = {f.resolve() for f in ti._walk(("*.py",))}
        for name in ("audit_packet.py", "audit_score.py"):
            path = REPO_ROOT / "tools" / name
            self.assertIn(path.resolve(), walked, name)
            src = path.read_text(encoding="utf-8")
            self.assertEqual(ti.forbidden_imports(src), set(), name)
            self.assertEqual(ti.forbidden_imports(src + "\nimport core\n"), {"core"}, name)


if __name__ == "__main__":
    unittest.main()
