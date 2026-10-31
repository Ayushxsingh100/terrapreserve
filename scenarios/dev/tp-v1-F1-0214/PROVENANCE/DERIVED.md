# Derived Native Redaction Log for Module 653852

This module is derived from a TerraDS native candidate excluded as E09.
The literal password attribute on `aws_db_instance` was replaced with `var.db_password`,
and a sensitive variable declaration was added without a default value.

| File | Line | Resource Address | Attribute | Replacement | SHA-256 Before | SHA-256 After |
|---|---|---|---|---|---|---|
| `main.tf` | 32 | `aws_db_instance.database_instance` | `password` | `var.db_password` | `933850f171f804e35f1df06213867af24ed528779c4a9b60f634e169e05919da` | `ace00c1ec1662af5aa047e6be8216ae4036c462131a97b02486bac386a760406` |

## Rescan Verification

- Inventory scan: clean (0 flagged credential attributes)
- Gitleaks scan: clean
