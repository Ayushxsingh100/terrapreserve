"""D5a Step 3 (D5-02, D5-04): oracle skeleton. Written before the code (test-first).

1. ``oracle/`` is a package: ``VERSION.py`` (``ORACLE_VERSION = "oracle-0.1"``), ``inputs.py``, ``record.py``, ``README.md``.
2. ``inputs.build_working_copy`` copies a step's ``.tf`` files, adds the oracle-only provider block and a
   ``terraform.tfvars.json`` from ``variable_values``, and never writes into ``scenarios/`` (it refuses such a
   destination, and the step directory is byte-identical afterwards).
3. The provider block (D5-04) sets region us-east-1 and the four skip flags; its placeholder keys are built
   at run time and are not credential-shaped; no file under ``oracle/`` holds a credential-shaped literal;
   gitleaks finds nothing in a working copy (when the local gitleaks binary exists).
4. ``inputs.terraform_env`` carries no AWS variable except ``AWS_SHARED_CREDENTIALS_FILE`` and
   ``AWS_CONFIG_FILE``, which point to empty files.
5. ``record`` writes the D0 Decision 6 structures in a dry run only: every truth value is ``null``; it refuses
   to write into ``scenarios/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
GITLEAKS = Path.home() / ".terrapreserve-cache" / "tools" / "gitleaks-8.30.1" / "gitleaks.exe"
STEP = REPO_ROOT / "scenarios" / "dev" / "tp-v1-F3-0274" / "step_0"
INVARIANTS = ["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"]

# Credential shapes: AWS access key ids and 40-character secret-like tokens.
CREDENTIAL_SHAPES = [re.compile(r"\b(AKIA|ASIA|AGPA|AIDA|AROA|ANPA)[A-Z0-9]{16}\b"),
                     re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])")]


def _tree_digest(path: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(path.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(path)).encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


class TestOracleSkeleton(unittest.TestCase):
    def test_01_layout_and_version(self) -> None:
        for name in ("__init__.py", "VERSION.py", "inputs.py", "record.py", "README.md"):
            self.assertTrue((REPO_ROOT / "oracle" / name).is_file(), f"oracle/{name} missing")
        from oracle.VERSION import ORACLE_VERSION

        self.assertEqual(ORACLE_VERSION, "oracle-0.1")

    def test_02_working_copy_never_touches_scenarios(self) -> None:
        from oracle import inputs

        before = _tree_digest(STEP.parent)
        with self.assertRaises(ValueError):
            inputs.build_working_copy(STEP, {"x": 1}, REPO_ROOT / "scenarios" / "oracle-work")
        with self.assertRaises(ValueError):
            inputs.build_working_copy(STEP, {"x": 1}, STEP / "work")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "work"
            values = json.loads((STEP.parent / "scenario.json").read_text(encoding="utf-8"))["variable_values"]
            inputs.build_working_copy(STEP, values, dest)
            names = sorted(p.name for p in dest.iterdir())
            for f in STEP.glob("*.tf"):
                self.assertIn(f.name, names)
                self.assertEqual((dest / f.name).read_bytes(), f.read_bytes())
            self.assertIn(inputs.PROVIDER_FILE, names)
            self.assertEqual(json.loads((dest / "terraform.tfvars.json").read_text(encoding="utf-8")), values)
        self.assertEqual(_tree_digest(STEP.parent), before, "the scenario directory changed")
        self.assertFalse((REPO_ROOT / "scenarios" / "oracle-work").exists())

    def test_03_provider_block(self) -> None:
        from oracle import inputs

        text = inputs.provider_block()
        for needle in ('region                      = "us-east-1"', "skip_credentials_validation = true",
                       "skip_requesting_account_id  = true", "skip_metadata_api_check     = true",
                       "skip_region_validation      = true", "max_retries                 = 1",
                       "access_key", "secret_key"):
            self.assertIn(needle, text)
        for rx in CREDENTIAL_SHAPES:
            self.assertIsNone(rx.search(text), f"credential-shaped literal in the provider block: {rx.pattern}")
        for f in sorted((REPO_ROOT / "oracle").rglob("*")):
            if f.is_file() and f.suffix in (".py", ".md", ".tf", ".json"):
                body = f.read_text(encoding="utf-8")
                for rx in CREDENTIAL_SHAPES:
                    self.assertIsNone(rx.search(body), f"credential-shaped literal in {f.relative_to(REPO_ROOT)}")
                self.assertNotRegex(body, r'(access_key|secret_key)\s*=\s*"[^"$]', f"literal key in {f.name}")

    @unittest.skipUnless(GITLEAKS.is_file(), "local gitleaks 8.30.1 not installed")
    def test_04_gitleaks_clean_on_working_copy(self) -> None:
        from oracle import inputs

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "work"
            inputs.build_working_copy(STEP, {"tp_db_password": "tp-placeholder"}, dest)
            proc = subprocess.run([str(GITLEAKS), "dir", str(dest), "--no-banner", "--exit-code", "1"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_05_terraform_env_has_no_credentials(self) -> None:
        from oracle import inputs

        with tempfile.TemporaryDirectory() as tmp:
            env = inputs.terraform_env(Path(tmp), base={"AWS_ACCESS_KEY_ID": "x", "AWS_PROFILE": "p", "PATH": "p"})
            aws = {k for k in env if k.startswith("AWS_")}
            self.assertEqual(aws - {"AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE", "AWS_EC2_METADATA_DISABLED"},
                             set())
            for k in ("AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE"):
                self.assertEqual(Path(env[k]).read_text(encoding="utf-8"), "")
            self.assertNotIn("AWS_ACCESS_KEY_ID", env)

    def test_06_record_dry_run_only_nulls(self) -> None:
        from oracle import record

        sc = json.loads((STEP.parent / "scenario.json").read_text(encoding="utf-8"))
        labels, oracle_block = record.dry_run(sc, versions={"terraform": "1.15.8"})
        self.assertEqual(len(labels), len(sc["steps"]))
        for k, row in enumerate(labels):
            self.assertEqual(row["step"], k)
            self.assertEqual(row["invariant_truth"], {i: None for i in INVARIANTS})
            self.assertEqual(row["oracle_affected"], [])
            self.assertIsNone(row["target_safe"])
        self.assertEqual(oracle_block["disagreements"], [])
        self.assertEqual(oracle_block["versions"]["oracle"], "oracle-0.1")
        self.assertTrue(oracle_block["dry_run"])
        with self.assertRaises(ValueError):
            record.write_dry_run(sc, REPO_ROOT / "scenarios" / "dev" / "x.json", versions={})
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "labels.json"
            record.write_dry_run(sc, out, versions={})
            doc = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual({v for row in doc["labels"] for v in row["invariant_truth"].values()}, {None})


if __name__ == "__main__":
    unittest.main()
