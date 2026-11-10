#!/usr/bin/env python3
"""D5b Step 2: build the oracle's plan-JSON fixtures (registry v1.0 section 8 vectors, section 6.5 worked cases).

Each fixture is a minimal configuration written here from the vector's text in registry v1.0 (DAIL
``docs/specs/INVARIANT_REGISTRY_v1.md`` at tag ``registry-v1.0``): one edit of the canonical topology below (VPC
10.0.0.0/16, application subnet 10.0.1.0/24, database subnet 10.0.2.0/24, route ``0.0.0.0/0 -> igw``, groups
``app`` and ``db``, rules ``app_egress_all`` (``-1`` to ``0.0.0.0/0``) and ``app_to_db_5432`` (TCP 5432 into
``db`` from ``app`` by reference), ``S = aws_instance.app``, ``D = aws_db_instance.database``). For every fixture
the tool writes ``tests/fixtures/oracle/<id>/main.tf`` and ``versions.tf``, runs it once offline with
``oracle.plan.Runner`` (D5-04: validate, plan, ``terraform show -json``), and writes ``validate.json`` and, when
the configuration validates, ``plan.json`` (the plan JSON with its ``timestamp`` removed, so a rerun gives the same
bytes). The expected results are not here: the tests copy them from the registry tables. Tests read the committed
files and need no Terraform. Standard library only.

Usage: ``python tools/make_oracle_fixtures.py [ID ...]`` (all fixtures when no id is given).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from oracle import plan as oplan  # noqa: E402

OUT = REPO_ROOT / "tests" / "fixtures" / "oracle"
WORK = Path.home() / ".terrapreserve-cache" / "d5b-fixtures"

VERSIONS_TF = """terraform {
  required_version = "~> 1.15.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.53.0"
    }
  }
}
"""

# The canonical topology, one block per key (order kept). Vectors replace, drop or add blocks.
CANON: dict[str, str] = {
    "vpc": '''resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}''',
    "igw": '''resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}''',
    "subnet_app": '''resource "aws_subnet" "app" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
}''',
    "subnet_db": '''resource "aws_subnet" "db" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1a"
}''',
    "rt": '''resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}''',
    "rta": '''resource "aws_route_table_association" "app" {
  subnet_id      = aws_subnet.app.id
  route_table_id = aws_route_table.public.id
}''',
    "sg_app": '''resource "aws_security_group" "app" {
  name   = "app"
  vpc_id = aws_vpc.main.id
}''',
    "sg_db": '''resource "aws_security_group" "db" {
  name   = "db"
  vpc_id = aws_vpc.main.id
}''',
    "app_egress": '''resource "aws_security_group_rule" "app_egress_all" {
  type              = "egress"
  security_group_id = aws_security_group.app.id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
}''',
    "app_to_db": '''resource "aws_security_group_rule" "app_to_db_5432" {
  type                     = "ingress"
  security_group_id        = aws_security_group.db.id
  protocol                 = "tcp"
  from_port                = 5432
  to_port                  = 5432
  source_security_group_id = aws_security_group.app.id
}''',
    "ec2": '''resource "aws_instance" "app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
}''',
    "rds": '''resource "aws_db_instance" "database" {
  identifier                  = "database"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "postgres"
  manage_master_user_password = true
  skip_final_snapshot         = true
  vpc_security_group_ids      = [aws_security_group.db.id]
}''',
}


def rule(name: str, sg: str, *, type_: str = "ingress", protocol: str = "tcp", ports: tuple[int, int] = (22, 22),
         cidr: str | None = None, extra: str = "") -> str:
    lines = [f'resource "aws_security_group_rule" "{name}" {{', f'  type              = "{type_}"',
             f"  security_group_id = {sg}", f'  protocol          = "{protocol}"',
             f"  from_port         = {ports[0]}", f"  to_port           = {ports[1]}"]
    if cidr is not None:
        lines.append(f"  cidr_blocks       = {cidr}")
    if extra:
        lines.append(extra)
    return "\n".join(lines) + "\n}"


def edit(*, drop: tuple[str, ...] = (), replace: dict[str, str] | None = None, add: dict[str, str] | None = None) -> str:
    blocks = dict(CANON)
    for k in drop:
        del blocks[k]
    for k, v in (replace or {}).items():
        assert k in blocks, k
        blocks[k] = v
    for k, v in (add or {}).items():
        assert k not in blocks, k
        blocks[k] = v
    return "\n\n".join(blocks.values()) + "\n"


APP = "aws_security_group.app.id"
SSH_GROUP_INLINE_PUBLIC = '''resource "aws_security_group" "ssh" {
  name   = "ssh"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["0.0.0.0/0"]
  }
}'''
WEB_PARENT = '''resource "aws_security_group" "web" {
  name   = "web"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["10.0.0.0/16"]
  }
}'''
WEB_ABSENT = '''resource "aws_security_group" "web" {
  name   = "web"
  vpc_id = aws_vpc.main.id
}'''
WEB_EMPTY = '''resource "aws_security_group" "web" {
  name    = "web"
  vpc_id  = aws_vpc.main.id
  ingress = []
}'''
DB_INLINE_FROM_APP = '''resource "aws_security_group" "db" {
  name   = "db"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [aws_security_group.app.id]
  }
}'''
UNRESOLVED_SG = "aws_vpc.main.default_security_group_id"  # provider-computed, not an identity reference: unresolved
# An unresolved IPv4 CIDR (a value unknown at plan time, not an identity reference; D5-13, S9 and R3).
UNRESOLVED_CIDR = '["${aws_instance.app.private_ip}/32"]'
EC2_IN = lambda subnet, extra="": f'''resource "aws_instance" "app" {{
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  subnet_id              = {subnet}
  vpc_security_group_ids = [aws_security_group.app.id]{extra}
}}'''  # noqa: E731
RDS = lambda extra: CANON["rds"][:-1] + extra + "\n}"  # noqa: E731

FIXTURES: dict[str, str] = {
    # ---- Section 8, INV-SEC-001 / INV-SEC-002
    "S1": edit(add={"ssh": SSH_GROUP_INLINE_PUBLIC}),
    "S2": edit(add={"r": rule("all_public", APP, protocol="-1", ports=(0, 0), cidr='["0.0.0.0/0"]')}),
    "S3": edit(add={"r": rule("v6_public", APP, ports=(0, 65535), extra='  ipv6_cidr_blocks  = ["::/0"]')}),
    "S4": edit(add={"r": rule("split_22", APP, cidr='["0.0.0.0/1", "128.0.0.0/1"]')}),
    "S5": edit(add={"a": rule("half_a_22", APP, cidr='["0.0.0.0/1"]'),
                    "b": rule("half_b_20_30", APP, ports=(20, 30), cidr='["128.0.0.0/1"]')}),
    "S6": edit(add={"a": rule("group_a_22", APP, cidr='["0.0.0.0/1"]'),
                    "b": rule("group_b_22", "aws_security_group.db.id", cidr='["128.0.0.0/1"]')}),
    "S7": edit(add={"r": rule("private_22", APP, cidr='["10.0.0.0/16"]')}),
    "S8": edit(add={"r": rule("udp_22", APP, protocol="udp", cidr='["0.0.0.0/0"]')}),
    "S9": edit(add={"r": rule("unresolved_22", APP, cidr=UNRESOLVED_CIDR)}),
    "S10": edit(add={"r": rule("prefix_list_22", APP, extra='  prefix_list_ids   = ["pl-0123456789abcdef0"]')}),
    "S11": edit(replace={"sg_db": '''resource "aws_security_group" "db" {
  name   = "db"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["10.0.0.0/16"]
  }
}'''}),
    "S12": edit(add={"unused": '''resource "aws_security_group" "unused" {
  name   = "unused"
  vpc_id = aws_vpc.main.id
}''', "r": rule("unused_public_22", "aws_security_group.unused.id", cidr='["0.0.0.0/0"]')}),
    "S13": edit(add={"r": '''resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.app.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "10.0.0.0/16"
}'''}),
    "S14": edit(add={"r": rule("app_public_5432", APP, ports=(5432, 5432), cidr='["0.0.0.0/0"]')}),
    "S15": edit(add={"r": '''resource "aws_vpc_security_group_rules_exclusive" "app" {
  security_group_id = aws_security_group.app.id
  ingress_rule_ids  = []
  egress_rule_ids   = []
}'''}),
    "S16_parent": edit(add={"web": WEB_PARENT}),
    "S16": edit(add={"web": WEB_ABSENT}),
    "S17": edit(add={"web": WEB_EMPTY}),
    "S18": edit(add={"empty": '''resource "aws_security_group" "empty" {
  name   = "empty"
  vpc_id = aws_vpc.main.id
}'''}),
    "S19": edit(add={"web": WEB_EMPTY, "r": rule("web_https", "aws_security_group.web.id", ports=(443, 443),
                                                 cidr='["10.0.0.0/16"]')}),
    "S20": edit(add={"web": WEB_ABSENT, "ssh": SSH_GROUP_INLINE_PUBLIC}),
    # ---- Section 8, INV-SEC-003
    "R1": edit(),
    "R2": edit(replace={"rds": RDS("\n  publicly_accessible         = true")}),
    "R3": edit(replace={"rds": RDS("\n  publicly_accessible         = length(aws_instance.app.private_ip) > 0")}),
    "R4": edit(drop=("rds",)),
    # ---- Section 8, INV-FUNC-001 (F1 is the canonical topology, also the 6.5 PASS case)
    "F1": edit(),
    "F2": edit(drop=("app_to_db",)),
    "F3": edit(replace={"app_to_db": rule("app_to_db_5432", "aws_security_group.db.id", ports=(5432, 5432),
                                          cidr='["10.0.1.0/24"]')}),
    "F4": edit(replace={"app_to_db": rule("app_to_db_5432", "aws_security_group.db.id", ports=(5432, 5432),
                                          cidr='["10.0.1.0/24"]'), "ec2": EC2_IN("aws_subnet.other.id")},
               add={"other": '''resource "aws_subnet" "other" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = "us-east-1a"
}'''}),
    "F5": edit(drop=("app_egress",)),
    "F6": edit(replace={"app_egress": rule("app_egress_db_subnet", APP, type_="egress", ports=(5432, 5432),
                                           cidr='["10.0.2.0/24"]')}),
    "F7": edit(add={"rt_mid": '''resource "aws_route_table" "middlebox" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block           = "10.0.2.0/24"
    network_interface_id = "eni-0123456789abcdef0"
  }
}'''}),
    "F8": edit(replace={"rt": '''resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
}'''}),
    "F9": edit(add={"nacl": '''resource "aws_network_acl" "main" {
  vpc_id = aws_vpc.main.id
}'''}),
    "F10": edit(drop=("rds",)),
    "F11": edit(replace={"rds": RDS("\n  port                        = 3306")}),
    "F12": edit(replace={"rds": CANON["rds"].replace("  vpc_security_group_ids      = [aws_security_group.db.id]\n", "")}),
    "F13a": edit(replace={"app_to_db": rule("app_to_db_5432", "aws_security_group.db.id", ports=(5432, 5432),
                                            cidr='["10.0.1.0/25"]')}),
    "F13b": edit(replace={"app_to_db": rule("app_to_db_5432", "aws_security_group.db.id", ports=(5432, 5432),
                                            cidr='["10.0.1.0/25"]'),
                          "ec2": EC2_IN("aws_subnet.app.id", '\n  private_ip             = "10.0.1.10"')}),
    "F14": edit(replace={"ec2": EC2_IN("aws_subnet.second.id")}, add={"vpc2": '''resource "aws_vpc" "second" {
  cidr_block = "10.1.0.0/16"
}''', "subnet2": '''resource "aws_subnet" "second" {
  vpc_id            = aws_vpc.second.id
  cidr_block        = "10.1.1.0/24"
  availability_zone = "us-east-1a"
}'''}),
    "F15": edit(replace={"rds": RDS("\n  db_subnet_group_name        = aws_db_subnet_group.main.name")},
                add={"subnet_db_b": '''resource "aws_subnet" "db_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.12.0/24"
  availability_zone = "us-east-1b"
}''', "dbsng": '''resource "aws_db_subnet_group" "main" {
  name       = "main"
  subnet_ids = [aws_subnet.db.id, aws_subnet.db_b.id]
}'''}),
    # Provider 6.53.0 rejects network_interface together with subnet_id and vpc_security_group_ids ("Conflicting
    # configuration arguments"), so S carries only the network_interface block here.
    "F16": edit(replace={"ec2": '''resource "aws_instance" "app" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  network_interface {
    network_interface_id = "eni-0123456789abcdef0"
    device_index         = 0
  }
}'''}),
    "F17": edit(replace={"rt": '''resource "aws_route_table" "public" {
  vpc_id           = aws_vpc.main.id
  propagating_vgws = ["vgw-0123456789abcdef0"]

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}'''}),
    "F18": edit(add={"assoc": '''resource "aws_vpc_security_group_vpc_association" "db" {
  security_group_id = aws_security_group.db.id
  vpc_id            = "vpc-0123456789abcdef0"
}'''}),
    "F19_parent": edit(drop=("app_to_db",), replace={"sg_db": DB_INLINE_FROM_APP}),
    "F19": edit(drop=("app_to_db",)),
    "F20": edit(add={"dvpc": '''resource "aws_default_vpc" "default" {
}'''}),
    # ---- Section 6.5 worked case 2 (the canonical regression): parent has public SSH; the candidate fixes SSH and
    # removes app_to_db_5432. Worked case 1 is F1; worked case 3 (route edit inside the VPC) is F1 -> F8.
    "W2_parent": edit(add={"r": rule("app_ssh_public", APP, cidr='["0.0.0.0/0"]')}),
    "W2": edit(drop=("app_to_db",)),
    # ---- Further rules the work package names (registry sections cited in the tests)
    "X_pseudo_literal": edit(add={"r": rule("literal_target_22", '"sg-0123456789abcdef0"', cidr='["0.0.0.0/0"]')}),
    "X_pseudo_unresolved": edit(add={"r": rule("unresolved_target_22", UNRESOLVED_SG, cidr='["0.0.0.0/0"]')}),
    "X_possible6": edit(add={"r": rule("unresolved_v6_22", APP,
                                       extra='  ipv6_cidr_blocks  = [aws_vpc.main.ipv6_cidr_block]')}),
    "X_func_row7_source": edit(replace={"app_to_db": rule(
        "app_to_db_5432", "aws_security_group.db.id", ports=(5432, 5432),
        extra=f"  source_security_group_id = {UNRESOLVED_SG}")}),
    "X_func_row7_pseudo": edit(replace={"app_to_db": rule(
        "app_to_db_5432", UNRESOLVED_SG, ports=(5432, 5432), extra=f"  source_security_group_id = {APP}")}),
    "X_invalid": edit(add={"r": rule("host_bits_22", APP, cidr='["10.0.1.1/24"]')}),
    "X_moved_rule": edit(replace={"app_to_db": '''resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  security_group_id        = aws_security_group.db.id
  protocol                 = "tcp"
  from_port                = 5432
  to_port                  = 5432
  source_security_group_id = aws_security_group.app.id
}

moved {
  from = aws_security_group_rule.app_to_db_5432
  to   = aws_security_group_rule.db_from_app
}'''}),
    "X_count_s": edit(replace={"ec2": '''resource "aws_instance" "app" {
  count                  = 1
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
}'''}),
    # ---- D5-22 symmetric references: two inline ingress blocks whose security_groups name two configured groups
    # (plan JSON merges the references; tp-v1-F3-0062 step 1 is the identical-block pattern).
    "X_sym_identical": edit(drop=("app_to_db",), replace={"sg_db": '''resource "aws_security_group" "db" {
  name   = "db"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [aws_security_group.app.id]
  }

  ingress {
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [aws_security_group.peer.id]
  }
}'''}, add={"sg_peer": '''resource "aws_security_group" "peer" {
  name   = "peer"
  vpc_id = aws_vpc.main.id
}'''}),
    "X_sym_differ": edit(drop=("app_to_db",), replace={"sg_db": '''resource "aws_security_group" "db" {
  name   = "db"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [aws_security_group.app.id]
  }

  ingress {
    protocol        = "tcp"
    from_port       = 5433
    to_port         = 5433
    cidr_blocks     = ["10.0.9.0/24"]
    security_groups = [aws_security_group.peer.id]
  }
}'''}, add={"sg_peer": '''resource "aws_security_group" "peer" {
  name   = "peer"
  vpc_id = aws_vpc.main.id
}'''}),
    # ---- D5-16 footprint pairs (parent F1)
    "P_instance_type": edit(replace={"ec2": CANON["ec2"].replace('"t3.micro"', '"t3.small"')}),
    "P_sg_tags": edit(replace={"sg_app": '''resource "aws_security_group" "app" {
  name   = "app"
  vpc_id = aws_vpc.main.id
  tags = {
    team = "tp"
  }
}'''}),
    "P_egress_rule_cidr": edit(replace={"app_egress": rule("app_egress_all", APP, type_="egress", protocol="-1",
                                                           ports=(0, 0), cidr='["10.0.0.0/16"]')}),
}


def write(fid: str, runner: oplan.Runner) -> str:
    d = OUT / fid
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "main.tf").write_text(FIXTURES[fid], encoding="utf-8", newline="\n")
    (d / "versions.tf").write_text(VERSIONS_TF, encoding="utf-8", newline="\n")
    res = runner.run(d, {})
    (d / "validate.json").write_text(json.dumps({"valid": res["validate_ok"], "first_error": res["validate_error"]},
                                                sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    if res["status"] == "planned":
        doc = dict(res["plan"])
        doc.pop("timestamp", None)
        (d / "plan.json").write_text(json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n",
                                     encoding="utf-8", newline="\n")
    elif res["status"] != "invalid":
        raise SystemExit(f"{fid}: {res['stage']} failed: {res['error_first_line']}")
    return res["status"]


def main(argv: list[str]) -> int:
    terraform = shutil.which("terraform")
    if terraform is None:
        raise SystemExit("terraform not found")
    ids = argv or sorted(FIXTURES)
    unknown = [i for i in ids if i not in FIXTURES]
    if unknown:
        raise SystemExit(f"unknown fixture ids: {unknown}")
    runner = oplan.Runner(WORK, terraform)
    for fid in ids:
        print(fid, write(fid, runner), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
