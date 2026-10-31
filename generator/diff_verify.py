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
_TOP_ATTR_RE = re.compile(
    r'^\s{2}(?P<key>[a-z_][a-z0-9_]*)\s+=\s+(?P<val>.+?)\s*$',
    re.MULTILINE,
)
_NESTED_BLOCK_RE = re.compile(
    r'^\s{2}(?P<label>[a-z_][a-z0-9_]*)\s*\{(?P<inner>[^{}]*)\}',
    re.MULTILINE | re.DOTALL,
)
_INNER_ATTR_RE = re.compile(
    r'^\s{4}(?P<key>[a-z_][a-z0-9_]*)\s+=\s+(?P<val>.+?)\s*$',
    re.MULTILINE,
)


def _diff_attrs(
    before_text: str,
    after_text: str,
) -> list[tuple[str, str, str | None, str | None]]:
    """Return ``(address, attribute, before_val, after_val)`` for every changed attr."""
    b_resources = {f"{m.group('type')}.{m.group('name')}": m.group("body") for m in _RESOURCE_BLOCK_RE.finditer(before_text)}
    a_resources = {f"{m.group('type')}.{m.group('name')}": m.group("body") for m in _RESOURCE_BLOCK_RE.finditer(after_text)}

    changes: list[tuple[str, str, str | None, str | None]] = []
    all_addrs = sorted(set(b_resources) | set(a_resources))

    for addr in all_addrs:
        b_body = b_resources.get(addr)
        a_body = a_resources.get(addr)
        if b_body is None:
            # Whole resource added
            assert a_body is not None
            for am in _TOP_ATTR_RE.finditer(a_body):
                changes.append((addr, am.group("key"), None, am.group("val").strip()))
            for bm in _NESTED_BLOCK_RE.finditer(a_body):
                for im in _INNER_ATTR_RE.finditer(bm.group("inner")):
                    changes.append((addr, im.group("key"), None, im.group("val").strip()))
            continue
        if a_body is None:
            # Whole resource removed
            assert b_body is not None
            for am in _TOP_ATTR_RE.finditer(b_body):
                changes.append((addr, am.group("key"), am.group("val").strip(), None))
            for bm in _NESTED_BLOCK_RE.finditer(b_body):
                for im in _INNER_ATTR_RE.finditer(bm.group("inner")):
                    changes.append((addr, im.group("key"), im.group("val").strip(), None))
            continue

        # Resource modified:
        # 1. Top-level attrs
        b_top = {am.group("key"): am.group("val").strip() for am in _TOP_ATTR_RE.finditer(b_body)}
        a_top = {am.group("key"): am.group("val").strip() for am in _TOP_ATTR_RE.finditer(a_body)}
        for k in sorted(set(b_top) | set(a_top)):
            if b_top.get(k) != a_top.get(k):
                changes.append((addr, k, b_top.get(k), a_top.get(k)))

        # 2. Nested blocks
        b_blocks = list(_NESTED_BLOCK_RE.finditer(b_body))
        a_blocks = list(_NESTED_BLOCK_RE.finditer(a_body))
        if len(b_blocks) == len(a_blocks):
            for bb, ab in zip(b_blocks, a_blocks):
                if bb.group("inner") != ab.group("inner"):
                    b_in = {im.group("key"): im.group("val").strip() for im in _INNER_ATTR_RE.finditer(bb.group("inner"))}
                    a_in = {im.group("key"): im.group("val").strip() for im in _INNER_ATTR_RE.finditer(ab.group("inner"))}
                    for k in sorted(set(b_in) | set(a_in)):
                        if b_in.get(k) != a_in.get(k):
                            changes.append((addr, k, b_in.get(k), a_in.get(k)))
        else:
            b_texts = [bb.group("inner") for bb in b_blocks]
            a_texts = [ab.group("inner") for ab in a_blocks]
            for bb in b_blocks:
                if bb.group("inner") not in a_texts:
                    for im in _INNER_ATTR_RE.finditer(bb.group("inner")):
                        changes.append((addr, im.group("key"), im.group("val").strip(), None))
            for ab in a_blocks:
                if ab.group("inner") not in b_texts:
                    for im in _INNER_ATTR_RE.finditer(ab.group("inner")):
                        changes.append((addr, im.group("key"), None, im.group("val").strip()))

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
    value_mismatches = []
    actual_dict = {(addr, attr): (b, a) for addr, attr, b, a in actual_changes}
    actual_set = set(actual_dict)
    for (addr, attr), (r_before, r_after) in recorded.items():
        if (addr, attr) not in actual_set:
            fabricated.append(f"  recorded but no change: ({addr!r}, {attr!r})")
        else:
            act_b, act_a = actual_dict[(addr, attr)]
            if r_before is not None and act_b is not None:
                if r_before.strip('"\'') != act_b.strip('"\'') and r_before != act_b:
                    value_mismatches.append(
                        f"  value mismatch ({addr!r}, {attr!r}) before: recorded {r_before!r} vs actual {act_b!r}"
                    )
            if r_after is not None and act_a is not None:
                if r_after.strip('"\'') != act_a.strip('"\'') and r_after != act_a:
                    value_mismatches.append(
                        f"  value mismatch ({addr!r}, {attr!r}) after: recorded {r_after!r} vs actual {act_a!r}"
                    )

    errors = missing + fabricated + value_mismatches
    if errors:
        raise DiffVerifyError(
            f"Operator {operator_name!r} step {step} mutation record is incorrect:\n"
            + "\n".join(errors)
        )

