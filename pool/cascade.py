"""The exclusion cascade (D3-06): codes E01 to E08 are decided here, from the archive text and TerraDS metadata.

``evaluate`` applies the codes in order and returns the **first** one that matches. The later codes (E09 to
E12) need the network, gitleaks and Terraform and are decided by ``redact``, ``lineage``, ``licence`` and
``validate``; they are listed in ``CODES`` so that every ledger uses the same stable names.

Modules are read from ``TerraDS.tar.gz`` in memory (``iter_archive``); nothing is extracted. Only the
modules that pass E01 to E08 are staged, in a work directory outside the repository, for the expensive steps.
Standard library and ``sources/*`` only.
"""

from __future__ import annotations

import collections
import io
import json
import posixpath
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import hcl_lex
import lexical_crosscheck
import measure_yield as my

from pool import refs

CODES = (
    "E01_LICENCE_BUCKET",
    "E02_NOT_IN_ARCHIVE",
    "E03_ANALYSER_DIAGNOSTICS",
    "E04_LEXER_ANOMALY",
    "E05_METADATA_DISAGREES",
    "E06_MODULE_CALLS",
    "E07_DANGLING_REFERENCE",
    "E08_OVERSIZE",
    "E09_SECRET_FOUND",
    "E10_LINEAGE_DUPLICATE",
    "E11_LICENCE_UNVERIFIED",
    "E12_INVALID_UNDER_PIN",
)
MAX_TF_BYTES = 200 * 1024
MAX_TF_FILES = 40
KINDS = ("native", "host")
LISTED = 5  # how many names a detail text lists before saying "and N more"


@dataclass(frozen=True)
class Candidate:
    module_id: int
    repo_id: int
    path: str
    full_name: str
    commit_sha: str
    licence: str | None
    kind: str  # native | host
    has_diagnostics: bool
    n_calls: int
    rows: frozenset[tuple[str, str]]  # TerraDS Resources, managed (type, name)


@dataclass
class Verdict:
    code: str | None  # None: passed E01 to E08
    detail: str = ""
    group: str = ""  # the detail with module-specific names removed, for counting reasons
    n_files: int = 0
    total_bytes: int = 0


@dataclass
class Loaded:
    candidates: list[Candidate]
    e01_not_candidates: dict[str, int]  # F3 / G modules outside the permissive bucket, by kind
    funnel: dict[str, dict[str, int]]  # F0..X, modules and repositories
    extra: dict = field(default_factory=dict)


def _names(items) -> str:
    items = sorted(items)
    shown = ", ".join(items[:LISTED])
    return shown + (f" and {len(items) - LISTED} more" if len(items) > LISTED else "")


def effective_files(files: dict[str, bytes]) -> dict[str, str]:
    """The ``.tf`` files Terraform would load from the module directory, decoded for the lexer."""
    return {
        name: data.decode("utf-8", errors="replace")
        for name, data in files.items()
        if name.endswith(".tf") and not lexical_crosscheck.ignored_by_terraform(name)
    }


def evaluate(c: Candidate, files: dict[str, bytes] | None) -> Verdict:
    """First matching code of E01 to E08 for one candidate; ``files`` is None if its repository is not in
    the archive, otherwise the module directory's ``.tf`` files as raw bytes."""
    bucket = my.licence_bucket(c.licence)
    if bucket != "permissive":
        return Verdict("E01_LICENCE_BUCKET", f"licence {c.licence!r} is in bucket {bucket!r}", f"bucket {bucket}")
    if files is None:
        return Verdict("E02_NOT_IN_ARCHIVE", "repository is not in the archive", "repository absent")
    text = effective_files(files)
    if not text:
        return Verdict("E02_NOT_IN_ARCHIVE", "module directory has no usable *.tf file in the archive", "no *.tf file")
    n_files = len(text)
    total = sum(len(files[name]) for name in text)
    if c.has_diagnostics:
        return Verdict("E03_ANALYSER_DIAGNOSTICS", "TerraDS reported diagnostics for this module",
                       "TerraDS diagnostics", n_files, total)
    headers = {name: hcl_lex.headers_from_hcl(body) for name, body in sorted(text.items())}
    bad = [name for name, h in headers.items() if h.anomalies]
    if bad:
        count = sum(headers[name].anomalies for name in bad)
        return Verdict("E04_LEXER_ANOMALY", f"{count} anomalies (unbalanced braces or malformed header) in {_names(bad)}",
                       "unbalanced braces or malformed header", n_files, total)
    merged = hcl_lex.merge(list(headers.values()))
    if merged.managed != set(c.rows):
        lexical_only = {f"{t}.{n}" for t, n in merged.managed - set(c.rows)}
        metadata_only = {f"{t}.{n}" for t, n in set(c.rows) - merged.managed}
        type_differs = {t for t, _ in merged.managed} != {t for t, _ in c.rows}
        parts = []
        if lexical_only:
            parts.append(f"lexer only: {_names(lexical_only)}")
        if metadata_only:
            parts.append(f"TerraDS only: {_names(metadata_only)}")
        return Verdict("E05_METADATA_DISAGREES", "; ".join(parts),
                       "resource type set differs" if type_differs else "resource names differ", n_files, total)
    if merged.modules or c.n_calls:
        return Verdict("E06_MODULE_CALLS", f"{len(merged.modules)} module block(s) read, {c.n_calls} recorded by TerraDS",
                       "module call", n_files, total)
    dangling = refs.dangling_references(text)
    if dangling:
        types = sorted({a.split(".", 1)[0] for a in dangling})
        return Verdict("E07_DANGLING_REFERENCE", f"undefined: {_names(dangling)}",
                       "dangling reference to " + ", ".join(types[:LISTED]), n_files, total)
    if n_files > MAX_TF_FILES:
        return Verdict("E08_OVERSIZE", f"{n_files} files (limit {MAX_TF_FILES})", "more than 40 files", n_files, total)
    if total > MAX_TF_BYTES:
        return Verdict("E08_OVERSIZE", f"{total} bytes (limit {MAX_TF_BYTES})", "over 200 KiB", n_files, total)
    return Verdict(None, "", "", n_files, total)


# --------------------------------------------------------------------------- archive


def iter_archive(archive: Path, repo_ids: set[int]) -> Iterator[tuple[int, dict[str, dict[str, bytes]]]]:
    """Stream ``TerraDS.tar.gz`` once. For each wanted repository yields ``(repo_id, {module_path: {file name:
    raw bytes}})`` holding its ``.tf`` files. Nothing is written to disk."""
    with tarfile.open(archive, "r|gz") as outer:
        for member in outer:
            if not member.isfile() or not member.name.endswith(".tar.gz"):
                continue
            repo_id = int(member.name.removesuffix(".tar.gz").rsplit("/", 1)[-1])
            if repo_id not in repo_ids:
                continue
            blob = outer.extractfile(member).read()
            modules: dict[str, dict[str, bytes]] = {}
            with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as inner:
                for item in inner:
                    if not item.isfile() or "/" not in item.name:
                        continue
                    base = posixpath.basename(item.name)
                    if not base.endswith(".tf"):
                        continue
                    rel = item.name.split("/", 1)[1]
                    handle = inner.extractfile(item)
                    modules.setdefault(posixpath.dirname(rel) or ".", {})[base] = handle.read()
            yield repo_id, modules


# --------------------------------------------------------------------------- candidates


def load_candidates(db: Path) -> Loaded:
    """Natives (F3, permissive) and hosts (G, permissive) from the pinned database (D3-05)."""
    conn = my.connect_readonly(db)
    try:
        repos = my.load_repos(conn)
        modules = my.load_modules(conn)
        measured = my.measure(modules, repos)
        wanted: dict[int, str] = {}
        e01 = collections.Counter()
        for kind, level in (("native", "F3"), ("host", "G")):
            for row in measured["members"][level]:
                licence = repos.get(row.repo_id, {}).get("licence")
                if my.licence_bucket(licence) == "permissive":
                    wanted[row.module_id] = kind
                else:
                    e01[kind] += 1
        pairs: dict[int, set[tuple[str, str]]] = collections.defaultdict(set)
        for module_id, rtype, name in conn.execute("SELECT ModuleId, Type, Name FROM Resources WHERE ResourceType = 'Managed'"):
            if module_id in wanted:
                pairs[module_id].add((rtype, name))
    finally:
        conn.close()
    candidates = []
    for row in modules:
        kind = wanted.get(row.module_id)
        if kind is None:
            continue
        repo = repos[row.repo_id]
        candidates.append(
            Candidate(
                row.module_id, row.repo_id, row.path, repo["full_name"], repo["commit"], repo["licence"], kind,
                row.has_diagnostics, row.n_calls, frozenset(pairs[row.module_id]),
            )
        )
    candidates.sort(key=lambda c: c.module_id)
    return Loaded(candidates, {k: e01[k] for k in KINDS}, measured["funnel"])


# --------------------------------------------------------------------------- the filter run


def run_filter(db: Path, archive: Path, work: Path) -> dict:
    """E01 to E08 over every candidate. Writes ``cheap_results.jsonl`` and stages the survivors' files
    under ``work/stage/<module_id>/``; returns the counts."""
    loaded = load_candidates(db)
    by_repo: dict[int, list[Candidate]] = collections.defaultdict(list)
    for c in loaded.candidates:
        by_repo[c.repo_id].append(c)
    stage = work / "stage"
    work.mkdir(parents=True, exist_ok=True)
    verdicts: dict[int, Verdict] = {}
    seen: set[int] = set()

    def decide(c: Candidate, modules: dict[str, dict[str, bytes]] | None) -> None:
        files = None if modules is None else modules.get(c.path, {})
        verdict = evaluate(c, files)
        verdicts[c.module_id] = verdict
        if verdict.code is None:
            target = stage / str(c.module_id)
            target.mkdir(parents=True, exist_ok=True)
            for name, data in files.items():
                if name.endswith(".tf") and not lexical_crosscheck.ignored_by_terraform(name):
                    (target / name).write_bytes(data)

    for repo_id, modules in iter_archive(archive, set(by_repo)):
        seen.add(repo_id)
        for c in by_repo[repo_id]:
            decide(c, modules)
    for repo_id, group in by_repo.items():
        if repo_id not in seen:
            for c in group:
                decide(c, None)

    considered = collections.Counter()
    passed = collections.Counter()
    by_code: dict[str, collections.Counter] = {k: collections.Counter() for k in KINDS}
    with (work / "cheap_results.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for c in loaded.candidates:
            v = verdicts[c.module_id]
            considered[c.kind] += 1
            if v.code is None:
                passed[c.kind] += 1
            else:
                by_code[c.kind][v.code] += 1
            handle.write(json.dumps(
                {"module_id": c.module_id, "repo_id": c.repo_id, "kind": c.kind, "path": c.path,
                 "code": v.code, "detail": v.detail, "group": v.group, "n_files": v.n_files,
                 "bytes": v.total_bytes},
                sort_keys=True) + "\n")
    return {
        "considered": {k: considered[k] for k in KINDS},
        "passed": {k: passed[k] for k in KINDS},
        "by_code": {k: dict(sorted(by_code[k].items())) for k in KINDS},
        "e01_not_candidates": loaded.e01_not_candidates,
        "funnel": loaded.funnel,
    }
