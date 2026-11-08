"""Operator catalogue implementation for TerraPreserve (D4-07).

Provides at least 3 safe and 3 unsafe operators per family (F1 to F8).
All operators operate on HCLModel and produce verified MutationRow records.
Standard library only. No DAIL import (D0 gate 1).
"""

from __future__ import annotations

import copy
import ipaddress
import random
import re
from dataclasses import dataclass
from typing import Any, Callable

import emitter as _emitter
from diff_verify import MutationRow
from model import (
    Block, CountIndex, EachKey, EachValue, HCLModel, MovedBlock,
    RawExpr, Ref, Resource, SortedList, ToSet, VarRef,
)


@dataclass(frozen=True)
class OperatorDef:
    name: str
    family: str  # F1..F8
    variant: str  # safe | unsafe
    target_kind: str  # change_request | repair
    target_invariant: str | None  # INV-SEC-001 | INV-SEC-002 | INV-SEC-003 | None
    description: str
    intent_breaks: list[str]  # e.g. ["INV-SEC-001"]
    intent_preserves: list[str]  # e.g. ["INV-SEC-002", ...]
    apply_fn: Callable[[HCLModel, random.Random, str], tuple[list[HCLModel], list[list[MutationRow]]]]
    mechanism: str | None = None  # B1..B5 for INV-FUNC-001 breaks, else None
    designed_row: int | None = None  # registry 6.4 row the operator is designed to reach

    def apply(self, base_model: HCLModel, rng: random.Random) -> tuple[list[HCLModel], list[list[MutationRow]]]:
        return self.apply_fn(base_model, rng, self.name)


CATALOGUE: list[OperatorDef] = []


class OperatorNotApplicable(RuntimeError):
    """Raised when an operator cannot be applied to a model (target not found / preconditions not met)."""


def is_safe_name(name: str) -> bool:
    """True for ``*_safe`` operator names. Never use ``"safe" in name``: it also matches ``unsafe``."""
    return name.endswith("_safe")


def register_op(op: OperatorDef) -> None:
    CATALOGUE.append(op)


# ---------------------------------------------------------------------------
# Row and attribute helpers
# ---------------------------------------------------------------------------

_DELETE = object()


def _fmt(val: Any) -> str:
    """Render a value exactly as the emitter writes it (so rows match the diff verifier)."""
    return _emitter._emit_value(val, 0)


def _edit(rows: list[MutationRow], step: int, name: str, addr: str, attrs: dict[str, Any],
          key: str, new: Any) -> None:
    """Set (or delete, with ``_DELETE``) ``attrs[key]`` and record the row. No-op edits record nothing."""
    had = key in attrs
    before = _fmt(attrs[key]) if had else None
    if new is _DELETE:
        if not had:
            return
        del attrs[key]
        after = None
    else:
        after = _fmt(new)
        if had and before == after:
            return
        attrs[key] = new
    rows.append(MutationRow(step=step, operator=name, target_address=addr, attribute=key,
                            before=before, after=after))


def _added_rows(step: int, name: str, addr: str, attrs: dict[str, Any]) -> list[MutationRow]:
    return [MutationRow(step=step, operator=name, target_address=addr, attribute=k,
                        before=None, after=_fmt(attrs[k])) for k in sorted(attrs)]


def _removed_rows(step: int, name: str, addr: str, attrs: dict[str, Any]) -> list[MutationRow]:
    return [MutationRow(step=step, operator=name, target_address=addr, attribute=k,
                        before=_fmt(attrs[k]), after=None) for k in sorted(attrs)]


# ---------------------------------------------------------------------------
# Locating the endpoints and their groups (derived from S and D, never from names)
# ---------------------------------------------------------------------------


def _sg_addr(ref: Any) -> str | None:
    m = re.fullmatch(r"(aws_security_group\.[A-Za-z0-9_\-]+)\.id", str(ref))
    return m.group(1) if m else None


def _groups_of(res: Resource) -> list[str]:
    return [a for a in (_sg_addr(x) for x in res.attrs.get("vpc_security_group_ids", [])) if a]


def _find_res(model: HCLModel, res_type: str) -> tuple[str, Resource]:
    for addr, res in model.resources.items():
        if res.type == res_type:
            return addr, res
    raise KeyError(f"No resource of type {res_type} in model")


def _find_app_sg(model: HCLModel) -> tuple[str, Resource]:
    """The first group attached to S (the aws_instance)."""
    try:
        _, s = _find_res(model, "aws_instance")
        for g in _groups_of(s):
            if g in model.resources:
                return g, model.resources[g]
    except KeyError:
        pass
    for addr, res in model.resources.items():
        if res.type == "aws_security_group" and "app" in addr:
            return addr, res
    for addr, res in model.resources.items():
        if res.type == "aws_security_group":
            return addr, res
    raise KeyError("No app security group found")


def _find_db_sg(model: HCLModel) -> tuple[str, Resource]:
    """The first group attached to D (the aws_db_instance)."""
    try:
        _, d = _find_res(model, "aws_db_instance")
        for g in _groups_of(d):
            if g in model.resources:
                return g, model.resources[g]
    except KeyError:
        pass
    for addr, res in model.resources.items():
        if res.type == "aws_security_group" and "db" in addr:
            return addr, res
    for addr, res in model.resources.items():
        if res.type == "aws_security_group":
            return addr, res
    raise KeyError("No db security group found")


@dataclass
class _RuleRef:
    kind: str  # "rule" (aws_security_group_rule resource) or "block" (inline block)
    addr: str  # address recorded in mutation rows (rule resource, or the group for a block)
    attrs: dict[str, Any]
    group: str
    direction: str
    res: Resource  # the rule resource, or the group that holds the block
    block: Block | None


def _rule_refs(m: HCLModel, group: str, direction: str) -> list[_RuleRef]:
    out: list[_RuleRef] = []
    g = m.resources.get(group)
    if g is not None:
        for b in g.blocks:
            if b.label == direction:
                out.append(_RuleRef("block", group, b.attrs, group, direction, g, b))
    for addr, res in m.resources.items():
        if (res.type == "aws_security_group_rule" and res.attrs.get("type") == direction
                and str(res.attrs.get("security_group_id")) == f"{group}.id"):
            out.append(_RuleRef("rule", addr, res.attrs, group, direction, res, None))
    return out


def _permits(attrs: dict[str, Any], port: int = 5432) -> bool:
    proto = attrs.get("protocol")
    if proto == "-1":
        return True
    if proto == "tcp":
        return int(attrs.get("from_port", 0)) <= port <= int(attrs.get("to_port", 0))
    return False


def _cidrs(val: Any) -> list[str]:
    if val is None:
        return []
    return list(val.items) if hasattr(val, "items") and not isinstance(val, dict) else list(val)


def _sources(attrs: dict[str, Any]) -> list[str]:
    out = []
    if "source_security_group_id" in attrs:
        out.append(str(attrs["source_security_group_id"]))
    for x in attrs.get("security_groups", []) or []:
        out.append(str(x))
    return out


def _vpc_net(m: HCLModel) -> ipaddress.IPv4Network:
    """CIDR(VPC(D)), computed from the scenario's own model."""
    _, db_sg = _find_db_sg(m)
    vpc_ref = str(db_sg.attrs.get("vpc_id", ""))
    vpc_addr = vpc_ref[:-3] if vpc_ref.endswith(".id") else vpc_ref
    if vpc_addr not in m.resources or "cidr_block" not in m.resources[vpc_addr].attrs:
        raise OperatorNotApplicable("cannot resolve CIDR(VPC(D))")
    return ipaddress.ip_network(str(m.resources[vpc_addr].attrs["cidr_block"]))  # type: ignore[return-value]


_RFC1918 = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
_DISJOINT_CANDIDATES = ("192.168.0.0/16", "10.255.0.0/16", "172.31.0.0/16", "100.64.0.0/16")


def _private_supernet(vpc: ipaddress.IPv4Network) -> str:
    """The RFC 1918 block that contains the VPC CIDR (covers it fully)."""
    for c in _RFC1918:
        if vpc.subnet_of(ipaddress.ip_network(c)):  # type: ignore[arg-type]
            return c
    raise OperatorNotApplicable(f"VPC CIDR {vpc} is not inside an RFC 1918 block")


def _disjoint_cidr(vpc: ipaddress.IPv4Network) -> str:
    """A CIDR that does not overlap the VPC CIDR at all (never a partial cover, registry 6.4 row 8)."""
    for c in _DISJOINT_CANDIDATES:
        if not ipaddress.ip_network(c).overlaps(vpc):  # type: ignore[arg-type]
            return c
    raise OperatorNotApplicable(f"no disjoint candidate CIDR for {vpc}")


def _app_subnet_cidr(m: HCLModel) -> str:
    _, s = _find_res(m, "aws_instance")
    ref = str(s.attrs.get("subnet_id", ""))
    addr = ref[:-3] if ref.endswith(".id") else ref
    if addr not in m.resources or "cidr_block" not in m.resources[addr].attrs:
        raise OperatorNotApplicable("cannot resolve the app subnet CIDR")
    return str(m.resources[addr].attrs["cidr_block"])


def _egress_carrier(m: HCLModel) -> _RuleRef:
    """The app group's egress rule that carries 5432 (protocol -1, or tcp covering 5432)."""
    app_addr, _ = _find_app_sg(m)
    for r in _rule_refs(m, app_addr, "egress"):
        if _permits(r.attrs) and "cidr_blocks" in r.attrs:
            return r
    raise OperatorNotApplicable("no app-group egress rule carrying 5432 with cidr_blocks")


def _assert_no_other_egress_carrier(m: HCLModel, keep: _RuleRef) -> None:
    """B1/B2 precondition: no other egress rule of any S group may permit 5432."""
    _, s = _find_res(m, "aws_instance")
    for g in _groups_of(s):
        for r in _rule_refs(m, g, "egress"):
            if r.attrs is not keep.attrs and _permits(r.attrs):
                raise OperatorNotApplicable("another egress rule permits 5432; the break would not hold")


def _db_ingress_carrier(m: HCLModel) -> _RuleRef:
    """The DB group's 5432 ingress rule whose source is a security group."""
    db_addr, _ = _find_db_sg(m)
    for r in _rule_refs(m, db_addr, "ingress"):
        if _permits(r.attrs) and _sources(r.attrs):
            return r
    raise OperatorNotApplicable("no DB-group 5432 ingress rule with a security-group source")


# ---------------------------------------------------------------------------
# INV-FUNC-001 break mechanisms (registry 6.3 / 6.4). Each reaches row 3 or 9 and
# never row 2 or 8. None of them empties vpc_security_group_ids.
# ---------------------------------------------------------------------------


def _egress_cidr(m: HCLModel, name: str, step: int, mode: str) -> list[MutationRow]:
    """Egress CIDR on the app group. mode: exact | supernet (safe, full cover) | disjoint (B2, row 9)."""
    carrier = _egress_carrier(m)
    vpc = _vpc_net(m)
    new = {"exact": str(vpc), "supernet": _private_supernet(vpc), "disjoint": _disjoint_cidr(vpc)}[mode]
    rows: list[MutationRow] = []
    _edit(rows, step, name, carrier.addr, carrier.attrs, "cidr_blocks", SortedList([new]))
    if mode == "disjoint":
        _assert_no_other_egress_carrier(m, carrier)
    return rows


def _egress_ports(m: HCLModel, name: str, step: int, lo: int, hi: int) -> list[MutationRow]:
    """Egress port range on the app group: [lo, hi] either includes 5432 (safe) or excludes it (B1, row 9)."""
    carrier = _egress_carrier(m)
    rows: list[MutationRow] = []
    _edit(rows, step, name, carrier.addr, carrier.attrs, "protocol", "tcp")
    _edit(rows, step, name, carrier.addr, carrier.attrs, "from_port", lo)
    _edit(rows, step, name, carrier.addr, carrier.attrs, "to_port", hi)
    if not (lo <= 5432 <= hi):
        _assert_no_other_egress_carrier(m, carrier)
    return rows


def _b3_db_ingress_port(m: HCLModel, name: str, step: int) -> list[MutationRow]:
    """B3: the DB group's 5432 ingress rule gets a port range that excludes 5432 (E6 fails, row 9).

    The rule or block stays in place, so no group becomes RETAINED-INLINE.
    """
    carrier = _db_ingress_carrier(m)
    rows: list[MutationRow] = []
    _edit(rows, step, name, carrier.addr, carrier.attrs, "from_port", 5433)
    _edit(rows, step, name, carrier.addr, carrier.attrs, "to_port", 5433)
    return rows


def _add_peer_group(m: HCLModel, name: str, step: int, tag: str, desc: str) -> tuple[str, list[MutationRow]]:
    """Add a new, empty client group in the DB group's VPC. It is not in SG(S)."""
    _, db = _find_db_sg(m)
    peer_name = f"{db.name}_{tag}"
    peer_addr = f"aws_security_group.{peer_name}"
    if peer_addr in m.resources:
        raise OperatorNotApplicable(f"{peer_addr} already exists")
    attrs = {
        "description": desc,
        "name": f"{db.attrs['name']}-{tag}",
        "vpc_id": db.attrs["vpc_id"],
    }
    m.add(Resource("aws_security_group", peer_name, attrs))
    return peer_addr, _added_rows(step, name, peer_addr, attrs)


def _b4_repoint_db_ingress(m: HCLModel, name: str, step: int, tag: str, desc: str) -> list[MutationRow]:
    """B4: the DB group's 5432 ingress rule is re-pointed to a group that is not in SG(S) (row 9)."""
    carrier = _db_ingress_carrier(m)
    peer_addr, rows = _add_peer_group(m, name, step, tag, desc)
    ref = Ref(f"{peer_addr}.id")
    if carrier.kind == "rule":
        _edit(rows, step, name, carrier.addr, carrier.attrs, "source_security_group_id", ref)
    else:
        _edit(rows, step, name, carrier.addr, carrier.attrs, "security_groups", [ref])
    return rows


def _b5_db_port(m: HCLModel, name: str, step: int) -> list[MutationRow]:
    """B5: D.port is set to a value other than 5432 (registry 6.4 row 3)."""
    d_addr, d = _find_res(m, "aws_db_instance")
    rows: list[MutationRow] = []
    _edit(rows, step, name, d_addr, d.attrs, "port", 5433)
    return rows


# ---------------------------------------------------------------------------
# SSH and DB-ingress repair helpers (F2, F4, F8)
# ---------------------------------------------------------------------------


def _repair_world_cidr(m: HCLModel, name: str, step: int, port: int, safe: bool, narrow_to: str) -> list[MutationRow]:
    """Narrow a world-open IPv4 ingress on ``port`` to ``narrow_to``.

    ``safe=False`` models a partial repair: the IPv4 CIDR is narrowed too, but ``::/0`` is
    left open through ``ipv6_cidr_blocks``, so the invariant is still violated.
    """
    holders: list[tuple[str, dict[str, Any]]] = []
    for addr, res in m.resources.items():
        if res.type == "aws_security_group_rule" and res.attrs.get("type") == "ingress":
            holders.append((addr, res.attrs))
    for addr, res in m.resources.items():
        if res.type == "aws_security_group":
            for b in res.blocks:
                if b.label == "ingress":
                    holders.append((addr, b.attrs))
    for addr, attrs in holders:
        if int(attrs.get("to_port", -1)) != port and int(attrs.get("from_port", -1)) != port:
            continue
        cidrs = _cidrs(attrs.get("cidr_blocks"))
        if "0.0.0.0/0" not in cidrs and "::/0" not in cidrs:
            continue
        rows: list[MutationRow] = []
        _edit(rows, step, name, addr, attrs, "cidr_blocks", SortedList([narrow_to]))
        if not safe:
            _edit(rows, step, name, addr, attrs, "ipv6_cidr_blocks", SortedList(["::/0"]))
        return rows
    raise OperatorNotApplicable(f"No world-open ingress on port {port} (separate or inline) found to repair in model")


def _repair_ssh(m: HCLModel, name: str, step: int, *, safe: bool) -> list[MutationRow]:
    return _repair_world_cidr(m, name, step, 22, safe, "10.0.0.0/8")


def _repair_db_ingress(m: HCLModel, name: str, step: int, *, safe: bool) -> list[MutationRow]:
    return _repair_world_cidr(m, name, step, 5432, safe, _private_supernet(_vpc_net(m)))


def _break_sec_001_open_ssh(m: HCLModel, name: str, step: int) -> list[MutationRow]:
    """Break INV-SEC-001 by introducing public SSH (port 22) ingress on application SG."""
    app_addr, app_sg = _find_app_sg(m)
    if app_sg.blocks:
        b = Block("ingress", {
            "cidr_blocks": SortedList(["0.0.0.0/0"]),
            "from_port": 22,
            "protocol": "tcp",
            "to_port": 22,
        })
        app_sg.blocks.append(b)
        return _added_rows(step, name, app_addr, b.attrs)
    rule_name = f"{app_sg.name}_ingress_ssh"
    rule_addr = f"aws_security_group_rule.{rule_name}"
    attrs = {
        "cidr_blocks": SortedList(["0.0.0.0/0"]),
        "from_port": 22,
        "protocol": "tcp",
        "security_group_id": Ref(f"{app_addr}.id"),
        "to_port": 22,
        "type": "ingress",
    }
    m.add(Resource("aws_security_group_rule", rule_name, attrs))
    return _added_rows(step, name, rule_addr, attrs)


def _break_sec_002_open_db(m: HCLModel, name: str, step: int) -> list[MutationRow]:
    """Break INV-SEC-002 by introducing public DB (port 5432) ingress on database SG."""
    db_addr, db_sg = _find_db_sg(m)
    if db_sg.blocks:
        b = Block("ingress", {
            "cidr_blocks": SortedList(["0.0.0.0/0"]),
            "from_port": 5432,
            "protocol": "tcp",
            "to_port": 5432,
        })
        db_sg.blocks.append(b)
        return _added_rows(step, name, db_addr, b.attrs)
    rule_name = f"{db_sg.name}_ingress_db_public"
    rule_addr = f"aws_security_group_rule.{rule_name}"
    attrs = {
        "cidr_blocks": SortedList(["0.0.0.0/0"]),
        "from_port": 5432,
        "protocol": "tcp",
        "security_group_id": Ref(f"{db_addr}.id"),
        "to_port": 5432,
        "type": "ingress",
    }
    m.add(Resource("aws_security_group_rule", rule_name, attrs))
    return _added_rows(step, name, rule_addr, attrs)


def _next_instance_type(old_size: str) -> str:
    cycle = {
        "t3.nano": "t3.micro",
        "t3.micro": "t3.small",
        "t3.small": "t3.medium",
        "t3.medium": "t3.large",
        "t3.large": "t3.xlarge",
    }
    return cycle.get(old_size, "t3.large" if old_size != "t3.large" else "t3.xlarge")


# ---------------------------------------------------------------------------
# Family F1: Unrelated change (change_request)
# The hidden side effect of the three unsafe operators breaks INV-SEC-003,
# INV-SEC-002 and INV-SEC-001 respectively.
# ---------------------------------------------------------------------------

_ALL_INVARIANTS = ["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"]


def _keep(*broken: str) -> list[str]:
    return [i for i in _ALL_INVARIANTS if i not in broken]


def _f1_resize_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, ec2 = _find_res(m1, "aws_instance")
    old_size = str(ec2.attrs.get("instance_type", "t3.micro"))
    rows: list[MutationRow] = []
    _edit(rows, 1, name, addr, ec2.attrs, "instance_type", _next_instance_type(old_size))
    if not is_safe_name(name):
        db_addr, db = _find_res(m1, "aws_db_instance")
        _edit(rows, 1, name, db_addr, db.attrs, "publicly_accessible", True)
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f1_instance_resize_safe", family="F1", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Resizes application EC2 instance type safely.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f1_resize_apply,
))
register_op(OperatorDef(
    name="op_f1_instance_resize_unsafe", family="F1", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Resizes EC2 instance with side effect making DB publicly accessible.",
    intent_breaks=["INV-SEC-003"], intent_preserves=_keep("INV-SEC-003"),
    apply_fn=_f1_resize_apply,
))


def _f1_storage_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, db = _find_res(m1, "aws_db_instance")
    old_storage = int(db.attrs.get("allocated_storage", 20))
    rows: list[MutationRow] = []
    _edit(rows, 1, name, addr, db.attrs, "allocated_storage", old_storage + 10)
    if not is_safe_name(name):
        rows.extend(_break_sec_002_open_db(m1, name, step=1))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f1_storage_expand_safe", family="F1", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Expands RDS allocated storage safely.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f1_storage_apply,
))
register_op(OperatorDef(
    name="op_f1_storage_expand_unsafe", family="F1", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Expands RDS storage with side effect opening port 5432 to the world on the DB group.",
    intent_breaks=["INV-SEC-002"], intent_preserves=_keep("INV-SEC-002"),
    apply_fn=_f1_storage_apply,
))


def _f1_vpc_dns_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, vpc = _find_res(m1, "aws_vpc")
    rows: list[MutationRow] = []
    _edit(rows, 1, name, addr, vpc.attrs, "enable_dns_hostnames", False)
    if not is_safe_name(name):
        rows.extend(_break_sec_001_open_ssh(m1, name, step=1))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f1_vpc_dns_toggle_safe", family="F1", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Disables VPC DNS hostnames safely.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f1_vpc_dns_apply,
))
register_op(OperatorDef(
    name="op_f1_vpc_dns_toggle_unsafe", family="F1", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Disables VPC DNS hostnames with side effect opening SSH to the world on the app group.",
    intent_breaks=["INV-SEC-001"], intent_preserves=_keep("INV-SEC-001"),
    apply_fn=_f1_vpc_dns_apply,
))


# ---------------------------------------------------------------------------
# Family F2: Direct impact (repair)
# ---------------------------------------------------------------------------

def _f2_repair_ssh_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    rows = _repair_ssh(m1, name, step=1, safe=is_safe_name(name))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f2_repair_ssh_safe", family="F2", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Repairs public SSH ingress by narrowing CIDR.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f2_repair_ssh_apply,
))
register_op(OperatorDef(
    name="op_f2_repair_ssh_unsafe", family="F2", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Narrows the IPv4 CIDR but leaves port 22 open to ::/0 through ipv6_cidr_blocks.",
    intent_breaks=["INV-SEC-001"], intent_preserves=_keep("INV-SEC-001"),
    apply_fn=_f2_repair_ssh_apply,
))


def _f2_repair_db_ingress_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    rows = _repair_db_ingress(m1, name, step=1, safe=is_safe_name(name))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f2_repair_db_ingress_safe", family="F2", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-002",
    description="Repairs public DB port by narrowing the CIDR to the private block that contains the VPC.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f2_repair_db_ingress_apply,
))
register_op(OperatorDef(
    name="op_f2_repair_db_ingress_unsafe", family="F2", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-002",
    description="Narrows the IPv4 CIDR but leaves port 5432 open to ::/0 through ipv6_cidr_blocks.",
    intent_breaks=["INV-SEC-002"], intent_preserves=_keep("INV-SEC-002"),
    apply_fn=_f2_repair_db_ingress_apply,
))


def _f2_repair_db_public_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, db = _find_res(m1, "aws_db_instance")
    rows: list[MutationRow] = []
    if is_safe_name(name):
        _edit(rows, 1, name, addr, db.attrs, "publicly_accessible", False)
    else:
        _edit(rows, 1, name, addr, db.attrs, "backup_retention_period", 7)
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f2_repair_db_public_safe", family="F2", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-003",
    description="Repairs RDS publicly accessible flag to false.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f2_repair_db_public_apply,
))
register_op(OperatorDef(
    name="op_f2_repair_db_public_unsafe", family="F2", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-003",
    description="Sets a backup retention period and leaves the RDS instance publicly accessible.",
    intent_breaks=["INV-SEC-003"], intent_preserves=_keep("INV-SEC-003"),
    apply_fn=_f2_repair_db_public_apply,
))


# ---------------------------------------------------------------------------
# Family F3: Dependency-induced impact (change_request)
# Unsafe INV-FUNC-001 breaks run through a security group rule or group that the
# endpoints use (B1, B2, B4), never through an attribute of S or D.
# ---------------------------------------------------------------------------

def _f3_subnet_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    sub_addr, sub = _find_res(m1, "aws_subnet")
    old_az = str(sub.attrs.get("availability_zone", "us-east-1a"))
    new_az = "us-east-1b" if old_az == "us-east-1a" else "us-east-1a"
    rows: list[MutationRow] = []
    _edit(rows, 1, name, sub_addr, sub.attrs, "availability_zone", new_az)
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f3_app_subnet_az_change_safe", family="F3", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Changes the availability zone of the application subnet (same VPC, same route table).",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f3_subnet_apply,
))


def _f3_dbsng_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    dbsng_addr, dbsng = _find_res(m1, "aws_db_subnet_group")
    old_ids = dbsng.attrs.get("subnet_ids", [])
    old_list = list(old_ids.items) if hasattr(old_ids, "items") else list(old_ids)
    rows: list[MutationRow] = []
    _edit(rows, 1, name, dbsng_addr, dbsng.attrs, "subnet_ids", list(reversed(old_list)))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f3_modify_db_subnet_group_safe", family="F3", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Reorders subnets in DB subnet group safely.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f3_dbsng_apply,
))


def _f3_egress_cidr_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    mode = "exact" if is_safe_name(name) else "disjoint"
    return [m1], [_egress_cidr(m1, name, 1, mode)]


register_op(OperatorDef(
    name="op_f3_app_egress_cidr_safe", family="F3", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Narrows the app group egress CIDR to exactly CIDR(VPC(D)), computed from the scenario.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f3_egress_cidr_apply,
))
register_op(OperatorDef(
    name="op_f3_app_egress_cidr_unsafe", family="F3", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Restricts the app group egress to a CIDR disjoint from CIDR(VPC(D)).",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f3_egress_cidr_apply, mechanism="B2", designed_row=9,
))


def _f3_egress_ports_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    lo, hi = (5432, 5432) if is_safe_name(name) else (443, 443)
    return [m1], [_egress_ports(m1, name, 1, lo, hi)]


register_op(OperatorDef(
    name="op_f3_app_egress_ports_safe", family="F3", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Restricts the app group egress to TCP 5432 only.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f3_egress_ports_apply,
))
register_op(OperatorDef(
    name="op_f3_app_egress_ports_unsafe", family="F3", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Restricts the app group egress to TCP 443 only, with no rule permitting 5432.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f3_egress_ports_apply, mechanism="B1", designed_row=9,
))


def _add_peer_ingress(m: HCLModel, name: str, step: int, tag: str, desc: str) -> list[MutationRow]:
    """Add a new client group and an extra 5432 ingress rule from it; the app rule is kept."""
    carrier = _db_ingress_carrier(m)
    db_addr, db = _find_db_sg(m)
    peer_addr, rows = _add_peer_group(m, name, step, tag, desc)
    ref = Ref(f"{peer_addr}.id")
    if carrier.kind == "rule":
        new_name = f"{carrier.res.name}_{tag}"
        attrs = {
            "from_port": 5432,
            "protocol": "tcp",
            "security_group_id": Ref(f"{db_addr}.id"),
            "source_security_group_id": ref,
            "to_port": 5432,
            "type": "ingress",
        }
        m.add(Resource("aws_security_group_rule", new_name, attrs))
        rows.extend(_added_rows(step, name, f"aws_security_group_rule.{new_name}", attrs))
    else:
        b = Block("ingress", {"from_port": 5432, "protocol": "tcp", "security_groups": [ref], "to_port": 5432})
        db.blocks.append(b)
        rows.extend(_added_rows(step, name, db_addr, b.attrs))
    return rows


def _f3_db_ingress_peer_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    desc = "Dependent client security group"
    if is_safe_name(name):
        rows = _add_peer_ingress(m1, name, 1, "peer", desc)
    else:
        rows = _b4_repoint_db_ingress(m1, name, 1, "peer", desc)
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f3_db_ingress_peer_safe", family="F3", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Adds a new client group and an extra 5432 ingress rule from it; the app rule is kept.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f3_db_ingress_peer_apply,
))
register_op(OperatorDef(
    name="op_f3_db_ingress_peer_unsafe", family="F3", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Adds a new client group and re-points the DB group's 5432 ingress source to it.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f3_db_ingress_peer_apply, mechanism="B4", designed_row=9,
))


# ---------------------------------------------------------------------------
# Family F4: Regression-inducing repair (repair)
# ---------------------------------------------------------------------------

def _f4_repair_ssh_break_db_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    rows = _repair_ssh(m1, name, step=1, safe=True)
    if not is_safe_name(name):
        rows.extend(_b3_db_ingress_port(m1, name, step=1))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f4_repair_ssh_break_db_ingress_safe", family="F4", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Repairs SSH by narrowing the public rule; the DB group's 5432 ingress is untouched.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f4_repair_ssh_break_db_apply,
))
register_op(OperatorDef(
    name="op_f4_repair_ssh_break_db_ingress_unsafe", family="F4", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Repairs SSH, and moves the DB group's 5432 ingress rule to port 5433.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f4_repair_ssh_break_db_apply, mechanism="B3", designed_row=9,
))


def _f4_repair_db_port_open_ssh_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    rows = _repair_db_ingress(m1, name, step=1, safe=True)
    if not is_safe_name(name):
        rows.extend(_break_sec_001_open_ssh(m1, name, step=1))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f4_repair_db_port_open_ssh_safe", family="F4", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-002",
    description="Repairs DB port safely without regressions.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f4_repair_db_port_open_ssh_apply,
))
register_op(OperatorDef(
    name="op_f4_repair_db_port_open_ssh_unsafe", family="F4", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-002",
    description="Repairs DB port but opens port 22 to the world, breaking INV-SEC-001.",
    intent_breaks=["INV-SEC-001"], intent_preserves=_keep("INV-SEC-001"),
    apply_fn=_f4_repair_db_port_open_ssh_apply,
))


def _f4_repair_rds_public_open_db_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    db_addr, db = _find_res(m1, "aws_db_instance")
    rows: list[MutationRow] = []
    _edit(rows, 1, name, db_addr, db.attrs, "publicly_accessible", False)
    if not is_safe_name(name):
        rows.extend(_break_sec_002_open_db(m1, name, step=1))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f4_repair_rds_public_open_db_safe", family="F4", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-003",
    description="Repairs RDS publicly accessible safely.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f4_repair_rds_public_open_db_apply,
))
register_op(OperatorDef(
    name="op_f4_repair_rds_public_open_db_unsafe", family="F4", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-003",
    description="Repairs RDS publicly accessible but opens port 5432 to the world, breaking INV-SEC-002.",
    intent_breaks=["INV-SEC-002"], intent_preserves=_keep("INV-SEC-002"),
    apply_fn=_f4_repair_rds_public_open_db_apply,
))


# ---------------------------------------------------------------------------
# Family F5: Restructuring / replacement (change_request)
# The three unsafe operators break INV-FUNC-001 through the restructuring of the DB
# group or its 5432 rule (B3, B4). No unsafe F5 operator edits S or D.
# Direction note: only separate rules -> inline blocks is evaluable. Inline blocks ->
# separate rules would leave the group RETAINED-INLINE or MIXED (registry 2.6, A10).
# ---------------------------------------------------------------------------

def _f5_separate_to_inline_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    """Move every separate rule of the DB group into inline blocks of that group."""
    m1 = base.copy()
    db_addr, db = _find_db_sg(m1)
    if db.blocks:
        raise OperatorNotApplicable("DB group already holds inline blocks")
    carrier = _db_ingress_carrier(m1)
    if carrier.kind != "rule":
        raise OperatorNotApplicable("DB 5432 ingress is not a separate rule")
    rules = [(a, r) for a, r in m1.resources.items()
             if r.type == "aws_security_group_rule" and str(r.attrs.get("security_group_id")) == f"{db_addr}.id"]
    unsafe = not is_safe_name(name)
    rows: list[MutationRow] = []
    new_blocks: list[Block] = []
    for addr, res in rules:
        rows.extend(_removed_rows(1, name, addr, res.attrs))
        del m1.resources[addr]
        if unsafe and addr == carrier.addr:
            continue  # B3: the 5432 rule is not carried into the inline form
        battrs = {k: v for k, v in res.attrs.items()
                  if k not in ("type", "security_group_id", "source_security_group_id")}
        if "source_security_group_id" in res.attrs:
            battrs["security_groups"] = [res.attrs["source_security_group_id"]]
        new_blocks.append(Block(str(res.attrs["type"]), battrs))
    db.blocks.extend(new_blocks)
    for b in new_blocks:
        rows.extend(_added_rows(1, name, db_addr, b.attrs))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_separate_to_inline_rules_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Moves every separate rule of the DB group into inline blocks with identical ports, protocols and sources.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f5_separate_to_inline_apply,
))
register_op(OperatorDef(
    name="op_f5_separate_to_inline_rules_unsafe", family="F5", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Moves the DB group's rules into inline blocks and drops the 5432 ingress rule in the process.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f5_separate_to_inline_apply, mechanism="B3", designed_row=9,
))


def _f5_moved_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    sub_addr, sub = _find_res(m1, "aws_subnet")
    old_name = sub.name
    new_name = f"{old_name}_app"
    old_attrs = copy.deepcopy(sub.attrs)

    del m1.resources[sub_addr]
    sub.name = new_name
    m1.add(sub)

    m1.add_moved(Ref(f"aws_subnet.{old_name}"), Ref(f"aws_subnet.{new_name}"))

    rows: list[MutationRow] = []

    # Update all resources that referenced the old subnet
    for res_addr, res in sorted(m1.resources.items()):
        val = res.attrs.get("subnet_id")
        if val is not None and str(val) == f"aws_subnet.{old_name}.id":
            res.set_attr("subnet_id", Ref(f"aws_subnet.{new_name}.id"))
            rows.append(MutationRow(
                step=1, operator=name, target_address=res_addr,
                attribute="subnet_id", before=f"aws_subnet.{old_name}.id", after=f"aws_subnet.{new_name}.id"
            ))
    rows.extend(_removed_rows(1, name, f"aws_subnet.{old_name}", old_attrs))
    rows.extend(_added_rows(1, name, f"aws_subnet.{new_name}", sub.attrs))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_restructure_moved_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Renames the application subnet with a moved block and updates its references.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f5_moved_apply,
))


def _f5_db_rule_moved_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    """Rename the DB group's 5432 ingress rule resource with a moved block."""
    m1 = base.copy()
    carrier = _db_ingress_carrier(m1)
    if carrier.kind != "rule":
        raise OperatorNotApplicable("DB 5432 ingress is not a separate rule")
    old_addr, old = carrier.addr, carrier.res
    rows: list[MutationRow] = []
    new_attrs = dict(old.attrs)
    if not is_safe_name(name):
        peer_addr, prows = _add_peer_group(m1, name, 1, "peer", "Client group of the recreated rule")
        rows.extend(prows)
        new_attrs["source_security_group_id"] = Ref(f"{peer_addr}.id")
    new_name = f"{old.name}_v2"
    new_addr = f"aws_security_group_rule.{new_name}"
    del m1.resources[old_addr]
    m1.add(Resource("aws_security_group_rule", new_name, new_attrs))
    m1.add_moved(Ref(old_addr), Ref(new_addr))
    rows.extend(_removed_rows(1, name, old_addr, old.attrs))
    rows.extend(_added_rows(1, name, new_addr, new_attrs))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_db_rule_moved_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Renames the DB group's 5432 ingress rule with a moved block; all attributes are identical.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f5_db_rule_moved_apply,
))
register_op(OperatorDef(
    name="op_f5_db_rule_moved_unsafe", family="F5", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Renames the 5432 ingress rule with a moved block; the recreated rule points to a new group outside SG(S).",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f5_db_rule_moved_apply, mechanism="B4", designed_row=9,
))


def _f5_replace_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_ami = str(ec2.attrs.get("ami", "ami-0c55b159cbfafe1f0"))
    new_ami = "ami-0d5eff06f840b45e9" if old_ami == "ami-0c55b159cbfafe1f0" else "ami-0c55b159cbfafe1f0"
    rows: list[MutationRow] = []
    _edit(rows, 1, name, ec2_addr, ec2.attrs, "ami", new_ami)
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_force_replacement_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Forces replacement of the application instance by changing its AMI.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f5_replace_apply,
))


def _f5_db_sg_replace_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    """Force replacement of the DB group by changing its name (a force-new attribute)."""
    m1 = base.copy()
    db_addr, db = _find_db_sg(m1)
    rows: list[MutationRow] = []
    _edit(rows, 1, name, db_addr, db.attrs, "name", f"{db.attrs['name']}-v2")
    if not is_safe_name(name):
        rows.extend(_b3_db_ingress_port(m1, name, step=1))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_db_sg_replacement_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Forces replacement of the DB group by changing its name; its rules are unchanged.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f5_db_sg_replace_apply,
))
register_op(OperatorDef(
    name="op_f5_db_sg_replacement_unsafe", family="F5", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Forces replacement of the DB group; the recreated 5432 ingress carries port 5433.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f5_db_sg_replace_apply, mechanism="B3", designed_row=9,
))


def _f5_count_each_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    rows: list[MutationRow] = []
    if "count" in ec2.attrs:
        _edit(rows, 1, name, ec2_addr, ec2.attrs, "count", _DELETE)
    else:
        _edit(rows, 1, name, ec2_addr, ec2.attrs, "count", 1)
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_count_each_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Adds or removes count = 1 on the application instance.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f5_count_each_apply,
))


# ---------------------------------------------------------------------------
# Family F6: New-resource creation (change_request)
# ---------------------------------------------------------------------------

def _f6_sg_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    vpc_addr, _ = _find_res(m1, "aws_vpc")
    _, ec2_res = _find_res(m1, "aws_instance")
    is_graft = ec2_res.name.startswith("tp_")
    sg_name = "tp_monitoring_sg" if is_graft else "monitoring_sg"
    is_unsafe = "unsafe" in name
    blocks: list[Block] = []
    if is_unsafe:
        blocks.append(Block("ingress", {
            "cidr_blocks": SortedList(["0.0.0.0/0"]),
            "from_port": 5432,
            "protocol": "tcp",
            "to_port": 5432,
        }))

    sg_res = Resource(
        "aws_security_group", sg_name,
        {
            "description": "Monitoring security group",
            "name": f"{sg_name}-mon",
            "vpc_id": Ref(f"{vpc_addr}.id"),
        },
        blocks=blocks,
    )
    m1.add(sg_res)
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_sgs = list(ec2.attrs.get("vpc_security_group_ids", []))
    new_sgs = old_sgs + [Ref(f"aws_security_group.{sg_name}.id")]
    ec2.set_attr("vpc_security_group_ids", new_sgs)

    rows = [
        MutationRow(
            step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
            attribute="description", before=None, after='"Monitoring security group"',
        ),
        MutationRow(
            step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
            attribute="name", before=None, after=f'"{sg_name}-mon"',
        ),
        MutationRow(
            step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
            attribute="vpc_id", before=None, after=f"{vpc_addr}.id",
        ),
        MutationRow(
            step=1, operator=name, target_address=ec2_addr,
            attribute="vpc_security_group_ids",
            before=f"[{', '.join(str(s) for s in old_sgs)}]",
            after=f"[{', '.join(str(s) for s in new_sgs)}]",
        )
    ]
    if is_unsafe:
        rows.extend([
            MutationRow(
                step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
                attribute="cidr_blocks", before=None, after='["0.0.0.0/0"]',
            ),
            MutationRow(
                step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
                attribute="from_port", before=None, after="5432",
            ),
            MutationRow(
                step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
                attribute="protocol", before=None, after='"tcp"',
            ),
            MutationRow(
                step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
                attribute="to_port", before=None, after="5432",
            ),
        ])
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f6_add_monitoring_sg_safe", family="F6", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Adds new monitoring security group safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f6_sg_apply,
))
register_op(OperatorDef(
    name="op_f6_add_monitoring_sg_unsafe", family="F6", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Adds monitoring security group open on 5432, breaking INV-SEC-002.",
    intent_breaks=["INV-SEC-002"], intent_preserves=["INV-SEC-001", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f6_sg_apply,
))


def _f6_bastion_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    sub_addr, _ = _find_res(m1, "aws_subnet")
    _, ec2_res = _find_res(m1, "aws_instance")
    is_graft = ec2_res.name.startswith("tp_")
    bastion_name = "tp_bastion" if is_graft else "bastion"
    bsg_name = "tp_bastion_sg" if is_graft else "bastion_sg"
    bastion = Resource(
        "aws_instance", bastion_name,
        {
            "ami": "ami-0c55b159cbfafe1f0",
            "instance_type": "t3.nano",
            "subnet_id": Ref(f"{sub_addr}.id"),
        }
    )
    m1.add(bastion)
    rows = [
        MutationRow(step=1, operator=name, target_address=f"aws_instance.{bastion_name}", attribute="ami", before=None, after='"ami-0c55b159cbfafe1f0"'),
        MutationRow(step=1, operator=name, target_address=f"aws_instance.{bastion_name}", attribute="instance_type", before=None, after='"t3.nano"'),
        MutationRow(step=1, operator=name, target_address=f"aws_instance.{bastion_name}", attribute="subnet_id", before=None, after=f"{sub_addr}.id"),
    ]
    if "unsafe" in name:
        vpc_addr, _ = _find_res(m1, "aws_vpc")
        bsg = Resource(
            "aws_security_group", bsg_name,
            {
                "description": "Bastion security group",
                "name": f"{bsg_name}-host",
                "vpc_id": Ref(f"{vpc_addr}.id"),
            },
            blocks=[Block("ingress", {"cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 22, "protocol": "tcp", "to_port": 22})]
        )
        m1.add(bsg)
        bastion.set_attr("vpc_security_group_ids", [Ref(f"aws_security_group.{bsg_name}.id")])
        rows.extend([
            MutationRow(step=1, operator=name, target_address=f"aws_instance.{bastion_name}", attribute="vpc_security_group_ids", before=None, after=f"[aws_security_group.{bsg_name}.id]"),
            MutationRow(step=1, operator=name, target_address=f"aws_security_group.{bsg_name}", attribute="description", before=None, after='"Bastion security group"'),
            MutationRow(step=1, operator=name, target_address=f"aws_security_group.{bsg_name}", attribute="name", before=None, after=f'"{bsg_name}-host"'),
            MutationRow(step=1, operator=name, target_address=f"aws_security_group.{bsg_name}", attribute="vpc_id", before=None, after=f"{vpc_addr}.id"),
            MutationRow(step=1, operator=name, target_address=f"aws_security_group.{bsg_name}", attribute="cidr_blocks", before=None, after='["0.0.0.0/0"]'),
            MutationRow(step=1, operator=name, target_address=f"aws_security_group.{bsg_name}", attribute="from_port", before=None, after="22"),
            MutationRow(step=1, operator=name, target_address=f"aws_security_group.{bsg_name}", attribute="protocol", before=None, after='"tcp"'),
            MutationRow(step=1, operator=name, target_address=f"aws_security_group.{bsg_name}", attribute="to_port", before=None, after="22"),
        ])
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f6_add_bastion_host_safe", family="F6", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Adds new bastion EC2 instance safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f6_bastion_apply,
))
register_op(OperatorDef(
    name="op_f6_add_bastion_host_unsafe", family="F6", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Adds new bastion instance with port 22 open to the world, breaking INV-SEC-001.",
    intent_breaks=["INV-SEC-001"], intent_preserves=["INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f6_bastion_apply,
))


def _f6_replica_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    dbsng_addr, _ = _find_res(m1, "aws_db_subnet_group")
    _, ec2_res = _find_res(m1, "aws_instance")
    is_graft = ec2_res.name.startswith("tp_")
    replica_name = "tp_replica" if is_graft else "replica"
    is_unsafe = "unsafe" in name
    replica = Resource(
        "aws_db_instance", replica_name,
        {
            "allocated_storage": 20,
            "db_subnet_group_name": Ref(f"{dbsng_addr}.name"),
            "engine": "postgres",
            "identifier": "tp-replica-db" if is_graft else "db-replica",
            "instance_class": "db.t3.micro",
            "publicly_accessible": is_unsafe,
        }
    )
    m1.add(replica)
    rows = [
        MutationRow(step=1, operator=name, target_address=f"aws_db_instance.{replica_name}", attribute="allocated_storage", before=None, after="20"),
        MutationRow(step=1, operator=name, target_address=f"aws_db_instance.{replica_name}", attribute="db_subnet_group_name", before=None, after=f"{dbsng_addr}.name"),
        MutationRow(step=1, operator=name, target_address=f"aws_db_instance.{replica_name}", attribute="engine", before=None, after='"postgres"'),
        MutationRow(step=1, operator=name, target_address=f"aws_db_instance.{replica_name}", attribute="identifier", before=None, after='"tp-replica-db"' if is_graft else '"db-replica"'),
        MutationRow(step=1, operator=name, target_address=f"aws_db_instance.{replica_name}", attribute="instance_class", before=None, after='"db.t3.micro"'),
        MutationRow(step=1, operator=name, target_address=f"aws_db_instance.{replica_name}", attribute="publicly_accessible", before=None, after="true" if is_unsafe else "false"),
    ]
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f6_add_read_replica_safe", family="F6", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Adds new private read-replica RDS instance safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f6_replica_apply,
))
register_op(OperatorDef(
    name="op_f6_add_read_replica_unsafe", family="F6", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Adds new read-replica RDS instance with publicly_accessible=true, breaking INV-SEC-003.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f6_replica_apply,
))


# ---------------------------------------------------------------------------
# Family F7: Broad impact (change_request)
# Hub = a security group shared by the app path (the app group or the DB group) or the VPC.
# Unsafe INV-FUNC-001 breaks run through the shared group (B1, B2, B4). Every CIDR is
# computed from the scenario's own CIDR(VPC(D)); none is hard-coded.
# ---------------------------------------------------------------------------

def _f7_dns_hostnames_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, vpc = _find_res(m1, "aws_vpc")
    rows: list[MutationRow] = []
    _edit(rows, 1, name, addr, vpc.attrs, "enable_dns_hostnames", False)
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f7_vpc_dns_hostnames_disable_safe", family="F7", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Sets enable_dns_hostnames = false on the VPC. enable_dns_support is never changed.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f7_dns_hostnames_apply,
))


def _f7_egress_cidr_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    mode = "supernet" if is_safe_name(name) else "disjoint"
    return [m1], [_egress_cidr(m1, name, 1, mode)]


register_op(OperatorDef(
    name="op_f7_app_egress_cidr_tighten_safe", family="F7", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Tightens the app group egress to the RFC 1918 block that contains CIDR(VPC(D)).",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f7_egress_cidr_apply,
))
register_op(OperatorDef(
    name="op_f7_app_egress_cidr_tighten_unsafe", family="F7", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Tightens the app group egress to a CIDR disjoint from CIDR(VPC(D)).",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f7_egress_cidr_apply, mechanism="B2", designed_row=9,
))


def _f7_egress_ports_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    lo, hi = (1024, 65535) if is_safe_name(name) else (1, 1023)
    return [m1], [_egress_ports(m1, name, 1, lo, hi)]


register_op(OperatorDef(
    name="op_f7_app_egress_port_range_safe", family="F7", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Restricts the app group egress to TCP 1024-65535, which includes 5432.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f7_egress_ports_apply,
))
register_op(OperatorDef(
    name="op_f7_app_egress_port_range_unsafe", family="F7", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Restricts the app group egress to TCP 1-1023, which excludes 5432.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f7_egress_ports_apply, mechanism="B1", designed_row=9,
))


def _f7_db_ingress_source_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    if is_safe_name(name):
        carrier = _db_ingress_carrier(m1)
        cidr = _app_subnet_cidr(m1)
        key = "source_security_group_id" if carrier.kind == "rule" else "security_groups"
        rows: list[MutationRow] = []
        _edit(rows, 1, name, carrier.addr, carrier.attrs, key, _DELETE)
        _edit(rows, 1, name, carrier.addr, carrier.attrs, "cidr_blocks", SortedList([cidr]))
    else:
        rows = _b4_repoint_db_ingress(m1, name, 1, "hub", "Shared client security group")
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f7_db_ingress_source_safe", family="F7", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Replaces the DB group's 5432 ingress source group with the application subnet CIDR.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f7_db_ingress_source_apply,
))
register_op(OperatorDef(
    name="op_f7_db_ingress_source_unsafe", family="F7", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Re-points the DB group's 5432 ingress source to a new shared group outside SG(S).",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f7_db_ingress_source_apply, mechanism="B4", designed_row=9,
))


# ---------------------------------------------------------------------------
# Family F8: Multi-step remediation (repair, 2 to 4 steps)
# The regression step uses one of B2, B3, B5 and persists to the final step, so the
# final step's intent matches what the last step leaves.
# ---------------------------------------------------------------------------

def _f8_twostep_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    # Step 1: EC2 resize
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_size = str(ec2.attrs.get("instance_type", "t3.micro"))
    r1: list[MutationRow] = []
    _edit(r1, 1, name, ec2_addr, ec2.attrs, "instance_type", _next_instance_type(old_size))

    # Step 2: Repair SSH rule (and, in unsafe, move the DB 5432 ingress off 5432)
    m2 = m1.copy()
    r2 = _repair_ssh(m2, name, step=2, safe=True)
    if not is_safe_name(name):
        r2.extend(_b3_db_ingress_port(m2, name, step=2))
    return [m1, m2], [r1, r2]


register_op(OperatorDef(
    name="op_f8_twostep_repair_safe", family="F8", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Two-step remediation safely resizing and repairing SSH.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f8_twostep_apply,
))
register_op(OperatorDef(
    name="op_f8_twostep_repair_unsafe", family="F8", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Two-step remediation; step 2 repairs SSH and moves the DB 5432 ingress to port 5433.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f8_twostep_apply, mechanism="B3", designed_row=9,
))


def _f8_threestep_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    # Step 1: EC2 resize
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_size = str(ec2.attrs.get("instance_type", "t3.micro"))
    r1: list[MutationRow] = []
    _edit(r1, 1, name, ec2_addr, ec2.attrs, "instance_type", _next_instance_type(old_size))

    # Step 2: DB storage expand (in unsafe, the middle step also sets D.port to 5433)
    m2 = m1.copy()
    db_addr, db = _find_res(m2, "aws_db_instance")
    old_storage = int(db.attrs.get("allocated_storage", 20))
    r2: list[MutationRow] = []
    _edit(r2, 2, name, db_addr, db.attrs, "allocated_storage", old_storage + 10)
    if not is_safe_name(name):
        r2.extend(_b5_db_port(m2, name, step=2))

    # Step 3: Repair SSH
    m3 = m2.copy()
    r3 = _repair_ssh(m3, name, step=3, safe=True)
    return [m1, m2, m3], [r1, r2, r3]


register_op(OperatorDef(
    name="op_f8_threestep_refactor_repair_safe", family="F8", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Three-step remediation sequence safely executing all steps.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f8_threestep_apply,
))
register_op(OperatorDef(
    name="op_f8_threestep_refactor_repair_unsafe", family="F8", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Three-step remediation; step 2 expands storage and sets D.port to 5433; step 3 repairs SSH.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f8_threestep_apply, mechanism="B5", designed_row=3,
))


def _f8_fourstep_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    # Step 1: EC2 resize
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_size = str(ec2.attrs.get("instance_type", "t3.micro"))
    r1: list[MutationRow] = []
    _edit(r1, 1, name, ec2_addr, ec2.attrs, "instance_type", _next_instance_type(old_size))

    # Step 2: DB storage expand
    m2 = m1.copy()
    db_addr, db2 = _find_res(m2, "aws_db_instance")
    old_storage = int(db2.attrs.get("allocated_storage", 20))
    r2: list[MutationRow] = []
    _edit(r2, 2, name, db_addr, db2.attrs, "allocated_storage", old_storage + 20)

    # Step 3: VPC DNS hostnames off (in unsafe, the middle step also restricts the app egress to a disjoint CIDR)
    m3 = m2.copy()
    vpc_addr, vpc3 = _find_res(m3, "aws_vpc")
    r3: list[MutationRow] = []
    _edit(r3, 3, name, vpc_addr, vpc3.attrs, "enable_dns_hostnames", False)
    if not is_safe_name(name):
        r3.extend(_egress_cidr(m3, name, 3, "disjoint"))

    # Step 4: Repair SSH
    m4 = m3.copy()
    r4 = _repair_ssh(m4, name, step=4, safe=True)
    return [m1, m2, m3, m4], [r1, r2, r3, r4]


register_op(OperatorDef(
    name="op_f8_fourstep_maintenance_safe", family="F8", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Four-step maintenance sequence safely executing all steps.",
    intent_breaks=[], intent_preserves=_keep(),
    apply_fn=_f8_fourstep_apply,
))
register_op(OperatorDef(
    name="op_f8_fourstep_maintenance_unsafe", family="F8", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Four-step maintenance sequence; step 3 disables DNS hostnames and restricts app egress to a disjoint CIDR; step 4 repairs SSH.",
    intent_breaks=["INV-FUNC-001"], intent_preserves=_keep("INV-FUNC-001"),
    apply_fn=_f8_fourstep_apply, mechanism="B2", designed_row=9,
))
