"""Summarise a `terraform show -json` plan: which attributes are known or unknown for each resource.

Usage: python plan_facts.py <plan.json> [--attrs a,b,c] [--type aws_x ...]

For each entry of ``resource_changes`` prints the address, the actions, and for the requested
attributes either the planned value (known), ``<unknown>`` (listed in ``after_unknown``) or ``<absent>``.
Then prints, for every resource in ``configuration``, the ``references`` recorded per expression.

Standard library only; reads the plan as data.
"""

from __future__ import annotations

import argparse
import json
import sys

DEFAULT_ATTRS = {
    "aws_security_group_rule": ["type", "security_group_id", "protocol", "from_port", "to_port", "cidr_blocks", "ipv6_cidr_blocks", "source_security_group_id", "self"],
    "aws_security_group": ["vpc_id", "ingress", "egress"],
    "aws_db_instance": ["engine", "port", "publicly_accessible", "vpc_security_group_ids", "db_subnet_group_name"],
    "aws_instance": ["subnet_id", "vpc_security_group_ids", "private_ip", "ami"],
    "aws_subnet": ["vpc_id", "cidr_block"],
    "aws_vpc": ["cidr_block"],
    "aws_route_table": ["vpc_id", "route"],
    "aws_route_table_association": ["subnet_id", "route_table_id"],
    "aws_internet_gateway": ["vpc_id"],
    "aws_db_subnet_group": ["subnet_ids", "name"],
}


def any_unknown(marker: object) -> bool:
    """True if an ``after_unknown`` fragment marks anything unknown."""
    if isinstance(marker, dict):
        return any(any_unknown(v) for v in marker.values())
    if isinstance(marker, list):
        return any(any_unknown(v) for v in marker)
    return marker is True


def describe(after: dict, unknown: dict, name: str) -> str:
    u = unknown.get(name)
    if u is not True and not any_unknown(u):
        u = None
    if name in after and after[name] is not None:
        if u is True:
            return "<unknown>"
        shown = json.dumps(after[name], sort_keys=True)
        if u:  # partially unknown structure
            return f"{shown}  (partly unknown: {json.dumps(u, sort_keys=True)})"
        return shown
    if u is True:
        return "<unknown>"
    return "<null>" if name in after else "<absent>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("--type", action="append", help="limit to these resource types")
    args = parser.parse_args()
    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)

    changes = plan.get("resource_changes", [])
    print(f"terraform_version: {plan.get('terraform_version')}  format_version: {plan.get('format_version')}")
    print(f"resource_changes: {len(changes)}")
    print(f"types: {sorted({c['type'] for c in changes})}")
    print()
    for change in sorted(changes, key=lambda c: c["address"]):
        if args.type and change["type"] not in args.type:
            continue
        after = change["change"].get("after") or {}
        unknown = change["change"].get("after_unknown") or {}
        print(f"{change['address']}  actions={change['change']['actions']}")
        for attr in DEFAULT_ATTRS.get(change["type"], []):
            print(f"    {attr:28s} {describe(after, unknown, attr)}")
    print()
    print("configuration.root_module resources and their expression references:")
    for res in sorted(plan.get("configuration", {}).get("root_module", {}).get("resources", []), key=lambda r: r["address"]):
        if args.type and res["type"] not in args.type:
            continue
        print(f"  {res['address']}")
        for key, expr in sorted(res.get("expressions", {}).items()):
            if isinstance(expr, dict) and expr.get("references"):
                print(f"      {key:26s} references={expr['references']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
