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
| How many instances are there? | Planned: 320 scenarios (D0 amendments A7, "excluded from the 320"). A7 also refers to a "20/20 balance"; what it is counted over: not yet established. The 15 canonical fixtures stay in the DAIL repository (ADR-013; D0 amendments A4.1). Actual counts: not yet established. |
| Is it a sample of a larger set? | Not yet established. |
| What data does each instance contain? | Not yet established. The D0 amendments name `gt_class`, `labels[]`, `truth_changed`, `footprint_hits`, `oracle_affected` and `rds_ingress_mode` (A1, A2, A7). |
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
| What was the sampling strategy? | Not yet established for the pool. The funnel F0..X over TerraDS metadata is measured (`sources/terrads/yield_report.md`); which modules enter the pool is a D3 decision. Pool filtering uses TerraDS's own metadata, produced by terraform-config-inspect, not DAIL's parser (ADR-013). A lexical re-derivation of module contents from the archive (an independent implementation, not terraform-config-inspect, which could not be run here and would not have been independent) agrees with the metadata on the managed type set for 656 of 657 sampled F3/F2 modules; see the report. |
| Who was involved in collection? | Not yet established. Run by Claude Code under the authors' instruction (D1 Prompt B). |
| Over what timeframe? | Sources retrieved on 2026-10-23 (UTC; `retrieved_utc` in the manifest). TerraDS's own data cutoff for the pinned version is January 2026, as its Zenodo record states. |
| Were ethical review processes conducted? | Not yet established. |

## Preprocessing / Cleaning / Labeling

| Question | Answer |
|---|---|
| Was any preprocessing done? | Not yet established. |
| Was the raw data saved? | Raw archives are kept in an external cache recorded in `sources/manifest.json` (`CLAUDE.md`); not yet created. |
| How were labels produced? | By an independent oracle written from the Invariant Registry Specification and Terraform and AWS semantics, by a different author from DAIL's verifiers, never reading DAIL's code or output (ADR-010; D0 amendments A4.2). Oracle labels are research labels only. |
| Is the tooling available? | Not yet established (`oracle/` and `generator/` are empty). |

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
