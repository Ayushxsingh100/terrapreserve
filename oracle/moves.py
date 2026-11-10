"""Moves (registry 2.3, D5-13).

Terraform 1.15.8 does not put ``moved`` blocks in ``terraform show -json``, and an offline plan with no prior state
has no ``previous_address``. Decided by the authors on 10 Nov 2026 (D5-13): the oracle reads the ``moved { from =
..., to = ... }`` blocks, and nothing else, from the step's ``.tf`` files. Implicit moves when ``count`` is added to
or removed from a single-instance resource (registry 2.3, C-76: ``x`` to ``x[0]`` and back) are derived from the
instance addresses of the two configurations. There is no implicit move into or out of ``for_each``.

Standard library only.
"""

from __future__ import annotations

import re
from pathlib import Path

_ADDR = r'[A-Za-z_][A-Za-z0-9_\-]*(?:\[[^\]\n]*\])?(?:\.[A-Za-z_][A-Za-z0-9_\-]*(?:\[[^\]\n]*\])?)*'
_MOVED = re.compile(r'(?:^|\n)[ \t]*moved[ \t]*\{(?P<body>[^{}]*)\}')
_FROM = re.compile(r'(?:^|\n)[ \t]*from[ \t]*=[ \t]*(?P<a>' + _ADDR + r')')
_TO = re.compile(r'(?:^|\n)[ \t]*to[ \t]*=[ \t]*(?P<a>' + _ADDR + r')')


def strip_comments(text: str) -> str:
    """Remove ``#``, ``//`` and ``/* */`` comments outside double-quoted strings (strings are kept)."""
    out: list[str] = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif c == "#" or text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def parse_moved(text: str) -> list[tuple[str, str]]:
    """The (from, to) addresses of every ``moved`` block in one file's text, in written order."""
    pairs = []
    for m in _MOVED.finditer(strip_comments(text)):
        body = m.group("body")
        f, t = _FROM.search(body), _TO.search(body)
        if f and t:
            pairs.append((f.group("a"), t.group("a")))
    return pairs


def read_moved(step_dir: Path) -> list[tuple[str, str]]:
    """Every ``moved`` block of a step (its ``.tf`` files in name order)."""
    out: list[tuple[str, str]] = []
    for p in sorted(step_dir.glob("*.tf")):
        out.extend(parse_moved(p.read_text(encoding="utf-8")))
    return out


def _covers(prefix: str, addr: str) -> str | None:
    """If ``addr`` is ``prefix`` or inside it (an instance or a nested address), the rest of ``addr``; else None."""
    if addr == prefix:
        return ""
    if addr.startswith(prefix) and addr[len(prefix)] in "[.":
        return addr[len(prefix):]
    return None


def parent_to_child_map(moved: list[tuple[str, str]], parent_addrs: set[str], child_addrs: set[str]) -> dict[str, str]:
    """Map each parent instance address to its child address after following moves (registry 2.3).

    Explicit ``moved`` blocks (written in the child) first; then the implicit ``count`` move: a parent ``x`` with
    no child ``x`` becomes ``x[0]`` when the child has ``x[0]`` and no parent ``x[0]`` exists, and the reverse.
    Addresses that do not move map to themselves. Only addresses present in the parent are mapped."""
    out: dict[str, str] = {}
    for a in parent_addrs:
        new = a
        for frm, to in moved:
            rest = _covers(frm, new)
            if rest is not None:
                new = to + rest
        out[a] = new
    for a, new in list(out.items()):
        if new in child_addrs or a != new:
            continue
        if f"{a}[0]" in child_addrs and f"{a}[0]" not in parent_addrs:
            out[a] = f"{a}[0]"
        elif a.endswith("[0]") and a[:-3] in child_addrs and a[:-3] not in parent_addrs:
            out[a] = a[:-3]
    return out
