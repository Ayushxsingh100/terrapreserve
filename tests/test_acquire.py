"""sources/acquire.py: file verification, the TerraDS pin rule and the cache guard.

Offline only: CI never downloads the large files.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "sources" / "terragoat"))

import acquire  # noqa: E402
import scan_secrets  # noqa: E402


class TestVerifyFile(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "blob.bin"
        self.path.write_bytes(b"terrapreserve" * 1000)
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_match_passes(self) -> None:
        self.assertIsNone(acquire.verify_file(self.path, self.sha, self.path.stat().st_size))

    def test_single_changed_byte_fails(self) -> None:
        data = bytearray(self.path.read_bytes())
        data[500] ^= 0x01
        self.path.write_bytes(bytes(data))
        problem = acquire.verify_file(self.path, self.sha, len(data))
        self.assertIsNotNone(problem)
        self.assertIn("sha256", problem)

    def test_size_mismatch_fails(self) -> None:
        self.assertIsNotNone(acquire.verify_file(self.path, self.sha, 1))

    def test_missing_file_fails(self) -> None:
        self.assertIsNotNone(acquire.verify_file(self.path.with_name("absent"), self.sha))

    def test_hash_file_reports_md5_and_sha256(self) -> None:
        digests = acquire.hash_file(self.path, ("md5", "sha256"))
        self.assertEqual(digests["sha256"], self.sha)
        self.assertEqual(digests["md5"], hashlib.md5(self.path.read_bytes()).hexdigest())


class TestTerraDsPinRule(unittest.TestCase):
    @staticmethod
    def _version(record_id: str, index: int, licence: str, keys: tuple[str, ...]) -> dict:
        return {
            "record_id": record_id, "index": index, "licence": licence,
            "publication_date": "2026-01-01",
            "files": [{"key": k, "size_bytes": 1, "checksum": "md5:x"} for k in keys],
        }

    def test_latest_is_pinned_when_licence_and_files_match(self) -> None:
        keys = ("a", "b")
        versions = [self._version("1", 0, "cc-by-4.0", keys), self._version("2", 1, "cc-by-4.0", keys)]
        self.assertEqual(acquire.choose_terrads_pin(versions)[0]["record_id"], "2")

    def test_first_is_pinned_when_latest_licence_changed(self) -> None:
        keys = ("a", "b")
        versions = [self._version("1", 0, "cc-by-4.0", keys), self._version("2", 1, "mit", keys)]
        pin, reason = acquire.choose_terrads_pin(versions)
        self.assertEqual(pin["record_id"], "1")
        self.assertIn("licence", reason)

    def test_first_is_pinned_when_file_structure_changed(self) -> None:
        versions = [
            self._version("1", 0, "cc-by-4.0", ("a", "b")),
            self._version("2", 1, "cc-by-4.0", ("a", "c")),
        ]
        self.assertEqual(acquire.choose_terrads_pin(versions)[0]["record_id"], "1")


class TestCacheAndLicence(unittest.TestCase):
    def test_cache_inside_repository_is_refused(self) -> None:
        with mock.patch.dict(os.environ, {"TERRAPRESERVE_CACHE": str(REPO_ROOT / "cache")}):
            with self.assertRaises(acquire.AcquireError):
                acquire.cache_root()

    def test_cache_outside_repository_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"TERRAPRESERVE_CACHE": tmp}):
                self.assertEqual(acquire.cache_root(), Path(tmp).resolve())

    def test_spdx_recognition(self) -> None:
        apache = (REPO_ROOT / "LICENSES" / "Apache-2.0.txt").read_text(encoding="utf-8")
        self.assertEqual(acquire.spdx_from_licence_text(apache), "Apache-2.0")
        self.assertIsNone(acquire.spdx_from_licence_text("All rights reserved."))


class TestSecretSummaryHasNoValues(unittest.TestCase):
    def test_render_copies_only_rule_ids_and_paths(self) -> None:
        marker = "".join(["not", "-a-", "real-", "value-", "1234"])
        finding = {
            "RuleID": "generic-api-key", "File": "terraform/aws/ec2.tf",
            "Secret": marker, "Match": marker, "Line": marker, "StartLine": 7,
        }
        text = scan_secrets.render("8.30.1", "a" * 40, {"dir": [finding], "git": []})
        self.assertNotIn(marker, text)
        self.assertIn("generic-api-key", text)
        self.assertIn("terraform/aws/ec2.tf", text)


if __name__ == "__main__":
    unittest.main()
