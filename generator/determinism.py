"""Determinism comparison for generated scenarios (D4-12, D4b-12).

``check_deterministic`` generates one plan item several times and compares the results
with ``compare_runs``. Both the clean determinism check and the mutation check that
breaks the generator (tools/run_d4b_mutation_checks.py, check 8) use this same
comparison, so the mutation check exercises the real code and not a stand-in.

Standard library only. No DAIL import (D0 gate 1).
"""

from __future__ import annotations

from typing import Any, Callable


class DeterminismError(AssertionError):
    """Two generator runs on the same plan item produced different output."""


def compare_runs(first: tuple[Any, Any, Any], second: tuple[Any, Any, Any], label: str) -> None:
    """Compare two ``(scenario_data, steps_files, mutation_records)`` results exactly."""
    sc_a, files_a, rec_a = first
    sc_b, files_b, rec_b = second
    if sc_a != sc_b:
        differing = sorted(k for k in set(sc_a) | set(sc_b) if sc_a.get(k) != sc_b.get(k))
        raise DeterminismError(f"{label}: scenario metadata differ between runs (keys: {differing})")
    if files_a != files_b:
        raise DeterminismError(f"{label}: emitted step files differ between runs")
    if rec_a != rec_b:
        raise DeterminismError(f"{label}: mutation records differ between runs")


def check_deterministic(generate_fn: Callable[[Any], tuple[Any, Any, Any]], item: Any,
                        label: str, runs: int = 2) -> None:
    """Generate ``item`` ``runs`` times and raise ``DeterminismError`` if any two results differ."""
    results = [generate_fn(item) for _ in range(runs)]
    for other in results[1:]:
        compare_runs(results[0], other, label)
