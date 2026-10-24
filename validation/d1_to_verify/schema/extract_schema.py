"""Derive the committed schema artefacts from the full ``terraform providers schema -json`` output.

The full dump is about 19 MB (over the repository's 5 MB per-file cap), so it is not committed.
This script reads it from a path and writes, next to itself:

* ``resource_types.txt``      every resource type name, one per line, sorted;
* ``data_source_types.txt``   every data source type name, one per line, sorted;
* ``schema_filtered.json``    the full schema of the ten types the registry models (nine supported
                              types plus ``aws_db_subnet_group``);
* ``SCHEMA_SHA256.txt``       sha256 and size of the full dump that was read, and of the provider version.

Usage: ``python extract_schema.py <path to schema_aws_6.53.0.json>``

Standard library only. Reads the schema file as data and never imports anything from it.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PROVIDER = "registry.terraform.io/hashicorp/aws"
MODELLED_TYPES = (
    "aws_vpc",
    "aws_subnet",
    "aws_internet_gateway",
    "aws_route_table",
    "aws_route_table_association",
    "aws_security_group",
    "aws_security_group_rule",
    "aws_instance",
    "aws_db_instance",
    "aws_db_subnet_group",
)
HERE = Path(__file__).resolve().parent


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    source = Path(argv[1])
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    document = json.loads(raw)
    provider = document["provider_schemas"][PROVIDER]
    resources = provider["resource_schemas"]
    data_sources = provider.get("data_source_schemas", {})

    (HERE / "resource_types.txt").write_text("\n".join(sorted(resources)) + "\n", encoding="utf-8", newline="\n")
    (HERE / "data_source_types.txt").write_text(
        "\n".join(sorted(data_sources)) + "\n", encoding="utf-8", newline="\n"
    )

    filtered = {
        "format_version": document["format_version"],
        "provider": PROVIDER,
        "resource_schemas": {name: resources[name] for name in MODELLED_TYPES},
    }
    (HERE / "schema_filtered.json").write_text(
        json.dumps(filtered, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )

    (HERE / "SCHEMA_SHA256.txt").write_text(
        f"file: schema_aws_6.53.0.json (output of `terraform providers schema -json`, not committed)\n"
        f"sha256: {digest}\n"
        f"size_bytes: {len(raw)}\n"
        f"resource_types: {len(resources)}\n"
        f"data_source_types: {len(data_sources)}\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"sha256 {digest}  {len(raw)} bytes  resources={len(resources)} data_sources={len(data_sources)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
