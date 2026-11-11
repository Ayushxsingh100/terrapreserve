"""Tests for D4b review round 4: family-specific, registry-evaluable INV-FUNC-001 breaks.

Written before the code change (test-first). Every test runs over every generated
scenario available: all of ``scenarios/dev/`` and, when ``TERRAPRESERVE_PRIVATE`` is set,
all of that directory (the withheld test split). When the variable is not set the
private part is skipped and the reason is printed.

Scope of the file-level rules (tests 1-5, 7, 10). The first-party generated model of a
step is ``main.tf`` for the controlled tier and ``terrapreserve_graft.tf`` for grafted
real-world hosts. Verbatim third-party host files and derived natives (F1 span edits only)
are not generator-controlled and are not parsed, except for the empty-list scan of
test 1, which reads every ``.tf`` file of every step.

The evaluator in this file is a generator self-check written from the quoted registry
text (section 6.3 E1-E6 and the section 6.4 rows 1, 2, 3, 6, 8, 9). It is NOT the oracle,
and it is not a label. It supports only the forms the generator emits (literal ports,
literal CIDRs, ``aws_security_group.<name>.id`` references) and fails with
"unsupported form" on anything else, so the generator must stay inside that subset.

Tests:
1. No step contains ``vpc_security_group_ids = []`` (registry 6.4 row 2: UNSUPPORTED).
2. No MIXED group in any step (registry 2.6 and C-84).
3. No RETAINED-INLINE group: a direction that is *blocks* in step k-1 is not *absent* in
   step k (registry 2.6, D0 amendment A10), following ``moved`` blocks.
4. No non-local route whose destination is inside the VPC CIDR (M3).
5. Egress CIDRs: no step has an app-group egress CIDR that only partly covers
   CIDR(VPC(D)); in safe scenarios every app-group egress rule that an operator changed
   covers CIDR(VPC(D)) fully or does not permit TCP 5432.
6. Family mechanism: F3, F5 and F7 unsafe scenarios that break INV-FUNC-001 do it through
   a security group or security group rule, never through an edit on S or D.
7. Intent truth: INV-FUNC-001 in intent.breaks <=> the evaluator says FAIL on the last
   step; INV-FUNC-001 in intent.preserves => PASS on every step; no step is UNSUPPORTED
   or UNKNOWN for a reason the generator controls.
8. Coverage: F3, F4, F5, F7, F8 have INV-FUNC-001-breaking unsafe scenarios in both tiers;
   F1 unsafe covers INV-SEC-001, INV-SEC-002 and INV-SEC-003.
9. Names: operator names in code and in docs/D4_OPERATORS.md agree, computed.
10. (Extra, found while writing test 7) Security intent truth: the lexical state of
    INV-SEC-001/002/003 at the last step matches intent.breaks, and S0 violates exactly
    the repair target.
11. (Extra) docs/D5_CARRYOVER.md lists each INV-FUNC-001-breaking operator with the
    mechanism code and designed registry row taken from the code.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

PRIVATE_ENV = "TERRAPRESERVE_PRIVATE"
FAMILIES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]


# ---------------------------------------------------------------------------
# Scenario loading
# ---------------------------------------------------------------------------


class UnsupportedForm(Exception):
    """The generated text uses a form the self-check evaluator does not support."""


def scenario_roots() -> list[tuple[str, Path]]:
    roots = [("dev", REPO_ROOT / "scenarios" / "dev")]
    env = os.environ.get(PRIVATE_ENV)
    if env and Path(env).is_dir():
        roots.append(("test", Path(env)))
    return roots


@dataclass
class Sc:
    split: str
    dir: Path
    data: dict[str, Any]
    _models: dict[int, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.data["scenario_id"]

    @property
    def family(self) -> str:
        return self.data["family"]

    @property
    def cls(self) -> str:
        return self.data["intent"]["class"]

    @property
    def tier(self) -> str:
        return self.data["source"]["tier"]

    @property
    def breaks(self) -> list[str]:
        return list(self.data["intent"]["breaks"])

    @property
    def preserves(self) -> list[str]:
        return list(self.data["intent"]["preserves"])

    def step_dirs(self) -> list[Path]:
        return sorted(
            (p for p in self.dir.glob("step_*") if p.is_dir()),
            key=lambda p: int(p.name.split("_")[1]),
        )

    def model_file(self) -> str | None:
        if self.data.get("grafted"):
            return "terrapreserve_graft.tf"
        if self.tier == "controlled":
            return "main.tf"
        return None

    def model(self, k: int) -> "Model | None":
        mf = self.model_file()
        if mf is None:
            return None
        if k not in self._models:
            sd = self.step_dirs()[k]
            # D4c-03 axis 5: a controlled step is main.tf, or split into network.tf, compute.tf and database.tf.
            parts = [mf] if (sd / mf).is_file() else ["network.tf", "compute.tf", "database.tf"]
            text = "\n".join((sd / f).read_text(encoding="utf-8") for f in parts)
            self._models[k] = parse_model(text)
        return self._models[k]

    def models(self) -> list["Model"]:
        return [self.model(k) for k in range(len(self.step_dirs()))]  # type: ignore[misc]


def load_scenario(path: Path, split: str = "scratch") -> Sc:
    data = json.loads((path / "scenario.json").read_text(encoding="utf-8"))
    return Sc(split=split, dir=path, data=data)


def load_all() -> list[Sc]:
    out: list[Sc] = []
    for split, root in scenario_roots():
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append(load_scenario(p, split))
    return out


# ---------------------------------------------------------------------------
# Mini parser for the emitter's canonical output
# ---------------------------------------------------------------------------


@dataclass
class Res:
    type: str
    name: str
    attrs: dict[str, str] = field(default_factory=dict)
    blocks: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    @property
    def addr(self) -> str:
        return f"{self.type}.{self.name}"


@dataclass
class Model:
    resources: dict[str, Res] = field(default_factory=dict)
    moved: list[tuple[str, str]] = field(default_factory=list)


_RES_RE = re.compile(r'^resource "([^"]+)" "([^"]+)" \{$')
_ATTR_RE = re.compile(r"^  ([a-z_0-9]+)\s+= (.*)$")
_BLOCK_START_RE = re.compile(r"^  ([a-z_0-9]+) \{$")
_BLOCK_ATTR_RE = re.compile(r"^    ([a-z_0-9]+)\s+= (.*)$")


def parse_model(text: str) -> Model:
    model = Model()
    lines = text.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line == "moved {":
            frm = to = None
            i += 1
            while lines[i] != "}":
                m = re.match(r"^  (from|to)\s+= (\S+)$", lines[i])
                if m:
                    if m.group(1) == "from":
                        frm = m.group(2)
                    else:
                        to = m.group(2)
                i += 1
            if frm and to:
                model.moved.append((frm, to))
            i += 1
            continue
        rm = _RES_RE.match(line)
        if not rm:
            if line.strip():
                raise UnsupportedForm(f"unsupported top-level line: {line!r}")
            i += 1
            continue
        res = Res(rm.group(1), rm.group(2))
        i += 1
        while lines[i] != "}":
            cur = lines[i]
            if not cur.strip():
                i += 1
                continue
            bm = _BLOCK_START_RE.match(cur)
            if bm:
                battrs: dict[str, str] = {}
                i += 1
                while lines[i] != "  }":
                    am = _BLOCK_ATTR_RE.match(lines[i])
                    if not am:
                        raise UnsupportedForm(f"unsupported block line: {lines[i]!r}")
                    battrs[am.group(1)] = am.group(2).strip()
                    i += 1
                res.blocks.append((bm.group(1), battrs))
                i += 1
                continue
            am = _ATTR_RE.match(cur)
            if not am:
                raise UnsupportedForm(f"unsupported resource line: {cur!r}")
            val = am.group(2).strip()
            if val.endswith("{") or val == "(":
                raise UnsupportedForm(f"multi-line value for {am.group(1)}")
            res.attrs[am.group(1)] = val
            i += 1
        model.resources[res.addr] = res
        i += 1
    return model


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------


def _split_top(s: str) -> list[str]:
    items: list[str] = []
    depth = 0
    in_q = False
    cur = []
    for ch in s:
        if ch == '"':
            in_q = not in_q
        if not in_q:
            if ch in "[({":
                depth += 1
            elif ch in "])}":
                depth -= 1
            elif ch == "," and depth == 0:
                items.append("".join(cur).strip())
                cur = []
                continue
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        items.append(tail)
    return items


def as_list(raw: str | None) -> list[str]:
    if raw is None:
        return []
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        raise UnsupportedForm(f"expected a list literal, got {raw!r}")
    return _split_top(raw[1:-1])


def as_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    m = re.fullmatch(r'"([^"\\]*)"', raw.strip())
    return m.group(1) if m else None


def as_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    if re.fullmatch(r"-?\d+", raw.strip()):
        return int(raw.strip())
    raise UnsupportedForm(f"expected an integer literal, got {raw!r}")


def ref_addr(raw: str | None) -> str | None:
    if raw is None:
        return None
    m = re.fullmatch(r"(aws_[a-z_]+\.[A-Za-z0-9_\-]+)\.(?:id|name)", raw.strip())
    return m.group(1) if m else None


def str_list(raw: str | None) -> list[str]:
    out = []
    for item in as_list(raw):
        s = as_str(item)
        if s is None:
            raise UnsupportedForm(f"expected string literals in list, got {item!r}")
        out.append(s)
    return out


def ref_list(raw: str | None) -> list[str]:
    out = []
    for item in as_list(raw):
        a = ref_addr(item)
        if a is None:
            raise UnsupportedForm(f"expected references in list, got {item!r}")
        out.append(a)
    return out


# ---------------------------------------------------------------------------
# Security group rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    kind: str  # "block" or "rule"
    holder: str  # address of the resource that holds the rule
    group: str  # address of the security group the rule belongs to
    direction: str
    index: int  # position among blocks of this direction (0 for rule resources)
    protocol: str
    from_port: int
    to_port: int
    cidrs: tuple[str, ...]
    ipv6: tuple[str, ...]
    src_groups: tuple[str, ...]
    self_flag: bool

    @property
    def key(self) -> tuple[Any, ...]:
        if self.kind == "rule":
            return ("rule", self.holder)
        return ("block", self.group, self.direction, self.index)

    @property
    def signature(self) -> tuple[Any, ...]:
        return (self.protocol, self.from_port, self.to_port, self.cidrs, self.ipv6,
                self.src_groups, self.self_flag)

    def permits_tcp(self, port: int) -> bool:
        if self.protocol == "-1":
            return True
        if self.protocol in ("tcp", "6"):
            return self.from_port <= port <= self.to_port
        return False


def _make_rule(kind: str, holder: str, group: str, direction: str, index: int,
               attrs: dict[str, str]) -> Rule:
    allowed = {"type", "from_port", "to_port", "protocol", "cidr_blocks", "ipv6_cidr_blocks",
               "security_group_id", "source_security_group_id", "security_groups", "self",
               "description", "count"}
    extra = set(attrs) - allowed
    if extra:
        raise UnsupportedForm(f"unsupported rule attributes {sorted(extra)} on {holder}")
    if attrs.get("count", "1") != "1":
        raise UnsupportedForm(f"count on {holder} is not 1")
    protocol = as_str(attrs.get("protocol"))
    if protocol is None:
        raise UnsupportedForm(f"non-literal protocol on {holder}")
    srcs: list[str] = []
    if "source_security_group_id" in attrs:
        a = ref_addr(attrs["source_security_group_id"])
        if a is None:
            raise UnsupportedForm(f"non-reference source on {holder}")
        srcs.append(a)
    if "security_groups" in attrs:
        srcs.extend(ref_list(attrs["security_groups"]))
    return Rule(
        kind=kind, holder=holder, group=group, direction=direction, index=index,
        protocol=protocol,
        from_port=as_int(attrs.get("from_port")) or 0,
        to_port=as_int(attrs.get("to_port")) or 0,
        cidrs=tuple(sorted(str_list(attrs.get("cidr_blocks")))),
        ipv6=tuple(sorted(str_list(attrs.get("ipv6_cidr_blocks")))),
        src_groups=tuple(sorted(srcs)),
        self_flag=attrs.get("self") == "true",
    )


def all_rules(model: Model) -> list[Rule]:
    rules: list[Rule] = []
    for addr, res in model.resources.items():
        if res.type == "aws_security_group":
            counters: dict[str, int] = {}
            for label, battrs in res.blocks:
                if label not in ("ingress", "egress"):
                    continue
                idx = counters.get(label, 0)
                counters[label] = idx + 1
                rules.append(_make_rule("block", addr, addr, label, idx, battrs))
        elif res.type == "aws_security_group_rule":
            direction = as_str(res.attrs.get("type"))
            grp = ref_addr(res.attrs.get("security_group_id"))
            if direction not in ("ingress", "egress") or grp is None:
                raise UnsupportedForm(f"unsupported rule resource {addr}")
            rules.append(_make_rule("rule", addr, grp, direction, 0, res.attrs))
    return rules


def rules_of(model: Model, group: str, direction: str) -> list[Rule]:
    return [r for r in all_rules(model) if r.group == group and r.direction == direction]


# ---------------------------------------------------------------------------
# Test 1 to 4 checks
# ---------------------------------------------------------------------------

_EMPTY_SG_RE = re.compile(r"vpc_security_group_ids\s*=\s*\[\s*\]")


def check_empty_sg_list(sc: Sc) -> list[str]:
    out = []
    for sd in sc.step_dirs():
        for tf in sorted(sd.glob("*.tf")):
            if _EMPTY_SG_RE.search(tf.read_text(encoding="utf-8")):
                out.append(f"{sc.id}/{sd.name}/{tf.name}: empty vpc_security_group_ids")
    return out


def mixed_groups(model: Model) -> list[str]:
    targets: dict[str, set[str]] = {}
    for res in model.resources.values():
        if res.type == "aws_security_group_rule":
            g = ref_addr(res.attrs.get("security_group_id"))
            d = as_str(res.attrs.get("type"))
            if g and d:
                targets.setdefault(g, set()).add(d)
    out = []
    for addr, res in model.resources.items():
        if res.type != "aws_security_group":
            continue
        inline = {lab for lab, _ in res.blocks if lab in ("ingress", "egress")}
        empty = {d for d in ("ingress", "egress") if res.attrs.get(d, "").replace(" ", "") == "[]"}
        t = targets.get(addr, set())
        if (inline and t) or (empty & t):
            out.append(addr)
    return out


def check_mixed(sc: Sc) -> list[str]:
    out = []
    if sc.model_file() is None:
        return out
    for k, m in enumerate(sc.models()):
        for g in mixed_groups(m):
            out.append(f"{sc.id}/step_{k}: MIXED group {g}")
    return out


def _form(res: Res, direction: str) -> str:
    if any(lab == direction for lab, _ in res.blocks):
        return "blocks"
    if res.attrs.get(direction, "").replace(" ", "") == "[]":
        return "empty"
    return "absent"


def check_retained_inline(sc: Sc) -> list[str]:
    out = []
    if sc.model_file() is None:
        return out
    models = sc.models()
    for k in range(1, len(models)):
        prev, cur = models[k - 1], models[k]
        rename = {a: b for a, b in cur.moved}
        for addr, pres in prev.resources.items():
            if pres.type != "aws_security_group":
                continue
            new_addr = rename.get(addr, addr)
            cres = cur.resources.get(new_addr)
            if cres is None:
                continue
            for d in ("ingress", "egress"):
                if _form(pres, d) == "blocks" and _form(cres, d) == "absent":
                    out.append(f"{sc.id}/step_{k}: {new_addr} {d} was blocks and is now absent (RETAINED-INLINE)")
    return out


def _vpc_cidr_of(model: Model, vpc_ref: str | None) -> ipaddress.IPv4Network | None:
    a = ref_addr(vpc_ref)
    if a is None or a not in model.resources:
        return None
    c = as_str(model.resources[a].attrs.get("cidr_block"))
    return ipaddress.ip_network(c) if c else None  # type: ignore[return-value]


def check_nonlocal_routes(sc: Sc) -> list[str]:
    out = []
    if sc.model_file() is None:
        return out
    for k, m in enumerate(sc.models()):
        for addr, res in m.resources.items():
            if res.type == "aws_route_table":
                vpc = _vpc_cidr_of(m, res.attrs.get("vpc_id"))
                if vpc is None:
                    continue
                for lab, battrs in res.blocks:
                    if lab != "route":
                        continue
                    c = as_str(battrs.get("cidr_block"))
                    if c and ipaddress.ip_network(c).subnet_of(vpc):  # type: ignore[arg-type]
                        out.append(f"{sc.id}/step_{k}: {addr} has non-local route {c} inside {vpc}")
            elif res.type == "aws_route":
                rt = ref_addr(res.attrs.get("route_table_id"))
                if rt and rt in m.resources:
                    vpc = _vpc_cidr_of(m, m.resources[rt].attrs.get("vpc_id"))
                    c = as_str(res.attrs.get("destination_cidr_block"))
                    if vpc is not None and c and ipaddress.ip_network(c).subnet_of(vpc):  # type: ignore[arg-type]
                        out.append(f"{sc.id}/step_{k}: {addr} has non-local route {c} inside {vpc}")
    return out


# ---------------------------------------------------------------------------
# Evaluator for the E5/E6 subset of registry 6.3 (generator self-check)
# ---------------------------------------------------------------------------


@dataclass
class Verdict:
    status: str  # PASS | FAIL | UNKNOWN | UNSUPPORTED
    row: int
    why: str


def endpoints(model0: Model) -> tuple[str, str]:
    inst = [a for a, r in model0.resources.items() if r.type == "aws_instance"]
    dbs = [a for a, r in model0.resources.items() if r.type == "aws_db_instance"]
    if len(inst) != 1 or len(dbs) != 1:
        raise UnsupportedForm(f"step 0 must hold exactly one aws_instance and one aws_db_instance, got {inst} {dbs}")
    return inst[0], dbs[0]


def _covers(cidrs: tuple[str, ...], target: ipaddress.IPv4Network) -> bool:
    return any(target.subnet_of(ipaddress.ip_network(c)) for c in cidrs)  # type: ignore[arg-type]


def _partial(cidrs: tuple[str, ...], target: ipaddress.IPv4Network) -> bool:
    for c in cidrs:
        net = ipaddress.ip_network(c)
        if net.overlaps(target) and not target.subnet_of(net):  # type: ignore[arg-type]
            return True
    return False


def evaluate_func(model: Model, s_addr: str, d_addr: str) -> Verdict:
    """Evaluate INV-FUNC-001 on the supported subset of registry 6.3 and 6.4."""
    if s_addr not in model.resources or d_addr not in model.resources:
        return Verdict("FAIL", 1, "S or D absent")
    s, d = model.resources[s_addr], model.resources[d_addr]
    # Registry 6.4 "first row that applies wins": row 2 (no vpc_security_group_ids) comes before row 3 (E2).
    d_sgs = ref_list(d.attrs.get("vpc_security_group_ids")) if "vpc_security_group_ids" in d.attrs else []
    s_sgs = ref_list(s.attrs.get("vpc_security_group_ids")) if "vpc_security_group_ids" in s.attrs else []
    if not d_sgs or not s_sgs:
        return Verdict("UNSUPPORTED", 2, "D or S has no vpc_security_group_ids")
    # E2
    port = as_int(d.attrs.get("port"))
    if port is not None:
        if port != 5432:
            return Verdict("FAIL", 3, f"D.port is {port}")
    elif as_str(d.attrs.get("engine")) != "postgres":
        raise UnsupportedForm("D.engine is not the literal postgres and D.port is absent")
    # E3
    vpcs = set()
    for g in d_sgs:
        if g not in model.resources:
            raise UnsupportedForm(f"D references unknown group {g}")
        v = ref_addr(model.resources[g].attrs.get("vpc_id"))
        if v is None:
            raise UnsupportedForm(f"group {g} has no resolvable vpc_id")
        vpcs.add(v)
    if len(vpcs) != 1:
        raise UnsupportedForm("SG(D) does not share one VPC")
    vpc_addr = vpcs.pop()
    # E4
    sub_addr = ref_addr(s.attrs.get("subnet_id"))
    if sub_addr is None or sub_addr not in model.resources:
        raise UnsupportedForm("S.subnet_id does not reference a configured aws_subnet")
    sub = model.resources[sub_addr]
    if ref_addr(sub.attrs.get("vpc_id")) != vpc_addr:
        return Verdict("FAIL", 9, "VPC(S) != VPC(D)")
    vpc_cidr = as_str(model.resources[vpc_addr].attrs.get("cidr_block"))
    sub_cidr = as_str(sub.attrs.get("cidr_block"))
    if vpc_cidr is None or sub_cidr is None:
        raise UnsupportedForm("non-literal VPC or subnet CIDR")
    if "private_ip" in s.attrs:
        raise UnsupportedForm("S.private_ip is set")
    vpc_net = ipaddress.ip_network(vpc_cidr)
    addr_net = ipaddress.ip_network(sub_cidr)
    for g in s_sgs:
        if g not in model.resources:
            raise UnsupportedForm(f"S references unknown group {g}")
    # row 2: MIXED groups among SG(S) and SG(D)
    mixed = set(mixed_groups(model))
    bad = [g for g in set(s_sgs) | set(d_sgs) if g in mixed]
    if bad:
        return Verdict("UNSUPPORTED", 2, f"MIXED group(s) {sorted(bad)}")
    # E5
    e5 = False
    egress_partial = False
    for g in s_sgs:
        for r in rules_of(model, g, "egress"):
            if r.permits_tcp(5432) and (set(r.src_groups) & set(d_sgs) or _covers(r.cidrs, vpc_net)):  # type: ignore[arg-type]
                e5 = True
            if _partial(r.cidrs, vpc_net):  # type: ignore[arg-type]
                egress_partial = True
    # E6
    e6 = False
    ingress_partial = False
    for h in d_sgs:
        for r in rules_of(model, h, "ingress"):
            if r.permits_tcp(5432) and (
                set(r.src_groups) & set(s_sgs)
                or (r.self_flag and h in s_sgs)
                or _covers(r.cidrs, addr_net)  # type: ignore[arg-type]
            ):
                e6 = True
            if _partial(r.cidrs, addr_net):  # type: ignore[arg-type]
                ingress_partial = True
    if e5 and e6:
        return Verdict("PASS", 6, "E5 and E6 hold")
    if (not e5 and egress_partial) or (not e6 and ingress_partial):
        return Verdict("UNKNOWN", 8, "a CIDR partly covers the VPC CIDR or ADDR(S)")
    return Verdict("FAIL", 9, f"E5={e5} E6={e6}")


def check_intent_truth(sc: Sc) -> list[str]:
    out: list[str] = []
    if sc.model_file() is None:
        return out
    models = sc.models()
    try:
        s_addr, d_addr = endpoints(models[0])
        verdicts = [evaluate_func(m, s_addr, d_addr) for m in models]
    except UnsupportedForm as exc:
        return [f"{sc.id}: unsupported form: {exc}"]
    for k, v in enumerate(verdicts):
        if v.status not in ("PASS", "FAIL"):
            out.append(f"{sc.id}/step_{k}: evaluator says {v.status} (row {v.row}): {v.why}")
    if verdicts[0].status != "PASS":
        out.append(f"{sc.id}/step_0: S0 is {verdicts[0].status}, expected PASS ({verdicts[0].why})")
    last = verdicts[-1]
    if "INV-FUNC-001" in sc.breaks and last.status != "FAIL":
        out.append(f"{sc.id}: intent breaks INV-FUNC-001 but last step is {last.status} ({last.why})")
    if "INV-FUNC-001" not in sc.breaks and last.status == "FAIL":
        out.append(f"{sc.id}: last step is FAIL ({last.why}) but intent.breaks lacks INV-FUNC-001")
    if "INV-FUNC-001" in sc.preserves:
        for k, v in enumerate(verdicts):
            if v.status != "PASS":
                out.append(f"{sc.id}/step_{k}: intent preserves INV-FUNC-001 but evaluator says {v.status} ({v.why})")
    return out


# ---------------------------------------------------------------------------
# Test 5: egress CIDRs
# ---------------------------------------------------------------------------


def check_egress(sc: Sc) -> list[str]:
    out: list[str] = []
    if sc.model_file() is None:
        return out
    models = sc.models()
    try:
        s_addr, d_addr = endpoints(models[0])
        per_step: list[tuple[ipaddress.IPv4Network, list[Rule]]] = []
        for m in models:
            d = m.resources[d_addr]
            g0 = ref_list(d.attrs.get("vpc_security_group_ids"))[0]
            vpc = _vpc_cidr_of(m, m.resources[g0].attrs.get("vpc_id"))
            if vpc is None:
                raise UnsupportedForm("cannot resolve CIDR(VPC(D))")
            s_sgs = ref_list(m.resources[s_addr].attrs.get("vpc_security_group_ids"))
            rules = [r for g in s_sgs for r in rules_of(m, g, "egress")]
            per_step.append((vpc, rules))
    except (UnsupportedForm, KeyError, IndexError) as exc:
        return [f"{sc.id}: unsupported form: {exc!r}"]
    for k, (vpc, rules) in enumerate(per_step):
        for r in rules:
            if _partial(r.cidrs, vpc):  # type: ignore[arg-type]
                out.append(f"{sc.id}/step_{k}: egress {r.holder} CIDR {list(r.cidrs)} partly covers {vpc}")
    if sc.cls == "safe":
        for k in range(1, len(per_step)):
            vpc, rules = per_step[k]
            before = {r.key: r.signature for r in per_step[k - 1][1]}
            for r in rules:
                if before.get(r.key) == r.signature:
                    continue
                if r.permits_tcp(5432) and not _covers(r.cidrs, vpc) and not r.src_groups:  # type: ignore[arg-type]
                    out.append(
                        f"{sc.id}/step_{k}: safe scenario changed egress {r.holder} to {list(r.cidrs)} "
                        f"which permits TCP 5432 but does not cover {vpc}"
                    )
    return out


# ---------------------------------------------------------------------------
# Test 6: family mechanism
# ---------------------------------------------------------------------------


def check_mechanism(sc: Sc) -> list[str]:
    out: list[str] = []
    if sc.family not in ("F3", "F5", "F7") or sc.cls != "unsafe" or "INV-FUNC-001" not in sc.breaks:
        return out
    if sc.model_file() is None:
        return out
    s_addr, d_addr = endpoints(sc.model(0))  # type: ignore[arg-type]
    rows = sc.data["mutation_record"]
    on_sg = [r for r in rows if r["target_address"].startswith(("aws_security_group.", "aws_security_group_rule."))]
    on_endpoint = [r for r in rows if r["target_address"] in (s_addr, d_addr)]
    if not on_sg:
        out.append(f"{sc.id}: no mutation row on an aws_security_group or aws_security_group_rule")
    for r in on_endpoint:
        out.append(f"{sc.id}: mutation row on endpoint {r['target_address']} ({r['attribute']})")
    return out


# ---------------------------------------------------------------------------
# Test 10: SEC intent truth (lexical)
# ---------------------------------------------------------------------------


def sec_violations(model: Model) -> set[str]:
    out: set[str] = set()
    for r in all_rules(model):
        if r.direction != "ingress":
            continue
        world = "0.0.0.0/0" in r.cidrs or "::/0" in r.ipv6
        if world and r.permits_tcp(22):
            out.add("INV-SEC-001")
        if world and r.permits_tcp(5432):
            out.add("INV-SEC-002")
    for res in model.resources.values():
        if res.type == "aws_db_instance" and res.attrs.get("publicly_accessible") == "true":
            out.add("INV-SEC-003")
    return out


def check_sec_intent(sc: Sc) -> list[str]:
    out: list[str] = []
    if sc.model_file() is None:
        return out
    models = sc.models()
    target = sc.data["target"].get("invariant_id")
    expected0 = {target} if target else set()
    got0 = sec_violations(models[0])
    if got0 != expected0:
        out.append(f"{sc.id}/step_0: SEC violations {sorted(got0)} but expected {sorted(expected0)}")
    last = sec_violations(models[-1])
    expected = {b for b in sc.breaks if b.startswith("INV-SEC")}
    if last != expected:
        out.append(f"{sc.id}/last step: SEC violations {sorted(last)} but intent.breaks has {sorted(expected)}")
    return out


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

_CACHE: dict[str, list[Sc]] = {}


def scenarios() -> list[Sc]:
    if "all" not in _CACHE:
        _CACHE["all"] = load_all()
        if not any(s == "test" for s, _ in scenario_roots()):
            print(f"\n[round4] {PRIVATE_ENV} is not set to an existing directory: "
                  "private test-split checks are skipped.", file=sys.stderr)
    return _CACHE["all"]


def _collect(fn: Callable[[Sc], list[str]]) -> list[str]:
    out: list[str] = []
    for sc in scenarios():
        out.extend(fn(sc))
    return out


class TestD4bReviewRound4(unittest.TestCase):
    def assertNoViolations(self, found: list[str], label: str) -> None:
        self.assertGreater(len(scenarios()), 0, "no scenarios loaded")
        self.assertEqual(found, [], f"{label}: {len(found)} violation(s), first 10: {found[:10]}")

    def test_01_no_empty_vpc_security_group_ids(self) -> None:
        """Rule: no step contains vpc_security_group_ids = [] (registry 6.4 row 2: UNSUPPORTED)."""
        self.assertNoViolations(_collect(check_empty_sg_list), "empty vpc_security_group_ids")

    def test_02_no_mixed_group(self) -> None:
        """Rule: no group holds inline blocks (or explicit empty) and is also a rule target (registry 2.6, C-84)."""
        self.assertNoViolations(_collect(check_mixed), "MIXED groups")

    def test_03_no_retained_inline_group(self) -> None:
        """Rule: a direction that is blocks in step k-1 is not absent in step k (registry 2.6, A10)."""
        self.assertNoViolations(_collect(check_retained_inline), "RETAINED-INLINE groups")

    def test_04_no_nonlocal_route_inside_vpc(self) -> None:
        """Rule: no non-local route has a destination inside the VPC CIDR (M3)."""
        self.assertNoViolations(_collect(check_nonlocal_routes), "non-local routes in VPC CIDR")

    def test_05_egress_cidrs(self) -> None:
        """Rule: no egress CIDR partly covers CIDR(VPC(D)); safe changes keep full cover or avoid 5432."""
        self.assertNoViolations(_collect(check_egress), "egress CIDRs")

    def test_06_family_mechanism(self) -> None:
        """Rule: F3, F5, F7 FUNC breaks run through a group or rule, with no row on S or D."""
        self.assertNoViolations(_collect(check_mechanism), "family mechanism")

    def test_07_intent_truth(self) -> None:
        """Rule: INV-FUNC-001 in breaks <=> FAIL on the last step; in preserves => PASS on every step."""
        self.assertNoViolations(_collect(check_intent_truth), "intent truth")

    def test_08_coverage_both_tiers(self) -> None:
        """Rule: F3, F4, F5, F7, F8 unsafe break INV-FUNC-001 in both tiers; F1 unsafe covers all three SEC."""
        scs = scenarios()
        self.assertGreater(len(scs), 0)
        missing = []
        for tier in ("controlled", "real_world"):
            for fam in ("F3", "F4", "F5", "F7", "F8"):
                n = sum(1 for s in scs if s.tier == tier and s.family == fam and s.cls == "unsafe"
                        and "INV-FUNC-001" in s.breaks)
                if n == 0:
                    missing.append(f"{tier}/{fam}: no unsafe scenario breaks INV-FUNC-001")
            f1 = {b for s in scs if s.tier == tier and s.family == "F1" and s.cls == "unsafe" for b in s.breaks}
            for inv in ("INV-SEC-001", "INV-SEC-002", "INV-SEC-003"):
                if inv not in f1:
                    missing.append(f"{tier}/F1: no unsafe scenario breaks {inv}")
        self.assertEqual(missing, [], f"coverage gaps: {missing}")

    def test_09_operator_names_agree_with_docs(self) -> None:
        """Rule: every D4a operator name in code is in docs/D4_OPERATORS.md and vice versa (computed)."""
        import operators  # type: ignore[import-not-found]

        code = {op.name for op in operators.CATALOGUE}
        text = (REPO_ROOT / "docs" / "D4_OPERATORS.md").read_text(encoding="utf-8")
        # Names in the rename/removal section are history, not live operators.
        live = re.split(r"^## Renames and removals", text, maxsplit=1, flags=re.MULTILINE)[0]
        doc = {m for m in re.findall(r"\bop_f[1-8]_[a-z0-9_]+", live)}
        self.assertEqual(sorted(code - doc), [], "operators in code but not in docs")
        self.assertEqual(sorted(doc - code), [], "operators in docs but not in code")

    def test_11_d5_carryover_lists_break_mechanisms(self) -> None:
        """Rule (extra): docs/D5_CARRYOVER.md lists every INV-FUNC-001-breaking operator with the mechanism and row from code."""
        import operators  # type: ignore[import-not-found]

        text = (REPO_ROOT / "docs" / "D5_CARRYOVER.md").read_text(encoding="utf-8")
        listed = {name: (mech, int(row)) for name, mech, row in
                  re.findall(r"^\| `(op_f[1-8]_[a-z0-9_]+)` \| (B[1-5]) \| (\d+) \|", text, flags=re.MULTILINE)}
        expected = {op.name: (op.mechanism, op.designed_row) for op in operators.CATALOGUE
                    if "INV-FUNC-001" in op.intent_breaks}
        self.assertEqual(listed, expected)

    def test_10_sec_intent_truth(self) -> None:
        """Rule (extra): lexical SEC state at S0 and the last step matches the repair target and intent.breaks."""
        self.assertNoViolations(_collect(check_sec_intent), "SEC intent truth")


if __name__ == "__main__":
    unittest.main()
