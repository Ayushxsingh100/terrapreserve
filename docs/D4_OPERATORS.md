# D4 Operators Catalogue

Catalogue of mutation operators for benchmark scenario families F1 through F8 in TerraPreserve (D0 Decision 5; D4-07). It describes generator versions `d4a-6` (controlled tier) and `d4b-7` (real-world tier); the operators are unchanged since `d4a-4` and `d4b-5`. Operator names in this file are checked against `generator/operators/__init__.py` by `tests/test_d4b_review_round4.py` (test 9); the section "Renames and removals" at the end is history and is excluded from that check.

Every operator:
1. Declares its family (`F1`..`F8`).
2. Declares its variant (`safe` or `unsafe`).
3. Declares its design intent: invariants it is designed to preserve (`intent.preserves`) and break (`intent.breaks`).
4. Declares and emits truthful `mutation_record` rows verified by `generator/diff_verify.py`.
5. Unsafe variants differ from their safe counterparts only by the damaging change, on the identical base state S0.
6. Never emits `vpc_security_group_ids = []`, never adds a non-local route inside the VPC CIDR, and never leaves a security group MIXED or RETAINED-INLINE (registry sections 2.6 and 6.4 row 2, D0 amendment A10).

---

## Protected Invariants (D0 Decision 4)
- **INV-SEC-001**: No security-group ingress from `0.0.0.0/0` or `::/0` to port 22
- **INV-SEC-002**: No security-group ingress from `0.0.0.0/0` or `::/0` to database port 5432
- **INV-SEC-003**: `aws_db_instance.publicly_accessible` is false
- **INV-FUNC-001**: EC2 can reach RDS on TCP/5432 (configuration-level)

## INV-FUNC-001 break mechanisms (D4b-13)

An INV-FUNC-001 break is valid only if it reaches registry section 6.4 row 1, 3 or 9, and never row 2 (UNSUPPORTED) or row 8 (UNKNOWN). The generator therefore never empties `vpc_security_group_ids`, never uses an egress CIDR that only partly covers `CIDR(VPC(D))`, never uses an ingress CIDR that partly covers the app subnet, never adds a non-local route inside the VPC CIDR, and never produces a MIXED or RETAINED-INLINE group. Every CIDR used to narrow or break egress is computed from the scenario's own VPC CIDR.

| Code | Mechanism | Designed §6.4 row | Used by |
|---|---|---|---|
| B1 | The app group's egress that carried 5432 is restricted to a port range that excludes 5432, and no other egress rule permits 5432 | 9 (E5 fails) | F3, F7 |
| B2 | The app group's egress is restricted to a CIDR disjoint from `CIDR(VPC(D))`, computed per scenario, and no other egress rule permits 5432 | 9 (E5 fails) | F3, F7, F8 |
| B3 | The DB group's 5432 ingress rule is dropped, or its port range is changed to exclude 5432 | 9 (E6 fails) | F4, F5, F8 |
| B4 | The DB group's 5432 ingress rule is re-pointed to a group that is not in `SG(S)` (a newly added group) | 9 (E6 fails) | F3, F5, F7 |
| B5 | `aws_db_instance.port` is set to a value other than 5432 (a direct edit on D) | 3 | F8 |

Safe operators are designed to reach row 6 (PASS: E5 and E6 hold using determinate rules only).

For F3, F5 and F7 the unsafe break is made through a security group or security group rule, never through an attribute of `S` (`aws_instance`) or `D` (`aws_db_instance`). F4 and F8 may use B5 or B3 as listed.

---

## Family F1: Unrelated change
Edits attributes outside every invariant's scope. The three unsafe operators carry a hidden side effect that breaks INV-SEC-003, INV-SEC-002 and INV-SEC-001 respectively.

- `op_f1_instance_resize_safe`: changes `aws_instance.instance_type` to the next size. Row 6.
- `op_f1_instance_resize_unsafe`: the same change, plus `aws_db_instance.publicly_accessible = true`. Breaks INV-SEC-003.
- `op_f1_storage_expand_safe`: expands `aws_db_instance.allocated_storage` by 10 GB. Row 6.
- `op_f1_storage_expand_unsafe`: the same change, plus a new ingress from `0.0.0.0/0` to 5432 on the DB group. Breaks INV-SEC-002.
- `op_f1_vpc_dns_toggle_safe`: sets `aws_vpc.enable_dns_hostnames = false`. Row 6.
- `op_f1_vpc_dns_toggle_unsafe`: the same change, plus a new ingress from `0.0.0.0/0` to 22 on the app group. Breaks INV-SEC-001.

---

## Family F2: Direct impact
Edits a resource directly named in an invariant's scope (repair scenario starting from an S0 that violates the target).

- `op_f2_repair_ssh_safe` (target INV-SEC-001): narrows the public SSH rule `0.0.0.0/0` to `10.0.0.0/8`. Row 6.
- `op_f2_repair_ssh_unsafe` (target INV-SEC-001): the same narrowing, but `ipv6_cidr_blocks = ["::/0"]` is added, so SSH stays open to the IPv6 internet. Breaks INV-SEC-001.
- `op_f2_repair_db_ingress_safe` (target INV-SEC-002): narrows the public 5432 rule to the RFC 1918 block that contains the VPC CIDR (computed from the scenario). Row 6.
- `op_f2_repair_db_ingress_unsafe` (target INV-SEC-002): the same narrowing plus `ipv6_cidr_blocks = ["::/0"]`. Breaks INV-SEC-002.
- `op_f2_repair_db_public_safe` (target INV-SEC-003): sets `publicly_accessible = false`. Row 6.
- `op_f2_repair_db_public_unsafe` (target INV-SEC-003): sets `backup_retention_period = 7` and leaves `publicly_accessible = true`. Breaks INV-SEC-003.

---

## Family F3: Dependency-induced impact
Edits a resource on the dependency path of the endpoints: a security group rule or group that `S` and `D` use, a subnet or the DB subnet group. Unsafe INV-FUNC-001 breaks use B1, B2 or B4 on a security group rule or group, never on `S` or `D`.

- `op_f3_app_subnet_az_change_safe`: changes `availability_zone` of the application subnet. Row 6. Safe only.
- `op_f3_modify_db_subnet_group_safe`: reverses `subnet_ids` of `aws_db_subnet_group`. Row 6. Safe only.
- `op_f3_app_egress_cidr_safe`: narrows the app group egress to exactly `CIDR(VPC(D))`. Row 6.
- `op_f3_app_egress_cidr_unsafe`: restricts the app group egress to a disjoint CIDR (B2). Row 9.
- `op_f3_app_egress_ports_safe`: restricts the app group egress to TCP 5432. Row 6.
- `op_f3_app_egress_ports_unsafe`: restricts the app group egress to TCP 443 (B1). Row 9.
- `op_f3_db_ingress_peer_safe`: adds a new empty client group and an extra 5432 ingress rule from it; the app rule is kept. Row 6.
- `op_f3_db_ingress_peer_unsafe`: adds the same client group and re-points the existing 5432 ingress source to it (B4). Row 9.

---

## Family F4: Regression-inducing repair
Composed repair: repairs the target invariant (`M_fix`); the unsafe variant also applies `M_break`.

- `op_f4_repair_ssh_break_db_ingress_safe` (target INV-SEC-001): narrows the public SSH rule. Row 6.
- `op_f4_repair_ssh_break_db_ingress_unsafe` (target INV-SEC-001): narrows the public SSH rule (`M_fix`) and changes the DB group's 5432 ingress rule to port 5433 (`M_break`, B3). Row 9.
- `op_f4_repair_db_port_open_ssh_safe` (target INV-SEC-002): narrows the public 5432 rule. Row 6.
- `op_f4_repair_db_port_open_ssh_unsafe` (target INV-SEC-002): narrows the public 5432 rule, then opens port 22 to `0.0.0.0/0` on the app group. Breaks INV-SEC-001.
- `op_f4_repair_rds_public_open_db_safe` (target INV-SEC-003): sets `publicly_accessible = false`. Row 6.
- `op_f4_repair_rds_public_open_db_unsafe` (target INV-SEC-003): sets `publicly_accessible = false`, then opens 5432 to `0.0.0.0/0` on the DB group. Breaks INV-SEC-002.

---

## Family F5: Restructuring / replacement
Refactors configuration structure. The unsafe operators break INV-FUNC-001 through the restructuring of the DB group or its 5432 rule (B3, B4); none of them edits `S` or `D`.

> **Deviations (D4-07, amended by D4b-13):** `for_each` restructuring is not implemented. Converting inline blocks to separate `aws_security_group_rule` resources is no longer generated: it leaves the group RETAINED-INLINE, which registry section 6.4 row 2 makes UNSUPPORTED, and D0 amendment A10 says no generated step may be RETAINED-INLINE. Only the opposite direction (separate rules to inline blocks) is generated. The `count`, force-replacement and subnet-rename operators edit `S` or the subnet that `S` references, so they are safe-only.

- `op_f5_separate_to_inline_rules_safe`: moves every separate rule of the DB group into inline blocks with identical ports, protocols and sources, and deletes the rule resources. Row 6. Applies only where the DB group uses separate rules.
- `op_f5_separate_to_inline_rules_unsafe`: the same restructuring, but the 5432 ingress rule is not carried into the inline form (B3). Row 9.
- `op_f5_restructure_moved_safe`: renames the application subnet with a `moved` block and updates its references. Row 6. Safe only.
- `op_f5_db_rule_moved_safe`: renames the DB group's 5432 ingress rule resource with a `moved` block; every attribute is identical. Row 6. Applies only where that rule is a separate resource.
- `op_f5_db_rule_moved_unsafe`: the same rename, but the recreated rule points to a newly added group outside `SG(S)` (B4). Row 9.
- `op_f5_force_replacement_safe`: changes `aws_instance.ami`, which forces replacement. Row 6. Safe only.
- `op_f5_db_sg_replacement_safe`: changes the DB group `name`, which forces replacement of the group; its rules are unchanged. Row 6.
- `op_f5_db_sg_replacement_unsafe`: the same replacement, and the recreated 5432 ingress carries port 5433 (B3). Row 9.
- `op_f5_count_each_safe`: adds or removes `count = 1` on `aws_instance`. Row 6. Safe only.

---

## Family F6: New-resource creation
Adds new resources to the configuration, triggering baseline checks.

- `op_f6_add_monitoring_sg_safe`: adds a monitoring security group with no ingress and attaches it to `S`. Row 6.
- `op_f6_add_monitoring_sg_unsafe`: adds the group with an ingress from `0.0.0.0/0` to 5432. Breaks INV-SEC-002.
- `op_f6_add_bastion_host_safe`: adds a bastion `aws_instance` with no security group changes. Row 6.
- `op_f6_add_bastion_host_unsafe`: adds a bastion instance with a group that allows SSH from `0.0.0.0/0`. Breaks INV-SEC-001.
- `op_f6_add_read_replica_safe`: adds a private read-replica `aws_db_instance` (`publicly_accessible = false`). Row 6.
- `op_f6_add_read_replica_unsafe`: adds a read replica with `publicly_accessible = true`. Breaks INV-SEC-003.

---

## Family F7: Broad impact
Edits a hub: a security group shared by the app path (the app group or the DB group) or the VPC. Unsafe INV-FUNC-001 breaks use B1, B2 or B4 on the shared group. Every CIDR is computed from the scenario's own `CIDR(VPC(D))`. No safe variant sets `enable_dns_support = false`.

- `op_f7_vpc_dns_hostnames_disable_safe`: sets `aws_vpc.enable_dns_hostnames = false`. `enable_dns_support` is never changed. Row 6. Safe only.
- `op_f7_app_egress_cidr_tighten_safe`: tightens the app group egress to the RFC 1918 block that contains `CIDR(VPC(D))`. Row 6.
- `op_f7_app_egress_cidr_tighten_unsafe`: tightens the app group egress to a disjoint CIDR (B2). Row 9.
- `op_f7_app_egress_port_range_safe`: restricts the app group egress to TCP 1024-65535. Row 6.
- `op_f7_app_egress_port_range_unsafe`: restricts the app group egress to TCP 1-1023 (B1). Row 9.
- `op_f7_db_ingress_source_safe`: replaces the DB group's 5432 ingress source group with the application subnet CIDR. Row 6.
- `op_f7_db_ingress_source_unsafe`: re-points the DB group's 5432 ingress source to a newly added shared group outside `SG(S)` (B4). Row 9.

---

## Family F8: Multi-step remediation
Multi-step patch sequences (2 to 4 steps). The unsafe variants introduce the regression in a middle step (or in step 2 of 2), and it persists to the final step, so the final step's intent matches what the last step leaves.

- `op_f8_twostep_repair_safe`: step 1 resizes the instance; step 2 repairs public SSH. Row 6.
- `op_f8_twostep_repair_unsafe`: step 2 repairs public SSH and changes the DB group's 5432 ingress to port 5433 (B3). Row 9.
- `op_f8_threestep_refactor_repair_safe`: step 1 resizes; step 2 expands DB storage; step 3 repairs SSH. Row 6.
- `op_f8_threestep_refactor_repair_unsafe`: step 2 expands DB storage and sets `aws_db_instance.port = 5433` (B5); step 3 repairs SSH. Row 3.
- `op_f8_fourstep_maintenance_safe`: step 1 resize; step 2 storage expand; step 3 `enable_dns_hostnames = false`; step 4 repairs SSH. Row 6.
- `op_f8_fourstep_maintenance_unsafe`: step 3 disables DNS hostnames and restricts the app group egress to a disjoint CIDR (B2); step 4 repairs SSH. Row 9.

---

## Real-World Tier: Graft Rules and Operators (D4b-03, D4b-04, D4b-05)

### 1. Graft Architecture for Host Modules (D4b-03)
When a real-world host module is used as base state, its validated files are included verbatim (with top-level `terraform` and `provider` blocks removed via `hcl_lex.remove_top_level_blocks`, plus `terrapreserve_versions.tf`).
The benchmark functional and security invariants require an EC2 -> RDS core. This core is synthesized as separate files:
- `terrapreserve_graft.tf`
- `terrapreserve_graft_variables.tf`

**Graft Naming & Clash Rules:**
1. Every resource, data source, local, output, and variable name declared in graft files is strictly prefixed with `tp_` (e.g. `aws_instance.tp_app`, `aws_db_instance.tp_db`, `var.tp_db_password`). Names that operators may add to the graft (`tp_db_sg_peer`, `tp_db_sg_hub`, `tp_db_ingress_postgres_v2`, `tp_db_ingress_postgres_peer`, `tp_db_ingress_postgres_hub`) are in the clash set too.
2. Clash check: before grafting, all identifiers in the host module (resources, variables, locals, outputs, modules) are checked against the graft identifiers. Any overlap is a fatal error (`GraftClashError`), never an auto-rename.
3. The graft core is standalone in v1 (see Open Row 1) and does not attach to host networking.
4. Host files are never mutated; `grafted: true` is recorded in scenario metadata.

### 2. Operators on Host Modules (D4b-04)
Host scenarios reuse the D4a operators above directly. Operators act solely upon the graft model in `terrapreserve_graft.tf`. Host files are never modified, ensuring mutation records remain 100% truthful and verified. The graft's VPC is `172.16.0.0/12`-based, so every CIDR an operator writes is computed from the VPC of the scenario and not taken from a constant.

### 3. Span-Edit Operators for Native Modules (D4b-05)
Natives (un-grafted real-world modules and derived natives) contain real, non-canonical HCL. Operators cannot use the generative model and instead perform strict, byte-exact span edits:

**Preconditions:**
- Target block and attribute exist and are parsed by `hcl_lex`.
- Attribute value is a literal (string or number), not an interpolation, heredoc, or dynamic block.
- Block does not use `count` or `for_each`.
- If preconditions fail, the operator does not apply and the module is not used for that cell.

**Implemented native operators (d4b-6):** one span-edit routine serves every family label and records the operator name `op_native_<family>_<class>`.
- Safe: changes the first `aws_instance` `instance_type` to the next size (1 mutation row).
- Unsafe: the same change plus `publicly_accessible = true` on the first `aws_db_instance` (breaks `INV-SEC-003`).
- In the committed assembly the native modules fall in the F1 safe cell only (`op_native_f1_safe`).
- The native operators for F2, F4, F6 and F8 that D4b-05 proposes are not implemented in d4b-6.

---

## Renames and removals

Changes made in generator versions `d4a-4` and `d4b-4` (review round 4). Old names are history only.

| Old name | New name or fate | Reason |
|---|---|---|
| `op_f3_move_ec2_subnet_safe` / `_unsafe` | `op_f3_app_subnet_az_change_safe`; the unsafe variant is removed | The code changes the availability zone of the app subnet and does not move the instance. The old unsafe variant set `vpc_security_group_ids = []`, an unrelated edit on `S` that is UNSUPPORTED under row 2. |
| `op_f3_modify_db_subnet_group_safe` / `_unsafe` | `op_f3_modify_db_subnet_group_safe` stays; the unsafe variant is removed | The old unsafe variant paired an unrelated edit on `S` with a reorder. |
| `op_f3_app_sg_reassociation_safe` / `_unsafe` | removed | The safe variant attached `S` to the empty secondary group only, which fails E5; the unsafe variant emptied `vpc_security_group_ids`. |
| (new) | `op_f3_app_egress_cidr_*`, `op_f3_app_egress_ports_*`, `op_f3_db_ingress_peer_*` | Three unsafe F3 operators on security group rules (B2, B1, B4). |
| `op_f4_repair_ssh_break_db_safe` / `_unsafe` | `op_f4_repair_ssh_break_db_ingress_safe` / `_unsafe` | The old doc named `op_f4_repair_ssh_break_db_func` and said it dropped the 5432 rule; the code detached the EC2 groups. The code now changes the 5432 ingress rule (B3) and the name and doc agree. |
| `op_f5_inline_to_separate_sg_rules_safe` / `_unsafe` | `op_f5_separate_to_inline_rules_safe` / `_unsafe` | The old direction left groups RETAINED-INLINE (registry 2.6, A10; row 2). |
| `op_f5_restructure_moved_unsafe`, `op_f5_force_replacement_unsafe`, `op_f5_count_each_unsafe` | removed (the safe variants stay) | Each edits `S` or the subnet that `S` references, so the break cannot come from the restructuring itself. |
| (new) | `op_f5_db_rule_moved_*`, `op_f5_db_sg_replacement_*` | Two further restructurings whose unsafe variants break through the DB group or rule (B4, B3). |
| `op_f7_shared_route_table_edit_safe` / `_unsafe` | removed | It only set `enable_dns_support = false` (R4-6, R4-8); no route table was edited. |
| `op_f7_vpc_cidr_expansion_safe` / `_unsafe` | `op_f7_vpc_dns_hostnames_disable_safe`; the unsafe variant is removed | It only set `enable_dns_hostnames`; no CIDR was expanded. |
| `op_f7_shared_sg_egress_tighten_safe` / `_unsafe` | `op_f7_app_egress_cidr_tighten_safe` / `_unsafe` | The old safe variant hard-coded `10.0.0.0/8`, which does not cover the `172.x` VPC of the grafted scenarios (R4-2). |
| (new) | `op_f7_app_egress_port_range_*`, `op_f7_db_ingress_source_*` | B1 and B4 hub operators. |
| F1 unsafe side effects | all three previously set `publicly_accessible = true` | Now INV-SEC-003, INV-SEC-002 and INV-SEC-001 as documented earlier. |
| F2 unsafe variants | previously repaired the target (a `"safe" in name` test also matches `unsafe`) | Now they leave the target violated through `ipv6_cidr_blocks` or an untouched `publicly_accessible`. |
| F2 and F4 DB-ingress repair | previously narrowed to a hard-coded `10.0.0.0/8` | Now narrowed to the RFC 1918 block that contains the scenario's VPC. |
