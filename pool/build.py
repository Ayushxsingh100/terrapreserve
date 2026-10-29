"""Entry point of the D3 pool builder: ``py -3.12 -m pool.build <command>``.

Standard library and ``sources/*`` only; nothing here imports DAIL (D3-02, CLAUDE.md rule 5).

    filter    E01 to E08 over every candidate; stages the survivors in the work directory
    ...       (later steps add lineage, scan, licence, validate, terragoat and assemble)

All intermediate files go to the work directory (``<cache>/d3-work`` by default), never into the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import acquire

from pool import cascade


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pool.build", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", metavar="command")
    p = sub.add_parser("filter", help="E01 to E08 over all candidates")
    p.add_argument("--db", type=Path, help="TerraDS.sqlite (default: the pinned one in the cache)")
    p.add_argument("--archive", type=Path, help="TerraDS.tar.gz (default: the pinned one in the cache)")
    p.add_argument("--work", type=Path, default=None, help="work directory outside the repository")
    p.set_defaults(func=cmd_filter)
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
