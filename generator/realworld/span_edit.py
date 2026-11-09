"""Span-edit operator layer for native modules (D4b-05).

Provides byte-exact AST span replacements on real non-canonical HCL text without
corrupting comments, formatting, or unaffected spans.
Standard library only.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))

import hcl_lex


@dataclass(frozen=True)
class SpanEditResult:
    success: bool
    new_content: str = ""
    start_offset: int = -1
    end_offset: int = -1
    old_value: str = ""
    new_value: str = ""
    error: str = ""


def apply_span_edit(
    content: str,
    target_address: str,
    target_attribute: str,
    new_value: str,
) -> SpanEditResult:
    """Find target_address.target_attribute in content and replace its span with new_value."""
    spans = hcl_lex.tokenize_spans(content)
    n = len(spans)
    i = 0
    stack: list[tuple[str, list[str]]] = []  # (block_type, labels)

    while i < n:
        tok, start, end = spans[i]
        if tok.kind == "PUNCT" and tok.text == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if tok.kind != "IDENT":
            i += 1
            continue

        # Check block declaration
        j = i + 1
        labels: list[str] = []
        while j < n and (lab := hcl_lex._label(spans[j][0])) is not None:
            labels.append(lab)
            j += 1
        if j < n and spans[j][0].kind == "PUNCT" and spans[j][0].text == "{":
            stack.append((tok.text, labels))
            i = j + 1
            continue

        # Check attribute assignment
        nxt = spans[i + 1][0] if i + 1 < n else None
        if nxt is not None and nxt.kind == "PUNCT" and nxt.text == "=":
            attr_name = tok.text
            val_idx = i + 2
            if val_idx < n:
                val_tok, vstart, vend = spans[val_idx]
                # Check current address
                curr_addr = ""
                if stack and stack[0][0] in ("resource", "data"):
                    curr_addr = f"{stack[0][1][0]}.{stack[0][1][1]}" if len(stack[0][1]) >= 2 else stack[0][0]
                elif stack:
                    curr_addr = stack[0][0]

                if curr_addr == target_address and attr_name == target_attribute:
                    # Check preconditions: literal value
                    if val_tok.kind not in ("STRING", "NUMBER", "IDENT"):
                        return SpanEditResult(
                            success=False,
                            error=f"Attribute {attr_name} has non-literal value kind {val_tok.kind}",
                        )

                    old_val = content[vstart:vend]
                    new_content = content[:vstart] + new_value + content[vend:]
                    return SpanEditResult(
                        success=True,
                        new_content=new_content,
                        start_offset=vstart,
                        end_offset=vend,
                        old_value=old_val,
                        new_value=new_value,
                    )
            i = val_idx
            continue
        i += 1

    return SpanEditResult(
        success=False,
        error=f"Target {target_address}.{target_attribute} not found in content",
    )

