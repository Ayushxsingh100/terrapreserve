"""Variable values for the scenario record (D5-01, rule ``vv-1``).

Registry v1.0 section 2.1 evaluates a configuration "together with the scenario's variable values", and
section 2.2 resolves an input variable to its "provided value, else declared default". No scenario carried
values before D5a. This module gives every variable that is declared **without** a default a value chosen
by the fixed, versioned rule ``vv-1``; variables with a default are not listed (the default applies).

Rule vv-1 (from the D5a work package; ``docs/D5_DECISIONS.md`` D5-01):

* by declared ``type`` when present, else as ``string``: ``string`` -> ``"tp-placeholder"``; ``number`` -> ``1``;
  ``bool`` -> ``false``; ``list(...)``, ``set(...)``, ``tuple(...)`` -> ``[]``; ``map(...)``, ``object(...)`` -> ``{}``;
* a variable that is ``sensitive = true`` or whose name contains ``password``, ``secret`` or ``token``
  -> ``"tp-placeholder"``;
* when the value cannot satisfy the type (an ``object`` with a required attribute, a non-empty ``tuple``,
  type ``any`` which the rule does not cover, a secret-named variable of a non-string type) or a
  ``validation`` block rejects it, the variable is recorded in ``variable_values_unresolved`` with the
  reason. No value is invented.

Validation blocks are checked by Terraform itself: the single ``variable`` block is copied into an empty
temporary directory and ``terraform plan`` is run with the candidate value (no provider, no init, no
network). Standard library only.
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
from realworld import modread  # noqa: E402

RULE = "vv-1"
PLACEHOLDER = "tp-placeholder"
_SECRET_NAME = re.compile(r"password|secret|token", re.IGNORECASE)


class _NoValue(Exception):
    """vv-1 gives no value; the message is the reason recorded in ``variable_values_unresolved``."""


# ---------------------------------------------------------------------------
# Type expressions
# ---------------------------------------------------------------------------


def _toks(tokens: list) -> list:
    return [t for t in tokens if t.kind != "NEWLINE"]


def _parse_type(toks: list, i: int = 0) -> tuple[tuple, int]:
    """Parse a Terraform type constraint. Returns (node, next index)."""
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
        attrs: dict[str, bool] = {}  # name -> optional
        while not (toks[j].kind == "PUNCT" and toks[j].text == "}"):
            if toks[j].kind == "PUNCT" and toks[j].text == ",":
                j += 1
                continue
            aname = toks[j].text
            j += 2  # name =
            optional = toks[j].kind == "IDENT" and toks[j].text == "optional"
            if optional:
                depth = 0
                while True:
                    if toks[j].kind == "PUNCT" and toks[j].text == "(":
                        depth += 1
                    elif toks[j].kind == "PUNCT" and toks[j].text == ")":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
            else:
                _e, j = _parse_type(toks, j)
            attrs[aname] = optional
        return ("object", attrs), j + 2  # skip "} )"
    raise _NoValue(f"type {name!r} not understood")


def _type_text(tokens: list) -> str:
    return "".join(t.text if t.kind != "STRING" else f'"{t.text}"' for t in _toks(tokens))


def vv1_value(name: str, blk: modread.Block) -> Any:
    """The vv-1 value for one variable block, before the validation check. Raises _NoValue."""
    node: tuple = ("string",)
    if "type" in blk.attrs:
        node, _ = _parse_type(_toks(blk.attrs["type"]))
    secret = "sensitive" in blk.attrs and _type_text(blk.attrs["sensitive"]) == "true"
    if secret or _SECRET_NAME.search(name):
        if node[0] in ("string", "any"):
            return PLACEHOLDER
        raise _NoValue(f"vv-1 gives the string placeholder to a sensitive or secret-named variable, "
                       f"but its type is {_type_text(blk.attrs['type'])}")
    kind = node[0]
    if kind == "string":
        return PLACEHOLDER
    if kind == "number":
        return 1
    if kind == "bool":
        return False
    if kind in ("list", "set"):
        return []
    if kind == "tuple":
        if node[1]:
            raise _NoValue("tuple type with elements: [] does not satisfy it")
        return []
    if kind == "map":
        return {}
    if kind == "object":
        required = sorted(a for a, opt in node[1].items() if not opt)
        if required:
            raise _NoValue(f"object type with required attributes {required}: {{}} does not satisfy it")
        return {}
    if kind == "any":
        raise _NoValue("type any is not covered by vv-1")
    raise _NoValue(f"type {kind!r} not covered by vv-1")


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


_VALIDATION_CACHE: dict[str, tuple[bool, str]] = {}


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
        raise RuntimeError("terraform is required to check validation blocks for rule vv-1")
    with tempfile.TemporaryDirectory(prefix="tp-vv1-") as tmp:
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


# ---------------------------------------------------------------------------
# Scenario level
# ---------------------------------------------------------------------------


def compute(steps_files: list[dict[str, str]]) -> tuple[dict[str, Any], dict[str, str]]:
    """(variable_values, variable_values_unresolved) for one scenario (all steps share one set)."""
    decls: dict[str, set[str]] = {}
    blocks: dict[str, modread.Block] = {}
    with_default: set[str] = set()
    for files in steps_files:
        tf = {n: t for n, t in files.items() if n.endswith(".tf")}
        mod = modread.read_module(tf)
        for name, blk in mod.variables.items():
            if "default" in blk.attrs:
                with_default.add(name)
                continue
            text = next((bt for t in tf.values() if (bt := variable_block_text(t, name)) is not None), None)
            decls.setdefault(name, set()).add(text or "")
            blocks.setdefault(name, blk)
    candidates: dict[str, Any] = {}
    unresolved: dict[str, str] = {}
    for name in sorted(decls):
        if name in with_default:
            unresolved[name] = "declared with a default in some steps and without one in others"
            continue
        if len(decls[name]) != 1:
            unresolved[name] = "declared differently across steps"
            continue
        try:
            candidates[name] = vv1_value(name, blocks[name])
        except _NoValue as exc:
            unresolved[name] = str(exc)
    values: dict[str, Any] = {}
    for name in sorted(candidates):
        blk = blocks[name]
        checks = [c for c in blk.children if c.kind == "validation"]
        if checks:
            refs = {n for c in checks for toks in c.attrs.values() for kind, n in _refs(toks) if kind == "var"}
            others = sorted(refs - {name})
            missing = [o for o in others if o not in candidates]
            if missing:
                unresolved[name] = (f"its validation refers to {', '.join('var.' + m for m in missing)}, "
                                    "which has no vv-1 value, so the vv-1 value cannot be checked")
                continue
            block_texts = {n: next(iter(decls[n])) for n in [name, *others]}
            status, err = validation_check(block_texts, {n: candidates[n] for n in block_texts})
            if status == "rejected":
                unresolved[name] = f"a validation block rejects the vv-1 value {json.dumps(candidates[name])} ({err})"
                continue
            if status == "unchecked":
                unresolved[name] = f"the validation block could not be checked ({err})"
                continue
        values[name] = candidates[name]
    return values, unresolved


# ---------------------------------------------------------------------------
# Relevance report: placeholders that reach attributes the registry reads
# ---------------------------------------------------------------------------

RELEVANT_ATTRS = frozenset({"vpc_security_group_ids", "subnet_id", "security_group_id", "publicly_accessible",
                            "port", "engine", "vpc_id", "cidr_block"})
SG_TYPES = frozenset({"aws_security_group", "aws_security_group_rule"})
_REF = re.compile(r"\b(var|local)\.([A-Za-z_][A-Za-z0-9_\-]*)")


def _refs(tokens: list) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    toks = _toks(tokens)
    for k, t in enumerate(toks):
        if t.kind == "IDENT" and t.text in ("var", "local") and k + 2 < len(toks) \
                and toks[k + 1].kind == "PUNCT" and toks[k + 1].text == "." and toks[k + 2].kind == "IDENT":
            out.add((t.text, toks[k + 2].text))
        elif t.kind == "STRING":
            out.update(_REF.findall(t.text))
    return out


def _var_closure(refs: set[tuple[str, str]], locals_: dict[str, list]) -> set[str]:
    out: set[str] = set()
    seen: set[str] = set()
    todo = list(refs)
    while todo:
        kind, name = todo.pop()
        if kind == "var":
            out.add(name)
        elif name not in seen and name in locals_:
            seen.add(name)
            todo.extend(_refs(locals_[name]))
    return out


def _walk_attrs(blk: modread.Block, path: str = ""):
    for name, toks in blk.attrs.items():
        yield f"{path}{name}", name, toks
    for child in blk.children:
        label = child.kind if not child.labels else f"{child.kind}.{child.labels[0]}"
        yield from _walk_attrs(child, f"{path}{label}.")


def relevance(steps_files: list[dict[str, str]], placeholders: set[str]) -> list[tuple[str, str, str]]:
    """(variable, resource address, attribute path) for each placeholder reaching a registry-read attribute."""
    hits: set[tuple[str, str, str]] = set()
    for files in steps_files:
        mod = modread.read_module({n: t for n, t in files.items() if n.endswith(".tf")})
        for addr, blk in mod.resources.items():
            rtype = blk.labels[0]
            holds_relevant = rtype in SG_TYPES
            rows = list(_walk_attrs(blk))
            for path, name, toks in rows:
                # Security-group rules (any field): rule resources, and the inline or dynamic ingress and
                # egress blocks of a group; elsewhere only the listed attributes.
                in_rule = rtype == "aws_security_group_rule" or (
                    rtype == "aws_security_group" and path.split(".", 1)[0] in ("ingress", "egress", "dynamic"))
                relevant = in_rule or name in RELEVANT_ATTRS
                if relevant:
                    holds_relevant = True
                    for v in _var_closure(_refs(toks), mod.locals) & placeholders:
                        hits.add((v, addr, path))
            if holds_relevant:
                for meta in ("count", "for_each"):
                    if meta in blk.attrs:
                        for v in _var_closure(_refs(blk.attrs[meta]), mod.locals) & placeholders:
                            hits.add((v, addr, meta))
    return sorted(hits)
