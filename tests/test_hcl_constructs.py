"""sources/hcl_lex.py construct flags (D3 step 2), on small synthetic text.

Expected values are written by hand from the rules in the D3 work package (section 3.3, D3-06/D3-08):
data sources, count, for_each, dynamic, locals, lifecycle and provisioners are flags, never exclusions.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))

import hcl_lex  # noqa: E402

FLAG_FIELDS = (
    "has_count", "has_for_each", "has_dynamic", "has_locals", "has_lifecycle",
    "has_provisioner", "has_terraform_block", "has_backend", "has_provider_block",
)


def true_flags(text: str) -> set[str]:
    got = hcl_lex.constructs_from_hcl(text)
    return {f for f in FLAG_FIELDS if getattr(got, f)}


class TestConstructFlags(unittest.TestCase):
    def test_empty_module_has_no_flags(self) -> None:
        got = hcl_lex.constructs_from_hcl('resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n')
        self.assertEqual(true_flags('resource "aws_vpc" "main" {}\n'), set())
        self.assertIsNone(got.terraform_required_version)
        self.assertEqual(got.provider_constraints, set())

    def test_count_and_for_each_on_a_resource(self) -> None:
        self.assertEqual(true_flags('resource "aws_instance" "w" {\n  count = 2\n}\n'), {"has_count"})
        self.assertEqual(true_flags('resource "aws_instance" "w" {\n  for_each = var.x\n}\n'), {"has_for_each"})

    def test_count_on_a_data_source_and_a_module_call_counts_too(self) -> None:
        self.assertEqual(true_flags('data "aws_ami" "a" {\n  count = 1\n}\n'), {"has_count"})
        self.assertEqual(true_flags('module "m" {\n  source = "./m"\n  for_each = var.x\n}\n'), {"has_for_each"})

    def test_count_inside_an_object_literal_or_nested_block_is_not_the_meta_argument(self) -> None:
        self.assertEqual(true_flags('resource "aws_instance" "w" {\n  tags = {\n    count = 1\n  }\n}\n'), set())
        self.assertEqual(true_flags('resource "aws_instance" "w" {\n  ebs_block_device {\n    count = 1\n  }\n}\n'), set())

    def test_attribute_names_that_only_start_with_count_are_not_flagged(self) -> None:
        self.assertEqual(true_flags('resource "aws_instance" "w" {\n  count_total = 1\n  for_each_x = 2\n}\n'), set())

    def test_dynamic_block_sets_only_has_dynamic(self) -> None:
        text = (
            'resource "aws_security_group" "sg" {\n'
            '  dynamic "ingress" {\n    for_each = var.ports\n    content {\n      from_port = ingress.value\n    }\n  }\n'
            "}\n"
        )
        self.assertEqual(true_flags(text), {"has_dynamic"})

    def test_locals_lifecycle_provisioner(self) -> None:
        self.assertEqual(true_flags("locals {\n  a = 1\n}\n"), {"has_locals"})
        self.assertEqual(
            true_flags('resource "aws_instance" "w" {\n  lifecycle {\n    create_before_destroy = true\n  }\n}\n'),
            {"has_lifecycle"},
        )
        self.assertEqual(
            true_flags('resource "aws_instance" "w" {\n  provisioner "local-exec" {\n    command = "true"\n  }\n}\n'),
            {"has_provisioner"},
        )

    def test_one_line_blocks_are_seen(self) -> None:
        text = 'resource "aws_instance" "w" {\n  lifecycle { create_before_destroy = true }\n}\n'
        self.assertEqual(true_flags(text), {"has_lifecycle"})

    def test_terraform_block_backend_and_required_version(self) -> None:
        text = 'terraform {\n  required_version = ">= 1.0"\n  backend "s3" {\n    bucket = "b"\n  }\n}\n'
        got = hcl_lex.constructs_from_hcl(text)
        self.assertEqual(true_flags(text), {"has_terraform_block", "has_backend"})
        self.assertEqual(got.terraform_required_version, ">= 1.0")

    def test_provider_block_and_legacy_version_constraint(self) -> None:
        text = 'provider "aws" {\n  region = "eu-west-1"\n  version = "~> 2.0"\n}\n'
        got = hcl_lex.constructs_from_hcl(text)
        self.assertEqual(true_flags(text), {"has_provider_block"})
        self.assertEqual(got.provider_constraints, {"aws=~> 2.0"})

    def test_required_providers_object_and_legacy_string_forms(self) -> None:
        obj = 'terraform {\n  required_providers {\n    aws = {\n      source = "hashicorp/aws"\n      version = "~> 5.0"\n    }\n  }\n}\n'
        legacy = 'terraform {\n  required_providers {\n    aws = "~> 3.0"\n  }\n}\n'
        self.assertEqual(hcl_lex.constructs_from_hcl(obj).provider_constraints, {"aws=~> 5.0"})
        self.assertEqual(hcl_lex.constructs_from_hcl(legacy).provider_constraints, {"aws=~> 3.0"})

    def test_required_providers_without_a_version_records_the_name_only(self) -> None:
        text = 'terraform {\n  required_providers {\n    aws = {\n      source = "hashicorp/aws"\n    }\n  }\n}\n'
        self.assertEqual(hcl_lex.constructs_from_hcl(text).provider_constraints, {"aws="})

    def test_words_in_comments_strings_and_heredocs_do_not_set_flags(self) -> None:
        text = (
            "# count = 3\n// lifecycle {\n/* locals { */\n"
            'resource "aws_instance" "w" {\n'
            '  description = "dynamic count for_each lifecycle provisioner"\n'
            "  user_data = <<EOT\nlocals {\nlifecycle {\ncount = 1\nEOT\n"
            "}\n"
        )
        self.assertEqual(true_flags(text), set())

    def test_merge_is_a_union_and_joins_required_versions(self) -> None:
        a = hcl_lex.constructs_from_hcl('resource "aws_instance" "w" {\n  count = 1\n}\n')
        b = hcl_lex.constructs_from_hcl('terraform {\n  required_version = "~> 1.0"\n}\nlocals {\n  x = 1\n}\n')
        got = hcl_lex.merge_constructs([a, b])
        self.assertTrue(got.has_count and got.has_locals and got.has_terraform_block)
        self.assertFalse(got.has_for_each)
        self.assertEqual(got.terraform_required_version, "~> 1.0")

    def test_two_different_required_versions_are_both_kept_sorted(self) -> None:
        a = hcl_lex.constructs_from_hcl('terraform {\n  required_version = ">= 1.2"\n}\n')
        b = hcl_lex.constructs_from_hcl('terraform {\n  required_version = "~> 1.0"\n}\n')
        self.assertEqual(hcl_lex.merge_constructs([b, a]).terraform_required_version, ">= 1.2; ~> 1.0")


class TestRemoveTopLevelBlocks(unittest.TestCase):
    """D3-09: the neutralisation removes top-level terraform and provider blocks, by brace depth."""

    def test_removes_terraform_and_provider_blocks_and_nothing_else(self) -> None:
        text = (
            'terraform {\n  required_version = ">= 1"\n  backend "s3" {\n    bucket = "b"\n  }\n}\n'
            'provider "aws" {\n  region = "r"\n}\n'
            'resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n'
        )
        got = hcl_lex.remove_top_level_blocks(text, ("terraform", "provider"))
        self.assertEqual(got, 'resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n')

    def test_nested_blocks_named_provider_inside_a_resource_stay(self) -> None:
        text = 'resource "aws_instance" "w" {\n  provider = aws.other\n  lifecycle {\n    x = 1\n  }\n}\n'
        self.assertEqual(hcl_lex.remove_top_level_blocks(text, ("terraform", "provider")), text)

    def test_braces_inside_strings_and_heredocs_do_not_confuse_the_depth(self) -> None:
        text = (
            'provider "aws" {\n  region = "}{"\n  x = <<EOT\n}\nEOT\n}\n'
            'resource "aws_vpc" "main" {\n}\n'
        )
        self.assertEqual(hcl_lex.remove_top_level_blocks(text, ("provider",)), 'resource "aws_vpc" "main" {\n}\n')

    def test_one_line_block_and_comment_before_it(self) -> None:
        text = '# note\nprovider "aws" { region = "r" }\nresource "aws_vpc" "main" {}\n'
        self.assertEqual(hcl_lex.remove_top_level_blocks(text, ("provider",)), '# note\nresource "aws_vpc" "main" {}\n')

    def test_text_without_those_blocks_is_unchanged_byte_for_byte(self) -> None:
        text = 'resource "aws_vpc" "main" {\r\n  cidr_block = "x"\r\n}\r\n'
        self.assertEqual(hcl_lex.remove_top_level_blocks(text, ("terraform", "provider")), text)


class TestObjectEntries(unittest.TestCase):
    """Keys of object literals, which attributes_from_hcl does not see (D3 review fix)."""

    @staticmethod
    def entries(text: str):
        return [(e.key, e.line, e.end_line, e.value_kind, e.top_level, e.container)
                for e in hcl_lex.object_entries_from_hcl(text)]

    def test_map_keys_inside_a_nested_block_attribute(self) -> None:
        text = (
            'resource "aws_lambda_function" "f" {\n'
            "  environment {\n"
            "    variables = {\n"
            '      access_key = "v1"\n'
            "      secret_key = var.s\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(self.entries(text), [
            ("access_key", 4, 4, "literal", "aws_lambda_function.f", "environment.variables"),
            ("secret_key", 5, 5, "reference", "aws_lambda_function.f", "environment.variables"),
        ])

    def test_single_line_object_and_comma_separated_entries(self) -> None:
        text = 'locals {\n  m = { a = "x", token = "y" }\n}\n'
        self.assertEqual([(k, v) for k, _l, _e, v, _t, _c in self.entries(text)], [("a", "literal"), ("token", "literal")])

    def test_string_keys_and_colon_separators(self) -> None:
        text = 'locals {\n  m = {\n    "access_key" = "x"\n    "password": "y"\n  }\n}\n'
        self.assertEqual([(k, v) for k, _l, _e, v, _t, _c in self.entries(text)], [("access_key", "literal"), ("password", "literal")])

    def test_nested_objects_name_their_container_path(self) -> None:
        text = 'locals {\n  outer = {\n    inner = {\n      password = "x"\n    }\n  }\n}\n'
        got = self.entries(text)
        self.assertEqual([(k, c) for k, _l, _e, _v, _t, c in got if k == "password"], [("password", "outer.inner")])

    def test_objects_inside_function_calls(self) -> None:
        text = 'locals {\n  m = merge({ password = "x" }, var.y)\n}\n'
        self.assertIn(("password", "literal"), [(k, v) for k, _l, _e, v, _t, _c in self.entries(text)])

    def test_heredoc_and_multiline_values_report_their_last_line(self) -> None:
        text = 'locals {\n  m = {\n    user_data = <<EOT\nline\nEOT\n    other = 1\n  }\n}\n'
        got = {k: (l, e, v) for k, l, e, v, _t, _c in self.entries(text)}
        self.assertEqual(got["user_data"], (3, 5, "heredoc"))

    def test_comparisons_and_for_expressions_are_not_keys(self) -> None:
        text = 'locals {\n  a = { for k, v in var.m : k => v }\n  b = var.x == "y" ? { z = 1 } : {}\n}\n'
        self.assertEqual([k for k, *_ in self.entries(text)], ["z"])

    def test_words_in_strings_and_comments_are_not_keys(self) -> None:
        text = 'locals {\n  # access_key = "x"\n  m = { note = "access_key = y" }\n}\n'
        self.assertEqual([k for k, *_ in self.entries(text)], ["note"])

    def test_plain_attributes_are_not_object_entries(self) -> None:
        self.assertEqual(self.entries('resource "aws_vpc" "v" {\n  cidr_block = "10.0.0.0/16"\n}\n'), [])


if __name__ == "__main__":
    unittest.main()
