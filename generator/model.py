"""Resource model for the D4a scenario generator (D4-08).

An ordered mapping of ``type.name`` to resource descriptors, plus nested
blocks, ``count``/``for_each``, ``moved`` blocks, and typed value wrappers
(references, variable references, raw HCL expressions).

The model acts on attributes; the HCL emitter in ``emitter.py`` converts it
to text.  Operators in ``operators/`` mutate model instances and record what
they changed.

**Secret rule:** any attribute whose name matches the credential-like pattern
and whose value is a plain Python string (a literal) is rejected at
construction time.  Credential-like attribute names must be wrapped in
``VarRef`` or another typed value.

Standard library only.  No DAIL import (D0 gate 1, CLAUDE.md rule 5).
"""

from __future__ import annotations

import copy
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Secret-name guard
# ---------------------------------------------------------------------------

_SECRET_RE = re.compile(
    r"password|passwd|secret|access_key|secret_key|token|private_key|api_key|"
    r"user_data|connection_string",
    re.IGNORECASE,
)


def _is_secret_name(name: str) -> bool:
    return bool(_SECRET_RE.search(name))


def _check_no_secret_literal(attrs: dict[str, Any]) -> None:
    """Raise ValueError if any secret-named attribute holds a plain string literal."""
    for key, val in attrs.items():
        if _is_secret_name(key) and isinstance(val, str):
            raise ValueError(
                f"Attribute {key!r} appears to hold a literal string; "
                "wrap it in VarRef, Ref, or RawExpr to prevent accidental secret emission."
            )


# ---------------------------------------------------------------------------
# Typed value wrappers
# ---------------------------------------------------------------------------


class _TypedValue:
    """Base class for non-literal HCL values."""


@dataclass(frozen=True)
class Ref(_TypedValue):
    """A resource attribute reference, e.g. ``aws_vpc.main.id``."""
    expr: str

    def __str__(self) -> str:
        return self.expr


@dataclass(frozen=True)
class VarRef(_TypedValue):
    """A variable reference rendered as ``var.<name>``."""
    name: str

    def __str__(self) -> str:
        return f"var.{self.name}"


@dataclass(frozen=True)
class RawExpr(_TypedValue):
    """A raw HCL expression emitted verbatim (e.g. type constraints, function calls)."""
    expr: str

    def __str__(self) -> str:
        return self.expr


@dataclass(frozen=True)
class EachKey(_TypedValue):
    """The ``each.key`` expression, used inside ``for_each`` resources."""
    def __str__(self) -> str:
        return "each.key"


@dataclass(frozen=True)
class EachValue(_TypedValue):
    """The ``each.value`` expression, used inside ``for_each`` resources."""
    def __str__(self) -> str:
        return "each.value"


@dataclass(frozen=True)
class CountIndex(_TypedValue):
    """The ``count.index`` expression, used inside ``count`` resources."""
    def __str__(self) -> str:
        return "count.index"


@dataclass(frozen=True)
class SortedList(_TypedValue):
    """A list of strings emitted in sorted order (e.g. ``cidr_blocks``)."""
    items: tuple[str, ...]

    def __init__(self, items: list[str]) -> None:
        object.__setattr__(self, "items", tuple(sorted(items)))

    def __str__(self) -> str:
        return repr(sorted(self.items))


@dataclass(frozen=True)
class ToSet(_TypedValue):
    """``toset([...])`` — used as the ``for_each`` value for a set of strings."""
    items: tuple[str, ...]

    def __init__(self, items: list[str]) -> None:
        object.__setattr__(self, "items", tuple(sorted(items)))

    def __str__(self) -> str:
        inner = ", ".join(f'"{s}"' for s in sorted(self.items))
        return f"toset([{inner}])"


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------


@dataclass
class Block:
    """A nested block inside a resource (e.g. ``ingress``, ``egress``, ``lifecycle``).

    ``attrs`` follows the same rules as ``Resource.attrs``:
    plain Python values for literals; typed wrappers for references.
    Nested ``Block`` instances are allowed as values.
    """
    label: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def copy(self) -> "Block":
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Variable
# ---------------------------------------------------------------------------


@dataclass
class Variable:
    """A Terraform ``variable`` block (for ``variables.tf``)."""
    name: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def copy(self) -> "Variable":
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# MovedBlock
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MovedBlock:
    """A ``moved { from = ... to = ... }`` block."""
    from_addr: Ref
    to_addr: Ref


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------


class Resource:
    """A single Terraform resource block.

    Parameters
    ----------
    type_:
        The resource type (e.g. ``aws_vpc``).
    name:
        The resource label (e.g. ``main``).
    attrs:
        Attribute dictionary.  Keys are strings.  Values are:
        - ``str``: string literal (must not be secret-named)
        - ``int``, ``float``: number
        - ``bool``: boolean
        - ``None``: null
        - ``list``: list literal (items rendered as strings)
        - ``_TypedValue`` subclass: reference / expression
        - ``Block``: nested block
    count:
        Integer ``count`` meta-argument (mutually exclusive with ``for_each``).
    for_each:
        ``ToSet`` or ``Ref`` ``for_each`` expression.
    blocks:
        Ordered list of additional named nested blocks.  Can also be embedded
        directly in ``attrs`` as ``Block`` values (for single-occurrence
        blocks); list values here appear after all attribute assignments.
    lifecycle:
        Optional ``lifecycle`` block.
    """

    def __init__(
        self,
        type_: str,
        name: str,
        attrs: dict[str, Any] | None = None,
        *,
        count: int | None = None,
        for_each: _TypedValue | None = None,
        blocks: list[Block] | None = None,
        lifecycle: Block | None = None,
    ) -> None:
        if count is not None and for_each is not None:
            raise ValueError("count and for_each are mutually exclusive")
        self.type: str = type_
        self.name: str = name
        self.attrs: dict[str, Any] = attrs or {}
        _check_no_secret_literal(self.attrs)
        self.count: int | None = count
        self.for_each: _TypedValue | None = for_each
        self.blocks: list[Block] = blocks or []
        self.lifecycle: Block | None = lifecycle

    @property
    def address(self) -> str:
        return f"{self.type}.{self.name}"

    def copy(self) -> "Resource":
        return copy.deepcopy(self)

    def set_attr(self, key: str, value: Any) -> None:
        """Set (or overwrite) one attribute, enforcing the secret rule."""
        if _is_secret_name(key) and isinstance(value, str):
            raise ValueError(
                f"Attribute {key!r} would hold a literal string; "
                "use VarRef or RawExpr."
            )
        self.attrs[key] = value

    def del_attr(self, key: str) -> None:
        """Delete an attribute (raises KeyError if absent)."""
        del self.attrs[key]


# ---------------------------------------------------------------------------
# HCLModel
# ---------------------------------------------------------------------------


class HCLModel:
    """An ordered collection of resources, variables, and moved blocks.

    The model is the mutable in-memory representation of one Terraform step.
    Operators mutate a *copy* of the model for each step; the emitter
    converts the model to HCL text.
    """

    def __init__(self) -> None:
        self.resources: OrderedDict[str, Resource] = OrderedDict()
        self.moved: list[MovedBlock] = []
        self.variables: OrderedDict[str, Variable] = OrderedDict()

    def add(self, resource: Resource) -> None:
        """Add a resource.  Raises ValueError on duplicate address."""
        if resource.address in self.resources:
            raise ValueError(f"Duplicate resource address: {resource.address}")
        self.resources[resource.address] = resource

    def remove(self, address: str) -> Resource:
        """Remove and return a resource by address."""
        return self.resources.pop(address)

    def get(self, address: str) -> Resource:
        """Return the resource at ``address`` (raises KeyError if absent)."""
        return self.resources[address]

    def add_moved(self, from_addr: Ref, to_addr: Ref) -> None:
        """Append a ``moved`` block."""
        self.moved.append(MovedBlock(from_addr, to_addr))

    def add_variable(self, variable: Variable) -> None:
        """Add a variable block."""
        if variable.name in self.variables:
            raise ValueError(f"Duplicate variable: {variable.name}")
        self.variables[variable.name] = variable

    def copy(self) -> "HCLModel":
        """Return a deep copy of the model."""
        return copy.deepcopy(self)

    def resource_addresses(self) -> list[str]:
        return list(self.resources.keys())

