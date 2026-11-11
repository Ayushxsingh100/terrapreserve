# D6 freeze gates (D0 Decision 10)

Written by `tools/check_freeze_gates.py` (D6-03); do not edit by hand. D0 Decision 10: "The dataset is frozen only when **all** of these pass". Scenarios checked: 288 dev and 128 test (test split: counts only). Gates 3 and 4 decide on the targets and report the reserves; gate 2 covers every step of every target; gates 5, 6 and 8 cover all scenarios.

| Gate | What was checked | Count | Result |
|---|---|---|---|
| 1. Independence | `tests/test_independence.py` (no file imports DAIL code or the DAIL package; the oracle imports no generator, pool, sources, tests or tools code) | Ran 21 tests | PASS |
| 2. Validity | `terraform validate` (Terraform 1.15.8, `hashicorp/aws` 6.53.0, pinned harness of `pool/validate.py`) on every step of every target | 716 steps | PASS |
| 3. Base-state check | step 0 of every target: every protected invariant PASS per the oracle except the repair target (labels in `scenario.json`) | 320 targets (reserves not clean: 0) | PASS |
| 4. Complete labels | every step of every target has an oracle result for all four protected invariants, and the scenario has a `gt_class` | 716 target steps (reserves incomplete: 0) | PASS |
| 5. No secrets | redaction scan of every scenario directory (attribute inventory and gitleaks 8.30.1; `pool/redact.py`, the scanners of D3) | 4804 .tf files in 416 scenarios | PASS |
| 6. No leakage | `source.repo_lineage_id` of every scenario (controlled: template id; real-world: TerraDS lineage): no lineage in both dev and test | 241 lineages in 416 scenarios | PASS |
| 7. Balance | targets per family by oracle `gt_class`, each within plus or minus 2 of 20 | 320 targets | PASS |
| 8. Integrity | every step content hash in `scenario.json`; `scenarios/test_manifest.json` (128 entries: `scenario.json` and step hashes); `scenarios/V1_MANIFEST.json`, the private manifest and `scenarios/V1_MANIFEST.sha256` | 931 steps | PASS |
| 9. Pinned versions | `oracle.versions` of every labelled scenario against the pins: Terraform 1.15.8, `hashicorp/aws` 6.53.0, Checkov 3.3.30, oracle-1.0, generator d4a-9 (controlled) and d4b-9 (real-world), registry-v1.0, value rule vv-3 | 391 labelled scenarios | PASS |

## Gate 7: targets per family (by oracle `gt_class`)

| Family | safe | unsafe |
|---|---|---|
| F1 | 20 | 20 |
| F2 | 20 | 20 |
| F3 | 20 | 20 |
| F4 | 20 | 20 |
| F5 | 20 | 20 |
| F6 | 20 | 20 |
| F7 | 20 | 20 |
| F8 | 20 | 20 |

## Problems

None: every gate is PASS.
