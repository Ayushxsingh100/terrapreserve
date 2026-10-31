# TerraPreserve Scenario Assembly Report (v1.0)

Assembly of the complete benchmark dataset across both tiers: controlled synthetic templates (D4a) and real-world TerraDS modules (D4b).

## Overall Summary

| Metric | Total | Dev Split | Test Split (Withheld) | Controlled Tier | Real-World Tier |
|---|---|---|---|---|---|
| **Benchmark Targets** | 320 | 224 | 96 | 160 | 160 |
| **Reserve Scenarios** | 96 | 64 | 32 | 48 | 48 |
| **Grand Total** | 416 | 288 | 128 | 208 | 208 |

## Real-World Tier Composition

- **Hosts (grafted):** 203
- **Original Natives (ungrafted):** 0
- **Derived Natives (redacted & ungrafted):** 5
- **Unique Modules Used:** 208 / 208 (no reuse)

## Lineage & Split Audit

- **Dev lineages/templates:** 151
- **Test lineages/templates:** 67
- **Overlap / Leakage across splits:** 0

## Breakdown by Family

| Family | Description | Targets | Reserves | Total | Dev | Test | Safe | Unsafe |
|---|---|---|---|---|---|---|---|---|
| F1 | Resource sizing and configuration updates | 40 | 12 | 52 | 36 | 16 | 26 | 26 |
| F2 | Network routing and CIDR modifications | 40 | 12 | 52 | 36 | 16 | 26 | 26 |
| F3 | Security group ingress/egress rules | 40 | 12 | 52 | 36 | 16 | 26 | 26 |
| F4 | Storage volume and database engine settings | 40 | 12 | 52 | 36 | 16 | 26 | 26 |
| F5 | Count and meta-argument restructuring | 40 | 12 | 52 | 36 | 16 | 26 | 26 |
| F6 | Resource additions and associations | 40 | 12 | 52 | 36 | 16 | 26 | 26 |
| F7 | Resource removals and disassociations | 40 | 12 | 52 | 36 | 16 | 26 | 26 |
| F8 | Multi-step chained refactoring workflows | 40 | 12 | 52 | 36 | 16 | 26 | 26 |

## Breakdown by Cell (16 Cells)

| Cell | Family | Class | Targets (Dev / Test) | Reserves (Dev / Test) | Cell Total (Dev / Test) |
|---|---|---|---|---|---|
| F1_safe | F1 | safe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F1_unsafe | F1 | unsafe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F2_safe | F2 | safe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F2_unsafe | F2 | unsafe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F3_safe | F3 | safe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F3_unsafe | F3 | unsafe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F4_safe | F4 | safe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F4_unsafe | F4 | unsafe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F5_safe | F5 | safe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F5_unsafe | F5 | unsafe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F6_safe | F6 | safe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F6_unsafe | F6 | unsafe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F7_safe | F7 | safe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F7_unsafe | F7 | unsafe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F8_safe | F8 | safe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
| F8_unsafe | F8 | unsafe | 20 (14 / 6) | 6 (4 / 2) | 26 (18 / 8) |
