"""List the Terraform checks in the installed Checkov that could bear on INV-SEC-002 / INV-SEC-003.

Runs ``checkov --list --framework terraform`` (Checkov must be on PATH; offline) and keeps the AWS rows whose
entity is a security-group, network-ACL or RDS resource, or whose policy text mentions a port, ingress,
postgres, 0.0.0.0 or public access. Writes a Markdown table. Standard library only.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys

ENTITY = re.compile(r"^aws_(security_group|vpc_security_group|default_security_group|network_acl|db_|rds_|default_network_acl)")
POLICY = re.compile(r"5432|postgres|ingress|0\.0\.0\.0|\bport\b|publicly|public access|security group", re.I)


def main() -> int:
    out = subprocess.run(
        [shutil.which("checkov") or "checkov", "--list", "--framework", "terraform"], capture_output=True, text=True, check=True
    ).stdout
    rows = []
    for line in out.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7 or not re.match(r"CKV2?_AWS_\d+", cells[1]):
            continue
        check_id, kind, entity, policy, link = cells[1], cells[2], cells[3], cells[4], cells[6]
        if ENTITY.match(entity) or POLICY.search(policy):
            rows.append((check_id, kind, entity, policy, link.rsplit("/", 1)[-1]))
    total_aws = sum(1 for line in out.splitlines() if re.search(r"\|\s*CKV2?_AWS_\d+\s*\|", line))
    print(f"Checkov terraform checks listed: {len(out.splitlines()) - 2} rows; AWS rows: {total_aws}; kept: {len(rows)}\n")
    print("| Id | Type | Entity | Policy | Source file |")
    print("|---|---|---|---|---|")
    for r in sorted(rows):
        print("| " + " | ".join(r) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
