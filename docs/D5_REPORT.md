# D5 report: the oracle and the labelling run (D5b)

Work package D5b (queue step 17, final part). Branch `feature/d5b-oracle-labels`, PRs #9 and #10; the controlled tier was relabelled in D4c (section below). This part is written by hand and explains the method; every id, count and status is in the computed part below the marker, written by `tools/report_d5b.py` from the repository, the oracle's run records and (counts only) the withheld test split.

## Method

- **Oracle.** `oracle/` at `oracle-1.0`, written from the Invariant Registry Specification (DAIL `docs/specs/INVARIANT_REGISTRY_v1.md`, tag `registry-v1.0`), Terraform semantics and AWS semantics (CLAUDE.md rule 7, ADR-010). It reads `terraform show -json` of an offline plan of each step (D5-04, D5-05, D5-13) and, by the authors' decision of 10 Nov 2026, the `moved` blocks of the step's `.tf` files (D5-13). Mapping rules: `oracle/README.md`. Footprint comparison as decided in Open D5-D; merged inline security-group references as decided in D5-22.
- **Registry tests.** `tests/test_d5b_oracle_registry.py`: every section 8 conformance vector and the section 6.5 worked cases, plus the further rules of the work package and D5-22, from committed plan-JSON fixtures (`tests/fixtures/oracle/`, produced once by `tools/make_oracle_fixtures.py`); they run without Terraform. Each test was run red before its code (Step 2 and D5-22).
- **Plans.** `tools/label_d5b.py --plans --include-excluded`: every step of every scenario of both splits, under both value sets (D5-06), offline, cached outside the repository (dev: `~/.terrapreserve-cache/d5b-plans`; test: `$TERRAPRESERVE_PRIVATE/d5b-plans`). The plan status of every step is compared with D5a-3's measurement (A5) before any label is decided.
- **Labels.** `tools/label_d5b.py --label --write`: for each scenario D5a-3 did not exclude, the oracle evaluates every step under both value sets (parent = step k - 1, D5-15); then, in this order, the endpoint binding (D5-12), the completeness property and ambiguities (stop if any), the invariance test (D5-18, `value_dependent`), the S0 gate (D5-21, `s0_not_clean`) and gt_class (D5-11, `unlabelable` when null). Checkov 3.3.30 runs on every step of every labelled scenario with `CKV_AWS_24`, `CKV_AWS_277` (INV-SEC-001) and `CKV_AWS_17` (INV-SEC-003) on a pristine copy of the step's `.tf` files, as in D5a; its disagreements are recorded in `oracle.disagreements` and never change a label (D5-19). Labels are written per D5-20 (dev into `scenario.json`; test only under `$TERRAPRESERVE_PRIVATE`, with the hashes in `scenarios/test_manifest.json`). The oracle's run records (both value sets' results, observations, assumptions, evidence) are kept outside the repository (dev: `~/.terrapreserve-cache/d5b-records`; test: `$TERRAPRESERVE_PRIVATE/d5b-records`).
- **Comparisons (Step 7).** Intent: oracle gt_class against `intent.class`, and the invariants FAIL at the last step (F8: any step k >= 1) against `intent.breaks`. Generator self-check: the D4b round-4/5 evaluators (`tests/test_d4b_review_round4.py`, `generator/realworld/modread.py`) against the oracle per step. Both are reports only: the oracle's label stands and the generator is not changed in D5b.
- **Earlier records kept.** `docs/d5b/dry_run.json` (Step 5) and `docs/d5b/scan_dev.json` (the dev scan before Open D5-D and D5-22 were decided) are kept as they were produced; the run below supersedes them.

## Controlled relabel (D4c)

Work package D4c (branch `feature/d4c-templates`) replaced the controlled tier: 33 templates instead of 10, a 23/10 template split, generator `d4a-9`, template set `tpl-v2.0` (`docs/D4C_DECISIONS.md`). No controlled scenario id changed side, and the real-world tier is byte-identical to `49837f2` (files, labels, test-manifest entries, validation rows, vv-3 search entries). The controlled tier was relabelled with the same oracle (`oracle-1.0`) and the same D5 rules (D4c-06):

- **Values and feasibility.** `tools/search_vv3.py --redo-controlled` searched the controlled tier again (both splits): every scenario plans under both sets with candidate index 0 and no override (as before D4c). `tools/run_d5a_feasibility.py --run d5a3 --redo-controlled` re-measured the controlled rows of the D5a-3 feasibility files under both sets; real-world rows are unchanged.
- **Plans and labels.** `tools/label_d5b.py --plans|--label [--write] --tier controlled`. A cached plan or Checkov run of a controlled step is used only when it records the step's `content_hash` (D4c-06), so no pre-D4c run was reused. Six dev plan runs ended as timeouts recording about 27,100 s of wall time (the machine was suspended overnight during the run); their cached results were deleted and the six steps planned again, all successfully, before any label was decided.
- **Self-check comparison.** Since D4c the self-check reader is the fixed one (D4c-05). With it the self-check agrees with the oracle on every step of both tiers; with the reader of `49837f2`, D5b found the three self-check misses F2-0250, F2-0252 and F3-0263 (steps 0 and 1).
- The computed part below covers both tiers: the real-world figures are those of D5b (unchanged), the controlled figures those of the D4c relabel; its last section lists the D4c specifics (per-template counts, F5 SG-name replacement usage).

<!-- computed below by tools/report_d5b.py; the part above is written by hand -->

## Computed results (`tools/report_d5b.py`)

Regenerate with `python tools/report_d5b.py` with `TERRAPRESERVE_PRIVATE` set and the run records in place. Test split: counts only.

### Decision rows (`docs/D5_DECISIONS.md`, id and status as written)

D5-01 Superseded; D5-02 Decided; D5-03 Decided; D5-04 Decided; D5-05 Decided; D5-06 Decided; D5-07 Decided; D5-08 Decided; D5-09 Decided; D5-10 Decided; D5-11 Decided; D5-12 Decided; D5-13 Decided; D5-14 Decided; D5-15 Decided; D5-16 Decided; D5-17 Decided; D5-18 Decided; D5-19 Decided; D5-20 Decided; D5-21 Decided; D5-22 Decided; Open D5-A Decided; Open D5-B Decided; Open D5-C Decided; Open D5-D Decided

### Versions recorded in the labels (D0 gate 9)

- dev: 144 scenarios: `{"checkov": "3.3.30", "generator": "d4a-9", "oracle": "oracle-1.0", "provider_hashicorp_aws": "6.53.0", "registry": "registry-v1.0", "terraform": "1.15.8", "value_rule": "vv-3", "value_set": "primary"}`
- dev: 125 scenarios: `{"checkov": "3.3.30", "generator": "d4b-9", "oracle": "oracle-1.0", "provider_hashicorp_aws": "6.53.0", "registry": "registry-v1.0", "terraform": "1.15.8", "value_rule": "vv-3", "value_set": "primary"}`
- test: 64 scenarios: `{"checkov": "3.3.30", "generator": "d4a-9", "oracle": "oracle-1.0", "provider_hashicorp_aws": "6.53.0", "registry": "registry-v1.0", "terraform": "1.15.8", "value_rule": "vv-3", "value_set": "primary"}`
- test: 58 scenarios: `{"checkov": "3.3.30", "generator": "d4b-9", "oracle": "oracle-1.0", "provider_hashicorp_aws": "6.53.0", "registry": "registry-v1.0", "terraform": "1.15.8", "value_rule": "vv-3", "value_set": "primary"}`

### A5: plannable set against D5a-3

D5b run (both tiers; its controlled part is superseded by the D4c relabel below, its real-world part stands because the real-world tier is unchanged):

- dev: {'alternate failure': 35, 'alternate success': 617, 'primary failure': 35, 'primary success': 617}; differences from D5a-3: 0
- test: {'alternate failure': 12, 'alternate success': 271, 'primary failure': 10, 'primary success': 273}; differences from D5a-3: 0

D4c relabel of the controlled tier (D4c-06; D5a-3 feasibility re-measured for the controlled tier):

- dev controlled: {'alternate success': 324, 'primary success': 324}; differences from D5a-3: 0
- test controlled: {'alternate success': 138, 'primary success': 138}; differences from D5a-3: 0

### Steps labelled (each under both value sets, D5-18)

| split | tier | scenarios labelled | steps labelled per value set | steps evaluated per value set |
|---|---|---|---|---|
| dev | controlled | 144 | 324 | 324 |
| dev | real_world | 125 | 283 | 289 |
| test | controlled | 64 | 138 | 138 |
| test | real_world | 58 | 133 | 133 |

### Exclusions by reason (D5-20; dev ids, test counts)

- dev unplannable: 16: tp-v1-F1-0219 (real_world), tp-v1-F1-0220 (real_world), tp-v1-F1-0228 (real_world), tp-v1-F2-0254 (real_world), tp-v1-F3-0266 (real_world), tp-v1-F3-0271 (real_world), tp-v1-F3-0284 (real_world), tp-v1-F5-0327 (real_world), tp-v1-F5-0330 (real_world), tp-v1-F5-0337 (real_world), tp-v1-F6-0342 (real_world), tp-v1-F6-0344 (real_world), tp-v1-F7-0369 (real_world), tp-v1-F7-0378 (real_world), tp-v1-F8-0393 (real_world), tp-v1-F8-0406 (real_world)
- dev unlabelable: 0
- dev value_dependent: 0
- dev s0_not_clean: 3: tp-v1-F2-0250 (real_world), tp-v1-F2-0252 (real_world), tp-v1-F3-0263 (real_world)
  - tp-v1-F2-0250: step 0: INV-SEC-001 UNSUPPORTED
  - tp-v1-F2-0252: step 0: INV-SEC-002 UNSUPPORTED
  - tp-v1-F3-0263: step 0: INV-SEC-001 UNSUPPORTED; INV-SEC-002 UNSUPPORTED
- test unplannable: 6 ({'real_world': 6})
- test unlabelable: 0 ({})
- test value_dependent: 0 ({})
- test s0_not_clean: 0 ({})

### gt_class per family x intent class x split x tier

| family | intent class | split | tier | scenarios | gt safe | gt unsafe | excluded |
|---|---|---|---|---|---|---|---|
| F1 | safe | dev | controlled | 9 | 9 | 0 | 0 |
| F1 | safe | dev | real_world | 9 | 7 | 0 | 2 |
| F1 | safe | test | controlled | 4 | 4 | 0 | 0 |
| F1 | safe | test | real_world | 4 | 4 | 0 | 0 |
| F1 | unsafe | dev | controlled | 9 | 0 | 9 | 0 |
| F1 | unsafe | dev | real_world | 9 | 0 | 8 | 1 |
| F1 | unsafe | test | controlled | 4 | 0 | 4 | 0 |
| F1 | unsafe | test | real_world | 4 | 0 | 3 | 1 |
| F2 | safe | dev | controlled | 9 | 9 | 0 | 0 |
| F2 | safe | dev | real_world | 9 | 9 | 0 | 0 |
| F2 | safe | test | controlled | 4 | 4 | 0 | 0 |
| F2 | safe | test | real_world | 4 | 4 | 0 | 0 |
| F2 | unsafe | dev | controlled | 9 | 0 | 9 | 0 |
| F2 | unsafe | dev | real_world | 9 | 0 | 6 | 3 |
| F2 | unsafe | test | controlled | 4 | 0 | 4 | 0 |
| F2 | unsafe | test | real_world | 4 | 0 | 4 | 0 |
| F3 | safe | dev | controlled | 9 | 9 | 0 | 0 |
| F3 | safe | dev | real_world | 9 | 6 | 0 | 3 |
| F3 | safe | test | controlled | 4 | 4 | 0 | 0 |
| F3 | safe | test | real_world | 4 | 3 | 0 | 1 |
| F3 | unsafe | dev | controlled | 9 | 0 | 9 | 0 |
| F3 | unsafe | dev | real_world | 9 | 0 | 8 | 1 |
| F3 | unsafe | test | controlled | 4 | 0 | 4 | 0 |
| F3 | unsafe | test | real_world | 4 | 0 | 3 | 1 |
| F4 | safe | dev | controlled | 9 | 9 | 0 | 0 |
| F4 | safe | dev | real_world | 9 | 9 | 0 | 0 |
| F4 | safe | test | controlled | 4 | 4 | 0 | 0 |
| F4 | safe | test | real_world | 4 | 4 | 0 | 0 |
| F4 | unsafe | dev | controlled | 9 | 0 | 9 | 0 |
| F4 | unsafe | dev | real_world | 9 | 0 | 9 | 0 |
| F4 | unsafe | test | controlled | 4 | 0 | 4 | 0 |
| F4 | unsafe | test | real_world | 4 | 0 | 4 | 0 |
| F5 | safe | dev | controlled | 9 | 9 | 0 | 0 |
| F5 | safe | dev | real_world | 9 | 9 | 0 | 0 |
| F5 | safe | test | controlled | 4 | 4 | 0 | 0 |
| F5 | safe | test | real_world | 4 | 3 | 0 | 1 |
| F5 | unsafe | dev | controlled | 9 | 0 | 9 | 0 |
| F5 | unsafe | dev | real_world | 9 | 0 | 6 | 3 |
| F5 | unsafe | test | controlled | 4 | 0 | 4 | 0 |
| F5 | unsafe | test | real_world | 4 | 0 | 4 | 0 |
| F6 | safe | dev | controlled | 9 | 9 | 0 | 0 |
| F6 | safe | dev | real_world | 9 | 7 | 0 | 2 |
| F6 | safe | test | controlled | 4 | 4 | 0 | 0 |
| F6 | safe | test | real_world | 4 | 3 | 0 | 1 |
| F6 | unsafe | dev | controlled | 9 | 0 | 9 | 0 |
| F6 | unsafe | dev | real_world | 9 | 0 | 9 | 0 |
| F6 | unsafe | test | controlled | 4 | 0 | 4 | 0 |
| F6 | unsafe | test | real_world | 4 | 0 | 4 | 0 |
| F7 | safe | dev | controlled | 9 | 9 | 0 | 0 |
| F7 | safe | dev | real_world | 9 | 8 | 0 | 1 |
| F7 | safe | test | controlled | 4 | 4 | 0 | 0 |
| F7 | safe | test | real_world | 4 | 4 | 0 | 0 |
| F7 | unsafe | dev | controlled | 9 | 0 | 9 | 0 |
| F7 | unsafe | dev | real_world | 9 | 0 | 8 | 1 |
| F7 | unsafe | test | controlled | 4 | 0 | 4 | 0 |
| F7 | unsafe | test | real_world | 4 | 0 | 3 | 1 |
| F8 | safe | dev | controlled | 9 | 9 | 0 | 0 |
| F8 | safe | dev | real_world | 9 | 8 | 0 | 1 |
| F8 | safe | test | controlled | 4 | 4 | 0 | 0 |
| F8 | safe | test | real_world | 4 | 4 | 0 | 0 |
| F8 | unsafe | dev | controlled | 9 | 0 | 9 | 0 |
| F8 | unsafe | dev | real_world | 9 | 0 | 8 | 1 |
| F8 | unsafe | test | controlled | 4 | 0 | 4 | 0 |
| F8 | unsafe | test | real_world | 4 | 0 | 4 | 0 |

- dev total: 288 scenarios, gt safe 135, gt unsafe 134, excluded 19
- test total: 128 scenarios, gt safe 61, gt unsafe 61, excluded 6

### Invariance (D5-18) and S0 gate (D5-21)

- dev: 272 scenarios evaluated under both value sets; value_dependent 0; s0_not_clean 3
- test: 122 scenarios evaluated under both value sets; value_dependent 0; s0_not_clean 0

### Checkov 3.3.30, advisory (D5-19)

- dev: 607 labelled steps; Checkov did not run on 0
- test: 271 labelled steps; Checkov did not run on 0
- dev INV-SEC-001: oracle PASS, Checkov FAIL: 3
- test INV-SEC-001: oracle PASS, Checkov FAIL: 2
- dev examples:
  - tp-v1-F1-0222 step 0 INV-SEC-001: oracle PASS, Checkov FAIL (failed resources ['aws_security_group.main'])
  - tp-v1-F1-0222 step 1 INV-SEC-001: oracle PASS, Checkov FAIL (failed resources ['aws_security_group.main'])
  - tp-v1-F8-0402 step 2 INV-SEC-001: oracle PASS, Checkov FAIL (failed resources ['aws_security_group.vpc_2_sg'])

### Intent comparison (Step 7; the oracle's label stands)

Per labelled scenario: oracle `gt_class` against `intent.class`, and the invariants FAIL at the last step (F8: at any step k >= 1, except the repair target before the last step, as in D5-11) against `intent.breaks`. The reason is the registry condition that fired (3.4, 5.4, 6.4 row) at the step concerned, primary value set.

- disagreements: none (dev and test)

- dev controlled scenarios: 144
- dev real_world scenarios: 125
- test controlled scenarios: 64
- test real_world scenarios: 58

### Generator self-check comparison (Step 7; `docs/D5_CARRYOVER.md` 5: findings to report)

The D4b round-4/5 self-check evaluators against the oracle (primary value set), per step and invariant, over every scenario the oracle evaluated (D5a-3 exclusions left out). Self-check result: INV-SEC-001/002 from `modread.analyse` over all `.tf` files of the step (a violation is FAIL; a MIXED group, a TCP rule with from_port > to_port or a relevant-unsupported type is UNSUPPORTED; `possible` is UNKNOWN; else PASS). Since D4c the reader is the fixed one (D4c-05: registry 2.5 and MIXED in any direction); in D5b, with the reader of 49837f2, F2-0250, F2-0252 and F3-0263 were self-check misses at steps 0 and 1 (oracle UNSUPPORTED, self-check PASS). INV-SEC-003 likewise (unresolved `publicly_accessible` is UNKNOWN); INV-FUNC-001 from `evaluate_func` of round 4 (controlled and grafted scenarios; n/a elsewhere or when it rejects the form).

- dev: no disagreement

- dev controlled INV-FUNC-001 compared: 324
- dev controlled INV-SEC-001 compared: 324
- dev controlled INV-SEC-002 compared: 324
- dev controlled INV-SEC-003 compared: 324
- dev real_world INV-FUNC-001 compared: 289
- dev real_world INV-SEC-001 compared: 289
- dev real_world INV-SEC-002 compared: 289
- dev real_world INV-SEC-003 compared: 289
- test controlled INV-FUNC-001 compared: 138
- test controlled INV-SEC-001 compared: 138
- test controlled INV-SEC-002 compared: 138
- test controlled INV-SEC-003 compared: 138
- test real_world INV-FUNC-001 compared: 133
- test real_world INV-SEC-001 compared: 133
- test real_world INV-SEC-002 compared: 133
- test real_world INV-SEC-003 compared: 133

### Yield table (by oracle gt_class) and the D0 Decision 3 fill

Per family x class x split x tier. *targets*: scenarios assigned as targets (not reserves) with that intent class; *labelled*: scenarios (targets and reserves) whose oracle `gt_class` is that class; *excluded*: by reason, by intent class. *short*: targets minus labelled, when positive. *fill*: for a real-world short cell, the controlled scenarios of the same family x class x split it would need (D0 Decision 3, D5-09 amended); *controlled surplus*: labelled minus targets of that controlled cell. D6 does the filling.

| family | class | split | tier | targets | reserves | labelled | excluded (by reason) | short | fill from controlled | controlled surplus |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 | safe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F1 | safe | dev | real_world | 7 | 2 | 7 | unplannable 2 | 0 | 0 | 2 |
| F1 | safe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F1 | safe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F1 | unsafe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F1 | unsafe | dev | real_world | 7 | 2 | 8 | unplannable 1 | 0 | 0 | 2 |
| F1 | unsafe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F1 | unsafe | test | real_world | 3 | 1 | 3 | unplannable 1 | 0 | 0 | 1 |
| F2 | safe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F2 | safe | dev | real_world | 7 | 2 | 9 | 0 | 0 | 0 | 2 |
| F2 | safe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F2 | safe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F2 | unsafe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F2 | unsafe | dev | real_world | 7 | 2 | 6 | s0_not_clean 2, unplannable 1 | 1 | 1 | 2 |
| F2 | unsafe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F2 | unsafe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F3 | safe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F3 | safe | dev | real_world | 7 | 2 | 6 | s0_not_clean 1, unplannable 2 | 1 | 1 | 2 |
| F3 | safe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F3 | safe | test | real_world | 3 | 1 | 3 | unplannable 1 | 0 | 0 | 1 |
| F3 | unsafe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F3 | unsafe | dev | real_world | 7 | 2 | 8 | unplannable 1 | 0 | 0 | 2 |
| F3 | unsafe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F3 | unsafe | test | real_world | 3 | 1 | 3 | unplannable 1 | 0 | 0 | 1 |
| F4 | safe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F4 | safe | dev | real_world | 7 | 2 | 9 | 0 | 0 | 0 | 2 |
| F4 | safe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F4 | safe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F4 | unsafe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F4 | unsafe | dev | real_world | 7 | 2 | 9 | 0 | 0 | 0 | 2 |
| F4 | unsafe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F4 | unsafe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F5 | safe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F5 | safe | dev | real_world | 7 | 2 | 9 | 0 | 0 | 0 | 2 |
| F5 | safe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F5 | safe | test | real_world | 3 | 1 | 3 | unplannable 1 | 0 | 0 | 1 |
| F5 | unsafe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F5 | unsafe | dev | real_world | 7 | 2 | 6 | unplannable 3 | 1 | 1 | 2 |
| F5 | unsafe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F5 | unsafe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F6 | safe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F6 | safe | dev | real_world | 7 | 2 | 7 | unplannable 2 | 0 | 0 | 2 |
| F6 | safe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F6 | safe | test | real_world | 3 | 1 | 3 | unplannable 1 | 0 | 0 | 1 |
| F6 | unsafe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F6 | unsafe | dev | real_world | 7 | 2 | 9 | 0 | 0 | 0 | 2 |
| F6 | unsafe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F6 | unsafe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F7 | safe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F7 | safe | dev | real_world | 7 | 2 | 8 | unplannable 1 | 0 | 0 | 2 |
| F7 | safe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F7 | safe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F7 | unsafe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F7 | unsafe | dev | real_world | 7 | 2 | 8 | unplannable 1 | 0 | 0 | 2 |
| F7 | unsafe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F7 | unsafe | test | real_world | 3 | 1 | 3 | unplannable 1 | 0 | 0 | 1 |
| F8 | safe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F8 | safe | dev | real_world | 7 | 2 | 8 | unplannable 1 | 0 | 0 | 2 |
| F8 | safe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F8 | safe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |
| F8 | unsafe | dev | controlled | 7 | 2 | 9 | 0 | 0 | - | - |
| F8 | unsafe | dev | real_world | 7 | 2 | 8 | unplannable 1 | 0 | 0 | 2 |
| F8 | unsafe | test | controlled | 3 | 1 | 4 | 0 | 0 | - | - |
| F8 | unsafe | test | real_world | 3 | 1 | 4 | 0 | 0 | 0 | 1 |

- dev controlled: targets 112, reserves 32, labelled 144, short 0
- dev real_world: targets 112, reserves 32, labelled 125, short 3
- test controlled: targets 48, reserves 16, labelled 64, short 0
- test real_world: targets 48, reserves 16, labelled 58, short 0

### D4c: controlled tier, 33 templates (D4c-01 to D4c-06)

- generator and template versions: dev d4a-9 tpl-v2.0: 144; test d4a-9 tpl-v2.0: 64
- dev scenarios per template: tpl-01 6, tpl-02 6, tpl-03 6, tpl-06 6, tpl-08 6, tpl-09 7, tpl-10 6, tpl-11 6, tpl-14 7, tpl-15 6, tpl-16 6, tpl-19 7, tpl-21 6, tpl-22 7, tpl-24 7, tpl-25 6, tpl-26 6, tpl-28 6, tpl-29 7, tpl-30 6, tpl-31 6, tpl-32 6, tpl-33 6
- test scenarios per template: tpl-04 6, tpl-05 7, tpl-07 7, tpl-12 6, tpl-13 6, tpl-17 7, tpl-18 6, tpl-20 6, tpl-23 7, tpl-27 6
- F5 scenarios using the SG-name replacement operator (`op_f5_db_sg_replacement_safe`/`_unsafe`), by tier, split, intent class: controlled dev safe: 1; controlled dev unsafe: 7; controlled test safe: 1; controlled test unsafe: 3; real_world dev safe: 1; real_world dev unsafe: 3; real_world test safe: 1; real_world test unsafe: 2
- controlled outcome by split: dev labelled: 144; test labelled: 64

