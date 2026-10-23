"""Scan the pinned TerraDS archive for the F2 repositories (D1 Prompt B, 5.4).

    py -3.12 sources/terrads/scan_archive.py <TerraDS.sqlite> <TerraDS.tar.gz> <out.json>

``TerraDS.tar.gz`` is a tar of ``<repository id>.tar.gz`` files, each holding
``<repository id>/...``. The script streams it and reads inner member *names*
only; no member is written to disk, so path traversal and Windows path limits
cannot arise. Nothing is parsed. It records:

* which F2 repositories ship a licence-like file (and which SPDX id its text
  names, to compare with the database field);
* whether every F3 module directory exists in the archive and holds ``*.tf``;
* whether the number of ``*.tf`` directories per F2 repository equals the number
  of its rows in ``Modules``.

The JSON goes to the cache; ``measure_yield.py`` copies only the summary lines
and the per-repository licence-file flags into committed files.
"""

from __future__ import annotations

import io
import json
import posixpath
import re
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import acquire  # noqa: E402
import measure_yield as my  # noqa: E402

LICENCE_NAME = re.compile(r"^(licen[sc]e|copying|unlicense)([.\-_].*)?$", re.IGNORECASE)
MAX_LICENCE_BYTES = 200_000


def module_dir(member_name: str) -> str:
    """Directory of a member relative to the repository root ('.' for the root)."""
    rel = posixpath.dirname(member_name.split("/", 1)[1]) if "/" in member_name else ""
    return rel or "."


def scan_inner(data: bytes, repo_id: int) -> dict:
    tf_dirs: set[str] = set()
    non_tf_files = 0
    licence_files: list[tuple[str, str | None]] = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as inner:
        for member in inner:
            if not member.isfile() or "/" not in member.name:
                continue
            if member.name.split("/", 1)[0] != str(repo_id):
                continue
            base = posixpath.basename(member.name)
            if base.endswith(".tf"):
                tf_dirs.add(module_dir(member.name))
                continue
            non_tf_files += 1
            if LICENCE_NAME.match(base):
                handle = inner.extractfile(member)
                text = handle.read(MAX_LICENCE_BYTES).decode("utf-8", errors="replace") if handle else ""
                licence_files.append((member.name.split("/", 1)[1], acquire.spdx_from_licence_text(text)))
    return {"tf_dirs": tf_dirs, "non_tf_files": non_tf_files, "licence_files": licence_files}


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    db, archive, out = Path(argv[1]), Path(argv[2]), Path(argv[3])
    conn = my.connect_readonly(db)
    repos = my.load_repos(conn)
    modules = my.load_modules(conn)
    members = my.measure(modules, repos)["members"]
    f2_repos = {m.repo_id for m in members["F2"]}
    f3_repos = {m.repo_id for m in members["F3"]}
    sqlite_module_paths: dict[int, set[str]] = {}
    for m in modules:
        if m.repo_id in f2_repos:
            sqlite_module_paths.setdefault(m.repo_id, set()).add(m.path)
    sqlite_module_rows: dict[int, int] = {}
    for m in modules:
        if m.repo_id in f2_repos:
            sqlite_module_rows[m.repo_id] = sqlite_module_rows.get(m.repo_id, 0) + 1
    f3_paths: dict[int, set[str]] = {}
    for m in members["F3"]:
        f3_paths.setdefault(m.repo_id, set()).add(m.path)

    total_inner = 0
    inner_ids: set[int] = set()
    scanned: dict[int, dict] = {}
    with tarfile.open(archive, "r|gz") as outer:
        for member in outer:
            if not member.isfile() or not member.name.endswith(".tar.gz"):
                continue
            total_inner += 1
            repo_id = int(member.name.removesuffix(".tar.gz").rsplit("/", 1)[-1])
            inner_ids.add(repo_id)
            if repo_id in f2_repos:
                scanned[repo_id] = scan_inner(outer.extractfile(member).read(), repo_id)

    licence_by_repo = {str(r): bool(s["licence_files"]) for r, s in scanned.items()}
    f3_licence_mismatch = []
    f3_with_file = 0
    for repo_id in sorted(f3_repos):
        files = scanned.get(repo_id, {}).get("licence_files", [])
        if files:
            f3_with_file += 1
            ids = {spdx for _, spdx in files if spdx}
            declared = repos[repo_id]["licence"]
            if ids and declared not in ids:
                f3_licence_mismatch.append(
                    {"repo_id": repo_id, "full_name": repos[repo_id]["full_name"], "database": declared, "file": sorted(ids)}
                )
    missing_f3_dirs = [
        {"repo_id": r, "path": p}
        for r, paths in sorted(f3_paths.items())
        for p in sorted(paths)
        if p not in scanned.get(r, {"tf_dirs": set()})["tf_dirs"]
    ]
    dir_count_mismatch = [
        {"repo_id": r, "database_modules": sqlite_module_rows[r], "archive_tf_dirs": len(scanned[r]["tf_dirs"])}
        for r in sorted(scanned)
        if len(scanned[r]["tf_dirs"]) != sqlite_module_rows[r]
    ]
    path_set_mismatch = [r for r in sorted(scanned) if scanned[r]["tf_dirs"] != sqlite_module_paths[r]]
    missing_from_archive = sorted(f2_repos - set(scanned))
    non_tf = sum(s["non_tf_files"] for s in scanned.values())
    f2_with_file = sum(1 for s in scanned.values() if s["licence_files"])

    lines = [
        f"The archive holds {total_inner:,} inner repository archives; `Repositories` has {len(repos):,} rows; "
        f"{len(set(repos) - inner_ids):,} database repositories have no inner archive and {len(inner_ids - set(repos)):,} "
        "inner archives have no database row.",
        f"Of the {len(f2_repos):,} F2 repositories, {len(f2_repos) - len(missing_from_archive):,} were found in the archive "
        f"({len(missing_from_archive):,} missing).",
        f"Non-`.tf` files in the F2 repositories' archives: {non_tf:,}; licence-like files (LICENSE/LICENCE/COPYING/UNLICENSE): "
        f"{sum(len(s['licence_files']) for s in scanned.values()):,} in {f2_with_file:,} F2 repositories.",
        f"F3 repositories: {len(f3_repos):,}; with a licence-like file in the archive: {f3_with_file:,}; "
        f"licence file names a different SPDX id than the database: {len(f3_licence_mismatch):,}.",
        f"F3 module directories absent from the archive or without a `*.tf` file: {len(missing_f3_dirs):,} of "
        f"{sum(len(p) for p in f3_paths.values()):,}.",
        f"F2 repositories whose set of `*.tf` directories in the archive differs from the database's module paths: "
        f"{len(path_set_mismatch):,} of {len(scanned):,} (count differs in {len(dir_count_mismatch):,}).",
        "This is a name-level consistency check only. No file was parsed and no member was written to disk, "
        "so there is nothing to report for Windows extraction failures.",
    ]
    result = {
        "inner_archives": total_inner,
        "f2_repositories_scanned": len(scanned),
        "f3_repositories": len(f3_repos),
        "f3_repositories_with_licence_file": f3_with_file,
        "f3_licence_mismatches": f3_licence_mismatch,
        "f3_missing_module_dirs": missing_f3_dirs,
        "module_dir_count_mismatches": dir_count_mismatch,
        "module_dir_set_mismatch_repos": path_set_mismatch,
        "summary_lines": lines,
        "licence_files_by_repo": licence_by_repo,
    }
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
