# D5 carry-over

Facts that D5 (the oracle and ground-truth labelling) inherits from D4a (controlled tier scenario generation). Facts only: each item cites the committed file that shows it, and decides nothing. Where a value was not measured the item says `not yet established`.

## 1. Controlled tier scenarios generated (`scenarios/`)

- Total controlled scenarios generated: 208 (160 primary targets + 48 reserves).
- Split assignment: 70/30 split assigned strictly by template lineage (`scenarios/split.json`):
  - 144 dev scenarios (112 targets + 32 reserves) committed under `scenarios/dev/tp-v1-<FAMILY>-<ID>/`.
  - 64 test scenarios (48 targets + 16 reserves) withheld outside Git in `$TERRAPRESERVE_PRIVATE` (default `~/.terrapreserve-private`), represented by `scenarios/test_manifest.json` (SHA-256 hashes of `scenario.json` and each step directory).
- Step structure: each scenario directory contains `scenario.json`, `step_0` (base state S0), and ordered remediation steps (`step_1`, and up to `step_4` for multi-step family F8).
- Step files: each step directory contains complete `.tf` files (`main.tf`, `variables.tf`, `versions.tf`), fully self-contained.
- Total steps across all 208 scenarios: 466 steps.
- Validation: 466 of 466 steps validated as `valid` under Terraform 1.15.8 and `hashicorp/aws` 6.53.0 mirror (`scenarios/validate_results.csv`).

## 2. Invariants and targets (`generator/model.py`, `generator/templates/`)

Four protected invariants are tracked per scenario (`scenario.json:protected_invariants`):
- `INV-SEC-001` (v1.0): No security-group ingress from `0.0.0.0/0` or `::/0` to port 22.
- `INV-SEC-002` (v1.0): No security-group ingress from `0.0.0.0/0` or `::/0` to database port 5432.
- `INV-SEC-003` (v1.0): `aws_db_instance.publicly_accessible` is false.
- `INV-FUNC-001` (v1.0): EC2 can reach RDS on TCP/5432 (configuration-level route and SG rules).

Base state S0 invariants:
- Clean templates satisfy all four invariants.
- Pre-violated templates for repair families (F2, F4, F8) violate exactly one target invariant in S0 (`INV-SEC-001`, `INV-SEC-002`, or `INV-SEC-003`), while satisfying all other invariants.

## 3. What D5 must label (ADR-010, D0 Decision 6)

For every step $k$ ($k \ge 0$) of every scenario (both dev and test splits):
1. **`invariant_truth`**: Mapping of each invariant ID to `{PASS, FAIL, UNKNOWN, UNSUPPORTED}`.
2. **`oracle_affected`**: Invariants whose truth changed between step 0 and step $k$.
3. **`target_safe`**: Whether the remediation change preserves or achieves safety without regressions.
4. **`gt_class`**: Ground-truth classification (`safe` | `unsafe`), populated by the oracle, not by generator intent.

The generator records an intended class (`intent.class`) and truthful mutation records (`mutation_record`), but sets `gt_class = null`, `labels = null`, and `oracle = null`. D5 provides the authoritative ground truth.

## 4. Real-world tier notice (D4b)

D4b delivers the 160 real-world targets (+ 48 reserves) by grafting onto pooled hosts (derived natives are out of v1.0, D4b-14):
- 208 real-world scenarios generated (144 dev, 64 test) across 16 cells.
- 208 host modules (grafted with standalone core prefixed `tp_`), each passing the whole-module S0 screen (D4b-15).
- 0 original native modules (module `631897` uses variable references for attributes, failing literal-span preconditions).
- 0 derived native modules: the 5 derived natives are out of v1.0 (D4b-14; reasons in `pool/DERIVED_REPORT.md`).
- Scope addresses: each scenario keeps `scope_addresses` as metadata only (for grafts: graft resources). It no longer limits any invariant (D4b-15).
- S0 eligibility screen: every host module is screened as a whole (D4b-15); the graft is clean except for the repair target (`s0_screen`).
- Decisions and Open items:
  - Open 1 (Graft attachment): Standalone network core used in v1.0.
  - Open 2 (Invariant scope on real-world modules): Decided by D4b-15 (9 Nov 2026). The oracle evaluates the security invariants over the whole module, host files and graft together, as registry v1.0 C-64 says ("every security group is in scope, attached or not"); the registry is not amended. The generator's S0 screen and the round-5 tests read the whole module the same way (`generator/realworld/modread.py`, a self-check, not the oracle).
- Total dataset across both tiers: 416 scenarios (320 targets + 96 reserves: 288 dev, 128 test). D5 will label both tiers using the unified oracle suite.


## 5. Generator intent for the D5 comparison (review round 4, generator `d4a-4` and `d4b-4`)

Facts for D5 so that oracle labels can be compared with generator intent and every disagreement reported. Decides nothing; D5 labels come from the oracle only (`oracle/`, ADR-010).

- Generator versions: controlled tier `d4a-7`, real-world tier `d4b-8` (`generator/VERSION.py`, `generator/realworld/generate_rw.py`). The operators are unchanged since `d4a-4` and `d4b-5`; D5a added `variable_values` (vv-1); D5a-2 replaced it by the two vv-2 value sets (D5-07) and turned real-world data blocks into variables (D5-08); D5a-3 replaced vv-2 by vv-3 (D5-10) and added `excluded_from_v1` (D5-09), step files unchanged.
- The generator is designed so that no generated step is UNSUPPORTED or UNKNOWN for INV-FUNC-001 for a reason the generator controls (D4b-13, Open 3; for the real-world screen see the D4c-05 correction in `docs/D4B_DECISIONS.md`: three accepted hosts had a MIXED group or a reversed TCP port range). It never emits `vpc_security_group_ids = []`, never leaves a group MIXED or RETAINED-INLINE, never adds a non-local route inside the VPC CIDR, and never uses an egress or ingress CIDR that only partly covers `CIDR(VPC(D))` or the app subnet. `tests/test_d4b_review_round4.py` checks this with a small self-check evaluator written from registry section 6.3 text (E1 to E6) and section 6.4 rows 1, 2, 3, 6, 8 and 9. That evaluator is not the oracle. If the oracle returns UNSUPPORTED or UNKNOWN for any generated step, that is a disagreement to report.
- Every safe operator is designed to give INV-FUNC-001 = PASS (row 6) on every step. Every unsafe operator that does not list INV-FUNC-001 below is designed to leave INV-FUNC-001 = PASS and to violate the SEC invariant in its `intent.breaks`.
- The INV-FUNC-001-breaking operators, their break mechanism and the registry section 6.4 row they are designed to reach on the last step (`intent.breaks` contains `INV-FUNC-001` for exactly these). Mechanisms: B1 egress port range excluding 5432; B2 egress CIDR disjoint from `CIDR(VPC(D))`; B3 DB group 5432 ingress dropped or moved off 5432; B4 DB group 5432 ingress re-pointed to a group outside `SG(S)`; B5 `aws_db_instance.port` not 5432.

| Operator | Mechanism | Designed row |
|---|---|---|
| `op_f3_app_egress_cidr_unsafe` | B2 | 9 |
| `op_f3_app_egress_ports_unsafe` | B1 | 9 |
| `op_f3_db_ingress_peer_unsafe` | B4 | 9 |
| `op_f4_repair_ssh_break_db_ingress_unsafe` | B3 | 9 |
| `op_f5_separate_to_inline_rules_unsafe` | B3 | 9 |
| `op_f5_db_rule_moved_unsafe` | B4 | 9 |
| `op_f5_db_sg_replacement_unsafe` | B3 | 9 |
| `op_f7_app_egress_cidr_tighten_unsafe` | B2 | 9 |
| `op_f7_app_egress_port_range_unsafe` | B1 | 9 |
| `op_f7_db_ingress_source_unsafe` | B4 | 9 |
| `op_f8_twostep_repair_unsafe` | B3 | 9 |
| `op_f8_threestep_refactor_repair_unsafe` | B5 | 3 |
| `op_f8_fourstep_maintenance_unsafe` | B2 | 9 |

- For F3, F5 and F7 the break is made through a security group or security group rule; no mutation row of those scenarios is on the `aws_instance` or `aws_db_instance` endpoint (D4b-13).
- The F1 unsafe operators break INV-SEC-003, INV-SEC-002 and INV-SEC-001 (one each: resize, storage expansion, VPC DNS toggle). The F2 unsafe operators leave the target SEC invariant violated through `ipv6_cidr_blocks = ["::/0"]` (SSH and DB ingress) or an untouched `publicly_accessible = true`; in review round 4 an earlier defect was found where they repaired the target instead (a `"safe" in name` test also matches `unsafe`).
- Direction of F5 restructuring: only separate rules to inline blocks is generated. Inline blocks to separate rules leaves the group RETAINED-INLINE (registry section 2.6, row 2, D0 amendment A10).
- The self-check evaluator treats the DNS settings as irrelevant, as the registry does. An AWS calibration run could still diverge on DNS-dependent behaviour (for example a name that does not resolve with `enable_dns_hostnames = false`); the generator never sets `enable_dns_support = false` in a safe variant.

## 6. Whole-module reader conventions and open D5 inputs (after review round 5)

The real-world S0 screen (`generator/realworld/screen.py`) and the round-5 tests (`tests/test_d4b_review_round5.py`) share one reader, `generator/realworld/modread.py`. It is a generator self-check, not the oracle. Its conventions are listed here so that the oracle's results can be compared with them. Where the oracle differs, the difference is a finding to report, not a reason to change the oracle.

### 6.1 Reader conventions (conservative; the registry is not amended)

- **Indeterminacy follows registry v1.0.** Sections 3.3 and 3.4 (`possible4` / `possible6` for TCP 22 and 5432), 5.4 (unresolved `publicly_accessible`) and 6.4 row 7 (an indeterminate rule that could permit TCP/5432 in SG(S), SG(D) or a pseudo-group). An unresolved value that cannot affect any of the four results never rejects a module.
- **Pseudo-groups.** A rule whose `security_group_id` does not resolve to a configured `aws_security_group` belongs to the pseudo-group `UNRESOLVED:<rule address>` (registry 3.3). A literal group id (for example `"sg-..."`) is also treated as a pseudo-group.
- **Pseudo-group rules count in any direction for INV-FUNC-001 (6.4 row 7).** An indeterminate pseudo-group rule that could permit TCP/5432 counts whether its type is ingress, egress or unresolved, because its target could be in SG(S) or SG(D).
- **Type-unresolved rules.** A rule whose `type` is unresolved counts as a possible ingress rule (registry 3.3). The reader also treats such a rule as possible when its resolved sources include `0.0.0.0/0` or `::/0`. This goes one step past the quoted formula, which names only unresolved sources. On the d4b-5 pool it never decided a rejection.
- **Prefix lists.** A non-empty `prefix_list_ids` counts as an unresolved source (registry 3.3 "include a prefix list"), for IPv4 and IPv6.
- **`count` and `for_each`.** Resources expanded by `count` or `for_each` are assumed to exist, so a violation is counted as if the resource were created. A `count` that resolves to the literal `0` removes the resource.
- **`dynamic` blocks.** A `dynamic "ingress"` or `dynamic "egress"` block whose `for_each` resolves is expanded. One whose `for_each` does not resolve becomes one fully unresolved rule in that direction.
- **What resolves:**
  - literals, lists and objects of literals;
  - `var.<name>` with a resolvable `default`;
  - `local.<name>`;
  - `aws_security_group.<name>.id` (indexes allowed);
  - `aws_vpc.<name>.cidr_block` and `aws_subnet.<name>.cidr_block` with a resolvable `cidr_block`;
  - quoted integer ports such as `"22"`;
  - the strings `"true"` and `"false"` for booleans.

  Everything else (`each.*`, `data.*`, `module.*`, functions, conditionals, variables without a default) is unresolved.
- **Equivalent public scope (C-64).** The CIDRs of a group's rules that permit port *p* are taken together. `0.0.0.0/1` plus `128.0.0.0/1` covers `0.0.0.0/0`.
- **Row order.** The self-check evaluator applies registry 6.4 "first row that applies wins": row 2 (an endpoint without `vpc_security_group_ids`) is checked before row 3 (E2).

### 6.2 Variable values: D5 must decide how the oracle gets them

**Update (D5a-3, D5-09 and D5-10):** every `scenario.json` now carries rule `vv-3`: the two vv-2 value sets, with a rejected declared default overridden (`reason` in `variable_values_kinds`), the candidate index taken per variable and set (`variable_values_candidates`), and `excluded_from_v1` (`null`, or `{reason, failing_steps, first_error}`). The values come from the recorded search result (`generator/vv3/dev.json`; the test split's in `$TERRAPRESERVE_PRIVATE/vv3_test.json`). Every step of every non-excluded scenario produces plan JSON under both sets; the D5a-3 part of `docs/D5A_FEASIBILITY.md` has the counts. For D5b and D6:
- **Excluded from v1.0 (D5-09, one bounded fix round; no second round):** dev 16 of 288 scenarios (all real-world): tp-v1-F1-0219, tp-v1-F1-0220, tp-v1-F1-0228, tp-v1-F2-0254, tp-v1-F3-0266, tp-v1-F3-0271, tp-v1-F3-0284, tp-v1-F5-0327, tp-v1-F5-0330, tp-v1-F5-0337, tp-v1-F6-0342, tp-v1-F6-0344, tp-v1-F7-0369, tp-v1-F7-0378, tp-v1-F8-0393, tp-v1-F8-0406 (reasons in each `scenario.json` and in `docs/D5A_FEASIBILITY.md` D5a-3.5); test 6 of 128 (all real-world; counts only). No controlled scenario is excluded.
- **Yields:** dev real-world 11 excluded targets and 5 excluded reserves of 112 and 32; test real-world 4 and 2 of 48 and 16; controlled tier none. Per cell (family x class x split x tier) in `docs/D5A_FEASIBILITY.md` D5a-3.6. D6 fills targets from the same cell's reserves only; one cell is short and is reported, not padded: F5 x unsafe x dev x real_world (short by 1).
- The oracle (D5b) skips scenarios with `excluded_from_v1` set; the target/reserve assignment in `scenarios/ASSEMBLY.json` is unchanged (D6's job).

**Update (D5a-2, D5-05 to D5-08):** every `scenario.json` now carries two value sets under rule `vv-2`: `variable_values` (primary) and `variable_values_alt` (alternate), with `variable_values_kinds` (kind and evidence per variable) and `variable_values_unresolved` (status `unresolved` or `conflict`, with the reason). The real-world tier has no `data` block left: each became a `tp_ds_*` variable (D5-08, recorded in `host_transform`), valued in both sets. For D5b: the oracle reads plan JSON only (D5-05), runs every scenario once per value set, and a scenario whose oracle labels differ between the two sets depends on an invented value and is excluded from v1.0 (D5-06, the invariance test; D6 fills from reserves and reports the count). Whether every step plans under both sets is measured in `docs/D5A_FEASIBILITY.md` (D5a-2 part). Not every step does: all controlled steps plan under both sets, but some real-world steps fail with variable errors (counts and dev ids there); D5a-2 stopped at that point, and Open D5-C in `docs/D5_DECISIONS.md` is for the authors to decide before D5b.

**Update (D5a, D5-01, superseded by D5-07):** D5a added `variable_values` under rule `vv-1`, with `variable_values_unresolved` for variables the rule could not satisfy. The text below records the state at `5fc927e`.

At `5fc927e`, no scenario carried variable values. No `scenario.json` had a values field, and no step has a `.tfvars` file. Registry 2.2 evaluates "with the scenario's variable values", so D5 must decide how these are supplied before the oracle runs. This matters in particular for any `terraform plan` path.

Measured with `generator/realworld/modread.py` over every step of `scenarios/dev/` at the merge commit `5fc927e`:

| Tier | Dev scenarios | With at least one variable that has no default |
|---|---|---|
| Controlled | 144 | 144 (for example `db_password`) |
| Real-world, whole module | 144 | 144 (every graft declares `tp_db_password` with no default) |
| Real-world, host files only | 144 | 95 (for example `vpc_id`, `environment`, `project_name`) |

The external review of PR #6 reported 125 of 144 for the real-world tier; the reviewer has since confirmed that figure came from a faulty block scan and that 144 of 144 (whole module) is correct. The test split was not measured for this item.


## 7. D6 carry-over (from D5b)

Figures below are from `docs/D5_REPORT.md` (computed by `tools/report_d5b.py`); test split as counts only.

- **Labels are in place.** Dev: `labels`, `gt_class` and `oracle` (D0 gate 9 versions; Checkov disagreements) in each `scenarios/dev/<id>/scenario.json`; 269 of 288 labelled (135 safe, 134 unsafe). Test: written only under `$TERRAPRESERVE_PRIVATE`, 122 of 128 labelled (61 safe, 61 unsafe); `scenarios/test_manifest.json` carries the new hashes. The oracle's run records (both value sets, evidence) are outside the repository (`~/.terrapreserve-cache/d5b-records`, `$TERRAPRESERVE_PRIVATE/d5b-records`).
- **Regeneration resets labels.** `generator/generate.py` and `generator/realworld/generate_rw.py` write `labels`, `gt_class` and `oracle` as null. Any regeneration in D6 must be followed by `tools/label_d5b.py --plans` and `--label --write` (and `tools/report_d5b.py`).
- **Exclusions from v1.0.** Dev: 16 `unplannable` (D5a-3) and 3 `s0_not_clean` (tp-v1-F2-0250, tp-v1-F2-0252, tp-v1-F3-0263), all real-world; test: 6 `unplannable`. No `value_dependent` and no `unlabelable` scenario in either split.
- **Fill (D0 Decision 3, D5-09 amended).** By oracle gt_class, three dev real-world cells are short by 1 each: F2 x unsafe, F3 x safe, F5 x unsafe; each same-cell controlled surplus is 2. No test cell is short. D6 fills from the same cell's reserves first, then from controlled scenarios of the same family x class x split, and reports the actual counts.
- **Generator self-check findings (reported, not fixed in D5b).** The D4b whole-module reader (`generator/realworld/modread.py`) accepted three hosts that the oracle finds UNSUPPORTED at step 0: it has no registry 2.5 rule for TCP `from_port > to_port` (tp-v1-F2-0250: `from_port = 443`, `to_port = 22`), and it marks a group MIXED only when the inline blocks and the separate `aws_security_group_rule` have the same direction, whereas registry 2.6 needs only one of each (tp-v1-F2-0252, tp-v1-F3-0263: inline `egress` with separate ingress rules). No other disagreement between the self-checks and the oracle (per step, both splits).
- **Intent.** No disagreement between oracle gt_class and `intent.class`, nor between the invariants FAIL and `intent.breaks` (both splits).
- **Checkov (advisory).** INV-SEC-001: oracle PASS, Checkov FAIL on 3 dev and 2 test steps; in the dev cases a TCP 22 inline ingress block has no source at all (no CIDR, no group), which registry 3.4 does not count as public. No other disagreement.
- **DAIL follow-up:** add a wording clarification of registry §2.9 in a new INVARIANT_REGISTRY_v1.1.md (C-85) so DAIL and the oracle read footprint comparison the same way; predicates and results unchanged.

## 8. D6 carry-over (from D4c)

Figures from `docs/D5_REPORT.md` (computed part) and `generator/templates/FEATURES.md`; test split as counts only.

- **Controlled tier replaced (D4c-01 to D4c-04).** 33 templates (`tpl-v2.0`, generator `d4a-9`), 23 dev and 10 test (10 test clusters); 208 scenarios with the D4-04 counts per cell; no controlled id changed side. D4-03, D4-04 and D4-05 are `Superseded` by D4c-01, D4c-03 and D4c-04.
- **Controlled relabel (D4c-06).** `oracle-1.0`, both value sets, D5 rules unchanged: dev 144 of 144 labelled, test 64 of 64; no exclusion; gt_class equals `intent.class` in every controlled cell; no intent, self-check or Checkov disagreement in the controlled tier. Overall: dev 269 of 288 labelled (135 safe, 134 unsafe), test 122 of 128 (61 safe, 61 unsafe), as after D5b.
- **Fill (D0 Decision 3).** Unchanged: dev real-world F2 x unsafe, F3 x safe and F5 x unsafe are each short by 1; the same-cell controlled surplus is 2 in each (dev controlled cells have 9 labelled for 7 targets). No test cell is short. D6 fills; D4c did not.
- **Self-check fixed in the generator only (D4c-05).** `generator/realworld/modread.py` now reads MIXED in any direction and flags TCP `from_port > to_port` (`RW-S0-UNSUP-RULE`). Re-running the screen on the unchanged real-world tier changes only tp-v1-F2-0250, tp-v1-F2-0252 and tp-v1-F3-0263 (already excluded); no test-split scenario changes. The committed real-world tier was generated with the old reader: regenerating it (`generator/realworld/generate_rw.py`) would now reject those 3 hosts and change the tier, so D6 should either keep the tier as committed or regenerate and relabel it deliberately.
- **Corrected claims.** `DATASHEET.md` and `docs/D4B_DECISIONS.md` no longer say the screen guaranteed no MIXED group (D4c-05 correction).
- **Run records.** The controlled run records in `~/.terrapreserve-cache/d5b-records` (and `$TERRAPRESERVE_PRIVATE/d5b-records`) are now those of the D4c relabel; D6 archives all run records with a recorded hash (external review of PR #10, limit 4).
- **Generator fix found in D4c.** `generator/generate.py` read `scenarios/test_manifest.json` (a JSON list) as an object inside a bare `except`, which would have dropped the 64 real-world test entries on a controlled-only regeneration; it now reads the list and stops on a read error.
