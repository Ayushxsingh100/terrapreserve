"""A small lexical reader for Terraform ``.tf`` and ``.tf.json`` text.

Standard library only. It is deliberately **not** an HCL parser and shares no code
with TerraDS's analyser (HashiCorp's terraform-config-inspect) or with DAIL. It
tokenises just enough to be right about the things the cross-check and the
attribute inventory need:

* comments (``#``, ``//``, ``/* */``) are dropped;
* heredoc bodies are a single token, so text inside them is never read as HCL;
* quoted strings are a single token, interpolations ``${...}`` / ``%{...}`` inside
  them are skipped (nested quotes and braces included), and ``$${`` is literal;
* top-level block headers ``resource "T" "N"``, ``data "T" "N"`` and ``module "N"``
  are found by brace depth.

Nothing is evaluated, and no value is kept beyond what each function documents.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]*")
NUMBER_RE = re.compile(r"[0-9][A-Za-z0-9_.]*")
HEREDOC_RE = re.compile(r"<<(-?)([A-Za-z_][A-Za-z0-9_\-]*)[ \t]*\r?\n")


@dataclass(frozen=True)
class Token:
    kind: str  # IDENT NUMBER STRING HEREDOC PUNCT NEWLINE
    text: str  # IDENT/NUMBER/PUNCT text; STRING: the raw text between the quotes; HEREDOC: ""
    line: int  # 1-based line on which the token starts
    end_line: int  # line on which it ends
    literal: bool = False  # STRING: has text outside ${...}/%{...}; HEREDOC: always True


def _skip_interpolation(text: str, i: int) -> tuple[int, int]:
    """``i`` points just after ``${`` or ``%{``. Returns (index after the closing brace, newlines)."""
    depth = 1
    newlines = 0
    n = len(text)
    while i < n and depth:
        ch = text[i]
        if ch == "\n":
            newlines += 1
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == '"':
            i, _lit, _inner, nl = _scan_string(text, i)
            newlines += nl
            continue
        i += 1
    return i, newlines


def _scan_string(text: str, i: int) -> tuple[int, bool, str, int]:
    """``i`` points at the opening quote. Returns (index after the string, has literal text, raw
    inner text, newlines inside). An unterminated string ends at the end of its line."""
    start = i + 1
    i = start
    n = len(text)
    literal = False
    newlines = 0
    while i < n:
        ch = text[i]
        if ch == "\\":
            literal = True
            i += 2
            continue
        if ch == '"':
            return i + 1, literal, text[start:i], newlines
        if ch == "\n":  # HCL strings cannot span lines: treat as unterminated
            return i, literal, text[start:i], newlines
        if text.startswith(("$${", "%%{"), i):
            literal = True
            i += 3
            continue
        if text.startswith(("${", "%{"), i):
            i, nl = _skip_interpolation(text, i + 2)
            newlines += nl
            continue
        literal = True
        i += 1
    return i, literal, text[start:i], newlines


def tokenize(text: str) -> list[Token]:
    return [tok for tok, _start, _end in tokenize_spans(text)]


def tokenize_spans(text: str) -> list[tuple[Token, int, int]]:
    """The tokens of :func:`tokenize`, each with its character span ``(start, end)`` in ``text``.

    A heredoc token spans its header and body up to the end of the terminator line; the NEWLINE token
    that follows it has an empty span at that end.
    """
    tokens: list[tuple[Token, int, int]] = []
    i, line, n = 0, 1, len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            tokens.append((Token("NEWLINE", "\n", line, line), i, i + 1))
            line += 1
            i += 1
        elif ch in " \t\r":
            i += 1
        elif ch == "#" or text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            line += text.count("\n", i, end)
            i = end
        elif ch == '"':
            j, literal, inner, nl = _scan_string(text, i)
            tokens.append((Token("STRING", inner, line, line + nl, literal), i, j))
            line += nl
            i = j
        elif ch == "<" and (m := HEREDOC_RE.match(text, i)):
            marker = m.group(2)
            j = m.end()
            body_lines = 1  # the header line's newline
            while j < n:
                eol = text.find("\n", j)
                eol = n if eol == -1 else eol
                current = text[j:eol].rstrip("\r")
                body_lines += 1
                j = min(eol + 1, n)
                # HCL accepts leading whitespace before the closing marker for both << and <<-
                if current.strip() == marker:
                    break
            end_line = line + body_lines - 1  # the terminator line
            tokens.append((Token("HEREDOC", "", line, end_line, True), i, j))
            i = j
            # the terminator line's own newline was consumed with it
            tokens.append((Token("NEWLINE", "\n", end_line, end_line), j, j))
            line = end_line + 1
        elif m := IDENT_RE.match(text, i):
            tokens.append((Token("IDENT", m.group(), line, line), i, m.end()))
            i = m.end()
        elif m := NUMBER_RE.match(text, i):
            tokens.append((Token("NUMBER", m.group(), line, line), i, m.end()))
            i = m.end()
        else:
            tokens.append((Token("PUNCT", ch, line, line), i, i + 1))
            i += 1
    return tokens


# --------------------------------------------------------------------------- headers


@dataclass
class Headers:
    """What the top level of one file declares."""

    managed: set[tuple[str, str]]  # (type, name)
    data: set[tuple[str, str]]
    modules: set[str]
    anomalies: int = 0  # unbalanced braces or a header that did not fit the expected shape


def _label(tok: Token) -> str | None:
    return tok.text if tok.kind in ("STRING", "IDENT") else None


def headers_from_hcl(text: str) -> Headers:
    """Top-level ``resource``/``data``/``module`` blocks of ``.tf`` text, found by brace depth."""
    tokens = tokenize(text)
    out = Headers(set(), set(), set())
    depth = 0
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok.kind == "PUNCT" and tok.text == "{":
            depth += 1
        elif tok.kind == "PUNCT" and tok.text == "}":
            if depth == 0:
                out.anomalies += 1
            else:
                depth -= 1
        elif depth == 0 and tok.kind == "IDENT" and tok.text in ("resource", "data", "module"):
            wanted = 1 if tok.text == "module" else 2
            labels = []
            j = i + 1
            while j < n and len(labels) < wanted and (lab := _label(tokens[j])) is not None:
                labels.append(lab)
                j += 1
            if len(labels) == wanted and j < n and tokens[j].kind == "PUNCT" and tokens[j].text == "{":
                if tok.text == "resource":
                    out.managed.add((labels[0], labels[1]))
                elif tok.text == "data":
                    out.data.add((labels[0], labels[1]))
                else:
                    out.modules.add(labels[0])
                i = j  # the "{" is handled on the next turn, raising the depth
                continue
            out.anomalies += 1
        i += 1
    if depth:
        out.anomalies += 1
    return out


def headers_from_json(text: str) -> Headers:
    """``resource`` / ``data`` / ``module`` keys of ``.tf.json`` text."""
    out = Headers(set(), set(), set())
    try:
        doc = json.loads(text)
    except ValueError:
        out.anomalies += 1
        return out
    if not isinstance(doc, dict):
        out.anomalies += 1
        return out

    def type_name_pairs(section: object) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for part in section if isinstance(section, list) else [section]:
            if not isinstance(part, dict):
                continue
            for rtype, named in part.items():
                for entry in named if isinstance(named, list) else [named]:
                    if isinstance(entry, dict):
                        pairs.update((rtype, name) for name in entry)
        return pairs

    out.managed = type_name_pairs(doc.get("resource", {}))
    out.data = type_name_pairs(doc.get("data", {}))
    for part in doc["module"] if isinstance(doc.get("module"), list) else [doc.get("module", {})]:
        if isinstance(part, dict):
            out.modules.update(part)
    return out


def merge(parts: list[Headers]) -> Headers:
    total = Headers(set(), set(), set())
    for part in parts:
        total.managed |= part.managed
        total.data |= part.data
        total.modules |= part.modules
        total.anomalies += part.anomalies
    return total


# --------------------------------------------------------------------------- attributes


@dataclass(frozen=True)
class Attribute:
    name: str
    block_path: tuple[str, ...]  # enclosing block headers, outermost first, e.g. ("resource.aws_x.y", "ingress")
    line: int
    end_line: int
    value_kind: str  # literal | interpolation-only | heredoc | call-with-literal | reference | other
    top_level: str  # address of the outermost block: "aws_instance.web", "data.aws_ami.x", "module.m", "locals"


REFERENCE_ROOTS = ("var", "local", "data", "module", "each", "count", "self", "path", "terraform")


def _classify(expr: list[Token]) -> str:
    """Kind of an attribute's value, from token shapes only. No text is kept."""
    meaningful = [t for t in expr if t.kind != "NEWLINE"]
    if not meaningful:
        return "other"
    first = meaningful[0]
    if first.kind == "HEREDOC":
        return "heredoc"
    if first.kind == "STRING":
        return "literal" if first.literal else "interpolation-only"
    if first.kind == "IDENT":
        followed_by_paren = len(meaningful) > 1 and meaningful[1].kind == "PUNCT" and meaningful[1].text == "("
        if followed_by_paren:
            has_literal = any(t.kind == "HEREDOC" or (t.kind == "STRING" and t.literal) for t in meaningful)
            return "call-with-literal" if has_literal else "other"
        if first.text in ("true", "false", "null"):
            return "other"
        return "reference"  # var./local./data./module./resource references
    return "other"


def attributes_from_hcl(text: str) -> list[Attribute]:
    """Every ``name = value`` attribute, with the block path it sits in."""
    tokens = tokenize(text)
    out: list[Attribute] = []
    stack: list[str] = []  # block header strings
    i, n = 0, len(tokens)

    def top_address(path: list[str]) -> str:
        return path[0] if path else ""

    while i < n:
        tok = tokens[i]
        if tok.kind in ("NEWLINE",) or (tok.kind == "PUNCT" and tok.text in (",", ";")):
            i += 1
            continue
        if tok.kind == "PUNCT" and tok.text == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if tok.kind != "IDENT":
            i += 1  # stray token: skip it
            continue
        nxt = tokens[i + 1] if i + 1 < n else None
        if nxt is not None and nxt.kind == "PUNCT" and nxt.text == "=":
            j = i + 2
            expr: list[Token] = []
            depth = 0
            while j < n:
                t = tokens[j]
                if t.kind == "NEWLINE" and depth == 0:
                    break
                if t.kind == "PUNCT" and t.text in "([{":
                    depth += 1
                elif t.kind == "PUNCT" and t.text in ")]}":
                    if depth == 0:
                        break  # the closing brace of a one-line block
                    depth -= 1
                expr.append(t)
                j += 1
            end_line = expr[-1].end_line if expr else tok.line
            out.append(
                Attribute(tok.text, tuple(stack), tok.line, max(end_line, tok.line), _classify(expr),
                          top_address(stack))
            )
            i = j
            continue
        labels = []
        j = i + 1
        while j < n and (lab := _label(tokens[j])) is not None:
            labels.append(lab)
            j += 1
        if j < n and tokens[j].kind == "PUNCT" and tokens[j].text == "{":
            if not stack:  # outermost block: build an address
                kind = tok.text
                if kind == "resource" and len(labels) == 2:
                    header = f"{labels[0]}.{labels[1]}"
                elif kind == "data" and len(labels) == 2:
                    header = f"data.{labels[0]}.{labels[1]}"
                elif kind == "module" and len(labels) == 1:
                    header = f"module.{labels[0]}"
                elif kind in ("variable", "output", "provider") and labels:
                    header = f"{kind}.{labels[0]}"
                else:
                    header = ".".join([kind, *labels])
            else:
                header = ".".join([tok.text, *labels])
            stack.append(header)
            i = j + 1
            continue
        i = j if j > i else i + 1
    return out


# --------------------------------------------------------------------------- D3 additions
# Added for the pool builder (D3 step 2). Nothing above this line was changed in behaviour;
# ``tokenize`` now delegates to ``tokenize_spans``, which returns the same tokens plus offsets.


def interpolations(raw: str, escapes: bool = True) -> list[str]:
    """Inner expression text of every ``${...}`` / ``%{...}`` in ``raw`` (``$${`` and ``%%{`` are literal).

    ``raw`` is a STRING token's text (``escapes=True``: a backslash protects the next character) or a
    heredoc body (``escapes=False``: a backslash is an ordinary character).
    """
    found: list[str] = []
    i, n = 0, len(raw)
    while i < n:
        if escapes and raw[i] == "\\":
            i += 2
        elif raw.startswith(("$${", "%%{"), i):
            i += 3
        elif raw.startswith(("${", "%{"), i):
            j, _newlines = _skip_interpolation(raw, i + 2)
            closed = j <= n and raw[j - 1 : j] == "}"
            found.append(raw[i + 2 : j - 1] if closed else raw[i + 2 : j])
            i = j
        else:
            i += 1
    return found


def heredoc_body(text: str, token: Token) -> str:
    """The lines strictly between a HEREDOC token's header line and its terminator line."""
    lines = text.split("\n")
    return "\n".join(lines[token.line : token.end_line - 1])


@dataclass
class Constructs:
    """Which Terraform constructs a module uses. Flags only; nothing is excluded because of them."""

    has_count: bool = False  # ``count`` as a meta-argument of a resource, data or module block
    has_for_each: bool = False  # ``for_each`` likewise (a dynamic block's for_each is has_dynamic)
    has_dynamic: bool = False
    has_locals: bool = False
    has_lifecycle: bool = False
    has_provisioner: bool = False
    has_terraform_block: bool = False
    has_backend: bool = False
    has_provider_block: bool = False
    required_versions: set[str] = field(default_factory=set)  # terraform { required_version = ... }
    provider_constraints: set[str] = field(default_factory=set)  # "name=constraint"

    @property
    def terraform_required_version(self) -> str | None:
        return "; ".join(sorted(self.required_versions)) or None


_BOOL_FIELDS = (
    "has_count", "has_for_each", "has_dynamic", "has_locals", "has_lifecycle",
    "has_provisioner", "has_terraform_block", "has_backend", "has_provider_block",
)


def merge_constructs(parts: list[Constructs]) -> Constructs:
    total = Constructs()
    for part in parts:
        for name in _BOOL_FIELDS:
            if getattr(part, name):
                setattr(total, name, True)
        total.required_versions |= part.required_versions
        total.provider_constraints |= part.provider_constraints
    return total


def _object_version(expr: list[Token]) -> str:
    """``version`` inside an object-literal expression ``{ source = "...", version = "..." }``, or ""."""
    for k, tok in enumerate(expr[:-2]):
        if tok.kind == "IDENT" and tok.text == "version" and expr[k + 1].text == "=" and expr[k + 2].kind == "STRING":
            return expr[k + 2].text
    return ""


def constructs_from_hcl(text: str) -> Constructs:
    """Flags for the constructs one ``.tf`` file uses, found by block structure (comments, strings and
    heredoc bodies are never read as HCL)."""
    tokens = tokenize(text)
    out = Constructs()
    stack: list[tuple[str, list[str]]] = []  # (block keyword, labels), outermost first
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok.kind == "NEWLINE" or (tok.kind == "PUNCT" and tok.text in (",", ";")):
            i += 1
            continue
        if tok.kind == "PUNCT" and tok.text == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if tok.kind != "IDENT":
            i += 1
            continue
        nxt = tokens[i + 1] if i + 1 < n else None
        if nxt is not None and nxt.kind == "PUNCT" and nxt.text == "=":
            j = i + 2
            expr: list[Token] = []
            depth = 0
            while j < n:
                t = tokens[j]
                if t.kind == "NEWLINE" and depth == 0:
                    break
                if t.kind == "PUNCT" and t.text in "([{":
                    depth += 1
                elif t.kind == "PUNCT" and t.text in ")]}":
                    if depth == 0:
                        break
                    depth -= 1
                expr.append(t)
                j += 1
            kinds = [k for k, _ in stack]
            first = next((t for t in expr if t.kind != "NEWLINE"), None)
            if len(stack) == 1 and kinds[0] in ("resource", "data", "module"):
                if tok.text == "count":
                    out.has_count = True
                elif tok.text == "for_each":
                    out.has_for_each = True
            elif kinds == ["terraform"] and tok.text == "required_version" and first and first.kind == "STRING":
                out.required_versions.add(first.text)
            elif kinds == ["terraform", "required_providers"]:
                if first is not None and first.kind == "STRING":
                    constraint = first.text
                elif first is not None and first.kind == "PUNCT" and first.text == "{":
                    constraint = _object_version(expr)
                else:
                    constraint = ""
                out.provider_constraints.add(f"{tok.text}={constraint}")
            elif kinds == ["provider"] and tok.text == "version" and first and first.kind == "STRING":
                labels = stack[0][1]
                out.provider_constraints.add(f"{labels[0] if labels else ''}={first.text}")
            i = j
            continue
        labels = []
        j = i + 1
        while j < n and (lab := _label(tokens[j])) is not None:
            labels.append(lab)
            j += 1
        if j < n and tokens[j].kind == "PUNCT" and tokens[j].text == "{":
            kinds = [k for k, _ in stack]
            if not stack:
                if tok.text == "locals":
                    out.has_locals = True
                elif tok.text == "terraform":
                    out.has_terraform_block = True
                elif tok.text == "provider":
                    out.has_provider_block = True
            else:
                if tok.text == "dynamic":
                    out.has_dynamic = True
                elif len(stack) == 1 and tok.text == "lifecycle":
                    out.has_lifecycle = True
                elif len(stack) == 1 and tok.text == "provisioner":
                    out.has_provisioner = True
                elif kinds == ["terraform"] and tok.text == "backend":
                    out.has_backend = True
            stack.append((tok.text, labels))
            i = j + 1
            continue
        i = j if j > i else i + 1
    return out


def remove_top_level_blocks(text: str, kinds: tuple[str, ...]) -> str:
    """``text`` without its top-level blocks whose keyword is in ``kinds``, found by brace depth.

    Each removed block takes its whole lines with it when only blanks share them; everything else is
    returned byte for byte. Used by the D3-09 neutralisation (``terraform`` and ``provider`` blocks).
    """
    spans = tokenize_spans(text)
    cuts: list[tuple[int, int]] = []
    depth = 0
    i, n = 0, len(spans)
    while i < n:
        tok, start, _end = spans[i]
        if tok.kind == "PUNCT" and tok.text == "{":
            depth += 1
        elif tok.kind == "PUNCT" and tok.text == "}":
            depth = max(depth - 1, 0)
        elif depth == 0 and tok.kind == "IDENT" and tok.text in kinds:
            j = i + 1
            while j < n and _label(spans[j][0]) is not None:
                j += 1
            if j < n and spans[j][0].kind == "PUNCT" and spans[j][0].text == "{":
                level = 0
                k = j
                block_end = len(text)
                while k < n:
                    t = spans[k][0]
                    if t.kind == "PUNCT" and t.text == "{":
                        level += 1
                    elif t.kind == "PUNCT" and t.text == "}":
                        level -= 1
                        if level == 0:
                            block_end = spans[k][2]
                            break
                    k += 1
                cuts.append((start, block_end))
                i = k + 1
                continue
        i += 1
    out: list[str] = []
    cursor = 0
    for start, end in cuts:
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


# --------------------------------------------------------------------------- object-literal keys (D3 review fix)


@dataclass(frozen=True)
class ObjectEntry:
    """A ``key = value`` entry inside an object literal, e.g. ``variables = { access_key = "..." }``."""

    key: str
    line: int  # line of the key
    end_line: int  # last line of the value
    value_kind: str  # as for Attribute.value_kind
    top_level: str  # address of the outermost block
    container: str  # enclosing blocks, the attribute and outer keys, joined by "."


def _entries_in_expression(expr: list[Token], top_level: str, base: list[str], attribute: str) -> list[ObjectEntry]:
    out: list[ObjectEntry] = []
    names: list[str] = []  # name of each open "{" (the key or attribute it is the value of), "" if none
    kinds: list[str] = []  # "{" or another bracket, for each open bracket
    pending: str | None = attribute
    n = len(expr)
    for i, tok in enumerate(expr):
        if tok.kind == "PUNCT" and tok.text in "([{":
            kinds.append(tok.text)
            if tok.text == "{":
                names.append(pending or "")
            pending = None
            continue
        if tok.kind == "PUNCT" and tok.text in ")]}":
            if kinds:
                if kinds.pop() == "{" and names:
                    names.pop()
            pending = None
            continue
        if not kinds or kinds[-1] != "{" or tok.kind not in ("IDENT", "STRING"):
            continue
        previous = expr[i - 1] if i else None
        starts_item = previous is None or previous.kind == "NEWLINE" or (previous.kind == "PUNCT" and previous.text in "{,")
        sep = expr[i + 1] if i + 1 < n else None
        after = expr[i + 2] if i + 2 < n else None
        if not (starts_item and sep is not None and sep.kind == "PUNCT" and sep.text in ("=", ":")
                and not (sep.text == "=" and after is not None and after.kind == "PUNCT" and after.text in "=>")):
            continue
        j = i + 2
        depth = 0
        value: list[Token] = []
        while j < n:
            t = expr[j]
            if t.kind == "NEWLINE" and depth == 0:
                break
            if t.kind == "PUNCT" and t.text in "([{":
                depth += 1
            elif t.kind == "PUNCT" and t.text in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif t.kind == "PUNCT" and t.text == "," and depth == 0:
                break
            value.append(t)
            j += 1
        end_line = value[-1].end_line if value else tok.line
        container = ".".join([*base, *[x for x in names if x]]) if (base or names) else ""
        out.append(ObjectEntry(tok.text, tok.line, max(end_line, tok.line), _classify(value), top_level, container))
        pending = tok.text
    return out


def object_entries_from_hcl(text: str) -> list[ObjectEntry]:
    """Every entry of every object literal that is the value of an attribute, with the block path it sits in.

    ``attributes_from_hcl`` stops at the attribute; this looks inside its value. Comments, strings and heredoc
    bodies are never read as HCL, and ``==``, ``=>`` and ``for`` expressions are not mistaken for keys.
    """
    tokens = tokenize(text)
    out: list[ObjectEntry] = []
    stack: list[str] = []
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok.kind == "NEWLINE" or (tok.kind == "PUNCT" and tok.text in (",", ";")):
            i += 1
            continue
        if tok.kind == "PUNCT" and tok.text == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if tok.kind != "IDENT":
            i += 1
            continue
        nxt = tokens[i + 1] if i + 1 < n else None
        if nxt is not None and nxt.kind == "PUNCT" and nxt.text == "=":
            j = i + 2
            expr: list[Token] = []
            depth = 0
            while j < n:
                t = tokens[j]
                if t.kind == "NEWLINE" and depth == 0:
                    break
                if t.kind == "PUNCT" and t.text in "([{":
                    depth += 1
                elif t.kind == "PUNCT" and t.text in ")]}":
                    if depth == 0:
                        break
                    depth -= 1
                expr.append(t)
                j += 1
            i = j
            out.extend(_entries_in_expression(expr, stack[0] if stack else "", stack[1:], tok.text))
            continue
        labels = []
        j = i + 1
        while j < n and (lab := _label(tokens[j])) is not None:
            labels.append(lab)
            j += 1
        if j < n and tokens[j].kind == "PUNCT" and tokens[j].text == "{":
            if not stack:
                if tok.text == "resource" and len(labels) == 2:
                    header = f"{labels[0]}.{labels[1]}"
                elif tok.text == "data" and len(labels) == 2:
                    header = f"data.{labels[0]}.{labels[1]}"
                elif tok.text == "module" and len(labels) == 1:
                    header = f"module.{labels[0]}"
                elif tok.text in ("variable", "output", "provider") and labels:
                    header = f"{tok.text}.{labels[0]}"
                else:
                    header = ".".join([tok.text, *labels])
            else:
                header = ".".join([tok.text, *labels])
            stack.append(header)
            i = j + 1
            continue
        i = j if j > i else i + 1
    return out
