"""pool/validate.py: the D3-09 neutralisation and the terraform validate harness (E12).

The neutralisation and the result parser are pure and always tested. The tests that run Terraform need the
local Terraform 1.15.x and the cached provider mirror; without them they skip with the reason (CI has neither).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pool import validate  # noqa: E402

VPC = 'resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n'


class TestPinFile(unittest.TestCase):
    def test_pin_text_is_the_repository_pin_and_matches_the_smoke_configuration(self) -> None:
        smoke = (REPO_ROOT / "validation" / "smoke" / "versions.tf").read_text(encoding="utf-8")
        self.assertEqual(validate.PINS_TF, smoke)
        self.assertIn('required_version = "~> 1.15.0"', validate.PINS_TF)
        self.assertIn('version = "6.53.0"', validate.PINS_TF)
        self.assertIn('source  = "hashicorp/aws"', validate.PINS_TF)

    def test_pin_file_name_cannot_collide_with_a_module_file(self) -> None:
        self.assertNotEqual(validate.PIN_FILE_NAME, "versions.tf")
        self.assertTrue(validate.PIN_FILE_NAME.endswith(".tf"))


class TestNeutralise(unittest.TestCase):
    def test_terraform_and_provider_blocks_go_everything_else_stays_verbatim(self) -> None:
        files = {
            "main.tf": 'terraform {\n  required_version = ">= 99"\n}\nprovider "aws" {\n  region = "r"\n}\n' + VPC,
            "other.tf": 'resource "aws_subnet" "s" {\n  vpc_id = aws_vpc.main.id\n}\n',
        }
        got = validate.neutralise(files)
        self.assertEqual(got["main.tf"], VPC)
        self.assertEqual(got["other.tf"], files["other.tf"])
        self.assertEqual(got[validate.PIN_FILE_NAME], validate.PINS_TF)
        self.assertEqual(sorted(got), sorted([*files, validate.PIN_FILE_NAME]))

    def test_input_is_not_modified(self) -> None:
        files = {"main.tf": 'provider "aws" {}\n' + VPC}
        before = dict(files)
        validate.neutralise(files)
        self.assertEqual(files, before)

    def test_a_modules_own_versions_tf_is_kept_not_overwritten(self) -> None:
        files = {"versions.tf": 'terraform {\n  required_version = ">= 0.12"\n}\n', "main.tf": VPC}
        got = validate.neutralise(files)
        self.assertEqual(got["versions.tf"], "")
        self.assertEqual(got[validate.PIN_FILE_NAME], validate.PINS_TF)

    def test_provider_aliases_in_resources_are_not_removed(self) -> None:
        text = 'provider "aws" {\n  alias = "w"\n}\nresource "aws_vpc" "v" {\n  provider = aws.w\n}\n'
        self.assertEqual(validate.neutralise({"m.tf": text})["m.tf"], 'resource "aws_vpc" "v" {\n  provider = aws.w\n}\n')

    def test_non_tf_names_are_not_passed_through(self) -> None:
        got = validate.neutralise({"main.tf": VPC, "notes.txt": "x"})
        self.assertNotIn("notes.txt", got)


class TestParseResult(unittest.TestCase):
    @staticmethod
    def out(valid: bool, *diagnostics: tuple[str, str, str]) -> str:
        return json.dumps({
            "format_version": "1.0", "valid": valid,
            "diagnostics": [{"severity": s, "summary": summ, "detail": det} for s, summ, det in diagnostics],
        })

    def test_valid(self) -> None:
        self.assertEqual(validate.parse_result(self.out(True), 0), ("valid", ""))

    def test_valid_with_only_warnings(self) -> None:
        self.assertEqual(validate.parse_result(self.out(True, ("warning", "Deprecated argument", "d")), 0), ("valid", ""))

    def test_invalid_takes_the_first_error_summary_and_never_the_detail(self) -> None:
        text = self.out(False, ("warning", "A warning", "w"), ("error", "Unsupported argument", "secret-ish detail"),
                        ("error", "Second", "x"))
        status, klass = validate.parse_result(text, 1)
        self.assertEqual((status, klass), ("invalid", "Unsupported argument"))
        self.assertNotIn("detail", klass)

    def test_summary_is_cut_at_200_characters(self) -> None:
        status, klass = validate.parse_result(self.out(False, ("error", "x" * 500, "d")), 1)
        self.assertEqual((status, len(klass)), ("invalid", 200))

    def test_unparsable_output_is_an_error_not_a_verdict(self) -> None:
        self.assertEqual(validate.parse_result("not json", 1), ("error", "terraform output was not JSON"))
        self.assertEqual(validate.parse_result("", 0), ("error", "terraform output was not JSON"))

    def test_invalid_without_an_error_diagnostic_is_still_invalid(self) -> None:
        self.assertEqual(validate.parse_result(self.out(False), 1), ("invalid", "no error diagnostic"))


UNAVAILABLE = validate.unavailable_reason()


@unittest.skipIf(UNAVAILABLE, f"Terraform harness not available: {UNAVAILABLE}")
class TestWithTerraform(unittest.TestCase):
    harness: validate.Harness

    @classmethod
    def setUpClass(cls) -> None:
        cls.harness = validate.Harness.default()
        cls.harness.ensure_ready()

    def test_valid_module(self) -> None:
        got = self.harness.validate({"main.tf": VPC})
        self.assertEqual(got.status, "valid", got)
        self.assertTrue(got.terraform_version.startswith("1.15."), got)
        self.assertEqual(got.provider_version, "6.53.0")

    def test_invalid_attribute_is_invalid_with_a_class(self) -> None:
        got = self.harness.validate({"main.tf": VPC.replace("}\n", "  bogus_attribute = 1\n}\n")})
        self.assertEqual((got.status, got.error_class), ("invalid", "Unsupported argument"))

    def test_conflicting_terraform_and_provider_blocks_are_neutralised_away(self) -> None:
        text = 'terraform {\n  required_version = ">= 99"\n}\nprovider "aws" {\n  region = "us-east-1"\n}\n' + VPC
        self.assertEqual(self.harness.validate({"main.tf": text}).status, "valid")

    def test_reference_to_a_provider_alias_whose_block_was_removed_is_invalid(self) -> None:
        text = 'provider "aws" {\n  alias = "w"\n}\nresource "aws_vpc" "v" {\n  provider = aws.w\n  cidr_block = "10.0.0.0/16"\n}\n'
        self.assertEqual(self.harness.validate({"main.tf": text}).status, "invalid")

    def test_an_earlier_modules_files_do_not_leak_into_the_next_run(self) -> None:
        self.harness.validate({"a.tf": VPC.replace("main", "first")})
        got = self.harness.validate({"b.tf": 'resource "aws_subnet" "s" {\n  vpc_id = aws_vpc.first.id\n}\n'})
        self.assertEqual(got.status, "invalid")  # aws_vpc.first is gone: Reference to undeclared resource


if __name__ == "__main__":
    unittest.main()
