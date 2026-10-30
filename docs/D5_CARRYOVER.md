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

D4a delivers the 160 controlled targets (+ 48 reserves). D4b will deliver the 160 real-world targets (+ 48 reserves) by grafting onto pooled hosts and derived natives. D5 will label both tiers using the unified oracle suite.

