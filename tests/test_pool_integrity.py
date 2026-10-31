"""The committed pool (D3 step 6, acceptance A2 to A5, A7, A9). Offline: it needs no cache, no network, no Terraform.

Everything is checked from the committed files: hashes, listing, ledger arithmetic, licence bucket, secrets,
one host per lineage, lineage coverage, sizes, and that the generated documents are exactly what the scripts
produce from the committed pool.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pool import cascade, redact, report  # noqa: E402

POOL = REPO_ROOT / "pool"


def entries() -> list[dict]:
    return json.loads((POOL / "pool.json").read_text(encoding="utf-8"))["entries"]


class TestCommittedPool(unittest.TestCase):
    def test_pool_json_is_committed(self) -> None:
        self.assertTrue((POOL / "pool.json").is_file(), "pool/pool.json must be committed")

    def test_verify_pool_finds_nothing(self) -> None:
        self.assertEqual(report.verify_pool(POOL), [])

    def test_the_funnel_starts_from_the_pinned_database(self) -> None:
        funnel = json.loads((POOL / "funnel.json").read_text(encoding="utf-8"))
        self.assertEqual(funnel["terrads_levels"]["F0"]["modules"], 394004)  # sources/terrads/yield_report.md
        self.assertEqual((funnel["sampling"]["seed"], funnel["sampling"]["host_accept_target"],
                          funnel["sampling"]["host_process_cap"]), (20261030, 400, 1500))

    def test_the_ledger_balances_for_each_candidate_set(self) -> None:
        funnel = json.loads((POOL / "funnel.json").read_text(encoding="utf-8"))
        for kind in cascade.KINDS:
            c = funnel["ledger"][kind]
            self.assertEqual(c["considered"], c["accepted"] + c["excluded"] + c["not_processed"], kind)
            self.assertEqual(c["accepted"], sum(1 for e in entries() if e["kind"] == kind), kind)

    def test_pins_are_recorded_and_match_the_repository_pins(self) -> None:
        pins = json.loads((POOL / "pool.json").read_text(encoding="utf-8"))["pins"]
        self.assertEqual(pins["terraform_required_version"], "~> 1.15.0")
        self.assertEqual(pins["terraform_ci_version"], "1.15.8")
        self.assertEqual(pins["aws_provider"], "6.53.0")
        self.assertEqual(pins["gitleaks"], "8.30.1")

    def test_every_real_world_entry_is_permissive_verified_secret_free_valid_and_in_a_lineage(self) -> None:
        for e in entries():
            if e["kind"] == "terragoat":
                continue
            with self.subTest(pool_id=e["pool_id"]):
                self.assertIn(e["licence_spdx"], {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD",
                                                  "Unlicense", "CC0-1.0", "Zlib", "MIT-0", "BSL-1.0"})
                self.assertEqual(e["secrets"], {"gitleaks_findings": 0, "inventory_flagged": 0})
                self.assertEqual(e["validate"]["status"], "valid")
                self.assertEqual(e["validate"]["provider_version"], "6.53.0")
                self.assertTrue(e["validate"]["terraform_version"].startswith("1.15."))
                self.assertRegex(e["lineage_id"], r"^lin-\d{12}$")
                self.assertTrue((POOL / e["dir"] / e["licence_file"]).is_file())

    def test_no_two_accepted_hosts_share_a_lineage(self) -> None:
        hosts = [e["lineage_id"] for e in entries() if e["kind"] == "host"]
        self.assertEqual(len(hosts), len(set(hosts)))

    def test_rescan_of_every_committed_tf_file_finds_no_credential_like_literal(self) -> None:
        for e in entries():
            with self.subTest(pool_id=e["pool_id"]):
                files = {f["path"]: (POOL / e["dir"] / f["path"]).read_text(encoding="utf-8") for f in e["files"]}
                self.assertEqual(redact.inventory_flags(files), [])

    @unittest.skipIf(redact.gitleaks_binary() is None, "pinned gitleaks 8.30.1 not in the cache; CI's gitleaks job scans the repository")
    def test_gitleaks_over_the_pool_directory_finds_nothing(self) -> None:
        binary = redact.gitleaks_binary()
        self.assertEqual(redact.gitleaks_findings(binary, POOL), [])

    def test_terragoat_is_redacted_logged_and_carries_the_apache_notice(self) -> None:
        goat = next(e for e in entries() if e["kind"] == "terragoat")
        directory = POOL / goat["dir"]
        self.assertEqual(goat["licence_spdx"], "Apache-2.0")
        self.assertIn("Apache License, Version 2.0", (directory / "NOTICE").read_text(encoding="utf-8"))
        self.assertIn("Apache License", (directory / "LICENSE.upstream").read_text(encoding="utf-8"))
        log = (directory / "REDACTION_LOG.md").read_text(encoding="utf-8")
        source = json.loads((directory / "SOURCE.json").read_text(encoding="utf-8"))
        self.assertEqual(source["redactions"], 6)  # 4 attributes + 2 map keys in lambda.tf (review fix)
        for attribute in ("access_key", "secret_key", "user_data"):
            self.assertIn(f"`{attribute}`", log)
        self.assertIn("`lambda.tf`", log)
        self.assertIn("aws_lambda_function", log)
        lambda_text = (directory / "lambda.tf").read_text(encoding="utf-8")
        for key in ("access_key", "secret_key"):
            self.assertNotIn(key, lambda_text)
        self.assertIn("sha256 upstream", log)

    def test_generated_documents_are_what_the_scripts_produce_from_the_committed_pool(self) -> None:
        view = report.load_view(POOL)
        self.assertEqual((POOL / "POOL_REPORT.md").read_text(encoding="utf-8"), report.render(view))
        datasheet = (REPO_ROOT / "DATASHEET.md").read_text(encoding="utf-8")
        self.assertEqual(report.update_datasheet(datasheet, report.datasheet_section(view)), datasheet)
        carryover = (REPO_ROOT / "docs" / "D4_CARRYOVER.md").read_text(encoding="utf-8")
        self.assertEqual(report.d4_carryover(view), carryover)

    def test_tampering_with_a_copy_of_the_committed_pool_is_detected(self) -> None:
        import shutil

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "pool"
            shutil.copytree(POOL, copy)
            target = next(p for p in sorted(copy.glob("terrads/host/*/*.tf")))
            target.write_bytes(target.read_bytes() + b"# edited after hashing\n")
            self.assertTrue(any("sha256" in p for p in report.verify_pool(copy)))


if __name__ == "__main__":
    unittest.main()
