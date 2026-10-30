"""Scenario writer, content hasher, diff computer, and split withholding (D4-01, D4-04, D4-09, D4-10).

Standard library only. No DAIL import (D0 gate 1).
"""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(doc: Any) -> str:
    """Format doc as canonical sorted JSON with 2 spaces and LF only."""
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_step_content_hash(files: dict[str, str]) -> str:
    """SHA-256 over the sorted (path, file_sha256) pairs in files (D4-09)."""
    lines = [f"{path}:{sha256_text(text)}" for path, text in sorted(files.items())]
    return sha256_text("\n".join(lines))


def compute_step_diff(prev_files: dict[str, str], curr_files: dict[str, str]) -> str:
    """Unified diff (LF) of all files between previous and current step."""
    diff_lines: list[str] = []
    all_paths = sorted(set(prev_files.keys()) | set(curr_files.keys()))

    for path in all_paths:
        prev_text = prev_files.get(path, "")
        curr_text = curr_files.get(path, "")
        if prev_text == curr_text:
            continue
        file_diff = difflib.unified_diff(
            prev_text.splitlines(keepends=True),
            curr_text.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
        diff_lines.extend(file_diff)

    return "".join(diff_lines)


def write_dev_scenario(
    dev_root: Path,
    scenario_data: dict[str, Any],
    steps_files: list[dict[str, str]],
) -> Path:
    """Write dev scenario to scenarios/dev/<scenario_id>/.

    Strict guard: REFUSES test-split scenarios (D4-01).
    """
    if scenario_data.get("split") != "dev":
        raise ValueError(
            f"Refusing to write test-split scenario {scenario_data.get('scenario_id')!r} to dev directory!"
        )

    scenario_id = scenario_data["scenario_id"]
    scenario_dir = dev_root / scenario_id
    scenario_dir.mkdir(parents=True, exist_ok=True)

    # Write step directories
    for step_idx, files in enumerate(steps_files):
        step_dir = scenario_dir / f"step_{step_idx}"
        step_dir.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (step_dir / name).write_text(text, encoding="utf-8", newline="\n")

    # Write scenario.json
    manifest_path = scenario_dir / "scenario.json"
    manifest_path.write_text(canonical_json(scenario_data), encoding="utf-8", newline="\n")

    return scenario_dir


def write_test_scenario(
    private_root: Path,
    scenario_data: dict[str, Any],
    steps_files: list[dict[str, str]],
) -> dict[str, Any]:
    """Write test scenario to private directory outside repo.

    Strict guard: REFUSES dev-split scenarios.
    Returns test_manifest entry containing ids and hashes ONLY (D4-01, A6).
    """
    if scenario_data.get("split") != "test":
        raise ValueError(
            f"Refusing to write dev-split scenario {scenario_data.get('scenario_id')!r} to private directory!"
        )

    scenario_id = scenario_data["scenario_id"]
    scenario_dir = private_root / scenario_id
    scenario_dir.mkdir(parents=True, exist_ok=True)

    # Write step directories
    step_manifests = []
    for step_idx, files in enumerate(steps_files):
        step_dir = scenario_dir / f"step_{step_idx}"
        step_dir.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (step_dir / name).write_text(text, encoding="utf-8", newline="\n")
        step_manifests.append({
            "step": step_idx,
            "content_hash": compute_step_content_hash(files),
        })

    # Write scenario.json
    scenario_json_text = canonical_json(scenario_data)
    manifest_path = scenario_dir / "scenario.json"
    manifest_path.write_text(scenario_json_text, encoding="utf-8", newline="\n")

    return {
        "scenario_id": scenario_id,
        "scenario_json_sha256": sha256_text(scenario_json_text),
        "steps": step_manifests,
    }

