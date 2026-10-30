"""pool/refs.py: resource references and the E07 dangling-reference check (D3 step 2).

Synthetic text only. The two cache-dependent positive controls (TerraDS modules 298829 and 311156, whose
symlinked files are absent from the archive) skip when the cache is missing; their synthetic twins run always.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "sources" / "terrads"))

from pool import refs  # noqa: E402


def refs_of(text: str) -> set[str]:
    return {f"{t}.{n}" for t, n in refs.referenced_addresses(text)}


class TestReferenceExtraction(unittest.TestCase):
    def test_plain_attribute_reference(self) -> None:
        self.assertEqual(refs_of("vpc_id = aws_vpc.main.id\n"), {"aws_vpc.main"})

    def test_index_and_splat_forms_reduce_to_the_root(self) -> None:
        self.assertEqual(refs_of("a = aws_instance.web[0].id\n"), {"aws_instance.web"})
        self.assertEqual(refs_of("a = aws_instance.web.*.id\n"), {"aws_instance.web"})
        self.assertEqual(refs_of("a = aws_instance.web[*].id\n"), {"aws_instance.web"})

    def test_depends_on_list(self) -> None:
        self.assertEqual(refs_of("depends_on = [aws_internet_gateway.igw, aws_vpc.main]\n"),
                         {"aws_internet_gateway.igw", "aws_vpc.main"})

    def test_interpolation_inside_a_string(self) -> None:
        self.assertEqual(refs_of('vpc_id = "${aws_vpc.main.id}"\n'), {"aws_vpc.main"})

    def test_interpolation_with_surrounding_text_and_functions(self) -> None:
        self.assertEqual(refs_of('name = "x-${aws_instance.web.id}-y"\n'), {"aws_instance.web"})
        self.assertEqual(refs_of('ids = "${join(",", aws_subnet.a.*.id)}"\n'), {"aws_subnet.a"})

    def test_interpolation_with_a_nested_quoted_string(self) -> None:
        self.assertEqual(refs_of('x = "${format("%s-%s", aws_subnet.a.id, "k")}"\n'), {"aws_subnet.a"})

    def test_template_directive_percent_brace(self) -> None:
        self.assertEqual(refs_of('x = "%{ if aws_instance.web.id != "" }y%{ endif }"\n'), {"aws_instance.web"})

    def test_interpolation_inside_a_heredoc_body(self) -> None:
        text = "user_data = <<EOT\n#!/bin/sh\necho ${aws_db_instance.db.address}\nEOT\n"
        self.assertEqual(refs_of(text), {"aws_db_instance.db"})

    def test_escaped_interpolation_is_literal(self) -> None:
        self.assertEqual(refs_of('x = "$${aws_vpc.main.id}"\n'), set())
        self.assertEqual(refs_of("x = <<EOT\n$${aws_vpc.main.id}\nEOT\n"), set())

    def test_comment_and_plain_string_that_look_like_addresses_are_ignored(self) -> None:
        text = (
            "# aws_vpc.main\n// aws_vpc.main\n/* aws_vpc.main */\n"
            'description = "see aws_vpc.main for details"\n'
            "note = <<EOT\naws_vpc.main\nEOT\n"
        )
        self.assertEqual(refs_of(text), set())

    def test_non_resource_roots_are_ignored(self) -> None:
        text = (
            "a = var.aws_vpc.main\nb = local.aws_vpc.main\nc = data.aws_ami.ubuntu.id\n"
            "d = module.net.aws_vpc.main\ne = each.value\nf = count.index\ng = self.id\n"
            "h = path.module\ni = terraform.workspace\n"
        )
        self.assertEqual(refs_of(text), set())

    def test_data_source_reference_is_not_a_managed_reference(self) -> None:
        self.assertEqual(refs_of('ami = "${data.aws_ami.ubuntu.id}"\n'), set())

    def test_block_header_labels_are_not_references(self) -> None:
        self.assertEqual(refs_of('resource "aws_instance" "web" {\n}\n'), set())
        self.assertEqual(refs_of('resource aws_instance web {\n}\n'), set())

    def test_two_part_names_only(self) -> None:
        self.assertEqual(refs_of("a = aws_vpc\nb = aws_vpc.\n"), set())


class TestDangling(unittest.TestCase):
    def test_reference_to_a_resource_defined_in_another_file_is_fine(self) -> None:
        files = {
            "main.tf": 'resource "aws_instance" "web" {\n  vpc_security_group_ids = [aws_security_group.sg.id]\n}\n',
            "sg.tf": 'resource "aws_security_group" "sg" {\n}\n',
        }
        self.assertEqual(refs.dangling_references(files), [])

    def test_missing_file_makes_the_reference_dangling(self) -> None:
        files = {"main.tf": 'resource "aws_instance" "web" {\n  vpc_security_group_ids = [aws_security_group.sg.id]\n}\n'}
        self.assertEqual(refs.dangling_references(files), ["aws_security_group.sg"])

    def test_dangling_through_interpolation(self) -> None:
        files = {"main.tf": 'resource "aws_instance" "web" {\n  subnet_id = "${aws_subnet.a.id}"\n}\n'}
        self.assertEqual(refs.dangling_references(files), ["aws_subnet.a"])

    def test_result_is_sorted_and_deduplicated(self) -> None:
        files = {"a.tf": "x = aws_vpc.v.id\ny = aws_vpc.v.arn\nz = aws_subnet.s.id\n"}
        self.assertEqual(refs.dangling_references(files), ["aws_subnet.s", "aws_vpc.v"])

    def test_a_resource_referencing_itself_is_not_dangling(self) -> None:
        files = {"a.tf": 'resource "aws_vpc" "v" {\n  x = aws_vpc.v.id\n}\n'}
        self.assertEqual(refs.dangling_references(files), [])

    def test_terraform_ignored_files_do_not_define_anything(self) -> None:
        files = {
            "main.tf": "x = aws_vpc.v.id\n",
            ".hidden.tf": 'resource "aws_vpc" "v" {\n}\n',
            "backup.tf~": 'resource "aws_vpc" "v" {\n}\n',
        }
        self.assertEqual(refs.dangling_references(files), ["aws_vpc.v"])

    def test_symlinked_file_twin_of_modules_298829_and_311156(self) -> None:
        """security.tf (a git symlink, absent from the archive) used to define the security group."""
        files = {
            "main.tf": 'resource "aws_instance" "chef" {\n  vpc_security_group_ids = ["${aws_security_group.chef.id}"]\n'
                       '  subnet_id = aws_subnet.a.id\n}\n',
        }
        self.assertEqual(refs.dangling_references(files), ["aws_security_group.chef", "aws_subnet.a"])


@unittest.skipUnless(
    (Path(os.environ.get("TERRAPRESERVE_CACHE") or Path.home() / ".terrapreserve-cache")
     / "terrads" / "20339474" / "TerraDS.tar.gz").is_file(),
    "TerraDS cache not present (CI has none); the synthetic twin above covers the rule",
)
class TestCacheDependentPositiveControls(unittest.TestCase):
    """Modules 298829 and 311156 have symlinked files absent from the archive (docs/D3_CARRYOVER.md item 2)."""

    def test_both_raise_e07_against_the_real_archive(self) -> None:
        import lexical_crosscheck as lc

        root = Path(os.environ.get("TERRAPRESERVE_CACHE") or Path.home() / ".terrapreserve-cache")
        archive = root / "terrads" / "20339474" / "TerraDS.tar.gz"
        wanted = {
            int(repo): {path: mid}
            for repo, path, mid in self._rows(root)
        }
        found, _n_tf, _n_json = lc.read_modules(archive, wanted)
        for module_id in (298829, 311156):
            with self.subTest(module=module_id):
                self.assertTrue(refs.dangling_references(found[module_id]), "expected a dangling reference")

    @staticmethod
    def _rows(root: Path):
        import measure_yield as my

        conn = my.connect_readonly(root / "terrads" / "20339474" / "TerraDS.sqlite")
        try:
            return conn.execute("SELECT RepositoryId, Path, Id FROM Modules WHERE Id IN (298829, 311156)").fetchall()
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
