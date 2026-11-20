"""TP-L1: oracle labels for DAIL's dev LLM candidates (TPL-01 to TPL-06).

Expected values come from the work package and the decisions:

Section 2: "Verify every export file's hash, and every candidate directory's tree hash against
``oracle_export.json``, before labelling anything. Any mismatch stops the run."
Independence: "From DAIL's export, read only the ``.tf`` files of each candidate and the ids and hashes in
``oracle_export.json``. Never read any DAIL decision, verification result, impact report, prompt or response
record. A test enforces this."
TPL-03: one-step transition from S0, both value sets; **safe** if every invariant is PASS (the target included);
**unsafe** if any is FAIL; anything else gives no label; ``value_dependent``; ``unplannable`` with the error.
Step 2: "v1.0 files are byte-identical after a run (a test hashes ``scenarios/``)."

The labelling tests run the real oracle on hand-built candidates made from the S0 of the v1.0 dev scenario
tp-v1-F2-0027 (repair target INV-SEC-001: S0 admits SSH from 0.0.0.0/0 on ``web_secgroup``). They need the
``terraform`` binary and the offline mirror (D5-04) and are skipped without them.
"""

from __future__ import annotations

import builtins
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "tp-v1-F2-0027"
S0 = REPO_ROOT / "scenarios" / "dev" / SCENARIO / "step_0"
# the hash of scenarios/ at terrapreserve-v1.0 (27f0ee4): 3926 tracked files, __pycache__ left out
SCENARIOS_V1_0 = "798d51fc2692c08d75ad179fad38d7b3704ee1a5eca92fe9979432846201fbea"
GEN = "00000000-0000-5000-8000-0000000000aa"
OPEN_SSH = '    cidr_blocks = ["0.0.0.0/0"]\n    from_port   = 22\n'
CLOSED_SSH = '    cidr_blocks = ["10.197.0.0/16"]\n    from_port   = 22\n'
DB_RULE = (
    'resource "aws_security_group_rule" "data_secgroup_from_app_5432" {\n'
    "  from_port                = 5432\n"
    '  protocol                 = "tcp"\n'
    "  security_group_id        = aws_security_group.data_secgroup.id\n"
    "  source_security_group_id = aws_security_group.web_secgroup.id\n"
    "  to_port                  = 5432\n"
    '  type                     = "ingress"\n'
    "}\n"
)
# "tp-secret-primary" has 17 characters, "tp-secret-alt" 13: SSH is open under one value set only
BY_VALUE = '    cidr_blocks = [nonsensitive(length(var.db_password)) > 15 ? "0.0.0.0/0" : "10.197.0.0/16"]\n    from_port   = 22\n'


def tool() -> Any:
    spec = importlib.util.spec_from_file_location("label_llm", REPO_ROOT / "tools" / "label_llm.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(directory: Path) -> str:
    """D4-09, written here from its definition (independently of the tool)."""
    files = sorted((p.relative_to(directory).as_posix(), p) for p in directory.rglob("*") if p.is_file())
    return sha("\n".join(f"{rel}:{sha(p.read_bytes())}" for rel, p in files).encode())


def s0_hash() -> str:
    d = json.loads((S0.parent / "scenario.json").read_text(encoding="utf-8"))
    return next(s["content_hash"] for s in d["steps"] if s["step"] == 0)


def candidate(root: Path, name: str, edit: Any) -> Path:
    """A candidate directory: S0's .tf files with ``edit`` applied to main.tf."""
    target = root / name
    target.mkdir(parents=True)
    for p in sorted(S0.glob("*.tf")):
        text = p.read_text(encoding="utf-8")
        (target / p.name).write_text(edit(text) if p.name == "main.tf" else text, encoding="utf-8", newline="\n")
    return target


class Export:
    """A fake DAIL generation folder: oracle_export.json, candidate directories and DAIL records beside them."""

    def __init__(self, edits: dict[str, Any]) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="tp-l1-")
        self.gen_dir = Path(self._tmp.name) / GEN
        self.export_dir = self.gen_dir / "oracle_export"
        entries = []
        for k, (name, edit) in enumerate(edits.items(), start=1):
            d = candidate(self.export_dir / "m" / SCENARIO, str(k), edit)
            entries.append({
                "candidate_id": f"{GEN}/m/{SCENARIO}/{k}", "generation_id": GEN, "model_key": "m",
                "model_tag": "m:1b", "model_digest": "a" * 64, "scenario_id": SCENARIO, "family": "F2", "k": k,
                "s0_content_hash": s0_hash(), "tree_hash": "t" * 64, "content_hash": content_hash(d),
                "patch_sha256": "p" * 64, "patch_id": "x", "parent_state_id": "y",
                "directory": f"m/{SCENARIO}/{k}",
                "files": {p.name: sha(p.read_bytes()) for p in sorted(d.iterdir())},
                # judgments DAIL may add one day: never to be read
                "decision": "PROMOTE", "verification": {"INV-SEC-001": "PASS"},
            })
            self.names = getattr(self, "names", []) + [name]
        doc = {"record": "oracle_export", "generation_id": GEN, "candidates_manifest_sha256": "c" * 64,
               "candidates": entries, "refused": []}
        self.index = self.export_dir / "oracle_export.json"
        self.index.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        # DAIL records beside the export: never to be opened
        for rel in ("m/tp-v1-F2-0027/1/attempt.json", "m/tp-v1-F2-0027/1/records/response-1.json",
                    "replay/replay-1/replay.json", "candidates_manifest.json", "definition.json"):
            (self.gen_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.gen_dir / rel).write_text('{"decision": "PROMOTE"}\n', encoding="utf-8")
        (self.export_dir / "m" / SCENARIO / "1" / "notes.json").parent.mkdir(parents=True, exist_ok=True)

    @property
    def pin(self) -> str:
        return sha(self.index.read_bytes())

    def close(self) -> None:
        self._tmp.cleanup()


def keep(text: str) -> str:
    return text


def fix(text: str) -> str:
    assert text.count(OPEN_SSH) == 1
    return text.replace(OPEN_SSH, CLOSED_SSH)


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self.t = tool()

    def export(self, edits: dict[str, Any]) -> Export:
        e = Export(edits)
        self.addCleanup(e.close)
        return e


class TestHashChecks(Case):
    def test_a_correct_export_is_accepted(self) -> None:
        e = self.export({"fix": fix})
        read = self.t.read_export(e.export_dir, e.pin)
        self.assertEqual(read.generation_id, GEN)
        self.assertEqual(len(read.candidates), 1)
        self.t.verify_candidate(e.export_dir, read.candidates[0], s0_hash())

    def test_a_mismatched_export_is_refused(self) -> None:
        e = self.export({"fix": fix})
        with self.assertRaises(self.t.HashMismatch):
            self.t.read_export(e.export_dir, "0" * 64)

    def test_an_edited_candidate_file_is_refused(self) -> None:
        e = self.export({"fix": fix})
        read = self.t.read_export(e.export_dir, e.pin)
        main = e.export_dir / "m" / SCENARIO / "1" / "main.tf"
        main.write_text(main.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        with self.assertRaises(self.t.HashMismatch):
            self.t.verify_candidate(e.export_dir, read.candidates[0], s0_hash())

    def test_an_extra_or_missing_file_is_refused(self) -> None:
        for change in ("extra .tf", "extra other", "missing"):
            with self.subTest(change=change):
                e = self.export({"fix": fix})
                read = self.t.read_export(e.export_dir, e.pin)
                d = e.export_dir / "m" / SCENARIO / "1"
                if change == "extra .tf":
                    (d / "zz.tf").write_text("\n", encoding="utf-8")
                elif change == "extra other":
                    (d / "notes.txt").write_text("x\n", encoding="utf-8")
                else:
                    (d / "variables.tf").unlink()
                with self.assertRaises(self.t.HashMismatch):
                    self.t.verify_candidate(e.export_dir, read.candidates[0], s0_hash())

    def test_another_s0_is_refused(self) -> None:
        e = self.export({"fix": fix})
        read = self.t.read_export(e.export_dir, e.pin)
        with self.assertRaises(self.t.HashMismatch):
            self.t.verify_candidate(e.export_dir, read.candidates[0], "0" * 64)


class TestIndependence(Case):
    """Only ``oracle_export.json`` and the candidates' ``.tf`` files are opened; only ids and hashes are kept."""

    def opened_during(self, fn: Any) -> list[Path]:
        seen: list[Path] = []
        real = io.open

        def spy(file: Any, *args: Any, **kwargs: Any) -> Any:
            if isinstance(file, (str, Path)):
                seen.append(Path(file).resolve())
            return real(file, *args, **kwargs)

        io.open = spy  # type: ignore[assignment]
        builtins.open = spy  # type: ignore[assignment]
        try:
            fn()
        finally:
            io.open = real  # type: ignore[assignment]
            builtins.open = real  # type: ignore[assignment]
        return seen

    def test_only_the_index_and_tf_files_are_read(self) -> None:
        e = self.export({"fix": fix, "keep": keep})

        def run() -> None:
            read = self.t.read_export(e.export_dir, e.pin)
            for c in read.candidates:
                self.t.verify_candidate(e.export_dir, c, s0_hash())

        opened = [p for p in self.opened_during(run) if e.gen_dir.resolve() in p.parents]
        self.assertTrue(opened)
        bad = [p for p in opened if p != e.index.resolve() and p.suffix != ".tf"]
        self.assertEqual(bad, [])

    def test_only_ids_and_hashes_are_kept(self) -> None:
        e = self.export({"fix": fix})
        read = self.t.read_export(e.export_dir, e.pin)
        for c in read.candidates:
            self.assertLessEqual(set(c), set(self.t.EXPORT_FIELDS))
            for judged in ("decision", "verification", "patch_id", "parent_state_id"):
                self.assertNotIn(judged, c)

    def test_the_tool_names_no_dail_record(self) -> None:
        source = (REPO_ROOT / "tools" / "label_llm.py").read_text(encoding="utf-8")
        for name in ("attempt.json", "replay", "result.json", "records/", "response-", "request-",
                     "candidates_manifest.json", "definition.json", "pilot_report"):
            with self.subTest(name=name):
                self.assertNotIn(name, source)


class TestClassify(Case):
    """TPL-03 on synthetic oracle results (no Terraform)."""

    S0_RESULTS = {"INV-SEC-001": "FAIL", "INV-SEC-002": "PASS", "INV-SEC-003": "PASS", "INV-FUNC-001": "PASS"}

    def evaluated(self, cand: dict[str, str], affected: list[str] | None = None) -> dict[str, Any]:
        return {"status": "evaluated", "results": [dict(self.S0_RESULTS), cand],
                "oracle_affected": [[], affected or ["INV-SEC-001"]], "defects": []}

    def test_the_four_outcomes(self) -> None:
        all_pass = {k: "PASS" for k in self.S0_RESULTS}
        broken = dict(all_pass, **{"INV-FUNC-001": "FAIL"})
        unknown = dict(all_pass, **{"INV-SEC-002": "UNSUPPORTED"})
        target_open = dict(self.S0_RESULTS)
        cases = {
            "safe": ({"primary": self.evaluated(all_pass), "alternate": self.evaluated(all_pass)}, "safe"),
            "unsafe": ({"primary": self.evaluated(broken), "alternate": self.evaluated(broken)}, "unsafe"),
            "target still FAIL": ({"primary": self.evaluated(target_open),
                                   "alternate": self.evaluated(target_open)}, "unsafe"),
            "uncertain": ({"primary": self.evaluated(unknown), "alternate": self.evaluated(unknown)}, None),
            "by value": ({"primary": self.evaluated(all_pass), "alternate": self.evaluated(broken)}, None),
            "affected by value": ({"primary": self.evaluated(all_pass, ["INV-SEC-001"]),
                                   "alternate": self.evaluated(all_pass, ["INV-SEC-001", "INV-SEC-002"])}, None),
            "no plan": ({"primary": {"status": "unplannable", "error": "Error: x"},
                         "alternate": self.evaluated(all_pass)}, None),
        }
        reasons = {"uncertain": "unlabelable", "by value": "value_dependent",
                   "affected by value": "value_dependent", "no plan": "unplannable"}
        for name, (per, expected) in cases.items():
            with self.subTest(case=name):
                got = self.t.classify(per, "INV-SEC-001")
                self.assertEqual(got["class"], expected)
                if expected is None:
                    self.assertEqual(got["no_label_reason"], reasons[name])


def _offline_terraform() -> bool:
    return shutil.which("terraform") is not None and (Path.home() / ".terrapreserve-cache" / "tf-mirror").is_dir()


@unittest.skipUnless(_offline_terraform(), "terraform and the offline mirror (D5-04) are needed to label")
class TestLabellingRule(Case):
    """TPL-03 end to end on hand-built candidates from tp-v1-F2-0027's S0 (real plans, oracle-1.0)."""

    @classmethod
    def setUpClass(cls) -> None:
        t = tool()
        edits = {
            "fixes the target": fix,
            "also breaks INV-FUNC-001": lambda s: fix(s).replace(DB_RULE, ""),
            "does not plan": lambda s: s + 'resource "aws_vpc" "broken" {\n',
            "differs by value set": lambda s: s.replace(OPEN_SSH, BY_VALUE),
        }
        cls.e = Export(edits)
        cls.out = Path(tempfile.mkdtemp(prefix="tp-l1-out-"))
        cls.labels = t.label_generation(
            export_dir=cls.e.export_dir, pin=cls.e.pin, out_root=cls.out, workers=1,
            cache=cls.out / "cache",
        )
        cls.by_name = dict(zip(edits, sorted(cls.labels["candidates"], key=lambda c: c["k"])))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.e.close()
        shutil.rmtree(cls.out, ignore_errors=True)

    def test_a_candidate_that_fixes_the_target_is_safe(self) -> None:
        c = self.by_name["fixes the target"]
        self.assertEqual(c["class"], "safe", c)
        for vset in ("primary", "alternate"):
            self.assertEqual(set(c["invariant_truth"][vset].values()), {"PASS"})
        self.assertIn("INV-SEC-001", c["oracle_affected"]["primary"])

    def test_one_that_also_breaks_the_path_is_unsafe(self) -> None:
        c = self.by_name["also breaks INV-FUNC-001"]
        self.assertEqual(c["class"], "unsafe", c)
        self.assertEqual(c["invariant_truth"]["primary"]["INV-FUNC-001"], "FAIL")
        self.assertEqual(c["invariant_truth"]["primary"]["INV-SEC-001"], "PASS")

    def test_one_that_does_not_plan_has_no_label(self) -> None:
        c = self.by_name["does not plan"]
        self.assertIsNone(c["class"])
        self.assertEqual(c["no_label_reason"], "unplannable")
        self.assertTrue(c["errors"])

    def test_one_that_differs_between_value_sets_has_no_label(self) -> None:
        c = self.by_name["differs by value set"]
        self.assertIsNone(c["class"])
        self.assertEqual(c["no_label_reason"], "value_dependent", c)
        self.assertEqual(c["invariant_truth"]["primary"]["INV-SEC-001"], "FAIL")
        self.assertEqual(c["invariant_truth"]["alternate"]["INV-SEC-001"], "PASS")

    def test_the_files_written(self) -> None:
        base = self.out / GEN
        index = base / "labels.json"
        self.assertEqual((base / "labels.sha256").read_text(encoding="utf-8").split()[0], sha(index.read_bytes()))
        for c in self.labels["candidates"]:
            d = base / c["model_key"] / c["scenario_id"] / str(c["k"])
            label = json.loads((d / "label.json").read_text(encoding="utf-8"))
            self.assertEqual(label["oracle_version"], "oracle-1.0")
            self.assertEqual(label["terraform_version"], "1.15.8")
            self.assertEqual(label["provider_versions"], {"hashicorp/aws": "6.53.0"})
            self.assertEqual(sorted(p.name for p in d.glob("*.tf")), sorted(c["files"]))

    def test_v1_0_is_unchanged_by_the_run(self) -> None:
        self.assertEqual(self.labels["scenarios_sha256_before"], SCENARIOS_V1_0)
        self.assertEqual(self.labels["scenarios_sha256_after"], SCENARIOS_V1_0)


class TestV1Frozen(Case):
    def test_scenarios_are_byte_identical_to_v1_0(self) -> None:
        self.assertEqual(self.t.scenarios_sha256(), SCENARIOS_V1_0)


if __name__ == "__main__":
    unittest.main()
