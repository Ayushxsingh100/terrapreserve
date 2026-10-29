# pool/

The committed pool of Terraform sources that scenario construction (D4) draws base states from: real-world TerraDS modules, and the controlled TerraGoat tier. Built by D3. The numbers are in [POOL_REPORT.md](POOL_REPORT.md); nothing in this file is a count.

Pool filtering and reading use our own lexical reader (`sources/hcl_lex.py`), TerraDS metadata and Terraform's own tooling, never DAIL's parser or a list of what DAIL can parse (DAIL ADR-013, D3-02). Nothing here imports DAIL; `tests/test_independence.py` walks this directory too.

## Layout

| Path | What it is |
|---|---|
| `terrads/native/<module_id>/` | accepted modules that already hold `aws_instance` and `aws_db_instance` |
| `terrads/host/<module_id>/` | accepted graft hosts, at most one per lineage |
| `terragoat/aws/` | the controlled tier: TerraGoat `terraform/aws/*.tf` with credential-like attributes deleted, `REDACTION_LOG.md`, `NOTICE`, `LICENSE.upstream` |
| `pool.json` | one entry per accepted module (schema D3-08): identity, commit, licence and its file hash, lineage, file hashes, resources, flags, graft facts, scan and validate results |
| `exclusions.csv` | one row per candidate considered and not accepted, with the first exclusion code; `NOT_PROCESSED` rows are hosts the stop rule never reached |
| `funnel.json` | counts at every stage, per candidate set |
| `lineages.json` | lineage id to repositories and modules, the method and its limits |
| `licence_checks.csv` | result of every upstream licence-file fetch (committed so reruns need no network) |
| `validate_results.csv` | result of every `terraform validate` run |
| `POOL_REPORT.md` | generated; every number is computed from the files above |

Each module directory holds the module's `.tf` files, `SOURCE.json` (provenance, `archive_sha256` of the archive bytes) and `LICENSE.upstream` (the licence file fetched at the pinned commit).

## Rules

- Third-party text is **verbatim**: the only change is CRLF read as LF (`.gitattributes` stores text with LF). A real-world module with a secret finding is excluded, never edited. The only edited text is TerraGoat, and every deletion is logged by file, line, resource address and attribute name, never a value.
- Only repositories whose licence is in the `permissive` bucket of `sources/terrads/measure_yield.py` enter the pool, and each accepted module's upstream licence file at the pinned commit names the same SPDX id (D3-01, E11).
- The files that Terraform validated were a **neutralised copy** (top-level `terraform` and `provider` blocks removed, one pin file added); the committed files are not neutralised. See `docs/D4_CARRYOVER.md`.
- The pool is a selection of small, self-contained, secret-free modules; it is not representative of Terraform in the wild.

## Rebuild

```powershell
py -3.12 -m pool.build filter      # E01 to E08 over the pinned TerraDS archive (reads it in memory)
py -3.12 -m pool.build lineage     # lineages over the survivors
py -3.12 -m pool.build process     # E09, E11, E12; resumable; needs gitleaks 8.30.1, network for licence files, local Terraform 1.15.x and the provider mirror
py -3.12 -m pool.build terragoat   # redacted controlled tier
py -3.12 -m pool.build assemble    # writes this directory, the DATASHEET pool section and docs/D4_CARRYOVER.md
```

Intermediate files live in `<cache>/d3-work`, outside the repository. `tests/test_pool_integrity.py` checks the committed pool offline.
