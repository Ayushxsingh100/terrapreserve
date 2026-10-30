# Derived Native Redaction Log for Module 588227

This module is derived from a TerraDS native candidate excluded as E09.
The literal password attribute on `aws_db_instance` was replaced with `var.db_password`,
and a sensitive variable declaration was added without a default value.

| File | Line | Resource Address | Attribute | Replacement | SHA-256 Before | SHA-256 After |
|---|---|---|---|---|---|---|
| `main.tf` | 166 | `aws_db_instance.my_db` | `password` | `var.db_password` | `cb37f71fece968af634179da41616b57a49602993fec3366f8b0b33b111a4863` | `93d6d9d9372b3d43063e10d0778be9a14683af20f6b18e5c390b1d64b8976c91` |

## Rescan Verification

- Inventory scan: clean (0 flagged credential attributes)
- Gitleaks scan: clean
