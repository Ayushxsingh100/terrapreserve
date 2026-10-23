"""Print the schema facts used by V05, V07, V13 and V14, from the committed schema_filtered.json.

Usage: python schema_facts.py > schema_facts.txt
Standard library only.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = json.loads((Path(__file__).resolve().parent / "schema_filtered.json").read_text(encoding="utf-8"))
RESOURCES = SCHEMA["resource_schemas"]


def flags(attribute: dict) -> str:
    kinds = [k for k in ("required", "optional", "computed") if attribute.get(k)]
    return "+".join(kinds) or "none"


def describe(resource: str, name: str) -> str:
    block = RESOURCES[resource]["block"]
    if name in block.get("attributes", {}):
        attribute = block["attributes"][name]
        return f"{resource}.{name}: attribute, {flags(attribute)}, type {json.dumps(attribute['type'])}"
    if name in block.get("block_types", {}):
        return f"{resource}.{name}: nested block ({block['block_types'][name]['nesting_mode']})"
    return f"{resource}.{name}: ABSENT"


QUESTIONS = (
    ("V13", "aws_instance", ("vpc_security_group_ids", "security_group_ids", "security_groups", "subnet_id", "private_ip")),
    (
        "V14",
        "aws_security_group_rule",
        ("type", "security_group_id", "security_group_ids", "source_security_group_id", "self", "cidr_blocks", "ipv6_cidr_blocks", "prefix_list_ids"),
    ),
    ("V05", "aws_db_instance", ("publicly_accessible",)),
    ("V07", "aws_db_instance", ("port", "engine")),
    ("V12", "aws_instance", ("network_interface", "primary_network_interface")),
    ("V12", "aws_route_table", ("route", "propagating_vgws")),
)

for item, resource, names in QUESTIONS:
    for name in names:
        print(f"[{item}] {describe(resource, name)}")

inline = RESOURCES["aws_security_group"]["block"]["attributes"]["ingress"]["type"][1][1]
print("[V14] aws_security_group.ingress element attributes:", ", ".join(sorted(inline)))
