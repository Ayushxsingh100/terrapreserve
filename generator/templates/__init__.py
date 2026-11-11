"""Thirty-three controlled templates for TerraPreserve (D4-05, D4c-01, D4c-03).

All templates implement the Doc 04 Appendix B topology (EC2 -> RDS on 5432, VPC, subnets, IGW, route table and
association, app and DB groups) with the supported types of Doc 04 plus the tolerated ``aws_db_subnet_group``.
They are written by hand here, not copied from any DAIL file. Each template is described by the eight D4c-03
variation axes (``AXES``); ``generator/templates/FEATURES.md`` is generated from ``features_table()``:

1. ``sg_style``: all_inline | all_separate | app_inline_db_separate | app_separate_db_inline. A group is either
   inline or separate, in both directions, so no group is MIXED (registry 2.6).
2. ``naming``: standard | kebab | tier | component | env | prefixed | short | role.
3. ``subnets``: one_app (one app subnet) | two_app (two app subnets in two AZs) | db_count (the DB subnets are
   created with ``count``).
4. ``routing``: shared_public (one public route table for the app subnets; the DB subnets use the VPC main table)
   | private_db (plus a private route table with no IGW route for the DB subnets) | per_subnet (one route table per
   subnet; only the app tables route to the IGW). No route inside the VPC CIDR has a non-local target (M3).
5. ``files``: single (``main.tf``) | split (``network.tf``, ``compute.tf``, ``database.tf``).
6. ``values``: literal | variables (variables with defaults) | locals. Only attributes no invariant reads (AMI,
   instance type, DB instance class) are written through variables or locals; ports, CIDRs, sources,
   ``publicly_accessible`` and group references are always literals.
7. ``extras``: none | second_app_sg (an empty second group on the instance; tpl-04, 05, 07, 10 as in D4-05) |
   unattached_sg (a group attached to nothing that opens only TCP 443 from the VPC CIDR) | extra_subnet.
8. ``egress``: all (allow-all egress on the app group) | db_only (TCP 5432 to the DB group only). ``db_only`` is
   never used with all_inline: two inline groups that reference each other form a dependency cycle.

The ten D4-05 templates keep their structure. tpl-08 (files: split) and tpl-10 (values: locals) each take one
new axis value so every pair of templates differs on at least two axes (D4c-03 distinctness rule).

Standard library and generator model only. No DAIL import (D0 gate 1).
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any

import emitter
from model import Block, HCLModel, RawExpr, Ref, Resource, SortedList, Variable, VarRef

TEMPLATE_VERSION: str = "tpl-v2.0"

AXES: dict[str, tuple[str, ...]] = {
    "sg_style": ("all_inline", "all_separate", "app_inline_db_separate", "app_separate_db_inline"),
    "naming": ("standard", "kebab", "tier", "component", "env", "prefixed", "short", "role"),
    "subnets": ("one_app", "two_app", "db_count"),
    "routing": ("shared_public", "private_db", "per_subnet"),
    "files": ("single", "split"),
    "values": ("literal", "variables", "locals"),
    "extras": ("none", "second_app_sg", "unattached_sg", "extra_subnet"),
    "egress": ("all", "db_only"),
}

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

APP_AMI = "ami-0c55b159cbfafe1f0"
# The default behind var./local. AMIs differs from APP_AMI, so op_f5_force_replacement_safe (which writes APP_AMI
# when the current value is not APP_AMI) still changes the AMI value in the plan.
INDIRECT_AMI = "ami-0d5eff06f840b45e9"

NETWORK_TYPES = ("aws_vpc", "aws_internet_gateway", "aws_subnet", "aws_route_table", "aws_route_table_association")
DATABASE_TYPES = ("aws_db_instance", "aws_db_subnet_group")


@dataclass(frozen=True)
class TemplateDef:
    id: str
    version: str
    sg_style: str
    naming: str
    subnets: str
    routing: str
    files: str
    values: str
    extras: str
    egress: str
    db_subnet_count: int  # 2 | 3
    instance_class: str
    db_class: str
    terragoat_vocabulary: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: copy.deepcopy(TERRAGOAT_VOCABULARY)
    )

    # D4-05 names, kept for the older tests and tools.
    @property
    def naming_scheme(self) -> str:
        return self.naming

    @property
    def has_second_app_sg(self) -> bool:
        return self.extras == "second_app_sg"

    @property
    def use_count_for_db_subnets(self) -> bool:
        return self.subnets == "db_count"

    @property
    def route_table_layout(self) -> str:
        return self.routing

    def features(self) -> dict[str, str]:
        return {axis: getattr(self, axis) for axis in AXES}

    def endpoints(self) -> dict[str, str]:
        """Registry 6.1 endpoint binding (D5-12): the application instance S and the database D this template builds."""
        names = _resolve_names(self.naming)
        return {"S": f"aws_instance.{names['ec2']}", "D": f"aws_db_instance.{names['rds']}"}

    # ------------------------------------------------------------------------------------------------------
    # Values written through variables or locals (axis 6)
    # ------------------------------------------------------------------------------------------------------

    def _indirect(self) -> dict[str, Any]:
        """The three indirect values: name -> literal default."""
        return {"app_ami": INDIRECT_AMI, "app_instance_type": self.instance_class, "db_instance_class": self.db_class}

    def _val(self, name: str, literal: Any) -> Any:
        if self.values == "variables":
            return VarRef(name)
        if self.values == "locals":
            return RawExpr(f"local.{name}")
        return literal

    def locals_tf(self) -> str | None:
        if self.values != "locals":
            return None
        lines = emitter._emit_attrs_block(self._indirect(), [], indent=1)
        return "locals {\n" + "\n".join(lines) + "\n}\n"

    # ------------------------------------------------------------------------------------------------------
    # Instantiation
    # ------------------------------------------------------------------------------------------------------

    def instantiate(
        self,
        rng: random.Random,
        variant: str = "clean",
    ) -> tuple[HCLModel, dict[str, Any]]:
        """Instantiate the template into an HCLModel and parameter metadata.

        variant: clean (all four invariants hold) | sec_001_violated (public SSH on the app group) |
        sec_002_violated (public 5432 on the DB group) | sec_003_violated (publicly_accessible = true).
        """
        cidr_octet = rng.randint(10, 200)
        vpc_cidr = f"10.{cidr_octet}.0.0/16"
        app_subnet_cidr = f"10.{cidr_octet}.1.0/24"
        app2_subnet_cidr = f"10.{cidr_octet}.2.0/24"
        extra_subnet_cidr = f"10.{cidr_octet}.200.0/24"
        db_subnet_cidrs = [f"10.{cidr_octet}.{10 + i}.0/24" for i in range(self.db_subnet_count)]
        azs = ["us-east-1a", "us-east-1b", "us-east-1c"][:max(self.db_subnet_count, 2)]

        cidr_plan: dict[str, Any] = {"vpc": vpc_cidr, "app": app_subnet_cidr, "db": db_subnet_cidrs}
        if self.subnets == "two_app":
            cidr_plan["app_2"] = app2_subnet_cidr
        if self.extras == "extra_subnet":
            cidr_plan["extra"] = extra_subnet_cidr
        param_meta = {
            "template_id": self.id,
            "template_version": self.version,
            "variant": variant,
            "cidr_plan": cidr_plan,
            "azs": azs,
            "instance_class": self.instance_class,
            "db_class": self.db_class,
            "naming_scheme": self.naming,
            "sg_style": self.sg_style,
            "features": self.features(),
        }

        names = _resolve_names(self.naming)
        model = HCLModel()
        if self.values == "variables":
            descr = {"app_ami": "AMI of the application instance.",
                     "app_instance_type": "Instance type of the application instance.",
                     "db_instance_class": "Instance class of the database."}
            for vname, default in self._indirect().items():
                model.add_variable(Variable(vname, {"default": default, "description": descr[vname],
                                                    "type": RawExpr("string")}))

        vpc_name = names["vpc"]
        vpc_id = Ref(f"aws_vpc.{vpc_name}.id")
        model.add(Resource("aws_vpc", vpc_name, {
            "cidr_block": vpc_cidr,
            "enable_dns_hostnames": True,
            "enable_dns_support": True,
        }))
        igw_name = names["igw"]
        model.add(Resource("aws_internet_gateway", igw_name, {"vpc_id": vpc_id}))

        # Subnets. The application subnet is always the first aws_subnet of the model (operators rely on it).
        app_sub_name = names["app_subnet"]
        app_subnets = [app_sub_name]
        model.add(Resource("aws_subnet", app_sub_name, {
            "availability_zone": azs[0], "cidr_block": app_subnet_cidr, "vpc_id": vpc_id,
        }))
        if self.subnets == "two_app":
            app_subnets.append(f"{app_sub_name}_b")
            model.add(Resource("aws_subnet", app_subnets[1], {
                "availability_zone": azs[1], "cidr_block": app2_subnet_cidr, "vpc_id": vpc_id,
            }))

        db_sub_name = names["db_subnet"]
        db_sub_refs: list[Any] = []
        db_sub_names: list[str] = []
        if self.use_count_for_db_subnets:
            az_list_str = "[" + ", ".join(f'"{az}"' for az in azs[:self.db_subnet_count]) + "]"
            cidr_list_str = "[" + ", ".join(f'"{c}"' for c in db_subnet_cidrs) + "]"
            model.add(Resource("aws_subnet", db_sub_name, {
                "availability_zone": RawExpr(f"{az_list_str}[count.index]"),
                "cidr_block": RawExpr(f"{cidr_list_str}[count.index]"),
                "vpc_id": vpc_id,
            }, count=self.db_subnet_count))
            for i in range(self.db_subnet_count):
                db_sub_refs.append(Ref(f"aws_subnet.{db_sub_name}[{i}].id"))
        else:
            for i in range(self.db_subnet_count):
                sub_res_name = f"{db_sub_name}_{i+1}"
                db_sub_names.append(sub_res_name)
                model.add(Resource("aws_subnet", sub_res_name, {
                    "availability_zone": azs[i % len(azs)], "cidr_block": db_subnet_cidrs[i], "vpc_id": vpc_id,
                }))
                db_sub_refs.append(Ref(f"aws_subnet.{sub_res_name}.id"))

        if self.extras == "extra_subnet":
            model.add(Resource("aws_subnet", f"{app_sub_name}_spare", {
                "availability_zone": azs[1], "cidr_block": extra_subnet_cidr, "vpc_id": vpc_id,
            }))

        # Route tables (axis 4)
        igw_route = [Block("route", {"cidr_block": "0.0.0.0/0", "gateway_id": Ref(f"aws_internet_gateway.{igw_name}.id")})]
        rta = names["rta"]
        if self.routing in ("shared_public", "private_db"):
            rt_public_name = names["rt_public"]
            model.add(Resource("aws_route_table", rt_public_name, {"vpc_id": vpc_id}, blocks=copy.deepcopy(igw_route)))
            for j, sub in enumerate(app_subnets):
                model.add(Resource("aws_route_table_association", f"{rta}_app" + ("" if j == 0 else "_b"), {
                    "route_table_id": Ref(f"aws_route_table.{rt_public_name}.id"),
                    "subnet_id": Ref(f"aws_subnet.{sub}.id"),
                }))
        else:  # per_subnet
            for j, sub in enumerate(app_subnets):
                rt_name = f"{names['rt_public']}_{'a' if j == 0 else 'b'}"
                model.add(Resource("aws_route_table", rt_name, {"vpc_id": vpc_id}, blocks=copy.deepcopy(igw_route)))
                model.add(Resource("aws_route_table_association", f"{rta}_app" + ("" if j == 0 else "_b"), {
                    "route_table_id": Ref(f"aws_route_table.{rt_name}.id"),
                    "subnet_id": Ref(f"aws_subnet.{sub}.id"),
                }))
        if self.routing in ("private_db", "per_subnet"):
            rt_db_name = names["rt_db"]
            per_subnet = self.routing == "per_subnet"
            if self.use_count_for_db_subnets:
                model.add(Resource("aws_route_table", rt_db_name, {"vpc_id": vpc_id},
                                   count=self.db_subnet_count if per_subnet else None))
                rt_ref = (RawExpr(f"aws_route_table.{rt_db_name}[count.index].id") if per_subnet
                          else Ref(f"aws_route_table.{rt_db_name}.id"))
                model.add(Resource("aws_route_table_association", f"{rta}_db", {
                    "route_table_id": rt_ref,
                    "subnet_id": RawExpr(f"aws_subnet.{db_sub_name}[count.index].id"),
                }, count=self.db_subnet_count))
            else:
                if not per_subnet:
                    model.add(Resource("aws_route_table", rt_db_name, {"vpc_id": vpc_id}))
                for i, sub in enumerate(db_sub_names):
                    rt_i = f"{rt_db_name}_{i+1}" if per_subnet else rt_db_name
                    if per_subnet:
                        model.add(Resource("aws_route_table", rt_i, {"vpc_id": vpc_id}))
                    model.add(Resource("aws_route_table_association", f"{rta}_db_{i+1}", {
                        "route_table_id": Ref(f"aws_route_table.{rt_i}.id"),
                        "subnet_id": Ref(f"aws_subnet.{sub}.id"),
                    }))

        # Security groups (axes 1, 7, 8)
        app_sg_name = names["app_sg"]
        db_sg_name = names["db_sg"]
        app_ref = Ref(f"aws_security_group.{app_sg_name}.id")
        db_ref = Ref(f"aws_security_group.{db_sg_name}.id")
        app_inline_blocks: list[Block] = []
        db_inline_blocks: list[Block] = []
        app_is_inline = self.sg_style in ("all_inline", "app_inline_db_separate")
        db_is_inline = self.sg_style in ("all_inline", "app_separate_db_inline")

        if variant == "sec_001_violated":
            if app_is_inline:
                app_inline_blocks.append(Block("ingress", {
                    "cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 22, "protocol": "tcp", "to_port": 22,
                }))
            else:
                model.add(Resource("aws_security_group_rule", f"{app_sg_name}_ssh_public", {
                    "cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 22, "protocol": "tcp",
                    "security_group_id": app_ref, "to_port": 22, "type": "ingress",
                }))

        if variant == "sec_002_violated":
            if db_is_inline:
                db_inline_blocks.append(Block("ingress", {
                    "cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 5432, "protocol": "tcp", "to_port": 5432,
                }))
            else:
                model.add(Resource("aws_security_group_rule", f"{db_sg_name}_public_5432", {
                    "cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 5432, "protocol": "tcp",
                    "security_group_id": db_ref, "to_port": 5432, "type": "ingress",
                }))

        # Functional path: ingress 5432 from the app group to the DB group
        if db_is_inline:
            db_inline_blocks.append(Block("ingress", {
                "from_port": 5432, "protocol": "tcp", "security_groups": [app_ref], "to_port": 5432,
            }))
            db_inline_blocks.append(Block("egress", {
                "cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 0, "protocol": "-1", "to_port": 0,
            }))
        else:
            model.add(Resource("aws_security_group_rule", f"{db_sg_name}_from_app_5432", {
                "from_port": 5432, "protocol": "tcp", "security_group_id": db_ref,
                "source_security_group_id": app_ref, "to_port": 5432, "type": "ingress",
            }))
            model.add(Resource("aws_security_group_rule", f"{db_sg_name}_egress", {
                "cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 0, "protocol": "-1",
                "security_group_id": db_ref, "to_port": 0, "type": "egress",
            }))

        # App egress (axis 8)
        if self.egress == "db_only":
            if self.sg_style == "all_inline":
                raise ValueError(f"{self.id}: egress db_only with all_inline groups is a dependency cycle")
            if app_is_inline:
                app_inline_blocks.append(Block("egress", {
                    "from_port": 5432, "protocol": "tcp", "security_groups": [db_ref], "to_port": 5432,
                }))
            else:
                model.add(Resource("aws_security_group_rule", f"{app_sg_name}_egress_db", {
                    "from_port": 5432, "protocol": "tcp", "security_group_id": app_ref,
                    "source_security_group_id": db_ref, "to_port": 5432, "type": "egress",
                }))
        elif app_is_inline:
            app_inline_blocks.append(Block("egress", {
                "cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 0, "protocol": "-1", "to_port": 0,
            }))
        else:
            model.add(Resource("aws_security_group_rule", f"{app_sg_name}_egress", {
                "cidr_blocks": SortedList(["0.0.0.0/0"]), "from_port": 0, "protocol": "-1",
                "security_group_id": app_ref, "to_port": 0, "type": "egress",
            }))

        model.add(Resource("aws_security_group", app_sg_name, {
            "description": f"Application security group for {self.id}",
            "name": f"{app_sg_name}-{self.id}",
            "vpc_id": vpc_id,
        }, blocks=app_inline_blocks))
        model.add(Resource("aws_security_group", db_sg_name, {
            "description": f"Database security group for {self.id}",
            "name": f"{db_sg_name}-{self.id}",
            "vpc_id": vpc_id,
        }, blocks=db_inline_blocks))

        app_sg_ids = [app_ref]
        if self.has_second_app_sg:
            app_sg_extra_name = f"{app_sg_name}_extra"
            model.add(Resource("aws_security_group", app_sg_extra_name, {
                "description": f"Secondary application security group for {self.id}",
                "name": f"{app_sg_extra_name}-{self.id}",
                "vpc_id": vpc_id,
            }))
            app_sg_ids.append(Ref(f"aws_security_group.{app_sg_extra_name}.id"))
        if self.extras == "unattached_sg":
            ops_name = f"{app_sg_name}_ops"
            model.add(Resource("aws_security_group", ops_name, {
                "description": f"Operations security group for {self.id}, attached to nothing",
                "name": f"{ops_name}-{self.id}",
                "vpc_id": vpc_id,
            }, blocks=[Block("ingress", {
                "cidr_blocks": SortedList([vpc_cidr]), "from_port": 443, "protocol": "tcp", "to_port": 443,
            })]))

        ec2_name = names["ec2"]
        model.add(Resource("aws_instance", ec2_name, {
            "ami": self._val("app_ami", APP_AMI),
            "instance_type": self._val("app_instance_type", self.instance_class),
            "subnet_id": Ref(f"aws_subnet.{app_sub_name}.id"),
            "vpc_security_group_ids": app_sg_ids,
        }))

        dbsng_name = names["db_subnet_group"]
        model.add(Resource("aws_db_subnet_group", dbsng_name, {
            "name": f"{dbsng_name}-{self.id}",
            "subnet_ids": db_sub_refs,
        }))

        rds_name = names["rds"]
        rds_identifier = f"{rds_name.replace('_', '-')}-{self.id.lower()}"
        model.add(Resource("aws_db_instance", rds_name, {
            "allocated_storage": 20,
            "db_subnet_group_name": Ref(f"aws_db_subnet_group.{dbsng_name}.name"),
            "engine": "postgres",
            "identifier": rds_identifier,
            "instance_class": self._val("db_instance_class", self.db_class),
            "password": VarRef("db_password"),
            "publicly_accessible": variant == "sec_003_violated",
            "skip_final_snapshot": True,
            "username": "postgres",
            "vpc_security_group_ids": [db_ref],
        }))

        return model, param_meta

    # ------------------------------------------------------------------------------------------------------
    # Emission (axis 5)
    # ------------------------------------------------------------------------------------------------------

    def emit_step_files(self, model: HCLModel) -> dict[str, str]:
        """The step directory's files: versions.tf, variables.tf, optional locals.tf, and the resource files."""
        variables_tf = emitter.emit_db_password_variable()
        if model.variables:
            variables_tf += "\n" + emitter.emit_variables(model)
        files: dict[str, str] = {"variables.tf": variables_tf, "versions.tf": emitter.emit_versions()}
        loc = self.locals_tf()
        if loc is not None:
            files["locals.tf"] = loc
        if self.files == "single":
            files["main.tf"] = emitter.emit(model)
            return dict(sorted(files.items()))
        parts = {"network.tf": HCLModel(), "compute.tf": HCLModel(), "database.tf": HCLModel()}
        where: dict[str, str] = {}
        for addr, res in model.resources.items():
            f = _file_of(model, res)
            where[addr] = f
            parts[f].resources[addr] = res
        for mv in model.moved:
            parts[where.get(mv.to_addr.expr, "network.tf")].moved.append(mv)
        for name, part in parts.items():
            files[name] = emitter.emit(part)
        return dict(sorted(files.items()))

    # ------------------------------------------------------------------------------------------------------
    # Structural checks (D4-05 tests)
    # ------------------------------------------------------------------------------------------------------

    def has_functional_path_structural(self, model: HCLModel) -> bool:
        """Structural check: db SG allows tcp 5432 ingress from app SG."""
        app_sg_addr = f"aws_security_group.{_resolve_names(self.naming)['app_sg']}"
        db_sg_addr = f"aws_security_group.{_resolve_names(self.naming)['db_sg']}"
        if db_sg_addr in model.resources:
            for b in model.resources[db_sg_addr].blocks:
                if b.label == "ingress" and b.attrs.get("to_port") == 5432:
                    if any(str(sg) == f"{app_sg_addr}.id" for sg in b.attrs.get("security_groups", [])):
                        return True
        for res in model.resources.values():
            if res.type == "aws_security_group_rule" and res.attrs.get("type") == "ingress" \
                    and res.attrs.get("to_port") == 5432:
                if str(res.attrs.get("source_security_group_id", "")) == f"{app_sg_addr}.id" \
                        and str(res.attrs.get("security_group_id", "")) == f"{db_sg_addr}.id":
                    return True
        return False

    def _world_ingress(self, model: HCLModel, port: int) -> bool:
        holders = []
        for res in model.resources.values():
            if res.type == "aws_security_group":
                holders += [b.attrs for b in res.blocks if b.label == "ingress"]
            elif res.type == "aws_security_group_rule" and res.attrs.get("type") == "ingress":
                holders.append(res.attrs)
        for attrs in holders:
            if attrs.get("to_port") != port:
                continue
            cidrs = attrs.get("cidr_blocks")
            cidrs = list(cidrs.items) if isinstance(cidrs, SortedList) else (cidrs if isinstance(cidrs, list) else [])
            if any(c in ("0.0.0.0/0", "::/0") for c in cidrs):
                return True
        return False

    def has_public_ssh_structural(self, model: HCLModel) -> bool:
        """Structural check: any SG allows 0.0.0.0/0 or ::/0 ingress to port 22."""
        return self._world_ingress(model, 22)

    def has_public_db_structural(self, model: HCLModel) -> bool:
        """Structural check: any SG allows 0.0.0.0/0 or ::/0 ingress to port 5432."""
        return self._world_ingress(model, 5432)


def _file_of(model: HCLModel, res: Resource) -> str:
    """Split layout: network types -> network.tf; the database, its subnet group, the groups attached to an
    aws_db_instance and their rules -> database.tf; everything else -> compute.tf."""
    if res.type in NETWORK_TYPES:
        return "network.tf"
    if res.type in DATABASE_TYPES:
        return "database.tf"
    db_groups = {str(r)[:-3] for d in model.resources.values() if d.type == "aws_db_instance"
                 for r in d.attrs.get("vpc_security_group_ids", []) if str(r).endswith(".id")}
    if res.type == "aws_security_group":
        return "database.tf" if res.address in db_groups else "compute.tf"
    if res.type == "aws_security_group_rule":
        g = str(res.attrs.get("security_group_id", ""))
        return "database.tf" if g.endswith(".id") and g[:-3] in db_groups else "compute.tf"
    return "compute.tf"


_NAMES: dict[str, dict[str, str]] = {
    "standard": {"vpc": "main", "igw": "igw", "app_subnet": "app", "db_subnet": "db", "rt_public": "public",
                 "rt_db": "db", "rta": "rta", "app_sg": "app", "db_sg": "db", "ec2": "app",
                 "db_subnet_group": "main", "rds": "main"},
    "kebab": {"vpc": "vpc_main", "igw": "igw_main", "app_subnet": "sub_app", "db_subnet": "sub_db",
              "rt_public": "rt_public", "rt_db": "rt_db", "rta": "rta", "app_sg": "sg_app", "db_sg": "sg_db",
              "ec2": "ec2_app", "db_subnet_group": "dbsng_main", "rds": "rds_postgres"},
    "tier": {"vpc": "network", "igw": "gateway", "app_subnet": "web_tier", "db_subnet": "data_tier",
             "rt_public": "public_route", "rt_db": "data_route", "rta": "assoc", "app_sg": "web_secgroup",
             "db_sg": "data_secgroup", "ec2": "web_instance", "db_subnet_group": "data_subnets",
             "rds": "data_instance"},
    "component": {"vpc": "corp_vpc", "igw": "corp_igw", "app_subnet": "frontend_subnet",
                  "db_subnet": "backend_subnet", "rt_public": "frontend_rt", "rt_db": "backend_rt", "rta": "assoc",
                  "app_sg": "frontend_sg", "db_sg": "backend_sg", "ec2": "frontend_server",
                  "db_subnet_group": "backend_sng", "rds": "backend_database"},
    "env": {"vpc": "prod_vpc", "igw": "prod_igw", "app_subnet": "prod_app_subnet", "db_subnet": "prod_db_subnet",
            "rt_public": "prod_public_rt", "rt_db": "prod_db_rt", "rta": "prod_rta", "app_sg": "prod_app_sg",
            "db_sg": "prod_db_sg", "ec2": "prod_app_server", "db_subnet_group": "prod_db_sng",
            "rds": "prod_postgres_db"},
    "prefixed": {"vpc": "acme_vpc", "igw": "acme_igw", "app_subnet": "acme_app_subnet",
                 "db_subnet": "acme_db_subnet", "rt_public": "acme_public_rt", "rt_db": "acme_db_rt",
                 "rta": "acme_rta", "app_sg": "acme_app_sg", "db_sg": "acme_db_sg", "ec2": "acme_app",
                 "db_subnet_group": "acme_db_sng", "rds": "acme_db"},
    "short": {"vpc": "net", "igw": "gw", "app_subnet": "pub", "db_subnet": "priv", "rt_public": "pub",
              "rt_db": "priv", "rta": "ra", "app_sg": "web", "db_sg": "pg", "ec2": "web",
              "db_subnet_group": "pg", "rds": "pg"},
    "role": {"vpc": "platform", "igw": "edge", "app_subnet": "service", "db_subnet": "storage",
             "rt_public": "edge_routes", "rt_db": "storage_routes", "rta": "route_link",
             "app_sg": "service_access", "db_sg": "storage_access", "ec2": "service_node",
             "db_subnet_group": "storage_subnets", "rds": "storage_db"},
}


def _resolve_names(scheme: str) -> dict[str, str]:
    return dict(_NAMES.get(scheme, _NAMES["standard"]))


def _t(tid: str, sg: str, naming: str, subnets: str, routing: str, files: str, values: str, extras: str,
       egress: str, db_subnets: int, inst: str, dbc: str) -> TemplateDef:
    return TemplateDef(id=tid, version=TEMPLATE_VERSION, sg_style=sg, naming=naming, subnets=subnets,
                       routing=routing, files=files, values=values, extras=extras, egress=egress,
                       db_subnet_count=db_subnets, instance_class=inst, db_class=dbc)


_S, _I, _AIDS, _ASDI = "all_separate", "all_inline", "app_inline_db_separate", "app_separate_db_inline"

# id: sg_style, naming, subnets, routing, files, values, extras, egress, db subnets, instance, db class
TEMPLATES: dict[str, TemplateDef] = {t.id: t for t in (
    # The ten D4-05 templates (tpl-08 and tpl-10 take one new axis value each; D4c-03).
    _t("tpl-01", _S, "standard", "one_app", "shared_public", "single", "literal", "none", "all", 2, "t3.micro", "db.t3.micro"),
    _t("tpl-02", _I, "kebab", "one_app", "private_db", "single", "literal", "none", "all", 2, "t3.small", "db.t3.small"),
    _t("tpl-03", _AIDS, "tier", "db_count", "shared_public", "single", "literal", "none", "all", 3, "t3.nano", "db.t3.micro"),
    _t("tpl-04", _ASDI, "standard", "one_app", "private_db", "single", "literal", "second_app_sg", "all", 2, "t3.micro", "db.t3.medium"),
    _t("tpl-05", _S, "component", "one_app", "shared_public", "single", "literal", "second_app_sg", "all", 3, "t3.small", "db.t3.micro"),
    _t("tpl-06", _I, "env", "db_count", "private_db", "single", "literal", "none", "all", 3, "t3.medium", "db.t3.small"),
    _t("tpl-07", _AIDS, "kebab", "one_app", "private_db", "single", "literal", "second_app_sg", "all", 2, "t3.micro", "db.t3.micro"),
    _t("tpl-08", _ASDI, "standard", "one_app", "shared_public", "split", "literal", "none", "all", 3, "t3.nano", "db.t3.micro"),
    _t("tpl-09", _S, "tier", "db_count", "private_db", "single", "literal", "none", "all", 2, "t3.small", "db.t3.small"),
    _t("tpl-10", _I, "component", "one_app", "shared_public", "single", "locals", "second_app_sg", "all", 2, "t3.micro", "db.t3.nano"),
    # The 23 D4c-01 templates.
    _t("tpl-11", _S, "prefixed", "two_app", "per_subnet", "single", "variables", "none", "all", 2, "t3.micro", "db.t3.micro"),
    _t("tpl-12", _I, "short", "one_app", "private_db", "split", "locals", "unattached_sg", "all", 3, "t3.small", "db.t3.small"),
    _t("tpl-13", _AIDS, "role", "two_app", "shared_public", "single", "literal", "extra_subnet", "db_only", 2, "t3.nano", "db.t3.micro"),
    _t("tpl-14", _ASDI, "prefixed", "db_count", "per_subnet", "split", "literal", "none", "db_only", 2, "t3.medium", "db.t3.small"),
    _t("tpl-15", _S, "short", "db_count", "private_db", "single", "locals", "extra_subnet", "db_only", 3, "t3.micro", "db.t3.micro"),
    _t("tpl-16", _I, "role", "db_count", "per_subnet", "single", "variables", "second_app_sg", "all", 2, "t3.small", "db.t3.micro"),
    _t("tpl-17", _AIDS, "standard", "one_app", "per_subnet", "split", "variables", "unattached_sg", "all", 3, "t3.micro", "db.t3.small"),
    _t("tpl-18", _ASDI, "kebab", "two_app", "private_db", "single", "locals", "none", "all", 2, "t3.nano", "db.t3.micro"),
    _t("tpl-19", _S, "tier", "two_app", "shared_public", "split", "literal", "unattached_sg", "db_only", 3, "t3.small", "db.t3.medium"),
    _t("tpl-20", _I, "prefixed", "two_app", "shared_public", "single", "literal", "extra_subnet", "all", 2, "t3.micro", "db.t3.micro"),
    _t("tpl-21", _AIDS, "component", "db_count", "private_db", "single", "variables", "none", "db_only", 3, "t3.medium", "db.t3.micro"),
    _t("tpl-22", _ASDI, "env", "one_app", "shared_public", "single", "variables", "extra_subnet", "all", 2, "t3.small", "db.t3.small"),
    _t("tpl-23", _S, "kebab", "db_count", "per_subnet", "single", "literal", "extra_subnet", "all", 2, "t3.nano", "db.t3.micro"),
    _t("tpl-24", _I, "tier", "one_app", "per_subnet", "split", "literal", "none", "all", 3, "t3.micro", "db.t3.small"),
    _t("tpl-25", _AIDS, "short", "two_app", "per_subnet", "single", "literal", "second_app_sg", "all", 2, "t3.small", "db.t3.micro"),
    _t("tpl-26", _ASDI, "role", "one_app", "private_db", "split", "literal", "second_app_sg", "db_only", 3, "t3.micro", "db.t3.micro"),
    _t("tpl-27", _S, "env", "two_app", "private_db", "split", "variables", "none", "all", 2, "t3.medium", "db.t3.small"),
    _t("tpl-28", _I, "standard", "two_app", "private_db", "single", "locals", "unattached_sg", "all", 3, "t3.nano", "db.t3.micro"),
    _t("tpl-29", _AIDS, "prefixed", "one_app", "shared_public", "single", "locals", "none", "all", 2, "t3.small", "db.t3.medium"),
    _t("tpl-30", _ASDI, "short", "db_count", "shared_public", "split", "variables", "unattached_sg", "all", 2, "t3.micro", "db.t3.micro"),
    _t("tpl-31", _S, "role", "one_app", "shared_public", "single", "locals", "unattached_sg", "db_only", 3, "t3.small", "db.t3.small"),
    _t("tpl-32", _I, "kebab", "db_count", "shared_public", "split", "variables", "extra_subnet", "all", 3, "t3.micro", "db.t3.micro"),
    _t("tpl-33", _AIDS, "env", "db_count", "per_subnet", "split", "locals", "extra_subnet", "db_only", 2, "t3.nano", "db.t3.small"),
)}


def axis_distance(a: TemplateDef, b: TemplateDef) -> int:
    """Number of D4c-03 axes on which two templates differ."""
    return sum(getattr(a, ax) != getattr(b, ax) for ax in AXES)


def features_table() -> str:
    """``generator/templates/FEATURES.md`` (generated; ``tools/make_template_features.py`` writes it)."""
    ids = sorted(TEMPLATES)
    dmin = min(axis_distance(TEMPLATES[x], TEMPLATES[y]) for i, x in enumerate(ids) for y in ids[i + 1:])
    head = ["# Controlled template features (generated)", "",
            f"Generated from `generator/templates/__init__.py` ({TEMPLATE_VERSION}) by "
            "`tools/make_template_features.py`; do not edit by hand. The eight columns after the id are the "
            "D4c-03 variation axes (see the module docstring for their values); the last three are further "
            "parameters, not axes.", "",
            f"Templates: {len(ids)}. Minimum pairwise distance over the eight axes: {dmin}.", "",
            "| Template | " + " | ".join(AXES) + " | db subnets | instance | db class |",
            "|---" * (len(AXES) + 4) + "|"]
    rows = [f"| {t} | " + " | ".join(getattr(TEMPLATES[t], ax) for ax in AXES)
            + f" | {TEMPLATES[t].db_subnet_count} | {TEMPLATES[t].instance_class} | {TEMPLATES[t].db_class} |"
            for t in ids]
    return "\n".join(head + rows) + "\n"
