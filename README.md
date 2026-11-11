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
| Pool (redacted, licence-checked, deduplicated selection of the above) | built in D3; see [pool/](pool/) |

## Licences

- Code: Apache-2.0 ([LICENSE](LICENSE)).
- Our own scenarios and labels: CC-BY-4.0.
- Files derived from a source keep that source's licence (recorded per file once sources are added).

Details are in [LICENSES/README.md](LICENSES/README.md).

## Pinned toolchain

Terraform `~> 1.15.0` (CI uses 1.15.8), `hashicorp/aws` 6.53.0, Python 3.12. These are identical to DAIL's pins (ADR-013).

## Status

**v1.0 frozen (D6), internal until paper submission** (D0 Decision 9). 416 scenarios (288 dev, 128 test), 320 of them v1.0 targets (20 safe and 20 unsafe per family), labelled by the independent oracle `oracle-1.0`; D0 freeze gates 1 to 9 all PASS ([docs/D6_GATES.md](docs/D6_GATES.md)). The frozen commit is the merge commit of the D6 pull request, tagged `terrapreserve-v1.0` by the maintainers after review; later fixes go to v1.1 ([docs/D6_FREEZE.md](docs/D6_FREEZE.md)). The test split is withheld until release. Composition and limitations: [DATASHEET.md](DATASHEET.md); scenarios: [scenarios/README.md](scenarios/README.md); the real-world pool: [pool/README.md](pool/README.md).
