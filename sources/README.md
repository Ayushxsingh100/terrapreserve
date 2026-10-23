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
| `terrads/SCHEMA.md` | tables, columns, types and row counts of the pinned `TerraDS.sqlite` |
| `terrads/measure_yield.py` | the funnel F0..X, written to `yield.json`, `yield_report.md`, `candidates.csv`, `licence_inventory.csv` |
| `terrads/scan_archive.py` | lists the pinned `TerraDS.tar.gz` and records which repositories ship a licence file |

## Reference tool

Checkov is a **reference tool only** (DAIL register C-12). It is installed into `.venv-tools` (gitignored) from `requirements-tools.txt`; nothing in `generator/` or `oracle/` may import it.

```powershell
py -3.12 -m venv .venv-tools
.venv-tools\Scripts\python -m pip install -r requirements-tools.txt
$env:PATH = "$PWD\.venv-tools\Scripts;$env:PATH"   # checkov.cmd runs the first `python` on PATH
checkov --version
```

Only `checkov` itself is pinned (`==3.3.30`); its transitive dependencies resolve at install time and are not pinned.
