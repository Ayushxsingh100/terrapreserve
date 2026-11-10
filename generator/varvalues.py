"""Variable values for the scenario record (D5-10, rule ``vv-3``; supersedes ``vv-2`` of D5-07 and ``vv-1`` of D5-01).

Rule vv-3 (``docs/D5_DECISIONS.md`` D5-10) is vv-2 (below) plus three changes: (1) a variable whose declared
default was rejected at plan time is valued like a variable without a default, with the reason recorded; (2) every
kind has a fixed, ordered candidate list per set (``KIND_CANDIDATES``; the first is the vv-2 value), and the
candidate index taken for each variable in each set is recorded in ``variable_values_candidates``; (3) a ``conflict``
or ``unresolved`` variable gets no value (its scenario is excluded under D5-09 if it cannot plan). Which defaults are
overridden and which indices are taken is decided by the offline plan search of ``tools/search_vv3.py``; its result
(per split: ``generator/vv3/dev.json``, ``$TERRAPRESERVE_PRIVATE/vv3_test.json``) is an input of ``compute``, which
also copies the scenario's ``excluded_from_v1`` (D5-09) from it.

The text below describes vv-2, which vv-3 keeps whole.

Registry v1.0 section 2.1 evaluates a configuration "together with the scenario's variable values", and
section 2.2 resolves an input variable to its "provided value, else declared default". Every variable that is
declared **without** a default (the D5-08 data-source variables ``tp_ds_*`` included) gets two values, a
primary (``variable_values``) and an alternate (``variable_values_alt``), chosen by the fixed, versioned rule
``vv-2``. Variables with a default are not listed (the default applies). D5-06 labels every scenario under both
sets; a scenario whose labels differ depends on an invented value.

Rule vv-2 (``docs/D5_DECISIONS.md`` D5-07):

1. The kind of every leaf of a variable's value is decided in this order and recorded with its evidence:
   the declared ``type`` (recursively; an ``object`` gets every required attribute); for a ``string`` leaf (or
   an untyped or ``any`` part), a secret name or ``sensitive = true`` gives ``secret``; for a D5-08 variable,
   the data source's attribute (``DS_KINDS``); otherwise the attributes the leaf flows into, directly or
   through a ``local``, by ``ATTR_KINDS`` (a use inside a string template with other text is a ``string`` use).
   No table attribute gives ``string``; two different table kinds give ``conflict`` (no value).
   ``number`` gives 1 / 2, ``bool`` false / true.
2. Collections: a collection the configuration never indexes is empty-able, giving ``[]`` / ``{}`` (primary)
   and one element (alternate). One that it indexes (``x[i]``, ``tolist(x)[i]``, ``element(x, i)``) is not
   empty-able and gets ``NON_EMPTY_LENGTH`` elements in both sets (more if a constant index needs it). A map
   indexed by constant keys gets those keys; a map indexed by a computed key is ``unresolved``.
   An untyped (or ``any``) variable takes its structure from its uses.
3. Validation blocks are checked by Terraform itself (the variable blocks planned in an empty directory, no
   provider, no network). When the value is rejected, the next candidate of the fixed per-kind list is tried:
   the kind's value, then the string literals the validation names (``contains([...], var.x)``,
   ``var.x == "..."``) in their written order. The alternate takes the first accepted candidate that differs
   from the primary. If none is accepted, the variable is ``unresolved`` with the reason.
4. The two sets differ wherever the kind allows; the exceptions are recorded as ``same_in_both_sets``.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import hcl_lex  # noqa: E402
from realworld import data_vars, modread  # noqa: E402

RULE = "vv-3"
SUPERSEDED_RULES = ("vv-1", "vv-2")  # D5-01 (D5a), D5-07 (D5a-2); described in docs/D5_DECISIONS.md
NON_EMPTY_LENGTH = 3
_SECRET_NAME = re.compile(r"password|secret|token", re.IGNORECASE)

# D5-10: (primary candidates, alternate candidates) by kind, fixed in advance; the first of each is the D5-07
# (vv-2) value. At most 4 per kind per set; never chosen for a single scenario.
KIND_CANDIDATES: dict[str, tuple[tuple[Any, ...], tuple[Any, ...]]] = {
    "string": (("tp-primary", "tpprimary", "tp-primary-1", "tpp"), ("tp-alt", "tpalt", "tp-alt-1", "tpa")),
    "ipv4_cidr": (("10.201.0.0/16", "10.201.1.0/24", "172.20.0.0/16", "10.201.0.0/20"),
                  ("192.168.77.0/24", "192.168.78.0/24", "172.21.0.0/16", "192.168.64.0/20")),
    "az": (("us-east-1a", "us-east-1b", "us-east-1c"), ("us-east-1b", "us-east-1c", "us-east-1a")),
    "number": ((1, 2, 3, 10), (2, 3, 4, 20)),
    "vpc_id": (("vpc-0201201201201201a", "vpc-02012012", "vpc-0123456789abcdef0"),
               ("vpc-0777777777777777b", "vpc-07777777", "vpc-0fedcba9876543210")),
    "subnet_id": (("subnet-0201201201201201a", "subnet-02012012", "subnet-0123456789abcdef0"),
                  ("subnet-0777777777777777b", "subnet-07777777", "subnet-0fedcba9876543210")),
    "sg_id": (("sg-0201201201201201a", "sg-02012012", "sg-0123456789abcdef0"),
              ("sg-0777777777777777b", "sg-07777777", "sg-0fedcba9876543210")),
    "ami": (("ami-0201201201201201a", "ami-02012012", "ami-0123456789abcdef0"),
            ("ami-0777777777777777b", "ami-07777777", "ami-0fedcba9876543210")),
    "secret": (("tp-secret-primary", "tp-secret-primary-long"), ("tp-secret-alt", "tp-secret-alt-long")),
    "bool": ((False,), (True,)),
    "region": (("us-east-1",), ("us-east-1",)),  # the provider pin, the same in both sets (recorded)
    "instance_type": (("t3.micro",), ("t3.small",)),
    "key_name": (("tp-key-primary",), ("tp-key-alt",)),
    "ipv6_cidr": (("fd00:201::/64",), ("fd00:77::/64",)),
}
# (primary, alternate) by kind: the D5-07 table (candidate 0).
KIND_VALUES: dict[str, tuple[Any, Any]] = {k: (p[0], a[0]) for k, (p, a) in KIND_CANDIDATES.items()}
OVERRIDE_PREFIX = "declared default rejected: "
SEARCH_DEV = REPO_ROOT / "generator" / "vv3" / "dev.json"
SEARCH_TEST_NAME = "vv3_test.json"
_SEARCH_CACHE: dict[str, dict[str, Any]] = {}


def candidate(kind: str, which: int, idx: int) -> Any:
    """Candidate ``idx`` of ``kind`` in set ``which`` (0 primary, 1 alternate); past the end, the last one."""
    lst = KIND_CANDIDATES[kind][which]
    return lst[min(idx, len(lst) - 1)]


def candidate_count(kt: Any) -> int:
    """Number of candidates of a variable: the longest list among its leaf kinds (1 with no leaf)."""
    return max([len(KIND_CANDIDATES[k][0]) for k in _all_leaves(kt)] + [1])


def search_record(scenario_id: str, split: str) -> dict[str, Any] | None:
    """The vv-3 search result of one scenario (None when the split has no search file yet)."""
    if split == "dev":
        path: Path | None = SEARCH_DEV
    else:
        priv = os.environ.get("TERRAPRESERVE_PRIVATE")
        path = Path(priv) / SEARCH_TEST_NAME if priv else None
    if path is None or not path.is_file():
        return None
    key = str(path)
    if key not in _SEARCH_CACHE:
        _SEARCH_CACHE[key] = json.loads(path.read_text(encoding="utf-8"))["scenarios"]
    return _SEARCH_CACHE[key].get(scenario_id)
# Attribute the value flows into -> kind (the D5-07 table, by argument name in the AWS provider 6.53.0).
ATTR_KINDS: dict[str, str] = {
    "cidr_block": "ipv4_cidr", "cidr_blocks": "ipv4_cidr", "destination_cidr_block": "ipv4_cidr",
    "cidr_ipv4": "ipv4_cidr",
    "ipv6_cidr_blocks": "ipv6_cidr", "ipv6_cidr_block": "ipv6_cidr", "destination_ipv6_cidr_block": "ipv6_cidr",
    "cidr_ipv6": "ipv6_cidr",
    "vpc_id": "vpc_id",
    "subnet_id": "subnet_id", "subnet_ids": "subnet_id",
    "vpc_security_group_ids": "sg_id", "security_group_id": "sg_id", "security_group_ids": "sg_id",
    "source_security_group_id": "sg_id", "security_groups": "sg_id", "referenced_security_group_id": "sg_id",
    "ami": "ami",
    "availability_zone": "az", "availability_zones": "az",
    "region": "region",
    "instance_type": "instance_type",
    "key_name": "key_name",
}
# D5-08 data-source attribute -> kind of its leaves (D5-07 table applied to the data source's schema).
DS_KINDS: dict[tuple[str, str], str] = {
    ("aws_ami", "id"): "ami", ("aws_ami", "image_id"): "ami",
    ("aws_availability_zones", "names"): "az", ("aws_availability_zones", "id"): "region",
    ("aws_vpc", "id"): "vpc_id", ("aws_vpc", "cidr_block"): "ipv4_cidr",
    ("aws_vpcs", "ids"): "vpc_id",
    ("aws_subnet", "id"): "subnet_id", ("aws_subnet", "vpc_id"): "vpc_id", ("aws_subnet", "cidr_block"): "ipv4_cidr",
    ("aws_subnet", "availability_zone"): "az",
    ("aws_subnets", "ids"): "subnet_id",
    ("aws_security_group", "id"): "sg_id", ("aws_security_group", "vpc_id"): "vpc_id",
    ("aws_region", "name"): "region", ("aws_region", "id"): "region", ("aws_region", "region"): "region",
    ("aws_key_pair", "key_name"): "key_name",
    ("aws_ip_ranges", "cidr_blocks"): "ipv4_cidr", ("aws_ip_ranges", "ipv6_cidr_blocks"): "ipv6_cidr",
    ("aws_instance", "ami"): "ami", ("aws_instance", "subnet_id"): "subnet_id",
    ("aws_instance", "instance_type"): "instance_type", ("aws_instance", "availability_zone"): "az",
    ("aws_instance", "key_name"): "key_name", ("aws_instance", "vpc_security_group_ids"): "sg_id",
}
SAME_REGION = "kind region: the provider pin us-east-1 in both sets"
SAME_EMPTY_OBJECT = "object with no attributes used"
SAME_VALIDATION = "the validation admits only one candidate"
_INDEX_FUNCS = frozenset({"tolist", "toset", "sort", "distinct", "compact", "reverse", "flatten", "tomap"})
_MAP_TYPES = ("map",)


class _NoValue(Exception):
    """vv-2 gives no value; the message is the reason recorded in ``variable_values_unresolved``."""

    def __init__(self, reason: str, status: str = "unresolved") -> None:
        super().__init__(reason)
        self.status = status


# ---------------------------------------------------------------------------
# Type expressions
# ---------------------------------------------------------------------------


def _toks(tokens: list) -> list:
    return [t for t in tokens if t.kind != "NEWLINE"]


def _parse_type(toks: list, i: int = 0) -> tuple[tuple, int]:
    """Parse a Terraform type constraint. Returns (node, next index).

    Nodes: ("string",) ("number",) ("bool",) ("any",) ("list", e) ("set", e) ("map", e) ("tuple", [e...])
    ("object", {name: (optional, node)}).
    """
    t = toks[i]
    if t.kind == "STRING":  # legacy quoted types: "string", "list", "map"
        return (t.text,) if t.text in ("string", "number", "bool") else (t.text, ("any",)), i + 1
    if t.kind != "IDENT":
        raise _NoValue("type expression not understood")
    name = t.text
    nxt = toks[i + 1] if i + 1 < len(toks) else None
    has_args = nxt is not None and nxt.kind == "PUNCT" and nxt.text == "("
    if name in ("string", "number", "bool", "any"):
        return (name,), i + 1
    if name in ("list", "set", "map"):
        if not has_args:
            return (name, ("any",)), i + 1
        elem, j = _parse_type(toks, i + 2)
        return (name, elem), j + 1  # skip ")"
    if name == "tuple":
        j = i + 3  # tuple ( [
        elems = []
        while not (toks[j].kind == "PUNCT" and toks[j].text == "]"):
            if toks[j].kind == "PUNCT" and toks[j].text == ",":
                j += 1
                continue
            e, j = _parse_type(toks, j)
            elems.append(e)
        return ("tuple", elems), j + 2  # skip "] )"
    if name == "object":
        j = i + 3  # object ( {
        attrs: dict[str, tuple[bool, tuple]] = {}
        while not (toks[j].kind == "PUNCT" and toks[j].text == "}"):
            if toks[j].kind == "PUNCT" and toks[j].text == ",":
                j += 1
                continue
            aname = toks[j].text
            j += 2  # name =
            optional = toks[j].kind == "IDENT" and toks[j].text == "optional"
            if optional:
                inner, k = _parse_type(toks, j + 2)  # optional ( type [, default] )
                depth = 1
                while depth:
                    if toks[k].kind == "PUNCT" and toks[k].text in "([{":
                        depth += 1
                    elif toks[k].kind == "PUNCT" and toks[k].text in ")]}":
                        depth -= 1
                    k += 1
                attrs[aname] = (True, inner)
                j = k
            else:
                node, j = _parse_type(toks, j)
                attrs[aname] = (False, node)
        return ("object", attrs), j + 2  # skip "} )"
    raise _NoValue(f"type {name!r} not understood")


def _type_text(tokens: list) -> str:
    return "".join(t.text if t.kind != "STRING" else f'"{t.text}"' for t in _toks(tokens))


# ---------------------------------------------------------------------------
# Uses of variables
# ---------------------------------------------------------------------------

# A use: (path parts, attribute name or None, where, mode, fn_indexed)
#   path parts: ".name", "[N]" (constant index), '["k"]' (constant key), "[*]" (computed index),
#               "[each]" (iteration: for_each/each.value, dynamic blocks, splat)
#   mode: "direct" or "template" (inside a string template with other text)


def _path_after(toks: list, k: int) -> tuple[list[str], int]:
    parts: list[str] = []
    n = len(toks)
    while k < n:
        t = toks[k]
        if t.kind == "PUNCT" and t.text == "." and k + 1 < n and toks[k + 1].kind in ("IDENT", "NUMBER"):
            parts.append("." + toks[k + 1].text)
            k += 2
        elif t.kind == "PUNCT" and t.text == "." and k + 1 < n and toks[k + 1].text == "*":
            parts.append("[each]")
            k += 2
        elif t.kind == "PUNCT" and t.text == "[":
            j = modread._match_close(toks, k)
            if j < 0:
                break
            inner = toks[k + 1:j]
            if len(inner) == 1 and inner[0].kind == "PUNCT" and inner[0].text == "*":
                parts.append("[each]")
            elif len(inner) == 1 and inner[0].kind == "NUMBER" and inner[0].text.isdigit():
                parts.append(f"[{inner[0].text}]")
            elif len(inner) == 1 and inner[0].kind == "STRING" and "${" not in inner[0].text:
                parts.append(f'["{inner[0].text}"]')
            else:
                parts.append("[*]")
            k = j + 1
        else:
            break
    return parts, k


def _fn_indexed(toks: list, start: int, end: int) -> bool:
    """Is the traversal toks[start:end] indexed through a function: f(x)[i] (f in _INDEX_FUNCS) or element(x, i)?"""
    if start >= 2 and toks[start - 1].text == "(" and toks[start - 2].kind == "IDENT":
        fname = toks[start - 2].text
        if fname == "element":
            return True
        if fname in _INDEX_FUNCS and end < len(toks) and toks[end].text == ")" and end + 1 < len(toks) \
                and toks[end + 1].text == "[":
            return True
    return False


_STR_REF = re.compile(r"(?<![\w.\-])(var|local|each)\.([A-Za-z_][A-Za-z0-9_\-]*)"
                      r"((?:\.[A-Za-z_0-9][A-Za-z0-9_\-]*|\[[^\]\[]*\])*)")


def _str_parts(raw: str) -> list[str]:
    out = []
    for p in re.findall(r"\.[A-Za-z_0-9][A-Za-z0-9_\-]*|\[[^\]\[]*\]", raw):
        if p.startswith("["):
            inner = p[1:-1].strip()
            out.append("[each]" if inner == "*" else (f"[{inner}]" if inner.isdigit() else
                                                       (f'["{inner[1:-1]}"]' if re.fullmatch(r'"[^"$]*"', inner)
                                                        else "[*]")))
        else:
            out.append(p)
    return out


def _raw_refs(tokens: list) -> list[tuple[str, str, list[str], str, bool]]:
    """(root, name, path, mode, fn_indexed) for var./local./each. references in an expression."""
    toks = _toks(tokens)
    out = []
    for k, t in enumerate(toks):
        if t.kind == "IDENT" and t.text in ("var", "local", "each") and k + 2 < len(toks) \
                and toks[k + 1].text == "." and toks[k + 2].kind == "IDENT" \
                and not (k > 0 and toks[k - 1].text == "."):
            parts, end = _path_after(toks, k + 3)
            out.append((t.text, toks[k + 2].text, parts, "direct", _fn_indexed(toks, k, end)))
        elif t.kind == "STRING" and ("${" in t.text or "%{" in t.text):
            whole = re.fullmatch(r"\$\{\s*(.*?)\s*\}", t.text, re.S)
            sub = hcl_lex.tokenize(whole.group(1)) if whole and t.text.count("${") == 1 else None
            if sub is not None and not any(x.kind == "PUNCT" and x.text in "+-*/%?:<>=!&|" for x in _toks(sub)):
                out.extend(_raw_refs(sub))  # "${var.x}" alone is a direct use
                continue
            for m in _STR_REF.finditer(t.text):
                out.append((m.group(1), m.group(2), _str_parts(m.group(3)), "template", False))
    return out


class _Uses:
    """Every use of every variable in a module, through locals and iteration bindings."""

    def __init__(self) -> None:
        self.by_var: dict[str, list[tuple[tuple[str, ...], str | None, str, str, bool]]] = {}

    def add(self, var: str, path: list[str], attr: str | None, where: str, mode: str, fn_idx: bool) -> None:
        self.by_var.setdefault(var, []).append((tuple(path), attr, where, mode, fn_idx))


def _resolve(root: str, name: str, path: list[str], mod: modread.Module, env: dict[str, tuple[str, list[str]]],
             depth: int = 0) -> list[tuple[str, list[str], bool]]:
    """(variable, path, exact) pairs a reference stands for. ``exact``: the reference is the variable's value."""
    if root == "var":
        return [(name, path, True)]
    if root == "each":
        if "each" in env and name == "value":
            v, base = env["each"]
            return [(v, base + path, True)]
        return []
    if root == "local" and name in mod.locals and depth < 8:
        expr = mod.locals[name]
        refs = _raw_refs(expr)
        exact_ref = None
        toks = _toks(expr)
        if refs and toks and toks[0].kind == "IDENT" and toks[0].text in ("var", "local"):
            parts, end = _path_after(toks, 3) if len(toks) > 2 else ([], len(toks))
            if end == len(toks):
                exact_ref = refs[0]
        out = []
        for r in refs:
            rpath = r[2] + path if r is exact_ref else r[2]
            for v, p, ex in _resolve(r[0], r[1], rpath, mod, env, depth + 1):
                out.append((v, p, ex and r is exact_ref))
        return out
    return []


def _binding(expr: list, mod: modread.Module, env: dict) -> tuple[str, list[str]] | None:
    """The variable a ``for_each`` iterates over, when the expression is exactly it (or toset/tolist of it)."""
    toks = _toks(expr)
    if len(toks) >= 4 and toks[0].kind == "IDENT" and toks[0].text in ("toset", "tolist", "tomap") \
            and toks[1].text == "(" and toks[-1].text == ")":
        toks = toks[2:-1]
    if len(toks) >= 3 and toks[0].kind == "IDENT" and toks[0].text in ("var", "local", "each") \
            and toks[1].text == "." and toks[2].kind == "IDENT":
        parts, end = _path_after(toks, 3)
        if end == len(toks):
            res = _resolve(toks[0].text, toks[2].text, parts, mod, env)
            if len(res) == 1 and res[0][2]:
                return res[0][0], res[0][1] + ["[each]"]
    return None


def _collect_block(blk: modread.Block, mod: modread.Module, uses: _Uses, where: str, env: dict) -> None:
    env = dict(env)
    if "for_each" in blk.attrs:
        b = _binding(blk.attrs["for_each"], mod, env)
        if b is not None:
            env["each"] = b
        else:
            env.pop("each", None)
    for aname, toks in blk.attrs.items():
        for root, name, path, mode, fn_idx in _raw_refs(toks):
            for v, p, _ex in _resolve(root, name, path, mod, env):
                uses.add(v, p, aname, f"{where}.{aname}", mode, fn_idx)
    for child in blk.children:
        if child.kind == "dynamic" and child.labels:
            iterator = child.labels[0]
            if "iterator" in child.attrs and _toks(child.attrs["iterator"]):
                iterator = _toks(child.attrs["iterator"])[0].text
            denv = dict(env)
            b = _binding(child.attrs.get("for_each", []), mod, env)
            for root, name, path, mode, fn_idx in _raw_refs(child.attrs.get("for_each", [])):
                for v, p, _ex in _resolve(root, name, path, mod, env):
                    uses.add(v, p, "for_each", f"{where}.dynamic.{child.labels[0]}.for_each", mode, fn_idx)
            for content in child.children:
                for aname, toks in content.attrs.items():
                    for root, name, path, mode, fn_idx in _raw_refs(toks):
                        for v, p, _ex in _resolve(root, name, path, mod, denv):
                            uses.add(v, p, aname, f"{where}.{child.labels[0]}.{aname}", mode, fn_idx)
                    # iterator.value.<path>
                    for k, t in enumerate(_toks(toks)):
                        tt = _toks(toks)
                        if b is not None and t.kind == "IDENT" and t.text == iterator and k + 2 < len(tt) \
                                and tt[k + 1].text == "." and tt[k + 2].kind == "IDENT" and tt[k + 2].text == "value" \
                                and not (k > 0 and tt[k - 1].text == "."):
                            parts, _e = _path_after(tt, k + 3)
                            uses.add(b[0], b[1] + parts, aname, f"{where}.{child.labels[0]}.{aname}", "direct", False)
                    for t in _toks(toks):
                        if b is not None and t.kind == "STRING" and f"{iterator}.value" in t.text:
                            for m in re.finditer(rf"(?<![\w.\-]){re.escape(iterator)}\.value"
                                                 r"((?:\.[A-Za-z_0-9][A-Za-z0-9_\-]*|\[[^\]\[]*\])*)", t.text):
                                uses.add(b[0], b[1] + _str_parts(m.group(1)), aname,
                                         f"{where}.{child.labels[0]}.{aname}", "template", False)
                for sub in content.children:
                    _collect_block(sub, mod, uses, f"{where}.{child.labels[0]}.{sub.kind}", denv)
        else:
            _collect_block(child, mod, uses, f"{where}.{child.kind}", env)


def collect_uses(mod: modread.Module, uses: _Uses) -> None:
    for blk in mod.blocks:
        if blk.kind == "resource" and len(blk.labels) == 2:
            _collect_block(blk, mod, uses, blk.addr, {})
        elif blk.kind == "data" and len(blk.labels) == 2:
            _collect_block(blk, mod, uses, f"data.{blk.labels[0]}.{blk.labels[1]}", {})
        elif blk.kind == "output" and blk.labels:
            for root, name, path, mode, fn_idx in _raw_refs(blk.attrs.get("value", [])):
                for v, p, _ex in _resolve(root, name, path, mod, {}):
                    uses.add(v, p, None, f"output.{blk.labels[0]}", mode, fn_idx)
        elif blk.kind == "module" and blk.labels:
            _collect_block(blk, mod, uses, f"module.{blk.labels[0]}", {})


# ---------------------------------------------------------------------------
# Building values
# ---------------------------------------------------------------------------


def _norm(part: str) -> str:
    return "[]" if part.startswith("[") else part


def _is_index(part: str) -> bool:
    return part.startswith("[") and part != "[each]"


class _Var:
    def __init__(self, name: str, blk: modread.Block, uses: list, ds: tuple[str, str] | None) -> None:
        self.name = name
        self.blk = blk
        self.uses = uses
        self.ds = ds
        sensitive = "sensitive" in blk.attrs and _type_text(blk.attrs["sensitive"]) == "true"
        self.secret = "sensitive" if sensitive else ("name" if _SECRET_NAME.search(name) else None)
        self.evidence: set[str] = set()

    # uses whose normalised path equals, or covers (only element markers left), the leaf path
    def leaf_uses(self, path: tuple[str, ...]) -> list:
        npath = tuple(_norm(p) for p in path)
        out = []
        for upath, attr, where, mode, fn_idx in self.uses:
            nu = tuple(_norm(p) for p in upath)
            if nu == npath or (len(nu) < len(npath) and nu == npath[:len(nu)]
                               and all(p == "[]" for p in npath[len(nu):])):
                out.append((upath, attr, where, mode, fn_idx))
        return out

    def below(self, path: tuple[str, ...]) -> list[tuple[str, ...]]:
        """Use paths strictly below ``path`` (normalised), as remainders (raw parts)."""
        npath = tuple(_norm(p) for p in path)
        out = []
        for upath, *_rest in self.uses:
            if len(upath) > len(npath) and tuple(_norm(p) for p in upath[:len(npath)]) == npath:
                out.append(upath[len(npath):])
        return out

    def fn_indexed_at(self, path: tuple[str, ...]) -> bool:
        npath = tuple(_norm(p) for p in path)
        return any(fn and tuple(_norm(p) for p in up) == npath for up, _a, _w, _m, fn in self.uses)


def _infer(var: _Var, path: tuple[str, ...]) -> tuple:
    """Structure of an untyped (or ``any``) part from its uses."""
    rest = var.below(path)
    if any(r[0].startswith("[") for r in rest):
        return ("list", ("any",))
    attrs = sorted({r[0][1:] for r in rest if r[0].startswith(".")})
    if attrs:
        return ("object", {a: (False, ("any",)) for a in attrs})
    return ("string",)


def _leaf_kind(var: _Var, path: tuple[str, ...], base: str) -> str:
    if base == "number" or base == "bool":
        var.evidence.add(f"declared_type:{base}" if "type" in var.blk.attrs else f"inferred:{base}")
        return base
    if var.secret:
        var.evidence.add(f"secret:{var.secret}")
        return "secret"
    if var.ds is not None:
        top = next((p[1:] for p in path if p.startswith(".")), None)
        if top is not None and (var.ds[0], top) in DS_KINDS:
            var.evidence.add(f"data_source:{var.ds[0]}.{top}")
            return DS_KINDS[(var.ds[0], top)]
    kinds: dict[str, list[str]] = {}
    for _up, attr, where, mode, _fn in var.leaf_uses(path):
        if mode == "direct" and attr in ATTR_KINDS:
            kinds.setdefault(ATTR_KINDS[attr], []).append(where)
    if len(kinds) > 1:
        detail = "; ".join(f"{k} by usage:{', '.join(sorted(set(w)))}" for k, w in sorted(kinds.items()))
        raise _NoValue(f"conflict at {''.join(path) or '(value)'}: {detail}", "conflict")
    if kinds:
        (kind, wheres), = kinds.items()
        var.evidence.update(f"usage:{w}" for w in wheres)
        return kind
    var.evidence.add(f"no table attribute reached at {''.join(path) or '(value)'}")
    return "string"


def _build(var: _Var, node: tuple, path: tuple[str, ...], ip: int = 0, ia: int = 0) -> tuple[Any, Any, Any]:
    """(kind tree, primary, alternate) for the part of ``var`` at ``path`` with type ``node``; ``ip`` and ``ia``
    are the candidate indices of the two sets (D5-10)."""
    kind = node[0]
    if kind == "any":
        node = _infer(var, path)
        kind = node[0]
        if node == ("string",) and var.below(path):
            raise _NoValue(f"type any at {''.join(path) or '(value)'}: the uses do not decide a structure")
    if kind in ("string", "number", "bool"):
        k = _leaf_kind(var, path, kind)
        return k, candidate(k, 0, ip), candidate(k, 1, ia)
    if kind in ("list", "set"):
        kt, pe, ae = _build(var, node[1], path + ("[]",), ip, ia)
        consts = [int(r[0][1:-1]) for r in var.below(path) if r[0][1:-1].isdigit()]
        indexed = var.fn_indexed_at(path) or any(_is_index(r[0]) for r in var.below(path))
        if not indexed:
            return {kind: kt, "length": "empty-able"}, [], [ae]
        n = max([NON_EMPTY_LENGTH] + [c + 1 for c in consts])
        return {kind: kt, "length": n}, [pe] * n, [ae] * n
    if kind == "tuple":
        parts = [_build(var, e, path + (f"[{i}]",), ip, ia) for i, e in enumerate(node[1])]
        return {"tuple": [p[0] for p in parts]}, [p[1] for p in parts], [p[2] for p in parts]
    if kind == "map":
        kt, pe, ae = _build(var, node[1], path + ("[]",), ip, ia)
        below = var.below(path)
        keys = sorted({r[0][2:-2] for r in below if r[0].startswith('["')}
                      | {r[0][1:] for r in below if r[0].startswith(".")})
        if any(r[0] == "[*]" for r in below) or var.fn_indexed_at(path):
            raise _NoValue(f"map at {''.join(path) or '(value)'} is indexed by a computed key")
        if keys:
            return {"map": kt, "keys": keys}, {k: pe for k in keys}, {k: ae for k in keys}
        return {"map": kt, "keys": "empty-able"}, {}, {KIND_VALUES["string"][1]: ae}
    if kind == "object":
        kts, pv, av = {}, {}, {}
        for aname, (optional, anode) in sorted(node[1].items()):
            if optional:
                continue
            kts[aname], pv[aname], av[aname] = _build(var, anode, path + (f".{aname}",), ip, ia)
        return {"object": kts}, pv, av
    raise _NoValue(f"type {kind!r} not covered by vv-3")


def _all_leaves(kt: Any) -> list[str]:
    if isinstance(kt, str):
        return [kt]
    out: list[str] = []
    for key in ("list", "set", "map"):
        if key in kt:
            out += _all_leaves(kt[key])
    for v in kt.get("object", {}).values():
        out += _all_leaves(v)
    for v in kt.get("tuple", []):
        out += _all_leaves(v)
    return out


# ---------------------------------------------------------------------------
# Validation check by Terraform
# ---------------------------------------------------------------------------


def variable_block_text(text: str, name: str) -> str | None:
    """The source text of the top-level ``variable "<name>" { ... }`` block in ``text``."""
    spans = [(t, s, e) for t, s, e in hcl_lex.tokenize_spans(text) if t.kind != "NEWLINE"]
    depth = 0
    for k, (t, s, _e) in enumerate(spans):
        if t.kind == "PUNCT" and t.text == "{":
            depth += 1
        elif t.kind == "PUNCT" and t.text == "}":
            depth -= 1
        if depth == 0 and t.kind == "IDENT" and t.text == "variable" and k + 2 < len(spans) \
                and spans[k + 1][0].kind == "STRING" and spans[k + 1][0].text == name \
                and spans[k + 2][0].kind == "PUNCT" and spans[k + 2][0].text == "{":
            d = 0
            for t2, _s2, e2 in spans[k + 2:]:
                if t2.kind == "PUNCT" and t2.text == "{":
                    d += 1
                elif t2.kind == "PUNCT" and t2.text == "}":
                    d -= 1
                    if d == 0:
                        return text[s:e2]
    return None


_VALIDATION_CACHE: dict[str, tuple[str, str]] = {}


def validation_check(blocks: dict[str, str], values: dict[str, Any]) -> tuple[str, str]:
    """Plan the given ``variable`` blocks with ``values`` in an empty directory (no provider, no network).

    Returns ("accepted", "") when Terraform accepts the values, ("rejected", first error) when it reports
    "Invalid value for variable", and ("unchecked", first error) for any other error.
    """
    key = hashlib.sha256(json.dumps([sorted(blocks.items()), values], sort_keys=True).encode()).hexdigest()
    if key in _VALIDATION_CACHE:
        return _VALIDATION_CACHE[key]
    terraform = shutil.which("terraform")
    if terraform is None:
        raise RuntimeError("terraform is required to check validation blocks for rule vv-3")
    with tempfile.TemporaryDirectory(prefix="tp-vv2-") as tmp:
        Path(tmp, "variables.tf").write_text("\n\n".join(blocks[n] for n in sorted(blocks)) + "\n",
                                             encoding="utf-8", newline="\n")
        Path(tmp, "values.tfvars.json").write_text(json.dumps(values, sort_keys=True), encoding="utf-8",
                                                   newline="\n")
        env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}
        env.update({"TF_IN_AUTOMATION": "1", "TF_INPUT": "0", "CHECKPOINT_DISABLE": "1"})
        proc = subprocess.run([terraform, f"-chdir={tmp}", "plan", "-input=false", "-lock=false", "-refresh=false",
                               "-no-color", "-var-file=values.tfvars.json"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                              timeout=120)
    if proc.returncode == 0:
        result = ("accepted", "")
    else:
        err = next((ln.strip() for ln in (proc.stderr + proc.stdout).splitlines() if ln.strip().startswith("Error:")),
                   "terraform plan failed")
        result = ("rejected" if err == "Error: Invalid value for variable" else "unchecked", err)
    _VALIDATION_CACHE[key] = result
    return result


def _validation_literals(name: str, checks: list[modread.Block]) -> list[str]:
    """String literals a validation names for ``var.<name>``: contains([...], var.x) lists, var.x == "..."."""
    out: list[str] = []
    for c in checks:
        toks = _toks(c.attrs.get("condition", []))
        for k, t in enumerate(toks):
            if t.kind == "IDENT" and t.text == "contains" and k + 2 < len(toks) and toks[k + 1].text == "(" \
                    and toks[k + 2].text == "[":
                end = modread._match_close(toks, k + 2)
                close = modread._match_close(toks, k + 1)
                rest = toks[end + 1:close]
                if [x.text for x in rest] == [",", "var", ".", name]:
                    out += [x.text for x in toks[k + 3:end] if x.kind == "STRING" and "${" not in x.text]
            if t.kind == "IDENT" and t.text == "var" and k + 4 < len(toks) and toks[k + 2].text == name \
                    and toks[k + 1].text == "." and toks[k + 3].text == "=" and toks[k + 4].text == "=" \
                    and k + 5 < len(toks) and toks[k + 5].kind == "STRING":
                out.append(toks[k + 5].text)
            if t.kind == "STRING" and k + 5 < len(toks) and toks[k + 1].text == "=" and toks[k + 2].text == "=" \
                    and toks[k + 3].text == "var" and toks[k + 5].text == name:
                out.append(t.text)
    seen: list[str] = []
    for v in out:
        if v not in seen:
            seen.append(v)
    return seen


# ---------------------------------------------------------------------------
# Scenario level
# ---------------------------------------------------------------------------


def _ds_of(blk: modread.Block) -> tuple[str, str] | None:
    toks = _toks(blk.attrs.get("description", []))
    if len(toks) == 1 and toks[0].kind == "STRING":
        m = data_vars.DESCRIPTION_RE.match(toks[0].text)
        if m:
            return m.group(1), m.group(2)
    return None


def compute(steps_files: list[dict[str, str]], search: dict[str, Any] | None = None) -> dict[str, Any]:
    """The vv-3 record of one scenario (all steps share both sets):
    ``variable_values``, ``variable_values_alt``, ``variable_values_rule``, ``variable_values_kinds``,
    ``variable_values_unresolved``, ``variable_values_candidates`` and ``excluded_from_v1``.

    ``search`` is the scenario's entry of the vv-3 search result (``candidates``: per set, variable to index,
    0 when absent; ``overrides``: variables whose declared default was rejected, with the error;
    ``excluded_from_v1``). None means no search result: every index 0, no override, not excluded."""
    search = search or {}
    overrides: dict[str, dict[str, Any]] = search.get("overrides") or {}
    cand_in = search.get("candidates") or {}
    decls: dict[str, set[str]] = {}
    blocks: dict[str, modread.Block] = {}
    with_default: set[str] = set()
    uses = _Uses()
    for files in steps_files:
        tf = {n: t for n, t in files.items() if n.endswith(".tf")}
        mod = modread.read_module(tf)
        collect_uses(mod, uses)
        for name, blk in mod.variables.items():
            if "default" in blk.attrs and name not in overrides:
                with_default.add(name)
                continue
            text = next((bt for t in tf.values() if (bt := variable_block_text(t, name)) is not None), None)
            decls.setdefault(name, set()).add(text or "")
            blocks.setdefault(name, blk)
    built: dict[str, tuple[Any, Any, Any, _Var]] = {}
    unresolved: dict[str, dict[str, str]] = {}
    for name in sorted(decls):
        if name in with_default:
            unresolved[name] = {"status": "unresolved",
                                "reason": "declared with a default in some steps and without one in others"}
            continue
        if len(decls[name]) != 1:
            unresolved[name] = {"status": "unresolved", "reason": "declared differently across steps"}
            continue
        blk = blocks[name]
        var = _Var(name, blk, sorted(set(uses.by_var.get(name, [])), key=repr), _ds_of(blk))
        try:
            if "type" in blk.attrs:
                node, _ = _parse_type(_toks(blk.attrs["type"]))
                var.evidence.add(f"declared_type:{_type_text(blk.attrs['type'])}")
            else:
                node = ("any",)
                var.evidence.add("untyped")
            ip = int((cand_in.get("primary") or {}).get(name, 0))
            ia = int((cand_in.get("alternate") or {}).get(name, 0))
            kt, pv, av = _build(var, node, (), ip, ia)
            if max(ip, ia) >= candidate_count(kt):
                raise ValueError(f"candidate index past the end of the lists for {name}")
        except _NoValue as exc:
            unresolved[name] = {"status": exc.status, "reason": str(exc)}
            continue
        built[name] = (kt, pv, av, var)
    values: dict[str, Any] = {}
    values_alt: dict[str, Any] = {}
    kinds: dict[str, dict[str, Any]] = {}
    pending = sorted(built)
    for _round in range(len(pending) + 1):
        progressed = False
        for name in list(pending):
            kt, pv, av, var = built[name]
            entry: dict[str, Any] = {"kind": kt}
            if name in overrides:
                entry["reason"] = OVERRIDE_PREFIX + overrides[name]["error"]
            checks = [c for c in var.blk.children if c.kind == "validation"]
            if checks:
                refs = {r[1] for c in checks for toks in c.attrs.values() for r in _raw_refs(toks) if r[0] == "var"}
                others = sorted(refs - {name})
                missing = [o for o in others if o not in built]
                if missing:
                    unresolved[name] = {"status": "unresolved",
                                        "reason": f"its validation refers to {', '.join('var.' + m for m in missing)},"
                                                  " which has no vv-3 value, so the value cannot be checked"}
                    pending.remove(name)
                    progressed = True
                    continue
                if any(o in pending for o in others):
                    continue  # check after the variables it refers to
                if any(o in unresolved for o in others):
                    bad = [o for o in others if o in unresolved]
                    unresolved[name] = {"status": "unresolved",
                                        "reason": f"its validation refers to {', '.join('var.' + m for m in bad)},"
                                                  " which has no vv-3 value, so the value cannot be checked"}
                    pending.remove(name)
                    progressed = True
                    continue
                block_texts = {n: next(iter(decls[n])) for n in [name, *others]}
                literals = _validation_literals(name, checks) if isinstance(kt, str) else []
                errors: list[str] = []

                def pick(first: Any, ctx: dict[str, Any], avoid: Any = None, has_avoid: bool = False) -> Any:
                    """First accepted candidate (for the alternate: the first that differs from ``avoid``,
                    else the first accepted). Raises _NoValue when none is accepted."""
                    fallback: list[Any] = []
                    for cand in [first] + [c for c in literals if c != first]:
                        status, err = validation_check(block_texts, {name: cand, **{o: ctx[o] for o in others}})
                        if status != "accepted":
                            if err not in errors:
                                errors.append(err)
                            continue
                        if not has_avoid or cand != avoid:
                            return cand
                        fallback.append(cand)
                    if fallback:
                        return fallback[0]
                    raise _NoValue("a validation block rejects every vv-3 candidate "
                                   f"{json.dumps([first] + [c for c in literals if c != first])} "
                                   f"({'; '.join(errors) or 'no error text'})")

                try:
                    pv = pick(pv, values)
                    av = pick(av, values_alt, pv, True)
                except _NoValue as exc:
                    unresolved[name] = {"status": "unresolved", "reason": str(exc)}
                    pending.remove(name)
                    progressed = True
                    continue
                var.evidence.add("validation")
                entry["validation"] = {"primary": pv, "alternate": av}
            if pv == av:
                leaves = _all_leaves(kt)
                if leaves and all(k == "region" for k in leaves):
                    entry["same_in_both_sets"] = SAME_REGION
                elif not leaves and kt == {"object": {}}:
                    entry["same_in_both_sets"] = SAME_EMPTY_OBJECT
                elif "validation" in entry:
                    entry["same_in_both_sets"] = SAME_VALIDATION
            entry["evidence"] = sorted(var.evidence)
            values[name], values_alt[name], kinds[name] = pv, av, entry
            pending.remove(name)
            progressed = True
        if not pending or not progressed:
            break
    for name in pending:  # validations that refer to each other in a cycle
        unresolved[name] = {"status": "unresolved", "reason": "validations refer to each other in a cycle"}
    return {
        "variable_values": dict(sorted(values.items())),
        "variable_values_alt": dict(sorted(values_alt.items())),
        "variable_values_rule": RULE,
        "variable_values_kinds": dict(sorted(kinds.items())),
        "variable_values_unresolved": dict(sorted(unresolved.items())),
        "variable_values_candidates": {
            "primary": {n: int((cand_in.get("primary") or {}).get(n, 0)) for n in sorted(values)},
            "alternate": {n: int((cand_in.get("alternate") or {}).get(n, 0)) for n in sorted(values)},
        },
        "excluded_from_v1": search.get("excluded_from_v1"),
    }
