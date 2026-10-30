"""Deterministic HCL emitter (D4-08).

Converts an ``HCLModel`` to HCL text that:
- uses 2-space indentation;
- uses LF line endings;
- aligns ``=`` signs within each attribute block (terraform fmt style);
- emits attributes in **sorted key order** within each block;
- emits ``count`` / ``for_each`` before all other attributes;
- emits nested blocks (``Block``) after all attribute assignments;
- emits ``moved`` blocks before all ``resource`` blocks;
- never writes a secret-named attribute with a literal value.

The output is designed to pass ``terraform fmt -check`` with Terraform 1.15.x.

Standard library only.  No DAIL import (D0 gate 1, CLAUDE.md rule 5).
"""

from __future__ import annotations

from typing import Any

from model import (
    Block, CountIndex, EachKey, EachValue, HCLModel, MovedBlock,
    RawExpr, Ref, Resource, SortedList, ToSet, Variable, VarRef,
    _TypedValue,
)

# The pin text, identical to validation/smoke/versions.tf
VERSIONS_TF = """\
terraform {
  required_version = "~> 1.15.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.53.0"
    }
  }
}
"""

# The variable block for db_password (no default — validate does not need a value)
DB_PASSWORD_VAR_TF = """\
variable "db_password" {
  description = "The RDS master password (passed at apply time; no default)."
  sensitive   = true
  type        = string

  validation {
    condition     = length(var.db_password) > 0
    error_message = "db_password must not be empty."
  }
}
"""


# ---------------------------------------------------------------------------
# Internal value serialisation
# ---------------------------------------------------------------------------


def _emit_value(value: Any, indent: int) -> str:
    """Serialise a single attribute value to HCL text (no trailing newline)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return f'"{_escape_string(value)}"'
    if isinstance(value, Ref):
        return value.expr
    if isinstance(value, VarRef):
        return f"var.{value.name}"
    if isinstance(value, RawExpr):
        return value.expr
    if isinstance(value, EachKey):
        return "each.key"
    if isinstance(value, EachValue):
        return "each.value"
    if isinstance(value, CountIndex):
        return "count.index"
    if isinstance(value, SortedList):
        items_str = ", ".join(f'"{_escape_string(s)}"' for s in value.items)
        return f"[{items_str}]"
    if isinstance(value, ToSet):
        items_str = ", ".join(f'"{_escape_string(s)}"' for s in sorted(value.items))
        return f"toset([{items_str}])"
    if isinstance(value, list):
        items_str = ", ".join(_emit_value(item, indent) for item in value)
        return f"[{items_str}]"
    if isinstance(value, Block):
        # Inline block value (rare) — emit as a nested block
        return _emit_block_inline(value, indent)
    raise TypeError(f"Unsupported attribute value type: {type(value).__name__}")


def _escape_string(s: str) -> str:
    """Escape backslashes and double-quotes in a string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _emit_block_inline(block: Block, indent: int) -> str:
    """Emit a Block as inline HCL (used inside attribute lists — not standard but kept for completeness)."""
    lines = ["{"]
    pad = "  " * (indent + 1)
    for key in sorted(block.attrs):
        val = _emit_value(block.attrs[key], indent + 1)
        lines.append(f"{pad}{key} = {val}")
    lines.append("  " * indent + "}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Block-level emission
# ---------------------------------------------------------------------------


def _split_attrs_and_blocks(attrs: dict[str, Any]) -> tuple[dict[str, Any], list[Block]]:
    """Separate plain attrs from Block-valued attrs (nested blocks)."""
    plain: dict[str, Any] = {}
    blocks: list[Block] = []
    for key, val in attrs.items():
        if isinstance(val, Block):
            # Set the block's label to the key if it doesn't have one already
            b = Block(key, val.attrs)
            blocks.append(b)
        else:
            plain[key] = val
    return plain, blocks


def _emit_attrs_block(
    attrs: dict[str, Any],
    extra_blocks: list[Block],
    indent: int,
    count: int | None = None,
    for_each: Any | None = None,
    lifecycle: Block | None = None,
) -> list[str]:
    """Emit all attribute lines and nested block lines for one resource/block body.

    Returns a list of text lines (without trailing newline) at ``indent`` level.
    Alignment: all ``=`` signs in the attribute section are padded to the same column.
    ``count`` and ``for_each`` appear first, separated by a blank line from the rest.
    """
    lines: list[str] = []
    pad = "  " * indent

    plain_attrs, embedded_blocks = _split_attrs_and_blocks(attrs)
    all_blocks = embedded_blocks + extra_blocks
    if lifecycle:
        all_blocks.append(lifecycle)

    # Build the attribute section (sorted keys)
    meta_pairs: list[tuple[str, str]] = []
    if count is not None:
        meta_pairs.append(("count", str(count)))
    if for_each is not None:
        meta_pairs.append(("for_each", _emit_value(for_each, indent)))

    attr_pairs: list[tuple[str, str]] = []
    for key in sorted(plain_attrs):
        attr_pairs.append((key, _emit_value(plain_attrs[key], indent)))

    # Alignment: find the longest key in the main section (not meta)
    def _pad_pairs(pairs: list[tuple[str, str]]) -> list[str]:
        if not pairs:
            return []
        max_key = max(len(k) for k, _ in pairs)
        result = []
        for k, v in pairs:
            # Pad key so that = is aligned
            result.append(f"{pad}{k:{max_key}} = {v}")
        return result

    if meta_pairs:
        lines.extend(_pad_pairs(meta_pairs))
        if attr_pairs or all_blocks:
            lines.append("")  # blank line after count/for_each

    lines.extend(_pad_pairs(attr_pairs))

    # Nested blocks
    for block in all_blocks:
        if attr_pairs or meta_pairs:
            lines.append("")  # blank line before nested block
        lines.append(f"{pad}{block.label} {{")
        block_plain, block_embedded = _split_attrs_and_blocks(block.attrs)
        lines.extend(_emit_attrs_block(block_plain, block_embedded, indent + 1))
        lines.append(f"{pad}}}")

    return lines


# ---------------------------------------------------------------------------
# Top-level emitters
# ---------------------------------------------------------------------------


def emit(model: HCLModel) -> str:
    """Emit the full HCL text for all resources and moved blocks in ``model``."""
    sections: list[str] = []

    # moved blocks first
    for moved in model.moved:
        block_lines = [
            "moved {",
            f"  from = {moved.from_addr.expr}",
            f"  to   = {moved.to_addr.expr}",
            "}",
        ]
        sections.append("\n".join(block_lines))

    # resource blocks
    for addr, resource in model.resources.items():
        header = f'resource "{resource.type}" "{resource.name}" {{'
        body_lines = _emit_attrs_block(
            resource.attrs,
            resource.blocks,
            indent=1,
            count=resource.count,
            for_each=resource.for_each,
            lifecycle=resource.lifecycle,
        )
        block = [header] + body_lines + ["}"]
        sections.append("\n".join(block))

    return "\n\n".join(sections) + "\n" if sections else ""


def emit_versions() -> str:
    """Return the pinned versions.tf content (identical to validation/smoke/versions.tf)."""
    return VERSIONS_TF


def emit_variables(model: HCLModel) -> str:
    """Emit variable blocks from ``model.variables``."""
    sections: list[str] = []
    for var_name, variable in model.variables.items():
        header = f'variable "{var_name}" {{'
        body_lines = _emit_attrs_block(variable.attrs, [], indent=1)
        block = [header] + body_lines + ["}"]
        sections.append("\n".join(block))
    return "\n\n".join(sections) + "\n" if sections else ""


def emit_db_password_variable() -> str:
    """Return the standard db_password variable block."""
    return DB_PASSWORD_VAR_TF

