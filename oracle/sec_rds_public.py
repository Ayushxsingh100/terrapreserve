"""INV-SEC-003: RDS instances are not publicly accessible (registry v1.0 section 5).

For every configured ``aws_db_instance`` instance d, ``publicly_accessible(d)`` is false; an absent attribute is
false (5.2; the plan JSON shows ``false`` for an unset attribute, D1 V05). With zero instances the predicate holds
vacuously and the count, 0, is recorded. Results (5.3, in order): FAIL if some instance has resolved
``publicly_accessible = true``; UNKNOWN if some instance has an unresolved value; otherwise PASS. Other RDS types
(``aws_rds_cluster_instance``) are out of scope. Standard library only.
"""

from __future__ import annotations

from typing import Any

from oracle.common import FAIL, PASS, UNKNOWN
from oracle.model import ABSENT, Config, Unresolved, value


def evaluate(config: Config) -> dict[str, Any]:
    rows = []
    for d in config.of_type("aws_db_instance"):
        v = value(d, "publicly_accessible")
        if isinstance(v, Unresolved):
            rows.append({"address": d.address, "value": None, "unresolved": v.reason})
        else:
            rows.append({"address": d.address, "value": bool(v) if v not in (None, ABSENT) else False})
    if any(r["value"] is True for r in rows):
        result = FAIL
    elif any("unresolved" in r for r in rows):
        result = UNKNOWN
    else:
        result = PASS
    return {"invariant_id": "INV-SEC-003", "invariant_version": 1, "verifier_id": "tp.oracle.rds_public_flag",
            "verifier_version": "1", "parameters": {}, "evidence_level": "L2", "result": result,
            "observations": {"db_instance_count": len(rows), "db_instances": rows},
            "assumptions": ["registry 5.2: an absent publicly_accessible is false"], "ambiguities": []}
