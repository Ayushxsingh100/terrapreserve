# Resolution of the `[TO VERIFY AT D1]` markers

Resolves every marker in `INVENTORY.md` (DAIL commit `7ed7aaf2602aaceba087608bb4b7db035bbc5194`, files `docs/specs/INVARIANT_REGISTRY_v1.md` = REG and `docs/specs/D0_AMENDMENTS_v1.0.1.md` = AMD) against the pinned versions:

| Pin | Value | How it was read in this session |
|---|---|---|
| Terraform | `1.15.8` (`required_version = "~> 1.15.0"`) | `terraform version` in `V01/output/commands.log` |
| `hashicorp/aws` | `6.53.0`, tag `v6.53.0` = commit `a0c8167ac1f9d8e20925e2084f56ce1d65a50a40` | lock file in every probe; `gh api repos/hashicorp/terraform-provider-aws/git/ref/tags/v6.53.0` |
| Checkov | `3.3.30`, tag `3.3.30` = commit `dfeb34b2d52a269bb417b4d4f7854a16bef06629` | `V02/output/checkov_version.txt`; the four source files cited below were compared byte-for-byte with the tag and are identical |
| Schema dump | sha256 `d6eca2ffe2141a23a742999b09c67b93c3e99939aacfff4e9afe37702664e9b2`, 19,169,003 bytes, 1,678 resource types | `validation/d1_to_verify/schema/SCHEMA_SHA256.txt` |

Provider source and docs links below use `PROV` = `https://github.com/hashicorp/terraform-provider-aws/blob/v6.53.0` and Checkov links use `CKV` = `https://github.com/bridgecrewio/checkov/blob/3.3.30`. The registry documentation pages `registry.terraform.io/providers/hashicorp/aws/6.53.0/docs/...` are rendered from the `website/docs/r/*.html.markdown` files at the tag; the files were read at the tag, the rendered pages were not opened.

AWS and HashiCorp web pages were retrieved on 2026-10-23.

**Conventions.** E1 = empirical probe committed under `validation/d1_to_verify/<item>/`. E2 = documentary (pinned-version source or docs). Probes run offline: mock credentials only in environment variables (`validation/d1_to_verify/common.sh`), the skip flags set, and `HTTPS_PROXY`/`HTTP_PROXY` pointing at the unreachable `http://127.0.0.1:9`. No probe ran `terraform apply` against AWS; V10 applied only the built-in `terraform_data` resource against local state.

**Machine-local setup (not a change to any pin).** `terraform init` downloaded nothing: the registry download failed with an IPv6 connection reset, so the identical `6.53.0` binary already installed by the smoke configuration was copied into a local filesystem mirror (`TF_CLI_CONFIG_FILE`, `TF_DATA_DIR`, see `common.sh`). `-lockfile=readonly` succeeded, so the binary matches the lock-file hashes. The local IPv4-only proxy from Prompt A was **not** used for any command.

---

### V01 — Offline `terraform plan` for the nine types plus `aws_db_subnet_group`

Marker: AMD:111, `[TO VERIFY AT D1: whether a plan can be produced offline for these nine types, with mock credentials and the provider's skip flags, without data sources.]`

Outcome: CONFIRMED

Verified fact: `terraform validate` and `terraform plan -out` succeed offline for a configuration containing all ten types (15 resource instances, `Plan: 15 to add`), and `terraform show -json` yields all 15 entries in `resource_changes`. The skip flags are necessary (the same provider without them fails calling STS through the dead proxy). The plan JSON leaves many oracle-relevant values unknown, so an oracle that reads it must also read the `configuration` section (see the list under Consequence).

Evidence E1: `validation/d1_to_verify/V01/` (`bash validation/d1_to_verify/V01/run.sh`).
- `V01/output/commands.log`: `terraform validate` -> `Success! The configuration is valid.`; `terraform plan -input=false -out=plan.bin` -> `Plan: 15 to add, 0 to change, 0 to destroy.` with `HTTPS_PROXY=http://127.0.0.1:9`.
- `V01/output/plan_facts.txt`: `resource_changes: 15`, `types: [aws_db_instance, aws_db_subnet_group, aws_instance, aws_internet_gateway, aws_route_table, aws_route_table_association, aws_security_group, aws_security_group_rule, aws_subnet, aws_vpc]`.
- Network-blocked proof: (a) the plan succeeded under the dead proxy; (b) control `V01/control_network_on/` (same provider, same proxy, **no** skip flags) fails: `output/control_commands.log` -> `Error: Retrieving AWS account details: validating provider credentials: retrieving caller identity from STS ... request send failed, Post "https://sts.us-east-1.amazonaws.com/": proxyconnect tcp: dial tcp 127.0.0.1:9: connectex: No connection could be made because the target machine actively refused it.` (`[exit 1]`), which shows the provider honours the proxy variables; (c) `V01/output/network_evidence.txt`: a `TF_LOG=DEBUG` plan has 345 lines, 0 mention `amazonaws.com`, 0 mention `proxyconnect`.

Evidence E2: none read. The four `skip_*` provider arguments are accepted by the pinned provider (they validate and plan in V01); the provider documentation of them was not opened in this session. The empirical result above is the primary evidence.

Consequence for DAIL / TerraPreserve: AMD A3.4 (lines 110-112) can take its first branch: the oracle can read `terraform show -json` as D5 plans (no second HCL parser is forced by offline planning). Attribute availability in the plan JSON (from `V01/output/plan_facts.txt`, `V05`, `V07`, `V09`):
- **Known:** `aws_security_group_rule` `type`, `protocol` (normalised, see V09), `from_port`, `to_port`, `cidr_blocks`, `self`; `aws_subnet.cidr_block`; `aws_vpc.cidr_block`; `aws_db_instance.engine`, `db_subnet_group_name` (literal or `name` reference of the group, as written), `publicly_accessible` (`false` when unset, see V05); `aws_instance.ami`; the route's `cidr_block`.
- **Unknown ("known after apply") whenever they depend on another resource's `id`:** `security_group_id`, `source_security_group_id` (also unknown when unset, because the attribute is optional+computed), `vpc_id`, `subnet_id`, `route_table_id`, `vpc_security_group_ids` (both `aws_instance` and `aws_db_instance`), `subnet_ids`, the route's `gateway_id` (plan shows the route object with `gateway_id` unknown and every other target field `""`).
- **Unknown even though not configured:** `aws_security_group.ingress` and `.egress` (optional+computed; the plan does not say that no inline rule was written), `aws_db_instance.port` when unset (V07), `aws_instance.private_ip`.
- **References** (the `configuration` section, `expressions.<attr>.references`) are complete for every wiring above, e.g. `aws_instance.app.vpc_security_group_ids` -> `["aws_security_group.app.id", "aws_security_group.app"]`, `aws_route_table.public.route` -> `aws_internet_gateway.main.id`. Registry §2.2 ("Identity references") matches this representation; an oracle must take wiring from `configuration`, not from `resource_changes[].change.after`.
- Whether an argument was *set* (for example `port`, `source_security_group_id`) is visible only in `configuration.expressions`, because unset computed arguments appear in `after_unknown`.
- Not tested: `count`/`for_each` whose size depends on an unknown value (plan would be expected to fail); no module or data-source cases.

Open question for authors: Should the oracle read plan JSON plus the `configuration` section as one input (as the evidence supports), or keep a second HCL reader as a cross-check? (Not decided here; AMD A3.4 leaves both open.)

### V02 — Checkov check for INV-SEC-002 (TCP/5432 from `0.0.0.0/0` or `::/0`)

Marker: AMD:135, `[TO VERIFY AT D1]`; REG:252, `[TO VERIFY AT D1 against the pinned Checkov version. If none exists, record "none; custom predicate only" (C-14).]`

Outcome: CONFIRMED

Verified fact: Checkov 3.3.30 has no check dedicated to port 5432 or to PostgreSQL ingress, and no generic check distinguishes a `0.0.0.0/0 -> 5432` rule from a `10.0.0.0/16 -> 5432` rule. Record: **none; custom predicate only.**

Evidence E1: `validation/d1_to_verify/V02/` (`bash validation/d1_to_verify/V02/run.sh`).
- `V02/output/grep_5432.txt`: the literal `5432` does not occur in any `.py`, `.yaml`, `.yml` or `.json` file of the installed Checkov package (`[grep exit 1 ; 1 means no match]`).
- `V02/output/candidate_checks.md`: the catalogue (`checkov --list --framework terraform`, 4,647 rows) filtered to security-group, NACL and RDS entities or port/ingress/postgres/public text: the only ingress-port checks are `CKV_AWS_24` (22), `CKV_AWS_25` (3389), `CKV_AWS_260` (80), `CKV_AWS_277` (-1, i.e. all) and the NACL checks `CKV_AWS_229`/`230`/`231`/`232` (ports 21, 20, 3389, 22); the other security-group rows are generic (`CKV2_AWS_5` attached, `CKV_AWS_23` description, `CKV_AWS_382` egress all); the PostgreSQL checks concern logging, version and encryption.
- `V02/output/public_vs_private.txt`: all Terraform checks run on `public_5432/` and `private_5432/` (same rules, only the CIDR differs). The failing check ids are identical (`CKV_AWS_23`, `CKV2_AWS_5`); `check ids failing on the public configuration but not the private one: []`.

Evidence E2: `CKV/checkov/terraform/checks/resource/aws/AbsSecurityGroupUnrestrictedIngress.py#L11-L17` builds the port-specific checks from a port number; the concrete subclasses at the tag are 22, 3389, 80 and -1 (`SecurityGroupUnrestrictedIngress22.py#L6`, `...3389.py`, `...80.py`, `...Any.py#L7`). No subclass uses 5432.

Consequence for DAIL / TerraPreserve: REG:252 and AMD:135 may be closed as "none; custom predicate only" (register C-14 wording). A5 table row for INV-SEC-002 stays "None". `CKV_AWS_277` fires only for all-port rules and is not a substitute.

Open question for authors: none.

### V03 — Checkov check for INV-SEC-003 (`aws_db_instance.publicly_accessible`)

Marker: AMD:136, `[TO VERIFY AT D1]`; REG:282, ``[TO VERIFY AT D1: that it tests `publicly_accessible` in the pinned version.]``

Outcome: CONFIRMED

Verified fact: `CKV_AWS_17` ("Ensure all data stored in RDS is not publicly accessible") is the right candidate. It inspects the key `publicly_accessible` and FAILs only for the value `true`; an absent attribute PASSes; an unresolved reference gives no result (UNKNOWN). It also scans `aws_rds_cluster_instance`.

Evidence E1: `validation/d1_to_verify/V03/` (`bash validation/d1_to_verify/V03/run.sh`), `V03/output/summary.txt`:
- absent -> PASSED; `false` -> PASSED; `true` -> FAILED; `"true"` (string) -> FAILED;
- `var.public` with no value -> no result (UNKNOWN); `var.public` with default `true` -> FAILED; `local.public = true` -> FAILED;
- two instances, one `true` -> `d1=PASSED d2=FAILED`;
- `count = 0` with `true` -> no result;
- `aws_rds_cluster_instance` `true` -> FAILED, absent -> PASSED.

Evidence E2: `CKV/checkov/terraform/checks/resource/aws/RDSPubliclyAccessible.py#L17-L26` (id `CKV_AWS_17`, `supported_resources = ['aws_db_instance', 'aws_rds_cluster_instance']`, inspected key `publicly_accessible`, forbidden values `[True]`); `CKV/checkov/terraform/checks/resource/base_resource_negative_value_check.py#L34-L67` (missing attribute -> `missing_attribute_result` = PASSED, line 22 default; references in the value -> UNKNOWN, lines 54-56).

Consequence for DAIL / TerraPreserve: AMD A5 row and REG §5.6 can drop "Candidate". Checkov's results agree with registry vectors R1 (absent PASS), R2 (true FAIL), R3 (unresolved: Checkov reports no result, registry UNKNOWN). Checkov also evaluates `aws_rds_cluster_instance`, which registry §5.3 declares out of scope; a difference on such a resource is not a defect of either.

Open question for authors: none.

### V04 — `CKV_AWS_24` semantics

Marker: REG:240, `[TO VERIFY AT D1: the semantics in the pinned Checkov version.]`

Outcome: CHANGED

Verified fact: `CKV_AWS_24` is not the "single rule's CIDR, no IPv6" check that REG §3.7 describes. At 3.3.30 it (a) scans `aws_security_group` inline `ingress`, `aws_security_group_rule` (type `ingress`) **and** `aws_vpc_security_group_ingress_rule`; (b) tests IPv6, but only for the exact strings `::/0` and `0000:0000:0000:0000:0000:0000:0000:0000/0`, and not at all for `aws_vpc_security_group_ingress_rule` (`cidr_ipv6`); (c) **ignores the protocol** unless it is `-1` (a `udp` or `icmp` rule on port 22 from `0.0.0.0/0` FAILs); (d) treats `from_port = to_port = 0` as all ports for any protocol; (e) matches only the literal `0.0.0.0/0` (a split `0.0.0.0/1` + `128.0.0.0/1` PASSes; `0.0.0.0/00` PASSes); (f) passes a rule that also lists `prefix_list_ids` or sets `self = true`; (g) in an inline `aws_security_group` it returns PASSED at the first ingress block with `self = true`, so a later public block is missed; (h) ignores egress: a `type = "egress"` rule gives no result, an inline `egress` block PASSes, `aws_vpc_security_group_egress_rule` is not scanned; (i) resolves variable defaults and gives no result for a variable without a value.

Evidence E1: `validation/d1_to_verify/V04/` (35 variants, one directory each; `bash validation/d1_to_verify/V04/run.sh`), results in `V04/output/summary.txt`. `FAILED` = Checkov reports a failure for that resource.

| Question | Variant (directory) | Result |
|---|---|---|
| Resource types | inline `ingress` tcp 22 `0.0.0.0/0` (`t1_...`) | FAILED |
| | `aws_security_group_rule` ingress tcp 22 (`t2_...`) | FAILED |
| | `aws_vpc_security_group_ingress_rule` tcp 22 `cidr_ipv4` (`t3_...`) | FAILED |
| | same type, `ip_protocol = "-1"`, no ports (`t4_...`) | PASSED (missed) |
| Egress ignored? | `aws_security_group_rule` `type = "egress"` tcp 22 (`t5_...`) | no result |
| | inline `egress` block tcp 22 (`t6_...`) | PASSED |
| | `aws_vpc_security_group_egress_rule` tcp 22 (`t7_...`) | no result (type not scanned) |
| IPv6 | rule `::/0` tcp 22 (`v1_...`) | FAILED |
| | rule `0000:0000:0000:0000:0000:0000:0000:0000/0` (`v2_...`) | FAILED |
| | rule `0:0:0:0:0:0:0:0/0` (`v3_...`) | PASSED (missed) |
| | inline `ipv6_cidr_blocks = ["::/0"]` (`v4_...`) | FAILED |
| | `aws_vpc_security_group_ingress_rule` `cidr_ipv6 = "::/0"` (`v5_...`) | PASSED (missed) |
| Port ranges / protocol | tcp 20-30 (`p1`) / tcp 0-65535 (`p2`) / tcp 0-0 (`p3`) | FAILED / FAILED / FAILED |
| | tcp 23-30 (`p4`) | PASSED |
| | **udp 22** (`p5`) / **icmp 22** (`p9`) | FAILED / FAILED |
| | protocol `-1` ports 0-0 (`p6`) / `all` 0-0 (`p7`) / `-1` 22-22 (`p8`) / `"6"` 22 (`p10`) | FAILED (all four) |
| CIDR spellings | `0.0.0.0/1` + `128.0.0.0/1` (`m1`) | PASSED (union not computed) |
| | `["10.0.0.0/8", "0.0.0.0/0"]` (`m2`) | FAILED |
| | `0.0.0.0/00` (`m3`) / `10.0.0.0/8` (`m4`) / `10.0.0.0/16` (`m13`) | PASSED / PASSED / PASSED |
| Other short-circuits | `0.0.0.0/0` plus `prefix_list_ids` (`m5`) | PASSED |
| | `0.0.0.0/0` plus `self = true` (`m6`) | PASSED |
| | SG source only (`m7`) | PASSED |
| | inline: `self` block first, public block second (`m8`) | PASSED (missed) |
| | inline: public block first, `self` block second (`m9`) | FAILED |
| | no ingress at all (`m10`) | PASSED |
| Unresolved | `var.ssh_cidr` without value (`m11`) | PASSED |
| | `var.ssh_cidr` with default `0.0.0.0/0` (`m12`) | FAILED |

Evidence E2: `CKV/checkov/terraform/checks/resource/aws/AbsSecurityGroupUnrestrictedIngress.py`:
- `#L14` supported resources (`aws_security_group`, `aws_security_group_rule`, `aws_vpc_security_group_ingress_rule`);
- `#L41-L57` inline loop, `#L46-L47` `check_self` returns PASSED immediately;
- `#L59-L68` rule resources; egress returns `CheckResult.UNKNOWN` (`#L68`);
- `#L69-L76` `aws_vpc_security_group_ingress_rule` branch (needs `from_port` or `to_port`);
- `#L78-L111` `contains_violation`: `#L82-L83` (0/0 means all ports), `#L85-L87` (prefix lists -> no violation), `#L89-L90` (port range or `-1` with 0-65535; the protocol is never compared with `tcp`), `#L98` (literal `0.0.0.0/0`), `#L104-L105` (the two IPv6 strings; `v5` PASSing is consistent with `cidr_ipv6` arriving as a plain string, where `ip in [...] for ip in ipv6_cidr_blocks[0]` iterates characters; that is a reading of the source, the observed result is E1), `#L107-L110` (no source at all counts as public);
- `#L113-L118` `check_self`. `SecurityGroupUnrestrictedIngress22.py#L6` binds it to `CKV_AWS_24`, port 22.

Consequence for DAIL / TerraPreserve: REG §3.7 (lines 237-240) needs correcting: line 238 ("lists it for `aws_security_group` and `aws_security_group_rule`") omits `aws_vpc_security_group_ingress_rule`; line 239 ("has no IPv6 clause here") is wrong for the two scanned forms. The agreement statements with the registry's conformance vectors (REG §8): S1, S2 (protocol `-1`, 0-0), S7 agree with Checkov; **S4** (split halves: registry FAIL, Checkov PASS), **S8** (`udp 22`: registry PASS, Checkov FAIL) and **S9** (variable without value: registry UNKNOWN, Checkov PASS) are disagreements. These are not defects of the registry, but the "differences recorded" wording of AMD A5 (line 134) should list them. A registry-versus-Checkov comparison harness must not treat Checkov FAIL/PASS as ground truth for S4/S8/S9.

Open question for authors: Which Checkov disagreements are "expected" (documented v1 limitations, e.g. S4, S8, S9, `aws_vpc_security_group_ingress_rule` IPv6 and all-protocol gaps) and which should be counted as findings against Checkov in the paper? (Not decided here.)

### V05 — `aws_db_instance.publicly_accessible` defaults to `false`

Marker: REG:261, `[TO VERIFY AT D1 against the pinned provider version.]`

Outcome: CONFIRMED

Verified fact: In 6.53.0 `publicly_accessible` is `Optional` with `Default: false`; the plan JSON therefore shows `false` for an unset attribute.

Evidence E1: `validation/d1_to_verify/V05/` (`V05/output/facts.txt`): `aws_db_instance.unset` -> `publicly_accessible false`; `explicit_false` -> `false`; `explicit_true` -> `true`; `from_variable` (`var.public`, default `true`) -> `true`. `V01/output/plan_facts.txt` shows `false` as well for the unset `aws_db_instance.database`.

Evidence E2: `PROV/internal/service/rds/instance.go#L540-L544` (`names.AttrPubliclyAccessible: { Type: schema.TypeBool, Optional: true, Default: false }`); `PROV/website/docs/r/db_instance.html.markdown#L370-L371` ("`publicly_accessible` - (Optional) Bool to control if instance is publicly accessible. Default is `false`."). The provider schema (`schema/schema_filtered.json`) shows `optional: true`, not computed.

Consequence for DAIL / TerraPreserve: REG §5.2 (line 261) holds. For an oracle reading the plan JSON, an unset `publicly_accessible` is already `false` in `after`; for an HCL reader the default must be applied. Both paths agree with registry vector R1.

Open question for authors: none.

### V06 — Default allow-all egress is removed when an `aws_security_group` is created

Marker: REG:130, `[TO VERIFY AT D1: the same note for the pinned provider version.]`

Outcome: CONFIRMED

Verified fact: The pinned provider documents the same note and its create function revokes AWS's default allow-all egress rules (IPv4 `0.0.0.0/0` and IPv6 `::/0`, protocol `-1`) right after creating the group. Limitation: this cannot be observed without `terraform apply`, so there is no E1; the evidence is the documentation and the source.

Evidence E1: none possible offline (state limitation above).

Evidence E2: `PROV/website/docs/r/security_group.html.markdown#L67` ("**NOTE on Egress rules:** By default, AWS creates an `ALLOW ALL` egress rule when creating a new Security Group inside of a VPC. When creating a new Security Group inside a VPC, **Terraform will remove this default rule**, and require you specifically re-create it if you desire that rule."); `PROV/internal/service/ec2/vpc_security_group.go#L222-L263` (comment "AWS defaults all Security Groups to have an ALLOW ALL egress rule. Here we revoke that rule, so users don't unknowingly have/use it.", then `RevokeSecurityGroupEgress` for `0.0.0.0/0` and for `::/0`). In the source the revocation is unconditional, not VPC-specific.

Consequence for DAIL / TerraPreserve: REG §2.6 "Default egress" (line 130) holds, including `Out(g)` possibly empty (conformance vectors F5). Note for the oracle: the plan JSON for `aws_security_group.egress` is unknown when no inline egress is configured (V01), so "empty" must be derived from the configuration, not from the plan.

Open question for authors: none.

### V07 — RDS postgres default port 5432, and what the plan shows

Marker: REG:310, `[TO VERIFY AT D1: the RDS default port for the postgres engine is 5432.]`

Outcome: CONFIRMED

Verified fact: AWS documents 5432 as the default port for RDS for PostgreSQL. The provider does not set a default: `port` is `Optional` + `Computed`, so the plan JSON shows `port` as **unknown** ("known after apply") when it is unset, even though `engine` is known. A literal or variable-driven port is known in the plan.

Evidence E1: `validation/d1_to_verify/V07/` (`V07/output/facts.txt`): `unset_postgres` -> `port <unknown>`; `unset_mysql` -> `<unknown>`; `literal_5432` -> `5432`; `literal_3306` -> `3306`; `from_variable` (`var.db_port` = 5432) -> `5432`. The same `<unknown>` appears for the canonical database in `V01/output/plan_facts.txt`.

Evidence E2: AWS RDS API Reference, CreateDBInstance, request parameter `Port`: "Default: RDS for Db2 - 50000 RDS for MariaDB - 3306 RDS for Microsoft SQL Server - 1433 RDS for MySQL - 3306 RDS for Oracle - 1521 RDS for PostgreSQL - 5432" (`https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_CreateDBInstance.html`, retrieved 2026-10-23). `PROV/internal/service/rds/instance.go#L535-L539` (`port`: `TypeInt`, `Optional`, `Computed`, no `Default`); `PROV/website/docs/r/db_instance.html.markdown#L369` ("The port on which the DB accepts connections.", no default stated).

Consequence for DAIL / TerraPreserve: REG §6.3 E2 (lines 309-310) is correct for postgres. An oracle that reads plan JSON cannot learn the effective port of an unset-port instance from the plan; it must apply the engine default itself (and decide the same for other engines, REG row 3 of §6.4). Registry vectors F11 (`port = 3306` -> FAIL) are visible in the plan; the "absent port, engine postgres" PASS path is not.

Open question for authors: Should the registry state a default-port table for engines other than `postgres` (here `engine != postgres` with no port gives FAIL by row 3), or keep "other engines with port unset" as FAIL? (Not decided here.)

### V08 — Host-bit and malformed CIDRs are rejected at validation

Marker: REG:84, `[TO VERIFY AT D1: the provider rejects host-bit CIDRs at validation.]`

Outcome: CONFIRMED

Verified fact: Host-bit CIDRs are rejected by `terraform validate` (and therefore by `plan`) for `aws_security_group_rule.cidr_blocks`, for inline `ingress.cidr_blocks` in `aws_security_group`, for `ipv6_cidr_blocks` in both forms, and for `aws_vpc.cidr_block`. Malformed values (no mask, prefix too long, non-CIDR text) are rejected too. Valid network addresses pass.

Evidence E1: `validation/d1_to_verify/V08/` (`bash validation/d1_to_verify/V08/run.sh`), `V08/output/summary.txt` (`validate=1 plan=1` = rejected):
- `rule_v4_hostbits` (`10.0.0.5/24`): `"10.0.0.5/24" is not a valid IPv4 CIDR block; did you mean "10.0.0.0/24"?`
- `inline_v4_hostbits`: same message; `rule_v6_hostbits` and `inline_v6_hostbits` (`2001:db8::1/32`): `is not a valid IPv6 CIDR block; did you mean "2001:db8::/32"?`
- `rule_v4_default_with_hostbits` (`0.0.0.1/0`) and `rule_v6_default_with_hostbits` (`::1/0`): rejected.
- `rule_v4_no_mask` (`10.0.0.1`), `rule_v4_prefix_too_long` (`10.0.0.0/33`), `rule_v4_not_a_cidr` (`not-a-cidr`): `is not a valid CIDR block: invalid CIDR address`.
- `vpc_v4_hostbits` (`10.1.0.5/16`): `expected cidr_block to contain a valid network Value, expected 10.1.0.0/16, got 10.1.0.5/16`.
- Controls `rule_v4_valid_control`, `inline_v4_valid_control`, `rule_v6_valid_control`, `inline_v6_valid_control`: `validate=0 plan=0`.

Evidence E2: `PROV/internal/verify/validate.go#L237-L245` (`ValidIPv4CIDRNetworkAddress`) and the IPv6 function at `#L248-L256`; used as `ValidateFunc` for `cidr_blocks` and `ipv6_cidr_blocks` at `PROV/internal/service/ec2/vpc_security_group_rule.go#L65` and `#L94` and for the inline rule schema at `PROV/internal/service/ec2/vpc_security_group.go#L142` and `#L159`.

Consequence for DAIL / TerraPreserve: REG §2.5 (line 84) holds as far as Terraform-valid configurations are concerned: a host-bit CIDR cannot occur in a configuration that passes `terraform validate` (REG §2.8 already makes such a configuration UNSUPPORTED for every invariant). The registry's own "host bits set makes the rule UNSUPPORTED" branch is therefore reachable only for configurations that Terraform rejects; D0 gate 2 keeps those out of TerraPreserve. A reader that works on HCL without Terraform (an independent parser) must still parse CIDRs strictly.

Open question for authors: none.

### V09 — Upper-case protocol values

Marker: REG:88, `[TO VERIFY AT D1: the provider accepts upper-case values.]`

Outcome: CONFIRMED

Verified fact: `"TCP"`, `"Tcp"`, `"ALL"`, `"All"`, `"ICMP"`, `"UDP"`, `"ICMPV6"` are accepted by both `aws_security_group_rule` and inline `aws_security_group` `ingress`. The plan JSON shows the **normalised** value, identical for both forms: names are lower-cased, `all`/`ALL`/`All` become `-1`, and numeric protocols that have a name become that name (`6` -> `tcp`, `17` -> `udp`, `58` -> `icmpv6`).

Evidence E1: `validation/d1_to_verify/V09/` (`V09/output/protocols.txt`, `validate=0 plan=0`):

| configured | rule form (plan `protocol`) | inline form (plan `ingress[].protocol`) |
|---|---|---|
| `TCP`, `tcp`, `Tcp` | `tcp` | `tcp` |
| `ALL`, `All`, `all`, `-1` | `-1` | `-1` |
| `6` | `tcp` | `tcp` |
| `ICMP` | `icmp` | `icmp` |
| `UDP`, `17` | `udp` | `udp` |
| `icmpv6`, `ICMPV6`, `58` | `icmpv6` | `icmpv6` |

Evidence E2: `PROV/internal/service/ec2/vpc_security_group.go#L1457-L1467` (`protocolStateFunc`) and `#L1469-L1502` (`protocolForValue`: `strings.ToLower`, `-1`/`all` -> `-1`, number -> name via `securityGroupProtocolIntegers`); wired as `StateFunc` at `PROV/internal/service/ec2/vpc_security_group_rule.go#L113` and `PROV/internal/service/ec2/vpc_security_group.go#L170`.

Consequence for DAIL / TerraPreserve: REG §2.5 (line 88) holds. An oracle that reads plan JSON receives canonical lower-case names, `-1` for "all", and names for numbers; an HCL reader receives what was written and must apply REG §2.5's table (which also lists `"icmp"`/`"1"`; the number `1` was not probed).

Open question for authors: none.

### V10 — Implicit moves for `count` and `for_each` in Terraform 1.15

Marker: REG:69, ``[TO VERIFY AT D1: the implicit-move rules for `count` and `for_each` in the pinned Terraform version.]``

Outcome: CONFIRMED

Verified fact: In Terraform 1.15.8, adding `count` to a resource without meta-arguments moves `x` to `x[0]` implicitly, and removing `count` moves `x[0]` back to `x`. There is **no** implicit move into or out of `for_each` (no meta-argument -> `for_each`, `count` -> `for_each`, `for_each` -> none, `for_each` -> `count` all plan a destroy plus a create). An explicit `moved` block makes each of those a no-op move. The 1.15 documentation states only the "add `count`" direction; the "remove `count`" direction is observed but not documented there.

Evidence E1: `validation/d1_to_verify/V10/` (`bash validation/d1_to_verify/V10/run.sh`; `terraform_data`, local state, no provider, no AWS), `V10/output/summary.txt`:
- `C1` none -> `count = 1`: `terraform_data.x[0]: actions=['no-op'] previous_address=terraform_data.x`; plan text `# terraform_data.x has moved to terraform_data.x[0]`, `Plan: 0 to add, 0 to change, 0 to destroy.` (`output/C1_none_to_count1.txt`).
- `C2` `count = 1` -> none: `terraform_data.x: no-op previous_address=terraform_data.x[0]`.
- `C3` none -> `for_each = toset(["a"])`: `terraform_data.x: delete; terraform_data.x["a"]: create` (plan text: `# terraform_data.x will be destroyed (because resource uses count or for_each)`).
- `C4` `count = 1` -> `for_each`: `terraform_data.x[0]: delete; terraform_data.x["a"]: create`.
- `C5` `for_each` -> none: `x: create; x["a"]: delete`. `C6` `for_each` -> `count = 1`: `x[0]: create; x["a"]: delete`.
- `C7` none -> `count = 2`: `x[0]: no-op previous_address=x; x[1]: create`. `C8` `count = 2` -> none: `x: no-op previous_address=x[0]; x[1]: delete`.
- With a `moved` block: `M3` (none -> `for_each`), `M4` (`count` -> `for_each`) and `M6` (`for_each` -> `count`) are each `no-op previous_address=<old address>`.

Evidence E2: Terraform v1.15.x documentation, "Refactoring" (`https://developer.hashicorp.com/terraform/language/v1.15.x/modules/develop/refactoring`, retrieved 2026-10-23, page marked v1.15.x): "When you add `count` to an existing resource that didn't previously have the argument, Terraform automatically proposes moving the original object to instance `0` unless you write a `moved` block that explicitly mentions that resource. However, we recommend writing out the corresponding `moved` block explicitly to make the change clearer"; and "you can use `moved` to switch between keys and to add and remove keys as you switch between `count`, `for_each`, or neither." The page has no passage about removing `count`; direction `count` -> none is therefore established by E1 only.

Consequence for DAIL / TerraPreserve: REG §2.3 (line 69): "Terraform's implicit move when `count` is added to or removed from a single-instance resource MUST be followed" is correct for both directions. The registry does not say what happens for `for_each`: a comparison that follows only explicit and `count` implicit moves will see a `for_each` introduction as delete + create, exactly as Terraform plans it, so a scenario that switches to `for_each` without a `moved` block must be treated as a delete of the old address (REG §6.4 row 1 when the endpoint is `S` or `D`). The oracle's identity step needs these rules (also for `count` > 1 -> none, only index 0 is moved).

Open question for authors: Should the registry add one sentence stating that no implicit move exists into or out of `for_each` (and for `count` -> `for_each`)? (This changes no predicate; recorded as register C-76.)

### V11 — Security groups are allow-only

Marker: REG:105, `[TO VERIFY AT D1: cite the AWS security-group documentation.]`

Outcome: CONFIRMED

Verified fact: AWS documents that security-group rules can only allow traffic.

Evidence E1: none (documentary fact about the AWS service).

Evidence E2: Amazon VPC User Guide, "Security group rules" -> "Security group rule basics" (`https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html`, retrieved 2026-10-23): "You can specify allow rules, but not deny rules." Also, from "Control traffic to your AWS resources using security groups" (`https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html`, retrieved 2026-10-23): "The only traffic that reaches the instance is the traffic allowed by the security group rules."

Consequence for DAIL / TerraPreserve: REG §2.6 (line 105) holds; the monotonic handling of unresolved rules in §3.4 and §6.4 rows 7-8 depends on it and is supported.

Open question for authors: none.

### V12 — Completeness of the relevant-unsupported type lists

Marker: REG:142, `[TO VERIFY AT D1: complete both lists against the pinned provider's resource index. Any further resource that creates security-group rules, attaches security groups, filters subnet traffic or adds routes inside a VPC must be added before the freeze.]`

Outcome: CHANGED

Verified fact: HEURISTIC, a human decides. The lists in REG §2.7 do not cover every type of the 6.53.0 resource index that the keyword heuristic associates with security-group rules, security-group attachment, routes or subnet placement. Of 1,678 resource types, 396 match; 25 are already supported or listed; 371 are not listed: 248 are tier 1 (type-family or strong attribute match) and 123 tier 2 (weak keyword), and 126 of the 371 sit in the core EC2/VPC/RDS name families. Every registry-listed type exists in the schema; `aws_vpc_peering_connection` matched no keyword, which shows the heuristic's limit.

Evidence E1: `validation/d1_to_verify/V12/` (`v12_unsupported_types.py`, run against the schema dump named in the header): `V12/output/summary.txt`, `candidates_all.tsv` (all matches), `missing_tier1.tsv`, `missing_tier2.tsv`, `missing_core.tsv`. The script prints the trigger attributes of every row. Schema facts for the supported types: `schema/schema_filtered.json`.

Evidence E2: provider docs at the tag for the types singled out below: `PROV/website/docs/r/vpc_security_group_rules_exclusive.html.markdown` ("manages the complete set of ingress and egress rules assigned to a security group ... removing any rules not explicitly defined in the configuration"); `.../vpc_security_group_vpc_association.html.markdown` ("managing Security Group VPC Associations"); `.../vpn_gateway_route_propagation.html.markdown` ("Requests automatic route propagation between a VPN gateway and a route table"); `.../vpc_route_server_propagation.html.markdown`; `.../route_table.html.markdown#L19-L23` (`propagating_vgws`); `.../default_subnet.html.markdown`.

Candidates a human should look at first, selected by reading `V12/output/missing_core.tsv` and `missing_tier1.tsv` (one line each; "probably irrelevant" is my judgement, not a result):

| Type | Trigger attribute | Possible impact |
|---|---|---|
| `aws_vpc_security_group_rules_exclusive` | `security_group_id`, ingress/egress rule ids | Removes rules not listed: the applied rule set differs from the configured one -> SEC-001/002, FUNC E5/E6 (similar to MIXED) |
| `aws_vpc_security_group_vpc_association` | `security_group_id`, `vpc_id` | A security group used from another VPC -> FUNC E3/E4, M1 (see X02) |
| `aws_vpn_gateway_route_propagation` | `route_table_id` | Adds routes to a route table that the configuration does not list -> FUNC M3/E7 |
| `aws_vpc_route_server_propagation` (and `aws_vpc_route_server*`) | `route_table_id` | Same: dynamic routes into a route table -> FUNC M3/E7 |
| `aws_default_subnet`, `aws_default_vpc` | `cidr_block`, `subnet_id` | Default subnet/VPC adopted as a resource; REG §6.4 row 2 covers a missing `subnet_id`, but the registry does not say how a `subnet_id` that references an `aws_default_subnet` (not an `aws_subnet`) is treated -> FUNC E4 |
| `aws_vpc_peering_connection_accepter`, `aws_vpc_peering_connection_options` | `vpc_peering_connection_id` | Accepter side of the listed `aws_vpc_peering_connection` -> FUNC M3 |
| `aws_ec2_transit_gateway_vpc_attachment_accepter` | `subnet_ids`, `transit_gateway_attachment_id` | Accepter side of the listed attachment -> FUNC M3 |
| `aws_ec2_transit_gateway_route`, `..._route_table`, `..._route_table_association`, `..._route_table_propagation` | `transit_gateway_route_table_id` | TGW-side routing; reaches the VPC only through a VPC route to the gateway, which `aws_route` / inline routes already cover -> probably irrelevant |
| `aws_vpc_endpoint_security_group_association`, `aws_vpc_endpoint_subnet_association`, `aws_vpc_endpoint_route_table_association` | `security_group_id`, `subnet_id`, `route_table_id` | Endpoint interfaces/routes (prefix-list destinations); the listed `aws_vpc_endpoint` is already UNSUPPORTED for FUNC -> probably irrelevant on their own |
| `aws_spot_instance_request`, `aws_launch_template`, `aws_launch_configuration`, `aws_ec2_fleet`, `aws_spot_fleet_request`, `aws_autoscaling_group` | `vpc_security_group_ids`, `security_groups`, `subnet_id` | Launch EC2 instances other than `aws_instance`; INV-FUNC-001 binds `S` to an `aws_instance` -> probably irrelevant (a scenario that swaps `aws_instance` for one of these deletes `S`, row 1) |
| `aws_db_proxy`, `aws_db_proxy_endpoint`, `aws_db_proxy_target` | `vpc_security_group_ids` | A proxy path between EC2 and RDS; `D` is bound to an `aws_db_instance` -> probably irrelevant to the predicate as written |
| `aws_rds_cluster`, `aws_rds_cluster_instance`, `aws_rds_shard_group`, `aws_docdb_cluster_instance`, `aws_neptune_cluster_instance`, `aws_dms_replication_instance`, `aws_mq_broker`, `aws_lightsail_database`, `aws_m2_environment` | `publicly_accessible` | Other public-flag resources; REG §5.3 already declares them out of scope for INV-SEC-003, C-65 keeps the list for SEC-003 empty -> recorded as a limitation |
| `aws_ec2_managed_prefix_list`, `aws_ec2_managed_prefix_list_entry` | `prefix_list_id`, `entry.cidr` | Prefix-list contents; rules that use them are already indeterminate (REG §2.6) -> probably irrelevant |
| `aws_vpc_ipv6_cidr_block_association`, `aws_vpc_ipam_pool_cidr*` | `ipv6_cidr_block`, `cidr` | IPv6 only (FUNC is IPv4 only) / IPAM-allocated CIDR (VPC `cidr_block` unresolved -> UNKNOWN already) -> probably irrelevant |
| `aws_ec2_secondary_network`, `aws_ec2_secondary_subnet` | `ipv4_cidr_block` | New resource kinds whose effect on VPC addressing was not read -> unclear, review |
| Other services (Lambda, ECS, ELB, EKS, ElastiCache, ...) attaching security groups to their own interfaces (the remaining tier-1 and tier-2 types in `missing_tier1.tsv` and `missing_tier2.tsv`) | `security_group_ids`, `security_groups` | Their own ENIs are neither `S` nor `D` -> probably irrelevant |

Further schema facts for the supported types that bear on the footprints (from `schema/schema_filtered.json`, 6.53.0): `aws_instance` has the blocks `network_interface` (`network_interface_id`, `device_index`, ...) and `primary_network_interface` (`network_interface_id`), which are not in the footprint of `S` (REG §6.6); `aws_route_table` has `propagating_vgws` next to the `route` attribute; `aws_security_group.ingress` and `.egress` are optional+computed attributes (processed as attribute-as-blocks, `PROV/website/docs/r/security_group.html.markdown#L111`: removing them from the configuration does not delete the managed rules).

Consequence for DAIL / TerraPreserve: REG §2.7 table (lines 136-140), the UNSUPPORTED condition in §3.4 and §6.4 row 2, and §9 depend on these lists; they must not be taken as complete until the authors decide each candidate. Nothing is added to the lists here.

Open question for authors: Which of the candidate types above (first six rows especially) join the relevant-unsupported lists before the freeze, and should the `S` footprint include the `network_interface` blocks? (Decision for the authors; recorded as register C-74 and C-78.)

### V13 — Doc 04 §7.6: `aws_instance` security-group arguments

Marker: REG:376, `[TO VERIFY AT D1. If confirmed, raise a Doc 04 errata row.]`

Outcome: CONFIRMED

Verified fact: `aws_instance` has no argument `security_group_ids` in 6.53.0. `vpc_security_group_ids` (a set of strings, optional, computed) takes security-group IDs for a VPC placement; `security_groups` (a set of strings, optional, computed) takes security-group **names** and is documented for EC2-Classic and the default VPC only.

Evidence E1: `schema/schema_facts.txt` (written by `schema/schema_facts.py` from `schema/schema_filtered.json`, which `schema/extract_schema.py` derives from `terraform providers schema -json`, sha256 in the header): `[V13] aws_instance.vpc_security_group_ids: attribute, optional+computed, type ["set", "string"]`, `aws_instance.security_groups: attribute, optional+computed, type ["set", "string"]`, `aws_instance.security_group_ids: ABSENT`.

Evidence E2: `PROV/website/docs/r/instance.html.markdown#L242-L244` ("`security_groups` - (Optional, EC2-Classic and default VPC only) List of security group names to associate with." and "**NOTE:** If you are creating Instances in a VPC, use `vpc_security_group_ids` instead.") and `#L257` ("`vpc_security_group_ids` - (Optional, VPC only) List of security group IDs to associate with.").

Consequence for DAIL / TerraPreserve: errata for Doc 04 §7.6: replace `security_group_ids` with `vpc_security_group_ids` (IDs, VPC) and note `security_groups` (names, EC2-Classic/default VPC). Registry §6.4 row 2 ("`S` uses name-based `security_groups`") and §6.6 already use the correct names. The registry is consistent with the provider.

Open question for authors: none.

### V14 — Doc 04 §7.8: `aws_security_group_rule` source-group argument

Marker: REG:378, `[TO VERIFY AT D1.]`

Outcome: CONFIRMED

Verified fact: `aws_security_group_rule` has no `security_group_ids` or `security_group_id(s)` source argument. The source security group is `source_security_group_id` (optional, computed string; conflicts with `cidr_blocks`, `ipv6_cidr_blocks` and `self`). `security_group_id` exists but is **required** and names the group the rule belongs to (the target), not a source. In an inline `aws_security_group` `ingress`/`egress` object the source groups are `security_groups` (a set of IDs).

Evidence E1: `schema/schema_facts.txt` (see V13): `aws_security_group_rule.security_group_id: attribute, required`, `source_security_group_id: attribute, optional+computed`, `self: attribute, optional`, `security_group_ids: ABSENT`; `[V14] aws_security_group.ingress element attributes: cidr_blocks, description, from_port, ipv6_cidr_blocks, prefix_list_ids, protocol, security_groups, self, to_port`. In the V01 plan, `app_to_db_5432` has `source_security_group_id` as a reference to `aws_security_group.app` and `security_group_id` as a reference to `aws_security_group.db` (`V01/output/plan_facts.txt`).

Evidence E2: `PROV/website/docs/r/security_group_rule.html.markdown#L94` ("`security_group_id` - (Required) Security group to apply this rule to."), `#L102` (one of `cidr_blocks`, `ipv6_cidr_blocks`, `prefix_list_ids`, `source_security_group_id` must be given), `#L109` ("`source_security_group_id` - (Optional) Security group id to allow access to/from, depending on the `type`. Cannot be specified with `cidr_blocks`, `ipv6_cidr_blocks`, or `self`."); `PROV/internal/service/ec2/vpc_security_group_rule.go#L107` (`AtLeastOneOf` the five source arguments).

Consequence for DAIL / TerraPreserve: errata for Doc 04 §7.8: the SG-to-SG source field is `source_security_group_id` (rule resource) / `security_groups` (inline blocks); `security_group_id` is the rule's target group. Registry §2.6 (`src_sg(r)`, lines 116 and 108) already says this correctly.

Open question for authors: none.

### X01 — Mixing inline rules and `aws_security_group_rule` (MIXED groups)

Marker: REG:128, `[TO VERIFY AT D1: the provider documentation for the pinned version.]`

Outcome: CONFIRMED

Verified fact: The pinned provider documentation warns against combining inline rules with `aws_security_group_rule` on one group. It extends the same warning to `aws_vpc_security_group_ingress_rule` and `aws_vpc_security_group_egress_rule`.

Evidence E1: none (documentary).

Evidence E2: `PROV/website/docs/r/security_group.html.markdown#L15` ("You should not use the `aws_security_group` resource with _in-line rules_ ... in conjunction with the `aws_vpc_security_group_egress_rule` and `aws_vpc_security_group_ingress_rule` resources or the `aws_security_group_rule` resource. Doing so may cause rule conflicts, perpetual differences, and result in rules being overwritten.") and `PROV/website/docs/r/security_group_rule.html.markdown#L15` (the same warning from the rule side).

Consequence for DAIL / TerraPreserve: REG §2.6 "MIXED groups" (line 128) holds. The provider's warning also covers `aws_vpc_security_group_*_rule` mixed with either form; those two types are already relevant-unsupported (REG §2.7), so the registry's result for such a configuration is UNSUPPORTED by that route.

Open question for authors: none.

### X02 — M1: RDS security groups and subnet group share a VPC

Marker: REG:299, `[TO VERIFY AT D1: cite the AWS RDS documentation for this requirement.]`

Outcome: UNRESOLVED

Verified fact: No AWS RDS page read in this session states the requirement "the instance's security groups and its subnet group are in the same VPC". The closest statements are: the CreateDBInstance parameter `VpcSecurityGroupIds` has "Default: The default EC2 VPC security group for the DB subnet group's VPC", and the RDS User Guide says a DB subnet group is "a collection of subnets ... that you create in a VPC". In addition, the VPC User Guide states that a security group can be assigned "to resources created in the same VPC as the security group or to resources in other VPCs if using the Security Group VPC Association feature", and the provider has a resource for it (`aws_vpc_security_group_vpc_association`, schema, V12). Whether RDS accepts such a group is not established.

Evidence E1: none (cannot be probed without AWS). The existence of the provider type is in `schema/resource_types.txt`.

Evidence E2: what was read: `https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_CreateDBInstance.html` (parameters `VpcSecurityGroupIds`, `DBSubnetGroupName`); `https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html` ("Working with DB subnet groups"); `https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html` ("Security group basics"); all retrieved 2026-10-23. A web search also surfaced an AWS re:Post community answer to the effect that the groups must be in the same VPC; it was not opened, is not AWS documentation and is not used as evidence.

Consequence for DAIL / TerraPreserve: REG §6.2 M1 (line 299) rests on an uncited assumption that is also weakened by Security Group VPC Association. It stays an assumption until the authors choose to cite or drop it; the evidence record already lists it under `assumptions` (REG §2.10).

Open question for authors: Keep M1 as a recorded assumption, or add `aws_vpc_security_group_vpc_association` to the relevant-unsupported list of INV-FUNC-001 (recorded as register C-77)?

### X03 — AWS Free plan eligibility and sign-up (D0 amendments A3.3 option a)

Marker: AMD:99, `[TO VERIFY before step 17: EC2, RDS and VPC Reachability Analyzer eligibility]` and `[TO VERIFY]` (sign-up identity and payment verification)

Outcome: UNRESOLVED

Verified fact: not established. These markers are due "before step 17", not at D1; they concern current AWS account and pricing policy, not the pinned Terraform, provider or Checkov versions, and the sign-up conditions cannot be observed without creating an account (not allowed in this work package).

Evidence E1: none.

Evidence E2: none gathered.

Consequence for DAIL / TerraPreserve: A3.3 recommendation (c) offline-only is unaffected; option (a) stays unverified.

Open question for authors: Is X03 to be handled in the step that chooses the calibration route (before step 17), as AMD:99 says?

### X04 — Emulator options (D0 amendments A3.3 option b)

Marker: AMD:100, three markers: `[TO VERIFY]` (whether research use qualifies for LocalStack Hobby), `[TO VERIFY]` (whether it includes EC2 and RDS), `[TO VERIFY per tool]` (security-group, route, NACL and Reachability Analyzer behaviour of emulators)

Outcome: UNRESOLVED

Verified fact: not established. Whether research use qualifies under a vendor's licence is a legal reading for the authors, and the other two questions need the vendors' current documentation and a test of each tool; none of it is a pinned-version fact and none was done in this work package.

Evidence E1: none.

Evidence E2: none gathered.

Consequence for DAIL / TerraPreserve: A3.3 already limits option (b) to "deployability smoke test, never runtime evidence", which does not depend on the answers.

Open question for authors: Is option (b) worth verifying at all, given that A3.3 keeps it out of the evidence chain?

---

## Summary

| Item | Outcome | E1 probes | E2 sources |
|---|---|---:|---:|
| V01 | CONFIRMED | 3 | 0 |
| V02 | CONFIRMED | 3 | 1 |
| V03 | CONFIRMED | 1 | 2 |
| V04 | CHANGED | 1 | 1 |
| V05 | CONFIRMED | 2 | 2 |
| V06 | CONFIRMED | 0 | 2 |
| V07 | CONFIRMED | 2 | 3 |
| V08 | CONFIRMED | 1 | 3 |
| V09 | CONFIRMED | 1 | 2 |
| V10 | CONFIRMED | 1 | 1 |
| V11 | CONFIRMED | 0 | 2 |
| V12 | CHANGED | 1 | 6 |
| V13 | CONFIRMED | 1 | 1 |
| V14 | CONFIRMED | 2 | 2 |
| X01 | CONFIRMED | 0 | 2 |
| X02 | UNRESOLVED | 0 | 3 |
| X03 | UNRESOLVED | 0 | 0 |
| X04 | UNRESOLVED | 0 | 0 |

Counting rule: E1 = directories or output files of separate probes cited under "Evidence E1"; E2 = distinct documents or source files cited under "Evidence E2". UNRESOLVED rows count what was read, even though it does not settle the marker.
