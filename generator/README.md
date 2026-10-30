# generator/

The scenario generator for TerraPreserve (D4a).

Produces benchmark scenarios consisting of trusted base states, ordered remediation steps, deterministic HCL files, truthful mutation records, and intent annotations.

Ground-truth evaluation is deferred to the independent oracle in D5 (ADR-010); the generator records only what it changed itself and states an intent.

## Architecture

- **`model.py`**: Minimal in-memory HCL resource model (`Resource`, `HCLModel`) supporting expressions (`Ref`, `VarRef`, `RawExpr`, `SortedList`, `ToSet`). Enforces a strict secret-name guard at model construction time.
- **`emitter.py`**: Deterministic HCL emitter producing canonical 2-space indentation, LF endings, sorted resource and attribute keys, and column-aligned `=` signs. Emitted files pass `terraform fmt -check` directly.
- **`templates/`**: 10 distinct controlled templates (`tpl-01` to `tpl-10`) sharing the Doc 04 Appendix B topology (VPC, internet gateway, subnets, route tables, app EC2, db subnet group, db RDS, and security groups) while varying across architectural axes (SG rule styles, subnet count, second security groups, route table structures, `count` meta-arguments, and naming schemes). Each template supports clean baseline and pre-violated variants (`sec_001_violated`, `sec_002_violated`, `sec_003_violated`).
- **`operators/`**: Operator catalogue covering benchmark families F1 through F8 with safe and unsafe variants (≥3 safe and ≥3 unsafe operators per family, 48 total). Operators produce pure AST/model transformations and return mutation records.
- **`diff_verify.py`**: Structural diff verifier that re-parses emitted HCL text of step k-1 and step k and strictly verifies that every change in the diff appears in the `mutation_record`, that no phantom changes are recorded, and that recorded `before` and `after` values match the text diff.
- **`seed.py`**: Deterministic master seed (`20261031`), template shuffle for 70/30 dev/test split assignment, and per-scenario PRNG.
- **`writer.py`**: Scenario writer producing canonical sorted JSON, computing SHA-256 step directory hashes, and generating unified diffs. Strictly enforces split withholding by refusing to write test-split scenarios to the repository.
- **`generate.py`**: Pipeline driver generating the 208 controlled tier scenarios (160 targets + 48 reserves) and validating every step under Terraform 1.15.8 and `hashicorp/aws` 6.53.0.
- **`VERSION.py`**: Generator version tag (`d4a-1`).

## Independence

Per D0 gate 1 and `CLAUDE.md` rule 5, this package is completely independent of DAIL. It uses only Python standard library and in-repo sources (`sources/*`, `pool/*`). No DAIL modules or code are imported.
