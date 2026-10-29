"""Upstream licence-file check (E11, D3-06).

TerraDS carries no licence files and its licence string is the GitHub API value at crawl time. For each
repository the licence file is fetched from ``raw.githubusercontent.com`` at the pinned commit
(``LatestCommitSha``), its SPDX id is detected from the text, and the two are compared.

* The file names are tried in the order ``LICENCE_NAMES``; the first hit wins. The result is cached per
  repository (so all of its modules share one fetch), outside the repository, and every outcome is written to
  ``pool/licence_checks.csv`` so that a rerun reads the committed file and makes no request.
* At most one request per second, up to ``ATTEMPTS`` tries per URL with back-off 2, 4, 8 seconds. A blocked or
  rate-limited call is recorded as ``error`` and the run continues. No token and no credential is used, and a
  result is never invented.
* ``detect_spdx`` recognises the permissive licences of D3-01 (and BSD variants, so that a mismatch can be
  told apart). Anything it does not recognise is ``None`` and counts as a mismatch, never as a match.

Standard library and ``sources/acquire`` only.
"""

from __future__ import annotations

import csv
import hashlib
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Callable

import acquire

LICENCE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING", "UNLICENSE")
MAX_BYTES = 100 * 1024
ATTEMPTS = 4
MIN_INTERVAL_SECONDS = 1.0
FINAL_OUTCOMES = ("found", "mismatch", "missing")  # an "error" row is retried on a rerun
CSV_FIELDS = ("repo_id", "full_name", "commit_sha", "file_name", "http_status", "bytes", "sha256",
              "detected_spdx", "terrads_spdx", "outcome", "detail")
URL = "https://raw.githubusercontent.com/{full_name}/{commit_sha}/{name}"
SHA_RE = re.compile(r"[0-9a-f]{40}")
MALFORMED = "(malformed)"


@dataclass(frozen=True)
class Check:
    repo_id: int
    full_name: str
    commit_sha: str
    file_name: str
    http_status: int
    bytes: int
    sha256: str
    detected_spdx: str
    terrads_spdx: str
    outcome: str  # found | mismatch | missing | error
    detail: str


# --------------------------------------------------------------------------- detection

_BSD_GRANT = ("redistribution and use in source and binary forms, with or without modification, "
              "are permitted provided that the following conditions are met")
_ISC_RE = re.compile(
    r"permission to use, copy, modify,? (?:and/or|and|or) distribute this software for any purpose "
    r"with or without fee is hereby granted(, provided that)?"
)


def _flat(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).lower()


def detect_spdx(text: str) -> str | None:
    """SPDX id of a licence text, or ``None`` when it is not one of the licences listed here."""
    exact = acquire.spdx_from_licence_text(text)  # Apache-2.0, MPL-2.0
    if exact:
        return exact
    t = _flat(text)
    if "boost software license" in t and "version 1.0" in t:
        return "BSL-1.0"
    if "cc0 1.0 universal" in t:
        return "CC0-1.0"
    if "this is free and unencumbered software released into the public domain" in t:
        return "Unlicense"
    if "provided 'as-is', without any express or implied warranty" in t and \
            "the origin of this software must not be misrepresented" in t:
        return "Zlib"
    if _BSD_GRANT in t:
        if "advertising materials" in t:
            return "BSD-4-Clause"
        if "neither the name of" in t and "endorse or promote" in t:
            if "no express or implied licenses to any party's patent rights are granted" in t:
                return "BSD-3-Clause-Clear"
            return "BSD-3-Clause"
        if "redistributions of source code must retain" in t and "redistributions in binary form must reproduce" in t:
            return "BSD-2-Clause"
    if "permission is hereby granted, free of charge, to any person obtaining a copy of this software " \
            "and associated documentation files" in t:
        if "the above copyright notice and this permission notice shall be included" in t:
            return "MIT"
        return "MIT-0"
    m = _ISC_RE.search(t)
    if m:
        return "ISC" if m.group(1) else "0BSD"
    return None


# --------------------------------------------------------------------------- fetching


class RateLimiter:
    """Spaces calls to ``wait`` at least ``interval`` seconds apart."""

    def __init__(self, interval: float = MIN_INTERVAL_SECONDS, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.interval, self.clock, self.sleep = interval, clock, sleep
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            remaining = self.interval - (self.clock() - self._last)
            if remaining > 0:
                self.sleep(remaining)
        self._last = self.clock()


def default_get(url: str) -> tuple[int, bytes]:
    """One GET, no credentials. HTTP errors return their status; network errors raise OSError."""
    request = urllib.request.Request(url, headers={"User-Agent": acquire.USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return resp.status, resp.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def _fetch(url: str, get, limiter: RateLimiter, sleep) -> tuple[int | None, bytes, str]:
    """(status, body, problem). Status is 200 or 404, or None after ``ATTEMPTS`` failed tries."""
    problem = ""
    for attempt in range(1, ATTEMPTS + 1):
        limiter.wait()
        try:
            status, body = get(url)
        except (OSError, ValueError) as exc:  # ValueError: a URL http.client refuses (control characters)
            status, body, problem = 0, b"", type(exc).__name__
        else:
            if status in (200, 404):
                return status, body, ""
            problem = f"HTTP {status}"
        if attempt < ATTEMPTS:
            sleep(2**attempt)
    return None, b"", problem


def _outcome(repo_id: int, full_name: str, sha: str, name: str, body: bytes, terrads: str | None) -> Check:
    detected = detect_spdx(body.decode("utf-8", errors="replace")) or ""
    expected = terrads or ""
    if detected and detected.casefold() == expected.casefold():
        outcome, detail = "found", ""
    elif detected:
        outcome, detail = "mismatch", f"file says {detected}, TerraDS says {expected or 'nothing'}"
    else:
        outcome, detail = "mismatch", "licence text not recognised"
    return Check(repo_id, full_name, sha, name, 200, len(body), hashlib.sha256(body).hexdigest(), detected, expected,
                 outcome, detail)


def check_repository(
    repo_id: int, full_name: str, commit_sha: str, terrads_spdx: str | None, *,
    get=default_get, limiter: RateLimiter | None = None, sleep=time.sleep,
    cache_dir: Path | None = None, known: dict[int, Check] | None = None,
) -> Check:
    """The E11 check of one repository: its licence file at the pinned commit against TerraDS's string."""
    prior = (known or {}).get(repo_id)
    if prior is not None and prior.outcome in FINAL_OUTCOMES and prior.commit_sha == commit_sha:
        return prior
    expected = terrads_spdx or ""
    if not SHA_RE.fullmatch(commit_sha):
        # TerraDS has a LatestCommitSha that holds a git warning and a hash; it is not repaired by guessing
        return Check(repo_id, full_name, MALFORMED, "", 0, 0, "", "", expected, "error",
                     "the pinned commit is not a 40-character lowercase hex string, so no file was requested")
    limiter = limiter or RateLimiter()
    folder = cache_dir / str(repo_id) if cache_dir is not None else None
    problems: list[str] = []
    for name in LICENCE_NAMES:
        if folder is not None:
            if (folder / f"{name}.404").is_file():
                continue
            if (folder / name).is_file():
                return _outcome(repo_id, full_name, commit_sha, name, (folder / name).read_bytes(), terrads_spdx)
        status, body, problem = _fetch(URL.format(full_name=full_name, commit_sha=commit_sha, name=name),
                                       get, limiter, sleep)
        if status is None:
            problems.append(f"{name}: {problem}")
            continue
        if status == 404:
            if folder is not None:
                folder.mkdir(parents=True, exist_ok=True)
                (folder / f"{name}.404").write_bytes(b"")
            continue
        if len(body) > MAX_BYTES:
            return Check(repo_id, full_name, commit_sha, name, 200, len(body), "", "", expected, "error",
                         "licence file larger than 100 KB")
        if folder is not None:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(body)
        return _outcome(repo_id, full_name, commit_sha, name, body, terrads_spdx)
    if problems:
        return Check(repo_id, full_name, commit_sha, "", 0, 0, "", "", expected, "error", "; ".join(problems))
    return Check(repo_id, full_name, commit_sha, "", 404, 0, "", "", expected, "missing",
                 f"all {len(LICENCE_NAMES)} names returned 404")


def cached_text(cache_dir: Path, check: Check) -> bytes | None:
    """The licence file bytes the check found, from the cache (``None`` if there is none)."""
    if not check.file_name:
        return None
    path = cache_dir / str(check.repo_id) / check.file_name
    return path.read_bytes() if path.is_file() else None


# --------------------------------------------------------------------------- the committed CSV


def write_checks(path: Path, checks: list[Check]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_FIELDS)
        for c in sorted(checks, key=lambda c: c.repo_id):
            writer.writerow([getattr(c, f) for f in CSV_FIELDS])


def read_checks(path: Path) -> dict[int, Check]:
    out: dict[int, Check] = {}
    types = {f.name: f.type for f in fields(Check)}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            values = {k: (int(v) if types[k] in ("int", int) else v) for k, v in row.items()}
            check = Check(**values)
            out[check.repo_id] = check
    return dict(sorted(out.items()))
