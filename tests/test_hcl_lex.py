"""sources/hcl_lex.py, the lexical cross-check and the TerraGoat attribute inventory, on small inline HCL.

Fake credentials are assembled at run time so that no literal in this file looks like a secret.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for sub in ("sources", "sources/terrads", "sources/terragoat"):
    sys.path.insert(0, str(REPO_ROOT / sub))

import attribute_inventory  # noqa: E402
import hcl_lex  # noqa: E402
import lexical_crosscheck as lc  # noqa: E402


def managed_types(text: str) -> set[str]:
    return {t for t, _ in hcl_lex.headers_from_hcl(text).managed}


class TestHeaders(unittest.TestCase):
    def test_plain_blocks(self) -> None:
        text = (
            'resource "aws_instance" "web" {\n  ami = "x"\n}\n'
            'data "aws_ami" "a" {}\n'
            'module "m" {\n  source = "./m"\n}\n'
        )
        got = hcl_lex.headers_from_hcl(text)
        self.assertEqual(got.managed, {("aws_instance", "web")})
        self.assertEqual(got.data, {("aws_ami", "a")})
        self.assertEqual(got.modules, {"m"})
        self.assertEqual(got.anomalies, 0)

    def test_comment_containing_resource_text_is_ignored(self) -> None:
        text = (
            '# resource "aws_fake" "hash" {}\n'
            '// resource "aws_fake" "slashes" {}\n'
            '/* resource "aws_fake" "block" {\n}\n   module "also_fake" {} */\n'
            'resource "aws_vpc" "real" {\n  cidr_block = "10.0.0.0/16" # resource "aws_fake" "trailing" {}\n}\n'
        )
        got = hcl_lex.headers_from_hcl(text)
        self.assertEqual(got.managed, {("aws_vpc", "real")})
        self.assertEqual(got.modules, set())

    def test_heredoc_containing_resource_text_is_ignored(self) -> None:
        for opener in ("<<EOT", "<<-EOT"):
            with self.subTest(opener=opener):
                text = (
                    'resource "aws_instance" "web" {\n'
                    f"  user_data = {opener}\n"
                    '    resource "aws_fake" "inside_heredoc" {\n    }\n'
                    "  EOT\n"
                    "}\n"
                    'resource "aws_subnet" "after" {}\n'
                )
                got = hcl_lex.headers_from_hcl(text)
                self.assertEqual(got.managed, {("aws_instance", "web"), ("aws_subnet", "after")})
                self.assertEqual(got.anomalies, 0)

    def test_strings_with_comment_markers_and_braces(self) -> None:
        text = (
            'resource "aws_instance" "a" {\n'
            '  url = "http://example.invalid//path#frag"\n'
            '  tpl = "${join(",", ["}", "{"])}-${var.x}"\n'
            '  esc = "$${not_interpolated} \\" quote"\n'
            "}\n"
            'resource "aws_vpc" "b" {}\n'
        )
        got = hcl_lex.headers_from_hcl(text)
        self.assertEqual(got.managed, {("aws_instance", "a"), ("aws_vpc", "b")})
        self.assertEqual(got.anomalies, 0)

    def test_nested_blocks_do_not_count_as_top_level(self) -> None:
        text = 'resource "aws_instance" "a" {\n  dynamic "ingress" {\n    resource "aws_fake" "n" {}\n  }\n}\n'
        self.assertEqual(managed_types(text), {"aws_instance"})

    def test_one_line_blocks_and_bare_labels(self) -> None:
        text = 'resource "aws_vpc" "v" { cidr_block = "10.0.0.0/16" }\nresource aws_subnet s {\n}\n'
        self.assertEqual(managed_types(text), {"aws_vpc", "aws_subnet"})

    def test_unbalanced_braces_are_counted_as_anomalies(self) -> None:
        self.assertGreater(hcl_lex.headers_from_hcl('resource "aws_vpc" "v" {\n').anomalies, 0)


class TestJson(unittest.TestCase):
    def test_tf_json_module_resource_and_data(self) -> None:
        doc = {
            "module": {"net": {"source": "./net"}},
            "resource": {"aws_instance": {"web": {"ami": "x"}}, "aws_vpc": {"main": {}}},
            "data": {"aws_ami": {"base": {}}},
        }
        got = hcl_lex.headers_from_json(json.dumps(doc))
        self.assertEqual(got.modules, {"net"})
        self.assertEqual(got.managed, {("aws_instance", "web"), ("aws_vpc", "main")})
        self.assertEqual(got.data, {("aws_ami", "base")})

    def test_list_forms_and_bad_json(self) -> None:
        doc = {"resource": [{"aws_vpc": {"a": {}}}, {"aws_subnet": [{"b": {}}]}], "module": [{"m": {}}]}
        got = hcl_lex.headers_from_json(json.dumps(doc))
        self.assertEqual(got.managed, {("aws_vpc", "a"), ("aws_subnet", "b")})
        self.assertEqual(got.modules, {"m"})
        self.assertGreater(hcl_lex.headers_from_json("{not json").anomalies, 0)

    def test_analyse_module_merges_tf_and_tf_json(self) -> None:
        files = {
            "main.tf": 'resource "aws_instance" "web" {}\n',
            "extra.tf.json": json.dumps({"module": {"net": {}}, "resource": {"aws_db_instance": {"db": {}}}}),
        }
        lex = lc.lexical_flags(lc.analyse_module(files))
        self.assertEqual(lex["types"], {"aws_instance", "aws_db_instance"})
        self.assertTrue(lex["has_module_calls"])
        self.assertTrue(lex["is_F3"])  # both aws_instance and aws_db_instance, all in S
        self.assertTrue(lex["is_F2"])

    def test_terraform_ignores_hidden_and_editor_files(self) -> None:
        files = {
            ".hidden.tf": 'module "x" {}\n',
            "old.tf~": 'resource "aws_fake" "y" {}\n',
            "#auto#": 'resource "aws_fake" "z" {}\n',
            "main.tf": 'resource "aws_vpc" "v" {}\n',
        }
        lex = lc.lexical_flags(lc.analyse_module(files))
        self.assertEqual(lex["types"], {"aws_vpc"})
        self.assertFalse(lex["has_module_calls"])


class TestCompare(unittest.TestCase):
    def test_compare_flags_each_difference(self) -> None:
        base = {"types": {"aws_vpc"}, "pairs": {("aws_vpc", "v")}, "has_data": False, "has_module_calls": False,
                "is_F2": True, "is_F3": False}
        self.assertTrue(all(lc.compare(base, dict(base)).values()))
        other = dict(base, types={"aws_vpc", "aws_subnet"}, has_data=True)
        got = lc.compare(base, other)
        self.assertFalse(got["types"])
        self.assertFalse(got["has_data"])
        self.assertTrue(got["has_module_calls"])


class TestAttributes(unittest.TestCase):
    def setUp(self) -> None:
        self.marker = "".join(["not", "-", "a-", "real-", "value-", "42"])
        self.text = (
            'resource "aws_instance" "web" {\n'
            f'  user_data = <<-EOT\n    echo {self.marker}\n  EOT\n'
            f'  secret_key = "{self.marker}"\n'
            '  api_key = "${var.key}"\n'
            "  password = var.db_password\n"
            f'  token = base64encode("{self.marker}")\n'
            '  ami = "ami-123"\n'
            "  nested {\n"
            f'    private_key = "{self.marker}"\n'
            "  }\n"
            "}\n"
            'provider "aws" {\n'
            f'  access_key = "{self.marker}"\n'
            "}\n"
        )

    def test_kinds_lines_and_addresses(self) -> None:
        attrs = {a.name: a for a in hcl_lex.attributes_from_hcl(self.text)}
        self.assertEqual(attrs["user_data"].value_kind, "heredoc")
        self.assertEqual((attrs["user_data"].line, attrs["user_data"].end_line), (2, 4))
        self.assertEqual(attrs["secret_key"].line, 5)  # the line after the heredoc terminator
        self.assertEqual(attrs["secret_key"].value_kind, "literal")
        self.assertEqual(attrs["api_key"].value_kind, "interpolation-only")
        self.assertEqual(attrs["password"].value_kind, "reference")
        self.assertEqual(attrs["token"].value_kind, "call-with-literal")
        self.assertEqual(attrs["private_key"].block_path, ("aws_instance.web", "nested"))
        self.assertEqual(attrs["access_key"].top_level, "provider.aws")
        self.assertEqual(attrs["ami"].top_level, "aws_instance.web")

    def test_inventory_flags_only_literal_credential_like_attributes(self) -> None:
        flagged, rest = attribute_inventory.split_flagged(attribute_inventory.matching_attributes(self.text))
        self.assertEqual(
            sorted(a.name for a in flagged),
            ["access_key", "private_key", "secret_key", "token", "user_data"],
        )
        self.assertEqual(sorted(a.name for a in rest), ["api_key", "password"])

    def test_rendered_inventory_contains_no_value(self) -> None:
        flagged, rest = attribute_inventory.split_flagged(attribute_inventory.matching_attributes(self.text))
        rows = [
            {"file": "terraform/aws/x.tf", "line": a.line, "address": a.top_level, "block_path": a.block_path,
             "attribute": a.name, "kind": a.value_kind, "gitleaks": []}
            for a in flagged
        ]
        text = attribute_inventory.render(rows, __import__("collections").Counter(a.value_kind for a in rest), [], set())
        self.assertNotIn(self.marker, text)
        self.assertIn("secret_key", text)


class TestCommittedCrosscheck(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = json.loads((REPO_ROOT / "sources" / "terrads" / "crosscheck.json").read_text(encoding="utf-8"))

    def test_population_seed_and_method_are_recorded(self) -> None:
        self.assertEqual(self.doc["status"], "OK")
        self.assertEqual(self.doc["seed"], 20261023)
        self.assertEqual(self.doc["population"]["F2_sample"], 500)
        self.assertIn("random.Random(20261023).sample(sorted(F2 module ids), 500)", self.doc["population"]["sampling"]["F2_sample"])
        self.assertEqual(self.doc["files_read"][".tf"] > 0, True)

    def test_rates_are_consistent_and_every_disagreement_has_a_cause(self) -> None:
        for group, table in self.doc["agreement"].items():
            for name, cell in table.items():
                with self.subTest(group=group, comparison=name):
                    self.assertLessEqual(cell["agree"], cell["total"])
        self.assertEqual(self.doc["disagreement_count"], len(self.doc["disagreements"]))
        for item in self.doc["disagreements"]:
            self.assertNotEqual(item["likely_cause"], "not yet inspected")
            self.assertTrue(item["disagrees_on"])


class TestLicenceDiff(unittest.TestCase):
    def test_whitespace_only_changes_are_not_differences(self) -> None:
        import licence_diff

        self.assertEqual(licence_diff.compare("Apache License\n  Version 2.0", "Apache   License Version\t2.0\n"), [])
        diffs = licence_diff.compare("a b c d", "a b X d")
        self.assertEqual(len(diffs), 1)
        self.assertEqual((diffs[0][3], diffs[0][4]), ("c", "X"))


if __name__ == "__main__":
    unittest.main()
