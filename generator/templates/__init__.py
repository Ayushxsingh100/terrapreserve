"""Ten controlled templates for TerraPreserve (D4-05).

All templates implement the Appendix B topology using the 10 pinned AWS resource types.
Each template differs across the axes specified in D4-05:
- security-group style (all_separate, all_inline, mixed_app_inline_db_separate, mixed_app_separate_db_inline)
- number of db subnets (2 or 3)
- a second app SG layered on the first
- route-table layout (shared or separate)
- use of count for db subnets
- instance and DB classes
- naming scheme
- CIDR plan

Standard library and generator model only. No DAIL import (D0 gate 1).
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any

from model import (
    Block, CountIndex, HCLModel, RawExpr, Ref, Resource, SortedList,
    ToSet, VarRef,
)

TEMPLATE_VERSION: str = "tpl-v1.0"

TERRAGOAT_VOCABULARY = {
    "aws_instance": (
        "ami", "instance_type", "subnet_id", "vpc_security_group_ids", "tags"
    ),
    "aws_db_instance": (
        "allocated_storage", "engine", "instance_class", "identifier",
        "username", "password", "db_subnet_group_name", "vpc_security_group_ids",
        "publicly_accessible", "skip_final_snapshot", "tags"
    ),
    "aws_db_subnet_group": (
        "name", "subnet_ids", "tags"
    ),
    "aws_security_group": (
        "name", "description", "vpc_id", "tags"
    ),
    "aws_security_group_rule": (
        "type", "from_port", "to_port", "protocol", "cidr_blocks",
        "source_security_group_id", "security_group_id"
    ),
}


@dataclass(frozen=True)
class TemplateDef:
    id: str
    version: str
    sg_style: str  # all_separate | all_inline | mixed_app_inline_db_separate | mixed_app_separate_db_inline
    db_subnet_count: int  # 2 | 3
    has_second_app_sg: bool
    route_table_layout: str  # shared | separate
    use_count_for_db_subnets: bool
    instance_class: str
    db_class: str
    naming_scheme: str  # standard | kebab | tier | component | env
    terragoat_vocabulary: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: copy.deepcopy(TERRAGOAT_VOCABULARY)
    )

    def instantiate(
        self,
        rng: random.Random,
        variant: str = "clean",
    ) -> tuple[HCLModel, dict[str, Any]]:
        """Instantiate template into an HCLModel and parameter metadata.

        variant can be:
        - clean: satisfies all 4 invariants
        - sec_001_violated: public SSH (0.0.0.0/0 on port 22) on app SG
        - sec_002_violated: public DB port (0.0.0.0/0 on port 5432) on db SG
        - sec_003_violated: publicly_accessible = true on RDS instance
        """
        # Deterministic parameter generation
        cidr_octet = rng.randint(10, 200)
        vpc_cidr = f"10.{cidr_octet}.0.0/16"
        app_subnet_cidr = f"10.{cidr_octet}.1.0/24"
        db_subnet_cidrs = [f"10.{cidr_octet}.{10 + i}.0/24" for i in range(self.db_subnet_count)]
        azs = ["us-east-1a", "us-east-1b", "us-east-1c"][:max(self.db_subnet_count, 2)]

        param_meta = {
            "template_id": self.id,
            "template_version": self.version,
            "variant": variant,
            "cidr_plan": {
                "vpc": vpc_cidr,
                "app": app_subnet_cidr,
                "db": db_subnet_cidrs,
            },
            "azs": azs,
            "instance_class": self.instance_class,
            "db_class": self.db_class,
            "naming_scheme": self.naming_scheme,
            "sg_style": self.sg_style,
        }

        # Names per naming scheme
        names = _resolve_names(self.naming_scheme)

        model = HCLModel()

        # 1. VPC
        vpc_name = names["vpc"]
        model.add(Resource(
            "aws_vpc", vpc_name,
            {
                "cidr_block": vpc_cidr,
                "enable_dns_hostnames": True,
                "enable_dns_support": True,
            }
        ))

        # 2. Internet Gateway
        igw_name = names["igw"]
        model.add(Resource(
            "aws_internet_gateway", igw_name,
            {
                "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
            }
        ))

        # 3. App Subnet
        app_sub_name = names["app_subnet"]
        model.add(Resource(
            "aws_subnet", app_sub_name,
            {
                "availability_zone": azs[0],
                "cidr_block": app_subnet_cidr,
                "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
            }
        ))

        # 4. DB Subnets
        db_sub_name = names["db_subnet"]
        db_sub_refs: list[Any] = []
        if self.use_count_for_db_subnets:
            az_list_str = "[" + ", ".join(f'"{az}"' for az in azs[:self.db_subnet_count]) + "]"
            cidr_list_str = "[" + ", ".join(f'"{c}"' for c in db_subnet_cidrs) + "]"
            model.add(Resource(
                "aws_subnet", db_sub_name,
                {
                    "availability_zone": RawExpr(f"{az_list_str}[count.index]"),
                    "cidr_block": RawExpr(f"{cidr_list_str}[count.index]"),
                    "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
                },
                count=self.db_subnet_count,
            ))
            # References for subnet group
            for i in range(self.db_subnet_count):
                db_sub_refs.append(Ref(f"aws_subnet.{db_sub_name}[{i}].id"))
        else:
            for i in range(self.db_subnet_count):
                sub_res_name = f"{db_sub_name}_{i+1}"
                model.add(Resource(
                    "aws_subnet", sub_res_name,
                    {
                        "availability_zone": azs[i % len(azs)],
                        "cidr_block": db_subnet_cidrs[i],
                        "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
                    }
                ))
                db_sub_refs.append(Ref(f"aws_subnet.{sub_res_name}.id"))

        # 5. Route Table(s)
        rt_public_name = names["rt_public"]
        model.add(Resource(
            "aws_route_table", rt_public_name,
            {
                "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
            },
            blocks=[
                Block("route", {
                    "cidr_block": "0.0.0.0/0",
                    "gateway_id": Ref(f"aws_internet_gateway.{igw_name}.id"),
                })
            ]
        ))
        # Association for app subnet
        rta_app_name = f"{names['rta']}_app"
        model.add(Resource(
            "aws_route_table_association", rta_app_name,
            {
                "route_table_id": Ref(f"aws_route_table.{rt_public_name}.id"),
                "subnet_id": Ref(f"aws_subnet.{app_sub_name}.id"),
            }
        ))

        if self.route_table_layout == "separate":
            rt_db_name = names["rt_db"]
            model.add(Resource(
                "aws_route_table", rt_db_name,
                {
                    "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
                }
            ))
            if self.use_count_for_db_subnets:
                model.add(Resource(
                    "aws_route_table_association", f"{names['rta']}_db",
                    {
                        "route_table_id": Ref(f"aws_route_table.{rt_db_name}.id"),
                        "subnet_id": RawExpr(f"aws_subnet.{db_sub_name}[count.index].id"),
                    },
                    count=self.db_subnet_count,
                ))
            else:
                for i in range(self.db_subnet_count):
                    model.add(Resource(
                        "aws_route_table_association", f"{names['rta']}_db_{i+1}",
                        {
                            "route_table_id": Ref(f"aws_route_table.{rt_db_name}.id"),
                            "subnet_id": Ref(f"aws_subnet.{db_sub_name}_{i+1}.id"),
                        }
                    ))

        # 6. Security Groups
        app_sg_name = names["app_sg"]
        db_sg_name = names["db_sg"]

        app_inline_blocks: list[Block] = []
        db_inline_blocks: list[Block] = []

        # Standard egress on app SG
        app_egress = Block("egress", {
            "cidr_blocks": SortedList(["0.0.0.0/0"]),
            "from_port": 0,
            "protocol": "-1",
            "to_port": 0,
        })
        # Standard egress on db SG
        db_egress = Block("egress", {
            "cidr_blocks": SortedList(["0.0.0.0/0"]),
            "from_port": 0,
            "protocol": "-1",
            "to_port": 0,
        })

        # Check SG style
        app_is_inline = self.sg_style in ("all_inline", "mixed_app_inline_db_separate")
        db_is_inline = self.sg_style in ("all_inline", "mixed_app_separate_db_inline")

        # Public SSH if sec_001_violated
        if variant == "sec_001_violated":
            if app_is_inline:
                app_inline_blocks.append(Block("ingress", {
                    "cidr_blocks": SortedList(["0.0.0.0/0"]),
                    "from_port": 22,
                    "protocol": "tcp",
                    "to_port": 22,
                }))
            else:
                model.add(Resource(
                    "aws_security_group_rule", f"{app_sg_name}_ssh_public",
                    {
                        "cidr_blocks": SortedList(["0.0.0.0/0"]),
                        "from_port": 22,
                        "protocol": "tcp",
                        "security_group_id": Ref(f"aws_security_group.{app_sg_name}.id"),
                        "to_port": 22,
                        "type": "ingress",
                    }
                ))

        # Public DB port if sec_002_violated
        if variant == "sec_002_violated":
            if db_is_inline:
                db_inline_blocks.append(Block("ingress", {
                    "cidr_blocks": SortedList(["0.0.0.0/0"]),
                    "from_port": 5432,
                    "protocol": "tcp",
                    "to_port": 5432,
                }))
            else:
                model.add(Resource(
                    "aws_security_group_rule", f"{db_sg_name}_public_5432",
                    {
                        "cidr_blocks": SortedList(["0.0.0.0/0"]),
                        "from_port": 5432,
                        "protocol": "tcp",
                        "security_group_id": Ref(f"aws_security_group.{db_sg_name}.id"),
                        "to_port": 5432,
                        "type": "ingress",
                    }
                ))

        # Functional path: ingress 5432 from app SG to db SG
        if db_is_inline:
            db_inline_blocks.append(Block("ingress", {
                "from_port": 5432,
                "protocol": "tcp",
                "security_groups": [Ref(f"aws_security_group.{app_sg_name}.id")],
                "to_port": 5432,
            }))
            db_inline_blocks.append(db_egress)
        else:
            model.add(Resource(
                "aws_security_group_rule", f"{db_sg_name}_from_app_5432",
                {
                    "from_port": 5432,
                    "protocol": "tcp",
                    "security_group_id": Ref(f"aws_security_group.{db_sg_name}.id"),
                    "source_security_group_id": Ref(f"aws_security_group.{app_sg_name}.id"),
                    "to_port": 5432,
                    "type": "ingress",
                }
            ))
            model.add(Resource(
                "aws_security_group_rule", f"{db_sg_name}_egress",
                {
                    "cidr_blocks": SortedList(["0.0.0.0/0"]),
                    "from_port": 0,
                    "protocol": "-1",
                    "security_group_id": Ref(f"aws_security_group.{db_sg_name}.id"),
                    "to_port": 0,
                    "type": "egress",
                }
            ))

        if app_is_inline:
            app_inline_blocks.append(app_egress)
        else:
            model.add(Resource(
                "aws_security_group_rule", f"{app_sg_name}_egress",
                {
                    "cidr_blocks": SortedList(["0.0.0.0/0"]),
                    "from_port": 0,
                    "protocol": "-1",
                    "security_group_id": Ref(f"aws_security_group.{app_sg_name}.id"),
                    "to_port": 0,
                    "type": "egress",
                }
            ))

        # App SG resource
        model.add(Resource(
            "aws_security_group", app_sg_name,
            {
                "description": f"Application security group for {self.id}",
                "name": f"{app_sg_name}-{self.id}",
                "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
            },
            blocks=app_inline_blocks,
        ))

        # DB SG resource
        model.add(Resource(
            "aws_security_group", db_sg_name,
            {
                "description": f"Database security group for {self.id}",
                "name": f"{db_sg_name}-{self.id}",
                "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
            },
            blocks=db_inline_blocks,
        ))

        # Optional second app SG
        app_sg_ids = [Ref(f"aws_security_group.{app_sg_name}.id")]
        if self.has_second_app_sg:
            app_sg_extra_name = f"{app_sg_name}_extra"
            model.add(Resource(
                "aws_security_group", app_sg_extra_name,
                {
                    "description": f"Secondary application security group for {self.id}",
                    "name": f"{app_sg_extra_name}-{self.id}",
                    "vpc_id": Ref(f"aws_vpc.{vpc_name}.id"),
                }
            ))
            app_sg_ids.append(Ref(f"aws_security_group.{app_sg_extra_name}.id"))

        # 7. EC2 Instance
        ec2_name = names["ec2"]
        model.add(Resource(
            "aws_instance", ec2_name,
            {
                "ami": "ami-0c55b159cbfafe1f0",
                "instance_type": self.instance_class,
                "subnet_id": Ref(f"aws_subnet.{app_sub_name}.id"),
                "vpc_security_group_ids": app_sg_ids,
            }
        ))

        # 8. DB Subnet Group
        dbsg_name = names["db_subnet_group"]
        model.add(Resource(
            "aws_db_subnet_group", dbsg_name,
            {
                "name": f"{dbsg_name}-{self.id}",
                "subnet_ids": db_sub_refs,
            }
        ))

        # 9. RDS Instance
        rds_name = names["rds"]
        is_public = (variant == "sec_003_violated")
        rds_identifier = f"{rds_name.replace('_', '-')}-{self.id.lower()}"
        model.add(Resource(
            "aws_db_instance", rds_name,
            {
                "allocated_storage": 20,
                "db_subnet_group_name": Ref(f"aws_db_subnet_group.{dbsg_name}.name"),
                "engine": "postgres",
                "identifier": rds_identifier,
                "instance_class": self.db_class,
                "password": VarRef("db_password"),
                "publicly_accessible": is_public,
                "skip_final_snapshot": True,
                "username": "postgres",
                "vpc_security_group_ids": [Ref(f"aws_security_group.{db_sg_name}.id")],
            }
        ))

        return model, param_meta

    def has_functional_path_structural(self, model: HCLModel) -> bool:
        """Structural check: db SG allows tcp 5432 ingress from app SG."""
        app_sg_addr = f"aws_security_group.{_resolve_names(self.naming_scheme)['app_sg']}"
        db_sg_addr = f"aws_security_group.{_resolve_names(self.naming_scheme)['db_sg']}"

        # Case 1: inline on db SG
        if db_sg_addr in model.resources:
            db_res = model.resources[db_sg_addr]
            for b in db_res.blocks:
                if b.label == "ingress" and b.attrs.get("to_port") == 5432:
                    sgs = b.attrs.get("security_groups", [])
                    if any(str(sg) == f"{app_sg_addr}.id" for sg in sgs):
                        return True

        # Case 2: separate rule resource
        for addr, res in model.resources.items():
            if res.type == "aws_security_group_rule" and res.attrs.get("type") == "ingress":
                if res.attrs.get("to_port") == 5432:
                    src_sg = str(res.attrs.get("source_security_group_id", ""))
                    tgt_sg = str(res.attrs.get("security_group_id", ""))
                    if src_sg == f"{app_sg_addr}.id" and tgt_sg == f"{db_sg_addr}.id":
                        return True

        return False

    def has_public_ssh_structural(self, model: HCLModel) -> bool:
        """Structural check: any SG allows 0.0.0.0/0 or ::/0 ingress to port 22."""
        # Inline
        for res in model.resources.values():
            if res.type == "aws_security_group":
                for b in res.blocks:
                    if b.label == "ingress" and b.attrs.get("to_port") == 22:
                        cidrs = b.attrs.get("cidr_blocks")
                        if isinstance(cidrs, SortedList):
                            cidrs = list(cidrs.items)
                        elif not isinstance(cidrs, list):
                            cidrs = []
                        if any(c in ("0.0.0.0/0", "::/0") for c in cidrs):
                            return True

        # Separate rule
        for res in model.resources.values():
            if res.type == "aws_security_group_rule" and res.attrs.get("type") == "ingress":
                if res.attrs.get("to_port") == 22:
                    cidrs = res.attrs.get("cidr_blocks")
                    if isinstance(cidrs, SortedList):
                        cidrs = list(cidrs.items)
                    elif not isinstance(cidrs, list):
                        cidrs = []
                    if any(c in ("0.0.0.0/0", "::/0") for c in cidrs):
                        return True

        return False

    def has_public_db_structural(self, model: HCLModel) -> bool:
        """Structural check: any SG allows 0.0.0.0/0 or ::/0 ingress to port 5432."""
        # Inline
        for res in model.resources.values():
            if res.type == "aws_security_group":
                for b in res.blocks:
                    if b.label == "ingress" and b.attrs.get("to_port") == 5432:
                        cidrs = b.attrs.get("cidr_blocks")
                        if isinstance(cidrs, SortedList):
                            cidrs = list(cidrs.items)
                        elif not isinstance(cidrs, list):
                            cidrs = []
                        if any(c in ("0.0.0.0/0", "::/0") for c in cidrs):
                            return True

        # Separate rule
        for res in model.resources.values():
            if res.type == "aws_security_group_rule" and res.attrs.get("type") == "ingress":
                if res.attrs.get("to_port") == 5432:
                    cidrs = res.attrs.get("cidr_blocks")
                    if isinstance(cidrs, SortedList):
                        cidrs = list(cidrs.items)
                    elif not isinstance(cidrs, list):
                        cidrs = []
                    if any(c in ("0.0.0.0/0", "::/0") for c in cidrs):
                        return True

        return False


def _resolve_names(scheme: str) -> dict[str, str]:
    if scheme == "kebab":
        return {
            "vpc": "vpc_main",
            "igw": "igw_main",
            "app_subnet": "sub_app",
            "db_subnet": "sub_db",
            "rt_public": "rt_public",
            "rt_db": "rt_db",
            "rta": "rta",
            "app_sg": "sg_app",
            "db_sg": "sg_db",
            "ec2": "ec2_app",
            "db_subnet_group": "dbsng_main",
            "rds": "rds_postgres",
        }
    if scheme == "tier":
        return {
            "vpc": "network",
            "igw": "gateway",
            "app_subnet": "web_tier",
            "db_subnet": "data_tier",
            "rt_public": "public_route",
            "rt_db": "data_route",
            "rta": "assoc",
            "app_sg": "web_secgroup",
            "db_sg": "data_secgroup",
            "ec2": "web_instance",
            "db_subnet_group": "data_subnets",
            "rds": "data_instance",
        }
    if scheme == "component":
        return {
            "vpc": "corp_vpc",
            "igw": "corp_igw",
            "app_subnet": "frontend_subnet",
            "db_subnet": "backend_subnet",
            "rt_public": "frontend_rt",
            "rt_db": "backend_rt",
            "rta": "assoc",
            "app_sg": "frontend_sg",
            "db_sg": "backend_sg",
            "ec2": "frontend_server",
            "db_subnet_group": "backend_sng",
            "rds": "backend_database",
        }
    if scheme == "env":
        return {
            "vpc": "prod_vpc",
            "igw": "prod_igw",
            "app_subnet": "prod_app_subnet",
            "db_subnet": "prod_db_subnet",
            "rt_public": "prod_public_rt",
            "rt_db": "prod_db_rt",
            "rta": "prod_rta",
            "app_sg": "prod_app_sg",
            "db_sg": "prod_db_sg",
            "ec2": "prod_app_server",
            "db_subnet_group": "prod_db_sng",
            "rds": "prod_postgres_db",
        }
    # default / standard
    return {
        "vpc": "main",
        "igw": "igw",
        "app_subnet": "app",
        "db_subnet": "db",
        "rt_public": "public",
        "rt_db": "db",
        "rta": "rta",
        "app_sg": "app",
        "db_sg": "db",
        "ec2": "app",
        "db_subnet_group": "main",
        "rds": "main",
    }


# The 10 controlled templates
TEMPLATES: dict[str, TemplateDef] = {
    "tpl-01": TemplateDef(
        id="tpl-01",
        version=TEMPLATE_VERSION,
        sg_style="all_separate",
        db_subnet_count=2,
        has_second_app_sg=False,
        route_table_layout="shared",
        use_count_for_db_subnets=False,
        instance_class="t3.micro",
        db_class="db.t3.micro",
        naming_scheme="standard",
    ),
    "tpl-02": TemplateDef(
        id="tpl-02",
        version=TEMPLATE_VERSION,
        sg_style="all_inline",
        db_subnet_count=2,
        has_second_app_sg=False,
        route_table_layout="separate",
        use_count_for_db_subnets=False,
        instance_class="t3.small",
        db_class="db.t3.small",
        naming_scheme="kebab",
    ),
    "tpl-03": TemplateDef(
        id="tpl-03",
        version=TEMPLATE_VERSION,
        sg_style="mixed_app_inline_db_separate",
        db_subnet_count=3,
        has_second_app_sg=False,
        route_table_layout="shared",
        use_count_for_db_subnets=True,
        instance_class="t3.nano",
        db_class="db.t3.micro",
        naming_scheme="tier",
    ),
    "tpl-04": TemplateDef(
        id="tpl-04",
        version=TEMPLATE_VERSION,
        sg_style="mixed_app_separate_db_inline",
        db_subnet_count=2,
        has_second_app_sg=True,
        route_table_layout="separate",
        use_count_for_db_subnets=False,
        instance_class="t3.micro",
        db_class="db.t3.medium",
        naming_scheme="standard",
    ),
    "tpl-05": TemplateDef(
        id="tpl-05",
        version=TEMPLATE_VERSION,
        sg_style="all_separate",
        db_subnet_count=3,
        has_second_app_sg=True,
        route_table_layout="shared",
        use_count_for_db_subnets=False,
        instance_class="t3.small",
        db_class="db.t3.micro",
        naming_scheme="component",
    ),
    "tpl-06": TemplateDef(
        id="tpl-06",
        version=TEMPLATE_VERSION,
        sg_style="all_inline",
        db_subnet_count=3,
        has_second_app_sg=False,
        route_table_layout="separate",
        use_count_for_db_subnets=True,
        instance_class="t3.medium",
        db_class="db.t3.small",
        naming_scheme="env",
    ),
    "tpl-07": TemplateDef(
        id="tpl-07",
        version=TEMPLATE_VERSION,
        sg_style="mixed_app_inline_db_separate",
        db_subnet_count=2,
        has_second_app_sg=True,
        route_table_layout="separate",
        use_count_for_db_subnets=False,
        instance_class="t3.micro",
        db_class="db.t3.micro",
        naming_scheme="kebab",
    ),
    "tpl-08": TemplateDef(
        id="tpl-08",
        version=TEMPLATE_VERSION,
        sg_style="mixed_app_separate_db_inline",
        db_subnet_count=3,
        has_second_app_sg=False,
        route_table_layout="shared",
        use_count_for_db_subnets=False,
        instance_class="t3.nano",
        db_class="db.t3.micro",
        naming_scheme="standard",
    ),
    "tpl-09": TemplateDef(
        id="tpl-09",
        version=TEMPLATE_VERSION,
        sg_style="all_separate",
        db_subnet_count=2,
        has_second_app_sg=False,
        route_table_layout="separate",
        use_count_for_db_subnets=True,
        instance_class="t3.small",
        db_class="db.t3.small",
        naming_scheme="tier",
    ),
    "tpl-10": TemplateDef(
        id="tpl-10",
        version=TEMPLATE_VERSION,
        sg_style="all_inline",
        db_subnet_count=2,
        has_second_app_sg=True,
        route_table_layout="shared",
        use_count_for_db_subnets=False,
        instance_class="t3.micro",
        db_class="db.t3.nano",
        naming_scheme="component",
    ),
}
