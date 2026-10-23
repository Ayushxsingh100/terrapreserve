# sources/

Acquisition, pinning and measurement of the three upstream sources: TerraGoat, TerraDS and Checkov. Written for D1 Prompt B.

**The raw files are deliberately not in Git.** Large archives and clones live in an external cache (`$TERRAPRESERVE_CACHE`, default `%USERPROFILE%\.terrapreserve-cache`, always outside the repository). Only the manifest, measurement scripts, small metadata and reports are committed. TerraGoat contains deliberate fake secrets, so none of its file contents is committed either (D0 gate 5).

## Reproduce the cache

```powershell
py -3.12 sources/acquire.py plan     # sizes from the Zenodo / PyPI / GitHub APIs, free-disk check, no download
py -3.12 sources/acquire.py fetch    # download into the cache, check md5 against Zenodo, hash, write manifest.json
py -3.12 sources/acquire.py verify   # re-hash the cache against manifest.json; exit code 1 on any mismatch
```

`plan` and `fetch` need the network; `verify` does not. Once `manifest.json` exists, `fetch` re-acquires exactly the pinned commit, record and wheel; it only resolves "latest" for an entry that is missing. `fetch` stops if the free space is below 3 × the download plus an extraction budget, and stops on any md5 or sha256 mismatch.

Stdlib only; no third-party package is needed to acquire or measure.

## Contents

| Path | What it is |
|---|---|
| `acquire.py` | `plan` / `fetch` / `verify` |
| `manifest.json` | one entry per downloaded artefact: version or commit, retrieval time, size, measured sha256, published md5 (Zenodo), SPDX licence and the sha256 of the licence text read |
| `tools.py` | installs the pinned helper tools into the cache: gitleaks (CI version), Go, and a build of terraform-config-inspect at a pinned commit |
| `terragoat/files.sha256` | `sha256  size  path` for every file under `terraform/aws/` at the pinned commit |
| `terragoat/scan_secrets.py`, `terragoat/secret_scan_summary.md` | gitleaks run with `--redact`; counts per rule and file paths only, no values |
| `terragoat/attribute_inventory.py` | second, rule-independent inventory of credential-like attributes (file, line, resource address, attribute name; no values); appended to the summary |
| `terragoat/licence_diff.py`, `terragoat/licence_diff.md` | whitespace-normalised diff of TerraGoat's `LICENSE` against `LICENSES/Apache-2.0.txt` |
| `hcl_lex.py` | stand-alone lexer for `.tf` / `.tf.json` text (comments, heredocs, strings, block headers); used by the two scripts that read HCL |
| `terrads/lexical_crosscheck.py`, `terrads/crosscheck.json` | independent re-derivation of module contents from the archive, compared with TerraDS's metadata |
| `terrads/SCHEMA.md` | tables, columns, types and row counts of the pinned `TerraDS.sqlite` |
| `terrads/measure_yield.py` | the funnel F0..X, written to `yield.json`, `yield_report.md`, `candidates.csv`, `licence_inventory.csv` |
| `terrads/scan_archive.py` | lists the pinned `TerraDS.tar.gz` and records which repositories ship a licence file |

## Reference tool

Checkov is a **reference tool only** (DAIL register C-12). It is installed into `.venv-tools` (gitignored); nothing in `generator/` or `oracle/` may import it. `requirements-tools.txt` pins Checkov itself (`==3.3.30`); `requirements-tools.lock.txt` is the full environment, the output of `python -m pip freeze --all` in `.venv-tools` (its sha256 is in `manifest.json`, entry `checkov`, field `lock_file`, and `acquire.py verify` checks it).

**Later runs must install from the lock file and put `.venv-tools\Scripts` first on PATH** (the `checkov.cmd` launcher runs the first `python` on PATH):

```powershell
py -3.12 -m venv .venv-tools
.venv-tools\Scripts\python -m pip install -r requirements-tools.lock.txt
$env:PATH = "$PWD\.venv-tools\Scripts;$env:PATH"
checkov --version
```

The lock file was produced on Windows with Python 3.12.10; another platform may need its own freeze.
