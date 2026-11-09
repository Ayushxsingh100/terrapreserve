# Derived Native Redaction Log for Module 613257

This module is derived from a TerraDS native candidate excluded as E09.
The literal password attribute on `aws_db_instance` was replaced with `var.db_password`,
and a sensitive variable declaration was added without a default value.

| File | Line | Resource Address | Attribute | Replacement | SHA-256 Before | SHA-256 After |
|---|---|---|---|---|---|---|
| `main.tf` | 22 | `aws_db_instance.academia_rds` | `password` | `var.db_password` | `7d210bb6479dcc807b84aa429b4e3646ca9244c538d998d042ecb9507dfe35c4` | `2b597eec4f9c2a0650c04283ad568d22b3b2f6020625790cf8bdd6742ffbbf82` |

## Rescan Verification

- Inventory scan: clean (0 flagged credential attributes)
- Gitleaks scan: clean
