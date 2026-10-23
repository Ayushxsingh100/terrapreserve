"""Summarise Checkov JSON results: one line per probe directory.

Usage: python checkov_summary.py <check_id> <dir> [<dir> ...]

Reads ``<dir>/checkov.json`` (output of ``checkov -d <dir> --framework terraform --compact --output json
--check <check_id>``) and prints, per resource of the probe, PASSED / FAILED / SKIPPED, or ``no result``
when the check produced nothing for that resource (resource type not scanned, or an UNKNOWN result,
which Checkov does not report as passed or failed).

Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def resources_in(main_tf: Path) -> list[str]:
    text = main_tf.read_text(encoding="utf-8")
    return [f"{t}.{n}" for t, n in re.findall(r'^resource "([^"]+)" "([^"]+)"', text, re.M)]


def main(argv: list[str]) -> int:
    check_id, dirs = argv[1], [Path(d) for d in argv[2:]]
    for d in dirs:
        raw = json.loads((d / "checkov.json").read_text(encoding="utf-8"))
        if isinstance(raw, list):  # one entry per framework
            raw = raw[0]
        results = raw.get("results", {})
        by_resource: dict[str, str] = {}
        for key, label in (("passed_checks", "PASSED"), ("failed_checks", "FAILED"), ("skipped_checks", "SKIPPED")):
            for item in results.get(key, []):
                if item["check_id"] == check_id:
                    by_resource[item["resource"]] = label
        parts = [f"{res}={by_resource.get(res, 'no result')}" for res in resources_in(d / "main.tf")]
        print(f"{d.name:36s} {check_id}: " + "  ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
