"""Tests for Step 3: Graft builder, span-edit operators, and real-text verifier (D4b-03, D4b-05, D4b-06).

Written first per the test-first rule:
1. Graft names all start with tp_.
2. Deliberate clash with a host address, variable, local, output or module name is a hard error.
3. Host files in step directory differ from pool files only by the recorded transform (and pin file).
4. Graft files pass formatting checks.
5. Span-edit operators change exactly the recorded span and nothing else.
6. Real-text verifier fails when a record omits a change.
7. Real-text verifier fails when a record invents a change.
8. Real-text verifier fails when a byte outside the recorded spans changed.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# These imports will fail initially until generator/realworld/ is implemented
try:
    from generator.realworld import graft, span_edit, real_diff_verify
except ImportError:
    graft = None  # type: ignore
    span_edit = None  # type: ignore
    real_diff_verify = None  # type: ignore


class TestGraftBuilder(unittest.TestCase):
    def setUp(self) -> None:
        if graft is None:
            self.fail("generator/realworld/graft.py does not exist yet (test-first failure)")

    def test_graft_names_all_prefixed_tp(self) -> None:
        """Every resource and variable declared in graft files starts with tp_."""
        graft_files = graft.build_graft_files(seed=12345)
        self.assertIn("terrapreserve_graft.tf", graft_files)
        self.assertIn("terrapreserve_graft_variables.tf", graft_files)

        from sources import hcl_lex
        headers = hcl_lex.headers_from_hcl(graft_files["terrapreserve_graft.tf"])
        for rtype, rname in headers.managed:
            self.assertTrue(rname.startswith("tp_"), f"Resource {rtype}.{rname} missing tp_ prefix")

        var_headers = hcl_lex.tokenize(graft_files["terrapreserve_graft_variables.tf"])
        for i, tok in enumerate(var_headers):
            if tok.kind == "IDENT" and tok.text == "variable" and i + 1 < len(var_headers):
                var_name = var_headers[i + 1].text
                self.assertTrue(var_name.startswith("tp_"), f"Variable {var_name} missing tp_ prefix")

    def test_graft_clash_detection_raises_error(self) -> None:
        """A clash with host resource, variable, local, output or module name is a hard error."""
        # Host declares aws_instance.tp_app
        host_files = {
            "main.tf": """
resource "aws_instance" "tp_app" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
}
"""
        }
        with self.assertRaises(graft.GraftClashError):
            graft.validate_no_clash(host_files, seed=12345)

    def test_host_files_differ_only_by_recorded_transform(self) -> None:
        """Host files differ only by stripped provider/terraform blocks and pin file."""
        orig_text = """
terraform {
  required_version = ">= 1.0"
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_security_group" "web" {
  name = "web-sg"
}
"""
        transformed, transform_record = graft.neutralise_host_file("main.tf", orig_text)
        self.assertNotIn('provider "aws"', transformed)
        self.assertNotIn('terraform {', transformed)
        self.assertIn('resource "aws_security_group" "web"', transformed)
        self.assertIn("terraform", transform_record["removed_blocks"])
        self.assertIn("provider", transform_record["removed_blocks"])

    def test_graft_files_pass_fmt(self) -> None:
        """Emitted graft files pass terraform fmt -check."""
        import os
        import shutil
        import subprocess
        tf = shutil.which("terraform")
        if not tf:
            if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
                self.fail("terraform binary required in CI; cannot skip format test")
            self.skipTest("terraform binary not available in PATH")
        graft_files = graft.build_graft_files(seed=54321)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for fname, content in graft_files.items():
                (tmp_path / fname).write_text(content, encoding="utf-8", newline="\n")

            proc = subprocess.run(
                ["terraform", "fmt", "-check", "-recursive", str(tmp_path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(
                proc.returncode, 0,
                f"Graft files failed terraform fmt:\n{proc.stdout}\n{proc.stderr}"
            )


class TestSpanEditAndRealVerifier(unittest.TestCase):
    def setUp(self) -> None:
        if span_edit is None or real_diff_verify is None:
            self.fail("generator/realworld/ span_edit/real_diff_verify does not exist yet (test-first failure)")

    def test_span_edit_changes_exact_span_and_nothing_else(self) -> None:
        """Span-edit operators change exactly the recorded span and nothing else."""
        content = """
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t3.micro"
}
"""
        result = span_edit.apply_span_edit(
            content,
            target_address="aws_instance.web",
            target_attribute="instance_type",
            new_value='"t3.large"',
        )
        self.assertTrue(result.success)
        self.assertIn('"t3.large"', result.new_content)
        # Check that characters before and after the span are identical
        self.assertEqual(content[:result.start_offset], result.new_content[:result.start_offset])
        tail_orig = content[result.end_offset:]
        tail_new = result.new_content[result.start_offset + len('"t3.large"'):]
        self.assertEqual(tail_orig, tail_new)

    def test_real_text_verifier_catches_omitted_change(self) -> None:
        """Verifier raises error if a file change occurred but was omitted from mutation records."""
        step0 = {"main.tf": 'resource "aws_instance" "a" { instance_type = "t3.micro" }\n'}
        step1 = {"main.tf": 'resource "aws_instance" "a" { instance_type = "t3.large" }\n'}
        # Empty record
        records: list[dict] = []
        with self.assertRaises(real_diff_verify.RealDiffVerifyError):
            real_diff_verify.verify(step0, step1, records)

    def test_real_text_verifier_catches_invented_change(self) -> None:
        """Verifier raises error if record claims an edit that did not happen."""
        step0 = {"main.tf": 'resource "aws_instance" "a" { instance_type = "t3.micro" }\n'}
        step1 = {"main.tf": 'resource "aws_instance" "a" { instance_type = "t3.micro" }\n'}
        records = [{
            "step": 1,
            "operator": "test_op",
            "target_address": "aws_instance.a",
            "attribute": "instance_type",
            "before": '"t3.micro"',
            "after": '"t3.large"',
        }]
        with self.assertRaises(real_diff_verify.RealDiffVerifyError):
            real_diff_verify.verify(step0, step1, records)

    def test_real_text_verifier_catches_unrecorded_byte_change(self) -> None:
        """Verifier raises error if an unrecorded byte (outside recorded spans) changed."""
        step0 = {"main.tf": 'resource "aws_instance" "a" { instance_type = "t3.micro" }\n'}
        # instance_type changed and recorded, but a comment was also snuck in
        step1 = {"main.tf": 'resource "aws_instance" "a" { instance_type = "t3.large" } # sneaky comment\n'}
        records = [{
            "step": 1,
            "operator": "test_op",
            "target_address": "aws_instance.a",
            "attribute": "instance_type",
            "before": '"t3.micro"',
            "after": '"t3.large"',
        }]
        with self.assertRaises(real_diff_verify.RealDiffVerifyError):
            real_diff_verify.verify(step0, step1, records)


if __name__ == "__main__":
    unittest.main()
