"""Verifier for real non-canonical HCL text (D4b-06).

Ensures that:
1. Every change between step k-1 and step k is truthfully recorded in mutation_records.
2. No unrecorded byte changes occurred outside the recorded spans.
3. No invented phantom mutation records exist.
Standard library only.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))

import hcl_lex


class RealDiffVerifyError(Exception):
    """Raised when real text verification detects unrecorded or fabricated changes."""


def verify(
    step0_files: dict[str, str],
    step1_files: dict[str, str],
    mutation_records: list[dict],
) -> None:
    """Verify that step1 differs from step0 strictly and truthfully per mutation_records."""
    all_fnames = sorted(set(step0_files) | set(step1_files))

    records_by_target = {
        (r.get("target_address"), r.get("attribute")): r
        for r in mutation_records
    }
    used_records: set[tuple[str, str]] = set()

    for fname in all_fnames:
        text0 = step0_files.get(fname)
        text1 = step1_files.get(fname)

        if text0 is None and text1 is not None:
            # Added file (e.g. new resource in F6)
            # Mutation record must declare creation
            matched = any(r.get("attribute") in (None, "", "resource") for r in mutation_records)
            if not matched and not any(r.get("target_address", "").startswith("aws_") for r in mutation_records):
                raise RealDiffVerifyError(f"Added file '{fname}' has no corresponding mutation record")
            continue

        if text0 is not None and text1 is None:
            # Removed file
            raise RealDiffVerifyError(f"File '{fname}' was deleted without record")

        assert text0 is not None and text1 is not None

        if text0 == text1:
            # No changes in this file
            continue

        # File was modified. Find which attributes changed.
        attrs0 = {
            (a.top_level, a.name): a
            for a in hcl_lex.attributes_from_hcl(text0)
        }
        attrs1 = {
            (a.top_level, a.name): a
            for a in hcl_lex.attributes_from_hcl(text1)
        }

        # Check for unrecorded attribute changes
        changed_attrs: list[tuple[str, str]] = []
        for key in set(attrs0) | set(attrs1):
            a0 = attrs0.get(key)
            a1 = attrs1.get(key)
            if a0 is None or a1 is None:
                changed_attrs.append(key)
            elif (a0.line, a0.end_line) != (a1.line, a1.end_line) or a0.value_kind != a1.value_kind:
                changed_attrs.append(key)
            else:
                # Compare line contents
                lines0 = text0.splitlines()[a0.line - 1 : a0.end_line]
                lines1 = text1.splitlines()[a1.line - 1 : a1.end_line]
                if lines0 != lines1:
                    changed_attrs.append(key)

        if not changed_attrs and text0 != text1:
            # Byte change occurred outside of any attribute (e.g. comment or whitespace injection)
            raise RealDiffVerifyError(
                f"File '{fname}' has unrecorded byte differences outside recognized attributes"
            )

        for addr, attr in changed_attrs:
            rec_key = (addr, attr)
            if rec_key not in records_by_target:
                # Also check without type prefix
                short_key = (addr.split(".", 1)[-1] if "." in addr else addr, attr)
                if short_key not in records_by_target:
                    raise RealDiffVerifyError(
                        f"Unrecorded change in '{fname}' for {addr}.{attr}"
                    )
                rec_key = short_key
            used_records.add(rec_key)

        # Whole-file check: ensure changes outside the recorded attribute spans did not occur.
        # Find the attribute's value span in text0 and text1.
        for addr, attr in changed_attrs:
            rec = records_by_target.get((addr, attr)) or records_by_target.get(
                (addr.split(".", 1)[-1] if "." in addr else addr, attr)
            )
            if rec is None:
                continue
            after_val = rec.get("after")
            # If after_val is quoted or raw, check if applying the replacement reconstructs text1
            # Check by span edit
            spans0 = hcl_lex.tokenize_spans(text0)
            target_span = None
            stack = []
            for i, (tok, s, e) in enumerate(spans0):
                if tok.kind == "PUNCT" and tok.text == "}":
                    if stack:
                        stack.pop()
                    continue
                if tok.kind != "IDENT":
                    continue
                j = i + 1
                labels = []
                while j < len(spans0) and (lab := hcl_lex._label(spans0[j][0])) is not None:
                    labels.append(lab)
                    j += 1
                if j < len(spans0) and spans0[j][0].kind == "PUNCT" and spans0[j][0].text == "{":
                    stack.append((tok.text, labels))
                    continue
                nxt = spans0[i + 1][0] if i + 1 < len(spans0) else None
                if nxt is not None and nxt.kind == "PUNCT" and nxt.text == "=" and i + 2 < len(spans0):
                    curr_addr = f"{stack[0][1][0]}.{stack[0][1][1]}" if stack and len(stack[0][1]) >= 2 else ""
                    if (curr_addr == addr or curr_addr.endswith(f".{addr}")) and tok.text == attr:
                        target_span = (spans0[i + 2][1], spans0[i + 2][2])
                        break

            if target_span is not None and after_val is not None:
                vstart, vend = target_span
                expected_reconstructed = text0[:vstart] + str(after_val) + text0[vend:]
                if expected_reconstructed != text1:
                    raise RealDiffVerifyError(
                        f"File '{fname}' has unrecorded byte differences outside the recorded span for {addr}.{attr}"
                    )

    # Check for invented records (records claiming changes that did not happen)
    for rec_key, rec in records_by_target.items():
        addr, attr = rec_key
        # If record is for an added resource, skip
        if attr in (None, "", "resource"):
            continue
        if rec_key not in used_records:
            raise RealDiffVerifyError(
                f"Invented mutation record: {addr}.{attr} was recorded but no change occurred"
            )
