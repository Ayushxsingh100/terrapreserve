# validation/d1_to_verify/

Evidence for D1 Prompt C: every `[TO VERIFY AT D1]` marker in DAIL's two specification documents, resolved against the pinned versions (Terraform `~> 1.15.0` / CI `1.15.8`, `hashicorp/aws` `6.53.0`, Checkov `3.3.30`).

| File or directory | What it is |
|---|---|
| `INVENTORY.md` | every marker found by `git grep` in DAIL's `docs/` at a pinned DAIL commit (`inventory.py` builds it) |
| `RESOLUTION.md` | one section per inventory item: outcome (`CONFIRMED`, `CHANGED` or `UNRESOLVED`), evidence, consequence, open question; summary table at the end |
| `schema/` | `terraform providers schema -json` for the pinned provider: the filtered schema of the ten types, all resource type names, the sha256 of the full 19 MB dump, and `schema_facts.txt` |
| `V01/` ... `V14/` | probes (`.tf`, `run.sh`, captured output); only the items that have an empirical probe have a directory |
| `V12/v12_unsupported_types.py` | the heuristic that lists provider resource types missing from the registry's unsupported lists (a human decides) |
| `common.sh`, `plan_facts.py`, `checkov_summary.py` | shared helpers for the probe scripts |

## Rules these probes follow

- **No credentials in any `.tf` file.** Mock credentials (`AWS_ACCESS_KEY_ID=mock`, `AWS_SECRET_ACCESS_KEY=mock`, `AWS_REGION=us-east-1`) are exported by `common.sh` only. Every provider block sets the four `skip_*` flags (the V01 control omits them on purpose).
- **No network use in a plan.** Each probe exports `HTTPS_PROXY`/`HTTP_PROXY` pointing at the unreachable `http://127.0.0.1:9`; V01 shows that the provider honours them.
- **No `terraform apply` against AWS.** `V10` applies only the built-in `terraform_data` resource to local state in a throw-away directory.
- **No DAIL code.** The scripts here import only the standard library; DAIL's documents are read as text by `inventory.py`.
- **Hand-written Terraform**, no TerraGoat or TerraDS content.

## Reproduce

```bash
# once: the pinned tools (Checkov) from the lock file
py -3.12 -m venv .venv-tools
.venv-tools/Scripts/python -m pip install -r requirements-tools.lock.txt

# per probe (needs terraform 1.15.x on PATH; downloads the provider on first init)
bash validation/d1_to_verify/V01/run.sh
bash validation/d1_to_verify/V08/run.sh      # also V09, V10, V05, V07
bash validation/d1_to_verify/V02/run.sh      # also V03, V04 (Checkov, offline)

# the schema artefacts, from the full dump
terraform -chdir=validation/d1_to_verify/schema init
terraform -chdir=validation/d1_to_verify/schema providers schema -json > schema_aws_6.53.0.json
python validation/d1_to_verify/schema/extract_schema.py schema_aws_6.53.0.json
python validation/d1_to_verify/V12/v12_unsupported_types.py schema_aws_6.53.0.json validation/d1_to_verify/V12/output
```

`common.sh` documents two optional, machine-local environment variables (`TF_CLI_CONFIG_FILE`, `TF_DATA_DIR`) used to install the provider from a local mirror when the registry download fails and to share one 880 MB provider directory between probes. They change where the identical `6.53.0` binary comes from, not which one is used.

`plan.json` files are the output of `terraform show -json` for a plan of mock-credential, offline configurations; they contain only the mock values written in the `.tf` files.
