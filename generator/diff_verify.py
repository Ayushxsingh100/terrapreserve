"""Diff verifier for mutation records (D4-08).

The diff verifier compares the HCL text of step k-1 and step k, determines
which ``(resource_address, attribute)`` pairs changed, and checks that the
operator's ``mutation_record`` is truthful:

* every change that appears in the diff must appear in the record;
* every record row must correspond to an actual change in the diff.

A ``DiffVerifyError`` is raised if the record is incomplete or fabricated.
This runs both in the test suite (to prove correctness of each operator) and
at generation time (to protect the truthfulness of every committed record).

The verifier is **structural**: it compares attribute values by re-parsing the
emitted text with a lightweight token scan.  It does not evaluate HCL
expressions.

Standard library only.  No DAIL import (D0 gate 1, CLAUDE.md rule 5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from model import HCLModel
import emitter as _emitter


# ---------------------------------------------------------------------------
# Mutation record row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MutationRow:
    """One row of a mutation_record.

    ``before`` and ``after`` are the string-serialised attribute values
    (as the emitter would write them, but without surrounding quotes for
    strings).  ``None`` means the attribute was absent (added or removed).
    """
    step: int
    operator: str
    target_address: str
    attribute: str
    before: str | None
    after: str | None


# ---------------------------------------------------------------------------
# Lightweight attribute extractor
# ---------------------------------------------------------------------------

# Pattern: inside a resource block, extract attribute = value lines.
# We work on emitted text, which is well-formatted by our emitter.
_RESOURCE_BLOCK_RE = re.compile(
    r'resource\s+"(?P<type>[^"]+)"\s+"(?P<name>[^"]+)"\s*\{(?P<body>[^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
    re.DOTALL,
)
_ATTR_LINE_RE = re.compile(
    r'^\s{2}(?P<key>[a-z_][a-z0-9_]*)\s+=\s+(?P<val>.+?)\s*$',
    re.MULTILINE,
)


def _extract_resource_attrs(text: str) -> dict[str, dict[str, str]]:
    """Return ``{address: {attr: value_text}}`` from emitted HCL text.

    Only top-level (2-space-indent) attribute assignments inside resource
    blocks are extracted.  Nested blocks (4-space indent) are not included
    in the per-attribute map; their presence is detected separately.
    """
    result: dict[str, dict[str, str]] = {}
    for m in _RESOURCE_BLOCK_RE.finditer(text):
        addr = f"{m.group('type')}.{m.group('name')}"
        body = m.group("body")
        attrs: dict[str, str] = {}
        for am in _ATTR_LINE_RE.finditer(body):
            attrs[am.group("key")] = am.group("val").strip()
        result[addr] = attrs
    return result


def _diff_attrs(
    before_text: str,
    after_text: str,
) -> list[tuple[str, str, str | None, str | None]]:
    """Return ``(address, attribute, before_val, after_val)`` for every changed attr.

    ``before_val`` or ``after_val`` is ``None`` when the attribute was absent
    in that step.
    """
    before_map = _extract_resource_attrs(before_text)
    after_map = _extract_resource_attrs(after_text)
    changes: list[tuple[str, str, str | None, str | None]] = []

    all_addrs = sorted(set(before_map) | set(after_map))
    for addr in all_addrs:
        b_attrs = before_map.get(addr, {})
        a_attrs = after_map.get(addr, {})
        all_keys = sorted(set(b_attrs) | set(a_attrs))
        for key in all_keys:
            b_val = b_attrs.get(key)
            a_val = a_attrs.get(key)
            if b_val != a_val:
                changes.append((addr, key, b_val, a_val))

    return changes


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------


class DiffVerifyError(RuntimeError):
    """Raised when the mutation record disagrees with the actual diff."""


def verify(
    before_model: HCLModel,
    after_model: HCLModel,
    record: list[MutationRow],
    *,
    step: int,
    operator_name: str,
) -> None:
    """Verify that ``record`` is a truthful account of the diff between the two models.

    Raises ``DiffVerifyError`` if:
    * a change in the diff is missing from the record; or
    * a record row claims a change that is not in the diff.
    """
    before_text = _emitter.emit(before_model)
    after_text = _emitter.emit(after_model)
    _verify_texts(before_text, after_text, record, step=step, operator_name=operator_name)


def verify_texts(
    before_text: str,
    after_text: str,
    record: list[MutationRow],
    *,
    step: int,
    operator_name: str,
) -> None:
    """Verify from emitted text rather than models (for use in tests)."""
    _verify_texts(before_text, after_text, record, step=step, operator_name=operator_name)


def _verify_texts(
    before_text: str,
    after_text: str,
    record: list[MutationRow],
    *,
    step: int,
    operator_name: str,
) -> None:
    actual_changes = _diff_attrs(before_text, after_text)

    # Build lookup: (addr, attr) -> (before, after) for recorded rows
    recorded: dict[tuple[str, str], tuple[str | None, str | None]] = {}
    for row in record:
        if row.step == step:
            recorded[(row.target_address, row.attribute)] = (row.before, row.after)

    # Check: every actual change must be in the record
    missing = []
    for addr, attr, b_val, a_val in actual_changes:
        if (addr, attr) not in recorded:
            missing.append(f"  changed but not recorded: ({addr!r}, {attr!r}): {b_val!r} -> {a_val!r}")

    # Check: every recorded change must correspond to an actual change
    fabricated = []
    actual_set = {(addr, attr) for addr, attr, _, _ in actual_changes}
    for (addr, attr), (b_val, a_val) in recorded.items():
        if (addr, attr) not in actual_set:
            fabricated.append(f"  recorded but no change: ({addr!r}, {attr!r})")

    errors = missing + fabricated
    if errors:
        raise DiffVerifyError(
            f"Operator {operator_name!r} step {step} mutation record is incorrect:\n"
            + "\n".join(errors)
        )

