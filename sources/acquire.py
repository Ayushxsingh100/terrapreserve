"""Acquire and pin the TerraPreserve sources (D1 Prompt B).

    py -3.12 sources/acquire.py plan     # sizes and disk check, no download
    py -3.12 sources/acquire.py fetch    # download into the cache, hash, write the manifest
    py -3.12 sources/acquire.py verify   # re-hash the cache against the manifest

Standard library only. Raw archives and clones live in the external cache
(``$TERRAPRESERVE_CACHE``, default ``~/.terrapreserve-cache``), never in the
repository (CLAUDE.md rule 6). Only ``sources/manifest.json`` and
``sources/terragoat/files.sha256`` are written into the repository.

Once ``sources/manifest.json`` exists, ``fetch`` re-acquires exactly what it
pins (commit, record id, version). It only resolves "latest" when an entry is
missing from the manifest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "sources" / "manifest.json"
TERRAGOAT_LISTING = REPO_ROOT / "sources" / "terragoat" / "files.sha256"
CHECKOV_LOCK = REPO_ROOT / "requirements-tools.lock.txt"

SCHEMA_VERSION = 1
CHUNK = 1024 * 1024
USER_AGENT = "terrapreserve-acquire/1 (research; stdlib urllib)"

TERRAGOAT_URL = "https://github.com/bridgecrewio/terragoat"
TERRAGOAT_API = "https://api.github.com/repos/bridgecrewio/terragoat"
TERRAGOAT_SUBDIR = "terraform/aws"
CHECKOV_REPO = "bridgecrewio/checkov"
TERRADS_RECORD = "14217386"  # the v1 record, from which the versions endpoint is reached
ZENODO_API = "https://zenodo.org/api/records"

# Required fields of every manifest entry (tests/test_manifest.py checks the same list).
REQUIRED_FIELDS = (
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
# The extra requirement of the TerraDS pin rule (Prompt B section 4).
TERRADS_PINNED_LICENCE = "cc-by-4.0"

# Extra room for the members extracted from the TerraDS archive, in bytes. The
# real figure is measured and reported once the extraction has been done.
EXTRACT_BUDGET = 4 * 1024**3
DISK_FACTOR = 3


class AcquireError(RuntimeError):
    """A measurement or check failed; the message is shown and the exit code is 1."""


# --------------------------------------------------------------------------- helpers


def cache_root() -> Path:
    raw = os.environ.get("TERRAPRESERVE_CACHE")
    root = Path(raw) if raw else Path.home() / ".terrapreserve-cache"
    root = root.resolve()
    if root == REPO_ROOT or REPO_ROOT in root.parents:
        raise AcquireError(f"the cache must be outside the repository, got {root}")
    return root


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _request(url: str, method: str = "GET", headers: dict[str, str] | None = None):
    hdrs = {"User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and urllib.parse.urlparse(url).hostname in ("api.github.com",):
        hdrs["Authorization"] = f"Bearer {token}"
    hdrs.update(headers or {})
    return urllib.request.Request(url, method=method, headers=hdrs)


def get_json(url: str, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(_request(url), timeout=60) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == retries:
                raise AcquireError(f"GET {url} failed: {exc}") from exc
            time.sleep(2 * attempt)
    raise AssertionError("unreachable")


def get_bytes(url: str) -> bytes:
    try:
        with urllib.request.urlopen(_request(url), timeout=60) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise AcquireError(f"GET {url} failed: {exc}") from exc


def head_size(url: str) -> int:
    try:
        with urllib.request.urlopen(_request(url, method="HEAD"), timeout=60) as resp:
            return int(resp.headers["Content-Length"])
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
        raise AcquireError(f"HEAD {url} failed: {exc}") from exc


def hash_file(path: Path, algorithms: tuple[str, ...] = ("sha256",)) -> dict[str, str]:
    digests = {name: hashlib.new(name) for name in algorithms}
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            for digest in digests.values():
                digest.update(chunk)
    return {name: digest.hexdigest() for name, digest in digests.items()}


def download(url: str, dest: Path, expected_size: int, attempts: int = 5) -> None:
    """Stream ``url`` to ``dest`` through a ``.part`` file, resuming after a drop."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for attempt in range(1, attempts + 1):
        have = part.stat().st_size if part.exists() else 0
        if have == expected_size:
            break
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with urllib.request.urlopen(_request(url, headers=headers), timeout=60) as resp:
                if have and resp.status != 206:
                    have = 0  # the server ignored Range; start again
                with part.open("ab" if have else "wb") as out:
                    while chunk := resp.read(CHUNK):
                        out.write(chunk)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            print(f"  download interrupted (attempt {attempt}/{attempts}): {exc}", file=sys.stderr)
            time.sleep(3 * attempt)
    size = part.stat().st_size if part.exists() else -1
    if size != expected_size:
        raise AcquireError(f"{dest.name}: got {size} bytes, expected {expected_size}")
    part.replace(dest)


def spdx_from_licence_text(text: str) -> str | None:
    """Recognise the SPDX id of a licence text, or ``None`` when it is not recognised."""
    flat = re.sub(r"\s+", " ", text)
    if "Apache License" in flat and "Version 2.0, January 2004" in flat:
        return "Apache-2.0"
    if "Mozilla Public License Version 2.0" in flat:
        return "MPL-2.0"
    return None


def git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode != 0:
        raise AcquireError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def lock_file_sha256(path: Path = CHECKOV_LOCK) -> str:
    """sha256 of the lock file with CRLF read as LF (the repository stores text files with LF)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_manifest() -> dict:
    if MANIFEST.is_file():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def entry_by_id(manifest: dict, entry_id: str) -> dict | None:
    return next((e for e in manifest.get("sources", []) if e.get("id") == entry_id), None)


# --------------------------------------------------------------------------- resolution


def resolve_terrads_versions() -> list[dict]:
    """Every version of the TerraDS concept record, oldest first."""
    hits = []
    url = f"{ZENODO_API}/{TERRADS_RECORD}/versions?size=25"  # Zenodo answers 400 to size=100
    while url:
        data = get_json(url)
        hits.extend(data["hits"]["hits"])
        url = data.get("links", {}).get("next")
    versions = []
    for hit in hits:
        meta = hit["metadata"]
        versions.append(
            {
                "record_id": str(hit["id"]),
                "doi": hit["doi"],
                "concept_doi": hit["conceptdoi"],
                "zenodo_version_field": meta.get("version"),
                "index": hit["metadata"]["relations"]["version"][0]["index"],
                "is_last": hit["metadata"]["relations"]["version"][0]["is_last"],
                "publication_date": meta["publication_date"],
                "licence": meta["license"]["id"],
                "title": meta["title"],
                "creators": [c["name"] for c in meta["creators"]],
                "files": [
                    {
                        "key": f["key"],
                        "size_bytes": f["size"],
                        "checksum": f["checksum"],
                    }
                    for f in sorted(hit["files"], key=lambda f: f["key"])
                ],
            }
        )
    return sorted(versions, key=lambda v: v["index"])


def choose_terrads_pin(versions: list[dict]) -> tuple[dict, str]:
    """Prompt B pin rule: the latest version if still CC-BY-4.0 with the same files."""
    first, latest = versions[0], versions[-1]
    same_files = [f["key"] for f in first["files"]] == [f["key"] for f in latest["files"]]
    if latest["licence"] == TERRADS_PINNED_LICENCE and same_files:
        reason = (
            f"latest version ({latest['record_id']}, published {latest['publication_date']}) "
            f"is {TERRADS_PINNED_LICENCE} and has the same file names as the first version "
            f"({first['record_id']}): {', '.join(f['key'] for f in latest['files'])}"
        )
        return latest, reason
    why = []
    if latest["licence"] != TERRADS_PINNED_LICENCE:
        why.append(f"latest licence is {latest['licence']}")
    if not same_files:
        why.append("the file names differ from the first version")
    return first, "first version pinned because " + "; ".join(why)


def resolve_terragoat() -> dict:
    meta = get_json(TERRAGOAT_API)
    branch = meta["default_branch"]
    head = get_json(f"{TERRAGOAT_API}/commits/{branch}")
    return {
        "default_branch": branch,
        "commit": head["sha"],
        "commit_date": head["commit"]["committer"]["date"],
        "archived": meta["archived"],
        "github_spdx": (meta.get("license") or {}).get("spdx_id"),
        "size_kb": meta["size"],
    }


def resolve_checkov() -> dict:
    data = get_json("https://pypi.org/pypi/checkov/json")
    version = data["info"]["version"]
    wheels = [
        f for f in data["releases"][version] if f["filename"].endswith(".whl") and not f["yanked"]
    ]
    if len(wheels) != 1:
        raise AcquireError(f"expected one wheel for checkov {version}, found {len(wheels)}")
    wheel = wheels[0]
    return {
        "version": version,
        "filename": wheel["filename"],
        "url": wheel["url"],
        "size_bytes": wheel["size"],
        "sha256_published": wheel["digests"]["sha256"],
        "upload_time": wheel["upload_time_iso_8601"],
    }


def checkov_tag(version: str) -> dict:
    ref = get_json(f"https://api.github.com/repos/{CHECKOV_REPO}/git/ref/tags/{version}")
    obj = ref["object"]
    kind = obj["type"]
    sha = obj["sha"]
    if kind == "tag":  # annotated tag: dereference to the commit
        tag = get_json(obj["url"])
        sha = tag["object"]["sha"]
    return {"tag": version, "tag_object_type": kind, "commit": sha}


# --------------------------------------------------------------------------- plan


def plan_items(manifest: dict) -> tuple[list[dict], dict]:
    """Network-only description of what ``fetch`` would download."""
    items: list[dict] = []
    context: dict = {}

    goat = resolve_terragoat()
    context["terragoat"] = goat
    items.append(
        {
            "id": "terragoat",
            "what": f"git clone {TERRAGOAT_URL} (GitHub API size, KB)",
            "bytes": goat["size_kb"] * 1024,
        }
    )

    versions = resolve_terrads_versions()
    context["terrads_versions"] = versions
    pinned = entry_by_id(manifest, "terrads-sqlite")
    if pinned:
        record = next(v for v in versions if v["record_id"] == pinned["record_id"])
        reason = "pinned in sources/manifest.json"
    else:
        record, reason = choose_terrads_pin(versions)
    context["terrads_pin"] = record
    context["terrads_pin_reason"] = reason
    for f in record["files"]:
        items.append(
            {
                "id": f"terrads {record['record_id']} {f['key']}",
                "what": f"Zenodo {record['record_id']}",
                "bytes": f["size_bytes"],
            }
        )
    # The first version's database is fetched as well, only to settle which published
    # count its data matches and to compare schemas with the pinned version.
    first = versions[0]
    if first["record_id"] != record["record_id"]:
        sql = next(f for f in first["files"] if f["key"] == "TerraDS.sqlite")
        items.append(
            {
                "id": f"terrads {first['record_id']} TerraDS.sqlite (comparison only)",
                "what": f"Zenodo {first['record_id']}",
                "bytes": sql["size_bytes"],
            }
        )

    checkov = resolve_checkov()
    context["checkov"] = checkov
    items.append({"id": "checkov wheel", "what": checkov["filename"], "bytes": checkov["size_bytes"]})
    return items, context


def disk_check(total_download: int, root: Path) -> tuple[int, int, bool]:
    probe = root
    while not probe.exists():
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    required = DISK_FACTOR * total_download + EXTRACT_BUDGET
    return free, required, free >= required


def cmd_plan(_args: argparse.Namespace) -> int:
    root = cache_root()
    manifest = load_manifest()
    items, context = plan_items(manifest)
    print(f"cache: {root}")
    print(f"{'item':<62}{'bytes':>14}")
    for item in items:
        print(f"{item['id']:<62}{item['bytes']:>14,}")
    total = sum(item["bytes"] for item in items)
    free, required, ok = disk_check(total, root)
    print(f"{'total download':<62}{total:>14,}")
    print(f"free disk at cache: {free:,} bytes")
    print(
        f"required: {DISK_FACTOR} x download + extraction budget "
        f"{EXTRACT_BUDGET:,} = {required:,} bytes"
    )
    print("TerraDS pin:", context["terrads_pin"]["record_id"], "-", context["terrads_pin_reason"])
    print("DISK OK" if ok else "NOT ENOUGH DISK SPACE")
    return 0 if ok else 1


# --------------------------------------------------------------------------- fetch


def fetch_terragoat(root: Path, manifest: dict, now: str) -> tuple[dict, str]:
    old = entry_by_id(manifest, "terragoat")
    clone = root / "terragoat"
    if old:
        commit = old["commit"]
        info = {k: old[k] for k in ("commit_date", "archived", "default_branch")}
        info["github_spdx"] = old.get("github_spdx")
    else:
        live = resolve_terragoat()
        commit = live["commit"]
        info = {k: live[k] for k in ("commit_date", "archived", "default_branch", "github_spdx")}
    # core.autocrlf must be off: Git for Windows defaults it to true, which would rewrite every
    # file with CRLF and make the recorded hashes differ from the committed (LF) blobs.
    plain = ("-c", "core.autocrlf=false", "-c", "core.longpaths=true")
    if not (clone / ".git").is_dir():
        clone.parent.mkdir(parents=True, exist_ok=True)
        git(*plain, "clone", "--quiet", TERRAGOAT_URL, str(clone))
    git("config", "core.autocrlf", "false", cwd=clone)
    git(*plain, "checkout", "--quiet", "--force", "--detach", commit, cwd=clone)
    head = git("rev-parse", "HEAD", cwd=clone)
    if head != commit:
        raise AcquireError(f"terragoat: checked out {head}, wanted {commit}")

    licence = clone / "LICENSE"
    if not licence.is_file():
        raise AcquireError("terragoat: no LICENSE file at the repository root")
    spdx = spdx_from_licence_text(licence.read_text(encoding="utf-8", errors="replace"))
    if spdx is None:
        spdx = "not yet established"
    licence_sha = hash_file(licence)["sha256"]
    listing = terragoat_listing(clone)
    TERRAGOAT_LISTING.parent.mkdir(parents=True, exist_ok=True)
    TERRAGOAT_LISTING.write_text(listing, encoding="utf-8", newline="\n")
    listing_sha = hashlib.sha256(listing.encode("utf-8")).hexdigest()
    n_files = listing.count("\n")
    entry = {
        "id": "terragoat",
        "kind": "git",
        "url": TERRAGOAT_URL,
        "commit": commit,
        "commit_date": info["commit_date"],
        "default_branch": info["default_branch"],
        "archived": info["archived"],
        "github_spdx": info["github_spdx"],
        "retrieved_utc": old["retrieved_utc"] if old else now,
        "size_bytes": sum(int(line.split()[1]) for line in listing.splitlines()),
        "sha256": listing_sha,
        "licence_spdx": spdx,
        "licence_evidence": {"path": "LICENSE", "sha256": licence_sha},
        "notes": (
            f"sha256 is the digest of sources/terragoat/files.sha256 ({n_files} files under "
            f"{TERRAGOAT_SUBDIR}/); size_bytes is their summed size. Hashes are of the files exactly as "
            "committed (LF; cloned with core.autocrlf=false). The clone holds deliberate "
            "fake secrets; see sources/terragoat/secret_scan_summary.md."
        ),
    }
    return entry, listing


def terragoat_listing(clone: Path) -> str:
    """``<sha256>  <size>  <path>`` for every file under terraform/aws/, sorted by path."""
    base = clone / TERRAGOAT_SUBDIR
    if not base.is_dir():
        raise AcquireError(f"terragoat: {TERRAGOAT_SUBDIR}/ not found in the clone")
    lines = []
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        rel = path.relative_to(clone).as_posix()
        lines.append(f"{hash_file(path)['sha256']}  {path.stat().st_size}  {rel}\n")
    return "".join(lines)


def zenodo_entry(
    root: Path, record: dict, file: dict, entry_id: str, old: dict | None, now: str, notes: str
) -> dict:
    dest = root / "terrads" / record["record_id"] / file["key"]
    url = f"{ZENODO_API}/{record['record_id']}/files/{urllib.parse.quote(file['key'])}/content"
    if not dest.is_file() or dest.stat().st_size != file["size_bytes"]:
        print(f"downloading {file['key']} ({file['size_bytes']:,} bytes) from record {record['record_id']}")
        download(url, dest, file["size_bytes"])
    digests = hash_file(dest, ("md5", "sha256"))
    published = file["checksum"].removeprefix("md5:")
    if digests["md5"] != published:
        raise AcquireError(
            f"STOP: md5 mismatch for {file['key']} (record {record['record_id']}): "
            f"published {published}, measured {digests['md5']}"
        )
    if old and old["sha256"] != digests["sha256"]:
        raise AcquireError(f"STOP: {file['key']} sha256 differs from the manifest")
    return {
        "id": entry_id,
        "source": "terrads",
        "kind": "zenodo",
        "url": f"https://zenodo.org/records/{record['record_id']}/files/{urllib.parse.quote(file['key'])}",
        "record_id": record["record_id"],
        "doi": record["doi"],
        "concept_doi": record["concept_doi"],
        "cache_path": dest.relative_to(root).as_posix(),
        "retrieved_utc": old["retrieved_utc"] if old else now,
        "size_bytes": dest.stat().st_size,
        "sha256": digests["sha256"],
        "md5_published": published,
        "md5_measured": digests["md5"],
        "licence_spdx": "CC-BY-4.0",
        "licence_evidence": {
            "source": f"Zenodo API {ZENODO_API}/{record['record_id']}, metadata.license.id",
            "value": record["licence"],
        },
        "notes": notes,
    }


def fetch_terrads(root: Path, manifest: dict, now: str) -> tuple[list[dict], list[dict], str]:
    versions = resolve_terrads_versions()
    pinned = entry_by_id(manifest, "terrads-sqlite")
    if pinned:
        record = next(v for v in versions if v["record_id"] == pinned["record_id"])
        reason = manifest["terrads_pin_reason"]
    else:
        record, reason = choose_terrads_pin(versions)
    entries = []
    names = {
        "TerraDS.sqlite": "terrads-sqlite",
        "TerraDS.tar.gz": "terrads-tar-gz",
        "HCL Dataset Tools.zip": "terrads-tools-zip",
    }
    for file in record["files"]:
        entry_id = names[file["key"]]
        entries.append(
            zenodo_entry(
                root, record, file, entry_id, entry_by_id(manifest, entry_id), now,
                f"Pinned TerraDS record {record['record_id']}. {reason}.",
            )
        )
    first = versions[0]
    if first["record_id"] != record["record_id"]:
        sql = next(f for f in first["files"] if f["key"] == "TerraDS.sqlite")
        entries.append(
            zenodo_entry(
                root, first, sql, "terrads-v1-sqlite", entry_by_id(manifest, "terrads-v1-sqlite"),
                now,
                "Comparison only, not part of the pool: the first TerraDS version's database, "
                "fetched to settle which published repository count it matches and to compare "
                "its schema with the pinned version.",
            )
        )
    return entries, versions, reason


def fetch_checkov(root: Path, manifest: dict, now: str) -> dict:
    old = entry_by_id(manifest, "checkov")
    if old:
        live = {
            "version": old["version"],
            "filename": old["wheel_filename"],
            "url": old["url"],
            "size_bytes": old["size_bytes"],
            "sha256_published": old["sha256_published"],
            "upload_time": old["upload_time"],
        }
    else:
        live = resolve_checkov()
    dest = root / "checkov" / live["filename"]
    if not dest.is_file() or dest.stat().st_size != live["size_bytes"]:
        download(live["url"], dest, live["size_bytes"])
    sha = hash_file(dest)["sha256"]
    if sha != live["sha256_published"]:
        raise AcquireError(
            f"STOP: checkov wheel sha256 mismatch: PyPI {live['sha256_published']}, measured {sha}"
        )
    tag = old["git_tag"] if old else checkov_tag(live["version"])
    licence_url = f"https://raw.githubusercontent.com/{CHECKOV_REPO}/{tag['commit']}/LICENSE"
    licence_bytes = get_bytes(licence_url)
    spdx = spdx_from_licence_text(licence_bytes.decode("utf-8", errors="replace"))
    entry = {
        "id": "checkov",
        "kind": "pypi",
        "url": live["url"],
        "version": live["version"],
        "wheel_filename": live["filename"],
        "upload_time": live["upload_time"],
        "git_tag": tag,
        "cache_path": dest.relative_to(root).as_posix(),
        "retrieved_utc": old["retrieved_utc"] if old else now,
        "size_bytes": dest.stat().st_size,
        "sha256": sha,
        "sha256_published": live["sha256_published"],
        "licence_spdx": spdx or "not yet established",
        "licence_evidence": {
            "path": "LICENSE",
            "git_commit": tag["commit"],
            "sha256": hashlib.sha256(licence_bytes).hexdigest(),
        },
        "notes": (
            "Reference tool only (advisory, DAIL C-12); nothing in generator/ or oracle/ imports "
            "it. Installed into .venv-tools and pinned in requirements-tools.txt; the full "
            "environment (`pip freeze --all`) is pinned in requirements-tools.lock.txt, whose "
            "sha256 is in lock_file."
        ),
    }
    if CHECKOV_LOCK.is_file():
        entry["lock_file"] = {
            "path": CHECKOV_LOCK.name,
            "sha256": lock_file_sha256(),
            "lines": CHECKOV_LOCK.read_bytes().count(b"\n"),
            "note": "output of `python -m pip freeze --all` in .venv-tools (Windows, Python 3.12.10)",
        }
    return entry


def cmd_fetch(_args: argparse.Namespace) -> int:
    root = cache_root()
    manifest = load_manifest()
    items, _context = plan_items(manifest)
    total = sum(item["bytes"] for item in items)
    free, required, ok = disk_check(total, root)
    print(f"download {total:,} bytes; free {free:,}; required {required:,}")
    if not ok:
        raise AcquireError("not enough free disk space (see `plan`); nothing was downloaded")
    root.mkdir(parents=True, exist_ok=True)
    now = utc_now()

    goat, _listing = fetch_terragoat(root, manifest, now)
    terrads, versions, reason = fetch_terrads(root, manifest, now)
    checkov = fetch_checkov(root, manifest, now)
    new = {
        "schema_version": SCHEMA_VERSION,
        "cache": "$TERRAPRESERVE_CACHE (default ~/.terrapreserve-cache); entries give cache_path relative to it",
        "terrads_pin_reason": reason,
        "terrads_versions": versions,
        "sources": [goat, *terrads, checkov],
    }
    MANIFEST.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {MANIFEST.relative_to(REPO_ROOT)}")
    return 0


# --------------------------------------------------------------------------- verify


def verify_file(path: Path, expected_sha256: str, expected_size: int | None = None) -> str | None:
    """``None`` when ``path`` matches, otherwise a one-line description of the mismatch."""
    if not path.is_file():
        return f"{path}: missing"
    if expected_size is not None and path.stat().st_size != expected_size:
        return f"{path.name}: size {path.stat().st_size} != {expected_size}"
    measured = hash_file(path)["sha256"]
    if measured != expected_sha256:
        return f"{path.name}: sha256 {measured} != {expected_sha256}"
    return None


def cmd_verify(_args: argparse.Namespace) -> int:
    root = cache_root()
    manifest = load_manifest()
    if not manifest:
        raise AcquireError("sources/manifest.json not found; run `fetch` first")
    problems: list[str] = []
    for entry in manifest["sources"]:
        if entry["kind"] == "git":
            clone = root / "terragoat"
            try:
                head = git("rev-parse", "HEAD", cwd=clone)
                listing = terragoat_listing(clone)
            except AcquireError as exc:
                problems.append(f"{entry['id']}: {exc}")
                continue
            if head != entry["commit"]:
                problems.append(f"{entry['id']}: HEAD {head} != {entry['commit']}")
            if git("status", "--porcelain", cwd=clone):
                problems.append(f"{entry['id']}: working tree differs from the commit (line endings or edits)")
            if hashlib.sha256(listing.encode("utf-8")).hexdigest() != entry["sha256"]:
                problems.append(f"{entry['id']}: file listing digest differs from the manifest")
            committed = TERRAGOAT_LISTING.read_text(encoding="utf-8") if TERRAGOAT_LISTING.is_file() else ""
            if committed != listing:
                problems.append(f"{entry['id']}: sources/terragoat/files.sha256 differs from the clone")
            licence = verify_file(clone / "LICENSE", entry["licence_evidence"]["sha256"])
            if licence:
                problems.append(f"{entry['id']} licence: {licence}")
        else:
            problem = verify_file(root / entry["cache_path"], entry["sha256"], entry["size_bytes"])
            if problem:
                problems.append(f"{entry['id']}: {problem}")
            lock = entry.get("lock_file")
            if lock and (not CHECKOV_LOCK.is_file() or lock_file_sha256() != lock["sha256"]):
                problems.append(f"{entry['id']}: {lock['path']} differs from the manifest")
        print(f"{entry['id']}: {'MISMATCH' if any(p.startswith(entry['id']) for p in problems) else 'ok'}")
    for problem in problems:
        print("MISMATCH", problem, file=sys.stderr)
    return 1 if problems else 0


# --------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="sizes and disk check, no download").set_defaults(func=cmd_plan)
    sub.add_parser("fetch", help="download into the cache, hash, write the manifest").set_defaults(func=cmd_fetch)
    sub.add_parser("verify", help="re-hash the cache against the manifest").set_defaults(func=cmd_verify)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except AcquireError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
