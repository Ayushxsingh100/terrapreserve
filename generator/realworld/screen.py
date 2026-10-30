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

        # 1. Check aws_db_instance publicly_accessible
        attrs = hcl_lex.attributes_from_hcl(text)
        for a in attrs:
            if a.top_level.startswith("aws_db_instance.") and a.name == "publicly_accessible":
                if a.value_kind == "literal" and "true" in text.splitlines()[a.line - 1 : a.end_line][0].lower():
                    if target_invariant != "INV-SEC-003":
                        return False, "RW-S0: violates INV-SEC-003 in S0 (non-target)"

            # 2. Check ingress rules
            if a.top_level.startswith("aws_security_group_rule.") or "ingress" in a.block_path:
                lines = text.splitlines()[a.line - 1 : a.end_line]
                combined = " ".join(lines)
                if "0.0.0.0/0" in combined or "::/0" in combined:
                    # Check port in surrounding block/lines
                    # If line has 22 or ssh
                    if "22" in combined:
                        if target_invariant != "INV-SEC-001":
                            return False, "RW-S0: violates INV-SEC-001 in S0 (non-target)"
                    elif "5432" in combined:
                        if target_invariant != "INV-SEC-002":
                            return False, "RW-S0: violates INV-SEC-002 in S0 (non-target)"

    return True, "eligible"
