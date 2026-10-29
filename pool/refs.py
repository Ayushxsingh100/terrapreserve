"""Resource references and the E07 dangling-reference check (D3-06).

A module is self-contained only if every ``aws_X.name`` it refers to is defined by one of its files. The
archive keeps regular files only, so a ``.tf`` that is a git symlink is missing from it (docs/D3_CARRYOVER.md
item 2); a reference to a resource that lived in that file then has no definition. This catches it.

Only roots that look like an ``aws_`` resource type are collected: ``var.``, ``local.``, ``data.``,
``module.``, ``each.``, ``count.``, ``self.``, ``path.`` and ``terraform.`` never match, and an ``aws_``-looking
word after a dot (``var.aws_vpc.main``, ``data.aws_ami.x``) is an attribute path, not a root. References are
read from expressions, from ``${...}`` / ``%{...}`` inside strings, and from the interpolations in heredoc
bodies. Comments and literal string text are ignored. Standard library and ``sources/hcl_lex`` only.
"""

from __future__ import annotations

import hcl_lex
import lexical_crosscheck  # ignored_by_terraform: Terraform's own file-selection rule

RESOURCE_ROOT_PREFIX = "aws_"


def _from_tokens(tokens: list[hcl_lex.Token], text: str, found: set[tuple[str, str]]) -> None:
    n = len(tokens)
    for i, tok in enumerate(tokens):
        if tok.kind == "STRING":
            for inner in hcl_lex.interpolations(tok.text):
                _scan(inner, found)
        elif tok.kind == "HEREDOC":
            for inner in hcl_lex.interpolations(hcl_lex.heredoc_body(text, tok), escapes=False):
                _scan(inner, found)
        elif tok.kind == "IDENT" and tok.text.startswith(RESOURCE_ROOT_PREFIX) and i + 2 < n:
            dot, name = tokens[i + 1], tokens[i + 2]
            if dot.kind != "PUNCT" or dot.text != "." or name.kind not in ("IDENT", "NUMBER"):
                continue
            previous = tokens[i - 1] if i else None
            if previous is not None and previous.kind == "PUNCT" and previous.text == ".":
                continue  # an attribute path such as var.aws_vpc.main or data.aws_ami.x
            found.add((tok.text, name.text))


def _scan(text: str, found: set[tuple[str, str]]) -> None:
    _from_tokens(hcl_lex.tokenize(text), text, found)


def referenced_addresses(text: str) -> set[tuple[str, str]]:
    """``(type, name)`` of every ``aws_`` resource the text refers to."""
    found: set[tuple[str, str]] = set()
    _scan(text, found)
    return found


def dangling_references(files: dict[str, str]) -> list[str]:
    """Sorted ``type.name`` addresses that a module's files refer to but none of them defines.

    ``files`` maps a file name to its text; files that Terraform ignores define and refer to nothing.
    """
    defined: set[tuple[str, str]] = set()
    referenced: set[tuple[str, str]] = set()
    for name in sorted(files):
        if lexical_crosscheck.ignored_by_terraform(name):
            continue
        if name.endswith(".tf.json"):
            defined |= hcl_lex.headers_from_json(files[name]).managed
        elif name.endswith(".tf"):
            defined |= hcl_lex.headers_from_hcl(files[name]).managed
            referenced |= referenced_addresses(files[name])
    return sorted(f"{rtype}.{rname}" for rtype, rname in referenced - defined)
