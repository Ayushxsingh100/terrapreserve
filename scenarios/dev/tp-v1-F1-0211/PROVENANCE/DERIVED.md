# Derived Native Redaction Log for Module 574780

This module is derived from a TerraDS native candidate excluded as E09.
The literal password attribute on `aws_db_instance` was replaced with `var.db_password`,
and a sensitive variable declaration was added without a default value.

| File | Line | Resource Address | Attribute | Replacement | SHA-256 Before | SHA-256 After |
|---|---|---|---|---|---|---|
| `main.tf` | 69 | `aws_db_instance.medusa_db` | `password` | `var.db_password` | `a8cf51136343f0c80f3c43e6dfb5124d53476cac0cc91c67982c871c9276377c` | `64959c37f77d9743b1c3613698ed6cf84d696387957aae1d6c6fcc5312d0cdef` |

## Rescan Verification

- Inventory scan: clean (0 flagged credential attributes)
- Gitleaks scan: clean
