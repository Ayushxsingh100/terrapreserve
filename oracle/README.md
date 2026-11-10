# oracle/

The independent oracle that produces every ground-truth label (D5). It is written only from the Invariant Registry Specification (DAIL `docs/specs/INVARIANT_REGISTRY_v1.md`, tag `registry-v1.0`, read as a specification), Terraform semantics and AWS semantics. It never reads DAIL code, guides, prompts or output (DAIL ADR-010).

**Version `oracle-1.0` (D5b).** Oracle verifier ids use the `tp.oracle.` prefix and oracle results are evidence level L2 (registry 10).

| File | Role |
|---|---|
| `VERSION.py` | `ORACLE_VERSION = "oracle-1.0"`. |
| `inputs.py` | The oracle's private working copy of a step (the step's `.tf` files, the oracle-only provider block, `terraform.tfvars.json` from one value set) and the offline Terraform environment (D5-04). |
| `plan.py` | `Runner`: `terraform init`, `validate -json`, `plan`, `show -json` of one working copy, offline (D5-04, D5-13). |
| `model.py` | The configuration as the registry sees it, read from plan JSON (registry 2.1 to 2.3; rules M-INST to M-SET below). |
| `moves.py` | `moved` blocks read from the step's `.tf` files (the D5-13 exception) and the implicit `count` move (2.3). |
| `common.py` | Result values and combination (2.4), CIDRs and protocols (2.5), the relevant-unsupported lists (2.7). |
| `rules.py` | The canonical security-group rule set: inline-rule forms, MIXED, RETAINED-INLINE, pseudo-groups (2.6). |
| `sec_public_ingress.py` | INV-SEC-001 (p = 22) and INV-SEC-002 (p = 5432), registry 3 and 4. |
| `sec_rds_public.py` | INV-SEC-003, registry 5. |
| `func_reach.py` | INV-FUNC-001, registry 6. |
| `footprint.py` | Footprints, `oracle_affected` and the completeness property (2.9, 3.5, 5.4, 6.6; D5-16). |
| `evaluate.py` | One step (2.8 validate failure, 2.4 VERIFIER_ERROR) and a trajectory (parent = step k - 1, D5-15; endpoints followed across moves). |
| `label.py` | `gt_class` (D5-11), `target_safe` (D5-17), the S0 gate (D5-21), the invariance comparison (D5-18). |
| `record.py` | The D0 Decision 6 `labels` and `oracle` structures. |

## Plan-JSON mapping rules (D5-13)

Each rule maps a field of `terraform show -json` (Terraform 1.15.8, provider `hashicorp/aws` 6.53.0) to a registry concept.

| Rule | Plan JSON | Registry concept | Section |
|---|---|---|---|
| M-INST | `resource_changes[]` with `mode = "managed"`: one entry per resource instance, full address (module path and instance key included) | Resource instances; `count` and `for_each` expansion (an expansion the plan cannot resolve fails the plan, so no instance is indeterminate by expansion) | 2.3 |
| M-MODULE | `configuration.root_module.module_calls[].source` | A resource in a non-local module source (not `./` or `../`) is unresolved; a local child module is evaluated as if inlined, under its full module address | 2.2 "Modules" |
| M-KNOWN | `change.after.<attr>` when `change.after_unknown.<attr>` marks nothing in it unknown; for lists of nested objects (inline rules, routes), per element and per field | A resolved value (literals, variables, locals, functions, references to configured arguments, all already evaluated by Terraform) | 2.2 |
| M-WRITTEN | An attribute unknown in `after_unknown` with no key in `configuration...expressions` | Not written: *absent* (for example `aws_db_instance.port`, `aws_instance.private_ip`, `source_security_group_id`, `security_groups` on an instance, an unset `route` or `propagating_vgws`) | 2.2; D1 V01, V07 |
| M-IDREF | An unknown attribute whose `expressions.<attr>.references` are only `<resource>.id` (and the bare `<resource>`) of configured instances | An identity reference to those instances; a scalar needs exactly one | 2.2 "Identity references" |
| M-LITERAL | A known ID string (`sg-...`, `vpc-...`, `subnet-...`) | An external reference: it names no configured resource (configured IDs are unknown at plan time) | 2.2 "External literal IDs" |
| M-SET | A set holding an unknown element is wholly unknown in plan JSON | An identity-reference list is taken as exactly its identity references (a literal written next to a reference is not visible; D5-13 gap c) | 2.2 |
| M-UNRES | Any other unknown value, and any reference through `var.*`, `local.*`, `each.*`, `count.*`, `data.*` or a non-`id` attribute whose value is unknown | Unresolved (D5-13 gap d) | 2.2 "Unresolved" |
| M-FORM | `expressions.ingress` / `.egress` (an empty constant or known empty list: *explicit empty*; otherwise *blocks*); with no expression (not written, or only `dynamic` blocks, which plan JSON omits): a known non-empty planned list is *blocks*, a known empty list is `dynamic_empty` (recorded as an ambiguity), null or unknown is *absent* | Inline-rule forms | 2.6 (C-84); D5-13 gap a |
| M-INLINE | `change.after.ingress[i]` / `.egress[i]` with `after_unknown` per block; an unknown `security_groups` gets the groups named in `expressions.<direction>.references` only when one block is unknown or one group is named, else it is unresolved | `In(g)` / `Out(g)` inline rules | 2.6; D5-13 gap b |
| M-RULE | `aws_security_group_rule`: `type`, `protocol` (normalised by the provider, compared case-insensitively), `from_port`, `to_port`, `cidr_blocks`, `ipv6_cidr_blocks`, `prefix_list_ids`, `self`, and `security_group_id`, `source_security_group_id` by M-IDREF / M-LITERAL | Canonical rule; `security_group_id` that is literal or unresolved gives the pseudo-group `literal:<id>` or `UNRESOLVED:<rule address>` | 2.5, 2.6 |
| M-VALIDATE | `terraform validate -json` `valid = false` | Every invariant UNSUPPORTED | 2.8 |
| M-ERROR | A plan JSON document that cannot be read, or any exception in an evaluator | VERIFIER_ERROR for the invariant concerned, and nothing else | 2.4 |
| M-MOVED | `moved { from, to }` blocks of the step's `.tf` files (not in plan JSON; decided by the authors on 10 Nov 2026, D5-13); implicit `x` to `x[0]` (and back) when `count` is added or removed | Moves, followed when comparing two configurations and for the endpoints | 2.3 (C-76), 6.1 |
| M-ROUTE | `aws_route_table.route[i]`: `cidr_block` (IPv4 destination) and `gateway_id == "local"` | M3: a route inside the VPC CIDR with a non-local target | 6.2 M3 |
| M-PRESENT | Resource types among the instances (M-INST) | Presence of a relevant-unsupported type | 2.7 |

## Assumptions recorded in the evidence

Each result carries an `assumptions` list (registry 2.10): for INV-FUNC-001, M1 (C-15, C-77: VPC(D) from D's security groups), M4 (default network ACL when no NACL-related type is present), M5 (IPv4 only), and `aws_db_subnet_group` tolerated when present (2.7); for INV-SEC-001/002, the relevant-unsupported list and the v1 limit on coverage split across groups; for INV-SEC-003, absent `publicly_accessible` is false (5.2). A case the registry does not settle is never PASS and is listed in the result's `ambiguities`; the labelling run stops while any is open (D5b work package).

## Rules (enforced by `tests/test_independence.py`, D5-03)

- Files under `oracle/` import only the Python standard library and `oracle` itself. They import nothing from `generator/`, `pool/`, `sources/`, `tests/` or `tools/`, and they do not edit `sys.path`. The generator's `realworld/modread.py` and the tests' self-check evaluators are never imported.
- Nothing outside `oracle/` and `tools/` writes a non-null `labels`, `gt_class` or `oracle` field.

## Offline runs (D5-04)

Terraform runs with a provider block that has placeholder keys built at run time (never real, not credential-shaped), the four `skip_*` flags and `max_retries = 1`; no AWS environment variables, and empty shared credentials and config files; the instance metadata service disabled; a CLI configuration that installs `hashicorp/aws` 6.53.0 only from the local filesystem mirror; HTTP(S) proxies set to a closed local port. Any attempt to reach an AWS endpoint therefore fails on this machine and is recorded as a failure, not worked around.
