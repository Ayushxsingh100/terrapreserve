# Derived Native Redaction Log for Module 358849

This module is derived from a TerraDS native candidate excluded as E09.
The literal password attribute on `aws_db_instance` was replaced with `var.db_password`,
and a sensitive variable declaration was added without a default value.

| File | Line | Resource Address | Attribute | Replacement | SHA-256 Before | SHA-256 After |
|---|---|---|---|---|---|---|
| `main.tf` | 21 | `aws_db_instance.mydb` | `password` | `var.db_password` | `5de5027657e0d3a8025d449f0f6be380f239dfac1641db7995f048202849b1fa` | `757d425d31a685be42f4b26c2bc158e24769578abe91bed1179a1039557bae57` |

## Rescan Verification

- Inventory scan: clean (0 flagged credential attributes)
- Gitleaks scan: clean
