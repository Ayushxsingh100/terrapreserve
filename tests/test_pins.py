"""ADR-013: Terraform and AWS provider pins are identical in DAIL and here."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE = REPO_ROOT / "validation" / "smoke"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestPins(unittest.TestCase):
    def test_terraform_required_version(self) -> None:
        text = _read(SMOKE / "versions.tf")
        self.assertRegex(text, r'required_version\s*=\s*"~>\s*1\.15\.0"')

    def test_aws_provider_in_versions_tf(self) -> None:
        text = _read(SMOKE / "versions.tf")
        self.assertRegex(text, r'source\s*=\s*"hashicorp/aws"')
        self.assertRegex(text, r'version\s*=\s*"6\.53\.0"')

    def test_aws_provider_in_lock_file(self) -> None:
        text = _read(SMOKE / ".terraform.lock.hcl")
        block = re.search(r'provider "registry\.terraform\.io/hashicorp/aws" \{(.*?)\n\}', text, re.S)
        self.assertIsNotNone(block, "no hashicorp/aws block in the lock file")
        assert block is not None
        self.assertRegex(block.group(1), r'version\s*=\s*"6\.53\.0"')
        self.assertRegex(block.group(1), r'constraints\s*=\s*"6\.53\.0"')

    def test_ci_terraform_version(self) -> None:
        versions = re.findall(r'terraform_version:\s*"?([\d.]+)"?', _read(CI))
        self.assertEqual(versions, ["1.15.8"])

    def test_ci_python_version(self) -> None:
        versions = re.findall(r'python-version:\s*"?([\d.]+)"?', _read(CI))
        self.assertTrue(versions)
        self.assertEqual(set(versions), {"3.12"})


if __name__ == "__main__":
    unittest.main()
