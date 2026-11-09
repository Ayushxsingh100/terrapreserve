# Derived Native Redaction Log for Module 290262

This module is derived from a TerraDS native candidate excluded as E09.
The literal password attribute on `aws_db_instance` was replaced with `var.db_password`,
and a sensitive variable declaration was added without a default value.

| File | Line | Resource Address | Attribute | Replacement | SHA-256 Before | SHA-256 After |
|---|---|---|---|---|---|---|
| `database.tf` | 51 | `aws_db_instance.empdb` | `password` | `var.db_password` | `509a776b932f597024535f0fc5372372e682cc7a09ec87214f8fa2015f0e4abc` | `c133ec0cabc9e00c74573e7f426509ea5b1ca0c3ee6eeb36522e8316dfb23d8a` |

## Rescan Verification

- Inventory scan: clean (0 flagged credential attributes)
- Gitleaks scan: clean
