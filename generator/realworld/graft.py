"""Graft builder and host neutraliser for TerraPreserve (D4b-03).

Provides:
- neutralise_host_file: strips provider and terraform blocks from host files.
- build_graft_files: synthesizes standalone EC2->RDS core with tp_ prefix.
- validate_no_clash: verifies zero identifier clashes with host modules.
Standard library only. No DAIL code.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import emitter
import hcl_lex
from model import Block, CountIndex, HCLModel, RawExpr, Ref, Resource, VarRef


class GraftClashError(Exception):
    """Raised when a graft identifier clashes with a host module identifier."""


GRAFT_DECLARED_IDENTIFIERS: set[str] = {
    "tp_vpc",
    "tp_igw",
    "tp_app_subnet",
    "tp_db_subnet_1",
    "tp_db_subnet_2",
    "tp_public_rt",
    "tp_rta_app",
    "tp_app_sg",
    "tp_db_sg",
    "tp_app_ingress_ssh",
    "tp_app_egress",
    "tp_db_ingress_postgres",
    "tp_app",
    "tp_db_subnet_group",
    "tp_db",
    "tp_db_password",
}


def build_graft_model(seed: int, variant: str = "clean") -> HCLModel:
    """Build the canonical HCLModel for the graft core with all tp_ prefixes."""
    rng = random.Random(seed)
    octet = rng.randint(20, 240)
    vpc_cidr = f"172.{octet % 16 + 16}.0.0/16"
    app_cidr = f"172.{octet % 16 + 16}.1.0/24"
    db1_cidr = f"172.{octet % 16 + 16}.10.0/24"
    db2_cidr = f"172.{octet % 16 + 16}.11.0/24"
    azs = ["us-east-1a", "us-east-1b"]

    m = HCLModel()

    # 1. VPC
    m.add(Resource(
        "aws_vpc", "tp_vpc",
        {
            "cidr_block": vpc_cidr,
            "enable_dns_hostnames": True,
            "enable_dns_support": True,
        }
    ))

    # 2. Internet Gateway
    m.add(Resource(
        "aws_internet_gateway", "tp_igw",
        {"vpc_id": Ref("aws_vpc.tp_vpc.id")}
    ))

    # 3. App Subnet
    m.add(Resource(
        "aws_subnet", "tp_app_subnet",
        {
            "vpc_id": Ref("aws_vpc.tp_vpc.id"),
            "cidr_block": app_cidr,
            "availability_zone": azs[0],
        }
    ))

    # 4. DB Subnets
    m.add(Resource(
        "aws_subnet", "tp_db_subnet_1",
        {
            "vpc_id": Ref("aws_vpc.tp_vpc.id"),
            "cidr_block": db1_cidr,
            "availability_zone": azs[0],
        }
    ))
    m.add(Resource(
        "aws_subnet", "tp_db_subnet_2",
        {
            "vpc_id": Ref("aws_vpc.tp_vpc.id"),
            "cidr_block": db2_cidr,
            "availability_zone": azs[1],
        }
    ))

    # 5. Route Table & Association
    m.add(Resource(
        "aws_route_table", "tp_public_rt",
        {"vpc_id": Ref("aws_vpc.tp_vpc.id")},
        blocks=[
            Block("route", {
                "cidr_block": "0.0.0.0/0",
                "gateway_id": Ref("aws_internet_gateway.tp_igw.id"),
            })
        ]
    ))
    m.add(Resource(
        "aws_route_table_association", "tp_rta_app",
        {
            "subnet_id": Ref("aws_subnet.tp_app_subnet.id"),
            "route_table_id": Ref("aws_route_table.tp_public_rt.id"),
        }
    ))

    # 6. Security Groups
    m.add(Resource(
        "aws_security_group", "tp_app_sg",
        {
            "name": "tp-app-sg",
            "description": "TerraPreserve app security group",
            "vpc_id": Ref("aws_vpc.tp_vpc.id"),
        }
    ))
    m.add(Resource(
        "aws_security_group", "tp_db_sg",
        {
            "name": "tp-db-sg",
            "description": "TerraPreserve database security group",
            "vpc_id": Ref("aws_vpc.tp_vpc.id"),
        }
    ))

    # 7. Security Group Rules
    ssh_cidr = ["0.0.0.0/0"] if variant == "sec_001_violated" else ["10.0.0.0/8"]
    m.add(Resource(
        "aws_security_group_rule", "tp_app_ingress_ssh",
        {
            "type": "ingress",
            "from_port": 22,
            "to_port": 22,
            "protocol": "tcp",
            "cidr_blocks": ssh_cidr,
            "security_group_id": Ref("aws_security_group.tp_app_sg.id"),
        }
    ))
    m.add(Resource(
        "aws_security_group_rule", "tp_app_egress",
        {
            "type": "egress",
            "from_port": 0,
            "to_port": 0,
            "protocol": "-1",
            "cidr_blocks": ["0.0.0.0/0"],
            "security_group_id": Ref("aws_security_group.tp_app_sg.id"),
        }
    ))

    # DB Ingress
    if variant == "sec_002_violated":
        m.add(Resource(
            "aws_security_group_rule", "tp_db_ingress_postgres",
            {
                "type": "ingress",
                "from_port": 5432,
                "to_port": 5432,
                "protocol": "tcp",
                "cidr_blocks": ["0.0.0.0/0"],
                "security_group_id": Ref("aws_security_group.tp_db_sg.id"),
            }
        ))
    else:
        m.add(Resource(
            "aws_security_group_rule", "tp_db_ingress_postgres",
            {
                "type": "ingress",
                "from_port": 5432,
                "to_port": 5432,
                "protocol": "tcp",
                "source_security_group_id": Ref("aws_security_group.tp_app_sg.id"),
                "security_group_id": Ref("aws_security_group.tp_db_sg.id"),
            }
        ))

    # 8. EC2 Instance
    m.add(Resource(
        "aws_instance", "tp_app",
        {
            "ami": "ami-0c55b159cbfafe1f0",
            "instance_type": "t3.micro",
            "subnet_id": Ref("aws_subnet.tp_app_subnet.id"),
            "vpc_security_group_ids": [Ref("aws_security_group.tp_app_sg.id")],
        }
    ))

    # 9. DB Subnet Group
    m.add(Resource(
        "aws_db_subnet_group", "tp_db_subnet_group",
        {
            "name": "tp-db-subnet-group",
            "subnet_ids": [
                Ref("aws_subnet.tp_db_subnet_1.id"),
                Ref("aws_subnet.tp_db_subnet_2.id"),
            ],
        }
    ))

    # 10. RDS DB Instance
    public_db = True if variant == "sec_003_violated" else False
    m.add(Resource(
        "aws_db_instance", "tp_db",
        {
            "allocated_storage": 20,
            "db_subnet_group_name": Ref("aws_db_subnet_group.tp_db_subnet_group.name"),
            "engine": "postgres",
            "identifier": "tp-db-instance",
            "instance_class": "db.t3.micro",
            "password": VarRef("tp_db_password"),
            "publicly_accessible": public_db,
            "skip_final_snapshot": True,
            "username": "tp_admin",
            "vpc_security_group_ids": [Ref("aws_security_group.tp_db_sg.id")],
        }
    ))

    return m


def build_graft_files(seed: int, variant: str = "clean") -> dict[str, str]:
    """Emit terrapreserve_graft.tf and terrapreserve_graft_variables.tf."""
    model = build_graft_model(seed, variant)
    main_tf = emitter.emit(model)
    vars_tf = """variable "tp_db_password" {
  type      = string
  sensitive = true
}
"""
    return {
        "terrapreserve_graft.tf": main_tf,
        "terrapreserve_graft_variables.tf": vars_tf,
    }


def validate_no_clash(host_files: dict[str, str], seed: int = 12345) -> None:
    """Verify that host_files declares zero identifiers clashing with graft."""
    clashing: list[str] = []

    for fname, content in host_files.items():
        if not fname.endswith(".tf"):
            continue
        headers = hcl_lex.headers_from_hcl(content)
        for _rtype, rname in headers.managed | headers.data:
            if rname in GRAFT_DECLARED_IDENTIFIERS:
                clashing.append(f"resource/data '{rname}' in {fname}")

        tokens = hcl_lex.tokenize(content)
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if tok.kind == "IDENT" and tok.text in ("variable", "locals", "output", "module") and i + 1 < n:
                nxt = tokens[i + 1]
                name = nxt.text
                if name in GRAFT_DECLARED_IDENTIFIERS:
                    clashing.append(f"{tok.text} '{name}' in {fname}")
            i += 1

    if clashing:
        raise GraftClashError(f"Host module has identifiers clashing with graft: {', '.join(clashing)}")


def neutralise_host_file(filename: str, content: str) -> tuple[str, dict]:
    """Remove top-level terraform and provider blocks from a host file."""
    removed: list[str] = []
    headers = hcl_lex.constructs_from_hcl(content)
    if headers.has_terraform_block:
        removed.append("terraform")
    if headers.has_provider_block:
        removed.append("provider")

    transformed = hcl_lex.remove_top_level_blocks(content, ("terraform", "provider"))
    log = {
        "file": filename,
        "removed_blocks": removed,
        "bytes_before": len(content),
        "bytes_after": len(transformed),
    }
    return transformed, log
