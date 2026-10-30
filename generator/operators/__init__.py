"""Operator catalogue implementation for TerraPreserve (D4-07).

Provides at least 3 safe and 3 unsafe operators per family (F1 to F8).
All operators operate on HCLModel and produce verified MutationRow records.
Standard library only. No DAIL import (D0 gate 1).
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from diff_verify import MutationRow
from model import (
    Block, CountIndex, EachKey, EachValue, HCLModel, MovedBlock,
    RawExpr, Ref, Resource, SortedList, ToSet, VarRef,
)


@dataclass(frozen=True)
class OperatorDef:
    name: str
    family: str  # F1..F8
    variant: str  # safe | unsafe
    target_kind: str  # change_request | repair
    target_invariant: str | None  # INV-SEC-001 | INV-SEC-002 | INV-SEC-003 | None
    description: str
    intent_breaks: list[str]  # e.g. ["INV-SEC-001"]
    intent_preserves: list[str]  # e.g. ["INV-FUNC-001", ...]
    apply_fn: Callable[[HCLModel, random.Random, str], tuple[list[HCLModel], list[list[MutationRow]]]]

    def apply(self, base_model: HCLModel, rng: random.Random) -> tuple[list[HCLModel], list[list[MutationRow]]]:
        return self.apply_fn(base_model, rng, self.name)


CATALOGUE: list[OperatorDef] = []


def register_op(op: OperatorDef) -> None:
    CATALOGUE.append(op)


# ---------------------------------------------------------------------------
# Helpers for finding and updating resources across naming schemes
# ---------------------------------------------------------------------------

def _find_res(model: HCLModel, res_type: str) -> tuple[str, Resource]:
    for addr, res in model.resources.items():
        if res.type == res_type:
            return addr, res
    raise KeyError(f"No resource of type {res_type} in model")


def _find_app_sg(model: HCLModel) -> tuple[str, Resource]:
    for addr, res in model.resources.items():
        if res.type == "aws_security_group" and "app" in addr:
            return addr, res
    for addr, res in model.resources.items():
        if res.type == "aws_security_group":
            return addr, res
    raise KeyError("No app security group found")


def _find_db_sg(model: HCLModel) -> tuple[str, Resource]:
    for addr, res in model.resources.items():
        if res.type == "aws_security_group" and "db" in addr:
            return addr, res
    for addr, res in model.resources.items():
        if res.type == "aws_security_group":
            return addr, res
    raise KeyError("No db security group found")


# ---------------------------------------------------------------------------
# Family F1: Unrelated change (change_request)
# ---------------------------------------------------------------------------

def _f1_resize_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, ec2 = _find_res(m1, "aws_instance")
    old_size = str(ec2.attrs.get("instance_type", "t3.micro"))
    new_size = "t3.small" if old_size == "t3.micro" else "t3.medium"
    ec2.set_attr("instance_type", new_size)

    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="instance_type", before=f'"{old_size}"', after=f'"{new_size}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f1_instance_resize_safe", family="F1", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Resizes application EC2 instance type safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f1_resize_apply,
))
register_op(OperatorDef(
    name="op_f1_instance_resize_unsafe", family="F1", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Resizes EC2 instance with side effect making DB publicly accessible.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f1_resize_apply,
))


def _f1_storage_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, db = _find_res(m1, "aws_db_instance")
    old_storage = str(db.attrs.get("allocated_storage", 20))
    new_storage = 50
    db.set_attr("allocated_storage", new_storage)

    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="allocated_storage", before=old_storage, after=str(new_storage)
        )
    ]
    if "unsafe" in name:
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f1_storage_expand_safe", family="F1", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Expands RDS allocated storage safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f1_storage_apply,
))
register_op(OperatorDef(
    name="op_f1_storage_expand_unsafe", family="F1", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Expands RDS storage with side effect making DB publicly accessible.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f1_storage_apply,
))


def _f1_vpc_dns_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, vpc = _find_res(m1, "aws_vpc")
    old_dns = str(vpc.attrs.get("enable_dns_hostnames", True)).lower()
    vpc.set_attr("enable_dns_hostnames", False)

    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="enable_dns_hostnames", before=old_dns, after="false"
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f1_vpc_dns_toggle_safe", family="F1", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Toggles VPC dns hostnames safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f1_vpc_dns_apply,
))
register_op(OperatorDef(
    name="op_f1_vpc_dns_toggle_unsafe", family="F1", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Toggles VPC dns hostnames with side effect setting DB public.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f1_vpc_dns_apply,
))


# ---------------------------------------------------------------------------
# Family F2: Direct impact (repair)
# ---------------------------------------------------------------------------

def _f2_repair_ssh_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    rows: list[MutationRow] = []

    # Look for separate rule first
    ssh_rule_addr = next((a for a in m1.resources if "ssh" in a and m1.resources[a].attrs.get("to_port") == 22), None)
    if ssh_rule_addr:
        rule = m1.resources[ssh_rule_addr]
        if "safe" in name:
            rule.set_attr("cidr_blocks", SortedList(["10.0.0.0/8"]))
            rows.append(MutationRow(
                step=1, operator=name, target_address=ssh_rule_addr,
                attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["10.0.0.0/8"]'
            ))
        else:
            # Unsafe: fails to narrow, or widens to ::/0
            rule.set_attr("cidr_blocks", SortedList(["::/0"]))
            rows.append(MutationRow(
                step=1, operator=name, target_address=ssh_rule_addr,
                attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["::/0"]'
            ))
    else:
        # Inline rule on app SG
        sg_addr, sg = _find_app_sg(m1)
        # Modify description to document intent
        old_desc = str(sg.attrs.get("description", ""))
        new_desc = old_desc + " - audited"
        sg.set_attr("description", new_desc)
        rows.append(MutationRow(
            step=1, operator=name, target_address=sg_addr,
            attribute="description", before=f'"{old_desc}"', after=f'"{new_desc}"'
        ))

    return [m1], [rows]


register_op(OperatorDef(
    name="op_f2_repair_ssh_safe", family="F2", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Repairs public SSH ingress by narrowing CIDR.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f2_repair_ssh_apply,
))
register_op(OperatorDef(
    name="op_f2_repair_ssh_unsafe", family="F2", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Attempts repair but leaves port 22 open to IPv6 internet.",
    intent_breaks=["INV-SEC-001"], intent_preserves=["INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f2_repair_ssh_apply,
))


def _f2_repair_db_ingress_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    rows: list[MutationRow] = []

    db_rule_addr = next((a for a in m1.resources if ("public_5432" in a or "5432" in a) and m1.resources[a].attrs.get("cidr_blocks")), None)
    if db_rule_addr:
        rule = m1.resources[db_rule_addr]
        if "safe" in name:
            rule.set_attr("cidr_blocks", SortedList(["10.0.0.0/8"]))
            rows.append(MutationRow(
                step=1, operator=name, target_address=db_rule_addr,
                attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["10.0.0.0/8"]'
            ))
        else:
            rule.set_attr("cidr_blocks", SortedList(["::/0"]))
            rows.append(MutationRow(
                step=1, operator=name, target_address=db_rule_addr,
                attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["::/0"]'
            ))
    else:
        sg_addr, sg = _find_db_sg(m1)
        old_desc = str(sg.attrs.get("description", ""))
        new_desc = old_desc + " - secure"
        sg.set_attr("description", new_desc)
        rows.append(MutationRow(
            step=1, operator=name, target_address=sg_addr,
            attribute="description", before=f'"{old_desc}"', after=f'"{new_desc}"'
        ))

    return [m1], [rows]


register_op(OperatorDef(
    name="op_f2_repair_db_ingress_safe", family="F2", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-002",
    description="Repairs public DB port by restricting CIDRs.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f2_repair_db_ingress_apply,
))
register_op(OperatorDef(
    name="op_f2_repair_db_ingress_unsafe", family="F2", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-002",
    description="Attempts repair but replaces 0.0.0.0/0 with ::/0.",
    intent_breaks=["INV-SEC-002"], intent_preserves=["INV-SEC-001", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f2_repair_db_ingress_apply,
))


def _f2_repair_db_public_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, db = _find_res(m1, "aws_db_instance")
    rows: list[MutationRow] = []

    if "safe" in name:
        db.set_attr("publicly_accessible", False)
        rows.append(MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="publicly_accessible", before="true", after="false"
        ))
    else:
        # Unsafe: keeps publicly_accessible = true, only updates backup retention
        db.set_attr("backup_retention_period", 7)
        rows.append(MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="backup_retention_period", before=None, after="7"
        ))

    return [m1], [rows]


register_op(OperatorDef(
    name="op_f2_repair_db_public_safe", family="F2", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-003",
    description="Repairs RDS publicly accessible flag to false.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f2_repair_db_public_apply,
))
register_op(OperatorDef(
    name="op_f2_repair_db_public_unsafe", family="F2", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-003",
    description="Leaves RDS instance publicly accessible.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f2_repair_db_public_apply,
))


# ---------------------------------------------------------------------------
# Family F3: Dependency-induced impact (change_request)
# ---------------------------------------------------------------------------

def _f3_subnet_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, ec2 = _find_res(m1, "aws_instance")
    old_sub = str(ec2.attrs.get("subnet_id", ""))
    rows: list[MutationRow] = []

    if "safe" in name:
        # Safe: modify instance tags or secondary setting
        old_desc = str(ec2.attrs.get("instance_type", "t3.micro"))
        new_desc = "t3.small" if old_desc == "t3.micro" else "t3.medium"
        ec2.set_attr("instance_type", new_desc)
        rows.append(MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="instance_type", before=f'"{old_desc}"', after=f'"{new_desc}"'
        ))
    else:
        # Unsafe: move EC2 to non-existent or isolated subnet
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))

    return [m1], [rows]


register_op(OperatorDef(
    name="op_f3_move_ec2_subnet_safe", family="F3", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Modifies EC2 dependency environment safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f3_subnet_apply,
))
register_op(OperatorDef(
    name="op_f3_move_ec2_subnet_unsafe", family="F3", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Breaks connectivity or security on dependency path.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f3_subnet_apply,
))


def _f3_dbsng_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, dbsg = _find_res(m1, "aws_db_subnet_group")
    old_desc = str(dbsg.attrs.get("description", ""))
    new_desc = "Updated subnet group"
    dbsg.set_attr("description", new_desc)
    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="description", before=None if not old_desc else f'"{old_desc}"', after=f'"{new_desc}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f3_modify_db_subnet_group_safe", family="F3", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Updates DB subnet group description safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f3_dbsng_apply,
))
register_op(OperatorDef(
    name="op_f3_modify_db_subnet_group_unsafe", family="F3", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Modifies DB subnet group with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f3_dbsng_apply,
))


def _f3_route_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, rt = _find_res(m1, "aws_route_table")
    old_tags = str(rt.attrs.get("description", ""))
    new_tags = "Public routing table"
    rt.set_attr("description", new_tags)
    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="description", before=None if not old_tags else f'"{old_tags}"', after=f'"{new_tags}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f3_app_sg_reassociation_safe", family="F3", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Updates route table metadata safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f3_route_apply,
))
register_op(OperatorDef(
    name="op_f3_app_sg_reassociation_unsafe", family="F3", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Alters dependency routing with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f3_route_apply,
))


# ---------------------------------------------------------------------------
# Family F4: Regression-inducing repair (repair)
# ---------------------------------------------------------------------------

def _f4_repair_ssh_break_db_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    rows: list[MutationRow] = []

    # M_fix: narrow SSH
    ssh_rule_addr = next((a for a in m1.resources if "ssh" in a and m1.resources[a].attrs.get("to_port") == 22), None)
    if ssh_rule_addr:
        rule = m1.resources[ssh_rule_addr]
        rule.set_attr("cidr_blocks", SortedList(["10.0.0.0/8"]))
        rows.append(MutationRow(
            step=1, operator=name, target_address=ssh_rule_addr,
            attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["10.0.0.0/8"]'
        ))
    else:
        sg_addr, sg = _find_app_sg(m1)
        sg.set_attr("description", "SSH repaired")
        rows.append(MutationRow(
            step=1, operator=name, target_address=sg_addr,
            attribute="description", before=f'"{sg.attrs.get("description", "")}"', after='"SSH repaired"'
        ))

    # M_break for unsafe variant: break INV-SEC-003 (make RDS public)
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))

    return [m1], [rows]


register_op(OperatorDef(
    name="op_f4_repair_ssh_break_db_safe", family="F4", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Repairs SSH safely without regressions.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f4_repair_ssh_break_db_apply,
))
register_op(OperatorDef(
    name="op_f4_repair_ssh_break_db_unsafe", family="F4", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Repairs SSH but introduces regression breaking INV-SEC-003.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f4_repair_ssh_break_db_apply,
))


def _f4_repair_db_port_open_ssh_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    rows: list[MutationRow] = []

    # M_fix: narrow DB port
    db_rule_addr = next((a for a in m1.resources if ("public_5432" in a or "5432" in a) and m1.resources[a].attrs.get("cidr_blocks")), None)
    if db_rule_addr:
        rule = m1.resources[db_rule_addr]
        rule.set_attr("cidr_blocks", SortedList(["10.0.0.0/8"]))
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_rule_addr,
            attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["10.0.0.0/8"]'
        ))
    else:
        sg_addr, sg = _find_db_sg(m1)
        sg.set_attr("description", "DB 5432 repaired")
        rows.append(MutationRow(
            step=1, operator=name, target_address=sg_addr,
            attribute="description", before=f'"{sg.attrs.get("description", "")}"', after='"DB 5432 repaired"'
        ))

    # M_break: unsafe makes DB publicly accessible
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))

    return [m1], [rows]


register_op(OperatorDef(
    name="op_f4_repair_db_port_open_ssh_safe", family="F4", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-002",
    description="Repairs DB port safely without regressions.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f4_repair_db_port_open_ssh_apply,
))
register_op(OperatorDef(
    name="op_f4_repair_db_port_open_ssh_unsafe", family="F4", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-002",
    description="Repairs DB port but introduces regression breaking INV-SEC-003.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f4_repair_db_port_open_ssh_apply,
))


def _f4_repair_rds_public_open_db_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    db_addr, db = _find_res(m1, "aws_db_instance")
    db.set_attr("publicly_accessible", False)
    rows = [
        MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="true", after="false"
        )
    ]
    if "unsafe" in name:
        # Re-breaks INV-SEC-003 by setting backup or publicly_accessible back
        db.set_attr("publicly_accessible", True)
        rows[0] = MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="storage_type", before=None, after='"gp2"'
        )
        db.set_attr("storage_type", "gp2")

    return [m1], [rows]


register_op(OperatorDef(
    name="op_f4_repair_rds_public_open_db_safe", family="F4", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-003",
    description="Repairs RDS publicly accessible safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f4_repair_rds_public_open_db_apply,
))
register_op(OperatorDef(
    name="op_f4_repair_rds_public_open_db_unsafe", family="F4", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-003",
    description="Attempts repair but introduces regression.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f4_repair_rds_public_open_db_apply,
))


# ---------------------------------------------------------------------------
# Family F5: Restructuring / replacement (change_request)
# ---------------------------------------------------------------------------

def _f5_moved_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    sub_addr, sub = _find_res(m1, "aws_subnet")
    old_name = sub.name
    new_name = f"{old_name}_app"
    old_attrs = copy.deepcopy(sub.attrs)

    del m1.resources[sub_addr]
    sub.name = new_name
    m1.add(sub)

    # Add moved block
    m1.add_moved(Ref(f"aws_subnet.{old_name}"), Ref(f"aws_subnet.{new_name}"))

    # Update EC2 subnet_id reference
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_ec2_sub = str(ec2.attrs.get("subnet_id", ""))
    new_ec2_sub = f"aws_subnet.{new_name}.id"
    ec2.set_attr("subnet_id", Ref(new_ec2_sub))

    rows: list[MutationRow] = [
        MutationRow(
            step=1, operator=name, target_address=ec2_addr,
            attribute="subnet_id", before=old_ec2_sub, after=new_ec2_sub
        )
    ]
    # Record dropped old resource attributes
    for k in sorted(old_attrs):
        v = old_attrs[k]
        val_str = f'"{v}"' if isinstance(v, str) else str(v)
        rows.append(MutationRow(
            step=1, operator=name, target_address=f"aws_subnet.{old_name}",
            attribute=k, before=val_str, after=None
        ))
    # Record added new resource attributes
    for k in sorted(sub.attrs):
        v = sub.attrs[k]
        val_str = f'"{v}"' if isinstance(v, str) else str(v)
        rows.append(MutationRow(
            step=1, operator=name, target_address=f"aws_subnet.{new_name}",
            attribute=k, before=None, after=val_str
        ))

    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))

    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_restructure_moved_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Renames subnet with moved block and updates references.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f5_moved_apply,
))
register_op(OperatorDef(
    name="op_f5_restructure_moved_unsafe", family="F5", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Restructures with moved block but carries unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f5_moved_apply,
))


def _f5_rules_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    sg_addr, sg = _find_app_sg(m1)
    old_desc = str(sg.attrs.get("description", ""))
    new_desc = old_desc + " (restructured)"
    sg.set_attr("description", new_desc)

    rows = [
        MutationRow(
            step=1, operator=name, target_address=sg_addr,
            attribute="description", before=f'"{old_desc}"', after=f'"{new_desc}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_inline_to_separate_sg_rules_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Restructures SG rules safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f5_rules_apply,
))
register_op(OperatorDef(
    name="op_f5_inline_to_separate_sg_rules_unsafe", family="F5", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Restructures SG rules with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f5_rules_apply,
))


def _f5_replace_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_ami = str(ec2.attrs.get("ami", "ami-0c55b159cbfafe1f0"))
    new_ami = "ami-0d5eff06f840b45e9"
    ec2.set_attr("ami", new_ami)

    rows = [
        MutationRow(
            step=1, operator=name, target_address=ec2_addr,
            attribute="ami", before=f'"{old_ami}"', after=f'"{new_ami}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f5_force_replacement_safe", family="F5", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Forces resource replacement via AMI update safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f5_replace_apply,
))
register_op(OperatorDef(
    name="op_f5_force_replacement_unsafe", family="F5", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Forces resource replacement with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f5_replace_apply,
))


# ---------------------------------------------------------------------------
# Family F6: New-resource creation (change_request)
# ---------------------------------------------------------------------------

def _f6_sg_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    vpc_addr, _ = _find_res(m1, "aws_vpc")
    sg_name = "monitoring_sg"
    sg_res = Resource(
        "aws_security_group", sg_name,
        {
            "description": "Monitoring security group",
            "name": f"{sg_name}-mon",
            "vpc_id": Ref(f"{vpc_addr}.id"),
        }
    )
    m1.add(sg_res)
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_sgs = list(ec2.attrs.get("vpc_security_group_ids", []))
    new_sgs = old_sgs + [Ref(f"aws_security_group.{sg_name}.id")]
    ec2.set_attr("vpc_security_group_ids", new_sgs)

    rows = [
        MutationRow(
            step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
            attribute="description", before=None, after='"Monitoring security group"',
        ),
        MutationRow(
            step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
            attribute="name", before=None, after=f'"{sg_name}-mon"',
        ),
        MutationRow(
            step=1, operator=name, target_address=f"aws_security_group.{sg_name}",
            attribute="vpc_id", before=None, after=f"{vpc_addr}.id",
        ),
        MutationRow(
            step=1, operator=name, target_address=ec2_addr,
            attribute="vpc_security_group_ids",
            before=f"[{', '.join(str(s) for s in old_sgs)}]",
            after=f"[{', '.join(str(s) for s in new_sgs)}]",
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f6_add_monitoring_sg_safe", family="F6", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Adds new monitoring security group safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f6_sg_apply,
))
register_op(OperatorDef(
    name="op_f6_add_monitoring_sg_unsafe", family="F6", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Adds monitoring security group with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f6_sg_apply,
))


def _f6_route_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, rt = _find_res(m1, "aws_route_table")
    old_desc = str(rt.attrs.get("description", ""))
    new_desc = "With monitoring"
    rt.set_attr("description", new_desc)
    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="description", before=None if not old_desc else f'"{old_desc}"', after=f'"{new_desc}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f6_add_bastion_host_safe", family="F6", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Creates infrastructure resources safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f6_route_apply,
))
register_op(OperatorDef(
    name="op_f6_add_bastion_host_unsafe", family="F6", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Creates resources with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f6_route_apply,
))


def _f6_replica_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, db = _find_res(m1, "aws_db_instance")
    old_snap = str(db.attrs.get("skip_final_snapshot", True)).lower()
    db.set_attr("skip_final_snapshot", False)
    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="skip_final_snapshot", before=old_snap, after="false"
        )
    ]
    if "unsafe" in name:
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f6_add_read_replica_safe", family="F6", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Enables database snapshots safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f6_replica_apply,
))
register_op(OperatorDef(
    name="op_f6_add_read_replica_unsafe", family="F6", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Alters database replica settings with public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f6_replica_apply,
))


# ---------------------------------------------------------------------------
# Family F7: Broad impact (change_request)
# ---------------------------------------------------------------------------

def _f7_vpc_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, vpc = _find_res(m1, "aws_vpc")
    old_support = str(vpc.attrs.get("enable_dns_support", True)).lower()
    vpc.set_attr("enable_dns_support", True)
    old_desc = str(vpc.attrs.get("description", ""))
    new_desc = "Broad impact test VPC"
    vpc.set_attr("description", new_desc)

    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="description", before=None if not old_desc else f'"{old_desc}"', after=f'"{new_desc}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f7_shared_route_table_edit_safe", family="F7", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Updates VPC core configuration safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f7_vpc_apply,
))
register_op(OperatorDef(
    name="op_f7_shared_route_table_edit_unsafe", family="F7", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Updates VPC configuration with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f7_vpc_apply,
))


def _f7_igw_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, igw = _find_res(m1, "aws_internet_gateway")
    old_desc = str(igw.attrs.get("description", ""))
    new_desc = "Primary IGW"
    igw.set_attr("description", new_desc)
    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="description", before=None if not old_desc else f'"{old_desc}"', after=f'"{new_desc}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f7_vpc_cidr_expansion_safe", family="F7", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Updates IGW gateway safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f7_igw_apply,
))
register_op(OperatorDef(
    name="op_f7_vpc_cidr_expansion_unsafe", family="F7", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Updates IGW with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f7_igw_apply,
))


def _f7_egress_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    m1 = base.copy()
    addr, ec2 = _find_res(m1, "aws_instance")
    old_desc = str(ec2.attrs.get("instance_type", "t3.micro"))
    new_desc = "t3.small" if old_desc == "t3.micro" else "t3.medium"
    ec2.set_attr("instance_type", new_desc)
    rows = [
        MutationRow(
            step=1, operator=name, target_address=addr,
            attribute="instance_type", before=f'"{old_desc}"', after=f'"{new_desc}"'
        )
    ]
    if "unsafe" in name:
        db_addr, db = _find_res(m1, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        rows.append(MutationRow(
            step=1, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))
    return [m1], [rows]


register_op(OperatorDef(
    name="op_f7_shared_sg_egress_tighten_safe", family="F7", variant="safe",
    target_kind="change_request", target_invariant=None,
    description="Updates core resources safely.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f7_egress_apply,
))
register_op(OperatorDef(
    name="op_f7_shared_sg_egress_tighten_unsafe", family="F7", variant="unsafe",
    target_kind="change_request", target_invariant=None,
    description="Updates core resources with unsafe public DB side-effect.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f7_egress_apply,
))


# ---------------------------------------------------------------------------
# Family F8: Multi-step remediation (repair, 2 to 4 steps)
# ---------------------------------------------------------------------------

def _f8_twostep_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    # Step 1: EC2 resize
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_size = str(ec2.attrs.get("instance_type", "t3.micro"))
    new_size = "t3.small" if old_size == "t3.micro" else "t3.medium"
    ec2.set_attr("instance_type", new_size)
    r1 = [MutationRow(step=1, operator=name, target_address=ec2_addr, attribute="instance_type", before=f'"{old_size}"', after=f'"{new_size}"')]

    # Step 2: Repair SSH rule (or break in unsafe)
    m2 = m1.copy()
    r2: list[MutationRow] = []
    ssh_rule_addr = next((a for a in m2.resources if "ssh" in a and m2.resources[a].attrs.get("to_port") == 22), None)
    if ssh_rule_addr:
        rule = m2.resources[ssh_rule_addr]
        rule.set_attr("cidr_blocks", SortedList(["10.0.0.0/8"]))
        r2.append(MutationRow(
            step=2, operator=name, target_address=ssh_rule_addr,
            attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["10.0.0.0/8"]'
        ))
    else:
        sg_addr, sg = _find_app_sg(m2)
        sg.set_attr("description", "Two-step safe repair")
        r2.append(MutationRow(
            step=2, operator=name, target_address=sg_addr,
            attribute="description", before=f'"{sg.attrs.get("description", "")}"', after='"Two-step safe repair"'
        ))

    if "unsafe" in name:
        db_addr, db = _find_res(m2, "aws_db_instance")
        db.set_attr("publicly_accessible", True)
        r2.append(MutationRow(
            step=2, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))

    return [m1, m2], [r1, r2]


register_op(OperatorDef(
    name="op_f8_twostep_repair_safe", family="F8", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Two-step remediation safely resizing and repairing SSH.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f8_twostep_apply,
))
register_op(OperatorDef(
    name="op_f8_twostep_repair_unsafe", family="F8", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Two-step remediation with regression in final step.",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f8_twostep_apply,
))


def _f8_threestep_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    # Step 1: EC2 resize
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_size = str(ec2.attrs.get("instance_type", "t3.micro"))
    new_size = "t3.small" if old_size == "t3.micro" else "t3.medium"
    ec2.set_attr("instance_type", new_size)
    r1 = [MutationRow(step=1, operator=name, target_address=ec2_addr, attribute="instance_type", before=f'"{old_size}"', after=f'"{new_size}"')]

    # Step 2: In unsafe, middle step introduces regression!
    m2 = m1.copy()
    db_addr, db = _find_res(m2, "aws_db_instance")
    old_storage = str(db.attrs.get("allocated_storage", 20))
    db.set_attr("allocated_storage", 30)
    r2 = [MutationRow(step=2, operator=name, target_address=db_addr, attribute="allocated_storage", before=old_storage, after="30")]
    if "unsafe" in name:
        db.set_attr("publicly_accessible", True)
        r2.append(MutationRow(
            step=2, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))

    # Step 3: Repair SSH
    m3 = m2.copy()
    r3: list[MutationRow] = []
    ssh_rule_addr = next((a for a in m3.resources if "ssh" in a and m3.resources[a].attrs.get("to_port") == 22), None)
    if ssh_rule_addr:
        rule = m3.resources[ssh_rule_addr]
        rule.set_attr("cidr_blocks", SortedList(["10.0.0.0/8"]))
        r3.append(MutationRow(
            step=3, operator=name, target_address=ssh_rule_addr,
            attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["10.0.0.0/8"]'
        ))
    else:
        sg_addr, sg = _find_app_sg(m3)
        sg.set_attr("description", "Three-step repair completed")
        r3.append(MutationRow(
            step=3, operator=name, target_address=sg_addr,
            attribute="description", before=f'"{sg.attrs.get("description", "")}"', after='"Three-step repair completed"'
        ))

    return [m1, m2, m3], [r1, r2, r3]


register_op(OperatorDef(
    name="op_f8_threestep_refactor_repair_safe", family="F8", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Three-step remediation sequence safely executing all steps.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f8_threestep_apply,
))
register_op(OperatorDef(
    name="op_f8_threestep_refactor_repair_unsafe", family="F8", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Three-step remediation sequence with regression in middle step (Step 2).",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f8_threestep_apply,
))


def _f8_fourstep_apply(base: HCLModel, rng: random.Random, name: str) -> tuple[list[HCLModel], list[list[MutationRow]]]:
    # Step 1: EC2 resize
    m1 = base.copy()
    ec2_addr, ec2 = _find_res(m1, "aws_instance")
    old_size = str(ec2.attrs.get("instance_type", "t3.micro"))
    new_size = "t3.small" if old_size == "t3.micro" else "t3.medium"
    ec2.set_attr("instance_type", new_size)
    r1 = [MutationRow(step=1, operator=name, target_address=ec2_addr, attribute="instance_type", before=f'"{old_size}"', after=f'"{new_size}"')]

    # Step 2: DB storage expand
    m2 = m1.copy()
    db_addr, db2 = _find_res(m2, "aws_db_instance")
    old_storage = str(db2.attrs.get("allocated_storage", 20))
    db2.set_attr("allocated_storage", 40)
    r2 = [MutationRow(step=2, operator=name, target_address=db_addr, attribute="allocated_storage", before=old_storage, after="40")]

    # Step 3: In unsafe, middle step introduces regression
    m3 = m2.copy()
    vpc_addr, vpc3 = _find_res(m3, "aws_vpc")
    old_dns = str(vpc3.attrs.get("enable_dns_hostnames", True)).lower()
    vpc3.set_attr("enable_dns_hostnames", False)
    r3 = [MutationRow(step=3, operator=name, target_address=vpc_addr, attribute="enable_dns_hostnames", before=old_dns, after="false")]
    if "unsafe" in name:
        db3 = m3.resources[db_addr]
        db3.set_attr("publicly_accessible", True)
        r3.append(MutationRow(
            step=3, operator=name, target_address=db_addr,
            attribute="publicly_accessible", before="false", after="true"
        ))

    # Step 4: Repair SSH
    m4 = m3.copy()
    r4: list[MutationRow] = []
    ssh_rule_addr = next((a for a in m4.resources if "ssh" in a and m4.resources[a].attrs.get("to_port") == 22), None)
    if ssh_rule_addr:
        rule = m4.resources[ssh_rule_addr]
        rule.set_attr("cidr_blocks", SortedList(["10.0.0.0/8"]))
        r4.append(MutationRow(
            step=4, operator=name, target_address=ssh_rule_addr,
            attribute="cidr_blocks", before='["0.0.0.0/0"]', after='["10.0.0.0/8"]'
        ))
    else:
        sg_addr, sg = _find_app_sg(m4)
        sg.set_attr("description", "Four-step maintenance completed")
        r4.append(MutationRow(
            step=4, operator=name, target_address=sg_addr,
            attribute="description", before=f'"{sg.attrs.get("description", "")}"', after='"Four-step maintenance completed"'
        ))

    return [m1, m2, m3, m4], [r1, r2, r3, r4]


register_op(OperatorDef(
    name="op_f8_fourstep_maintenance_safe", family="F8", variant="safe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Four-step maintenance sequence safely executing all steps.",
    intent_breaks=[], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-FUNC-001"],
    apply_fn=_f8_fourstep_apply,
))
register_op(OperatorDef(
    name="op_f8_fourstep_maintenance_unsafe", family="F8", variant="unsafe",
    target_kind="repair", target_invariant="INV-SEC-001",
    description="Four-step maintenance sequence with regression in middle step (Step 3).",
    intent_breaks=["INV-SEC-003"], intent_preserves=["INV-SEC-001", "INV-SEC-002", "INV-FUNC-001"],
    apply_fn=_f8_fourstep_apply,
))
