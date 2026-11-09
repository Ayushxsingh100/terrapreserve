# oracle/

The independent oracle that will produce every ground-truth label (D5). It is written only from the Invariant Registry Specification (DAIL `docs/specs/INVARIANT_REGISTRY_v1.md`, tag `registry-v1.0`, read as a specification), Terraform semantics and AWS semantics. It never reads DAIL code, guides, prompts or output (DAIL ADR-010).

**Status (D5a, version `oracle-0.1`): skeleton only. There is no invariant evaluator and no label.** `record.py` writes dry-run records whose truth values are all `null`.

| File | Role |
|---|---|
| `VERSION.py` | `ORACLE_VERSION = "oracle-0.1"` (D5-02). |
| `inputs.py` | Builds the oracle's private working copy of a step (the step's `.tf` files, the oracle-only provider block `zz_oracle_provider.tf`, `terraform.tfvars.json` from the scenario's `variable_values`). Also writes the Terraform environment and CLI configuration for offline runs (D5-04). It never writes into `scenarios/` or the private test split. |
| `record.py` | Writes the D0 Decision 6 `labels` and `oracle` structures. D5a: dry run only, every truth value `null`. |

Rules (enforced by `tests/test_independence.py`, `TestOracleIndependence`, D5-03):

- Files under `oracle/` import only the Python standard library and `oracle` itself. They import nothing from `generator/`, `pool/`, `sources/`, `tests/` or `tools/`, and they do not edit `sys.path`. In particular, the generator's `realworld/modread.py` and the tests' self-check evaluators are never imported.
- Nothing outside `oracle/` and `tools/` writes a non-null `labels`, `gt_class` or `oracle` field. Committed scenarios keep all three `null` until the D5b labelling run.

Offline runs (D5-04). Terraform runs with:

- a provider block that has placeholder keys built at run time (never real, not credential-shaped), the four `skip_*` flags, and `max_retries = 1` (an attempted AWS call fails on its first refusal instead of being retried for minutes);
- no AWS environment variables, and empty shared credentials and config files;
- the instance metadata service disabled;
- a CLI configuration that installs `hashicorp/aws` 6.53.0 only from the local filesystem mirror (`~/.terrapreserve-cache/tf-mirror`), with no registry download;
- HTTP(S) proxies set to a closed local port.

Any attempt to reach an AWS endpoint therefore fails on this machine and is recorded as a failure, not worked around.
