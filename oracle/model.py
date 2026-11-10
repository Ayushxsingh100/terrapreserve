"""The configuration as the registry sees it, read from plan JSON (registry 2.1 to 2.3, D5-13).

Mapping rules (each is listed in ``oracle/README.md`` with its registry section):

* M-INST (2.3): the resource instances are the ``managed`` entries of ``resource_changes`` (full instance address,
  module path included). A resource in a local child module keeps its full module address (2.2 "Modules"); one in
  a non-local module source is ``unresolved``. ``count``/``for_each`` are already expanded by the plan; an expansion
  the plan could not resolve fails the plan, so no instance here is indeterminate by expansion.
* M-KNOWN (2.2): an attribute is resolved to its value when ``change.after`` holds it and ``after_unknown`` does
  not mark it, or anything inside it, unknown.
* M-WRITTEN (2.2, D1 V01): an optional+computed attribute that is unknown in the plan but has no expression in
  ``configuration`` was not written: it is *absent* (for example ``port``, ``private_ip``,
  ``source_security_group_id``, ``security_groups`` on an instance).
* M-IDREF (2.2 "Identity references"): an attribute that is unknown in the plan and whose configuration expression
  references only ``<resource>.id`` (plus the bare ``<resource>``) of configured instances resolves *as a reference*
  to those instances. A scalar needs exactly one such reference. Any other reference (``var.*``, ``local.*``,
  ``each.*``, ``count.*``, ``data.*`` or another attribute) leaves it unresolved (D5-13 gap d).
* M-LITERAL (2.2 "External literal IDs"): a known ID string names no configured resource (the configured IDs are
  unknown at plan time): an external reference.
* M-SET (D5-13 gap c): a set with an unknown element is wholly unknown in plan JSON; an identity-reference list is
  taken as exactly its identity references.
* Anything else unknown is unresolved (2.2 "Unresolved").

Standard library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class Unresolved:
    """A value the registry calls unresolved (2.2), with the reason."""

    __slots__ = ("reason",)

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def __repr__(self) -> str:
        return f"Unresolved({self.reason!r})"

    def __eq__(self, other: object) -> bool:  # unresolved never equals anything (2.9: treated as changed)
        return False

    def __hash__(self) -> int:
        return id(self)


class _Absent:
    """An argument that was not written (M-WRITTEN). A singleton, never equal to any value."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<absent>"

    def __str__(self) -> str:
        return "<absent>"


ABSENT = _Absent()


@dataclass(frozen=True)
class Ref:
    """An identity reference to a configured resource instance (2.2)."""

    address: str


@dataclass(frozen=True)
class Literal:
    """An external literal ID that names no configured resource (2.2)."""

    value: str


@dataclass
class Instance:
    address: str
    type: str
    module: str  # "" for the root module, else "module.a.module.b" (instance keys included)
    expressions: dict[str, Any]
    after: dict[str, Any]
    unknown: Any
    nonlocal_module: bool = False


@dataclass
class Config:
    instances: dict[str, Instance]
    config_types: dict[str, int]  # resource type -> number of configuration blocks (any count, zero included)
    moved: list[tuple[str, str]] = field(default_factory=list)
    module_sources: dict[str, str] = field(default_factory=dict)

    def of_type(self, *types: str) -> list[Instance]:
        return [i for a, i in sorted(self.instances.items()) if i.type in types]

    def present_types(self) -> set[str]:
        return {i.type for i in self.instances.values()}


def _contains_true(u: Any) -> bool:
    if u is True:
        return True
    if isinstance(u, list):
        return any(_contains_true(x) for x in u)
    if isinstance(u, dict):
        return any(_contains_true(x) for x in u.values())
    return False


def _strip_keys(module_address: str) -> str:
    return re.sub(r"\[[^\]]*\]", "", module_address)


def _config_resources(mod: dict[str, Any], prefix: str, out: dict[str, dict], sources: dict[str, str],
                      types: dict[str, int]) -> None:
    for r in mod.get("resources", []):
        if r.get("mode") != "managed":
            continue
        out[(prefix + "." if prefix else "") + r["address"]] = r
        types[r["type"]] = types.get(r["type"], 0) + 1
    for name, call in (mod.get("module_calls") or {}).items():
        p = (prefix + "." if prefix else "") + f"module.{name}"
        sources[p] = str(call.get("source", ""))
        _config_resources(call.get("module") or {}, p, out, sources, types)


def is_local_source(src: str) -> bool:
    return src.startswith("./") or src.startswith("../")


def build(plan: dict[str, Any], moved: list[tuple[str, str]] | None = None) -> Config:
    """The configuration of one plan JSON document (raises on a malformed document: VERIFIER_ERROR, 2.4)."""
    if not isinstance(plan, dict) or not isinstance(plan.get("configuration"), dict):
        raise ValueError("malformed plan JSON: no configuration section")
    cfg: dict[str, dict] = {}
    sources: dict[str, str] = {}
    types: dict[str, int] = {}
    _config_resources(plan["configuration"].get("root_module") or {}, "", cfg, sources, types)
    instances: dict[str, Instance] = {}
    for rc in plan.get("resource_changes") or []:
        if rc.get("mode") != "managed":
            continue
        change = rc["change"]
        if "delete" in change.get("actions", []) and change.get("after") is None:
            continue
        module = rc.get("module_address", "") or ""
        key = (_strip_keys(module) + "." if module else "") + f"{rc['type']}.{rc['name']}"
        conf = cfg.get(key, {})
        nonlocal_mod = any(not is_local_source(src) for p, src in sources.items()
                           if module and (_strip_keys(module) == p or _strip_keys(module).startswith(p + ".")))
        instances[rc["address"]] = Instance(
            address=rc["address"], type=rc["type"], module=module, expressions=conf.get("expressions") or {},
            after=change.get("after") or {}, unknown=change.get("after_unknown") or {}, nonlocal_module=nonlocal_mod)
    if not isinstance(plan.get("resource_changes", []), list):
        raise ValueError("malformed plan JSON: resource_changes is not a list")
    return Config(instances=instances, config_types=types, moved=list(moved or []), module_sources=sources)


# ---- attribute access

def raw(inst: Instance, key: str) -> tuple[str, Any]:
    """("known", value) or ("unknown", None) for a top-level attribute (M-KNOWN)."""
    if inst.nonlocal_module:
        return "unknown", None
    u = inst.unknown.get(key) if isinstance(inst.unknown, dict) else inst.unknown
    if _contains_true(u):
        return "unknown", None
    return "known", inst.after.get(key)


def blocks(inst: Instance, key: str) -> tuple[list[dict], list[dict]] | Unresolved:
    """A list of nested objects (route blocks, inline rules) with each element's ``after_unknown`` (M-KNOWN per field)."""
    u = inst.unknown.get(key) if isinstance(inst.unknown, dict) else inst.unknown
    v = inst.after.get(key)
    if inst.nonlocal_module:
        return Unresolved(f"{inst.address}.{key}: non-local module")
    if u is True and not written(inst, key):
        return [], []  # optional+computed and not written (M-WRITTEN): no blocks
    if u is True:
        return Unresolved(f"{inst.address}.{key} is unknown in the plan")
    if not isinstance(v, list):
        return [], []
    us = u if isinstance(u, list) else [{}] * len(v)
    return [x if isinstance(x, dict) else {} for x in v], [x if isinstance(x, dict) else {} for x in us]


def field_value(block: dict, unknown: dict, key: str) -> Any:
    """One field of a nested object: its value, or Unresolved when the plan marks it unknown."""
    if _contains_true(unknown.get(key) if isinstance(unknown, dict) else unknown):
        return Unresolved(f"{key} is unknown in the plan")
    return block.get(key)


def written(inst: Instance, key: str) -> bool:
    """Whether the configuration writes ``key`` (an expression or a static nested block) (M-WRITTEN)."""
    return key in inst.expressions


def value(inst: Instance, key: str) -> Any:
    """Resolved value, ``ABSENT`` (not written; optional+computed unknown), or ``Unresolved``."""
    state, v = raw(inst, key)
    if state == "known":
        return v
    if not written(inst, key) and not inst.nonlocal_module:
        return ABSENT
    return Unresolved(f"{inst.address}.{key} is unknown in the plan")


_IDREF = re.compile(r'^(?P<res>[a-z][a-z0-9_]*\.[A-Za-z_][A-Za-z0-9_\-]*(?:\[[^\]]+\])?)\.id$')
_BARE = re.compile(r'^(?P<res>[a-z][a-z0-9_]*\.[A-Za-z_][A-Za-z0-9_\-]*)(?:\[[^\]]+\])?$')


def identity_refs(config: Config, inst: Instance, references: list[str]) -> list[str] | Unresolved:
    """The configured instances a reference list names by ``.id`` (M-IDREF), or Unresolved."""
    prefix = (inst.module + ".") if inst.module else ""
    ids: list[str] = []
    for r in references:
        m = _IDREF.match(r)
        if m:
            ids.append(m.group("res"))
    if not ids:
        return Unresolved(f"{inst.address}: no identity reference in {references}")
    id_bases = {re.sub(r"\[[^\]]+\]$", "", i) for i in ids}
    for r in references:
        if _IDREF.match(r):
            continue
        b = _BARE.match(r)
        if b and b.group("res") in id_bases:
            continue
        return Unresolved(f"{inst.address}: reference {r!r} is not an identity reference (D5-13 gap d)")
    out: list[str] = []
    for i in ids:
        addr = prefix + i
        if addr in config.instances:
            out.append(addr)
            continue
        return Unresolved(f"{inst.address}: {i} names no single configured instance")
    seen: list[str] = []
    for a in out:
        if a not in seen:
            seen.append(a)
    return seen


def id_scalar(config: Config, inst: Instance, key: str) -> Ref | Literal | str | Unresolved:
    """A scalar ID attribute: Ref, Literal, ABSENT, or Unresolved."""
    v = value(inst, key)
    if isinstance(v, Unresolved):
        refs = identity_refs(config, inst, (inst.expressions.get(key) or {}).get("references") or [])
        if isinstance(refs, Unresolved):
            return refs
        if len(refs) != 1:
            return Unresolved(f"{inst.address}.{key} references {len(refs)} instances")
        return Ref(refs[0])
    if v is ABSENT or v is None or v == "":
        return ABSENT
    if isinstance(v, str):
        return Literal(v)
    return Unresolved(f"{inst.address}.{key} has a non-string value")


def id_list(config: Config, inst: Instance, key: str) -> list[Ref | Literal] | str | Unresolved:
    """A list/set of IDs: a list of Ref/Literal, ABSENT, or Unresolved (M-SET)."""
    v = value(inst, key)
    if isinstance(v, Unresolved):
        refs = identity_refs(config, inst, (inst.expressions.get(key) or {}).get("references") or [])
        if isinstance(refs, Unresolved):
            return refs
        return [Ref(a) for a in refs]
    if v is ABSENT or v is None:
        return ABSENT
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return [Literal(x) for x in v]
    return Unresolved(f"{inst.address}.{key} is not a list of IDs")
