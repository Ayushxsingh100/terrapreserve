"""Tier assembly and comprehensive count aggregation (D0, D4b-01, D4b-08, D4b-09, A11).

Aggregates counts across both tiers:
- Controlled tier: 208 scenarios (144 dev, 64 test)
- Real-world tier: 208 scenarios (144 dev, 64 test)
- Total: 416 scenarios (288 dev, 128 test)
- Benchmark targets: 320 scenarios (224 dev, 96 test)
- Reserves: 96 scenarios (64 dev, 32 test)

Outputs:
- scenarios/ASSEMBLY.json
- scenarios/ASSEMBLY.md
Standard library only.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "generator"))

from realworld import plan as rw_plan  # noqa: E402
from generate import build_scenario_plan as ctrl_build_plan  # noqa: E402

FAMILIES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
CLASSES = ["safe", "unsafe"]


def compute_assembly() -> dict[str, Any]:
    """Compute exact scenario counts and verification metrics across both tiers."""
    controlled_items = ctrl_build_plan()
    real_world_items = rw_plan.build_real_world_plan()

    assert len(controlled_items) == 208, f"Expected 208 controlled scenarios, got {len(controlled_items)}"
    assert len(real_world_items) == 208, f"Expected 208 real-world scenarios, got {len(real_world_items)}"

    all_items = [
        dict(item, tier="controlled", **{"class": item.get("cls", item.get("class"))})
        for item in controlled_items
    ] + [
        dict(item, tier="real_world", **{"class": item.get("class", item.get("cls"))})
        for item in real_world_items
    ]

    total_scenarios = len(all_items)

    targets = [i for i in all_items if not i["reserve"]]
    reserves = [i for i in all_items if i["reserve"]]

    dev_items = [i for i in all_items if i["split"] == "dev"]
    test_items = [i for i in all_items if i["split"] == "test"]

    # Controlled vs Real-world
    ctrl_items = [i for i in all_items if i["tier"] == "controlled"]
    rw_items = [i for i in all_items if i["tier"] == "real_world"]

    # Family breakdowns
    family_stats: dict[str, dict[str, int]] = {}
    for fam in FAMILIES:
        f_all = [i for i in all_items if i["family"] == fam]
        f_tgt = [i for i in f_all if not i["reserve"]]
        f_res = [i for i in f_all if i["reserve"]]
        f_dev = [i for i in f_all if i["split"] == "dev"]
        f_test = [i for i in f_all if i["split"] == "test"]
        f_safe = [i for i in f_all if i["class"] == "safe"]
        f_unsafe = [i for i in f_all if i["class"] == "unsafe"]
        family_stats[fam] = {
            "total": len(f_all),
            "targets": len(f_tgt),
            "reserves": len(f_res),
            "dev": len(f_dev),
            "test": len(f_test),
            "safe": len(f_safe),
            "unsafe": len(f_unsafe),
        }

    # Cell breakdowns
    cell_stats: dict[str, dict[str, Any]] = {}
    for fam in FAMILIES:
        for cls in CLASSES:
            cell_key = f"{fam}_{cls}"
            c_all = [i for i in all_items if i["family"] == fam and i["class"] == cls]
            c_tgt = [i for i in c_all if not i["reserve"]]
            c_res = [i for i in c_all if i["reserve"]]

            cell_stats[cell_key] = {
                "family": fam,
                "class": cls,
                "total": len(c_all),
                "targets": {
                    "total": len(c_tgt),
                    "dev": sum(1 for i in c_tgt if i["split"] == "dev"),
                    "test": sum(1 for i in c_tgt if i["split"] == "test"),
                    "controlled": sum(1 for i in c_tgt if i["tier"] == "controlled"),
                    "real_world": sum(1 for i in c_tgt if i["tier"] == "real_world"),
                },
                "reserves": {
                    "total": len(c_res),
                    "dev": sum(1 for i in c_res if i["split"] == "dev"),
                    "test": sum(1 for i in c_res if i["split"] == "test"),
                    "controlled": sum(1 for i in c_res if i["tier"] == "controlled"),
                    "real_world": sum(1 for i in c_res if i["tier"] == "real_world"),
                },
                "dev_total": sum(1 for i in c_all if i["split"] == "dev"),
                "test_total": sum(1 for i in c_all if i["split"] == "test"),
            }

    # Real-world module composition
    rw_hosts = sum(1 for i in rw_items if i["kind"] == "host")
    rw_orig_natives = sum(1 for i in rw_items if i["kind"] == "native" and not i["derived"])
    rw_derived_natives = sum(1 for i in rw_items if i["kind"] == "native" and i["derived"])
    rw_unique_modules = len({i["module_id"] for i in rw_items})

    # Lineage disjointness check
    dev_lineages = {i.get("lineage_id") or i.get("template_id") for i in dev_items}
    test_lineages = {i.get("lineage_id") or i.get("template_id") for i in test_items}
    lineage_overlap = dev_lineages.intersection(test_lineages)

    return {
        "dataset_version": "1.0",
        "total_scenarios": total_scenarios,
        "targets": {
            "total": len(targets),
            "dev": sum(1 for i in targets if i["split"] == "dev"),
            "test": sum(1 for i in targets if i["split"] == "test"),
            "controlled": sum(1 for i in targets if i["tier"] == "controlled"),
            "real_world": sum(1 for i in targets if i["tier"] == "real_world"),
        },
        "reserves": {
            "total": len(reserves),
            "dev": sum(1 for i in reserves if i["split"] == "dev"),
            "test": sum(1 for i in reserves if i["split"] == "test"),
            "controlled": sum(1 for i in reserves if i["tier"] == "controlled"),
            "real_world": sum(1 for i in reserves if i["tier"] == "real_world"),
        },
        "splits": {
            "dev_total": len(dev_items),
            "test_total": len(test_items),
        },
        "controlled": {
            "total": len(ctrl_items),
            "targets": sum(1 for i in ctrl_items if not i["reserve"]),
            "reserves": sum(1 for i in ctrl_items if i["reserve"]),
            "dev": sum(1 for i in ctrl_items if i["split"] == "dev"),
            "test": sum(1 for i in ctrl_items if i["split"] == "test"),
        },
        "real_world": {
            "total": len(rw_items),
            "targets": sum(1 for i in rw_items if not i["reserve"]),
            "reserves": sum(1 for i in rw_items if i["reserve"]),
            "dev": sum(1 for i in rw_items if i["split"] == "dev"),
            "test": sum(1 for i in rw_items if i["split"] == "test"),
            "composition": {
                "hosts": rw_hosts,
                "original_natives": rw_orig_natives,
                "derived_natives": rw_derived_natives,
                "unique_modules": rw_unique_modules,
            },
        },
        "families": family_stats,
        "cells": cell_stats,
        "lineage_audit": {
            "dev_lineages_count": len(dev_lineages),
            "test_lineages_count": len(test_lineages),
            "leakage_count": len(lineage_overlap),
            "leaked_lineages": sorted(list(lineage_overlap)),
        },
    }


def render_markdown(data: dict[str, Any]) -> str:
    """Render comprehensive assembly markdown document."""
    lines = [
        "# TerraPreserve Scenario Assembly Report (v1.0)",
        "",
        "Assembly of the complete benchmark dataset across both tiers: controlled synthetic templates (D4a) and real-world TerraDS modules (D4b).",
        "",
        "## Overall Summary",
        "",
        "| Metric | Total | Dev Split | Test Split (Withheld) | Controlled Tier | Real-World Tier |",
        "|---|---|---|---|---|---|",
        f"| **Benchmark Targets** | {data['targets']['total']} | {data['targets']['dev']} | {data['targets']['test']} | {data['targets']['controlled']} | {data['targets']['real_world']} |",
        f"| **Reserve Scenarios** | {data['reserves']['total']} | {data['reserves']['dev']} | {data['reserves']['test']} | {data['reserves']['controlled']} | {data['reserves']['real_world']} |",
        f"| **Grand Total** | {data['total_scenarios']} | {data['splits']['dev_total']} | {data['splits']['test_total']} | {data['controlled']['total']} | {data['real_world']['total']} |",
        "",
        "## Real-World Tier Composition",
        "",
        f"- **Hosts (grafted):** {data['real_world']['composition']['hosts']}",
        f"- **Original Natives (ungrafted):** {data['real_world']['composition']['original_natives']}",
        f"- **Derived Natives (redacted & ungrafted):** {data['real_world']['composition']['derived_natives']}",
        f"- **Unique Modules Used:** {data['real_world']['composition']['unique_modules']} / 208 (no reuse)",
        "",
        "## Lineage & Split Audit",
        "",
        f"- **Dev lineages/templates:** {data['lineage_audit']['dev_lineages_count']}",
        f"- **Test lineages/templates:** {data['lineage_audit']['test_lineages_count']}",
        f"- **Overlap / Leakage across splits:** {data['lineage_audit']['leakage_count']}",
        "",
        "## Breakdown by Family",
        "",
        "| Family | Description | Targets | Reserves | Total | Dev | Test | Safe | Unsafe |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    family_descriptions = {
        "F1": "Resource sizing and configuration updates",
        "F2": "Network routing and CIDR modifications",
        "F3": "Security group ingress/egress rules",
        "F4": "Storage volume and database engine settings",
        "F5": "Count and meta-argument restructuring",
        "F6": "Resource additions and associations",
        "F7": "Resource removals and disassociations",
        "F8": "Multi-step chained refactoring workflows",
    }

    for fam in FAMILIES:
        f = data["families"][fam]
        desc = family_descriptions.get(fam, "")
        lines.append(
            f"| {fam} | {desc} | {f['targets']} | {f['reserves']} | {f['total']} | {f['dev']} | {f['test']} | {f['safe']} | {f['unsafe']} |"
        )

    lines.extend([
        "",
        "## Breakdown by Cell (16 Cells)",
        "",
        "| Cell | Family | Class | Targets (Dev / Test) | Reserves (Dev / Test) | Cell Total (Dev / Test) |",
        "|---|---|---|---|---|---|",
    ])

    for cell_key, c in data["cells"].items():
        fam = c["family"]
        cls = c["class"]
        tgt_str = f"{c['targets']['total']} ({c['targets']['dev']} / {c['targets']['test']})"
        res_str = f"{c['reserves']['total']} ({c['reserves']['dev']} / {c['reserves']['test']})"
        tot_str = f"{c['total']} ({c['dev_total']} / {c['test_total']})"
        lines.append(f"| {cell_key} | {fam} | {cls} | {tgt_str} | {res_str} | {tot_str} |")

    lines.append("")
    return "\n".join(lines)


def run_assembly() -> tuple[Path, Path]:
    """Execute assembly, generate ASSEMBLY.json and ASSEMBLY.md."""
    data = compute_assembly()
    scenarios_dir = REPO_ROOT / "scenarios"

    json_path = scenarios_dir / "ASSEMBLY.json"
    json_path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    md_text = render_markdown(data)
    md_path = scenarios_dir / "ASSEMBLY.md"
    md_path.write_text(md_text, encoding="utf-8", newline="\n")

    return json_path, md_path


if __name__ == "__main__":
    jpath, mpath = run_assembly()
    print(f"Assembly completed successfully:")
    print(f"  JSON: {jpath}")
    print(f"  MD:   {mpath}")
