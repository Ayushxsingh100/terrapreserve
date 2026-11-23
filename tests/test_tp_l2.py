"""TP-L2: oracle labels for the test LLM candidates of the DAIL main run (TPL2-01 to TPL2-05).

Expected values come from the work package (Section 1 and Step 1) and the decisions:

Step 1: "the tool accepts ``--split test`` only with a private directory whose manifest hash is the pin; it writes
only under the private directory, and the repository's git status is unchanged after a run; the hash checks refuse
a mismatched export; the independence test covers the new code path."
Section 1: "``oracle_export.json`` must have SHA-256 ``7d008d9d…80ff``"; "``V1_MANIFEST_PRIVATE.json`` SHA-256
``14ca1fff…6efe``. Each candidate's S0 hash must equal the private v1.0 step-0 hash."
Decision 4: labels go to ``$TERRAPRESERVE_PRIVATE/llm_candidates/test/<generation id>/`` in TP-L1's format.
The user's decision (23 Nov 2026, TPL2-05): the oracle's transient working copies stay outside the private
directory, as in D5b (``oracle.inputs`` refuses a destination inside it), and are deleted when the run ends.

The fixtures are synthetic and built at test time: a private directory holding a copy of the *dev* scenario
tp-v1-F2-0027 marked ``split: test``, and a private manifest written for it. No test-split data is used.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_independence import _walk, forbidden_imports  # noqa: E402
from test_tp_l1 import (  # noqa: E402
    GEN,
    S0,
    SCENARIO,
    SCENARIOS_V1_0,
    Export,
    _offline_terraform,
    fix,
    keep,
    sha,
    tool,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
# Section 1 of the work package
MAIN_RUN_GENERATION = "40e2052b-b489-552d-8c27-88785414a4b1"
MAIN_RUN_EXPORT_SHA256 = "7d008d9d4fa28329d3d3d39ddddec76ea280c5b46b601316ecb06722754f80ff"
PRIVATE_MANIFEST_SHA256 = "14ca1fff3af778a81d43f90e70a14cb7b56d6ebf5474648514169e8c2d376efe"


class Private:
    """A synthetic private directory: one scenario (a copy of dev tp-v1-F2-0027 marked test) and its manifest."""

    def __init__(self, *, step0_hash: str | None = None, split: str = "test") -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="tp-l2-private-")
        self.root = Path(self._tmp.name) / "private"
        sdir = self.root / SCENARIO
        shutil.copytree(S0.parent, sdir, ignore=shutil.ignore_patterns("__pycache__"))
        doc = json.loads((sdir / "scenario.json").read_text(encoding="utf-8"))
        doc["split"] = split
        text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
        (sdir / "scenario.json").write_text(text, encoding="utf-8", newline="\n")
        steps = [{"step": s["step"], "content_hash": s["content_hash"]} for s in doc["steps"]]
        if step0_hash is not None:
            steps = [dict(s, content_hash=step0_hash) if s["step"] == 0 else s for s in steps]
        manifest = {"dataset_version": "1.0", "decision": "D6-04", "test": [{
            "scenario_id": SCENARIO, "v1_role": "target", "scenario_json_sha256": sha(text.encode("utf-8")),
            "steps": steps}]}
        self.manifest = self.root / "V1_MANIFEST_PRIVATE.json"
        self.manifest.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                 newline="\n")

    @property
    def pin(self) -> str:
        return sha(self.manifest.read_bytes())

    def files(self) -> set[Path]:
        return {p for p in self.root.rglob("*") if p.is_file()}

    def close(self) -> None:
        self._tmp.cleanup()


def git_status() -> str:
    return subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=all"],
                          capture_output=True, text=True, check=True).stdout


@contextlib.contextmanager
def spy_open(reads: list[Path], writes: list[Path]) -> Any:
    real = io.open

    def spy(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, (str, Path)):
            (writes if any(m in mode for m in "wax+") else reads).append(Path(file).resolve())
        return real(file, mode, *args, **kwargs)

    io.open = spy  # type: ignore[assignment]
    builtins.open = spy  # type: ignore[assignment]
    try:
        yield
    finally:
        io.open = real  # type: ignore[assignment]
        builtins.open = real  # type: ignore[assignment]


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self.t = tool()

    def private(self, **kwargs: Any) -> Private:
        p = Private(**kwargs)
        self.addCleanup(p.close)
        return p

    def export(self, edits: dict[str, Any]) -> Export:
        e = Export(edits)
        self.addCleanup(e.close)
        return e


class TestThePins(Case):
    def test_the_private_manifest_pin_is_v1_0s(self) -> None:
        self.assertEqual(self.t.private_manifest_pin(), PRIVATE_MANIFEST_SHA256)

    def test_the_main_run_export_is_pinned(self) -> None:
        self.assertEqual(self.t.TEST_EXPORT_PINS, {MAIN_RUN_GENERATION: MAIN_RUN_EXPORT_SHA256})


class TestThePrivateDirectory(Case):
    def test_a_manifest_with_the_pin_is_accepted(self) -> None:
        p = self.private()
        manifest = self.t.open_private(p.root, p.pin)
        self.assertEqual(sorted(manifest), [SCENARIO])

    def test_a_manifest_that_is_not_the_pin_is_refused(self) -> None:
        p = self.private()
        with self.assertRaisesRegex(self.t.HashMismatch, "manifest"):
            self.t.open_private(p.root, "0" * 64)

    def test_a_missing_manifest_is_refused(self) -> None:
        p = self.private()
        pin = p.pin
        p.manifest.unlink()
        with self.assertRaisesRegex(self.t.HashMismatch, "manifest"):
            self.t.open_private(p.root, pin)

    def test_the_command_refuses_without_the_pinned_private_directory(self) -> None:
        p = self.private()
        e = self.export({"fix": fix})
        base = ["--split", "test", "--generation", MAIN_RUN_GENERATION, "--dail-candidates", str(e.gen_dir.parent)]
        cases = {
            "no private directory": base + ["--private", str(p.root / "missing")],
            "manifest not the pin": base + ["--private", str(p.root)],  # the synthetic manifest is not v1.0's
            "inside the repository": base + ["--private", str(REPO_ROOT / "scenarios")],
        }
        for name, argv in cases.items():
            with self.subTest(case=name), contextlib.redirect_stdout(io.StringIO()) as out:
                with self.assertRaises(SystemExit) as cm:
                    self.t.main(argv)
                self.assertNotEqual(cm.exception.code, 0)
                self.assertEqual(out.getvalue(), "")
        self.assertFalse((p.root / "llm_candidates").exists())

    def test_a_private_directory_inside_the_repository_is_refused_before_its_manifest_is_read(self) -> None:
        inside = Path(tempfile.mkdtemp(prefix="tp-l2-inside-", dir=REPO_ROOT / "tests"))
        self.addCleanup(shutil.rmtree, inside, True)
        with self.assertRaisesRegex(SystemExit, "outside the repository"):
            self.t.main(["--split", "test", "--generation", MAIN_RUN_GENERATION, "--dail-candidates", str(inside),
                         "--private", str(inside)])

    def test_a_generation_that_is_not_pinned_is_refused(self) -> None:
        p = self.private()
        with self.assertRaisesRegex(SystemExit, "not pinned"):
            self.t.main(["--split", "test", "--generation", GEN, "--dail-candidates", str(p.root),
                         "--private", str(p.root)])


class TestTheTestSplitChecks(Case):
    """Every check runs before anything is labelled; one mismatch stops the run and writes nothing."""

    def label(self, p: Private, e: Export, pin: str | None = None) -> Any:
        return self.t.label_generation(export_dir=e.export_dir, pin=pin or e.pin, split="test", private=p.root,
                                       manifest_pin=p.pin, runner_cache=p.root.parent / "runners", workers=1)

    def assert_refused(self, p: Private, e: Export, pin: str | None = None) -> None:
        before = p.files()
        with self.assertRaises(self.t.HashMismatch):
            self.label(p, e, pin)
        self.assertEqual(p.files(), before)

    def test_a_mismatched_export_is_refused(self) -> None:
        self.assert_refused(self.private(), self.export({"fix": fix}), pin="0" * 64)

    def test_an_edited_candidate_is_refused(self) -> None:
        p, e = self.private(), self.export({"fix": fix})
        main = e.export_dir / "m" / SCENARIO / "1" / "main.tf"
        main.write_text(main.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        self.assert_refused(p, e)

    def test_an_s0_that_is_not_the_private_step_0_is_refused(self) -> None:
        self.assert_refused(self.private(step0_hash="0" * 64), self.export({"fix": fix}))

    def test_a_scenario_json_that_is_not_the_manifests_is_refused(self) -> None:
        p = self.private()
        sj = p.root / SCENARIO / "scenario.json"
        sj.write_text(sj.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        self.assert_refused(p, self.export({"fix": fix}))

    def test_an_s0_directory_that_is_not_its_hash_is_refused(self) -> None:
        p = self.private()
        main = p.root / SCENARIO / "step_0" / "main.tf"
        main.write_text(main.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        self.assert_refused(p, self.export({"fix": fix}))

    def test_a_scenario_not_in_the_private_manifest_is_refused(self) -> None:
        p = self.private()
        doc = json.loads(p.manifest.read_text(encoding="utf-8"))
        doc["test"] = []
        p.manifest.write_text(json.dumps(doc) + "\n", encoding="utf-8", newline="\n")
        self.assert_refused(p, self.export({"fix": fix}))

    def test_a_dev_scenario_in_the_private_directory_is_refused(self) -> None:
        self.assert_refused(self.private(split="dev"), self.export({"fix": fix}))

    def test_the_counts_of_the_checks(self) -> None:
        p, e = self.private(), self.export({"fix": fix, "keep": keep})
        export = self.t.read_export(e.export_dir, e.pin)
        manifest = self.t.open_private(p.root, p.pin)
        checks = self.t.check_test_candidates(export, e.export_dir, p.root, manifest)
        self.assertEqual(checks.counts, {"candidates_read": 2, "files_and_hashes_verified": 2, "s0_matched": 2})


class TestIndependenceOfTheTestPath(Case):
    def test_only_the_index_and_tf_files_of_the_export_are_read(self) -> None:
        p, e = self.private(), self.export({"fix": fix, "keep": keep})
        reads: list[Path] = []
        writes: list[Path] = []
        with spy_open(reads, writes):
            export = self.t.read_export(e.export_dir, e.pin)
            self.t.check_test_candidates(export, e.export_dir, p.root, self.t.open_private(p.root, p.pin))
        opened = [x for x in reads + writes if e.gen_dir.resolve() in x.parents]
        self.assertTrue(opened)
        self.assertEqual([x for x in opened if x != e.index.resolve() and x.suffix != ".tf"], [])
        self.assertEqual(writes, [])

    def test_the_tool_is_under_the_import_ban(self) -> None:
        path = (REPO_ROOT / "tools" / "label_llm.py").resolve()
        self.assertIn(path, [f.resolve() for f in _walk(("*.py",))])
        self.assertEqual(forbidden_imports(path.read_text(encoding="utf-8")), set())

    def test_the_test_summary_holds_no_label(self) -> None:
        doc = {"generation_id": GEN, "export_sha256": "e" * 64, "candidates": [
            {"class": "safe", "no_label_reason": None}, {"class": None, "no_label_reason": "unplannable"}]}
        checks = {"candidates_read": 2, "files_and_hashes_verified": 2, "s0_matched": 2}
        out = self.t.summary(doc, checks, split="test", labels_sha256="a" * 64, written=2, path=Path("x"))
        text = json.dumps(out)
        for word in ("safe", "unsafe", "unplannable", "counts", "class", "reason"):
            self.assertNotIn(word, text)
        self.assertEqual(out["label_json_written"], 2)


@unittest.skipUnless(_offline_terraform(), "terraform and the offline mirror (D5-04) are needed to label")
class TestATestSplitRun(Case):
    """A whole ``--split test`` run on the synthetic private directory (real plans, oracle-1.0)."""

    def test_it_writes_only_under_the_private_directory_and_leaves_git_unchanged(self) -> None:
        p, e = self.private(), self.export({"fix": fix, "keep": keep})
        runners = p.root.parent / "runners"
        status = git_status()
        reads: list[Path] = []
        writes: list[Path] = []
        with spy_open(reads, writes):
            doc = self.t.label_generation(export_dir=e.export_dir, pin=e.pin, split="test", private=p.root,
                                          manifest_pin=p.pin, runner_cache=runners, workers=1)
        self.assertEqual(git_status(), status)
        private = p.root.resolve()
        outside = [w for w in writes if private not in w.parents and runners.resolve() not in w.parents]
        self.assertEqual(outside, [])
        self.assertTrue(list(runners.rglob("seed")))  # the runners were here
        self.assertEqual(list(runners.rglob("work")), [])  # TPL2-05: the working copies are deleted at the end
        out = p.root / "llm_candidates" / "test" / GEN
        labels = sorted(out.rglob("label.json"))
        self.assertEqual(len(labels), 2)
        self.assertEqual((out / "labels.sha256").read_text(encoding="utf-8"),
                         f"{sha((out / 'labels.json').read_bytes())}  labels.json\n")
        self.assertTrue(any(p.root / "tp-l2-plans" in w.parents for w in writes))
        self.assertEqual(doc["scenarios_sha256_before"], SCENARIOS_V1_0)
        self.assertEqual(doc["scenarios_sha256_after"], SCENARIOS_V1_0)
        by_k = {c["k"]: c for c in doc["candidates"]}
        self.assertEqual(by_k[1]["class"], "safe", by_k[1])  # TPL-03 unchanged: the fix closes SSH, keeps the path
        self.assertEqual(by_k[1]["oracle_version"], "oracle-1.0")
        with self.assertRaises(SystemExit):  # labels are written once
            self.t.label_generation(export_dir=e.export_dir, pin=e.pin, split="test", private=p.root,
                                    manifest_pin=p.pin, runner_cache=runners, workers=1)


if __name__ == "__main__":
    unittest.main()
