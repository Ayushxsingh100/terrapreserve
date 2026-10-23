"""sources/manifest.json has the fields D1 Prompt B requires, with well-formed hashes."""

from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "sources" / "manifest.json"

REQUIRED = (
    "id",
    "kind",
    "url",
    "retrieved_utc",
    "size_bytes",
    "sha256",
    "licence_spdx",
    "licence_evidence",
    "notes",
)
KINDS = ("git", "zenodo", "pypi")
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX32 = re.compile(r"[0-9a-f]{32}")
UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def manifest_problems(manifest: dict) -> list[str]:
    problems: list[str] = []
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["no sources list"]
    ids = [s.get("id") for s in sources]
    if len(set(ids)) != len(ids):
        problems.append(f"duplicate ids: {ids}")
    for entry in sources:
        name = entry.get("id", "?")
        problems += [f"{name}: missing {f}" for f in REQUIRED if f not in entry]
        if entry.get("kind") not in KINDS:
            problems.append(f"{name}: kind {entry.get('kind')!r} not in {KINDS}")
        if not HEX64.fullmatch(str(entry.get("sha256", ""))):
            problems.append(f"{name}: sha256 is not 64 lowercase hex characters")
        if not str(entry.get("licence_spdx", "")).strip():
            problems.append(f"{name}: licence_spdx is empty")
        if not entry.get("licence_evidence"):
            problems.append(f"{name}: licence_evidence is empty")
        elif "sha256" in entry["licence_evidence"] and not HEX64.fullmatch(
            str(entry["licence_evidence"]["sha256"])
        ):
            problems.append(f"{name}: licence_evidence.sha256 is not 64 hex characters")
        if not UTC.fullmatch(str(entry.get("retrieved_utc", ""))):
            problems.append(f"{name}: retrieved_utc is not YYYY-MM-DDTHH:MM:SSZ")
        size = entry.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            problems.append(f"{name}: size_bytes is not a positive integer")
        if entry.get("kind") == "git" and not HEX40.fullmatch(str(entry.get("commit", ""))):
            problems.append(f"{name}: commit is not 40 hex characters")
        if entry.get("kind") == "zenodo":
            for field in ("md5_published", "md5_measured"):
                if not HEX32.fullmatch(str(entry.get(field, ""))):
                    problems.append(f"{name}: {field} is not 32 hex characters")
            if entry.get("md5_published") != entry.get("md5_measured"):
                problems.append(f"{name}: md5_published != md5_measured")
            if not str(entry.get("doi", "")).startswith("10.5281/zenodo."):
                problems.append(f"{name}: doi is not a Zenodo DOI")
        if entry.get("kind") == "pypi":
            if not HEX64.fullmatch(str(entry.get("sha256_published", ""))):
                problems.append(f"{name}: sha256_published is not 64 hex characters")
            if entry.get("sha256_published") != entry.get("sha256"):
                problems.append(f"{name}: sha256_published != sha256")
            if not entry.get("version"):
                problems.append(f"{name}: version is empty")
    return problems


def _good_manifest() -> dict:
    return {
        "sources": [
            {
                "id": "g", "kind": "git", "url": "https://example.invalid/g",
                "commit": "a" * 40, "retrieved_utc": "2026-10-23T00:00:00Z", "size_bytes": 5,
                "sha256": "b" * 64, "licence_spdx": "Apache-2.0",
                "licence_evidence": {"path": "LICENSE", "sha256": "c" * 64}, "notes": "n",
            },
            {
                "id": "z", "kind": "zenodo", "url": "https://example.invalid/z",
                "doi": "10.5281/zenodo.1", "md5_published": "d" * 32, "md5_measured": "d" * 32,
                "retrieved_utc": "2026-10-23T00:00:00Z", "size_bytes": 5, "sha256": "e" * 64,
                "licence_spdx": "CC-BY-4.0", "licence_evidence": {"value": "cc-by-4.0"}, "notes": "n",
            },
            {
                "id": "p", "kind": "pypi", "url": "https://example.invalid/p", "version": "1.0",
                "sha256_published": "f" * 64, "retrieved_utc": "2026-10-23T00:00:00Z",
                "size_bytes": 5, "sha256": "f" * 64, "licence_spdx": "Apache-2.0",
                "licence_evidence": {"path": "LICENSE", "sha256": "1" * 64}, "notes": "n",
            },
        ]
    }


class TestManifestChecker(unittest.TestCase):
    """Self-test: the checker accepts a good manifest and catches each kind of defect."""

    def test_accepts_good_manifest(self) -> None:
        self.assertEqual(manifest_problems(_good_manifest()), [])

    def test_catches_missing_field(self) -> None:
        for field in REQUIRED:
            with self.subTest(field=field):
                manifest = _good_manifest()
                del manifest["sources"][0][field]
                self.assertTrue(manifest_problems(manifest))

    def test_catches_bad_hashes(self) -> None:
        for mutate in (
            lambda e: e.update(sha256="b" * 63),
            lambda e: e.update(sha256="B" * 64),
            lambda e: e.update(sha256="g" * 64),
            lambda e: e.update(commit="a" * 39),
        ):
            manifest = _good_manifest()
            mutate(manifest["sources"][0])
            self.assertTrue(manifest_problems(manifest))

    def test_catches_empty_licence(self) -> None:
        manifest = _good_manifest()
        manifest["sources"][0]["licence_spdx"] = " "
        self.assertTrue(manifest_problems(manifest))

    def test_catches_zenodo_md5_mismatch(self) -> None:
        manifest = _good_manifest()
        manifest["sources"][1]["md5_measured"] = "0" * 32
        self.assertTrue(manifest_problems(manifest))

    def test_catches_pypi_sha_mismatch(self) -> None:
        manifest = copy.deepcopy(_good_manifest())
        manifest["sources"][2]["sha256"] = "0" * 64
        self.assertTrue(manifest_problems(manifest))


class TestCommittedManifest(unittest.TestCase):
    def test_manifest_is_well_formed(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest_problems(manifest), [])

    def test_manifest_covers_the_three_sources(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        ids = {s["id"] for s in manifest["sources"]}
        self.assertTrue({"terragoat", "terrads-sqlite", "terrads-tar-gz", "checkov"} <= ids)

    def test_checkov_lock_file_hash_matches(self) -> None:
        import hashlib

        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        entry = next(s for s in manifest["sources"] if s["id"] == "checkov")
        lock = REPO_ROOT / entry["lock_file"]["path"]
        data = lock.read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(data).hexdigest(), entry["lock_file"]["sha256"])
        self.assertEqual(data.count(b"\n"), entry["lock_file"]["lines"])
        self.assertIn(b"checkov==" + entry["version"].encode() + b"\n", data)

    def test_manifest_has_no_local_user_path(self) -> None:
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?i)[a-z]:[\\/]+users[\\/]")


if __name__ == "__main__":
    unittest.main()
