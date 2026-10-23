# D3 carry-over

Facts that D3 (pool construction) inherits from D1. Facts only: each item cites the committed file that shows it, and decides nothing. Where a value is not recorded in the repository the item says `not yet established`.

## 1. TerraGoat secrets: redact before anything enters `pool/`

- `terraform/aws/providers.tf` has literal `access_key` (line 10) and `secret_key` (line 11) attributes on the `aws` provider. `terraform/aws/db-app.tf` (line 252, `aws_instance.db_app`) and `terraform/aws/ec2.tf` (line 9, `aws_instance.web_host`) have `user_data` heredocs. This is a rule-independent inventory of 4 flagged attributes.
- gitleaks (8.30.1, working tree) covered 1 of the 4 (`ec2.tf`) and missed 3: the two `providers.tf` attributes and the `db-app.tf` heredoc.
- Every flagged file must be redacted before anything enters `pool/` (D0 gate 5).
- Shown in: `sources/terragoat/secret_scan_summary.md` ("Rule-independent attribute inventory"; the line "D3 must redact the files listed below before anything enters `pool/`"). Method: `sources/terragoat/attribute_inventory.py`, `sources/terragoat/scan_secrets.py`.

## 2. Three TerraDS modules use symlinked `.tf` files that are absent from the archive

- Modules `298829`, `311156` and `405005` have `.tf` files that are git symlinks (mode 120000 in the GitHub git-trees API at the pinned commit). The archive holds only regular files, so the definitions behind the symlinks are not in the archived text, and TerraDS's metadata and the lexical re-reading disagree on their resource types.
- Shown in: `sources/terrads/yield_report.md`, section "Disagreements (6)", rows `298829`, `311156`, `405005` (lines 197, 198 and 201); data in `sources/terrads/crosscheck.json` and `sources/terrads/crosscheck_causes.json`.

## 3. Analyser diagnostics and HCL syntax errors

- 156 of the 20,903 F2 modules have non-empty `DiagnosticMessages`, so their resource lists may be incomplete. They stay in the funnel and carry `has_diagnostics` in `sources/terrads/candidates.csv`. Shown in: `sources/terrads/yield_report.md` line 43.
- Three modules in the cross-check sample, `367075`, `381210` and `625313`, disagree between TerraDS and the lexical re-reading because of HCL syntax errors that made the analyser drop blocks. Shown in: `sources/terrads/yield_report.md` section "Disagreements (6)" (lines 199, 200 and 202). How many of the 156 contain syntax errors (as opposed to other diagnostics): `not yet established`.

## 4. Licences come from crawl-time metadata

- TerraDS's licence for a repository is the GitHub API `license.spdx_id` at search time, stored in `Repositories.License`; it is `null` when GitHub reported none. The archive contains no licence file: 0 licence-like files in the F2 repositories and in the 106 F3 repositories. Shown in: `sources/terrads/yield_report.md` line 17 and section "Archive checks".
- Re-verification of the licences of the selected repositories through the GitHub API at a pinned commit: `not yet established` (no such record exists in the repository).

## 5. Pending author decisions on licences

- Strings that match no list and stay `other/unknown`: `UPL-1.0`, `WTFPL`, `CC-BY-SA-4.0`, `EUPL-1.2`, `CC-BY-4.0`, `BSD-3-Clause-Clear`, `AFL-3.0`, `BSD-4-Clause`, `CECILL-2.1`, plus `NOASSERTION` and null. Shown in: `sources/terrads/yield_report.md` line 132 and the licence table above it; rules in `sources/terrads/measure_yield.py`; per-string counts in `sources/terrads/licence_inventory.csv`.
- Whether copyleft repositories (weak copyleft: MPL-2.0, LGPL-\*, EPL-\*; strong copyleft: GPL-\*, AGPL-\*) enter the pool is "a D3 decision for the user". Shown in: `sources/terrads/yield_report.md` line 75. The bucket counts are in the same report (F2: weak copyleft 1,622 modules / 1,130 repositories, strong copyleft 2,282 / 1,112; F3: 4 / 3 and 23 / 14).

## 6. Nine F2 repositories have fewer module directories in the archive than module rows

- For 9 of the 9,220 F2 repositories the number of `*.tf` directories in the archive differs from the number of module rows in the database; in all 9 the archive has fewer. Repository ids with both counts: `sources/terrads/yield.json`, key `module_dir_count_mismatches`. The F2 repositories' directory sets differ from the database's module paths in the same 9. Shown in: `sources/terrads/yield_report.md` line 213.

## 7. Arithmetic of the real-world slots (no decision)

- Real-world slots: 160 (8 families x 20; D0 Decision 3 as quoted in the Prompt B), `sources/terrads/yield_report.md` line 219.
- Native F3 permissive: 133 modules in 89 repositories (`sources/terrads/yield_report.md` line 85 and the table in "What this means for D3"; 133 - 160 = -27 modules, 89 - 160 = -71 repositories).
- Permissive graft hosts (level G): 8,542 modules in 5,029 repositories after the reviewer-approved permissive list change (line 93; 8,463 / 4,967 before it).
- The grafting ratio is a D3 decision; nothing here chooses it.

## 8. File-size cap

- `sources/terrads/candidates.csv` is 3,733,637 bytes (3.7 MB). The per-file cap enforced by `tests/test_no_large_or_raw_files.py` (line 10) is 5 MiB (5,242,880 bytes). Headroom: 1,509,243 bytes.
