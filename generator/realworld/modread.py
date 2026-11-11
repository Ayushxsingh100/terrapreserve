"""Whole-module reader for security groups, their rules and database instances (D4b-15).

Registry v1.0 C-64: "every security group is in scope, attached or not". The round-5 S0 screen
and the round-5 tests therefore read the WHOLE module (verbatim host files and the graft together),
not only the graft. This module is that reader. It is a generator self-check written from the
quoted registry text (sections 2.6, 2.7, 3.3, 3.4 and C-64). It is NOT the oracle, it is not a label,
and it shares no code with DAIL. Standard library plus ``sources/hcl_lex.py`` only.

What it resolves (a value that does not resolve is "unresolved"):

* literals: strings without interpolation, integers, ``true``/``false``/``null``, lists and objects of these;
* ``var.<name>`` when the variable has a ``default`` that resolves; ``local.<name>`` that resolves;
* ``aws_security_group.<name>.id`` (a reference to a configured group, indexes allowed);
* ``aws_vpc.<name>.cidr_block`` and ``aws_subnet.<name>.cidr_block`` when the block has a resolvable ``cidr_block``;
* ``dynamic`` blocks whose ``for_each`` resolves.

Unresolved values follow the registry's own indeterminacy rules, not a blanket rejection (round 5):

* SEC-001/002, registry 3.3 and 3.4: ``possible4(g)`` / ``possible6(g)`` hold when an indeterminate rule of
  group ``g`` (configured, or the per-rule pseudo-group ``UNRESOLVED:<rule address>`` of a rule whose
  ``security_group_id`` is unresolved) could permit TCP/p and has unresolved sources or a prefix list. A rule
  whose type is unresolved counts as a possible ingress rule. Any such group makes the result UNKNOWN.
* SEC-003, registry 5.4: an unresolved ``publicly_accessible`` makes the result UNKNOWN.
* FUNC-001, registry 6.4 row 7: an indeterminate rule that could permit TCP/5432 in SG(S), SG(D) or a
  pseudo-group makes the result UNKNOWN.

An unresolved value that cannot affect any of the four results is recorded in ``Analysis.ignored`` and never
rejects a module. Existence of ``count``/``for_each`` expanded resources is assumed (a violation is counted
as if the resource were created).
"""

from __future__ import annotations

import ipaddress
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))

import hcl_lex  # noqa: E402
from hcl_lex import Token  # noqa: E402

# Registry section 2.7: relevant-unsupported types (presence anywhere in the configuration).
UNSUPPORTED_SEC = (
    "aws_vpc_security_group_ingress_rule",
    "aws_default_security_group",
    "aws_vpc_security_group_rules_exclusive",
)
UNSUPPORTED_FUNC = (
    "aws_vpc_security_group_ingress_rule",
    "aws_vpc_security_group_egress_rule",
    "aws_default_security_group",
    "aws_network_interface",
    "aws_network_interface_attachment",
    "aws_network_interface_sg_attachment",
    "aws_network_acl",
    "aws_network_acl_rule",
    "aws_network_acl_association",
    "aws_default_network_acl",
    "aws_route",
    "aws_default_route_table",
    "aws_main_route_table_association",
    "aws_vpc_ipv4_cidr_block_association",
    "aws_vpc_peering_connection",
    "aws_ec2_transit_gateway_vpc_attachment",
    "aws_vpc_endpoint",
    "aws_vpc_security_group_rules_exclusive",
    "aws_vpc_security_group_vpc_association",
    "aws_vpn_gateway_route_propagation",
    "aws_vpc_route_server_propagation",
    "aws_default_subnet",
    "aws_default_vpc",
    "aws_vpc_peering_connection_accepter",
    "aws_vpc_peering_connection_options",
    "aws_ec2_transit_gateway_vpc_attachment_accepter",
)
RELEVANT_UNSUPPORTED = tuple(sorted(set(UNSUPPORTED_SEC) | set(UNSUPPORTED_FUNC)))


class Unresolved(Exception):
    """A value the reader cannot resolve to a literal or a configured-group reference."""


@dataclass(frozen=True)
class GroupRef:
    addr: str  # aws_security_group.<name>


@dataclass
class Block:
    kind: str
    labels: list[str]
    attrs: dict[str, list[Token]] = field(default_factory=dict)
    children: list["Block"] = field(default_factory=list)
    line: int = 0

    @property
    def addr(self) -> str:
        return ".".join(self.labels[:2]) if self.kind == "resource" else ".".join([self.kind, *self.labels])


# ---------------------------------------------------------------------------
# Structural parser over hcl_lex tokens
# ---------------------------------------------------------------------------


def _label(tok: Token) -> str | None:
    if tok.kind == "STRING":
        return tok.text
    if tok.kind == "IDENT":
        return tok.text
    return None


def _parse_body(toks: list[Token], i: int, top: bool) -> tuple[dict[str, list[Token]], list[Block], int]:
    attrs: dict[str, list[Token]] = {}
    children: list[Block] = []
    n = len(toks)
    while i < n:
        t = toks[i]
        if t.kind == "NEWLINE" or (t.kind == "PUNCT" and t.text in (",", ";")):
            i += 1
            continue
        if t.kind == "PUNCT" and t.text == "}":
            return attrs, children, i + 1
        if t.kind != "IDENT":
            i += 1
            continue
        nxt = toks[i + 1] if i + 1 < n else None
        if nxt is not None and nxt.kind == "PUNCT" and nxt.text == "=":
            j = i + 2
            expr: list[Token] = []
            depth = 0
            while j < n:
                u = toks[j]
                if u.kind == "NEWLINE" and depth == 0:
                    break
                if u.kind == "PUNCT" and u.text in "([{":
                    depth += 1
                elif u.kind == "PUNCT" and u.text in ")]}":
                    if depth == 0:
                        break
                    depth -= 1
                if u.kind != "NEWLINE" or depth > 0:
                    expr.append(u)
                j += 1
            attrs[t.text] = expr
            i = j
            continue
        labels: list[str] = []
        j = i + 1
        while j < n and (lab := _label(toks[j])) is not None:
            labels.append(lab)
            j += 1
        if j < n and toks[j].kind == "PUNCT" and toks[j].text == "{":
            a, c, j2 = _parse_body(toks, j + 1, False)
            children.append(Block(t.text, labels, a, c, t.line))
            i = j2
            continue
        i = j if j > i else i + 1
    return attrs, children, i


def parse_blocks(text: str) -> list[Block]:
    toks = hcl_lex.tokenize(text)
    _attrs, blocks, _i = _parse_body(toks, 0, True)
    return blocks


# ---------------------------------------------------------------------------
# Module and expression evaluation
# ---------------------------------------------------------------------------


@dataclass
class Module:
    blocks: list[Block]
    resources: dict[str, Block]
    variables: dict[str, Block]
    locals: dict[str, list[Token]]


def read_module(files: dict[str, str]) -> Module:
    blocks: list[Block] = []
    for name in sorted(files):
        if name.endswith(".tf"):
            blocks.extend(parse_blocks(files[name]))
    resources: dict[str, Block] = {}
    variables: dict[str, Block] = {}
    locs: dict[str, list[Token]] = {}
    for b in blocks:
        if b.kind == "resource" and len(b.labels) == 2:
            resources[b.addr] = b
        elif b.kind == "variable" and b.labels:
            variables[b.labels[0]] = b
        elif b.kind == "locals":
            locs.update(b.attrs)
    return Module(blocks, resources, variables, locs)


def _match_close(toks: list[Token], i: int) -> int:
    depth = 0
    for j in range(i, len(toks)):
        if toks[j].kind == "PUNCT" and toks[j].text in "([{":
            depth += 1
        elif toks[j].kind == "PUNCT" and toks[j].text in ")]}":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _split_commas(toks: list[Token]) -> list[list[Token]]:
    out: list[list[Token]] = []
    cur: list[Token] = []
    depth = 0
    for t in toks:
        if t.kind == "PUNCT" and t.text in "([{":
            depth += 1
        elif t.kind == "PUNCT" and t.text in ")]}":
            depth -= 1
        if t.kind == "PUNCT" and t.text == "," and depth == 0:
            out.append(cur)
            cur = []
            continue
        cur.append(t)
    if cur:
        out.append(cur)
    return out


def _traversal(toks: list[Token]) -> list[str] | None:
    """IDENT ('.' IDENT | '[' NUMBER|STRING ']')* as a list of parts (indexes kept as ``[x]``), or None."""
    parts: list[str] = []
    n = len(toks)
    if n == 0 or toks[0].kind != "IDENT":
        return None
    parts.append(toks[0].text)
    i = 1
    while i < n:
        t = toks[i]
        if t.kind == "PUNCT" and t.text == "." and i + 1 < n and toks[i + 1].kind in ("IDENT", "NUMBER"):
            parts.append(toks[i + 1].text)
            i += 2
        elif t.kind == "PUNCT" and t.text == "[" and i + 2 < n and toks[i + 1].kind in ("NUMBER", "STRING") \
                and toks[i + 2].kind == "PUNCT" and toks[i + 2].text == "]":
            parts.append(f"[{toks[i + 1].text}]")
            i += 3
        else:
            return None
    return parts


def _object_entries(inner: list[Token]) -> list[tuple[str, list[Token]]]:
    """Entries of an object literal body (NEWLINE and comma separate entries at depth 0)."""
    entries: list[tuple[str, list[Token]]] = []
    cur: list[Token] = []
    depth = 0

    def flush() -> None:
        nonlocal cur
        body = [t for t in cur if t.kind != "NEWLINE"]
        cur = []
        if not body:
            return
        if len(body) < 3 or body[0].kind not in ("IDENT", "STRING") or body[1].kind != "PUNCT" \
                or body[1].text not in ("=", ":"):
            raise Unresolved("object entry")
        entries.append((body[0].text, body[2:]))

    for t in inner:
        if t.kind == "PUNCT" and t.text in "([{":
            depth += 1
        elif t.kind == "PUNCT" and t.text in ")]}":
            depth -= 1
        if depth == 0 and (t.kind == "NEWLINE" or (t.kind == "PUNCT" and t.text == ",")):
            flush()
            continue
        cur.append(t)
    flush()
    return entries


def _walk(value: Any, path: list[str]) -> Any:
    for p in path:
        if p.startswith("["):
            key: Any = p[1:-1]
            if isinstance(value, list):
                if not key.isdigit() or int(key) >= len(value):
                    raise Unresolved("index")
                value = value[int(key)]
                continue
            if isinstance(value, dict) and key in value:
                value = value[key]
                continue
            raise Unresolved("index")
        if isinstance(value, dict) and p in value:
            value = value[p]
        else:
            raise Unresolved(f"attribute {p}")
    return value


def evaluate(toks: list[Token], mod: Module, depth: int = 0, env: dict[str, Any] | None = None) -> Any:
    """Evaluate a token list to str, int, bool, None, list, dict or GroupRef; raise Unresolved otherwise.

    ``env`` binds ``dynamic`` block iterators: name -> {"key": ..., "value": ...}.
    """
    if depth > 8:
        raise Unresolved("reference chain too deep")
    raw = toks
    toks = [t for t in toks if t.kind != "NEWLINE"]
    if not toks:
        raise Unresolved("empty expression")
    if len(toks) == 1:
        t = toks[0]
        if t.kind == "STRING":
            if "${" in t.text or "%{" in t.text:
                inner = t.text
                if inner.startswith("${") and inner.endswith("}") and inner.count("${") == 1:
                    sub = hcl_lex.tokenize(inner[2:-1])
                    return evaluate(sub, mod, depth + 1, env)
                raise Unresolved("interpolated string")
            return t.text
        if t.kind == "NUMBER":
            if t.text.isdigit():
                return int(t.text)
            raise Unresolved("non-integer number")
        if t.kind == "IDENT" and t.text in ("true", "false"):
            return t.text == "true"
        if t.kind == "IDENT" and t.text == "null":
            return None
    if len(toks) == 2 and toks[0].kind == "PUNCT" and toks[0].text == "-" and toks[1].kind == "NUMBER" \
            and toks[1].text.isdigit():
        return -int(toks[1].text)
    if toks[0].kind == "PUNCT" and toks[0].text == "[" and _match_close(toks, 0) == len(toks) - 1:
        idx = [i for i, t in enumerate(raw) if t.kind != "NEWLINE"]
        inner = raw[idx[0] + 1:idx[-1]]  # raw keeps the NEWLINE separators of nested objects
        first = next((t for t in inner if t.kind != "NEWLINE"), None)
        if first is not None and first.kind == "IDENT" and first.text == "for":
            raise Unresolved("for expression")
        return [evaluate(part, mod, depth + 1, env) for part in _split_commas(inner)
                if any(t.kind != "NEWLINE" for t in part)]
    if toks[0].kind == "PUNCT" and toks[0].text == "{" and _match_close(toks, 0) == len(toks) - 1:
        # the raw token list keeps the NEWLINE separators inside the braces
        idx = [i for i, t in enumerate(raw) if t.kind != "NEWLINE"]
        inner_raw = raw[idx[0] + 1:idx[-1]]
        first = next((t for t in inner_raw if t.kind != "NEWLINE"), None)
        if first is not None and first.kind == "IDENT" and first.text == "for":
            raise Unresolved("for expression")
        return {k: evaluate(v, mod, depth + 1, env) for k, v in _object_entries(inner_raw)}
    parts = _traversal(toks)
    if parts is not None:
        root = parts[0]
        if env and root in env:
            return _walk(env[root], parts[1:])
        if root == "var" and len(parts) >= 2:
            v = mod.variables.get(parts[1])
            if v is None or "default" not in v.attrs:
                raise Unresolved(f"var.{parts[1]} has no default")
            return _walk(evaluate(v.attrs["default"], mod, depth + 1), parts[2:])
        if root == "local" and len(parts) >= 2:
            if parts[1] not in mod.locals:
                raise Unresolved(f"local.{parts[1]} not found")
            return _walk(evaluate(mod.locals[parts[1]], mod, depth + 1), parts[2:])
        if root == "aws_security_group" and len(parts) >= 3:
            idx = 2 if not parts[2].startswith("[") else 3
            if len(parts) == idx + 1 and parts[idx] in ("id", "name", "arn"):
                addr = f"aws_security_group.{parts[1]}"
                if addr in mod.resources:
                    return GroupRef(addr)
                raise Unresolved(f"reference to unconfigured group {addr}")
        if root in ("aws_vpc", "aws_subnet") and len(parts) == 3 and parts[2] == "cidr_block":
            blk = mod.resources.get(f"{root}.{parts[1]}")
            if blk is not None and "cidr_block" in blk.attrs:
                return evaluate(blk.attrs["cidr_block"], mod, depth + 1)
        raise Unresolved(f"reference {'.'.join(parts)[:60]}")
    raise Unresolved("expression")


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SgRule:
    holder: str  # address of the holder (group for inline, rule resource otherwise)
    group: str  # configured group address, or "UNRESOLVED:<rule address>" (registry 3.3, pseudo-group)
    direction: str  # ingress | egress | ? (type unresolved: counts as a possible ingress rule)
    form: str  # "block" or "rule"
    protocol: str | None
    from_port: int | None
    to_port: int | None
    v4: tuple[str, ...]
    v6: tuple[str, ...]
    sources: tuple[str, ...]  # group addresses or literal ids
    self_flag: bool
    unres: tuple[str, ...] = ()  # subset of: type protocol ports v4 v6 prefix source

    @property
    def indeterminate(self) -> bool:
        return bool(self.unres)

    @property
    def possible_ingress(self) -> bool:
        return self.direction in ("ingress", "?")

    def permits_tcp(self, port: int) -> bool:
        """Determinate: protocol and ports are resolved and permit ``port``."""
        if self.protocol is None:
            return False
        if self.protocol in ("-1", "all"):
            return True
        if self.protocol in ("tcp", "6") and self.from_port is not None and self.to_port is not None:
            return self.from_port <= port <= self.to_port
        return False

    def could_permit_tcp(self, port: int) -> bool:
        """Registry 3.3: its protocol or ports are unresolved, or they permit ``port``."""
        if self.protocol is None:
            return True
        if self.protocol in ("-1", "all"):
            return True
        if self.protocol in ("tcp", "6"):
            if self.from_port is None or self.to_port is None:
                return True
            return self.from_port <= port <= self.to_port
        return False

    def world_cidr(self) -> bool:
        """A resolved source of this rule is ``0.0.0.0/0`` or ``::/0``."""
        return "0.0.0.0/0" in self.v4 or "::/0" in self.v6

    @property
    def v4_open(self) -> bool:
        """IPv4 sources unresolved or include a prefix list (registry 3.3)."""
        return "v4" in self.unres or "prefix" in self.unres

    @property
    def v6_open(self) -> bool:
        return "v6" in self.unres or "prefix" in self.unres


def _as_list(v: Any) -> list[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    raise Unresolved("expected a list")


_RULE_FIELDS = ("prefix_list_ids", "protocol", "from_port", "to_port", "cidr_blocks", "ipv6_cidr_blocks",
                "source_security_group_id", "security_groups", "self")
_UNSET = object()


def _make_rule(holder: str, group: str, direction: str, form: str, attrs: dict[str, list[Token]],
               mod: Module, env: dict[str, Any] | None = None, extra_unres: tuple[str, ...] = ()) -> SgRule:
    values: dict[str, Any] = {}
    for name, toks in attrs.items():
        if name in _RULE_FIELDS:
            try:
                values[name] = evaluate(toks, mod, env=env)
            except Unresolved:
                values[name] = _UNSET
    return _rule_from_values(holder, group, direction, form, values, extra_unres)


def _rule_from_values(holder: str, group: str, direction: str, form: str, values: dict[str, Any],
                      extra_unres: tuple[str, ...] = ()) -> SgRule:
    """Build a rule, recording which of its fields do not resolve (``_UNSET`` marks an unresolved value)."""
    unres: set[str] = set(extra_unres)

    def get(name: str) -> Any:
        v = values.get(name)
        return v

    proto = get("protocol")
    if isinstance(proto, int) and not isinstance(proto, bool):
        proto = str(proto)
    if isinstance(proto, str):
        proto = proto.lower()
    else:
        proto = None
        unres.add("protocol")
    ports: list[int | None] = []
    for name in ("from_port", "to_port"):
        v = get(name)
        if isinstance(v, str) and re.fullmatch(r"-?\d+", v):  # Terraform converts "22" to 22
            v = int(v)
        if isinstance(v, bool) or not isinstance(v, int):
            ports.append(None)
            unres.add("ports")
        else:
            ports.append(v)
    cidrs: dict[str, tuple[str, ...]] = {}
    for label, key in (("cidr_blocks", "v4"), ("ipv6_cidr_blocks", "v6")):
        cidrs[key] = ()
        if label not in values:
            continue
        v = values[label]
        if v is _UNSET:
            unres.add(key)
            continue
        try:
            items = _as_list(v)
            for c in items:
                if not isinstance(c, str):
                    raise Unresolved("element")
                ipaddress.ip_network(c, strict=False)
            cidrs[key] = tuple(sorted(items))
        except (Unresolved, ValueError):
            unres.add(key)
    pl = values.get("prefix_list_ids", [])
    if pl is _UNSET or (isinstance(pl, list) and pl) or not isinstance(pl, (list, type(None))):
        unres.add("prefix")
    srcs: list[str] = []
    raw_srcs: list[Any] = []
    for key in ("source_security_group_id", "security_groups"):
        if key not in values:
            continue
        v = values[key]
        if v is _UNSET:
            unres.add("source")
        elif key == "security_groups":
            try:
                raw_srcs.extend(_as_list(v))
            except Unresolved:
                unres.add("source")
        else:
            raw_srcs.append(v)
    for sg in raw_srcs:
        if isinstance(sg, GroupRef):
            srcs.append(sg.addr)
        elif isinstance(sg, str):
            srcs.append(sg)
        elif sg is not None:
            unres.add("source")
    self_flag = values.get("self") in (True, "true")
    return SgRule(holder, group, direction, form, proto, ports[0], ports[1], cidrs["v4"], cidrs["v6"],
                  tuple(sorted(srcs)), self_flag, tuple(sorted(unres)))


def _fully_unresolved(holder: str, group: str, direction: str, form: str) -> SgRule:
    return SgRule(holder, group, direction, form, None, None, None, (), (), (), False,
                  ("protocol", "ports", "v4", "v6", "prefix", "source"))


@dataclass
class GroupForms:
    ingress: str = "absent"  # blocks | empty | absent
    egress: str = "absent"
    rule_targets: set[str] = field(default_factory=set)  # directions targeted by rule resources


@dataclass
class Analysis:
    rules: list[SgRule] = field(default_factory=list)
    groups: dict[str, GroupForms] = field(default_factory=dict)
    violations: dict[str, list[str]] = field(default_factory=dict)  # determinate violations, invariant -> where
    possible: dict[str, list[str]] = field(default_factory=dict)  # registry 3.3/3.4 possible(g) -> UNKNOWN
    unresolved_public: list[str] = field(default_factory=list)  # registry 5.4: unresolved publicly_accessible
    func_unknown: list[str] = field(default_factory=list)  # registry 6.4 row 7, pseudo-group rules
    unsupported_types: list[str] = field(default_factory=list)  # addresses
    mixed: list[str] = field(default_factory=list)
    unsupported_rules: list[str] = field(default_factory=list)  # registry 2.5: TCP with from_port > to_port
    ignored: list[str] = field(default_factory=list)  # unresolved values that cannot affect any of the four results
    db_instances: list[str] = field(default_factory=list)

    @property
    def undecidable(self) -> list[str]:
        """Registry indeterminacy that can change a result of INV-SEC-001/002/003 or INV-FUNC-001."""
        out = []
        for inv, wheres in sorted(self.possible.items()):
            out += [f"{inv} possible (UNKNOWN) for {w}" for w in wheres]
        out += self.unresolved_public
        out += self.func_unknown
        return out

    @property
    def codes(self) -> list[str]:
        """Exclusion codes triggered, in the fixed priority order of the screen."""
        out = []
        if self.unsupported_types:
            out.append("RW-S0-UNSUP-TYPE")
        if self.mixed:
            out.append("RW-S0-MIXED")
        if self.unsupported_rules:
            out.append("RW-S0-UNSUP-RULE")
        for inv, code in (("INV-SEC-001", "RW-S0-SEC-001"), ("INV-SEC-002", "RW-S0-SEC-002"),
                          ("INV-SEC-003", "RW-S0-SEC-003")):
            if self.violations.get(inv):
                out.append(code)
        if self.undecidable:
            out.append("RW-S0-UNDECIDABLE")
        return out

    def indeterminate_5432(self, sg_of_endpoints: set[str]) -> list[str]:
        """Registry 6.4 row 7: indeterminate rules that could permit TCP/5432 in SG(S), SG(D) or a pseudo-group."""
        return [r.holder for r in self.rules
                if r.indeterminate and r.could_permit_tcp(5432)
                and (r.group in sg_of_endpoints or r.group.startswith("UNRESOLVED:"))]


def _covers_world(cidrs: list[str], v6: bool) -> bool:
    nets = [ipaddress.ip_network(c, strict=False) for c in cidrs]
    nets = [n for n in nets if (n.version == 6) == v6]
    if not nets:
        return False
    return any(n.prefixlen == 0 for n in ipaddress.collapse_addresses(nets))


def _count_zero(blk: Block, mod: Module) -> bool:
    if "count" not in blk.attrs:
        return False
    try:
        return evaluate(blk.attrs["count"], mod) == 0
    except Unresolved:
        return False


def _expand_dynamic(an: "Analysis", mod: Module, addr: str, direction: str, di: int, dblk: Block) -> None:
    """Expand a ``dynamic`` ingress or egress block whose ``for_each`` resolves; else one indeterminate rule."""
    holder = f"{addr}#dynamic-{direction}[{di}]"
    try:
        if "for_each" not in dblk.attrs:
            raise Unresolved("dynamic block without for_each")
        fe = evaluate(dblk.attrs["for_each"], mod)
        content = next((c for c in dblk.children if c.kind == "content"), None)
        if content is None:
            raise Unresolved("dynamic block without content")
        iterator = dblk.labels[0]
        if "iterator" in dblk.attrs:
            toks = [t for t in dblk.attrs["iterator"] if t.kind != "NEWLINE"]
            if len(toks) != 1 or toks[0].kind != "IDENT":
                raise Unresolved("iterator")
            iterator = toks[0].text
        if isinstance(fe, dict):
            items = list(fe.items())
        elif isinstance(fe, list):
            items = list(enumerate(fe))
        else:
            raise Unresolved("for_each is not a list or map")
        for idx, (k, v) in enumerate(items):
            env = {iterator: {"key": k, "value": v}}
            an.rules.append(_make_rule(f"{holder}[{idx}]", addr, direction, "block", content.attrs, mod, env))
    except Unresolved:
        an.rules.append(_fully_unresolved(holder, addr, direction, "block"))


def analyse(files: dict[str, str]) -> Analysis:
    """Read every ``.tf`` file of one step and apply the registry's whole-module rules.

    Determinate violations follow registry C-64. Indeterminate rules follow registry 3.3 and 3.4
    (``possible4``/``possible6`` over every configured group and every pseudo-group), 5.4 (unresolved
    ``publicly_accessible``) and 6.4 row 7 (indeterminate rules in a pseudo-group that could permit TCP/5432).
    An unresolved value that cannot affect any of these is listed in ``ignored``, never a rejection.
    """
    mod = read_module(files)
    an = Analysis()

    for addr, blk in sorted(mod.resources.items()):
        if blk.labels[0] in RELEVANT_UNSUPPORTED:
            an.unsupported_types.append(addr)

    for addr, blk in sorted(mod.resources.items()):
        rtype = blk.labels[0]
        if _count_zero(blk, mod):
            continue
        if rtype == "aws_security_group":
            gf = an.groups.setdefault(addr, GroupForms())
            for direction in ("ingress", "egress"):
                kids = [c for c in blk.children if c.kind == direction]
                dyn = [c for c in blk.children if c.kind == "dynamic" and c.labels[:1] == [direction]]
                has_attr = direction in blk.attrs
                if dyn:
                    setattr(gf, direction, "blocks")
                    for di, dblk in enumerate(dyn):
                        _expand_dynamic(an, mod, addr, direction, di, dblk)
                if has_attr:
                    holder = f"{addr}#{direction}"
                    try:
                        val = evaluate(blk.attrs[direction], mod)
                    except Unresolved:
                        setattr(gf, direction, "blocks")
                        an.rules.append(_fully_unresolved(holder, addr, direction, "block"))
                        continue
                    if val == []:
                        setattr(gf, direction, "empty")
                        continue
                    setattr(gf, direction, "blocks")
                    if not isinstance(val, list) or not all(isinstance(o, dict) for o in val):
                        an.rules.append(_fully_unresolved(holder, addr, direction, "block"))
                        continue
                    for oi, obj in enumerate(val):
                        an.rules.append(_rule_from_values(f"{holder}[{oi}]", addr, direction, "block", obj))
                    continue
                if kids:
                    setattr(gf, direction, "blocks")
                for idx, kid in enumerate(kids):
                    an.rules.append(_make_rule(f"{addr}#{direction}[{idx}]", addr, direction, "block",
                                               kid.attrs, mod))
        elif rtype == "aws_security_group_rule":
            extra: tuple[str, ...] = ()
            d = "?"
            if "type" in blk.attrs:
                try:
                    v = evaluate(blk.attrs["type"], mod)
                    if v in ("ingress", "egress"):
                        d = v
                except Unresolved:
                    pass
            if d == "?":
                extra = ("type",)
            group_key = f"UNRESOLVED:{addr}"
            if "security_group_id" in blk.attrs:
                try:
                    g = evaluate(blk.attrs["security_group_id"], mod)
                    if isinstance(g, GroupRef):
                        group_key = g.addr
                except Unresolved:
                    pass
            if not group_key.startswith("UNRESOLVED:") and d in ("ingress", "egress"):
                an.groups.setdefault(group_key, GroupForms()).rule_targets.add(d)
            an.rules.append(_make_rule(addr, group_key, d, "rule", blk.attrs, mod, None, extra))
        elif rtype == "aws_db_instance":
            an.db_instances.append(addr)
            if "publicly_accessible" in blk.attrs:
                try:
                    v = evaluate(blk.attrs["publicly_accessible"], mod)
                except Unresolved as exc:
                    an.unresolved_public.append(f"{addr}: publicly_accessible unresolved ({exc})")
                    continue
                if v is True:
                    an.violations.setdefault("INV-SEC-003", []).append(addr)
                elif v is not False and v is not None:
                    if v in ("true", "false"):  # Terraform converts the string to a bool
                        if v == "true":
                            an.violations.setdefault("INV-SEC-003", []).append(addr)
                    else:
                        an.unresolved_public.append(f"{addr}: publicly_accessible is not a boolean")

    # MIXED groups (registry 2.6, C-84): at least one inline rule block, ingress or egress, and the target of at
    # least one aws_security_group_rule in any direction (D4c-05; before D4c only the same direction was checked);
    # an explicit empty list in a direction that a rule resource also targets is MIXED too.
    for key, gf in an.groups.items():
        has_blocks = "blocks" in (gf.ingress, gf.egress)
        same_dir_empty = any(d in gf.rule_targets and getattr(gf, d) == "empty" for d in ("ingress", "egress"))
        if (has_blocks and gf.rule_targets) or same_dir_empty:
            if key not in an.mixed:
                an.mixed.append(key)

    # Registry 2.5: for TCP, from_port > to_port makes the rule UNSUPPORTED (D4c-05).
    for r in an.rules:
        if r.protocol in ("tcp", "6") and r.from_port is not None and r.to_port is not None \
                and r.from_port > r.to_port:
            an.unsupported_rules.append(f"{r.holder}: TCP from_port {r.from_port} > to_port {r.to_port}")

    # public ingress per group, alone or together (C-64); possible(g) per registry 3.3 and 3.4
    by_group: dict[str, list[SgRule]] = {}
    for r in an.rules:
        if r.possible_ingress:
            by_group.setdefault(r.group, []).append(r)
    for key, rs in sorted(by_group.items()):
        for port, inv in ((22, "INV-SEC-001"), (5432, "INV-SEC-002")):
            hit = [r for r in rs if r.direction == "ingress" and not r.indeterminate and r.permits_tcp(port)]
            # a rule with unresolved sources only still contributes its resolved CIDRs when it determinately permits
            hit += [r for r in rs if r.direction == "ingress" and r.indeterminate and r.permits_tcp(port)
                    and not r.v4_open and not r.v6_open]
            v4 = [c for r in hit for c in r.v4]
            v6 = [c for r in hit for c in r.v6]
            if _covers_world(v4, False) or _covers_world(v6, True):
                an.violations.setdefault(inv, []).append(key)
            for r in rs:
                # A rule whose type is unresolved counts as a possible ingress rule (registry 3.3): it is
                # also possible when its resolved sources are public (the formula's "unresolved sources" is
                # read to include this case, so a type-unresolved world-open rule is never skipped).
                if r.indeterminate and r.could_permit_tcp(port) and (
                        r.v4_open or r.v6_open or (r.direction == "?" and r.world_cidr())):
                    an.possible.setdefault(inv, []).append(f"{key} via {r.holder}")
                    break
    # registry 6.4 row 7: indeterminate rules (any direction) of a pseudo-group that could permit TCP/5432
    for r in an.rules:
        if r.group.startswith("UNRESOLVED:") and r.indeterminate and r.could_permit_tcp(5432):
            an.func_unknown.append(f"INV-FUNC-001 possible (UNKNOWN) via pseudo-group rule {r.holder}")
    # unresolved values that cannot affect a result
    for r in an.rules:
        if r.indeterminate and not (
            (r.possible_ingress and r.could_permit_tcp(22) and (r.v4_open or r.v6_open or r.world_cidr()))
            or (r.possible_ingress and r.could_permit_tcp(5432) and (r.v4_open or r.v6_open or r.world_cidr()))
            or (r.group.startswith("UNRESOLVED:") and r.could_permit_tcp(5432))
        ):
            an.ignored.append(f"{r.holder}: unresolved {','.join(r.unres)}")
    return an


def forms_of(files: dict[str, str]) -> dict[str, tuple[str, str]]:
    """Per configured group: the form (blocks, empty, absent) of ingress and egress, for A10 checks."""
    mod = read_module(files)
    out: dict[str, tuple[str, str]] = {}
    for addr, blk in mod.resources.items():
        if blk.labels[0] != "aws_security_group":
            continue
        row = []
        for d in ("ingress", "egress"):
            if any(c.kind == d or (c.kind == "dynamic" and c.labels[:1] == [d]) for c in blk.children):
                row.append("blocks")
            elif d in blk.attrs:
                try:
                    row.append("empty" if evaluate(blk.attrs[d], mod) == [] else "blocks")
                except Unresolved:
                    row.append("blocks")
            else:
                row.append("absent")
        out[addr] = (row[0], row[1])
    return out


# ---------------------------------------------------------------------------
# Natives (modules without a graft): INV-FUNC-001 precheck, E2 to E4 only
# ---------------------------------------------------------------------------


def native_func_precheck(files: dict[str, str]) -> tuple[str, int, str]:
    """E2 to E4 of registry 6.3 on a module that has no graft. Returns (status, row, why).

    ``PASS?`` means E2 to E4 did not fail; E5 and E6 are not evaluated for natives, so such a native
    is still not accepted (see the screen). Any other status is the registry result of section 6.4.
    """
    mod = read_module(files)
    inst = sorted(a for a in mod.resources if a.startswith("aws_instance."))
    dbs = sorted(a for a in mod.resources if a.startswith("aws_db_instance."))
    if not inst or not dbs:
        return "FAIL", 1, "S or D absent"
    s, d = mod.resources[inst[0]], mod.resources[dbs[0]]
    # Registry 6.4 "first row that applies wins": row 2 (no vpc_security_group_ids) comes before row 3 (E2).
    for label, blk in (("D", d), ("S", s)):
        if "vpc_security_group_ids" not in blk.attrs:
            return "UNSUPPORTED", 2, f"{label} has no vpc_security_group_ids"
        try:
            ids = evaluate(blk.attrs["vpc_security_group_ids"], mod)
        except Unresolved as exc:
            return "UNKNOWN", 0, f"{label}.vpc_security_group_ids unresolved: {exc}"
        if not ids:
            return "UNSUPPORTED", 2, f"{label}.vpc_security_group_ids is empty"
    try:
        port = evaluate(d.attrs["port"], mod) if "port" in d.attrs else None
    except Unresolved as exc:
        return "UNKNOWN", 0, f"D.port unresolved: {exc}"
    if port is not None:
        if port != 5432:
            return "FAIL", 3, f"D.port is {port}"
    else:
        try:
            engine = evaluate(d.attrs["engine"], mod) if "engine" in d.attrs else None
        except Unresolved as exc:
            return "UNKNOWN", 0, f"D.engine unresolved: {exc}"
        if engine != "postgres":
            return "FAIL", 3, f"D.engine is {engine!r}, D.port absent"
    subnet_ok = False
    if "subnet_id" in s.attrs:
        parts = _traversal(s.attrs["subnet_id"])
        subnet_ok = bool(parts and parts[0] == "aws_subnet" and f"aws_subnet.{parts[1]}" in mod.resources)
    if not subnet_ok:
        # E4 does not hold; which §6.4 row applies to that is not quoted in the work package, so none is named.
        return "NOT-PASS", 0, "E4 does not hold: S.subnet_id does not reference a configured aws_subnet"
    return "PASS?", 0, "E2 to E4 do not fail"
