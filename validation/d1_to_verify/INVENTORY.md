# Inventory of `TO VERIFY` markers

Source: DAIL commit `7ed7aaf2602aaceba087608bb4b7db035bbc5194`, `git grep -n -F "TO VERIFY"` and `"TO-VERIFY"` in `docs/`
(case-sensitive; the case-insensitive grep also matches the word REVERIFYING in register row C-30, which is not a marker).
Produced by `validation/d1_to_verify/inventory.py`.

Items `V01`-`V14` are the reviewer's expected set. `X01`-`X04` are markers the grep found that the
expected set did not name. `definition` rows only explain the convention and need no resolution.
`aggregate` is the registry's section 12 heading, which restates items already listed above.

| Item | File:line | Marker text (exact) |
|---|---|---|
| V01 | `docs/specs/D0_AMENDMENTS_v1.0.1.md:111` | [TO VERIFY AT D1: whether a plan can be produced offline for these nine types, with mock credentials and the provider's skip flags, without data sources.] |
| V02 | `docs/specs/D0_AMENDMENTS_v1.0.1.md:135` | [TO VERIFY AT D1] |
| V02 | `docs/specs/INVARIANT_REGISTRY_v1.md:252` | [TO VERIFY AT D1 against the pinned Checkov version. If none exists, record "none; custom predicate only" (C-14).] |
| V03 | `docs/specs/D0_AMENDMENTS_v1.0.1.md:136` | [TO VERIFY AT D1] |
| V03 | `docs/specs/INVARIANT_REGISTRY_v1.md:282` | [TO VERIFY AT D1: that it tests `publicly_accessible` in the pinned version.] |
| V04 | `docs/specs/INVARIANT_REGISTRY_v1.md:240` | [TO VERIFY AT D1: the semantics in the pinned Checkov version.] |
| V05 | `docs/specs/INVARIANT_REGISTRY_v1.md:261` | [TO VERIFY AT D1 against the pinned provider version.] |
| V06 | `docs/specs/INVARIANT_REGISTRY_v1.md:130` | [TO VERIFY AT D1: the same note for the pinned provider version.] |
| V07 | `docs/specs/INVARIANT_REGISTRY_v1.md:310` | [TO VERIFY AT D1: the RDS default port for the postgres engine is 5432.] |
| V08 | `docs/specs/INVARIANT_REGISTRY_v1.md:84` | [TO VERIFY AT D1: the provider rejects host-bit CIDRs at validation.] |
| V09 | `docs/specs/INVARIANT_REGISTRY_v1.md:88` | [TO VERIFY AT D1: the provider accepts upper-case values.] |
| V10 | `docs/specs/INVARIANT_REGISTRY_v1.md:69` | [TO VERIFY AT D1: the implicit-move rules for `count` and `for_each` in the pinned Terraform version.] |
| V11 | `docs/specs/INVARIANT_REGISTRY_v1.md:105` | [TO VERIFY AT D1: cite the AWS security-group documentation.] |
| V12 | `docs/specs/INVARIANT_REGISTRY_v1.md:142` | [TO VERIFY AT D1: complete both lists against the pinned provider's resource index. Any further resource that creates security-group rules, attaches security groups, filters subnet traffic or adds routes inside a VPC must be added before the freeze.] |
| V13 | `docs/specs/INVARIANT_REGISTRY_v1.md:376` | [TO VERIFY AT D1. If confirmed, raise a Doc 04 errata row.] |
| V14 | `docs/specs/INVARIANT_REGISTRY_v1.md:378` | [TO VERIFY AT D1.] |
| X01 | `docs/specs/INVARIANT_REGISTRY_v1.md:128` | [TO VERIFY AT D1: the provider documentation for the pinned version.] |
| X02 | `docs/specs/INVARIANT_REGISTRY_v1.md:299` | [TO VERIFY AT D1: cite the AWS RDS documentation for this requirement.] |
| X03 | `docs/specs/D0_AMENDMENTS_v1.0.1.md:99` (1/2) | [TO VERIFY before step 17: EC2, RDS and VPC Reachability Analyzer eligibility] |
| X03 | `docs/specs/D0_AMENDMENTS_v1.0.1.md:99` (2/2) | [TO VERIFY] |
| X04 | `docs/specs/D0_AMENDMENTS_v1.0.1.md:100` (1/3) | [TO VERIFY] |
| X04 | `docs/specs/D0_AMENDMENTS_v1.0.1.md:100` (2/3) | [TO VERIFY] |
| X04 | `docs/specs/D0_AMENDMENTS_v1.0.1.md:100` (3/3) | [TO VERIFY per tool] |
| definition | `docs/specs/D0_AMENDMENTS_v1.0.1.md:13` | [TO VERIFY] |
| definition | `docs/specs/INVARIANT_REGISTRY_v1.md:14` | [TO VERIFY AT D1] |
| aggregate | `docs/specs/INVARIANT_REGISTRY_v1.md:464` | [TO VERIFY AT D1] |

Markers found (rows above, excluding definitions): 24
Resolution items: 18 (V01, V02, V03, V04, V05, V06, V07, V08, V09, V10, V11, V12, V13, V14, X01, X02, X03, X04)
