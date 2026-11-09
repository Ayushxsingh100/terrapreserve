"""Tests for Step 2: Derived Natives (D4b-02).

Tests written first per test-first rule:
1. Literal password in aws_db_instance is redacted to var.db_password with variable added.
2. Module that already declares db_password is refused (DX01).
3. Module where the password literal appears elsewhere is refused (DX01).
4. Module with non-password findings is refused.
5. The password literal appears nowhere in any written output or DERIVED.md.
6. DERIVED.md rows hold file, line, address, attribute and hashes only.
7. Rescan of derived module yields zero findings.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# This import will fail until pool/derive.py is implemented
try:
    from pool import derive
except ImportError:
    derive = None  # type: ignore


class TestDerivedNatives(unittest.TestCase):
    def setUp(self) -> None:
        if derive is None:
            self.fail("pool/derive.py does not exist yet (test-first failure)")

    def test_fixture_redaction_and_variable_addition(self) -> None:
        """A fixture module with a literal password is redacted to var.db_password with variable added."""
        secret_pw = "P@ssw0rd99XYZSecret!"
        main_tf = f"""
resource "aws_db_instance" "test" {{
  allocated_storage   = 20
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  password            = "{secret_pw}"
  username            = "dbadmin"
  skip_final_snapshot = true
}}
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = Path(tmp) / "input"
            mod_dir.mkdir()
            (mod_dir / "main.tf").write_text(main_tf, encoding="utf-8")

            res = derive.transform_module(mod_dir, "test-mod-001")
            self.assertTrue(res.success, f"Transform failed: {res.refusal_code}")
            self.assertIsNotNone(res.derived_files)
            files = res.derived_files

            # Check password replaced with var.db_password
            self.assertIn("var.db_password", files["main.tf"])
            self.assertNotIn(secret_pw, files["main.tf"])

            # Check variable declared with no default
            all_text = "\n".join(files.values())
            self.assertIn('variable "db_password"', all_text)
            self.assertIn("sensitive = true", all_text)
            self.assertIn("string", all_text)
            self.assertNotIn("default =", all_text)

            # Check secret literal appears NOWHERE in any output file
            for fname, content in files.items():
                self.assertNotIn(secret_pw, content, f"Secret leaked in {fname}")

            # Check DERIVED.md has no secret value
            self.assertNotIn(secret_pw, res.derived_md)
            self.assertIn("aws_db_instance.test", res.derived_md)
            self.assertIn("password", res.derived_md)
            self.assertTrue("sha-256" in res.derived_md.lower() or "sha256" in res.derived_md.lower())

    def test_refuse_if_already_declares_db_password_dx01(self) -> None:
        """A module that already declares variable db_password must be refused with DX01."""
        main_tf = """
resource "aws_db_instance" "test" {
  allocated_storage = 20
  password          = "literalSecret123"
}
"""
        var_tf = """
variable "db_password" {
  type = string
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = Path(tmp) / "input"
            mod_dir.mkdir()
            (mod_dir / "main.tf").write_text(main_tf, encoding="utf-8")
            (mod_dir / "variables.tf").write_text(var_tf, encoding="utf-8")

            res = derive.transform_module(mod_dir, "test-mod-002")
            self.assertFalse(res.success)
            self.assertEqual(res.refusal_code, "DX01")
            self.assertIn("already declares", res.refusal_reason.lower())

    def test_refuse_if_password_literal_appears_elsewhere_dx01(self) -> None:
        """A module where the password literal appears anywhere else must be refused with DX01."""
        secret_pw = "SharedSecret123"
        main_tf = f"""
resource "aws_db_instance" "test" {{
  allocated_storage = 20
  password          = "{secret_pw}"
}}
resource "aws_instance" "app" {{
  ami           = "ami-12345"
  instance_type = "t3.micro"
  tags = {{
    Name = "{secret_pw}"
  }}
}}
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = Path(tmp) / "input"
            mod_dir.mkdir()
            (mod_dir / "main.tf").write_text(main_tf, encoding="utf-8")

            res = derive.transform_module(mod_dir, "test-mod-003")
            self.assertFalse(res.success)
            self.assertEqual(res.refusal_code, "DX01")
            self.assertIn("appears elsewhere", res.refusal_reason.lower())

    def test_refuse_if_other_findings_exist(self) -> None:
        """A module with findings other than db_instance password must be refused."""
        main_tf = """
resource "aws_db_instance" "test" {
  allocated_storage = 20
  password          = "dbsecret123"
}
resource "aws_instance" "app" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
  user_data     = <<-EOF
    #!/bin/bash
    echo "something"
  EOF
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = Path(tmp) / "input"
            mod_dir.mkdir()
            (mod_dir / "main.tf").write_text(main_tf, encoding="utf-8")

            res = derive.transform_module(mod_dir, "test-mod-004", candidate_exclusions=["inventory:user_data:heredoc"])
            self.assertFalse(res.success)
            self.assertIn("non-password", res.refusal_reason.lower())

    def test_derived_rescan_finds_zero_secrets(self) -> None:
        """Rescanning derived files with attribute inventory returns zero findings."""
        secret_pw = "AnotherSecretPassword99!"
        main_tf = f"""
resource "aws_db_instance" "test" {{
  allocated_storage   = 20
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  password            = "{secret_pw}"
  username            = "dbadmin"
  skip_final_snapshot = true
}}
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = Path(tmp) / "input"
            mod_dir.mkdir()
            (mod_dir / "main.tf").write_text(main_tf, encoding="utf-8")

            res = derive.transform_module(mod_dir, "test-mod-005")
            self.assertTrue(res.success)

            # Rescan with pool.redact inventory_flags
            from pool import redact
            flags = redact.inventory_flags(res.derived_files)
            self.assertEqual(len(flags), 0, f"Rescan found unexpected inventory flags: {flags}")


if __name__ == "__main__":
    unittest.main()
