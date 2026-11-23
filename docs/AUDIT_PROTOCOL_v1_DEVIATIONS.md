# TerraPreserve v1.0 human label audit: deviations from protocol v1

Recorded before the auditor opened any packet. `docs/AUDIT_PROTOCOL_v1.md` is unchanged.

## D-1: the auditor (23 Nov 2026)

**Protocol text.** "Auditor: Krishika (co-author)."

**Change.** The audit is done by Ayush Kumar Singh (first author), because Krishika is not available in time for the planned submission. The protocol's other rules apply unchanged: the sample, the packet, the labels, the scoring, and the review of disagreements by both authors after κ is computed.

**What the new auditor has and has not seen** (his statement, recorded now):
- He did not write the oracle or DAIL code. Both were written by an AI coding assistant from work packages he relayed and merged.
- He has not opened any file in `audit/v1/` (the packet, `audit_labels.csv` or `key.json`). He has not opened any test-split scenario folder, `labels.json` or any oracle label of a test scenario.
- He has seen the aggregate test results of the DAIL main run (`docs/P10_RESULTS.md` in the DAIL repository). These include counts per family and per invariant, but no result per scenario.
- He knows the generator's operator catalogue (`docs/D4_OPERATORS.md`), which is public in this repository, as Krishika would have.

**Effect.** The paper reports that the audit was done by the first author, together with this statement.
