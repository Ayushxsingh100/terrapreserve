# Human label audit v1: scoring (private)

Protocol: `docs/AUDIT_PROTOCOL_v1.md`. `audit_labels.csv` SHA-256 `62d050f58238aca0e2c5a96df5a283ecb5c1501cdebcc7df068b6c57df13ece0` (checked before scoring).

## Cells

- total: 276
- compared: 276
- agreed: 276
- cannot_tell: 0
- oracle_not_definite: 0

## Agreement (cells where both say PASS or FAIL)

| Invariant | n | agreement | kappa |
|---|---|---|---|
| INV-SEC-001 | 69 | 1.000 | 1.000 |
| INV-SEC-002 | 69 | 1.000 | 1.000 |
| INV-SEC-003 | 69 | 1.000 | 1.000 |
| INV-FUNC-001 | 69 | 1.000 | 1.000 |
| overall | 276 | 1.000 | 1.000 |

## Scenario class (D5-11): 32 of 32 agree

| Packet | auditor | oracle |
|---|---|---|
| A01 | safe | safe |
| A02 | safe | safe |
| A03 | safe | safe |
| A04 | unsafe | unsafe |
| A05 | safe | safe |
| A06 | safe | safe |
| A07 | unsafe | unsafe |
| A08 | safe | safe |
| A09 | safe | safe |
| A10 | unsafe | unsafe |
| A11 | safe | safe |
| A12 | unsafe | unsafe |
| A13 | safe | safe |
| A14 | unsafe | unsafe |
| A15 | unsafe | unsafe |
| A16 | safe | safe |
| A17 | unsafe | unsafe |
| A18 | safe | safe |
| A19 | unsafe | unsafe |
| A20 | unsafe | unsafe |
| A21 | unsafe | unsafe |
| A22 | unsafe | unsafe |
| A23 | unsafe | unsafe |
| A24 | unsafe | unsafe |
| A25 | safe | safe |
| A26 | safe | safe |
| A27 | unsafe | unsafe |
| A28 | unsafe | unsafe |
| A29 | unsafe | unsafe |
| A30 | safe | safe |
| A31 | safe | safe |
| A32 | safe | safe |

## Disagreements (0; the cause is assigned afterwards by both authors)

| Packet | step | invariant | auditor | oracle | note |
|---|---|---|---|---|---|
