# TerraPreserve

TerraPreserve is a benchmark dataset for evaluating whether a Terraform repair preserves the invariants that the original configuration already satisfied. It is built from three public sources, shaped to a fixed set of protected invariants, and labelled by an independent oracle written from the Invariant Registry Specification and from Terraform and AWS semantics.

## Relation to DAIL

TerraPreserve is the companion dataset to [DAIL](https://github.com/Ayushxsingh100/DAIL) (Dependency-Aware Invariant Ledger), a deterministic safety gate for LLM-generated Terraform repairs. It lives in a separate repository (DAIL ADR-013). **Independence rule (DAIL ADR-010):** nothing in this repository imports DAIL code or depends on the DAIL package, so the ground-truth labels stay independent of the system under test. `tests/test_independence.py` enforces this. DAIL consumes frozen TerraPreserve releases, pinned by version and content hash.

## Planned sources

| Source | Status |
|---|---|
| TerraGoat | acquired in D1 Prompt B |
| TerraDS | acquired in D1 Prompt B |
| Checkov rule library | acquired in D1 Prompt B |

## Licences

- Code: Apache-2.0 ([LICENSE](LICENSE)).
- Our own scenarios and labels: CC-BY-4.0.
- Files derived from a source keep that source's licence (recorded per file once sources are added).

Details are in [LICENSES/README.md](LICENSES/README.md).

## Pinned toolchain

Terraform `~> 1.15.0` (CI uses 1.15.8), `hashicorp/aws` 6.53.0, Python 3.12. These are identical to DAIL's pins (ADR-013).

## Status

Pre-release; scenarios not yet generated.
