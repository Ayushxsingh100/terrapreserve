"""D5-08: data-source variables, a recorded host transform (real-world tier).

Every top-level ``data "<type>" "<name>"`` block of a module is removed. Every reference
``data.<type>.<name>`` (with any attribute path or index after it, in expressions and inside string
templates) becomes ``var.tp_ds_<type>_<name>`` with the same path. The new variables are declared, with no
default, in ``terrapreserve_data_variables.tf``, typed as an ``object`` with exactly the attributes the module
uses (nested types as used; ``list(...)`` of it for a block with ``count``, ``map(...)`` for ``for_each``).
Each removal is recorded in the scenario's ``host_transform`` list with the sha256 of the original block text
(from the ``data`` keyword to the closing brace, as written in the pool file).

Rule vv-3 (``generator/varvalues.py``, D5-10, which keeps vv-2) then gives the variables a primary and an alternate value. The
attribute types follow the use in the module, with the list-typed attributes of ``DS_LIST_ATTRS`` typed as
lists. Standard library only.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))

import hcl_lex  # noqa: E402

VARIABLES_FILE = "terrapreserve_data_variables.tf"
PREFIX = "tp_ds_"
DESCRIPTION = "TerraPreserve D5-08: replaces data block {type}/{name}"
DESCRIPTION_RE = re.compile(r"^TerraPreserve D5-08: replaces data block ([A-Za-z0-9_\-]+)/([A-Za-z0-9_\-]+)$")
HEADER = ("# TerraPreserve D5-08 (data-source variables): each variable below replaces a data block of the\n"
          "# module. The block's sha256 and the variable are recorded in scenario.json (host_transform).\n")

# Attributes that are lists in the AWS provider 6.53.0 schema of the data source (their element kind is
# given by rule vv-2, generator/varvalues.py DS_KINDS).
DS_LIST_ATTRS = frozenset({
    ("aws_availability_zones", "names"), ("aws_availability_zones", "zone_ids"),
    ("aws_ip_ranges", "cidr_blocks"), ("aws_ip_ranges", "ipv6_cidr_blocks"),
    ("aws_subnets", "ids"), ("aws_vpcs", "ids"),
    ("aws_db_instance", "db_parameter_groups"), ("aws_db_instance", "db_security_groups"),
    ("aws_db_instance", "vpc_security_groups"),
    ("aws_instance", "security_groups"), ("aws_instance", "vpc_security_group_ids"),
})
_PATH_RE = r"((?:\.[A-Za-z_][A-Za-z0-9_\-]*|\.[0-9]+|\[[^\]\[]*\])*)"


def variable_name(dtype: str, dname: str) -> str:
    return f"{PREFIX}{dtype}_{dname}"


def _spans(text: str) -> list[tuple[hcl_lex.Token, int, int]]:
    return [s for s in hcl_lex.tokenize_spans(text) if s[0].kind != "NEWLINE"]


def data_blocks(text: str) -> list[tuple[str, str, int, int, dict[str, bool]]]:
    """(type, name, start, end, meta) of each top-level data block; meta says whether count/for_each is set."""
    spans = _spans(text)
    out = []
    depth = 0
    i = 0
    while i < len(spans):
        tok, start, _e = spans[i]
        if tok.kind == "PUNCT" and tok.text == "{":
            depth += 1
        elif tok.kind == "PUNCT" and tok.text == "}":
            depth -= 1
        elif depth == 0 and tok.kind == "IDENT" and tok.text == "data" and i + 3 < len(spans) \
                and spans[i + 1][0].kind == "STRING" and spans[i + 2][0].kind == "STRING" \
                and spans[i + 3][0].kind == "PUNCT" and spans[i + 3][0].text == "{":
            level = 0
            meta = {"count": False, "for_each": False}
            for k in range(i + 3, len(spans)):
                t = spans[k][0]
                if t.kind == "PUNCT" and t.text == "{":
                    level += 1
                elif t.kind == "PUNCT" and t.text == "}":
                    level -= 1
                    if level == 0:
                        out.append((spans[i + 1][0].text, spans[i + 2][0].text, start, spans[k][2], meta))
                        i = k
                        break
                elif level == 1 and t.kind == "IDENT" and t.text in meta and k + 1 < len(spans) \
                        and spans[k + 1][0].text == "=":
                    meta[t.text] = True
        i += 1
    return out


def _remove(text: str, cuts: list[tuple[int, int]]) -> str:
    """Remove the spans, each with its whole lines when only blanks share them (as hcl_lex does)."""
    out: list[str] = []
    cursor = 0
    for start, end in sorted(cuts):
        line_start = text.rfind("\n", 0, start) + 1
        if text[line_start:start].strip(" \t") == "":
            start = line_start
        eol = text.find("\n", end)
        tail_end = len(text) if eol == -1 else eol
        if text[end:tail_end].strip(" \t\r") == "":
            end = min(tail_end + 1, len(text))
        out.append(text[cursor:start])
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


def _token_path(spans: list, k: int) -> tuple[list[str], int]:
    """Path parts after the traversal ending at span index k-1; returns (parts, index after the path)."""
    parts: list[str] = []
    n = len(spans)
    while k < n:
        t = spans[k][0]
        if t.kind == "PUNCT" and t.text == "." and k + 1 < n and spans[k + 1][0].kind in ("IDENT", "NUMBER"):
            parts.append("." + spans[k + 1][0].text)
            k += 2
        elif t.kind == "PUNCT" and t.text == "." and k + 1 < n and spans[k + 1][0].text == "*":
            parts.append("[each]")
            k += 2
        elif t.kind == "PUNCT" and t.text == "[":
            depth = 0
            j = k
            while j < n:
                if spans[j][0].kind == "PUNCT" and spans[j][0].text == "[":
                    depth += 1
                elif spans[j][0].kind == "PUNCT" and spans[j][0].text == "]":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            inner = [s[0] for s in spans[k + 1:j]]
            if len(inner) == 1 and inner[0].kind == "PUNCT" and inner[0].text == "*":
                parts.append("[each]")
            elif len(inner) == 1 and inner[0].kind == "NUMBER":
                parts.append(f"[{inner[0].text}]")
            elif len(inner) == 1 and inner[0].kind == "STRING":
                parts.append(f'["{inner[0].text}"]')
            else:
                parts.append("[*]")
            k = j + 1
        else:
            break
    return parts, k


def _string_paths(raw: str, dtype: str, dname: str) -> list[list[str]]:
    out = []
    for m in re.finditer(rf"(?<![\w.\-])data\.{re.escape(dtype)}\.{re.escape(dname)}(?![\w\-])" + _PATH_RE, raw):
        parts = re.findall(r"\.[A-Za-z_0-9][A-Za-z0-9_\-]*|\[[^\]\[]*\]", m.group(1))
        norm = []
        for p in parts:
            if p.startswith("["):
                inner = p[1:-1].strip()
                norm.append("[each]" if inner == "*" else (f"[{inner}]" if inner.isdigit() else "[*]"))
            else:
                norm.append(p)
        out.append(norm)
    return out


def _rewrite_refs(text: str, targets: set[tuple[str, str]], uses: dict[tuple[str, str], list[list[str]]]) -> str:
    spans = hcl_lex.tokenize_spans(text)
    dense = [s for s in spans if s[0].kind != "NEWLINE"]
    edits: list[tuple[int, int, str]] = []
    for k, (t, start, end) in enumerate(dense):
        if t.kind == "IDENT" and t.text == "data" and k + 4 < len(dense) and dense[k + 1][0].text == "." \
                and dense[k + 2][0].kind == "IDENT" and dense[k + 3][0].text == "." \
                and dense[k + 4][0].kind == "IDENT":
            key = (dense[k + 2][0].text, dense[k + 4][0].text)
            if key in targets and not (k > 0 and dense[k - 1][0].text == "."):
                parts, _n = _token_path(dense, k + 5)
                uses.setdefault(key, []).append(parts)
                edits.append((start, dense[k + 4][2], "var." + variable_name(*key)))
        elif t.kind in ("STRING", "HEREDOC"):
            raw = text[start:end]
            new = raw
            for key in sorted(targets):
                for p in _string_paths(raw, *key):
                    uses.setdefault(key, []).append(p)
                new = re.sub(rf"(?<![\w.\-])data\.{re.escape(key[0])}\.{re.escape(key[1])}(?![\w\-])",
                             "var." + variable_name(*key), new)
            if new != raw:
                edits.append((start, end, new))
    for start, end, new in sorted(edits, reverse=True):
        text = text[:start] + new + text[end:]
    return text


def _type_tree(paths: list[list[str]]) -> dict | str:
    """Nested structure of the uses below one attribute: "string", {"list": ...} or {"object": {...}}."""
    paths = [p for p in paths]
    if not paths or all(not p for p in paths):
        return "string"
    if any(p and p[0].startswith("[") for p in paths):
        return {"list": _type_tree([p[1:] for p in paths if p and p[0].startswith("[")])}
    attrs: dict[str, list[list[str]]] = {}
    for p in paths:
        if p and p[0].startswith("."):
            attrs.setdefault(p[0][1:], []).append(p[1:])
    return {"object": {a: _type_tree(v) for a, v in sorted(attrs.items())}}


def _render(tree: dict | str, indent: int) -> str:
    if tree == "string":
        return "string"
    if "list" in tree:
        return f"list({_render(tree['list'], indent)})"
    if "map" in tree:
        return f"map({_render(tree['map'], indent)})"
    attrs = tree["object"]
    if not attrs:
        return "object({})"
    pad = " " * (indent + 2)
    width = max(len(a) for a in attrs)
    lines = [f"{pad}{a.ljust(width)} = {_render(t, indent + 2)}" for a, t in attrs.items()]
    return "object({\n" + "\n".join(lines) + "\n" + " " * indent + "})"


def variable_type(dtype: str, meta: dict[str, bool], uses: list[list[str]]) -> dict | str:
    """The object type of the variable that replaces one data block."""
    if meta.get("count") or meta.get("for_each"):
        inner = [p[1:] for p in uses if p and p[0].startswith("[")]
    else:
        inner = list(uses)
    attrs: dict[str, list[list[str]]] = {}
    for p in inner:
        if p and p[0].startswith("."):
            attrs.setdefault(p[0][1:], []).append(p[1:])
    obj = {}
    for a, rest in sorted(attrs.items()):
        t = _type_tree(rest)
        if (dtype, a) in DS_LIST_ATTRS and not (isinstance(t, dict) and "list" in t):
            t = {"list": "string"}
        obj[a] = t
    tree: dict = {"object": obj}
    if meta.get("count"):
        return {"list": tree}
    if meta.get("for_each"):
        return {"map": tree}
    return tree


def transform(files: dict[str, str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Apply D5-08 to a module. Returns (new files, host_transform entries). No data block: files unchanged."""
    found: dict[tuple[str, str], tuple[str, str, dict[str, bool]]] = {}
    cut: dict[str, list[tuple[int, int]]] = {}
    for fname in sorted(files):
        if not fname.endswith(".tf"):
            continue
        for dtype, dname, start, end, meta in data_blocks(files[fname]):
            text = files[fname][start:end]
            found[(dtype, dname)] = (fname, hashlib.sha256(text.encode("utf-8")).hexdigest(), meta)
            cut.setdefault(fname, []).append((start, end))
    if not found:
        return dict(files), []
    if VARIABLES_FILE in files:
        raise ValueError(f"{VARIABLES_FILE} already exists in the module")
    targets = set(found)
    uses: dict[tuple[str, str], list[list[str]]] = {}
    out: dict[str, str] = {}
    for fname in sorted(files):
        text = files[fname]
        if fname.endswith(".tf"):
            if fname in cut:
                text = _remove(text, cut[fname])
            text = _rewrite_refs(text, targets, uses)
        out[fname] = text
    blocks = []
    records = []
    for (dtype, dname), (fname, sha, meta) in sorted(found.items()):
        vname = variable_name(dtype, dname)
        tree = variable_type(dtype, meta, uses.get((dtype, dname), []))
        rendered = _render(tree, 2)
        # terraform fmt aligns "=" only across single-line attributes
        type_line = f"  type = {rendered}" if "\n" in rendered else f"  type        = {rendered}"
        blocks.append(f'variable "{vname}" {{\n'
                      f'  description = "{DESCRIPTION.format(type=dtype, name=dname)}"\n'
                      f"{type_line}\n"
                      "}\n")
        records.append({"kind": "data_source_to_variable", "file": fname, "data_type": dtype, "data_name": dname,
                        "block_sha256": sha, "variable": vname})
    out[VARIABLES_FILE] = HEADER + "\n" + "\n".join(blocks)
    return out, records
