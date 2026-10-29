"""Entry point of the D3 pool builder: ``py -3.12 -m pool.build <command>``.

Standard library and ``sources/*`` only; nothing here imports DAIL (D3-02, CLAUDE.md rule 5).
Sub-commands are added step by step; ``assemble`` writes the committed pool files.
"""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pool.build", description=__doc__)
    parser.add_subparsers(dest="command", metavar="command")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
