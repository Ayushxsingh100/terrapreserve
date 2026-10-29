"""Entry point of the D3 pool builder: ``py -3.12 -m pool.build <command>``.

Standard library and ``sources/*`` only; nothing here imports DAIL (D3-02, CLAUDE.md rule 5).

    filter    E01 to E08 over every candidate; stages the survivors in the work directory
    lineage   lineages over the staged survivors (E10 is applied later, to hosts only)
    ...       (later steps add lineage, scan, licence, validate, terragoat and assemble)

All intermediate files go to the work directory (``<cache>/d3-work`` by default), never into the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import acquire

from pool import cascade, lineage


def pinned_inputs() -> tuple[Path, Path]:
    """The pinned TerraDS database and archive in the cache, after checking size and sha256 against the manifest."""
    manifest = acquire.load_manifest()
    root = acquire.cache_root()
    paths = []
    for entry_id in ("terrads-sqlite", "terrads-tar-gz"):
        entry = acquire.entry_by_id(manifest, entry_id)
        path = root / entry["cache_path"]
        problem = acquire.verify_file(path, entry["sha256"], entry["size_bytes"])
        if problem:
            raise acquire.AcquireError(problem)
        paths.append(path)
    return paths[0], paths[1]


def default_work() -> Path:
    return acquire.cache_root() / "d3-work"


def cmd_filter(args: argparse.Namespace) -> int:
    if args.db and args.archive:
        db, archive = args.db, args.archive
    else:
        db, archive = pinned_inputs()
    summary = cascade.run_filter(db, archive, args.work)
    (args.work / "cheap_summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "funnel"}, indent=1, sort_keys=True))
    return 0


def load_staged(work: Path) -> list[lineage.ModuleInput]:
    """The modules that passed E01 to E08, read back from the staging directory."""
    repo_of = {}
    for line in (work / "cheap_results.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["code"] is None:
            repo_of[row["module_id"]] = row["repo_id"]
    modules = []
    for module_id, repo_id in sorted(repo_of.items()):
        files = {p.name: p.read_bytes().decode("utf-8", errors="replace") for p in sorted((work / "stage" / str(module_id)).glob("*.tf"))}
        modules.append(lineage.ModuleInput(module_id, repo_id, files))
    return modules


def cmd_lineage(args: argparse.Namespace) -> int:
    modules = load_staged(args.work)
    result = lineage.build_lineages(modules, min_shared_tokens=args.min_shared_tokens)
    out = {
        "method": {
            "rules": ["a same repository", "b identical normalised text", "c half of the files share a hash",
                      "d 5-token shingle Jaccard >= 0.8 (MinHash, exact-confirmed)"],
            "seed": lineage.SEED, "permutations": lineage.PERMUTATIONS, "bands": lineage.BANDS, "rows": lineage.ROWS,
            "shingle_tokens": lineage.SHINGLE, "min_shared_tokens": args.min_shared_tokens,
        },
        "stats": result.stats,
        "merges": result.merges,
        "lineage_of": {str(k): v for k, v in sorted(result.lineage_of.items())},
    }
    target = args.work / f"lineage_min{args.min_shared_tokens}.json"
    target.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"stats": result.stats, "merges": result.merges}, indent=1, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pool.build", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", metavar="command")
    p = sub.add_parser("filter", help="E01 to E08 over all candidates")
    p.add_argument("--db", type=Path, help="TerraDS.sqlite (default: the pinned one in the cache)")
    p.add_argument("--archive", type=Path, help="TerraDS.tar.gz (default: the pinned one in the cache)")
    p.add_argument("--work", type=Path, default=None, help="work directory outside the repository")
    p.set_defaults(func=cmd_filter)
    p = sub.add_parser("lineage", help="lineages over the staged survivors")
    p.add_argument("--work", type=Path, default=None, help="work directory outside the repository")
    p.add_argument("--min-shared-tokens", type=int, default=lineage.FILE_TOKEN_FLOOR, help="token floor for a shared file under rule c")
    p.set_defaults(func=cmd_lineage)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    if args.work is None:
        args.work = default_work()
    try:
        return args.func(args)
    except acquire.AcquireError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
