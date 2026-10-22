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

## Collection Process

| Question | Answer |
|---|---|
| How was the data acquired? | Planned sources: TerraGoat, TerraDS, Checkov rule library (ADR-013). Acquisition is D1 Prompt B; versions and hashes: not yet established. |
| What was the sampling strategy? | Not yet established. Pool filtering uses Terraform's own tooling or a parser different from DAIL's (ADR-013). |
| Who was involved in collection? | Not yet established. |
| Over what timeframe? | Not yet established. |
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
