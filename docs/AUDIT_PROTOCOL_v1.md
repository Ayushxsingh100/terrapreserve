# TerraPreserve v1.0 — human label audit, protocol v1

Fixed by the authors on 23 Nov 2026, before any sample is drawn and before the auditor sees any test scenario.

## Purpose
To estimate how far the oracle's labels (`oracle-1.0`) agree with a human who reads the same configurations and the same invariant definitions. The oracle and DAIL were both written by an AI coding assistant (TPL2-02; DAIL C-233). This audit adds a human, independent check of the labels. It does not change any label.

## Auditor
Krishika (co-author). She did not write the oracle or DAIL code, and she has not seen any test-split label, DAIL decision or analysis output for the scenarios she audits.

## Sample
- **Population:** the 96 test-split targets of TerraPreserve v1.0.
- **Strata:** family (F1–F8) × tier (controlled, real-world) × oracle class (safe, unsafe), giving 32 strata of 3 scenarios each.
- **Draw:** one scenario per stratum, 32 in total. The draw uses Python's `random.Random(20261124)`. Within each stratum the candidates are sorted by scenario id and one is picked with `rng.choice`. The strata are visited in the order F1..F8, then controlled before real-world, then safe before unsafe.
- **Order:** the 32 scenarios are shown in an order shuffled with `random.Random(20261125)`, under packet ids `A01`..`A32`.
- **What the auditor knows:** that each family contributes two controlled and two real-world scenarios, and two of each class. She is not told which scenario is which class.

## What the auditor receives (the blinded packet)
For each sampled scenario:
- every step directory (`step_0` .. `step_n`), unchanged;
- a `brief.json` with only:
  - the packet id;
  - the family;
  - the target's `kind` and `invariant_id` (never its description);
  - the endpoints `S` and `D`;
  - the primary variable values;
  - the list of step numbers.

The packet never contains `labels`, `gt_class`, `oracle`, `intent`, `mutation_record`, `target.description`, `v1_role_reason`, `parameters`, the diffs or the alternate value set, and no DAIL output of any kind.

**Reference text:** the Invariant Registry Specification v1.0 (`docs/specs/INVARIANT_REGISTRY_v1.md` in the DAIL repository, tag `registry-v1.0`), which is the text the oracle was written from, together with Terraform and AWS documentation.

## What the auditor records
For each packet, each step (step 0 included) and each of the four invariants: one row in `audit_labels.csv`, with the columns:
- `packet_id`;
- `step`;
- `invariant_id`;
- `label`, which is one of `PASS`, `FAIL` or `CANNOT_TELL`;
- `note`, free text, required for `CANNOT_TELL`.

She works from the configuration text alone: she runs no tool that evaluates the invariants (neither the oracle nor DAIL), and she runs no Terraform plan. When the file is complete, its SHA-256 is recorded before any scoring.

## Scoring (V3)
- **Per invariant and overall:** Cohen's κ and percent agreement between the auditor and the oracle, over the cells where both say `PASS` or `FAIL`. `CANNOT_TELL` cells, and any oracle non-`PASS`/`FAIL` cells, are counted apart.
- **Per scenario:** the auditor's class is derived from her labels by the oracle's own rule (D5-11) and compared with the oracle's class.
- **Every disagreement is listed.** Afterwards, the two authors review each one together and assign one cause: *oracle error*, *auditor error*, or *registry ambiguity*. This review comes after κ is computed and never changes it.

## What follows from the result
- No threshold is set. Every number is reported as measured, in the paper and in `docs/AUDIT_REPORT_v1.md`.
- An oracle error found here is reported. The v1.0 labels are not edited; a correction would go into a later version (an erratum for v1.0.1).
- If an oracle error touches a scenario the DAIL main run used, the paper says which result it affects.
