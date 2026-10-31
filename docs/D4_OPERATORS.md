# D4 Operators Catalogue

Catalogue of mutation operators for benchmark scenario families F1 through F8 in TerraPreserve (D0 Decision 5; D4-07).

Every operator:
1. Declares its family (`F1`..`F8`).
2. Declares its variant (`safe` or `unsafe`).
3. Declares its design intent: invariants it is designed to preserve (`intent.preserves`) and break (`intent.breaks`).
4. Declares and emits truthful `mutation_record` rows verified by `generator/diff_verify.py`.
5. Unsafe variants differ from their safe counterparts only by the damaging mutation on the identical base state S0.

---

## Protected Invariants (D0 Decision 4)
- **INV-SEC-001**: No security-group ingress from `0.0.0.0/0` or `::/0` to port 22
- **INV-SEC-002**: No security-group ingress from `0.0.0.0/0` or `::/0` to database port 5432
- **INV-SEC-003**: `aws_db_instance.publicly_accessible` is false
- **INV-FUNC-001**: EC2 can reach RDS on TCP/5432 (configuration-level)

---

## Family F1: Unrelated change
Edits attributes outside every invariant's scope (e.g. instance size, storage, monitoring, tags). Unsafe variants carry a hidden side-effect on a scoped attribute.

### Operators:
- **`op_f1_instance_resize`**
  - *Safe*: Updates `aws_instance.app.instance_type` from current to an alternative instance size (e.g. `t3.small` to `t3.medium`).
  - *Unsafe*: Updates `aws_instance.app.instance_type` AND modifies `aws_db_instance.main.publicly_accessible` to `true` (breaks `INV-SEC-003`).
- **`op_f1_storage_expand`**
  - *Safe*: Expands `aws_db_instance.main.allocated_storage` from 20 to 50 GB.
  - *Unsafe*: Expands `aws_db_instance.main.allocated_storage` AND removes the DB ingress rule or sets SG ingress from `0.0.0.0/0` to 5432 (breaks `INV-SEC-002`).
- **`op_f1_vpc_dns_toggle`**
  - *Safe*: Toggles `aws_vpc.main.enable_dns_hostnames` to false.
  - *Unsafe*: Toggles `aws_vpc.main.enable_dns_hostnames` to false AND adds an ingress rule for `0.0.0.0/0` on port 22 (breaks `INV-SEC-001`).

---

## Family F2: Direct impact
Edits a resource directly named in an invariant's scope (repair scenario starting from S0 violating target).
Target can be `INV-SEC-001`, `INV-SEC-002`, or `INV-SEC-003`.

### Operators:
- **`op_f2_repair_ssh`** (Target: `INV-SEC-001`)
  - *Safe*: Removes or narrows public SSH rule (`0.0.0.0/0` port 22) to a specific bastion CIDR (e.g. `10.0.0.0/8`).
  - *Unsafe*: Leaves SSH open to `0.0.0.0/0` or widens to `::/0` (fails to repair `INV-SEC-001`).
- **`op_f2_repair_db_ingress`** (Target: `INV-SEC-002`)
  - *Safe*: Removes the public `0.0.0.0/0` ingress on port 5432 while preserving the internal app SG ingress.
  - *Unsafe*: Fails to remove `0.0.0.0/0` or widens DB ingress to `::/0` (fails to repair `INV-SEC-002`).
- **`op_f2_repair_db_publicly_accessible`** (Target: `INV-SEC-003`)
  - *Safe*: Sets `aws_db_instance.main.publicly_accessible = false`.
  - *Unsafe*: Retains `publicly_accessible = true` (fails to repair `INV-SEC-003`).

---

## Family F3: Dependency-induced impact
Edits a resource not directly named in an invariant scope but on a dependency path (e.g. subnet, routing, DB subnet group).

### Operators:
- **`op_f3_move_ec2_subnet`**
  - *Safe*: Moves EC2 instance to a newly added equivalent application subnet within the same VPC and route table.
  - *Unsafe*: Moves EC2 instance to an isolated subnet with no route to RDS / different VPC (breaks `INV-FUNC-001`).
- **`op_f3_modify_db_subnet_group`**
  - *Safe*: Reorders or updates DB subnets in `aws_db_subnet_group.main` keeping valid multi-AZ subnets.
  - *Unsafe*: Replaces DB subnet group with single-AZ or detached subnets, or accidentally changes DB instance to public subnet.
- **`op_f3_app_sg_reassociation`**
  - *Safe*: Replaces app SG with an equivalent secondary SG having the same functional permissions.
  - *Unsafe*: Disassociates the app SG from EC2, assigning an empty SG (breaks `INV-FUNC-001`).

---

## Family F4: Regression-inducing repair
Composed repair: repairs the target invariant (`M_fix`), but unsafe variant simultaneously damages another invariant (`M_break`).

### Operators:
- **`op_f4_repair_ssh_break_db_func`** (Target: `INV-SEC-001`)
  - *Safe*: Removes public SSH rule on app SG.
  - *Unsafe*: Removes public SSH rule (`M_fix`), but also drops the 5432 ingress rule from app SG to db SG (`M_break`, breaks `INV-FUNC-001`).
- **`op_f4_repair_db_port_open_ssh`** (Target: `INV-SEC-002`)
  - *Safe*: Removes public 5432 ingress from db SG.
  - *Unsafe*: Removes public 5432 ingress (`M_fix`), but opens port 22 to `0.0.0.0/0` on app SG (`M_break`, breaks `INV-SEC-001`).
- **`op_f4_repair_rds_public_open_db_port`** (Target: `INV-SEC-003`)
  - *Safe*: Sets `aws_db_instance.publicly_accessible = false`.
  - *Unsafe*: Sets `publicly_accessible = false` (`M_fix`), but attempts to "fix" connectivity by opening 5432 to `0.0.0.0/0` (`M_break`, breaks `INV-SEC-002`). Canonical paper example.

---

## Family F5: Restructuring / replacement
Refactors configuration structure (`moved` blocks, inline vs separate rule resources, force-replacement, `count`).

> **Deviation:** In family F5, only `count` meta-argument restructuring is implemented (`op_f5_count_each_safe` and `op_f5_count_each_unsafe`); `for_each` restructuring is not implemented in D4a.

### Operators:
- **`op_f5_restructure_moved`**
  - *Safe*: Renames a resource (e.g. `aws_subnet.app` -> `aws_subnet.application`) and emits corresponding `moved { from = ... to = ... }` block.
  - *Unsafe*: Renames resource with `moved` block and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`.
- **`op_f5_inline_to_separate_sg_rules`**
  - *Safe*: Converts inline `ingress`/`egress` blocks of a security group into standalone `aws_security_group_rule` resources, preserving all ports, protocols, and sources.
  - *Unsafe*: Converts to standalone rules and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`.
- **`op_f5_count_each`**
  - *Safe*: Restructures `aws_instance` with `count` meta-argument (adding or removing `count = 1`), preserving resource references and protected invariants.
  - *Unsafe*: Restructures `count` meta-argument on `aws_instance` and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`.
- **`op_f5_force_replacement`**
  - *Safe*: Changes an attribute requiring resource replacement (e.g. instance AMI) with semantics intact.
  - *Unsafe*: Force-replacement updates AMI and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`.

---

## Family F6: New-resource creation
Adds new resources to the configuration, triggering baseline checks.

### Operators:
- **`op_f6_add_monitoring_sg`**
  - *Safe*: Adds a new security group for internal monitoring with restricted ingress (e.g. internal VPC CIDR only).
  - *Unsafe*: Adds a new security group open to `0.0.0.0/0` on port 22 or 5432 (breaks `INV-SEC-001` or `INV-SEC-002`).
- **`op_f6_add_bastion_host`**
  - *Safe*: Adds a bastion EC2 instance with ingress only from corporate IP ranges.
  - *Unsafe*: Adds a bastion instance with SSH ingress from `0.0.0.0/0` (breaks `INV-SEC-001`).
- **`op_f6_add_read_replica`**
  - *Safe*: Adds a private read-replica RDS instance in the same DB subnet group with `publicly_accessible = false`.
  - *Unsafe*: Adds a read-replica RDS instance with `publicly_accessible = true` (breaks `INV-SEC-003`).

---

## Family F7: Broad impact
Edits a central hub resource (VPC, shared route table, default security group) affecting multiple dependent resources.

### Operators:
- **`op_f7_shared_route_table_edit`**
  - *Safe*: Toggles core VPC DNS support (`enable_dns_support = false`).
  - *Unsafe*: Toggles core VPC DNS support and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`.
- **`op_f7_vpc_cidr_expansion`**
  - *Safe*: Toggles core VPC DNS hostnames (`enable_dns_hostnames = false`).
  - *Unsafe*: Toggles core VPC DNS hostnames and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`.
- **`op_f7_shared_sg_egress_tighten`**
  - *Safe*: Restricts outbound traffic on app SG to specific CIDRs (`10.0.0.0/8`) while maintaining DB 5432 access.
  - *Unsafe*: Restricts outbound traffic and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`.

---

## Family F8: Multi-step remediation
Multi-step patch sequences (2 to 4 steps) composing remediation steps. Unsafe variants introduce a regression in a middle step.

### Operators:
- **`op_f8_twostep_repair`** (2 steps)
  - *Safe*: Step 1 resizes instance; Step 2 repairs public SSH target.
  - *Unsafe*: Step 1 resizes instance; Step 2 repairs public SSH target and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`.
- **`op_f8_threestep_refactor_repair`** (3 steps)
  - *Safe*: Step 1 resizes instance; Step 2 expands DB storage; Step 3 repairs SSH target.
  - *Unsafe*: Step 1 resizes instance; Step 2 introduces regression by expanding DB storage and detaching application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`; Step 3 repairs SSH.
- **`op_f8_fourstep_maintenance`** (4 steps)
  - *Safe*: 4 distinct steps: Step 1 (resize), Step 2 (storage expand), Step 3 (VPC DNS toggle), Step 4 (repair SSH).
  - *Unsafe*: Middle step (Step 3) toggles VPC DNS hostnames and detaches application security group (`vpc_security_group_ids = []`), breaking `INV-FUNC-001`; Step 4 repairs SSH.

---

## Real-World Tier: Graft Rules and Operators (D4b-03, D4b-04, D4b-05)

### 1. Graft Architecture for Host Modules (D4b-03)
When a real-world host module is used as base state, its validated files are included verbatim (with top-level `terraform` and `provider` blocks removed via `hcl_lex.remove_top_level_blocks`, plus `terrapreserve_versions.tf`).
The benchmark functional and security invariants require an EC2 -> RDS core. This core is synthesized as separate files:
- `terrapreserve_graft.tf`
- `terrapreserve_graft_variables.tf`

**Graft Naming & Clash Rules:**
1. Every resource, data source, local, output, and variable name declared in graft files is strictly prefixed with `tp_` (e.g. `aws_instance.tp_app`, `aws_db_instance.tp_db`, `var.tp_db_password`).
2. Clash check: before grafting, all identifiers in the host module (resources, variables, locals, outputs, modules) are checked against the graft identifiers. Any overlap is a fatal error (`GraftClashError`), never an auto-rename.
3. The graft core is standalone in v1 (see Open Row 1) and does not attach to host networking.
4. Host files are never mutated; `grafted: true` is recorded in scenario metadata.

### 2. Operators on Host Modules (D4b-04)
Host scenarios reuse the 50 D4a operators directly. Operators act solely upon the graft model in `terrapreserve_graft.tf`. Host files are never modified, ensuring mutation records remain 100% truthful and verified.

### 3. Span-Edit Operators for Native Modules (D4b-05)
Natives (un-grafted real-world modules and derived natives) contain real, non-canonical HCL. Operators cannot use the generative model and instead perform strict, byte-exact span edits:

**Preconditions:**
- Target block and attribute exist and are parsed by `hcl_lex`.
- Attribute value is a literal (string or number), not an interpolation, heredoc, or dynamic block.
- Block does not use `count` or `for_each`.
- If preconditions fail, the operator does not apply and the module is not used for that cell.

**Native Operators:**
- **`op_native_f1_resize_safe` / `op_native_f1_resize_unsafe`** (Family F1)
  - Preconditions: `aws_instance.*` exists with literal `instance_type`.
  - Safe: Changes `instance_type` (e.g. `"t3.micro"` -> `"t3.small"`). Mutation record: 1 row.
  - Unsafe: Changes `instance_type` AND mutates `aws_db_instance.*` `publicly_accessible` span to `true` (breaks `INV-SEC-003`).
- **`op_native_f2_narrow_ssh_safe` / `op_native_f2_widen_ssh_unsafe`** (Family F2)
  - Preconditions: Target SG rule or inline ingress on port 22 exists.
  - Safe: Replaces CIDR span `"0.0.0.0/0"` with a private CIDR `"10.0.0.0/8"`.
  - Unsafe: Replaces CIDR span with `"0.0.0.0/0"` or widens scope (fails repair).
- **`op_native_f4_repair_ssh_safe` / `op_native_f4_repair_ssh_break_db_unsafe`** (Family F4)
  - Preconditions: Ingress on port 22 and port 5432 rule exist.
  - Safe: Repairs SSH rule only (replaces `"0.0.0.0/0"` with `"10.0.0.0/8"`).
  - Unsafe: Repairs SSH rule AND widens port 5432 ingress to `"0.0.0.0/0"` (breaks `INV-SEC-002`).
- **`op_native_f6_create_locked_sg_safe` / `op_native_f6_create_open_sg_unsafe`** (Family F6)
  - Preconditions: Host has valid VPC and CIDR.
  - Safe: Adds a separate file `terrapreserve_aux_sg.tf` creating an auxiliary locked-down SG (port 443 only).
  - Unsafe: Adds `terrapreserve_aux_sg.tf` creating an SG open to `0.0.0.0/0` on port 22 (breaks `INV-SEC-001`).
- **`op_native_f8_twostep_safe` / `op_native_f8_twostep_unsafe`** (Family F8)
  - Preconditions: Module supports F1 and F2 preconditions.
  - Safe: Step 1 executes F1 span edit; Step 2 executes F2 safe repair.
  - Unsafe: Step 1 executes F2 repair; Step 2 modifies database configuration to `publicly_accessible = true`.


