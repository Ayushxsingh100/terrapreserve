# Datasheet for TerraPreserve

Structure follows Gebru et al., *Datasheets for Datasets* (section headings: Motivation, Composition, Collection Process, Preprocessing/Cleaning/Labeling, Uses, Distribution, Maintenance).

**Status:** skeleton. Every answer is `not yet established` unless a source is cited. Facts are cited to the DAIL repository at commit `7ed7aaf` (`docs/specs/D0_AMENDMENTS_v1.0.1.md`, cited "D0 amendments"; `docs/adr/`; `docs/DECISIONS_REGISTER.md`). The base document `D0_Dataset_Specification_TerraPreserve_v1.md` is not in the DAIL repository and was not read for this skeleton; facts that only it can confirm are marked as such.

## Motivation

| Question | Answer |
|---|---|
| Name of the dataset | TerraPreserve (DAIL ADR-013). |
| For what purpose was it created? | A benchmark for DAIL's evaluation of LLM-generated Terraform repairs; built from TerraGoat, TerraDS and Checkov's rule library and shaped to DAIL's parameters (ADR-013, Context). Fuller statement: not yet established. |
| Who created it, and who funded it? | Authors: Ayush Kumar Singh and Krishika, UPES School of Computer Science (project statement). Funding: the project spends USD 0 (N-08; D0 amendments A3.1). |

## Composition

| Question | Answer |
|---|---|
| What do the instances represent? | Labelled scenarios over Terraform configurations. Instance schema: not yet established. |
| How many instances are there? | Planned: 320 scenarios (160 controlled + 160 real-world). In D4a, the controlled tier is generated: 208 scenarios (160 targets + 48 reserves across 8 families × 2 classes). Dev split (144 scenarios: 112 targets + 32 reserves) is committed under `scenarios/dev/`; test split (64 scenarios: 48 targets + 16 reserves) is withheld outside the repository (`scenarios/test_manifest.json`). Real-world tier (160 scenarios) follows in D4b. |
| Is it a sample of a larger set? | Controlled tier: synthetic variations generated from 10 distinct architectural templates sharing the Doc 04 Appendix B topology. Real-world tier: sampled from the TerraDS pool. |
| What data does each instance contain? | Base state S0, ordered remediation steps (full Terraform directories), step content hashes (SHA-256), unified diffs, intent annotations, and generator-recorded mutation records. Labels and oracle evaluation follow in D5 (ADR-010). |
| Is there a label or target? | Yes: oracle labels per protected invariant (INV-SEC-001, INV-SEC-002, INV-SEC-003, INV-FUNC-001; D0 amendments A5) and a derived `gt_class` (A7). |
| Is any information missing? | Not yet established. |
| Are there errors, noise or redundancies? | Not yet established. |
| Does it contain confidential or sensitive data? | Not yet established. TerraGoat contains deliberate fake secrets, which are redacted before commit (D0 gate 5, per `CLAUDE.md`). |

### Composition (sources)

Measured on 2026-10-23 (UTC) by `sources/acquire.py` and `sources/terrads/measure_yield.py`; every value is read from [sources/manifest.json](sources/manifest.json) or [sources/terrads/yield.json](sources/terrads/yield.json). Raw archives are kept outside Git.

| Source | Pinned version | Licence (manifest `licence_spdx`) | What was measured |
|---|---|---|---|
| TerraGoat | `bridgecrewio/terragoat`, default branch `master`, commit `729f8da62c6a85ce4af5ad3d123de97776d954c4` (committed 2023-04-27); not archived | Apache-2.0, read from the repository's `LICENSE` (sha256 in `licence_evidence`); identical to `LICENSES/Apache-2.0.txt` after whitespace normalisation (`sources/terragoat/licence_diff.md`) | 17 files under `terraform/aws/` (`sources/terragoat/files.sha256`); 2 gitleaks findings there in the working tree and 4 in history, values redacted; a second, rule-independent inventory flags 4 credential-like literal attributes, 3 of which gitleaks did not flag (`sources/terragoat/secret_scan_summary.md`) |
| TerraDS | Zenodo record `20339474` (published 2026-05-26), version DOI `10.5281/zenodo.20339474`, concept DOI `10.5281/zenodo.14217385` | CC-BY-4.0 for the dataset; each repository keeps its own licence, recorded per repository in the database (D0 Decision 9) | 82,749 repositories, 394,004 modules and 2,497,629 resources in the database; the funnel and licence tables are in [sources/terrads/yield_report.md](sources/terrads/yield_report.md) |
| Checkov | PyPI `checkov` 3.3.30, git tag `3.3.30` at commit `dfeb34b2d52a269bb417b4d4f7854a16bef06629` | Apache-2.0, read from `LICENSE` at that commit | reference tool only; wheel sha256 `32c3d6a808399f3fd6ec83e68a337050d17f019336f4d8f3b23aae469ba79408` (PyPI and measured agree); full environment pinned in `requirements-tools.lock.txt` (sha256 in the manifest) |

**Attribution (CC-BY-4.0).** TerraDS is cited twice: the paper that describes it, and the data we use.

(a) Paper:

> Bühler, C., Spielmann, D., Meier, R., & Salvaneschi, G. (2025). TerraDS: A Dataset for Terraform HCL Programs. In *2025 IEEE/ACM 22nd International Conference on Mining Software Repositories (MSR)*, Data and Tool Showcase Track, pp. 654-658. https://doi.org/10.1109/MSR66628.2025.00101

(b) Data (the version we pin, as the Zenodo record and its DOI give it):

> Bühler, C., Spielmann, D., Meier, R., & Salvaneschi, G. (2026). *TerraDS: A Dataset for Terraform HCL Programs* [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.20339474

The earlier data version is https://doi.org/10.5281/zenodo.14217386 (2024) and the concept DOI is https://doi.org/10.5281/zenodo.14217385.

Repository counts: the paper's abstract states 67,360 repositories, while its body (371,981 found, 67,360 with a permissive licence, minus 14 not clonable and 4,940 without Terraform) and the v1 data state 62,406; TerraPreserve reports its own measured v2 counts (82,749 repositories, 394,004 modules, 2,497,629 resources).

Terraform, AWS provider and Checkov versions (D0 gate 9): Terraform 1.15.8 and `hashicorp/aws` 6.53.0 (ADR-013 pins); Checkov 3.3.30. Instance schema and counts of scenarios: not yet established.

## Collection Process

| Question | Answer |
|---|---|
| How was the data acquired? | `sources/acquire.py fetch`: TerraGoat by `git clone` at the pinned commit; TerraDS from Zenodo record `20339474` (`TerraDS.sqlite`, `TerraDS.tar.gz`, `HCL Dataset Tools.zip`), md5 checked against Zenodo's published values and sha256 measured; Checkov from PyPI. Hashes, sizes and licence evidence: `sources/manifest.json`. Raw files are in an external cache, not in Git. |
| What was the sampling strategy? | The funnel F0..X over TerraDS metadata is measured (`sources/terrads/yield_report.md`). The pool is selected by the exclusion cascade E01 to E12 (`docs/D3_DECISIONS.md`, `pool/funnel.json`): all native modules go through every step, graft hosts are reduced to one per repository lineage and sampled with a fixed seed; see the Pool section below. Pool filtering uses TerraDS's own metadata, produced by terraform-config-inspect, not DAIL's parser (ADR-013). A lexical re-derivation of module contents from the archive (an independent implementation, not terraform-config-inspect, which could not be run here and would not have been independent) agrees with the metadata on the managed type set for 656 of 657 sampled F3/F2 modules; see the report. |
| Who was involved in collection? | Not yet established. Run by Claude Code under the authors' instruction (D1 Prompt B). |
| Over what timeframe? | Sources retrieved on 2026-10-23 (UTC; `retrieved_utc` in the manifest). TerraDS's own data cutoff for the pinned version is January 2026, as its Zenodo record states. |
| Were ethical review processes conducted? | Not yet established. |

## Preprocessing / Cleaning / Labeling

| Question | Answer |
|---|---|
| Was any preprocessing done? | Yes, in D3: real-world files are verbatim copies (CRLF read as LF); real-world modules with a secret finding are excluded, never edited; TerraGoat's credential-like attributes are deleted and logged without values (`pool/terragoat/aws/REDACTION_LOG.md`). The copy that `terraform validate` read was neutralised as described in `docs/D4_CARRYOVER.md`. |
| Was the raw data saved? | Raw archives are kept in an external cache recorded in `sources/manifest.json` (`CLAUDE.md`), created in D1 Prompt B and never committed. Each pooled module keeps the sha256 of its archive bytes in `SOURCE.json`. |
| How were labels produced? | By an independent oracle written from the Invariant Registry Specification and Terraform and AWS semantics, by a different author from DAIL's verifiers, never reading DAIL's code or output (ADR-010; D0 amendments A4.2). Oracle labels are research labels only (produced in D5). |
| Is the tooling available? | The scenario generator (`generator/`) is implemented in D4a (version `d4a-1`). Oracle (`oracle/`) is implemented in D5. |

<!-- POOL:BEGIN (generated by pool/report.py; do not edit by hand) -->
## Pool (D3)

Measured by `pool/build.py`; the full account, with every exclusion, is in `pool/POOL_REPORT.md`, `pool/funnel.json` and `pool/exclusions.csv`.

- Real-world modules accepted: 401 (1 native, holding both `aws_instance` and `aws_db_instance`; 400 graft hosts), from 401 repositories in 401 lineages. Real-world slots: 160; shortfall in modules: 0 (not filled).
- Candidates considered: 133 native, 8,542 host; hosts not processed after the stop rule: 2,381.
- Licences of accepted modules: MIT 282, Apache-2.0 105, Unlicense 7, BSD-3-Clause 4, CC0-1.0 2, MIT-0 1.
- `terraform validate` under Terraform 1.15.x and `hashicorp/aws` 6.53.0: 401 of 526 modules that reached that step were valid.
- Lineages over the candidates that passed the cheap filters: 3,060; largest 344 modules. Undetected forks: not yet established.
- Controlled tier: TerraGoat, 14 `.tf` files, Apache-2.0 notice kept, 6 credential-like attributes deleted and logged.
- Secrets: every accepted real-world module has 0 gitleaks findings and 0 flagged attributes; real-world modules with a finding were excluded, never edited.
- Selection bias: small, self-contained, secret-free, permissively licensed modules that validate under the pins; the pool is not representative of Terraform in the wild.
<!-- POOL:END -->

## Controlled Tier (D4a)

Measured by `generator/generate.py` on 2026-10-30; records in `scenarios/validate_results.csv`, `scenarios/split.json`, `scenarios/test_manifest.json`, and `docs/D4_DECISIONS.md`.

- **Total scenarios generated**: 208 scenarios (160 targets + 48 reserves).
- **Cells**: 16 cells (8 families F1..F8 × 2 classes safe/unsafe). Each cell contains 13 scenarios (10 targets, 3 reserves).
- **Templates**: 10 controlled templates (`tpl-01` to `tpl-10`) in the Doc 04 Appendix B topology, varying across security-group rule structures, subnet counts, dual security groups, route table topologies, and resource naming.
- **Split assignment**: 70/30 split assigned strictly by template lineage (`scenarios/split.json`, master seed `20261031`):
  - Dev templates (7): `tpl-03`, `tpl-09`, `tpl-06`, `tpl-02`, `tpl-08`, `tpl-10`, `tpl-01`
  - Test templates (3): `tpl-07`, `tpl-04`, `tpl-05`
  - Yields 144 dev scenarios (112 targets + 32 reserves) and 64 test scenarios (48 targets + 16 reserves), rotating reserves across all 10 templates (2 dev + 1 test per cell).
- **Withholding (D4-01, D0 Decision 9)**: 144 dev scenarios committed under `scenarios/dev/` (1,128 files, ~1.51 MiB); 64 test scenarios withheld outside Git in `$TERRAPRESERVE_PRIVATE` (`~/.terrapreserve-private`). The repository carries cryptographic SHA-256 integrity hashes in `scenarios/test_manifest.json`.
- **Validation**: 466 total steps across all 208 scenarios. 466 of 466 steps passed `terraform validate` under Terraform 1.15.8 and `hashicorp/aws` 6.53.0 (0 invalid, 0 error).
- **Mutation verification**: 100% of generated steps verified by structural diff verifier (`generator/diff_verify.py`); 0 unrecorded or fabricated changes.
- **Deviations**: In Family F5 (restructuring), only `count` meta-argument restructuring is implemented (`op_f5_count_each_safe`, `op_f5_count_each_unsafe`); `for_each` restructuring is not implemented in D4a.
- **Licencing**: CC-BY-4.0 for scenario definitions; Apache-2.0 notice for reshaped TerraGoat resource vocabulary (`scenarios/NOTICE`).

## Uses

| Question | Answer |
|---|---|
| What tasks has it been used for? | None yet. Intended: evaluating DAIL (P8 experiments; D0 amendments A2). |
| Is there a repository linking to papers or systems using it? | Not yet established. |
| What other tasks could it be used for? | Not yet established. |
| Are there tasks it should not be used for? | Not yet established. Oracle results are research labels and never feed promotion decisions (ADR-010; D0 amendments A4.2). |

## Distribution

| Question | Answer |
|---|---|
| Will it be distributed to third parties? | Released as frozen releases that DAIL consumes pinned by version and content hash (ADR-013). Public release plan and venue: not yet established. |
| How will it be distributed? | Not yet established. Repository: https://github.com/Ayushxsingh100/terrapreserve. DOI: not yet established. |
| Under what licence? | Code: Apache-2.0. Our own scenarios and labels: CC-BY-4.0. TerraGoat-derived files keep Apache-2.0; TerraDS-derived files keep each source repository's own licence (D0 Decision 9, as quoted in the D1 Prompt A; the base D0 document was not read). See [LICENSES/README.md](LICENSES/README.md). |
| Are there export controls or other restrictions? | Not yet established. |

## Maintenance

| Question | Answer |
|---|---|
| Who maintains it? | Not yet established. |
| How can the maintainers be contacted? | Not yet established. |
| Will it be updated? | Not yet established. Releases are frozen and versioned (ADR-013); versioning scheme: not yet established. |
| Will older versions remain available? | Not yet established. |
| How can others contribute? | Not yet established. |
