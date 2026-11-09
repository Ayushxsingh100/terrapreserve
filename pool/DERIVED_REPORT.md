# Derived Natives Pipeline Report (D4b-02)

## Summary

- **Candidates evaluated:** 96
- **DX01 refusals (declares db_password or password appears elsewhere):** 12
- **Accepted derived natives:** 6

## Ledger by Exclusion Code

| Code | Count | Description |
|---|---|---|
| `ACCEPTED` | 6 | |
| `DX01` | 12 | |
| `E10_LINEAGE_DUPLICATE` | 74 | |
| `E12_INVALID_UNDER_PIN` | 4 | |

## Accepted Derived Natives

| Module ID | Repo Full Name | Lineage ID | Files |
|---|---|---|---|
| `290262` | `asquarezone/TerraformZone` | `lin-000102797961` | 8 |
| `358849` | `antonputra/tutorials` | `lin-000316823064` | 2 |
| `574780` | `Sarthak-017s/Terraform-IaC-for-Medusa-open-source` | `lin-000852752600` | 2 |
| `588227` | `RajeshRangdal/terraform-aws-2tier` | `lin-000893886026` | 3 |
| `613257` | `Luanacsilva/Academia-corpo-em-forma` | `lin-000961020473` | 3 |
| `653852` | `abdoulWaris/handleTerraform` | `lin-001057181459` | 4 |

## Not used in v1.0 (D4b-14, decided 9 Nov 2026)

The derived natives are not used in v1.0. **Derived-native yield for v1.0: 0 scenarios.** D0 Decision 3: yields are reported, never padded. The code (`pool/derive.py`) and `pool/derived.json` stay in the repository for v1.1. The five that had been assigned to `tp-v1-F1-0209` to `tp-v1-F1-0213` violate D0 Decision 6 (base state S0 must satisfy every protected invariant except the remediation target). Measured on the d4b-4 scenarios at commit `47a2781` with `generator/realworld/modread.py`:

| Scenario at `47a2781` | Module ID | Reason (registry v1.0) |
|---|---|---|
| `tp-v1-F1-0209` | `290262` | `aws_db_instance` engine `mysql`, no port: INV-FUNC-001 FAIL (6.4 row 3). Also `aws_security_group.web` covers `0.0.0.0/0` on TCP 22: INV-SEC-001 FAIL. |
| `tp-v1-F1-0210` | `358849` | `aws_db_instance.mydb` has no `vpc_security_group_ids`: INV-FUNC-001 UNSUPPORTED (6.4 row 2). `publicly_accessible = true`: INV-SEC-003 FAIL. |
| `tp-v1-F1-0211` | `574780` | An endpoint has no `vpc_security_group_ids`: INV-FUNC-001 UNSUPPORTED (6.4 row 2). |
| `tp-v1-F1-0212` | `588227` | `aws_db_instance` engine `mysql`, no port: INV-FUNC-001 FAIL (6.4 row 3). |
| `tp-v1-F1-0213` | `613257` | An endpoint has no `vpc_security_group_ids`: INV-FUNC-001 UNSUPPORTED (6.4 row 2). `publicly_accessible = true`: INV-SEC-003 FAIL. |

The sixth accepted derived native, `653852`, was already unused because its values are references, not literals (D4b-05 span-edit preconditions).

