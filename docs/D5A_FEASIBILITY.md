# D5a measurements (computed by `tools/report_d5a.py`)

Every number below is computed from the repository and, for the test split, from the withheld directory (counts only). Regenerate with `python tools/report_d5a.py` (with `TERRAPRESERVE_PRIVATE` set).

## 1. Baseline
| split | tier | scenarios | steps | with a variable without a default | with data sources | with module blocks |
|---|---|---|---|---|---|---|
| dev | controlled | 144 | 328 | 144 | 0 | 0 |
| dev | real_world | 144 | 324 | 144 | 32 | 0 |
| test | controlled | 64 | 138 | 64 | 0 | 0 |
| test | real_world | 64 | 145 | 64 | 17 | 0 |

Data-source types (number of scenarios using each):
- dev: `aws_ami` 5, `aws_availability_zones` 19, `aws_db_instance` 1, `aws_instance` 1, `aws_ip_ranges` 1, `aws_key_pair` 1, `aws_region` 4, `aws_security_group` 1, `aws_subnets` 1, `aws_vpc` 3, `terraform_remote_state` 1
- test: `aws_ami` 1, `aws_availability_zones` 10, `aws_caller_identity` 2, `aws_ec2_transit_gateway` 1, `aws_ec2_transit_gateway_route_table` 1, `aws_ec2_transit_gateway_vpc_attachment` 1, `aws_region` 1, `aws_subnet` 1, `aws_vpc` 6, `aws_vpcs` 1
- validation/smoke: required_version ['~> 1.15.0'], hashicorp/aws version ['6.53.0']; terraform on this machine 1.15.8; provider in the offline mirror: ['6.53.0']

## 2. Variable values (D5-01, rule vv-1)
| split | tier | scenarios | with rule vv-1 | variables valued | variables unresolved | scenarios with an unresolved variable | scenarios where a placeholder reaches a registry-read attribute |
|---|---|---|---|---|---|---|---|
| dev | controlled | 144 | 144 | 144 | 0 | 0 | 0 |
| dev | real_world | 144 | 144 | 483 | 17 | 15 | 84 |
| test | controlled | 64 | 64 | 64 | 0 | 0 | 0 |
| test | real_world | 64 | 64 | 177 | 7 | 6 | 31 |

Unresolved reasons (count of variables):
- dev: 2 x a validation block rejects the vv-1 value ... ...
- dev: 1 x its validation refers to var.vpc_config, which has no vv-1 value, so the vv-1 value cannot be checked
- dev: 12 x object type with required attributes ...: {} does not satisfy it
- dev: 2 x type any is not covered by vv-1
- test: 1 x its validation refers to var.vpc_config, which has no vv-1 value, so the vv-1 value cannot be checked
- test: 6 x object type with required attributes ...: {} does not satisfy it

Dev unresolved variables (17):
- tp-v1-F1-0225: `vpc_config`: object type with required attributes ['cidr_block', 'name']: {} does not satisfy it
- tp-v1-F1-0226: `vpc_config`: object type with required attributes ['cidr_block', 'name']: {} does not satisfy it
- tp-v1-F2-0238: `subnet_config`: its validation refers to var.vpc_config, which has no vv-1 value, so the vv-1 value cannot be checked
- tp-v1-F2-0238: `vpc_config`: object type with required attributes ['cidr_block', 'name']: {} does not satisfy it
- tp-v1-F2-0245: `vpc_config`: object type with required attributes ['cidr_block', 'name']: {} does not satisfy it
- tp-v1-F2-0258: `vpc_config`: object type with required attributes ['cidr_block', 'name']: {} does not satisfy it
- tp-v1-F2-0259: `vpc_config`: object type with required attributes ['cidr_block', 'name']: {} does not satisfy it
- tp-v1-F3-0265: `aws_region`: a validation block rejects the vv-1 value "tp-placeholder" (Error: Invalid value for variable)
- tp-v1-F3-0271: `vpc`: object type with required attributes ['id']: {} does not satisfy it
- tp-v1-F3-0279: `vpc_config`: object type with required attributes ['cidr_block', 'name']: {} does not satisfy it
- tp-v1-F4-0297: `aws_config`: object type with required attributes ['Name', 'cidr_block']: {} does not satisfy it
- tp-v1-F5-0316: `vpc_config`: object type with required attributes ['Name', 'cidr_block']: {} does not satisfy it
- tp-v1-F6-0358: `vpc_config`: object type with required attributes ['cidr_block', 'name', 'region']: {} does not satisfy it
- tp-v1-F8-0397: `vpc_config`: object type with required attributes ['cidr_block', 'name']: {} does not satisfy it
- tp-v1-F8-0405: `env`: a validation block rejects the vv-1 value "tp-placeholder" (Error: Invalid value for variable)
- tp-v1-F8-0406: `project`: type any is not covered by vv-1
- tp-v1-F8-0406: `subnets`: type any is not covered by vv-1

Relevance report: registry-read attributes are security-group and security-group-rule fields (any), `vpc_security_group_ids`, `subnet_id`, `security_group_id`, `publicly_accessible`, `port`, `engine`, `vpc_id`, `cidr_block`, and `count`/`for_each` of any resource holding them (direct or through locals).
Dev scenarios where a placeholder reaches one (84):
- tp-v1-F1-0212: 3 reach(es); variables cidr_block, vpc_id; e.g. `cidr_block` -> `aws_subnet.subnet.cidr_block`
- tp-v1-F1-0214: 6 reach(es); variables engine, vpc_id; e.g. `engine` -> `aws_db_instance.rds.engine`
- tp-v1-F1-0215: 6 reach(es); variables backend_instance_count, frontend_instance_count, private_subnet_ids, public_subnet_ids, vpc_id; e.g. `backend_instance_count` -> `aws_instance.backend.count`
- tp-v1-F1-0219: 7 reach(es); variables cidr_block, subnet_count, vpc_id; e.g. `cidr_block` -> `aws_subnet.subnets.cidr_block`
- tp-v1-F1-0220: 9 reach(es); variables game_server_port, proxy_server_port, vpc_id; e.g. `game_server_port` -> `aws_security_group.sg_alb.egress.from_port`
- tp-v1-F1-0222: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.main.vpc_id`
- tp-v1-F1-0223: 2 reach(es); variables cidr_block; e.g. `cidr_block` -> `aws_subnet.eks_subnet_public_1a.cidr_block`
- tp-v1-F1-0225: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.main.count`
- tp-v1-F1-0226: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.igw.count`
- tp-v1-F1-0233: 2 reach(es); variables subnet_config, vpc_id; e.g. `subnet_config` -> `aws_subnet.main.for_each`
- tp-v1-F2-0236: 2 reach(es); variables subnet_cidr_block, vpc_id; e.g. `subnet_cidr_block` -> `aws_subnet.this.cidr_block`
- tp-v1-F2-0239: 6 reach(es); variables vpc_id, web_port; e.g. `vpc_id` -> `aws_security_group.lb_sg.vpc_id`
- tp-v1-F2-0241: 5 reach(es); variables private_subnet_cidrs, public_subnet_cidrs, vpc_cidr; e.g. `private_subnet_cidrs` -> `aws_subnet.private.cidr_block`
- tp-v1-F2-0245: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.this.count`
- tp-v1-F2-0251: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.alb_sg.vpc_id`
- tp-v1-F2-0254: 7 reach(es); variables private_cidr_block, public_cidr_block, vpc_cidr; e.g. `private_cidr_block` -> `aws_route_table_association.private-subnets.count`
- tp-v1-F2-0258: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.this.count`
- tp-v1-F2-0259: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.this.count`
- tp-v1-F3-0261: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.lambda_sg.vpc_id`
- tp-v1-F3-0262: 2 reach(es); variables subnet_cidr_block, vpc_id; e.g. `subnet_cidr_block` -> `aws_subnet.subnet.cidr_block`
- tp-v1-F3-0263: 6 reach(es); variables private_subnet_cidr, vpc_cidr, vpc_id; e.g. `private_subnet_cidr` -> `aws_security_group.ssm_sg.egress.cidr_blocks`
- tp-v1-F3-0264: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_subnet.main.vpc_id`
- tp-v1-F3-0265: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.sig_sg.vpc_id`
- tp-v1-F3-0271: 1 reach(es); variables cidr_blocks; e.g. `cidr_blocks` -> `aws_subnet.this.for_each`
- tp-v1-F3-0272: 2 reach(es); variables subnet_cidr, target_vpc; e.g. `subnet_cidr` -> `aws_subnet.test-subnet.cidr_block`
- tp-v1-F3-0276: 6 reach(es); variables private_cidr_blocks, private_subnet_count, public_cidr_blocks, public_subnet_count, vpc_id; e.g. `private_cidr_blocks` -> `aws_subnet.private.cidr_block`
- tp-v1-F3-0277: 1 reach(es); variables vpc_cidr; e.g. `vpc_cidr` -> `aws_vpc.vpc.cidr_block`
- tp-v1-F3-0278: 16 reach(es); variables client_vpn_cidr, ec2_app_port, ec2_app_port_health, isolated_subnet_cidrs, private_subnet_cidrs, public_subnet_cidrs, vpc_id; e.g. `client_vpn_cidr` -> `aws_security_group.vpn_endpoint_sg.ingress.cidr_blocks`
- tp-v1-F3-0279: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.main.count`
- tp-v1-F3-0284: 5 reach(es); variables admin_sg, azs, bat_count, vpc_id, web_sg; e.g. `admin_sg` -> `aws_security_group.bat.ingress.security_groups`
- tp-v1-F3-0285: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.this.vpc_id`
- tp-v1-F4-0287: 3 reach(es); variables vpc_cidr, vpc_public_subnet_cidr_1, vpc_public_subnet_cidr_2; e.g. `vpc_cidr` -> `aws_vpc.main_vpc.cidr_block`
- tp-v1-F4-0289: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.this.vpc_id`
- tp-v1-F4-0290: 5 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.trident_app_alb_sg.vpc_id`
- tp-v1-F4-0291: 6 reach(es); variables azs, private_cidrs, public_cidrs, vpc_id; e.g. `azs` -> `aws_subnet.private.count`
- tp-v1-F4-0292: 2 reach(es); variables public_subnet_1_cidr, vpc_cidr; e.g. `public_subnet_1_cidr` -> `aws_subnet.public_1.cidr_block`
- tp-v1-F4-0297: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.main.count`
- tp-v1-F4-0298: 6 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_route_table.manage.vpc_id`
- tp-v1-F4-0300: 3 reach(es); variables vpc_cidr; e.g. `vpc_cidr` -> `aws_subnet.private.cidr_block`
- tp-v1-F4-0303: 2 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.alb.vpc_id`
- tp-v1-F4-0306: 2 reach(es); variables ec2_security_group_id, vpc_id; e.g. `ec2_security_group_id` -> `aws_security_group.rds_sg.ingress.security_groups`
- tp-v1-F4-0310: 1 reach(es); variables cidr_block; e.g. `cidr_block` -> `aws_vpc.this.cidr_block`
- tp-v1-F5-0314: 2 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.locust_master.vpc_id`
- tp-v1-F5-0316: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.igw.count`
- tp-v1-F5-0317: 5 reach(es); variables cidr_block; e.g. `cidr_block` -> `aws_subnet.eks_subnet_private_1a.cidr_block`
- tp-v1-F5-0318: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.main.vpc_id`
- tp-v1-F5-0319: 6 reach(es); variables cidrs, vpc_id; e.g. `cidrs` -> `aws_route_table.subnet.count`
- tp-v1-F5-0323: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.rds.vpc_id`
- tp-v1-F5-0324: 3 reach(es); variables vpc_cidr, vpc_id; e.g. `vpc_cidr` -> `aws_security_group.eks_additional.ingress.cidr_blocks`
- tp-v1-F5-0326: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.this.vpc_id`
- tp-v1-F5-0328: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.sg.vpc_id`
- tp-v1-F5-0330: 3 reach(es); variables cidr_block, subnets; e.g. `cidr_block` -> `aws_subnet.main.for_each`
- tp-v1-F5-0331: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.this.vpc_id`
- tp-v1-F5-0332: 4 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.alb.vpc_id`
- tp-v1-F5-0337: 2 reach(es); variables container_port, vpc_id; e.g. `container_port` -> `aws_security_group.ecs_tasks.ingress.to_port`
- tp-v1-F6-0339: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.rds.vpc_id`
- tp-v1-F6-0340: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.this.vpc_id`
- tp-v1-F6-0344: 2 reach(es); variables sg_cidr, sg_vpc_id; e.g. `sg_cidr` -> `aws_security_group.aws_sg.ingress.cidr_blocks`
- tp-v1-F6-0345: 6 reach(es); variables private_subnet_cidr_block, public_subnet_cidr_block, vpc_Id; e.g. `private_subnet_cidr_block` -> `aws_subnet.dev-private-subnet.cidr_block`
- tp-v1-F6-0350: 1 reach(es); variables aws_vpc_id; e.g. `aws_vpc_id` -> `aws_security_group.sg.vpc_id`
- tp-v1-F6-0352: 4 reach(es); variables backend_security_group_id, vpc_id; e.g. `backend_security_group_id` -> `aws_security_group.rds.ingress.security_groups`
- tp-v1-F6-0353: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.rds.vpc_id`
- tp-v1-F6-0354: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.ecs_tasks.vpc_id`
- tp-v1-F6-0356: 4 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.alb.vpc_id`
- tp-v1-F6-0358: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.test-igw.count`
- tp-v1-F6-0363: 2 reach(es); variables app_sg_id, vpc_id; e.g. `app_sg_id` -> `aws_security_group.rds.ingress.security_groups`
- tp-v1-F7-0369: 3 reach(es); variables cidr_blocks, private_subnet_cidr_blocks; e.g. `cidr_blocks` -> `aws_vpc.vpc.cidr_block`
- tp-v1-F7-0371: 3 reach(es); variables private_subnet_cidr, public_subnet_cidr, vpc_cidr; e.g. `private_subnet_cidr` -> `aws_subnet.private_subnet.cidr_block`
- tp-v1-F7-0375: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.rds_sg.vpc_id`
- tp-v1-F7-0378: 3 reach(es); variables bastion_sg_id, subnet_id, vpc_id; e.g. `bastion_sg_id` -> `aws_security_group_rule.worker_ssh_ingress.source_security_group_id`
- tp-v1-F7-0381: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.sg.vpc_id`
- tp-v1-F7-0388: 3 reach(es); variables controller_sg_id, subnet_id, vpc_id; e.g. `controller_sg_id` -> `aws_security_group.k8s_master_sg.ingress.security_groups`
- tp-v1-F8-0391: 3 reach(es); variables cidr_block, subnet_az_a, subnet_az_b; e.g. `cidr_block` -> `aws_vpc.vpc.cidr_block`
- tp-v1-F8-0392: 6 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_route_table.private1.vpc_id`
- tp-v1-F8-0393: 5 reach(es); variables cidr_private_subnet, cidr_public_subnet, vpc_cidr; e.g. `cidr_private_subnet` -> `aws_subnet.dev_proj_1_private_subnets.cidr_block`
- tp-v1-F8-0394: 6 reach(es); variables kaira_vpc_id, kaira_vpc_ip_block; e.g. `kaira_vpc_id` -> `aws_subnet.kaira_subnet_public_a.vpc_id`
- tp-v1-F8-0395: 6 reach(es); variables one_fireedge_port, one_sunstone_port, subnet_id, vpc_id; e.g. `one_fireedge_port` -> `aws_security_group.allow_web.ingress.from_port`
- tp-v1-F8-0396: 5 reach(es); variables cidr_block, private_cidr_block, public_cidr_block; e.g. `cidr_block` -> `aws_vpc.custom.cidr_block`
- tp-v1-F8-0397: 4 reach(es); variables subnet_config; e.g. `subnet_config` -> `aws_internet_gateway.this.count`
- tp-v1-F8-0401: 6 reach(es); variables cidrs, vpc_id; e.g. `cidrs` -> `aws_route_table.private.count`
- tp-v1-F8-0402: 2 reach(es); variables vpc_1_vpc_id, vpc_2_vpc_id; e.g. `vpc_1_vpc_id` -> `aws_security_group.vpc_1_sg.vpc_id`
- tp-v1-F8-0404: 1 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_subnet.this.vpc_id`
- tp-v1-F8-0408: 6 reach(es); variables cidr_block, private_subnet_cidrs, public_subnet_cidrs; e.g. `cidr_block` -> `aws_vpc.main.cidr_block`
- tp-v1-F8-0414: 3 reach(es); variables vpc_id; e.g. `vpc_id` -> `aws_security_group.alb.vpc_id`

## 3. Input-path feasibility (Step 4)
| split | tier | steps | plan JSON produced | failed | failed: data source needs API | failed: provider tried to call AWS | failed: variable error | failed: other | median wall s | max wall s | Checkov ran | Checkov median s | Checkov max s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | controlled | 328 | 328 | 0 | 0 | 0 | 0 | 0 | 22.1 | 45.3 | 328 | 15.4 | 24.3 |
| dev | real_world | 324 | 170 | 154 | 50 | 0 | 104 | 0 | 15.0 | 31.0 | 324 | 15.3 | 23.6 |
| test | controlled | 138 | 138 | 0 | 0 | 0 | 0 | 0 | 11.6 | 16.6 | 138 | 8.3 | 9.7 |
| test | real_world | 145 | 74 | 71 | 36 | 0 | 35 | 0 | 9.8 | 13.5 | 145 | 8.1 | 11.2 |

Wall time is init + plan + show for one step, measured with 8 steps running in parallel on one machine; init reuses the provider already installed for its worker (a seeded lock file), so it does not copy the provider binary each time. Checkov time is separate.

Measured twice: 13 dev steps and 2 test steps. Measured a second time with 4 workers on 2026-11-09. First pass: 8 dev steps (tp-v1-F5-0120, -0123, -0125, -0126) stalled together for about 2420 s (an environmental stall during the run: wall or Checkov time of 2407 to 2424 s at the same moment, 2 of them reported as a show-stage timeout); 5 dev and 2 test steps had Checkov exit with UnicodeDecodeError ('charmap' codec, Windows cp1252 locale reading UTF-8 files), fixed by running Checkov with PYTHONUTF8=1. The rows in the CSVs are the second measurement.

Failures by stage and class: dev/plan/data source needs API: 50, dev/plan/variable error: 104, test/plan/data source needs API: 36, test/plan/variable error: 35

Failures by class and cause (steps):
- dev: data source needs API; aws_ami: AWS request refused: 8
- dev: data source needs API; aws_availability_zones: AWS request refused: 30
- dev: data source needs API; aws_db_instance: AWS request refused: 2
- dev: data source needs API; aws_instance: AWS request refused: 2
- dev: data source needs API; aws_ip_ranges: AWS request refused: 2
- dev: data source needs API; aws_key_pair: AWS request refused: 2
- dev: data source needs API; aws_vpc: AWS request refused: 2
- dev: data source needs API; terraform_remote_state: AWS credential lookup failed (no credential is available): 2
- dev: variable error; a declared default (not set by vv-1) rejected in an expression or by the provider: 6
- dev: variable error; unresolved variable has no value: 35
- dev: variable error; vv-1 value rejected in an expression or by the provider: 63
- test: data source needs API; aws_ami: AWS request refused: 2
- test: data source needs API; aws_availability_zones: AWS request refused: 19
- test: data source needs API; aws_caller_identity: AWS request refused: 2
- test: data source needs API; aws_vpc: AWS request refused: 13
- test: variable error; a declared default (not set by vv-1) rejected in an expression or by the provider: 8
- test: variable error; unresolved variable has no value: 14
- test: variable error; vv-1 value rejected in an expression or by the provider: 13

Failed steps in scenarios that do / do not use `data` sources:
- dev: without data sources, planned: 498
- dev: without data sources, failed: 81
- dev: with data sources, failed: 73
- test: without data sources, planned: 212
- test: without data sources, failed: 31
- test: with data sources, failed: 40

Dev scenarios with at least one failed step (70): tp-v1-F1-0210, tp-v1-F1-0212, tp-v1-F1-0213, tp-v1-F1-0214, tp-v1-F1-0215, tp-v1-F1-0219, tp-v1-F1-0220, tp-v1-F1-0223, tp-v1-F1-0225, tp-v1-F1-0226, tp-v1-F1-0227, tp-v1-F1-0228, tp-v1-F2-0236, tp-v1-F2-0238, tp-v1-F2-0240, tp-v1-F2-0241, tp-v1-F2-0245, tp-v1-F2-0252, tp-v1-F2-0254, tp-v1-F2-0258, tp-v1-F2-0259, tp-v1-F3-0262, tp-v1-F3-0263, tp-v1-F3-0265, tp-v1-F3-0266, tp-v1-F3-0271, tp-v1-F3-0272, tp-v1-F3-0275, tp-v1-F3-0276, tp-v1-F3-0277, tp-v1-F3-0278, tp-v1-F3-0279, tp-v1-F3-0284, tp-v1-F4-0287, tp-v1-F4-0292, tp-v1-F4-0297, tp-v1-F4-0300, tp-v1-F4-0304, tp-v1-F4-0305, tp-v1-F4-0310, tp-v1-F5-0316, tp-v1-F5-0317, tp-v1-F5-0324, tp-v1-F5-0327, tp-v1-F5-0330, tp-v1-F5-0337, tp-v1-F6-0342, tp-v1-F6-0344, tp-v1-F6-0345, tp-v1-F6-0349, tp-v1-F6-0357, tp-v1-F6-0358, tp-v1-F6-0362, tp-v1-F7-0367, tp-v1-F7-0369, tp-v1-F7-0371, tp-v1-F7-0378, tp-v1-F7-0379, tp-v1-F7-0382, tp-v1-F7-0384, tp-v1-F7-0388, tp-v1-F8-0391, tp-v1-F8-0393, tp-v1-F8-0394, tp-v1-F8-0396, tp-v1-F8-0397, tp-v1-F8-0405, tp-v1-F8-0406, tp-v1-F8-0408, tp-v1-F8-0409

Dev failures (154 steps):
- tp-v1-F1-0210/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F1-0210/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F1-0212/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F1-0212/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F1-0213/step_0 (plan, data source needs API; aws_ip_ranges: AWS request refused): Error: downloading IP ranges
- tp-v1-F1-0213/step_1 (plan, data source needs API; aws_ip_ranges: AWS request refused): Error: downloading IP ranges
- tp-v1-F1-0214/step_0 (plan, data source needs API; aws_db_instance: AWS request refused): Error: reading RDS DB Instance: operation error RDS: DescribeDBInstances, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://rds.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could 
- tp-v1-F1-0214/step_1 (plan, data source needs API; aws_db_instance: AWS request refused): Error: reading RDS DB Instance: operation error RDS: DescribeDBInstances, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://rds.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could 
- tp-v1-F1-0215/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F1-0215/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F1-0219/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Incorrect value type
- tp-v1-F1-0219/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Incorrect value type
- tp-v1-F1-0220/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Incorrect attribute value type
- tp-v1-F1-0220/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Incorrect attribute value type
- tp-v1-F1-0223/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F1-0223/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F1-0225/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F1-0225/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F1-0226/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F1-0226/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F1-0227/step_0 (plan, data source needs API; aws_ami: AWS request refused): Error: reading EC2 AMIs: operation error EC2: DescribeImages, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made beca
- tp-v1-F1-0227/step_1 (plan, data source needs API; aws_ami: AWS request refused): Error: reading EC2 AMIs: operation error EC2: DescribeImages, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made beca
- tp-v1-F1-0228/step_0 (plan, variable error; a declared default (not set by vv-1) rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:
- tp-v1-F1-0228/step_1 (plan, variable error; a declared default (not set by vv-1) rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:
- tp-v1-F2-0236/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F2-0236/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F2-0238/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F2-0238/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F2-0240/step_0 (plan, data source needs API; aws_ami: AWS request refused): Error: reading EC2 AMIs: operation error EC2: DescribeImages, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made beca
- tp-v1-F2-0240/step_1 (plan, data source needs API; aws_ami: AWS request refused): Error: reading EC2 AMIs: operation error EC2: DescribeImages, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made beca
- tp-v1-F2-0241/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F2-0241/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F2-0245/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F2-0245/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F2-0252/step_0 (plan, variable error; a declared default (not set by vv-1) rejected in an expression or by the provider): Error: "This variable must be defined at environment level." is not a valid CIDR block: invalid CIDR address: This variable must be defined at environment level.
- tp-v1-F2-0252/step_1 (plan, variable error; a declared default (not set by vv-1) rejected in an expression or by the provider): Error: "This variable must be defined at environment level." is not a valid CIDR block: invalid CIDR address: This variable must be defined at environment level.
- tp-v1-F2-0254/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F2-0254/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F2-0258/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F2-0258/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F2-0259/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F2-0259/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F3-0262/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F3-0262/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F3-0263/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F3-0263/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F3-0265/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F3-0265/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F3-0266/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F3-0266/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F3-0271/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F3-0271/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F3-0272/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F3-0272/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F3-0275/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F3-0275/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F3-0276/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F3-0276/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F3-0277/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F3-0277/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F3-0278/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F3-0278/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F3-0279/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F3-0279/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F3-0284/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Invalid index
- tp-v1-F3-0284/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Invalid index
- tp-v1-F4-0287/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F4-0287/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F4-0292/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F4-0292/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F4-0297/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F4-0297/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F4-0300/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F4-0300/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F4-0304/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F4-0304/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F4-0305/step_0 (plan, data source needs API; aws_ami: AWS request refused): Error: reading EC2 AMIs: operation error EC2: DescribeImages, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made beca
- tp-v1-F4-0305/step_1 (plan, data source needs API; aws_ami: AWS request refused): Error: reading EC2 AMIs: operation error EC2: DescribeImages, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made beca
- tp-v1-F4-0310/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F4-0310/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F5-0316/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F5-0316/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F5-0317/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F5-0317/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F5-0324/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F5-0324/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F5-0327/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F5-0327/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F5-0330/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Invalid function argument
- tp-v1-F5-0330/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Invalid function argument
- tp-v1-F5-0337/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Incorrect attribute value type
- tp-v1-F5-0337/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Incorrect attribute value type
- tp-v1-F6-0342/step_0 (plan, data source needs API; terraform_remote_state: AWS credential lookup failed (no credential is available)): Error: No valid credential sources found
- tp-v1-F6-0342/step_1 (plan, data source needs API; terraform_remote_state: AWS credential lookup failed (no credential is available)): Error: No valid credential sources found
- tp-v1-F6-0344/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Incorrect attribute value type
- tp-v1-F6-0344/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Incorrect attribute value type
- tp-v1-F6-0345/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F6-0345/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: "tp-placeholder" is not a valid CIDR block: invalid CIDR address: tp-placeholder
- tp-v1-F6-0349/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F6-0349/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F6-0357/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F6-0357/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F6-0358/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F6-0358/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F6-0362/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F6-0362/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F7-0367/step_0 (plan, data source needs API; aws_instance: AWS request refused): Error: reading EC2 Instance: operation error EC2: DescribeInstances, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be ma
- tp-v1-F7-0367/step_1 (plan, data source needs API; aws_instance: AWS request refused): Error: reading EC2 Instance: operation error EC2: DescribeInstances, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be ma
- tp-v1-F7-0369/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F7-0369/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F7-0371/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F7-0371/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F7-0378/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Invalid function argument
- tp-v1-F7-0378/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Invalid function argument
- tp-v1-F7-0379/step_0 (plan, data source needs API; aws_vpc: AWS request refused): Error: reading EC2 VPC: operation error EC2: DescribeVpcs, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made because
- tp-v1-F7-0379/step_1 (plan, data source needs API; aws_vpc: AWS request refused): Error: reading EC2 VPC: operation error EC2: DescribeVpcs, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made because
- tp-v1-F7-0382/step_0 (plan, variable error; a declared default (not set by vv-1) rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:
- tp-v1-F7-0382/step_1 (plan, variable error; a declared default (not set by vv-1) rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:
- tp-v1-F7-0384/step_0 (plan, data source needs API; aws_ami: AWS request refused): Error: reading EC2 AMIs: operation error EC2: DescribeImages, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made beca
- tp-v1-F7-0384/step_1 (plan, data source needs API; aws_ami: AWS request refused): Error: reading EC2 AMIs: operation error EC2: DescribeImages, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made beca
- tp-v1-F7-0388/step_0 (plan, data source needs API; aws_key_pair: AWS request refused): Error: reading EC2 Key Pair: operation error EC2: DescribeKeyPairs, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be mad
- tp-v1-F7-0388/step_1 (plan, data source needs API; aws_key_pair: AWS request refused): Error: reading EC2 Key Pair: operation error EC2: DescribeKeyPairs, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be mad
- tp-v1-F8-0391/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F8-0391/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F8-0391/step_2 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F8-0391/step_3 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F8-0393/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F8-0393/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F8-0393/step_2 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: expected cidr_block to contain a valid Value, got: tp-placeholder with err: invalid CIDR address: tp-placeholder
- tp-v1-F8-0394/step_0 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F8-0394/step_1 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F8-0394/step_2 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F8-0394/step_3 (plan, variable error; vv-1 value rejected in an expression or by the provider): Error: Error in function call
- tp-v1-F8-0396/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0396/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0396/step_2 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0397/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0397/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0397/step_2 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0397/step_3 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0405/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0405/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0405/step_2 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0406/step_0 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0406/step_1 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0406/step_2 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0406/step_3 (plan, variable error; unresolved variable has no value): Error: No value for required variable
- tp-v1-F8-0408/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0408/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0408/step_2 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0409/step_0 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0409/step_1 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0409/step_2 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect
- tp-v1-F8-0409/step_3 (plan, data source needs API; aws_availability_zones: AWS request refused): Error: fetching Availability Zones: operation error EC2: DescribeAvailabilityZones, exceeded maximum number of attempts, 1, https response error StatusCode: 0, RequestID: , request send failed, Post "https://ec2.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connect

## 4. Possible routes for the failing steps (listed, not chosen; Open D5-A and D5-B)
- Route 1, HCL instead of plan JSON for every step: the oracle parses the configuration itself (like DAIL), so all steps are readable offline; it gives up the different input path that ADR-010 independence leans on.
- Route 2, plan JSON where it plans, HCL elsewhere: two input paths inside one oracle; labels would depend on which path a step took, and both paths need their own tests.
- Route 3, oracle-only data-source substitution: replace each `data` block in the working copy by a fixed local value; the planned configuration is no longer the scenario's text, and the substituted values become a new recorded rule like vv-1.
- Route 4, a revised value rule (vv-2) with typed placeholders (a valid CIDR, a well-formed id): would remove most variable errors; it changes `scenario.json` again and is the substance of Open D5-B.
- Route 5, plan with a mock provider (`terraform test` `mock_provider`, Terraform 1.7 or later): data sources return generated values offline; computed values are synthetic, so a label could rest on invented attributes.
- Route 6, a local AWS emulator such as LocalStack: excluded by the work package (no emulator); listed only for completeness.
- Route 7, mark failing steps UNKNOWN or UNSUPPORTED under the registry's indeterminacy rules and keep plan JSON only: no new machinery; D0 gate 4 (every step labelled) still holds, but many real-world steps carry no PASS or FAIL.
- Route 8, drop or replace the scenarios that cannot be planned: reduces the real-world tier; D0 Decision 3 says yields are reported, never padded.

## 5. Decision rows (docs/D5_DECISIONS.md, id and Status as written)
- D5-01: Proposed
- D5-02: Proposed
- D5-03: Proposed
- D5-04: Proposed
- Open D5-A: Open
- Open D5-B: Open

<!-- D5a-2 results below: written by tools/report_d5a2.py; the D5a part above is kept as it was -->

## D5a-2 measurements (computed by `tools/report_d5a2.py`)

Value rule vv-2 (D5-07), data-source variables (D5-08), both value sets (D5-06). Every number below is computed from the repository and, for the test split, from the withheld directory (counts only). Regenerate with `python tools/report_d5a2.py` (with `TERRAPRESERVE_PRIVATE` set). The D5a part above describes vv-1 at `e96c017` and is kept as it was.

### D5a-2.1 Decision rows (as written in `docs/D5_DECISIONS.md`)
- D5-01: Superseded
- D5-02: Proposed
- D5-03: Proposed
- D5-04: Proposed
- D5-05: Decided
- D5-06: Decided
- D5-07: Proposed
- D5-08: Proposed
- Open D5-A: Decided
- Open D5-B: Decided
- Open D5-C: Open

### D5a-2.2 Variable values, rule vv-2 (D5-07)
| split | tier | scenarios | with rule vv-2 | variables valued (both sets) | of which tp_ds_* | unresolved | conflict |
|---|---|---|---|---|---|---|---|
| dev | controlled | 144 | 144 | 144 | 0 | 0 | 0 |
| dev | real_world | 144 | 144 | 536 | 38 | 1 | 2 |
| test | controlled | 64 | 64 | 64 | 0 | 0 | 0 |
| test | real_world | 64 | 64 | 208 | 25 | 1 | 0 |

Leaves by kind (a leaf is one scalar position of a value; per split and tier):
- dev controlled: `secret` 144
- dev real_world: `ami` 11, `az` 52, `bool` 3, `instance_type` 4, `ipv4_cidr` 81, `key_name` 3, `number` 15, `region` 6, `secret` 153, `sg_id` 8, `string` 157, `subnet_id` 14, `vpc_id` 61
- test controlled: `secret` 64
- test real_world: `ami` 1, `az` 18, `bool` 1, `ipv4_cidr` 29, `number` 6, `region` 3, `secret` 71, `sg_id` 4, `string` 57, `subnet_id` 7, `vpc_id` 24

Variables by evidence class (a variable counts once per class it records):
- dev controlled: `declared_type` 144, `secret` 144, `validation` 144
- dev real_world: `data_source` 32, `declared_type` 452, `no table attribute reached` 153, `secret` 153, `untyped` 84, `usage` 191, `validation` 22
- test controlled: `declared_type` 64, `secret` 64, `validation` 64
- test real_world: `data_source` 19, `declared_type` 198, `no table attribute reached` 56, `secret` 71, `untyped` 10, `usage` 58, `validation` 8

Validation candidates taken (variables with a validation block):
- dev controlled: 144 x the kind's value in both sets (first candidate)
- dev real_world: 1 x a later candidate: primary 'tst', alternate 'dev'
- dev real_world: 1 x a later candidate: primary 'us-gov-east-1', alternate 'us-gov-west-1'
- dev real_world: 20 x the kind's value in both sets (first candidate)
- test controlled: 64 x the kind's value in both sets (first candidate)
- test real_world: 8 x the kind's value in both sets (first candidate)

Values equal in both sets (recorded exceptions):
- dev real_world: 2 x kind region: the provider pin us-east-1 in both sets
- dev real_world: 2 x object with no attributes used

Unresolved and conflict reasons (count of variables):
- dev: 1 x conflict: conflict at []: az by usage:...; ipv4_cidr by usage:...
- dev: 1 x conflict: conflict at []: ipv4_cidr by usage:...; ipv6_cidr by usage:...
- dev: 1 x unresolved: map at (value) is indexed by a computed key
- test: 1 x unresolved: map at (value) is indexed by a computed key

Dev variables without a value:
- tp-v1-F3-0271 `cidr_blocks` (conflict: conflict at []: ipv4_cidr by usage:aws_subnet.this.cidr_block; ipv6_cidr by usage:aws_subnet.this.ipv6_cidr_block)
- tp-v1-F7-0369 `private_subnet_cidr_blocks` (conflict: conflict at []: az by usage:aws_subnet.private_subnets.availability_zone; ipv4_cidr by usage:aws_subnet.private_subnets.cidr_block)
- tp-v1-F8-0406 `tp_ds_aws_vpc_net` (unresolved: map at (value) is indexed by a computed key)

### D5a-2.3 Data-source transform (D5-08)
- dev: blocks removed by type: `aws_ami` 5, `aws_availability_zones` 19, `aws_db_instance` 1, `aws_instance` 2, `aws_ip_ranges` 1, `aws_key_pair` 1, `aws_region` 4, `aws_security_group` 1, `aws_subnets` 1, `aws_vpc` 3, `terraform_remote_state` 1; variables created: 39; scenarios affected: 32
- test: blocks removed by type: `aws_ami` 1, `aws_availability_zones` 10, `aws_caller_identity` 2, `aws_ec2_transit_gateway` 1, `aws_ec2_transit_gateway_route_table` 1, `aws_ec2_transit_gateway_vpc_attachment` 1, `aws_region` 1, `aws_subnet` 1, `aws_vpc` 6, `aws_vpcs` 1; variables created: 25; scenarios affected: 17
- dev scenarios affected: tp-v1-F1-0210, tp-v1-F1-0213, tp-v1-F1-0214, tp-v1-F1-0223, tp-v1-F1-0227, tp-v1-F1-0228, tp-v1-F2-0240, tp-v1-F2-0245, tp-v1-F2-0258, tp-v1-F2-0259, tp-v1-F3-0266, tp-v1-F3-0275, tp-v1-F3-0277, tp-v1-F4-0300, tp-v1-F4-0304, tp-v1-F4-0305, tp-v1-F5-0317, tp-v1-F5-0327, tp-v1-F6-0342, tp-v1-F6-0349, tp-v1-F6-0357, tp-v1-F6-0362, tp-v1-F7-0367, tp-v1-F7-0379, tp-v1-F7-0384, tp-v1-F7-0388, tp-v1-F8-0396, tp-v1-F8-0397, tp-v1-F8-0405, tp-v1-F8-0406, tp-v1-F8-0408, tp-v1-F8-0409

### D5a-2.4 Whole-module S0 screen, re-run after the transform
- dev host: result after the transform: accepted 144; same result as before the transform: 144, changed: 0
- test host: result after the transform: accepted 64; same result as before the transform: 64, changed: 0
- natives are rejected by design (RW-S0-FUNC, D4b-15); they are not re-selected either.
- stop list (hosts that fail the screen after the transform): 0

### D5a-2.5 Feasibility under each value set (D5-04 offline rules unchanged)
#### Value set: primary (`variable_values`)
| split | tier | steps | plan JSON | data source needs API | provider tried to call AWS | variable error | other | median wall s | max wall s |
|---|---|---|---|---|---|---|---|---|---|
| dev | controlled | 328 | 328 | 0 | 0 | 0 | 0 | 20.5 | 37.8 |
| dev | real_world | 324 | 283 | 0 | 0 | 39 | 2 | 19.7 | 33.3 |
| test | controlled | 138 | 138 | 0 | 0 | 0 | 0 | 23.8 | 44.8 |
| test | real_world | 145 | 121 | 0 | 0 | 22 | 2 | 20.1 | 33.5 |

Failures by class and cause:
- dev: 2 x other: (no sub-cause)
- dev: 8 x variable error: a declared default (not set by vv-2) rejected in an expression or by the provider
- dev: 8 x variable error: unresolved variable has no value
- dev: 23 x variable error: vv-2 value rejected in an expression or by the provider
- test: 2 x other: (no sub-cause)
- test: 12 x variable error: a declared default (not set by vv-2) rejected in an expression or by the provider
- test: 2 x variable error: unresolved variable has no value
- test: 8 x variable error: vv-2 value rejected in an expression or by the provider

Dev failures (first error):
- tp-v1-F1-0214 step 0: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: first character of "identifier" must be a letter`
- tp-v1-F1-0214 step 1: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: first character of "identifier" must be a letter`
- tp-v1-F1-0219 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect value type`
- tp-v1-F1-0219 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect value type`
- tp-v1-F1-0220 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F1-0220 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F1-0228 step 0: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:`
- tp-v1-F1-0228 step 1: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:`
- tp-v1-F2-0252 step 0: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: "This variable must be defined at environment level." is not a valid CIDR block: invalid CIDR address: This variable must be defined at environment level`
- tp-v1-F2-0252 step 1: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: "This variable must be defined at environment level." is not a valid CIDR block: invalid CIDR address: This variable must be defined at environment level`
- tp-v1-F2-0254 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F2-0254 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F3-0266 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Resource precondition failed`
- tp-v1-F3-0266 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Resource precondition failed`
- tp-v1-F3-0271 step 0: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F3-0271 step 1: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F3-0284 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F3-0284 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F5-0327 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Invalid index`
- tp-v1-F5-0327 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Invalid index`
- tp-v1-F5-0330 step 0: other; ; `Error: Invalid index`
- tp-v1-F5-0330 step 1: other; ; `Error: Invalid index`
- tp-v1-F5-0337 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F5-0337 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F6-0342 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: "tp-primary/32" is not a valid CIDR block: invalid CIDR address: tp-primary/32`
- tp-v1-F6-0342 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: "tp-primary/32" is not a valid CIDR block: invalid CIDR address: tp-primary/32`
- tp-v1-F6-0344 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F6-0344 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F7-0369 step 0: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F7-0369 step 1: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F7-0378 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Invalid function argument`
- tp-v1-F7-0378 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Invalid function argument`
- tp-v1-F7-0382 step 0: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:`
- tp-v1-F7-0382 step 1: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:`
- tp-v1-F8-0393 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F8-0393 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F8-0393 step 2: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F8-0406 step 0: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F8-0406 step 1: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F8-0406 step 2: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F8-0406 step 3: variable error; unresolved variable has no value; `Error: No value for required variable`

#### Value set: alternate (`variable_values_alt`)
| split | tier | steps | plan JSON | data source needs API | provider tried to call AWS | variable error | other | median wall s | max wall s |
|---|---|---|---|---|---|---|---|---|---|
| dev | controlled | 328 | 328 | 0 | 0 | 0 | 0 | 16.9 | 37.1 |
| dev | real_world | 324 | 283 | 0 | 0 | 39 | 2 | 16.3 | 32.3 |
| test | controlled | 138 | 138 | 0 | 0 | 0 | 0 | 16.8 | 31.5 |
| test | real_world | 145 | 119 | 0 | 0 | 24 | 2 | 16.0 | 30.6 |

Failures by class and cause:
- dev: 2 x other: (no sub-cause)
- dev: 8 x variable error: a declared default (not set by vv-2) rejected in an expression or by the provider
- dev: 8 x variable error: unresolved variable has no value
- dev: 23 x variable error: vv-2 value rejected in an expression or by the provider
- test: 2 x other: (no sub-cause)
- test: 12 x variable error: a declared default (not set by vv-2) rejected in an expression or by the provider
- test: 2 x variable error: unresolved variable has no value
- test: 10 x variable error: vv-2 value rejected in an expression or by the provider

Dev failures (first error):
- tp-v1-F1-0214 step 0: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: first character of "identifier" must be a letter`
- tp-v1-F1-0214 step 1: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: first character of "identifier" must be a letter`
- tp-v1-F1-0219 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect value type`
- tp-v1-F1-0219 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect value type`
- tp-v1-F1-0220 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F1-0220 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F1-0228 step 0: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:`
- tp-v1-F1-0228 step 1: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:`
- tp-v1-F2-0252 step 0: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: "This variable must be defined at environment level." is not a valid CIDR block: invalid CIDR address: This variable must be defined at environment level`
- tp-v1-F2-0252 step 1: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: "This variable must be defined at environment level." is not a valid CIDR block: invalid CIDR address: This variable must be defined at environment level`
- tp-v1-F2-0254 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F2-0254 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F3-0266 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Resource precondition failed`
- tp-v1-F3-0266 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Resource precondition failed`
- tp-v1-F3-0271 step 0: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F3-0271 step 1: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F3-0284 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F3-0284 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F5-0327 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Invalid index`
- tp-v1-F5-0327 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Invalid index`
- tp-v1-F5-0330 step 0: other; ; `Error: Invalid index`
- tp-v1-F5-0330 step 1: other; ; `Error: Invalid index`
- tp-v1-F5-0337 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F5-0337 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F6-0342 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: "tp-alt/32" is not a valid CIDR block: invalid CIDR address: tp-alt/32`
- tp-v1-F6-0342 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: "tp-alt/32" is not a valid CIDR block: invalid CIDR address: tp-alt/32`
- tp-v1-F6-0344 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F6-0344 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Incorrect attribute value type`
- tp-v1-F7-0369 step 0: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F7-0369 step 1: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F7-0378 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Invalid function argument`
- tp-v1-F7-0378 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Invalid function argument`
- tp-v1-F7-0382 step 0: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:`
- tp-v1-F7-0382 step 1: variable error; a declared default (not set by vv-2) rejected in an expression or by the provider; `Error: expected cidr_block to contain a valid Value, got:  with err: invalid CIDR address:`
- tp-v1-F8-0393 step 0: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F8-0393 step 1: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F8-0393 step 2: variable error; vv-2 value rejected in an expression or by the provider; `Error: Error in function call`
- tp-v1-F8-0406 step 0: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F8-0406 step 1: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F8-0406 step 2: variable error; unresolved variable has no value; `Error: No value for required variable`
- tp-v1-F8-0406 step 3: variable error; unresolved variable has no value; `Error: No value for required variable`

#### Step 4 outcome
- Not every step plans offline: 67 steps in 31 scenarios fail under at least one value set (dev 41 steps, test 26 steps). As the work package requires, D5a-2 stopped here: the first error, class and sub-cause are recorded above, and no step was fixed, dropped or given a fallback. Open D5-C in `docs/D5_DECISIONS.md` records the decision this needs.

### D5a-2.6 Drift against `e96c017`
- dev controlled: M scenario.json: 144
- dev real_world: A terrapreserve_data_variables.tf: 73
- dev real_world: M other step file: 94
- dev real_world: M scenario.json: 144
- repo -: M scenarios/test_manifest.json: 1
- test controlled: M scenario.json: 64
- test real_world: A terrapreserve_data_variables.tf: 40
- test real_world: M other step file: 52
- test real_world: M scenario.json: 64

