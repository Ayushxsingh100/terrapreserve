"""Footprints and oracle_affected (registry 2.9, 3.5, 5.4, 6.6; D5-16).

Two configurations (parent, step k - 1, and candidate, step k) are compared instance by instance after following
moves (2.3), on resolved values. A footprint element is changed when it is created or deleted, when its resolved
value differs, or when it is unresolved on either side (2.9). ``oracle_affected`` is the set of invariants with at
least one changed element. The completeness property (2.9) is checked: a result that differs with no changed
element is a registry defect.

Parent elements are named in the candidate's address space (``parent_to_child_map``), so a moved resource is the
same element on both sides. Two readings are proposed in Open D5-D (registry text, read literally, makes some
elements changed on every step): an argument that neither configuration writes compares as "absent" on both sides
and is not changed (2.2 calls a provider-computed attribute that is not set unresolved, which would make every
unset ``S.private_ip`` a changed element); and the parent counterpart's form is compared through what it
decides, the RETAINED-INLINE status of the direction (form *absent* and the parent counterpart used *blocks*, 2.6):
a baseline has no parent, which would make the element created at step 1 for every group, and the parent's form
alone changes at step k when step k - 1 changed it.
Standard library only.
"""

from __future__ import annotations

from typing import Any, Callable

from oracle import common, func_reach
from oracle.model import ABSENT, Config, Literal, Ref, Unresolved, blocks, field_value, id_list, id_scalar, value, written
from oracle.rules import BLOCKS, Rule, RuleSet

UNRES = ("<unresolved>",)


def _is_unres(v: Any) -> bool:
    if v == UNRES:
        return True
    if isinstance(v, (tuple, frozenset, list)):
        return any(_is_unres(x) for x in v)
    return False


def _norm(v: Any, name: Callable[[str], str]) -> Any:
    """A hashable, comparable form of a value; Unresolved becomes UNRES; references are named after moves."""
    if isinstance(v, Unresolved):
        return UNRES
    if isinstance(v, Ref):
        return ("ref", name(v.address))
    if isinstance(v, Literal):
        return ("literal", v.value)
    if isinstance(v, list):
        return frozenset(_norm(x, name) for x in v)
    if isinstance(v, dict):
        return tuple(sorted((k, _norm(x, name)) for k, x in v.items()))
    return v


def _rule_fields(r: Rule, name: Callable[[str], str]) -> dict[str, Any]:
    owner = r.owner
    if owner.startswith("UNRESOLVED:"):
        target: Any = UNRES
    elif owner.startswith("literal:"):
        target = ("literal", owner[len("literal:"):])
    else:
        target = ("ref", name(owner))
    return {"type": _norm(r.direction, name), "from_port": _norm(r.from_port, name), "to_port": _norm(r.to_port, name),
            "protocol": _norm(r.protocol, name), "cidr_blocks": _norm(r.v4, name),
            "ipv6_cidr_blocks": _norm(r.v6, name), "prefix_list_ids": _norm(r.pl, name),
            "source_security_group_id": _norm(r.src_sg, name), "self": _norm(r.self_, name), "security_group_id": target}


def _blocks(rs: RuleSet, gkey: str, direction: str, name: Callable[[str], str]) -> Any:
    g = rs.groups[gkey]
    if g.form.get(direction) != BLOCKS:
        return ()
    return frozenset(tuple(sorted((k, v) for k, v in _rule_fields(r, name).items() if k not in ("type", "security_group_id")))
                     for r in g.inline.get(direction, []))


class Side:
    """One configuration with its rule set, its own parent's rule set (for C-84 forms) and its endpoints."""

    def __init__(self, config: Config, ruleset: RuleSet, parent_ruleset: RuleSet | None,
                 child_to_parent: dict[str, str], endpoints: dict[str, str]) -> None:
        self.config, self.rs, self.parent_rs, self.c2p, self.endpoints = (config, ruleset, parent_ruleset,
                                                                          child_to_parent, endpoints)


def sec_elements(side: Side, inv: str, name: Callable[[str], str]) -> dict[tuple, Any]:
    el: dict[tuple, Any] = {}
    for gkey, g in side.rs.groups.items():
        if g.pseudo:
            continue
        a = name(gkey)
        el[("sg", a, "exists")] = True
        el[("sg", a, "ingress blocks")] = _blocks(side.rs, gkey, "ingress", name)
        el[("sg", a, "inline egress exists")] = g.form.get("egress") == BLOCKS
        for d in ("ingress", "egress"):
            el[("sg", a, f"{d} form")] = g.form.get(d)
        el[("sg", a, "ingress RETAINED-INLINE")] = bool(g.retained_inline.get("ingress"))
    for r in side.rs.rules:
        if r.inline:
            continue
        a = name(r.address)
        el[("rule", a, "exists")] = True
        for k, v in _rule_fields(r, name).items():
            el[("rule", a, k)] = v
    present = side.config.present_types()
    for t in common.RELEVANT_UNSUPPORTED[inv]:
        el[("type", t, "present")] = t in present
    return el


def sec003_elements(side: Side, name: Callable[[str], str]) -> dict[tuple, Any]:
    el: dict[tuple, Any] = {}
    for d in side.config.of_type("aws_db_instance"):
        a = name(d.address)
        el[("db", a, "exists")] = True
        v = value(d, "publicly_accessible")
        el[("db", a, "publicly_accessible")] = UNRES if isinstance(v, Unresolved) else (False if v in (None, ABSENT) else v)
    return el


def func_context(side: Side) -> dict[str, Any]:
    """SG(S), SG(D), S's subnet, VPC(S), VPC(D) of one side (addresses; empty when not resolved)."""
    cfg = side.config
    S = cfg.instances.get(side.endpoints.get("S", ""))
    D = cfg.instances.get(side.endpoints.get("D", ""))
    ctx: dict[str, Any] = {"S": S, "D": D, "sgs": [], "sgd": [], "subnet": None, "vpcs": []}
    if S is not None:
        lst = id_list(cfg, S, "vpc_security_group_ids")
        ctx["sgs"] = [x.address for x in lst if isinstance(x, Ref)] if isinstance(lst, list) else []
        sub = id_scalar(cfg, S, "subnet_id")
        if isinstance(sub, Ref):
            ctx["subnet"] = sub.address
            v = id_scalar(cfg, cfg.instances[sub.address], "vpc_id")
            if isinstance(v, Ref):
                ctx["vpcs"].append(v.address)
    if D is not None:
        lst = id_list(cfg, D, "vpc_security_group_ids")
        ctx["sgd"] = [x.address for x in lst if isinstance(x, Ref)] if isinstance(lst, list) else []
        for a in ctx["sgd"]:
            g = side.rs.groups.get(a)
            if g is not None and isinstance(g.vpc, Ref):
                ctx["vpcs"].append(g.vpc.address)
    return ctx


def func_elements(side: Side, name: Callable[[str], str], roles: dict[str, set[str]]) -> dict[tuple, Any]:
    """``roles``: addresses (in the candidate's naming) of S's subnets, VPCs, SG(S), SG(D) and VPC(D), from both sides."""
    cfg = side.config
    el: dict[tuple, Any] = {}
    S = cfg.instances.get(side.endpoints.get("S", ""))
    D = cfg.instances.get(side.endpoints.get("D", ""))
    if S is not None:
        el[("S", "exists")] = True
        el[("S", "subnet_id")] = _norm(id_scalar(cfg, S, "subnet_id"), name)
        el[("S", "vpc_security_group_ids")] = _norm(id_list(cfg, S, "vpc_security_group_ids"), name)
        for k in ("security_groups", "private_ip", "network_interface", "primary_network_interface"):
            el[("S", k)] = _norm(value(S, k), name) if written(S, k) or isinstance(value(S, k), list) and value(S, k) \
                else ABSENT
    if D is not None:
        el[("D", "exists")] = True
        el[("D", "vpc_security_group_ids")] = _norm(id_list(cfg, D, "vpc_security_group_ids"), name)
        for k in ("port", "engine"):
            el[("D", k)] = _norm(value(D, k), name) if written(D, k) or k == "engine" else ABSENT
    for a, inst in cfg.instances.items():
        n = name(a)
        if inst.type == "aws_subnet" and n in roles["subnets"]:
            el[("subnet", n, "exists")] = True
            el[("subnet", n, "vpc_id")] = _norm(id_scalar(cfg, inst, "vpc_id"), name)
            el[("subnet", n, "cidr_block")] = _norm(value(inst, "cidr_block"), name)
        if inst.type == "aws_vpc" and n in roles["vpcs"]:
            el[("vpc", n, "exists")] = True
            el[("vpc", n, "cidr_block")] = _norm(value(inst, "cidr_block"), name)
    for gkey, g in side.rs.groups.items():
        if g.pseudo:
            continue
        n = name(gkey)
        if n not in roles["sgs"] and n not in roles["sgd"]:
            continue
        el[("fsg", n, "exists")] = True
        el[("fsg", n, "vpc_id")] = _norm(g.vpc, name) if g.vpc is not ABSENT else ABSENT
        el[("fsg", n, "inline blocks present")] = tuple(g.form.get(d) == BLOCKS for d in ("ingress", "egress"))
        for d in ("ingress", "egress"):
            el[("fsg", n, f"{d} form")] = g.form.get(d)
        if n in roles["sgs"]:
            el[("fsg", n, "egress blocks")] = _blocks(side.rs, gkey, "egress", name)
            el[("fsg", n, "egress RETAINED-INLINE")] = bool(g.retained_inline.get("egress"))
        if n in roles["sgd"]:
            el[("fsg", n, "ingress blocks")] = _blocks(side.rs, gkey, "ingress", name)
            el[("fsg", n, "ingress RETAINED-INLINE")] = bool(g.retained_inline.get("ingress"))
    for r in side.rs.rules:
        if r.inline:
            continue
        target = r.owner
        if not (target.startswith("UNRESOLVED:") or name(target) in roles["sgs"] or name(target) in roles["sgd"]):
            continue
        a = name(r.address)
        el[("rule", a, "exists")] = True
        for k, v in _rule_fields(r, name).items():
            el[("rule", a, k)] = v
    for rt in cfg.of_type("aws_route_table"):
        v = id_scalar(cfg, rt, "vpc_id")
        if not (isinstance(v, Ref) and name(v.address) in roles["vpcd"]):
            continue
        n = name(rt.address)
        vpc = cfg.instances.get(v.address)
        cidr = common.parse_cidr(value(vpc, "cidr_block")) if vpc is not None and isinstance(value(vpc, "cidr_block"), str) else None
        got = blocks(rt, "route")
        if isinstance(got, Unresolved) or cidr is None:
            el[("rt", n, "routes inside the VPC CIDR")] = UNRES
        else:
            inner: list[Any] = []
            for r, u in zip(*got):
                dv = field_value(r, u, "cidr_block")
                if isinstance(dv, Unresolved):
                    inner.append(UNRES)  # a route that might be inside the VPC CIDR
                    continue
                dest = common.parse_cidr(dv or "")
                if dest is not None and dest.version == 4 and common.covers([cidr], dest):
                    inner.append(tuple(sorted((k, _norm(field_value(r, u, k), name)) for k in r)))
            el[("rt", n, "routes inside the VPC CIDR")] = frozenset(inner)
        el[("rt", n, "propagating_vgws")] = _norm(value(rt, "propagating_vgws"), name) if written(rt, "propagating_vgws") else ABSENT
    present = cfg.present_types()
    for t in common.RELEVANT_UNSUPPORTED["INV-FUNC-001"]:
        el[("type", t, "present")] = t in present
    ends = {side.endpoints.get("S", ""), side.endpoints.get("D", "")}
    el[("moved", "naming S or D")] = frozenset(
        (f, t) for f, t in cfg.moved if any(x == e or x.startswith(e + "[") for x in (f, t) for e in ends if e))
    return el


def changed(parent_el: dict[tuple, Any], child_el: dict[tuple, Any]) -> list[tuple]:
    """Registry 2.9: created or deleted, different resolved value, or unresolved on either side."""
    out = []
    for k in sorted(set(parent_el) | set(child_el), key=repr):
        if k not in parent_el or k not in child_el:
            out.append(k)
        elif _is_unres(parent_el[k]) or _is_unres(child_el[k]) or parent_el[k] != child_el[k]:
            out.append(k)
    return out


def affected(parent: Side, child: Side, parent_to_child: dict[str, str]) -> dict[str, list[tuple]]:
    """For each invariant, the changed footprint elements between ``parent`` and ``child`` (moves followed)."""
    pname = lambda a: parent_to_child.get(a, a)  # noqa: E731
    cname = lambda a: a  # noqa: E731
    pc, cc = func_context(parent), func_context(child)
    roles = {
        "subnets": {pname(x) for x in [pc["subnet"]] if x} | {x for x in [cc["subnet"]] if x},
        "vpcs": {pname(x) for x in pc["vpcs"]} | set(cc["vpcs"]),
        "sgs": {pname(x) for x in pc["sgs"]} | set(cc["sgs"]),
        "sgd": {pname(x) for x in pc["sgd"]} | set(cc["sgd"]),
        "vpcd": {pname(parent.rs.groups[x].vpc.address) for x in pc["sgd"]
                 if x in parent.rs.groups and isinstance(parent.rs.groups[x].vpc, Ref)}
        | {child.rs.groups[x].vpc.address for x in cc["sgd"] if x in child.rs.groups and isinstance(child.rs.groups[x].vpc, Ref)},
    }
    out = {}
    for inv in ("INV-SEC-001", "INV-SEC-002"):
        out[inv] = changed(sec_elements(parent, inv, pname), sec_elements(child, inv, cname))
    out["INV-SEC-003"] = changed(sec003_elements(parent, pname), sec003_elements(child, cname))
    out["INV-FUNC-001"] = changed(func_elements(parent, pname, roles), func_elements(child, cname, roles))
    return out


_ = func_reach  # the FUNC footprint follows 6.6, which names the 6.3 path
