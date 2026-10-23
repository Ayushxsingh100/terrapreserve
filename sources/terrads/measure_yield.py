"""Measure the TerraDS yield funnel (D1 Prompt B, section 5).

    py -3.12 sources/terrads/measure_yield.py <TerraDS.sqlite> [--out-dir DIR]
        [--archive-scan FILE] [--crosscheck FILE] [--pin-info FILE]

Reads the TerraDS database **read-only** and writes ``schema`` (see
``dump_schema``), ``yield.json``, ``yield_report.md``, ``candidates.csv`` and
``licence_inventory.csv``. Every number in those files is computed here.

The filter uses TerraDS's own metadata (its analyser is built on HashiCorp's
terraform-config-inspect, see the report), never DAIL's parser (ADR-013).
Standard library only; nothing here imports DAIL.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

# The nine supported resource types, copied from the Invariant Registry
# Specification v1, section 1.3 (DAIL commit 7ed7aaf). A test pins the sets.
T9 = frozenset(
    {
        "aws_vpc",
        "aws_subnet",
        "aws_route_table",
        "aws_route_table_association",
        "aws_internet_gateway",
        "aws_instance",
        "aws_security_group",
        "aws_security_group_rule",
        "aws_db_instance",
    }
)
# C-67: aws_db_subnet_group is tolerated (Registry section 2.7).
S = T9 | {"aws_db_subnet_group"}
SG_TYPES = frozenset({"aws_security_group", "aws_security_group_rule"})
GRAFT_TYPES = SG_TYPES | {"aws_subnet"}

PERMISSIVE = frozenset(
    {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Unlicense", "CC0-1.0", "Zlib"}
)
BUCKETS = ("permissive", "weak copyleft", "strong copyleft", "other/unknown")
LEVELS = ("F0", "F1", "F2", "F2a", "F2b", "F2ab", "F3", "F3ab", "F4", "G", "X")
LICENCE_LEVELS = ("F2", "F3", "F3ab", "G")
SEED = 20261023


def licence_bucket(licence: str | None) -> str:
    """Bucket a repository licence string; anything unlisted is ``other/unknown``."""
    if licence in PERMISSIVE:
        return "permissive"
    if licence is None:
        return "other/unknown"
    if licence == "MPL-2.0" or licence.startswith(("LGPL-", "EPL-")):
        return "weak copyleft"
    if licence.startswith(("GPL-", "AGPL-")):
        return "strong copyleft"
    return "other/unknown"


@dataclass(frozen=True)
class ModuleRow:
    module_id: int
    repo_id: int
    path: str
    managed_types: frozenset[str]
    n_managed: int
    n_data: int
    n_calls: int
    n_nonlocal_calls: int
    has_diagnostics: bool


def is_local_source(source: str) -> bool:
    return source in (".", "..") or source.startswith(("./", "../"))


def parse_module_calls(raw: str | None) -> tuple[int, int]:
    """(all calls, calls whose source is not a local path) from the ModuleCalls JSON."""
    calls = json.loads(raw) if raw else []
    calls = calls or []
    return len(calls), sum(1 for c in calls if not is_local_source(c.get("source", "")))


def flags(row: ModuleRow) -> dict[str, bool]:
    """Funnel membership of one module."""
    types = row.managed_types
    f1 = any(t.startswith("aws_") for t in types)
    f2 = row.n_managed >= 1 and types <= S
    f2a = f2 and row.n_data == 0
    f2b = f2 and row.n_calls == 0
    f3 = f2 and {"aws_instance", "aws_db_instance"} <= types
    return {
        "F0": True,
        "F1": f1,
        "F2": f2,
        "F2a": f2a,
        "F2b": f2b,
        "F2ab": f2a and f2b,
        "F3": f3,
        "F3ab": f3 and f2a and f2b,
        "F4": f3 and bool(types & SG_TYPES),
        "G": f2 and not f3 and bool(types & GRAFT_TYPES),
        "X": {"aws_instance", "aws_db_instance"} <= types,
    }


def connect_readonly(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)


def load_modules(conn: sqlite3.Connection) -> list[ModuleRow]:
    types: dict[int, set[str]] = collections.defaultdict(set)
    managed: collections.Counter[int] = collections.Counter()
    data: collections.Counter[int] = collections.Counter()
    for module_id, kind, rtype, n in conn.execute(
        "SELECT ModuleId, ResourceType, Type, COUNT(*) FROM Resources GROUP BY ModuleId, ResourceType, Type"
    ):
        if kind == "Managed":
            types[module_id].add(rtype)
            managed[module_id] += n
        elif kind == "Data":
            data[module_id] += n
        else:
            raise ValueError(f"unexpected ResourceType {kind!r}")
    rows = []
    for module_id, repo_id, path, calls, diagnostics in conn.execute(
        "SELECT Id, RepositoryId, Path, ModuleCalls, DiagnosticMessages FROM Modules ORDER BY Id"
    ):
        n_calls, n_nonlocal = parse_module_calls(calls)
        rows.append(
            ModuleRow(
                module_id, repo_id, path, frozenset(types.get(module_id, ())),
                managed[module_id], data[module_id], n_calls, n_nonlocal, bool(diagnostics),
            )
        )
    return rows


def load_repos(conn: sqlite3.Connection) -> dict[int, dict]:
    return {
        repo_id: {"full_name": full_name, "licence": licence, "commit": sha}
        for repo_id, full_name, licence, sha in conn.execute(
            "SELECT Id, FullName, License, LatestCommitSha FROM Repositories"
        )
    }


def dump_schema(conn: sqlite3.Connection) -> list[dict]:
    """Every table and view with its columns, declared types and row count."""
    tables = []
    for name, kind in conn.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name"
    ):
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [
            {"name": c[1], "type": c[2], "notnull": bool(c[3]), "pk": bool(c[5])}
            for c in conn.execute(f"PRAGMA table_info({quoted})")
        ]
        count = conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
        tables.append({"name": name, "kind": kind, "columns": columns, "rows": count})
    return tables


def measure(modules: list[ModuleRow], repos: dict[int, dict]) -> dict:
    """The funnel (modules and distinct repositories per level) and the licence tables."""
    members: dict[str, list[ModuleRow]] = {level: [] for level in LEVELS}
    for row in modules:
        for level, hit in flags(row).items():
            if hit:
                members[level].append(row)

    def licence_of(row: ModuleRow) -> str | None:
        return repos.get(row.repo_id, {}).get("licence")

    funnel = {
        level: {"modules": len(rows), "repos": len({r.repo_id for r in rows})}
        for level, rows in members.items()
    }
    buckets: dict[str, dict] = {}
    raw: dict[str, dict] = {}
    for level in LICENCE_LEVELS:
        buckets[level] = {
            b: {
                "modules": sum(1 for r in members[level] if licence_bucket(licence_of(r)) == b),
                "repos": len({r.repo_id for r in members[level] if licence_bucket(licence_of(r)) == b}),
            }
            for b in BUCKETS
        }
        per_licence: dict[str, set[int]] = collections.defaultdict(set)
        per_licence_modules: collections.Counter[str] = collections.Counter()
        for r in members[level]:
            key = licence_of(r) or "<null>"
            per_licence[key].add(r.repo_id)
            per_licence_modules[key] += 1
        raw[level] = {
            k: {"modules": per_licence_modules[k], "repos": len(per_licence[k])}
            for k in sorted(per_licence, key=lambda k: (-len(per_licence[k]), k))
        }
    whole = collections.Counter(r["licence"] or "<null>" for r in repos.values())
    f2 = members["F2"]
    return {
        "funnel": funnel,
        "licence_buckets": buckets,
        "licence_raw": raw,
        "whole_dataset_repo_licences": dict(sorted(whole.items(), key=lambda kv: (-kv[1], kv[0]))),
        "f2_modules_with_diagnostics": sum(1 for r in f2 if r.has_diagnostics),
        "f2b_nonlocal_calls_only": sum(1 for r in f2 if r.n_nonlocal_calls == 0),
        "f2_modules_in_repos_missing_from_repositories_table": sum(1 for r in f2 if r.repo_id not in repos),
        "members": members,
    }


# --------------------------------------------------------------------------- outputs


def write_candidates(path: Path, members: list[ModuleRow], repos: dict[int, dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "repo_id", "repo_full_name", "repo_commit_sha", "module_id", "module_path",
                "licence", "licence_bucket", "managed_types", "has_diagnostics",
                "F2a", "F2b", "F3", "F4", "G",
            ]
        )
        for row in sorted(members, key=lambda r: (repos.get(r.repo_id, {}).get("full_name", ""), r.path, r.module_id)):
            repo = repos.get(row.repo_id, {})
            f = flags(row)
            writer.writerow(
                [
                    row.repo_id, repo.get("full_name", ""), repo.get("commit", ""), row.module_id,
                    row.path, repo.get("licence") or "", licence_bucket(repo.get("licence")),
                    ";".join(sorted(row.managed_types)), int(row.has_diagnostics),
                    int(f["F2a"]), int(f["F2b"]), int(f["F3"]), int(f["F4"]), int(f["G"]),
                ]
            )


def write_licence_inventory(path: Path, members: list[ModuleRow], repos: dict[int, dict], licence_files: dict | None) -> None:
    repo_ids = sorted({r.repo_id for r in members}, key=lambda i: repos.get(i, {}).get("full_name", ""))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["repo_id", "repo_full_name", "licence", "licence_bucket", "licence_file_in_archive"])
        for repo_id in repo_ids:
            repo = repos.get(repo_id, {})
            if licence_files is None:
                found = "not yet established"
            else:
                found = "yes" if licence_files.get(str(repo_id)) else "no"
            writer.writerow(
                [repo_id, repo.get("full_name", ""), repo.get("licence") or "", licence_bucket(repo.get("licence")), found]
            )


def schema_markdown(tables: list[dict], db_name: str) -> str:
    lines = [
        "# TerraDS database schema",
        "",
        f"Read from `{db_name}` (opened read-only) by `sources/terrads/measure_yield.py`. "
        "Row counts are measured.",
        "",
    ]
    for table in tables:
        lines += [
            f"## {table['kind']} `{table['name']}`: {table['rows']:,} rows",
            "",
            "| Column | Declared type | Not null | Primary key |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| `{c['name']}` | `{c['type']}` | {'yes' if c['notnull'] else 'no'} | {'yes' if c['pk'] else 'no'} |"
            for c in table["columns"]
        ]
        lines.append("")
    return "\n".join(lines)


def pin_info(manifest: dict) -> dict:
    sqlite = next(e for e in manifest["sources"] if e["id"] == "terrads-sqlite")
    return {
        "record_id": sqlite["record_id"],
        "doi": sqlite["doi"],
        "concept_doi": sqlite["concept_doi"],
        "sqlite_sha256": sqlite["sha256"],
        "pin_reason": manifest.get("terrads_pin_reason"),
    }


def _schema_signature(tables: list[dict], kind: str) -> list:
    return [
        (t["name"], [(c["name"], c["type"]) for c in t["columns"]]) for t in tables if t["kind"] == kind
    ]


def _compare(label: str, measured: dict, published: dict) -> list[str]:
    notes = []
    for key, name in (
        ("repositories", "repositories"), ("modules", "modules"), ("resources", "resources"),
        ("managed_resources", "managed resources"), ("data_resources", "data resources"),
    ):
        if key in published and key in measured:
            verdict = "matches" if measured[key] == published[key] else "DIFFERS from"
            notes.append(f"{label}: measured {name} {measured[key]:,} {verdict} published {published[key]:,}.")
    return notes


def comparison_notes(args: argparse.Namespace, counts: dict, result: dict, modules: list[ModuleRow]) -> list[str]:
    if not args.published.is_file():
        return []
    published = json.loads(args.published.read_text(encoding="utf-8"))
    pin = None
    if args.manifest.is_file():
        pin = pin_info(json.loads(args.manifest.read_text(encoding="utf-8")))["record_id"]
    measured = {
        "repositories": counts["Repositories"], "modules": counts["Modules"], "resources": counts["Resources"],
        "managed_resources": sum(m.n_managed for m in modules), "data_resources": sum(m.n_data for m in modules),
    }
    notes = []
    if pin in published["versions"]:
        notes += _compare(f"Pinned record {pin}", measured, published["versions"][pin])
    if args.v1_db:
        conn = connect_readonly(args.v1_db)
        v1_tables = dump_schema(conn)
        v1_counts = {t["name"]: t["rows"] for t in v1_tables}
        v1_modules = load_modules(conn)
        conn.close()
        v1 = {
            "repositories": v1_counts["Repositories"], "modules": v1_counts["Modules"],
            "resources": v1_counts["Resources"],
            "managed_resources": sum(m.n_managed for m in v1_modules),
            "data_resources": sum(m.n_data for m in v1_modules),
        }
        first = next(k for k in published["versions"] if k != pin)
        notes += _compare(f"First record {first} (measured from its own database)", v1, published["versions"][first])
        for other in published["other_published_repository_counts"]:
            verdict = "matches" if v1["repositories"] == other["figure"] else "does not match"
            notes.append(
                f"First record {first}: measured repositories {v1['repositories']:,} {verdict} the {other['figure']:,} "
                f"figure ({other['source'].split(' (')[0]})."
            )
        pinned = connect_readonly(args.database)
        pinned_tables = dump_schema(pinned)
        pinned.close()
        same = _schema_signature(v1_tables, "table") == _schema_signature(pinned_tables, "table")
        notes.append(
            "Table names, column names and declared types of the first and the pinned database are "
            f"{'identical' if same else 'DIFFERENT'} (row counts excluded)."
        )
        v1_views = {t["name"] for t in v1_tables if t["kind"] == "view"}
        new_views = {t["name"] for t in pinned_tables if t["kind"] == "view"}
        if v1_views != new_views:
            notes.append(
                f"Views only in the first database: {sorted(v1_views - new_views) or 'none'}; "
                f"views only in the pinned database: {sorted(new_views - v1_views) or 'none'}."
            )
    return notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("database", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--archive-scan", type=Path, help="JSON from scan_archive.py (cache)")
    parser.add_argument("--crosscheck", type=Path, help="JSON describing the cross-check outcome")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] / "manifest.json")
    parser.add_argument("--published", type=Path, default=Path(__file__).resolve().parent / "published_counts.json")
    parser.add_argument("--v1-db", type=Path, help="first TerraDS version's database, for the count comparison only")
    args = parser.parse_args(argv)

    conn = connect_readonly(args.database)
    tables = dump_schema(conn)
    repos = load_repos(conn)
    modules = load_modules(conn)
    conn.close()
    result = measure(modules, repos)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "SCHEMA.md").write_text(schema_markdown(tables, "TerraDS.sqlite"), encoding="utf-8", newline="\n")

    archive_scan = json.loads(args.archive_scan.read_text(encoding="utf-8")) if args.archive_scan else None
    crosscheck = json.loads(args.crosscheck.read_text(encoding="utf-8")) if args.crosscheck else None
    pin = pin_info(json.loads(args.manifest.read_text(encoding="utf-8"))) if args.manifest.is_file() else None
    f2 = result["members"]["F2"]
    write_candidates(out / "candidates.csv", f2, repos)
    write_licence_inventory(out / "licence_inventory.csv", f2, repos, (archive_scan or {}).get("licence_files_by_repo"))

    counts = {t["name"]: t["rows"] for t in tables}
    document = {
        "run_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": SEED,
        "pin": pin,
        "published_comparison": comparison_notes(args, counts, result, modules),
        "table_row_counts": counts,
        "distinct_repositories_with_modules": len({m.repo_id for m in modules}),
        "managed_resources": sum(m.n_managed for m in modules),
        "data_resources": sum(m.n_data for m in modules),
        "definitions": {"S": sorted(S), "T9": sorted(T9)},
        **{k: v for k, v in result.items() if k != "members"},
        "archive_scan": archive_scan and {k: v for k, v in archive_scan.items() if k != "licence_files_by_repo"},
        "crosscheck": crosscheck,
    }
    (out / "yield.json").write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    import render_report  # sibling module, imported late so the library part has no side effects

    (out / "yield_report.md").write_text(render_report.render(document), encoding="utf-8", newline="\n")
    for level in LEVELS:
        print(f"{level:>5}  modules {result['funnel'][level]['modules']:>8,}  repos {result['funnel'][level]['repos']:>7,}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
