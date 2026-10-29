# CLAUDE.md — TerraPreserve

Standing rules for every Claude Code session in this repository. Each work package comes with its own prompt. If that prompt and this file conflict, stop and ask.

## What this repository is

TerraPreserve is a benchmark dataset for Terraform invariant-preservation, built from TerraGoat, TerraDS and Checkov's rule library. It is the companion to DAIL (https://github.com/Ayushxsingh100/DAIL) and lives in its own repository (DAIL ADR-013). Authors: Ayush Kumar Singh and Krishika, UPES School of Computer Science.

## Rules

1. **Free of cost only.** No paid services, no licence keys, no trials.
2. **No fabrication.** Never invent a version, hash, URL, count or licence. If you did not measure or read it, write `not yet established`.
3. **Pins (ADR-013), identical to DAIL.**
   - Terraform `required_version = "~> 1.15.0"`; CI uses Terraform `1.15.8`.
   - `hashicorp/aws` exactly `6.53.0`.
   - Python 3.12.
   - Change a pin only when the prompt says so, and mirror the change in DAIL.
4. **Python standard library first.** Any third-party dependency needs an exact pin and a one-line justification in the PR description.
5. **Independence.** No file in this repository may import DAIL code or depend on the DAIL package, now or later (D0 gate 1, ADR-010). `tests/test_independence.py` enforces it.
6. **Sources and secrets.**
   - Large raw archives are never committed; they live in an external cache recorded in `sources/manifest.json`.
   - TerraGoat contains deliberate fake secrets. Never copy them unredacted into committed files (D0 gate 5).
   - Never commit real secrets. Fake secrets in tests are built at runtime.
7. **Labels come only from `oracle/`,** which never reads DAIL output and is written from the Invariant Registry Specification and from Terraform and AWS semantics (ADR-010).
8. **Every commit leaves CI green.** Open a PR and **never merge your own PR**; do not enable auto-merge. The user merges only after an external reviewer's verdict (DAIL rule C-28), using a merge commit (no squash) so SHAs cited in evidence stay valid.
9. **Line endings.** Text files are stored with LF (`.gitattributes`). CI runs on Linux and Windows.

## Git and GitHub

- Ask the user before pushing, opening or merging PRs, or changing repository or branch-protection settings, unless the current prompt authorises it.
- Never force-push or rewrite pushed history, never use `--no-verify`, never disable or weaken a CI job or gitleaks, never commit directly to `main` (the bootstrap commit was the one exception).
- Never run `terraform apply` or `terraform destroy`, and never use AWS credentials.

## Commands

```bash
python -m unittest discover -s tests -p "test_*.py"
terraform fmt -check -recursive validation   # first-party only; pool/ is verbatim third-party text
terraform -chdir=validation/smoke init -backend=false -lockfile=readonly
terraform -chdir=validation/smoke validate
```

Never report that tests pass without running them in the current session.
