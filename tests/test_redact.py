"""pool/redact.py: the secret scans (E09) and the TerraGoat redaction (D3-12).

Fake credentials are assembled at run time, so no literal in this file looks like a secret. The gitleaks
tests skip when the pinned 8.30.1 binary is not in the cache; the inventory tests always run.
"""

from __future__ import annotations

import difflib
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pool import redact  # noqa: E402

# Built at run time: matches gitleaks' aws-access-token shape without being one in the source text.
FAKE_KEY = "AKIA" + "QYLPMNSDRTUVWXYZ"
FAKE_PW = "change" + "me-" + "now1"  # low entropy on purpose: gitleaks skips it, the inventory does not
FAKE_USER_DATA_LINE = "export AWS_KEY=" + FAKE_KEY

TERRAGOAT_LIKE = (
    'provider "aws" {\n'
    f'  access_key = "{FAKE_KEY}"\n'
    f'  secret_key = "{FAKE_PW}x"\n'
    '  region     = "us-west-2"\n'
    "}\n"
    "\n"
    'resource "aws_instance" "web_host" {\n'
    '  ami           = "ami-0123456789abcdef0"\n'
    '  instance_type = "t2.nano"\n'
    "  user_data     = <<EOF\n"
    "#!/bin/bash\n"
    f"{FAKE_USER_DATA_LINE}\n"
    "EOF\n"
    "  tags = {\n"
    '    Name = "web"\n'
    "  }\n"
    "}\n"
    "\n"
    'resource "aws_db_instance" "db" {\n'
    "  password = var.db_password\n"
    '  engine   = "mysql"\n'
    "}\n"
)


class TestInventory(unittest.TestCase):
    def flags(self, text: str):
        return redact.inventory_flags({"main.tf": text})

    def test_literal_credential_attributes_are_flagged_with_address_and_kind(self) -> None:
        got = [(f.line, f.end_line, f.address, f.attribute, f.kind) for f in self.flags(TERRAGOAT_LIKE)]
        self.assertEqual(got, [
            (2, 2, "provider.aws", "access_key", "literal"),
            (3, 3, "provider.aws", "secret_key", "literal"),
            (10, 13, "aws_instance.web_host", "user_data", "heredoc"),
        ])

    def test_references_and_interpolations_are_not_flagged(self) -> None:
        text = ('resource "aws_db_instance" "d" {\n  password = var.p\n  token = "${var.t}"\n'
                '  secret_key = random_password.x.result\n}\n')
        self.assertEqual(self.flags(text), [])

    def test_function_wrapping_a_literal_is_flagged(self) -> None:
        text = 'resource "aws_instance" "i" {\n  user_data = base64encode("x")\n}\n'
        self.assertEqual([f.attribute for f in self.flags(text)], ["user_data"])

    def test_the_name_match_is_a_case_insensitive_substring(self) -> None:
        text = 'resource "aws_db_instance" "d" {\n  Master_Password = "abc"\n  api_key_id = "k"\n}\n'
        self.assertEqual([f.attribute for f in self.flags(text)], ["Master_Password", "api_key_id"])

    def test_no_value_is_kept_in_a_flag(self) -> None:
        dump = repr(self.flags(TERRAGOAT_LIKE))
        for secret in (FAKE_KEY, FAKE_PW, FAKE_USER_DATA_LINE):
            self.assertNotIn(secret, dump)

    def test_clean_module_has_no_flags(self) -> None:
        self.assertEqual(self.flags('resource "aws_vpc" "v" {\n  cidr_block = "10.0.0.0/16"\n}\n'), [])


LAMBDA_LIKE = (
    'resource "aws_lambda_function" "lf" {\n'
    '  runtime = "python3.9"\n'
    "  environment {\n"
    "    variables = {\n"
    f'      access_key = "{FAKE_KEY}"\n'
    f'      secret_key = "{FAKE_PW}x"\n'
    '      region     = "us-west-2"\n'
    "    }\n"
    "  }\n"
    "}\n"
)


class TestObjectKeysAndDenyList(unittest.TestCase):
    """D3 review fix: secret-named keys inside object literals are flagged; IMDSv2 settings are not."""

    def flags(self, text: str):
        return redact.inventory_flags({"main.tf": text})

    def test_secret_named_map_keys_are_flagged_with_their_container(self) -> None:
        got = [(f.line, f.end_line, f.address, f.attribute, f.kind, f.container) for f in self.flags(LAMBDA_LIKE)]
        self.assertEqual(got, [
            (5, 5, "aws_lambda_function.lf", "access_key", "literal", "environment.variables"),
            (6, 6, "aws_lambda_function.lf", "secret_key", "literal", "environment.variables"),
        ])

    def test_reference_values_in_a_map_are_not_flagged(self) -> None:
        text = 'locals {\n  m = {\n    password = var.p\n    token = "${var.t}"\n  }\n}\n'
        self.assertEqual(self.flags(text), [])

    def test_a_non_secret_key_is_not_flagged(self) -> None:
        self.assertEqual(self.flags('locals {\n  m = {\n    region = "x"\n  }\n}\n'), [])

    def test_literal_secret_key_in_a_single_line_object(self) -> None:
        self.assertEqual([f.attribute for f in self.flags('locals {\n  m = { token = "x" }\n}\n')], ["token"])

    def test_imdsv2_settings_are_never_flagged_as_attributes_or_keys(self) -> None:
        text = (
            'resource "aws_instance" "i" {\n'
            "  metadata_options {\n"
            '    http_tokens = "required"\n'
            '    http_put_response_hop_limit = "1"\n'
            "  }\n"
            "}\n"
            'locals {\n  m = {\n    http_tokens = "required"\n    HTTP_PUT_RESPONSE_HOP_LIMIT = "1"\n  }\n}\n'
        )
        self.assertEqual(self.flags(text), [])

    def test_the_deny_list_is_exactly_the_two_names_in_the_review(self) -> None:
        self.assertEqual(redact.DENY_LIST, frozenset({"http_tokens", "http_put_response_hop_limit"}))

    def test_other_token_names_are_still_flagged(self) -> None:
        self.assertEqual([f.attribute for f in self.flags('resource "aws_x" "y" {\n  api_token = "x"\n  http_tokens_extra = "y"\n}\n')],
                         ["api_token", "http_tokens_extra"])

    def test_no_value_is_kept_for_object_keys(self) -> None:
        dump = repr(self.flags(LAMBDA_LIKE))
        for secret in (FAKE_KEY, FAKE_PW):
            self.assertNotIn(secret, dump)

    def test_redaction_deletes_exactly_the_logged_map_lines(self) -> None:
        files = {"lambda.tf": LAMBDA_LIKE}
        plan = redact.plan_redactions(files)
        out = redact.apply_redactions(files, plan)["lambda.tf"]
        before, after = LAMBDA_LIKE.split("\n"), out.split("\n")
        self.assertEqual([n for n in range(1, len(before) + 1) if before[n - 1] not in after], [5, 6])
        self.assertEqual(len(after), len(before) - 2)
        self.assertIn('      region     = "us-west-2"', after)
        self.assertEqual(redact.inventory_flags({"lambda.tf": out}), [])
        import hcl_lex

        self.assertEqual(hcl_lex.headers_from_hcl(out).anomalies, 0)

    def test_log_names_file_line_address_and_key_but_no_value(self) -> None:
        files = {"lambda.tf": LAMBDA_LIKE}
        plan = redact.plan_redactions(files)
        log = redact.redaction_log(plan, files, redact.apply_redactions(files, plan), commit="c" * 40)
        for needle in ("lambda.tf", "aws_lambda_function.lf", "`access_key`", "`secret_key`", "environment.variables"):
            self.assertIn(needle, log)
        for secret in (FAKE_KEY, FAKE_PW):
            self.assertNotIn(secret, log)


GITLEAKS = redact.gitleaks_binary()


@unittest.skipIf(GITLEAKS is None, "pinned gitleaks 8.30.1 is not in the cache (CI's gitleaks job covers the repository)")
class TestGitleaks(unittest.TestCase):
    def scan(self, files: dict[str, str]) -> redact.SecretsResult:
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                (Path(tmp) / name).write_text(text, encoding="utf-8", newline="\n")
            return redact.scan_directory(GITLEAKS, Path(tmp))

    def test_gitleaks_catches_a_key_the_inventory_cannot_see(self) -> None:
        # the key sits in an attribute whose name the inventory does not match
        text = f'resource "aws_instance" "i" {{\n  description = "{FAKE_KEY}"\n}}\n'
        got = self.scan({"main.tf": text})
        self.assertGreaterEqual(got.gitleaks_findings, 1)
        self.assertEqual(got.inventory_flagged, 0)
        self.assertTrue(redact.has_secrets(got))

    def test_the_inventory_catches_secrets_gitleaks_misses(self) -> None:
        """The D1 lesson: gitleaks covered 1 of 4 TerraGoat secrets. These only the inventory sees: a user_data
        heredoc, and a provider access_key/secret_key pair that is not shaped like an AWS key."""
        text = (
            'provider "aws" {\n  access_key = "plain" \n  secret_key = "plain2"\n}\n'
            'resource "aws_instance" "i" {\n  user_data = <<EOF\n#!/bin/bash\necho hello\nEOF\n}\n'
        )
        got = self.scan({"main.tf": text})
        self.assertEqual(got.gitleaks_findings, 0)
        self.assertEqual(got.inventory_flagged, 3)
        self.assertTrue(redact.has_secrets(got))

    def test_a_literal_password_is_caught_by_both_scanners(self) -> None:
        """gitleaks has a rule for *_password literals in .tf files; the inventory flags it as well."""
        text = f'resource "aws_db_instance" "d" {{\n  master_password = "{FAKE_PW}"\n}}\n'
        got = self.scan({"main.tf": text})
        self.assertGreaterEqual(got.gitleaks_findings, 1)
        self.assertEqual(got.inventory_flagged, 1)

    def test_clean_module_reports_zero_and_zero(self) -> None:
        got = self.scan({"main.tf": 'resource "aws_vpc" "v" {\n  cidr_block = "10.0.0.0/16"\n}\n'})
        self.assertEqual((got.gitleaks_findings, got.inventory_flagged), (0, 0))
        self.assertFalse(redact.has_secrets(got))

    def test_no_value_reaches_the_result(self) -> None:
        text = f'resource "aws_instance" "i" {{\n  description = "{FAKE_KEY}"\n}}\n'
        self.assertNotIn(FAKE_KEY, repr(self.scan({"main.tf": text})))


class TestSecretsResultRule(unittest.TestCase):
    def test_either_scanner_alone_is_enough(self) -> None:
        self.assertTrue(redact.has_secrets(redact.SecretsResult(1, 0, (), ())))
        self.assertTrue(redact.has_secrets(redact.SecretsResult(0, 1, (), ())))
        self.assertFalse(redact.has_secrets(redact.SecretsResult(0, 0, (), ())))


class TestRedaction(unittest.TestCase):
    files = {"providers.tf": TERRAGOAT_LIKE}

    def test_plan_lists_the_flagged_attributes_with_their_line_ranges(self) -> None:
        plan = redact.plan_redactions(self.files)
        self.assertEqual([(r.file, r.line, r.end_line, r.address, r.attribute) for r in plan], [
            ("providers.tf", 2, 2, "provider.aws", "access_key"),
            ("providers.tf", 3, 3, "provider.aws", "secret_key"),
            ("providers.tf", 10, 13, "aws_instance.web_host", "user_data"),
        ])

    def test_redaction_removes_exactly_the_logged_lines_and_nothing_else(self) -> None:
        plan = redact.plan_redactions(self.files)
        out = redact.apply_redactions(self.files, plan)["providers.tf"]
        before, after = TERRAGOAT_LIKE.split("\n"), out.split("\n")
        logged = {n for r in plan for n in range(r.line, r.end_line + 1)}
        self.assertEqual(logged, {2, 3, 10, 11, 12, 13})
        ops = difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes()
        deleted: set[int] = set()
        for tag, i1, i2, _j1, _j2 in ops:
            self.assertIn(tag, ("equal", "delete"), "redaction may only delete lines")
            if tag == "delete":
                deleted |= set(range(i1 + 1, i2 + 1))
        self.assertEqual(deleted, logged)
        self.assertEqual(len(after), len(before) - len(logged))

    def test_the_rescan_of_the_redacted_text_is_clean_and_the_block_structure_survives(self) -> None:
        plan = redact.plan_redactions(self.files)
        out = redact.apply_redactions(self.files, plan)
        self.assertEqual(redact.inventory_flags(out), [])
        import hcl_lex

        self.assertEqual(hcl_lex.headers_from_hcl(out["providers.tf"]).anomalies, 0)
        self.assertEqual(hcl_lex.headers_from_hcl(out["providers.tf"]).managed,
                         {("aws_instance", "web_host"), ("aws_db_instance", "db")})
        for secret in (FAKE_KEY, FAKE_PW, FAKE_USER_DATA_LINE):
            self.assertNotIn(secret, out["providers.tf"])

    def test_skipping_one_redaction_is_caught_by_the_rescan(self) -> None:
        """Mutation: apply all but the last redaction. The rescan must still see a flagged attribute."""
        plan = redact.plan_redactions(self.files)
        partial = redact.apply_redactions(self.files, plan[:-1])
        left = redact.inventory_flags(partial)
        self.assertEqual([f.attribute for f in left], ["user_data"])
        self.assertTrue(left, "a skipped redaction must not pass the rescan")

    def test_other_files_are_untouched(self) -> None:
        files = {**self.files, "other.tf": 'resource "aws_vpc" "v" {\n}\n'}
        out = redact.apply_redactions(files, redact.plan_redactions(files))
        self.assertEqual(out["other.tf"], files["other.tf"])

    def test_log_has_names_lines_and_hashes_but_no_values(self) -> None:
        plan = redact.plan_redactions(self.files)
        after = redact.apply_redactions(self.files, plan)
        log = redact.redaction_log(plan, self.files, after, commit="c" * 40)
        for needle in ("providers.tf", "access_key", "secret_key", "user_data", "aws_instance.web_host",
                       hashlib.sha256(TERRAGOAT_LIKE.encode()).hexdigest(),
                       hashlib.sha256(after["providers.tf"].encode()).hexdigest()):
            self.assertIn(needle, log)
        for secret in (FAKE_KEY, FAKE_PW, FAKE_USER_DATA_LINE):
            self.assertNotIn(secret, log)
        self.assertNotIn("\r", log)

    def test_plan_is_deterministic(self) -> None:
        self.assertEqual(redact.plan_redactions(self.files), redact.plan_redactions(dict(reversed(list(self.files.items())))))


APACHE_HEAD = "                                 Apache License\n                           Version 2.0, January 2004\n"
COMMIT = "c" * 40


def make_clone(root: Path) -> Path:
    clone = root / "clone"
    aws = clone / "terraform" / "aws"
    (aws / "resources").mkdir(parents=True)
    (aws / "providers.tf").write_text(TERRAGOAT_LIKE, encoding="utf-8", newline="\n")
    (aws / "plain.tf").write_text('resource "aws_vpc" "v" {\n  cidr_block = "10.0.0.0/16"\n}\n', encoding="utf-8", newline="\n")
    (aws / "resources" / "payload.zip").write_bytes(b"PK")
    (clone / "LICENSE").write_text(APACHE_HEAD, encoding="utf-8", newline="\n")
    return clone


class TestBuildTerragoat(unittest.TestCase):
    def build(self, tmp: str):
        clone = make_clone(Path(tmp))
        dest = Path(tmp) / "pool" / "terragoat" / "aws"
        listing = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (clone / "terraform" / "aws").glob("*.tf")}
        summary = redact.build_terragoat(clone, dest, COMMIT, listing=listing, binary=GITLEAKS)
        return dest, summary, listing

    def test_writes_redacted_files_log_source_notice_and_licence(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as tmp:
            dest, summary, listing = self.build(tmp)
            self.assertEqual(sorted(p.name for p in dest.iterdir()),
                             ["LICENSE.upstream", "NOTICE", "REDACTION_LOG.md", "SOURCE.json", "plain.tf", "providers.tf"])
            self.assertEqual((dest / "plain.tf").read_text(encoding="utf-8"),
                             'resource "aws_vpc" "v" {\n  cidr_block = "10.0.0.0/16"\n}\n')
            written = (dest / "providers.tf").read_text(encoding="utf-8")
            for secret in (FAKE_KEY, FAKE_PW, FAKE_USER_DATA_LINE):
                self.assertNotIn(secret, written)
            source = json.loads((dest / "SOURCE.json").read_text(encoding="utf-8"))
            self.assertEqual(source["commit"], COMMIT)
            self.assertEqual(source["licence_spdx"], "Apache-2.0")
            by_path = {f["path"]: f for f in source["files"]}
            self.assertEqual(by_path["providers.tf"]["sha256"], hashlib.sha256((dest / "providers.tf").read_bytes()).hexdigest())
            self.assertEqual(by_path["providers.tf"]["upstream_sha256"], listing["providers.tf"])
            self.assertEqual(by_path["plain.tf"]["sha256"], by_path["plain.tf"]["upstream_sha256"])
            self.assertEqual(source["not_copied"], ["terraform/aws/resources/payload.zip"])
            self.assertEqual(summary["redactions"], 3)
            for name in ("NOTICE", "REDACTION_LOG.md", "SOURCE.json", "LICENSE.upstream", "providers.tf"):
                self.assertNotIn(b"\r", (dest / name).read_bytes(), name)
            self.assertIn("Apache License", (dest / "LICENSE.upstream").read_text(encoding="utf-8"))
            self.assertIn("Apache License, Version 2.0", (dest / "NOTICE").read_text(encoding="utf-8"))
            self.assertIn("REDACTION_LOG.md", (dest / "NOTICE").read_text(encoding="utf-8"))

    def test_an_upstream_file_that_differs_from_the_pinned_listing_stops_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = make_clone(Path(tmp))
            with self.assertRaises(redact.RedactionError) as ctx:
                redact.build_terragoat(clone, Path(tmp) / "out", COMMIT, listing={"providers.tf": "0" * 64, "plain.tf": "0" * 64},
                                       binary=GITLEAKS)
            self.assertIn("providers.tf", str(ctx.exception))

    def test_a_skipped_redaction_fails_the_rescan_and_nothing_is_published(self) -> None:
        """Mutation: a planner that misses an attribute must make the build refuse to write the pool."""
        original = redact.plan_redactions
        redact.plan_redactions = lambda files: original(files)[:-1]  # type: ignore[assignment]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                clone = make_clone(Path(tmp))
                dest = Path(tmp) / "out"
                with self.assertRaises(redact.RedactionError) as ctx:
                    redact.build_terragoat(clone, dest, COMMIT, listing=None, binary=GITLEAKS)
                self.assertIn("rescan", str(ctx.exception))
                self.assertEqual(list(dest.glob("*")) if dest.exists() else [], [])
        finally:
            redact.plan_redactions = original  # type: ignore[assignment]

    def test_stale_files_in_the_destination_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = make_clone(Path(tmp))
            dest = Path(tmp) / "out"
            dest.mkdir()
            (dest / "stale.tf").write_text("x", encoding="utf-8")
            redact.build_terragoat(clone, dest, COMMIT, listing=None, binary=GITLEAKS)
            self.assertFalse((dest / "stale.tf").exists())


if __name__ == "__main__":
    unittest.main()
