"""INV-SEC-001 (p = 22) and INV-SEC-002 (p = 5432): no public ingress to TCP/p (registry v1.0 sections 3 and 4).

Predicate ``PIP(p)`` (3.3), for each security group g, configured groups and pseudo-groups, attached or not:

* ``D(g)`` = determinate rules of ``In(g)`` with ``permits_tcp(r, p)``;
* ``violates4(g)``: the union of ``v4(r)`` over ``D(g)`` covers ``0.0.0.0/0``; ``violates6(g)`` the same for ``::/0``;
* ``possible4(g)``: an indeterminate rule of ``In(g)`` that could permit TCP/p and whose IPv4 sources are unresolved
  or include a prefix list; ``possible6(g)`` the same for IPv6.

Clause results (3.4, in order): FAIL if some non-MIXED group violates; UNSUPPORTED if some group is MIXED or
RETAINED-INLINE in ingress, some ingress rule is UNSUPPORTED (2.5), or a relevant-unsupported type (2.7) is present;
UNKNOWN if some group has ``possible``; otherwise PASS. Invariant: FAIL if either clause FAILs, otherwise the worst
clause (UNSUPPORTED, UNKNOWN, PASS). A RETAINED-INLINE group is not evaluated by ``violates`` (its inline rules
are not known). Standard library only.
"""

from __future__ import annotations

from typing import Any

from oracle import common
from oracle.common import FAIL, PASS, UNKNOWN, UNSUPPORTED
from oracle.model import Config, Literal, Ref, Unresolved
from oracle.rules import Group, Rule, RuleSet

VERIFIER = {22: ("tp.oracle.public_ingress", "INV-SEC-001"), 5432: ("tp.oracle.public_ingress", "INV-SEC-002")}


def _ip_sources_open(r: Rule, which: str) -> bool:
    """possible: the rule's IPv4 (or IPv6) sources are unresolved or include a prefix list."""
    lst = r.v4 if which == "v4" else r.v6
    return isinstance(lst, Unresolved) or isinstance(r.pl, Unresolved) or (isinstance(r.pl, list) and bool(r.pl))


def evaluate(config: Config, ruleset: RuleSet, p: int) -> dict[str, Any]:
    inv = VERIFIER[p][1]
    unsupported_types = sorted(t for t in config.present_types() if t in common.RELEVANT_UNSUPPORTED[inv])
    ambiguities: list[str] = []
    obs: dict[str, Any] = {"port": p, "groups_evaluated": len(ruleset.groups), "violations": [], "mixed_groups": [],
                           "retained_inline_groups": [], "indeterminate_rules": [], "unsupported_rules": [],
                           "relevant_unsupported_resources": [i.address for t in unsupported_types
                                                              for i in config.of_type(t)]}
    clause: dict[str, str] = {}
    targets = {"v4": common.ALL_V4, "v6": common.ALL_V6}
    unsupported_rule = False
    for g in ruleset.groups.values():
        if g.mixed:
            obs["mixed_groups"].append(g.key)
        if g.retained_inline.get("ingress"):
            obs["retained_inline_groups"].append({"group": g.key, "direction": "ingress"})
        for r in g.rules("ingress"):
            why = r.unsupported()
            if why:
                unsupported_rule = True
                obs["unsupported_rules"].append({"rule": r.address, "reason": why})
            elif not r.determinate():
                obs["indeterminate_rules"].append({"rule": r.address, "reasons": r.indeterminate_reasons()})
        if g.type_unresolved_rules():
            ambiguities.extend(f"{x.address}: rule type unresolved" for x in g.type_unresolved_rules())
    for which in ("v4", "v6"):
        violating = []
        possible = []
        for g in ruleset.groups.values():
            ingress = g.rules("ingress")
            d_g = [r for r in ingress if not r.unsupported() and r.determinate() and r.permits_tcp(p)]
            nets = [n for r in d_g for n in r.nets(which)]
            if common.covers(nets, targets[which]) and not g.mixed:
                violating.append((g, d_g))
            if any(not r.determinate() and not r.unsupported() and r.could_permit_tcp(p) and _ip_sources_open(r, which)
                   for r in ingress):
                possible.append(g.key)
            # A registry gap, recorded: an indeterminate rule whose own resolved CIDRs are public (it is outside D(g),
            # and its IP sources are resolved, so neither violates nor possible counts it).
            for r in ingress:
                if not r.determinate() and not r.unsupported() and r.permits_tcp(p) \
                        and not _ip_sources_open(r, which) and common.covers(r.nets(which), targets[which]):
                    ambiguities.append(f"{r.address}: public {which} CIDR on a rule indeterminate only by "
                                       f"{r.indeterminate_reasons()} (registry 3.3 counts it in neither violates nor possible)")
        if violating:
            clause[which] = FAIL
            for g, d_g in violating:
                obs["violations"].append({
                    "clause": "IPv4" if which == "v4" else "IPv6", "group": g.key,
                    "rules": [{"rule": r.address, "cidrs": (r.v4 if which == "v4" else r.v6),
                               "protocol": r.protocol, "ports": [r.from_port, r.to_port]}
                              for r in d_g if r.nets(which)]})
        elif obs["mixed_groups"] or obs["retained_inline_groups"] or unsupported_rule or unsupported_types:
            clause[which] = UNSUPPORTED
        elif possible:
            clause[which] = UNKNOWN
        else:
            clause[which] = PASS
    result = FAIL if FAIL in clause.values() else common.worst(clause.values())
    return {"invariant_id": inv, "invariant_version": 1, "verifier_id": VERIFIER[p][0], "verifier_version": "1",
            "parameters": {"p": p}, "evidence_level": "L2", "result": result,
            "clauses": {"IPv4": clause["v4"], "IPv6": clause["v6"]}, "observations": obs,
            "assumptions": ["registry 2.7: only the listed relevant-unsupported types change the result",
                            "registry 3.3: coverage split across two groups is not detected (v1)"],
            "ambiguities": sorted(set(ambiguities))}


def _src_repr(x: Any) -> Any:
    if isinstance(x, Ref):
        return x.address
    if isinstance(x, Literal):
        return x.value
    return str(x)


_ = Group  # re-exported type for callers
