"""Registry v1.0 common definitions used by every evaluator (D5-14): sections 2.4, 2.5 and 2.7.

* Result values and their order (2.4).
* CIDRs, "covers" and "partly covers" (2.5); protocols and ``permits_tcp`` (2.5).
* The relevant-unsupported lists (2.7) and the tolerated type ``aws_db_subnet_group``.

The canonical security-group rule set with MIXED and RETAINED-INLINE (2.6) is in ``oracle/rules.py``, resource
instances and resolved values (2.2, 2.3) in ``oracle/model.py``. Standard library only.
"""

from __future__ import annotations

import ipaddress
from typing import Iterable

PASS, FAIL, UNKNOWN, UNSUPPORTED, VERIFIER_ERROR = "PASS", "FAIL", "UNKNOWN", "UNSUPPORTED", "VERIFIER_ERROR"
RESULTS = (PASS, FAIL, UNKNOWN, UNSUPPORTED, VERIFIER_ERROR)
INVARIANTS = ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001")
REGISTRY_TAG = "registry-v1.0"

# Registry 2.7, relevant-unsupported types (presence anywhere in the configuration).
_SG_LIST = ("aws_vpc_security_group_ingress_rule", "aws_default_security_group", "aws_vpc_security_group_rules_exclusive")
RELEVANT_UNSUPPORTED: dict[str, tuple[str, ...]] = {
    "INV-SEC-001": _SG_LIST,
    "INV-SEC-002": _SG_LIST,
    "INV-SEC-003": (),
    "INV-FUNC-001": (
        "aws_vpc_security_group_ingress_rule", "aws_vpc_security_group_egress_rule", "aws_default_security_group",
        "aws_network_interface", "aws_network_interface_attachment", "aws_network_interface_sg_attachment",
        "aws_network_acl", "aws_network_acl_rule", "aws_network_acl_association", "aws_default_network_acl",
        "aws_route", "aws_default_route_table", "aws_main_route_table_association",
        "aws_vpc_ipv4_cidr_block_association", "aws_vpc_peering_connection", "aws_ec2_transit_gateway_vpc_attachment",
        "aws_vpc_endpoint", "aws_vpc_security_group_rules_exclusive", "aws_vpc_security_group_vpc_association",
        "aws_vpn_gateway_route_propagation", "aws_vpc_route_server_propagation", "aws_default_subnet",
        "aws_default_vpc", "aws_vpc_peering_connection_accepter", "aws_vpc_peering_connection_options",
        "aws_ec2_transit_gateway_vpc_attachment_accepter",
    ),
}
# Registry 2.7 / 6.2 M4: the NACL-related types of INV-FUNC-001's list.
NACL_TYPES = ("aws_network_acl", "aws_network_acl_rule", "aws_network_acl_association", "aws_default_network_acl")
TOLERATED = ("aws_db_subnet_group",)  # registry 2.7: tolerated, not relevant (C-15, 6.2 M1)
SUPPORTED_TYPES = ("aws_vpc", "aws_subnet", "aws_internet_gateway", "aws_route_table", "aws_route_table_association",
                   "aws_security_group", "aws_security_group_rule", "aws_instance", "aws_db_instance")  # registry 1.3


def worst(results: Iterable[str]) -> str:
    """Registry 3.4: FAIL if any FAIL; otherwise UNSUPPORTED, then UNKNOWN, then PASS, taking the worst."""
    rs = list(results)
    if VERIFIER_ERROR in rs:
        return VERIFIER_ERROR
    for r in (FAIL, UNSUPPORTED, UNKNOWN):
        if r in rs:
            return r
    return PASS


# ---- CIDRs (registry 2.5)

def parse_cidr(text: object) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    """A strictly parsed CIDR, or None when it is syntactically invalid or has host bits set (the rule is UNSUPPORTED)."""
    if not isinstance(text, str) or "/" not in text:
        return None
    try:
        return ipaddress.ip_network(text.strip(), strict=True)
    except ValueError:
        return None


def _ranges(nets: Iterable[ipaddress.IPv4Network | ipaddress.IPv6Network], version: int) -> list[tuple[int, int]]:
    out = sorted((int(n.network_address), int(n.broadcast_address)) for n in nets if n.version == version)
    merged: list[tuple[int, int]] = []
    for lo, hi in out:
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def covers(nets: Iterable[ipaddress.IPv4Network | ipaddress.IPv6Network], target: ipaddress.IPv4Network | ipaddress.IPv6Network) -> bool:
    """Registry 2.5: the union of the listed ranges contains the target range (order and duplicates never matter)."""
    lo, hi = int(target.network_address), int(target.broadcast_address)
    return any(a <= lo and hi <= b for a, b in _ranges(nets, target.version))


def overlaps(nets: Iterable[ipaddress.IPv4Network | ipaddress.IPv6Network], target: ipaddress.IPv4Network | ipaddress.IPv6Network) -> bool:
    lo, hi = int(target.network_address), int(target.broadcast_address)
    return any(a <= hi and lo <= b for a, b in _ranges(nets, target.version))


def partly_covers(nets: Iterable[ipaddress.IPv4Network | ipaddress.IPv6Network], target: ipaddress.IPv4Network | ipaddress.IPv6Network) -> bool:
    """Registry 6.4 row 8: the ranges meet the target range but do not contain it."""
    nets = list(nets)
    return overlaps(nets, target) and not covers(nets, target)


ALL_V4 = ipaddress.ip_network("0.0.0.0/0")
ALL_V6 = ipaddress.ip_network("::/0")

# ---- Protocols (registry 2.5)
_NAMES = {"-1": "ALL", "all": "ALL", "tcp": "TCP", "6": "TCP", "udp": "UDP", "17": "UDP", "icmp": "ICMP", "1": "ICMP",
          "icmpv6": "ICMPV6", "58": "ICMPV6"}


def canonical_protocol(value: object) -> str:
    """Registry 2.5 table, compared case-insensitively. Any other value is that protocol (not TCP)."""
    text = str(value).strip().lower()
    return _NAMES.get(text, f"PROTO:{text}")
