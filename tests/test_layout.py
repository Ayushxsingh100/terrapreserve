"""The repository layout (D1 Prompt A section 5.2) and the licence texts exist."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FILES = (
    "README.md",
    "CLAUDE.md",
    "DATASHEET.md",
    "LICENSE",
    "LICENSES/Apache-2.0.txt",
    "LICENSES/CC-BY-4.0.txt",
    "LICENSES/README.md",
    ".gitignore",
    ".gitattributes",
    "sources/README.md",
    "pool/README.md",
    "generator/README.md",
    "oracle/README.md",
    "scenarios/README.md",
    "validation/README.md",
    "validation/smoke/versions.tf",
    "validation/smoke/main.tf",
    "validation/smoke/.terraform.lock.hcl",
    ".github/workflows/ci.yml",
    # D3 (pool construction)
    "docs/D3_DECISIONS.md",
    "pool/__init__.py",
    "pool/build.py",
    "pool/cascade.py",
    "pool/lineage.py",
    "pool/refs.py",
    "pool/redact.py",
    "pool/licence.py",
    "pool/validate.py",
    "pool/report.py",
    "pool/assemble.py",
    "docs/D4_CARRYOVER.md",
    # D4a (scenario generator and controlled tier)
    "docs/D4_DECISIONS.md",
    "generator/__init__.py",
    "generator/model.py",
    "generator/emitter.py",
    "generator/VERSION.py",
    "generator/seed.py",
    "generator/diff_verify.py",
    "generator/templates/__init__.py",
    "generator/operators/__init__.py",
    "generator/writer.py",
    "scenarios/split.json",
    "scenarios/NOTICE",
)
DIRS = ("LICENSES", "sources", "pool", "generator", "oracle", "scenarios", "validation/smoke", "tests")

LICENCE_TITLES = {
    "LICENSE": ("Apache License", "Version 2.0, January 2004"),
    "LICENSES/Apache-2.0.txt": ("Apache License", "Version 2.0, January 2004"),
    "LICENSES/CC-BY-4.0.txt": ("Attribution 4.0 International",),
}


class TestLayout(unittest.TestCase):
    def test_files_exist(self) -> None:
        missing = [f for f in FILES if not (REPO_ROOT / f).is_file()]
        self.assertEqual(missing, [])

    def test_directories_exist(self) -> None:
        missing = [d for d in DIRS if not (REPO_ROOT / d).is_dir()]
        self.assertEqual(missing, [])

    def test_licence_texts_are_complete(self) -> None:
        for name, titles in LICENCE_TITLES.items():
            with self.subTest(file=name):
                text = (REPO_ROOT / name).read_text(encoding="utf-8")
                self.assertGreater(len(text.strip()), 0)
                for title in titles:
                    self.assertIn(title, text)

    def test_fmt_check_is_scoped_to_first_party_directories(self) -> None:
        """pool/ holds verbatim third-party text (D3-04); the fmt check must not cover it."""
        ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        fmt_lines = [ln.strip() for ln in ci.splitlines() if "terraform fmt" in ln and not ln.strip().startswith("#")]
        self.assertEqual(fmt_lines, ["- run: terraform fmt -check -recursive validation generator scenarios"])

    def test_terraform_lock_file_is_not_ignored(self) -> None:
        # check-ignore exits 0 if the path is ignored, 1 if it is not.
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", "validation/smoke/.terraform.lock.hcl"],
            cwd=REPO_ROOT,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
