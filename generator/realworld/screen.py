"""S0 eligibility screen for real-world native modules (D4b-07).

Performs lexical screening of in-scope resources in S0 to reject modules that
violate protected invariants when that invariant is NOT the scenario's repair target.
Standard library only. No guessing.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))

import hcl_lex


def screen_native_s0(
    files: dict[str, str],
    target_invariant: str | None = None,
) -> tuple[bool, str]:
    """Screen native files lexically for S0 eligibility.

    Returns (is_eligible, reason_code_or_status).
    """
    for fname, text in sorted(files.items()):
        if not fname.endswith(".tf"):
            continue

        attrs = hcl_lex.attributes_from_hcl(text)

        # 1. Check aws_db_instance publicly_accessible
        for a in attrs:
            if a.top_level.startswith("aws_db_instance.") and a.name == "publicly_accessible":
                lines = text.splitlines()[a.line - 1 : a.end_line]
                if lines and "true" in lines[0].lower():
                    if target_invariant != "INV-SEC-003":
                        return False, "RW-S0: violates INV-SEC-003 in S0 (non-target)"

        # 2. Check security group ingress blocks and aws_security_group_rule resources
        blocks: dict[tuple[str, tuple[str, ...]], dict[str, str]] = {}
        for a in attrs:
            is_rule = a.top_level.startswith("aws_security_group_rule.")
            is_ingress = "ingress" in a.block_path
            if is_rule or is_ingress:
                key = (a.top_level, tuple(a.block_path))
                if key not in blocks:
                    blocks[key] = {}
                lines = text.splitlines()[a.line - 1 : a.end_line]
                blocks[key][a.name] = " ".join(lines)

        for (top_lvl, bpath), attr_map in blocks.items():
            rule_type = attr_map.get("type", "").lower()
            if top_lvl.startswith("aws_security_group_rule.") and '"egress"' in rule_type:
                continue

            cidr_text = attr_map.get("cidr_blocks", "") + " " + attr_map.get("ipv6_cidr_blocks", "")
            has_public = ("0.0.0.0/0" in cidr_text) or ("::/0" in cidr_text)
            if not has_public:
                continue

            fp_text = attr_map.get("from_port", "")
            tp_text = attr_map.get("to_port", "")

            covers_22 = False
            covers_5432 = False

            all_port_text = f" {fp_text} {tp_text} "
            if "22" in all_port_text:
                covers_22 = True
            if "5432" in all_port_text:
                covers_5432 = True

            if " 0 " in f" {fp_text} " and " 0 " in f" {tp_text} ":
                covers_22 = True
                covers_5432 = True

            if covers_22 and target_invariant != "INV-SEC-001":
                return False, "RW-S0: violates INV-SEC-001 in S0 (non-target)"
            if covers_5432 and target_invariant != "INV-SEC-002":
                return False, "RW-S0: violates INV-SEC-002 in S0 (non-target)"

    return True, "eligible"

