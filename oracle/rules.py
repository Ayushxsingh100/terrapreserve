"""Registry 2.6: the canonical security-group rule set, inline-rule forms, MIXED, RETAINED-INLINE, pseudo-groups.

For each configured ``aws_security_group`` instance g, ``In(g)`` is g's inline ``ingress`` blocks plus every
``aws_security_group_rule`` with ``type = "ingress"`` whose ``security_group_id`` resolves to a reference to g;
``Out(g)`` is the same for ``egress``. A rule whose ``security_group_id`` is external or unresolved belongs to a
pseudo-group keyed by the literal ID or by ``UNRESOLVED:<rule address>``.

Inline-rule forms (C-84), read from plan JSON (D5-13 gap a): when the configuration writes the argument, an empty
list is *explicit empty* and anything else is *blocks*; when it does not (no expression: not written, or written
only as ``dynamic`` blocks, which plan JSON leaves out of ``configuration``), a known non-empty planned list is
*blocks* (``dynamic``), a known empty list is ``dynamic_empty`` (a case the registry does not name; it is recorded as
an ambiguity), and a null or unknown planned value is *absent*.

Per-block identity references (D5-13 gap b): plan JSON merges the references of all inline blocks of one direction;
a block whose ``security_groups`` is unknown gets the referenced groups only when that is unambiguous: one such
block, one named group, or (D5-22) blocks identical in every other field, so that every assignment yields the same
canonical rule set.

Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oracle import common
from oracle.model import ABSENT, Config, Instance, Literal, Ref, Unresolved, _contains_true, blocks, id_list, \
    id_scalar, identity_refs, value

BLOCKS, EMPTY, ABSENT_FORM, DYNAMIC_EMPTY = "blocks", "explicit empty", "absent", "dynamic_empty"


@dataclass
class Rule:
    address: str
    direction: str | Unresolved  # "ingress" | "egress" | Unresolved
    owner: str  # group key: instance address, "literal:<id>" or "UNRESOLVED:<rule address>"
    inline: bool
    protocol: Any = None  # canonical protocol string or Unresolved
    from_port: Any = None
    to_port: Any = None
    v4: Any = None  # list[str] or Unresolved
    v6: Any = None
    pl: Any = None  # list[str] or Unresolved
    src_sg: Any = None  # list[Ref|Literal] or Unresolved
    self_: Any = False  # bool or Unresolved
    indeterminate_resource: str = ""  # reason when the rule comes from an indeterminate resource or block
    notes: list[str] = field(default_factory=list)

    # -- registry 2.6 "Indeterminate rules" and 2.5 UNSUPPORTED
    def unresolved_parts(self) -> list[str]:
        parts = []
        for name in ("protocol", "from_port", "to_port", "v4", "v6", "pl", "src_sg", "self_"):
            if isinstance(getattr(self, name), Unresolved):
                parts.append(name)
        return parts

    def indeterminate_reasons(self) -> list[str]:
        r = []
        if self.indeterminate_resource:
            r.append(self.indeterminate_resource)
        if isinstance(self.protocol, Unresolved) or isinstance(self.from_port, Unresolved) or isinstance(self.to_port, Unresolved):
            r.append("protocol or ports unresolved")
        for name, label in (("v4", "cidr_blocks"), ("v6", "ipv6_cidr_blocks"), ("pl", "prefix_list_ids"),
                            ("src_sg", "security-group sources"), ("self_", "self")):
            if isinstance(getattr(self, name), Unresolved):
                r.append(f"{label} unresolved")
        if isinstance(self.pl, list) and self.pl:
            r.append("non-empty prefix_list_ids")
        return r

    def determinate(self) -> bool:
        return not self.indeterminate_reasons()

    def unsupported(self) -> str:
        """Registry 2.5: an invalid or host-bit CIDR, or TCP with from_port > to_port, makes the rule UNSUPPORTED."""
        for lst in (self.v4, self.v6):
            if isinstance(lst, list):
                for c in lst:
                    if common.parse_cidr(c) is None:
                        return f"invalid CIDR {c!r}"
        if self.protocol == "TCP" and isinstance(self.from_port, int) and isinstance(self.to_port, int) \
                and self.from_port > self.to_port:
            return "TCP from_port > to_port"
        return ""

    def permits_tcp(self, p: int) -> bool:
        """Registry 2.5 ``permits_tcp(r, p)`` (resolved protocol and ports only)."""
        if self.protocol == "ALL":
            return True
        return self.protocol == "TCP" and isinstance(self.from_port, int) and isinstance(self.to_port, int) \
            and self.from_port <= p <= self.to_port

    def could_permit_tcp(self, p: int) -> bool:
        """Registry 3.3 ``possible``: protocol or ports unresolved, or they permit p."""
        if isinstance(self.protocol, Unresolved):
            return True
        if self.protocol == "ALL":
            return True
        if self.protocol != "TCP":
            return False
        if isinstance(self.from_port, Unresolved) or isinstance(self.to_port, Unresolved):
            return True
        return self.permits_tcp(p)

    def nets(self, which: str) -> list:
        lst = self.v4 if which == "v4" else self.v6
        if not isinstance(lst, list):
            return []
        return [n for n in (common.parse_cidr(c) for c in lst) if n is not None]


@dataclass
class Group:
    key: str
    instance: Instance | None  # None for a pseudo-group
    form: dict[str, str] = field(default_factory=dict)  # direction -> form
    inline: dict[str, list[Rule]] = field(default_factory=dict)
    separate: list[Rule] = field(default_factory=list)  # aws_security_group_rule resources targeting it
    vpc: Any = None  # Ref | Literal | ABSENT | Unresolved
    mixed: bool = False
    retained_inline: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def pseudo(self) -> bool:
        return self.instance is None

    def rules(self, direction: str) -> list[Rule]:
        """In(g) or Out(g). A RETAINED-INLINE direction contributes no known inline rule (2.6, 3.4)."""
        inline = [] if self.retained_inline.get(direction) else self.inline.get(direction, [])
        return inline + [r for r in self.separate if r.direction == direction]

    def type_unresolved_rules(self) -> list[Rule]:
        return [r for r in self.separate if isinstance(r.direction, Unresolved)]


def _str_list(v: Any) -> list[str] | Unresolved:
    if isinstance(v, Unresolved):
        return v
    if v is None or v is ABSENT:
        return []
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return list(v)
    return Unresolved(f"not a list of strings: {v!r}")


def _port(v: Any) -> int | Unresolved:
    if isinstance(v, bool):
        return Unresolved("boolean port")
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v)
    if isinstance(v, Unresolved):
        return v
    return Unresolved(f"port {v!r}")


def _proto(v: Any) -> str | Unresolved:
    if isinstance(v, Unresolved) or v is None or v is ABSENT:
        return v if isinstance(v, Unresolved) else Unresolved("protocol not set")
    return common.canonical_protocol(v)


def _field(block: dict, unk: Any, key: str, where: str) -> Any:
    u = unk.get(key) if isinstance(unk, dict) else unk
    if _contains_true(u):
        return Unresolved(f"{where}.{key} is unknown in the plan")
    return block.get(key)


_SYM_FIELDS = ("protocol", "from_port", "to_port", "cidr_blocks", "ipv6_cidr_blocks", "prefix_list_ids", "self")


def _symmetric(v: list, unk_list: list, idx: list[int], where: str) -> bool:
    """D5-22: the blocks ``idx`` (each with unknown ``security_groups``) are identical in every other canonical field,
    all resolved. With two or more named groups this is exactly when every assignment of the merged references to
    the blocks yields the same canonical rule set (a block that differs could take all groups or only one)."""
    keys = []
    for i in idx:
        bu = unk_list[i] if i < len(unk_list) and isinstance(unk_list[i], dict) else {}
        k = []
        for f in _SYM_FIELDS:
            x = _field(v[i], bu, f, f"{where}[{i}]")
            if isinstance(x, Unresolved):
                return False
            if f in ("cidr_blocks", "ipv6_cidr_blocks", "prefix_list_ids"):
                x = tuple(sorted(x or []))
            elif f == "protocol":
                x = _proto(x)
            elif f in ("from_port", "to_port"):
                x = _port(x)
            elif f == "self":
                x = bool(x)
            if isinstance(x, Unresolved):
                return False
            k.append(x)
        keys.append(tuple(k))
    return len(set(keys)) == 1


def inline_form(inst: Instance, direction: str) -> str:
    """The C-84 form of one direction of a configured group (D5-13 gap a)."""
    v = value(inst, direction)
    if direction in inst.expressions:
        expr = inst.expressions[direction]
        if isinstance(expr, dict) and expr.get("constant_value") == []:
            return EMPTY
        if isinstance(v, list) and not v:
            return EMPTY
        return BLOCKS
    if isinstance(v, list):
        return BLOCKS if v else DYNAMIC_EMPTY
    return ABSENT_FORM


def inline_rules(config: Config, inst: Instance, direction: str) -> tuple[list[Rule], list[str]]:
    """The canonical rules of one direction's inline blocks, and notes (D5-13 gap b)."""
    notes: list[str] = []
    got = blocks(inst, direction)  # per element: one unknown field does not make the other blocks unknown
    where = f"{inst.address}.{direction}"
    if isinstance(got, Unresolved):
        # Written but its contents are unknown in the plan: one fully unresolved rule (indeterminate block, 2.3).
        u = Unresolved(f"{where} contents unknown in the plan")
        return [Rule(address=f"{where}[?]", direction=direction, owner=inst.address, inline=True, protocol=u,
                     from_port=u, to_port=u, v4=u, v6=u, pl=u, src_sg=u, self_=u,
                     indeterminate_resource="inline block contents unknown in the plan")], notes
    v, unk_list = got
    refs = ((inst.expressions.get(direction) or {}) if isinstance(inst.expressions.get(direction), dict) else {}).get(
        "references") or []
    sg_refs = identity_refs(config, inst, refs) if refs else Unresolved("no references")
    sg_refs = [a for a in sg_refs if config.instances[a].type == "aws_security_group"] \
        if isinstance(sg_refs, list) else []
    unknown_sg_blocks = [i for i, b in enumerate(v)
                         if _contains_true((unk_list[i] if i < len(unk_list) else {}).get("security_groups")
                                           if isinstance(unk_list[i] if i < len(unk_list) else {}, dict) else False)]
    symmetric = bool(sg_refs) and len(unknown_sg_blocks) > 1 and len(sg_refs) > 1 \
        and _symmetric(v, unk_list, unknown_sg_blocks, where)
    if symmetric:
        notes.append(f"{where}: {len(unknown_sg_blocks)} blocks with merged security_groups references are identical "
                     f"apart from them; every assignment gives the same rule set (D5-22)")
    out: list[Rule] = []
    for i, block in enumerate(v):
        bu = unk_list[i] if i < len(unk_list) and isinstance(unk_list[i], dict) else {}
        w = f"{where}[{i}]"
        if i in unknown_sg_blocks:
            if sg_refs and (len(unknown_sg_blocks) == 1 or len(sg_refs) == 1 or symmetric):
                # One block, one group, or identical blocks (D5-22): giving every such block every named group is
                # one of the possible assignments and yields the rule set every assignment yields.
                src: Any = [Ref(a) for a in sg_refs]
            else:
                src = Unresolved(f"{w}.security_groups: plan JSON merges the references of {len(unknown_sg_blocks)} "
                                 f"blocks and names {len(sg_refs)} groups (D5-13 gap b)")
                notes.append(src.reason)
        else:
            s = _field(block, bu, "security_groups", w)
            src = [Literal(x) for x in s] if isinstance(s, list) else ([] if s is None else s)
        out.append(Rule(
            address=w, direction=direction, owner=inst.address, inline=True,
            protocol=_proto(_field(block, bu, "protocol", w)), from_port=_port(_field(block, bu, "from_port", w)),
            to_port=_port(_field(block, bu, "to_port", w)), v4=_str_list(_field(block, bu, "cidr_blocks", w)),
            v6=_str_list(_field(block, bu, "ipv6_cidr_blocks", w)), pl=_str_list(_field(block, bu, "prefix_list_ids", w)),
            src_sg=src, self_=_field(block, bu, "self", w) or False))
    return out, notes


def separate_rule(config: Config, inst: Instance) -> Rule:
    t = value(inst, "type")
    direction: str | Unresolved = t if t in ("ingress", "egress") else (
        t if isinstance(t, Unresolved) else Unresolved(f"{inst.address}.type is {t!r}"))
    target = id_scalar(config, inst, "security_group_id")
    if isinstance(target, Ref) and config.instances[target.address].type == "aws_security_group":
        owner = target.address
    elif isinstance(target, Literal):
        owner = f"literal:{target.value}"
    else:
        owner = f"UNRESOLVED:{inst.address}"
    src = id_scalar(config, inst, "source_security_group_id")
    src_sg: Any = [] if src is ABSENT else ([src] if isinstance(src, (Ref, Literal)) else src)
    self_v = value(inst, "self")
    return Rule(address=inst.address, direction=direction, owner=owner, inline=False,
                protocol=_proto(value(inst, "protocol")), from_port=_port(value(inst, "from_port")),
                to_port=_port(value(inst, "to_port")), v4=_str_list(value(inst, "cidr_blocks")),
                v6=_str_list(value(inst, "ipv6_cidr_blocks")), pl=_str_list(value(inst, "prefix_list_ids")),
                src_sg=src_sg, self_=False if self_v in (None, ABSENT) else self_v)


@dataclass
class RuleSet:
    groups: dict[str, Group]
    rules: list[Rule]
    notes: list[str]
    ambiguities: list[str]

    def group_of(self, key: str) -> Group | None:
        return self.groups.get(key)


def build(config: Config, parent: Config | None, parent_map: dict[str, str] | None) -> RuleSet:
    """The canonical rule set of ``config``; ``parent`` (with the parent -> child address map) for C-84."""
    groups: dict[str, Group] = {}
    notes: list[str] = []
    ambiguities: list[str] = []
    child_to_parent = {c: p for p, c in (parent_map or {}).items()}
    for inst in config.of_type("aws_security_group"):
        g = Group(key=inst.address, instance=inst, vpc=id_scalar(config, inst, "vpc_id"))
        for d in ("ingress", "egress"):
            g.form[d] = inline_form(inst, d)
            if g.form[d] == DYNAMIC_EMPTY:
                ambiguities.append(f"{inst.address}.{d}: dynamic blocks that expand to none (no registry 2.6 form)")
            rs, ns = inline_rules(config, inst, d) if g.form[d] == BLOCKS else ([], [])
            g.inline[d] = rs
            notes.extend(ns)
            g.retained_inline[d] = False
            if g.form[d] == ABSENT_FORM and parent is not None:
                pa = child_to_parent.get(inst.address)
                pinst = parent.instances.get(pa) if pa else None
                if pinst is not None and pinst.type == "aws_security_group" and inline_form(pinst, d) == BLOCKS:
                    g.retained_inline[d] = True
        groups[g.key] = g
    rules: list[Rule] = []
    for inst in config.of_type("aws_security_group_rule"):
        r = separate_rule(config, inst)
        rules.append(r)
        if r.owner not in groups:
            groups[r.owner] = Group(key=r.owner, instance=None)
        groups[r.owner].separate.append(r)
        if isinstance(r.direction, Unresolved):
            ambiguities.append(f"{inst.address}: rule type unresolved (registry 2.6 In/Out membership not defined)")
    for g in groups.values():
        rules.extend(x for d in ("ingress", "egress") for x in g.inline.get(d, []))
        if g.pseudo:
            continue
        has_blocks = any(g.form.get(d) == BLOCKS for d in ("ingress", "egress"))
        targeted = bool(g.separate)
        if has_blocks and targeted:
            g.mixed = True
        for d in ("ingress", "egress"):
            if g.form.get(d) == EMPTY and any(r.direction == d for r in g.separate):
                g.mixed = True
    return RuleSet(groups=groups, rules=rules, notes=notes, ambiguities=ambiguities)
