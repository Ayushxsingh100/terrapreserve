# TerraPreserve

TerraPreserve is a benchmark dataset for evaluating whether a Terraform repair preserves the invariants that the original configuration already satisfied. Each scenario is a trusted starting configuration, a remediation target and one or more ordered changes, labelled per step and per protected invariant by an oracle that is implemented separately from the system under test. It is built from three public sources (TerraGoat, TerraDS and Checkov's rule library) and shaped to a fixed set of four protected invariants.

**Status:** v1.0, public release (R2, 24 Nov 2026). The dataset was frozen at the tag `terrapreserve-v1.0` (`27f0ee4`, D6); R2 releases the test split that was withheld until then, byte for byte as frozen ([docs/R2_DECISIONS.md](docs/R2_DECISIONS.md)). The test split is public from this release on, so any later evaluation on it is not blind.

## Composition

Counts from [DATASHEET.md](DATASHEET.md) (v1.0 section) and the frozen manifests.

- **320 targets:** 8 families (F1 to F8) × 40, with 20 safe and 20 unsafe targets per family by the oracle's `gt_class`.
- **Two tiers:** controlled (TerraGoat's EC2, RDS and security-group resources reshaped into 33 hand-written templates) and real-world (TerraDS modules, each grafted with the canonical EC2/RDS/security-group core).
- **Split:** 224 dev and 96 test targets. The controlled tier is split by template (23 dev, 10 test templates); the real-world tier by repository lineage (285 dev, 122 test lineages). No lineage is on both sides.
- **All scenarios:** 416 (288 dev, 128 test): 320 targets, 71 reserves and 25 excluded.

| | dev controlled | dev real-world | test controlled | test real-world | total |
|---|---|---|---|---|---|
| targets | 115 | 109 | 48 | 48 | 320 |
| reserves | 29 | 16 | 16 | 10 | 71 |
| excluded | 0 | 19 | 0 | 6 | 25 |

- **Exclusions:** dev 16 `unplannable` and 3 `s0_not_clean`, test 6 `unplannable`, all real-world. No `unlabelable` and no `value_dependent` scenario.
- **Families (D0 Decision 5):** F1 unrelated change, F2 direct impact, F3 dependency-induced impact, F4 regression-inducing repair, F5 restructuring or replacement, F6 new-resource creation, F7 broad impact, F8 multi-step remediation.

## The four invariants

| ID | Property |
|---|---|
| INV-SEC-001 | No security-group ingress from `0.0.0.0/0` or `::/0` to port 22 |
| INV-SEC-002 | No security-group ingress from `0.0.0.0/0` or `::/0` to database port 5432 |
| INV-SEC-003 | `aws_db_instance.publicly_accessible` is false |
| INV-FUNC-001 | EC2 can reach RDS on TCP/5432 (configuration-level) |

## The oracle

The labels come only from the oracle in [oracle/](oracle/) (version `oracle-1.0`), written from the Invariant Registry Specification (`registry-v1.0`) and from Terraform and AWS semantics. It never reads DAIL's code or output.

- **Input path:** each step is planned offline (Terraform 1.15.8, `hashicorp/aws` 6.53.0, no credentials) and evaluated from the plan JSON (`terraform show -json`); the mapping rules are in [oracle/README.md](oracle/README.md).
- **Two value sets:** every step is evaluated under a primary and an alternate set of invented variable values (rule vv-3). A scenario whose labels differ between the sets would be excluded as `value_dependent`; none was.
- **Import ban:** nothing in this repository imports DAIL code or depends on the DAIL package (DAIL ADR-010); [tests/test_independence.py](tests/test_independence.py) enforces it.
- **Authorship note (TPL2-02):** the oracle, like DAIL, was written by Claude Code from work-package prompts under the authors' direction, not by a different human author. Its independence rests on a separate implementation in a separate repository, a different input path (Terraform plan JSON), the enforced import ban and the two-value-set invariance test ([docs/TP_L2_DECISIONS.md](docs/TP_L2_DECISIONS.md)).
- Oracle labels are research labels only.

## The layout of a scenario

Each scenario is a folder `scenarios/<split>/tp-v1-<family>-<number>/` (`scenarios/dev/` and `scenarios/test/`):

- `scenario.json`: the record.
  - Identity and version: `scenario_id`, `dataset_version` (`"1.0"`), `family`, `split`, `v1_role` (`target`, `reserve` or `excluded`), `v1_role_reason`, `excluded_from_v1`.
  - Source: `source` (tier, origin, repository lineage, commit or version, licence, grafted), `generator_version`, `template_id`, `parameters`.
  - Task: `target` (repair or change request), `protected_invariants`, `endpoints`, `intent`.
  - Steps: `steps` (per step its `terraform_dir`, `content_hash` and `diff_from_previous`; step 0 is S0) and `mutation_record` (the generator's record of each change).
  - Values: `variable_values` and `variable_values_alt` (the two value sets), with their rule and provenance.
  - Labels: `labels` (per step `invariant_truth`, `oracle_affected`, `target_safe`), `gt_class` and `oracle` (versions and the advisory Checkov disagreements).
- `step_0/`, `step_1/`, ...: the full Terraform directory of each step, so every step runs with standard Terraform tooling.
- `PROVENANCE/` (real-world scenarios): the upstream `LICENSE.upstream` and `SOURCE.json`.

A step's `content_hash` is the SHA-256 of the path-sorted lines `<relative path>:<sha256 of the file>` (D4-09).

**Manifests.**
- `scenarios/V1_MANIFEST.json`: every scenario's id, role and hashes.
- `scenarios/test/V1_MANIFEST_PRIVATE.json`: the test split's entries with family, class and tier.
- `scenarios/V1_MANIFEST.sha256`: the SHA-256 of both manifests, frozen at D6.

**LLM candidates** (TerraPreserve v1.1 labels, R2-02): `llm_candidates/<split>/<generation id>/`. Per candidate, its `.tf` files and `label.json`; per generation, `labels.json` and `labels.sha256`. `llm_candidates/dev/` holds the TP-L1 labels of DAIL's dev pilots; `llm_candidates/test/40e2052b-b489-552d-8c27-88785414a4b1/` holds the TP-L2 labels of DAIL's main run.

## How to use it

1. **Check the release.** Clone the repository and run the suite: `python -m unittest discover -s tests -p "test_*.py"`. It recomputes every hash against the frozen manifests, including the released test split.
2. **Read the scenarios.** Use the dev split (`scenarios/dev/`) for development and the test split (`scenarios/test/`) for reported results. The labels are in each `scenario.json`; use them for scoring only, never as input to the system under test.
3. **Run a step with Terraform.** Every `step_N/` is a complete configuration; every step passed `terraform validate` under Terraform 1.15.8 and `hashicorp/aws` 6.53.0. The oracle planned each step offline with the invented values of `variable_values` (primary) and `variable_values_alt` (alternate).

**Rebuilding a private directory.** Until R2 the test split lived only in `$TERRAPRESERVE_PRIVATE`. The tools that read it are unchanged; point them at a directory rebuilt from the released files, which holds the scenario folders and `V1_MANIFEST_PRIVATE.json` (the file DAIL's main-run guard reads from `$TERRAPRESERVE_PRIVATE`):

```bash
cp -r scenarios/test /path/outside/the/repository/terrapreserve-private
export TERRAPRESERVE_PRIVATE=/path/outside/the/repository/terrapreserve-private
python tools/check_freeze_gates.py --no-write   # gates 1 to 9 over both splits; writes no document
```

The directory must lie outside the repository. A rebuilt directory holds the scenarios and the manifest only. The plan caches, the oracle's intermediate files and the evidence archives are not released (R2-03). Neither are the D5a feasibility results or the vv-3 search result of the test split, which some private-directory checks of the test suite read. So run the test suite with `TERRAPRESERVE_PRIVATE` unset: it checks the released split from the committed files.

## Relation to DAIL

TerraPreserve is the companion dataset to [DAIL](https://github.com/Ayushxsingh100/DAIL) (Dependency-Aware Invariant Ledger, DOI [10.5281/zenodo.24495207](https://doi.org/10.5281/zenodo.24495207)), a deterministic safety gate for LLM-generated Terraform repairs. It lives in a separate repository (DAIL ADR-013). DAIL consumes frozen TerraPreserve releases, pinned by version and content hash. DAIL's evaluation used this dataset's test split once, under its frozen protocol (DAIL `protocol-v1`); the results are in DAIL `docs/P10_RESULTS.md`.

## Pinned toolchain

Terraform `~> 1.15.0` (CI uses 1.15.8), `hashicorp/aws` 6.53.0, Python 3.12. These are identical to DAIL's pins (ADR-013).

## Licences

- Code: Apache-2.0 ([LICENSE](LICENSE)).
- Our own scenarios and labels: CC-BY-4.0.
- TerraGoat-derived files keep TerraGoat's Apache-2.0 notice. TerraDS-derived files keep each source repository's own licence, recorded per module (`PROVENANCE/`, `pool/pool.json`).

Details are in [LICENSES/README.md](LICENSES/README.md).

## Citation

See [CITATION.cff](CITATION.cff). TerraDS, from which the real-world tier is drawn, is cited in [DATASHEET.md](DATASHEET.md).

## Limitations

From the datasheet's "Known limitations":

- The controlled test split had 3 template clusters until D4c, which expanded the controlled tier to 33 templates (10 test clusters).
- Grafts are standalone (D4b `Open 1`, decided for v1.0): the core is not attached to the host's VPC or subnets; attach mode is v1.1 work.
- The generator's S0 screen missed three hosts (MIXED in either direction, a reversed TCP port range); the oracle caught them and they are excluded (`s0_not_clean`). The screen was fixed in D4c; the real-world tier was not regenerated.
- Reserves are spread unevenly across controlled templates (five test templates carry none, `tpl-05` carries 4); per-template reporting must use the actual counts.
- INV-FUNC-001 is evaluated at configuration level and does not model DNS (for example `enable_dns_hostnames = false`).
- F5 `for_each` restructuring is not generated (only `count`); inline-to-separate rule restructuring is not generated (it leaves a group RETAINED-INLINE).

Composition, collection and labelling in full: [DATASHEET.md](DATASHEET.md). Scenarios: [scenarios/README.md](scenarios/README.md). The real-world pool: [pool/README.md](pool/README.md).
