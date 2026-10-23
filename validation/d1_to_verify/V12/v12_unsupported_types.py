"""V12: heuristic completeness check of the registry's unsupported-type lists against the provider schema.

HEURISTIC. The output is a worklist for a human; it is not a decision. Nothing here proves that a type
can or cannot change the truth of INV-SEC-001/002/003 or INV-FUNC-001.

Usage: python v12_unsupported_types.py <schema_aws_6.53.0.json> <output_dir>

Reads the full output of ``terraform providers schema -json`` (not committed; its sha256 is in
../schema/SCHEMA_SHA256.txt) and writes into <output_dir>:

* ``candidates_all.tsv``       every resource type that matches the heuristic, with the matching attribute
                               paths, a tier, and whether the registry already lists it;
* ``missing_tier1.tsv``        tier-1 candidates absent from the registry lists (name or strong-attribute match);
* ``missing_tier2.tsv``        tier-2 candidates absent from the registry lists (weak keyword match only);
* ``missing_core.tsv``         the subset of missing candidates (either tier) whose type name is in the core
                               EC2 / VPC / RDS networking families (``CORE``); the worklist for a human;
* ``summary.txt``              counts.

The registry lists are copied from docs/specs/INVARIANT_REGISTRY_v1.md section 1.3 (supported types) and
section 2.7 (relevant-unsupported lists, tolerated type), DAIL commit 7ed7aaf.

Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROVIDER = "registry.terraform.io/hashicorp/aws"

# Registry section 1.3: supported types.
SUPPORTED = {
    "aws_vpc", "aws_subnet", "aws_internet_gateway", "aws_route_table", "aws_route_table_association",
    "aws_security_group", "aws_security_group_rule", "aws_instance", "aws_db_instance",
}
# Registry section 2.7: tolerated type, then the relevant-unsupported lists (union of the rows).
TOLERATED = {"aws_db_subnet_group"}
REGISTRY_SEC = {"aws_vpc_security_group_ingress_rule", "aws_default_security_group"}
REGISTRY_FUNC = {
    "aws_vpc_security_group_ingress_rule", "aws_vpc_security_group_egress_rule", "aws_default_security_group",
    "aws_network_interface", "aws_network_interface_attachment", "aws_network_interface_sg_attachment",
    "aws_network_acl", "aws_network_acl_rule", "aws_network_acl_association", "aws_default_network_acl",
    "aws_route", "aws_default_route_table", "aws_main_route_table_association",
    "aws_vpc_ipv4_cidr_block_association", "aws_vpc_peering_connection",
    "aws_ec2_transit_gateway_vpc_attachment", "aws_vpc_endpoint",
}
REGISTRY_LISTED = SUPPORTED | TOLERATED | REGISTRY_SEC | REGISTRY_FUNC

# Keywords from the work-package prompt, matched against every attribute / nested-block name.
KEYWORDS = (
    "security_group", "cidr", "ingress", "egress", "from_port", "to_port", "route", "gateway", "subnet",
    "publicly_accessible", "network_acl", "vpc_endpoint", "peering", "transit_gateway", "prefix_list",
    "network_interface",
)
# Type-name families from the prompt.
FAMILIES = re.compile(
    r"^aws_(vpc_security_group_|default_|network_acl|route|main_route_table_association|db_|rds_|"
    r"network_interface|ec2_)"
)
# Strong attributes: the exact names through which a resource attaches security groups, creates rules,
# edits routes, or sets database exposure. A type with one of these (at any depth) is tier 1.
STRONG_ATTRS = {
    "security_groups", "security_group_ids", "vpc_security_group_ids", "security_group_id",
    "source_security_group_id", "referenced_security_group_id", "publicly_accessible", "route_table_id",
    "route_table_ids", "network_interface_id", "network_interface_ids", "ingress", "egress",
    "from_port", "to_port", "ip_protocol", "prefix_list_id", "prefix_list_ids",
}
# Core networking families: where a resource can plausibly touch an aws_instance, an aws_db_instance, a
# security group, a subnet's traffic or a VPC route. Other services (Lambda, ELB, ECS, ...) attach security
# groups to their own interfaces; whether that matters is a human decision (S must be an aws_instance and D an
# aws_db_instance in INV-FUNC-001).
CORE = re.compile(
    r"^aws_(vpc_|ec2_|default_|network_|route(_|$)|main_route|security_group|eip|nat_gateway|egress_only|"
    r"internet_gateway|vpn_|customer_gateway|subnet|spot_|launch_|autoscaling|db_|rds_|instance|key_pair|"
    r"placement_group|ami)"
)
HINTS = (
    (re.compile(r"security_group|ingress|egress|from_port|to_port|ip_protocol|prefix_list"),
     "SEC-001/002 and FUNC-001 E5/E6 (security-group rules or attachment)"),
    (re.compile(r"publicly_accessible"), "SEC-003 (database exposure flag)"),
    (re.compile(r"route|gateway|peering|transit_gateway|vpc_endpoint|network_interface"),
     "FUNC-001 M3/E7 (routing or interface placement)"),
    (re.compile(r"network_acl"), "FUNC-001 M4 (network ACL)"),
    (re.compile(r"subnet|cidr"), "FUNC-001 M2/E4/E6 (placement or address ranges)"),
)


def walk(block: dict, prefix: str = ""):
    """Yield (dotted path, leaf name) for every attribute and nested block."""
    for name in block.get("attributes", {}):
        yield f"{prefix}{name}", name
    for name, nested in block.get("block_types", {}).items():
        yield f"{prefix}{name}{{}}", name
        yield from walk(nested.get("block", {}), f"{prefix}{name}.")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    schema = json.loads(Path(argv[1]).read_bytes())["provider_schemas"][PROVIDER]["resource_schemas"]
    out = Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for rtype in sorted(schema):
        paths = list(walk(schema[rtype]["block"]))
        keyword_hits = sorted({p for p, leaf in paths if any(k in leaf for k in KEYWORDS)})
        strong_hits = sorted({p for p, leaf in paths if leaf in STRONG_ATTRS})
        family = bool(FAMILIES.match(rtype))
        if not (keyword_hits or family):
            continue
        tier = 1 if (family or strong_hits) else 2
        triggers = (["type-family"] if family else []) + (strong_hits or keyword_hits)
        hint_text = " ".join([rtype] + [p for p, _ in paths if p in set(strong_hits or keyword_hits)])
        hints = sorted({h for rx, h in HINTS if rx.search(hint_text)})
        status = "listed" if rtype in REGISTRY_LISTED else "MISSING"
        rows.append((rtype, tier, status, triggers, hints))

    def line(r):
        rtype, tier, status, triggers, hints = r
        shown = ", ".join(triggers[:6]) + (f" (+{len(triggers) - 6} more)" if len(triggers) > 6 else "")
        return f"{rtype}\t{tier}\t{status}\t{shown}\t{'; '.join(hints)}"

    header = "type\ttier\tregistry\ttriggering attributes (first 6)\tpossible invariant impact (heuristic)\n"
    (out / "candidates_all.tsv").write_text(header + "\n".join(line(r) for r in rows) + "\n", encoding="utf-8", newline="\n")
    core = [r for r in rows if r[2] == "MISSING" and CORE.match(r[0])]
    (out / "missing_core.tsv").write_text(
        header + "\n".join(line(r) for r in core) + "\n", encoding="utf-8", newline="\n"
    )
    for tier in (1, 2):
        sel = [r for r in rows if r[1] == tier and r[2] == "MISSING"]
        (out / f"missing_tier{tier}.tsv").write_text(
            header + "\n".join(line(r) for r in sel) + "\n", encoding="utf-8", newline="\n"
        )

    listed_but_unmatched = sorted(REGISTRY_LISTED - {r[0] for r in rows} - SUPPORTED)
    absent_from_schema = sorted(t for t in REGISTRY_LISTED if t not in schema)
    summary = [
        f"resource types in the schema:                    {len(schema)}",
        f"types matching the heuristic:                    {len(rows)}",
        f"  already in the registry lists/supported:       {sum(1 for r in rows if r[2] == 'listed')}",
        f"  MISSING, tier 1 (family or strong attribute):  {sum(1 for r in rows if r[1] == 1 and r[2] == 'MISSING')}",
        f"  MISSING, tier 2 (weak keyword only):           {sum(1 for r in rows if r[1] == 2 and r[2] == 'MISSING')}",
        f"  of which in the core EC2/VPC/RDS families:     {len(core)}",
        f"registry-listed types not matched by heuristic:  {listed_but_unmatched}",
        f"registry-listed types absent from the schema:    {absent_from_schema}",
    ]
    (out / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
