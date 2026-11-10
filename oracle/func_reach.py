"""INV-FUNC-001: EC2 -> RDS on TCP/5432 at configuration level (registry v1.0 section 6).

Endpoints S (``aws_instance``) and D (``aws_db_instance``) are bound by the scenario (6.1, D5-12) and followed
across moves by the caller. Network model 6.2 (M1 RDS VPC from its security groups, M2 EC2 placement from its
subnet, M3 intra-VPC routes, M4 default network ACL, M5 IPv4 only, stateful groups). Predicate ``REACH(S, D, 5432)``
(6.3, E1 to E7) and results (6.4, rows 1 to 9, first row that applies). Where the registry text does not settle a
case met here, the evaluator never returns PASS for it and records the case in ``ambiguities`` (the work package's
stop rule: an ambiguity becomes an ``Open`` row before any label is written). Standard library only.
"""

from __future__ import annotations

from typing import Any

from oracle import common
from oracle.common import FAIL, PASS, UNKNOWN, UNSUPPORTED
from oracle.model import ABSENT, Config, Literal, Ref, Unresolved, blocks, field_value, id_list, id_scalar, value, written
from oracle.rules import Group, Rule, RuleSet

PORT = 5432
ASSUMPTIONS = ["M1 (C-15, C-77): VPC(D) is the VPC of D's security groups; RDS subnets are not modelled",
               "M4: default network ACL assumed (no NACL-related type present)", "M5: IPv4 only"]


def _key(x: Ref | Literal) -> str:
    return x.address if isinstance(x, Ref) else f"literal:{x.value}"


def _same(a: Any, b: Any) -> bool:
    return isinstance(a, (Ref, Literal)) and isinstance(b, (Ref, Literal)) and _key(a) == _key(b)


def _present(inst, key: str) -> bool:
    if written(inst, key):
        return True
    v = value(inst, key)
    return isinstance(v, list) and bool(v)


def _out(row: int, result: str, reason: str, obs: dict, ambiguities: list[str], assumptions: list[str]) -> dict[str, Any]:
    obs["row"] = row
    obs["reason"] = reason
    return {"invariant_id": "INV-FUNC-001", "invariant_version": 1, "verifier_id": "tp.oracle.reachability_cfg",
            "verifier_version": "1", "parameters": {"port": PORT}, "evidence_level": "L2", "result": result,
            "observations": obs, "assumptions": assumptions, "ambiguities": sorted(set(ambiguities))}


def evaluate(config: Config, ruleset: RuleSet, endpoints: dict[str, str]) -> dict[str, Any]:
    amb: list[str] = []
    assumptions = list(ASSUMPTIONS)
    if config.of_type("aws_db_subnet_group"):
        assumptions.append("registry 2.7: aws_db_subnet_group tolerated; its subnets are not modelled (C-15)")
    obs: dict[str, Any] = {"S": endpoints.get("S"), "D": endpoints.get("D"), "port": PORT}
    S = config.instances.get(endpoints.get("S", ""))
    D = config.instances.get(endpoints.get("D", ""))
    # Row 1: the protected endpoint is gone (deleted, with no move).
    if S is None or S.type != "aws_instance" or D is None or D.type != "aws_db_instance":
        gone = [r for r, i, t in (("S", S, "aws_instance"), ("D", D, "aws_db_instance")) if i is None or i.type != t]
        return _out(1, FAIL, f"endpoint {', '.join(gone)} absent", obs, amb, assumptions)
    sgs = id_list(config, S, "vpc_security_group_ids")
    sgd = id_list(config, D, "vpc_security_group_ids")
    subnet = id_scalar(config, S, "subnet_id")
    obs.update(SG_S=_show(sgs), SG_D=_show(sgd), subnet=_show(subnet))

    def groups_of(lst: Any) -> list[Group]:
        if not isinstance(lst, list):
            return []
        out = []
        for x in lst:
            g = ruleset.groups.get(_key(x))
            if g is not None:
                out.append(g)
        return out

    gs, gd = groups_of(sgs), groups_of(sgd)
    # VPC(D) (M1, E3) is needed by row 2 (M3, propagating_vgws); computed first, judged in row 4.
    vpc_d, e3_problem = _vpc_of_groups(config, sgd, ruleset, amb)
    # ---- Row 2
    reasons = []
    types = sorted(t for t in config.present_types() if t in common.RELEVANT_UNSUPPORTED["INV-FUNC-001"])
    if types:
        reasons.append(f"relevant-unsupported type present: {types}")
    if isinstance(vpc_d, (Ref, Literal)):
        for rt in config.of_type("aws_route_table"):
            if not _same(id_scalar(config, rt, "vpc_id"), vpc_d):
                continue
            if written(rt, "propagating_vgws"):
                reasons.append(f"{rt.address} sets propagating_vgws (C-78)")
            reasons.extend(_m3_routes(config, rt, vpc_d, amb))
    s_names = value(S, "security_groups")
    if written(S, "security_groups") and (isinstance(s_names, Unresolved) or (isinstance(s_names, list) and s_names)):
        reasons.append("S uses name-based security_groups")
    if sgd is ABSENT or sgd == []:
        reasons.append("D has no vpc_security_group_ids (default security group not modelled)")
    if sgs is ABSENT or sgs == []:
        reasons.append("S has no vpc_security_group_ids (default security group not modelled)")
    if subnet is ABSENT:
        reasons.append("S has no subnet_id (default VPC not modelled)")
    for g in gs + gd:
        if g.mixed:
            reasons.append(f"{g.key} is MIXED")
    for g in gd:
        if g.retained_inline.get("ingress"):
            reasons.append(f"{g.key} (SG(D)) is RETAINED-INLINE in ingress (C-84)")
    for g in gs:
        if g.retained_inline.get("egress"):
            reasons.append(f"{g.key} (SG(S)) is RETAINED-INLINE in egress (C-84)")
    for key in ("network_interface", "primary_network_interface"):
        if _present(S, key):
            reasons.append(f"S has a {key} block (C-78)")
    for r in [r for g in gs for r in g.rules("egress")] + [r for g in gd for r in g.rules("ingress")]:
        why = r.unsupported()
        if why:
            reasons.append(f"rule {r.address} is UNSUPPORTED: {why}")
    if reasons:
        return _out(2, UNSUPPORTED, "; ".join(sorted(set(reasons))), obs, amb, assumptions)
    # ---- Row 3: E2 definitely false
    port = value(D, "port")
    engine = value(D, "engine")
    e2_unresolved = False
    if port is not ABSENT and port is not None:
        if isinstance(port, Unresolved):
            e2_unresolved = True
        elif _int(port) != PORT:
            return _out(3, FAIL, f"D.port = {port}", obs, amb, assumptions)
    else:
        if isinstance(engine, Unresolved):
            e2_unresolved = True
        elif engine != "postgres":
            return _out(3, FAIL, f"port absent and D.engine = {engine!r}", obs, amb, assumptions)
    if e2_unresolved:
        amb.append("E2 unresolved (D.port or D.engine): registry 6.4 has no row for it; never PASS")
    # ---- Row 4: E3 or E4 fails because a needed value is unresolved
    if isinstance(sgd, Unresolved):
        return _out(4, UNKNOWN, f"D.vpc_security_group_ids unresolved: {sgd.reason}", obs, amb, assumptions)
    if e3_problem:
        return _out(4, UNKNOWN, e3_problem, obs, amb, assumptions)
    if isinstance(subnet, Unresolved):
        return _out(4, UNKNOWN, f"S.subnet_id unresolved: {subnet.reason}", obs, amb, assumptions)
    if isinstance(subnet, Literal):
        amb.append("E4 fails on an external subnet ID (no configured aws_subnet): registry 6.4 has no row; never PASS")
        return _out(4, UNKNOWN, "S.subnet_id is an external literal", obs, amb, assumptions)
    sub = config.instances[subnet.address]
    if sub.type != "aws_subnet":
        amb.append(f"E4: S.subnet_id references {sub.type}, not aws_subnet; never PASS")
        return _out(4, UNKNOWN, f"S.subnet_id references a {sub.type}", obs, amb, assumptions)
    vpc_s = id_scalar(config, sub, "vpc_id")
    if isinstance(vpc_s, Unresolved) or vpc_s is ABSENT:
        return _out(4, UNKNOWN, f"VPC(S) unresolved ({sub.address}.vpc_id)", obs, amb, assumptions)
    obs.update(VPC_S=_show(vpc_s), VPC_D=_show(vpc_d))
    # ---- Row 5
    if not _same(vpc_s, vpc_d):
        return _out(5, FAIL, f"VPC(S) {_show(vpc_s)} != VPC(D) {_show(vpc_d)}", obs, amb, assumptions)
    # ---- Rows 6 to 9
    cidr_d = _vpc_cidr(config, vpc_d)
    addr_s = _addr_s(S, sub)
    obs.update(CIDR_VPC_D=str(cidr_d) if cidr_d is not None else None, ADDR_S=str(addr_s) if addr_s is not None else None)
    if cidr_d is None:
        amb.append("CIDR(VPC(D)) unresolved (external VPC or unresolved cidr_block): registry 6.4 has no row; never PASS")
    if addr_s is None:
        amb.append("ADDR(S) unresolved (no private_ip and no resolved subnet cidr_block): never PASS")
    sgd_keys = {_key(x) for x in sgd}
    sgs_keys = {_key(x) for x in sgs} if isinstance(sgs, list) else set()
    pseudo_unres = [r for g in ruleset.groups.values() if g.pseudo and g.key.startswith("UNRESOLVED:") for r in g.separate]

    def e5_match(r: Rule) -> bool:
        return r.permits_tcp(PORT) and ((isinstance(r.src_sg, list) and any(_key(x) in sgd_keys for x in r.src_sg))
                                        or (cidr_d is not None and common.covers(r.nets("v4"), cidr_d)))

    def e6_match(r: Rule, h: Group) -> bool:
        return r.permits_tcp(PORT) and (
            (isinstance(r.src_sg, list) and any(_key(x) in sgs_keys for x in r.src_sg))
            or (r.self_ is True and h.key in sgs_keys)
            or (addr_s is not None and common.covers(r.nets("v4"), addr_s)))

    egress = [(g, r) for g in gs for r in g.rules("egress")]
    ingress = [(h, r) for h in gd for r in h.rules("ingress")]
    m5 = [r for _g, r in egress if r.determinate() and e5_match(r)]
    m6 = [r for h, r in ingress if r.determinate() and e6_match(r, h)]
    obs.update(egress_rule_matched=[r.address for r in m5], ingress_rule_matched=[r.address for r in m6])
    if m5 and m6:
        if e2_unresolved:
            return _out(6, UNKNOWN, "E5 and E6 hold, but E2 is unresolved", obs, amb, assumptions)
        return _out(6, PASS, "E5 and E6 hold with determinate rules", obs, amb, assumptions)
    failing = {}
    if not m5:
        possible = [r for _g, r in egress if not r.determinate() and _could_e5(r, sgd_keys, cidr_d)] + \
                   [r for r in pseudo_unres if _dir_could(r, "egress") and _could_e5(r, sgd_keys, cidr_d)]
        partial = [r for _g, r in egress if r.determinate() and r.permits_tcp(PORT) and cidr_d is not None
                   and common.partly_covers(r.nets("v4"), cidr_d)]
        failing["E5"] = ("indeterminate", possible) if possible else (("partial", partial) if partial else ("no", []))
        if cidr_d is None and failing["E5"][0] == "no":
            failing["E5"] = ("unresolved", [])
    if not m6:
        possible = [r for h, r in ingress if not r.determinate() and _could_e6(r, h.key, sgs_keys, addr_s)] + \
                   [r for r in pseudo_unres if _dir_could(r, "ingress") and _could_e6(r, None, sgs_keys, addr_s)]
        partial = [r for _h, r in ingress if r.determinate() and r.permits_tcp(PORT) and addr_s is not None
                   and common.partly_covers(r.nets("v4"), addr_s)]
        failing["E6"] = ("indeterminate", possible) if possible else (("partial", partial) if partial else ("no", []))
        if addr_s is None and failing["E6"][0] == "no":
            failing["E6"] = ("unresolved", [])
    obs["failing"] = {e: {"status": s, "rules": [r.address for r in rs]} for e, (s, rs) in failing.items()}
    statuses = {s for s, _rs in failing.values()}
    if "no" in statuses and statuses - {"no"}:
        amb.append(f"{sorted(failing)} fail; only some have a possible rule ({ {e: s for e, (s, _r) in failing.items()} }): "
                   "registry 6.4 rows 7 and 8 do not say whether one definite failure decides (FAIL used)")
    if "no" in statuses:
        return _out(9, FAIL, f"{' and '.join(e for e, (s, _r) in sorted(failing.items()) if s == 'no')} does not hold",
                    obs, amb, assumptions)
    if "unresolved" in statuses:
        return _out(8, UNKNOWN, "a value needed by E5 or E6 is unresolved", obs, amb, assumptions)
    if "indeterminate" in statuses:
        return _out(7, UNKNOWN, "an indeterminate rule could satisfy " + ", ".join(sorted(failing)), obs, amb, assumptions)
    return _out(8, UNKNOWN, "a CIDR partly covers " + ", ".join(sorted(failing)), obs, amb, assumptions)


def _int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _show(x: Any) -> Any:
    if isinstance(x, list):
        return [_show(y) for y in x]
    if isinstance(x, Ref):
        return x.address
    if isinstance(x, Literal):
        return x.value
    if isinstance(x, Unresolved):
        return f"unresolved: {x.reason}"
    return x


def _vpc_of_groups(config: Config, sgd: Any, ruleset: RuleSet, amb: list[str]) -> tuple[Any, str]:
    """(VPC(D), problem). VPC(D) is the one VPC of D's groups (M1, E3); problem is a row-4 reason or ""."""
    if not isinstance(sgd, list) or not sgd:
        return None, ""
    vpcs = []
    for x in sgd:
        if isinstance(x, Literal) or config.instances[x.address].type != "aws_security_group":
            amb.append("E3 fails on a member of SG(D) that is not a configured aws_security_group: registry 6.4 has "
                       "no row; never PASS")
            return None, f"SG(D) member {_show(x)} is not a configured aws_security_group"
        v = ruleset.groups[x.address].vpc
        if v is ABSENT:  # provider-computed and not set: unresolved (registry 2.2)
            return None, f"{x.address}.vpc_id not set (provider-computed, unresolved)"
        if isinstance(v, Unresolved):
            return None, f"{x.address}.vpc_id unresolved: {v.reason}"
        vpcs.append(v)
    if any(not _same(v, vpcs[0]) for v in vpcs):
        amb.append("E3 fails because D's groups are in different VPCs: registry 6.4 has no row; never PASS")
        return None, "D's security groups do not share one VPC"
    return vpcs[0], ""


def _vpc_cidr(config: Config, vpc: Any):
    if isinstance(vpc, Ref) and config.instances[vpc.address].type == "aws_vpc":
        c = value(config.instances[vpc.address], "cidr_block")
        n = common.parse_cidr(c) if isinstance(c, str) else None
        return n if n is not None and n.version == 4 else None
    return None


def _addr_s(S, sub):
    ip = value(S, "private_ip")
    if isinstance(ip, str) and ip:
        return common.parse_cidr(ip + "/32")
    c = value(sub, "cidr_block")
    return common.parse_cidr(c) if isinstance(c, str) else None


def _m3_routes(config: Config, rt, vpc_d: Any, amb: list[str]) -> list[str]:
    """M3: a route of a route table of VPC(D) whose destination is contained in the VPC CIDR, target not local."""
    out = []
    cidr = _vpc_cidr(config, vpc_d)
    got = blocks(rt, "route")
    if isinstance(got, Unresolved):
        amb.append(f"{rt.address}.route unresolved: M3 cannot be decided; never PASS")
        return [f"{rt.address}.route unresolved (M3 not decidable)"]
    for i, (r, u) in enumerate(zip(*got)):
        dest = field_value(r, u, "cidr_block")
        if isinstance(dest, Unresolved):
            amb.append(f"{rt.address}.route[{i}]: destination unresolved for M3; never PASS")
            out.append(f"{rt.address}.route[{i}] destination unresolved (M3 not decidable)")
            continue
        if not dest:
            continue  # an IPv6 or prefix-list destination (M5: IPv4 only)
        n = common.parse_cidr(dest)
        if n is None or cidr is None:
            amb.append(f"{rt.address}.route[{i}]: destination or VPC CIDR unresolved for M3; never PASS")
            out.append(f"{rt.address}.route[{i}] cannot be placed against the VPC CIDR")
            continue
        if common.covers([cidr], n) and field_value(r, u, "gateway_id") != "local":
            out.append(f"{rt.address}.route[{i}] {dest} is inside the VPC CIDR with a non-local target (M3)")
    return out


def _dir_could(r: Rule, direction: str) -> bool:
    return isinstance(r.direction, Unresolved) or r.direction == direction


def _could_e5(r: Rule, sgd_keys: set[str], cidr_d) -> bool:
    if r.unsupported() or not r.could_permit_tcp(PORT):
        return False
    if isinstance(r.src_sg, Unresolved) or isinstance(r.v4, Unresolved) or isinstance(r.pl, Unresolved) \
            or (isinstance(r.pl, list) and r.pl):
        return True
    if isinstance(r.src_sg, list) and any(_key(x) in sgd_keys for x in r.src_sg):
        return True
    return cidr_d is not None and common.covers(r.nets("v4"), cidr_d)


def _could_e6(r: Rule, h_key: str | None, sgs_keys: set[str], addr_s) -> bool:
    if r.unsupported() or not r.could_permit_tcp(PORT):
        return False
    if isinstance(r.src_sg, Unresolved) or isinstance(r.v4, Unresolved) or isinstance(r.pl, Unresolved) \
            or (isinstance(r.pl, list) and r.pl) or isinstance(r.self_, Unresolved):
        return True
    if isinstance(r.src_sg, list) and any(_key(x) in sgs_keys for x in r.src_sg):
        return True
    if r.self_ is True and (h_key is None or h_key in sgs_keys):
        return True
    return addr_s is not None and common.covers(r.nets("v4"), addr_s)
