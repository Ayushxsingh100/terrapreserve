# Licences

| Path | Licence | File |
|---|---|---|
| All code (`generator/`, `oracle/`, `tests/`, `validation/`, scripts, CI) | Apache-2.0 | [Apache-2.0.txt](Apache-2.0.txt), also [../LICENSE](../LICENSE) |
| `scenarios/` labels and our own data and documentation | CC-BY-4.0 | [CC-BY-4.0.txt](CC-BY-4.0.txt) |
| Files derived from TerraGoat | Apache-2.0 (TerraGoat's licence, kept) | [../pool/terragoat/aws/LICENSE.upstream](../pool/terragoat/aws/LICENSE.upstream) and [NOTICE](../pool/terragoat/aws/NOTICE) |
| Files derived from TerraDS | each source repository's own licence (D0 Decision 9) | one `LICENSE.upstream` per module under `../pool/terrads/`; the SPDX id is in `../pool/pool.json` |
| Checkov rule-library content | not yet established | not yet added |

The full licence texts were downloaded from apache.org and creativecommons.org, not retyped.

Source-derived files are committed under `pool/` (D3). The per-module licence file, its sha256 and the source commit are recorded next to the files (`SOURCE.json`, `LICENSE.upstream`) and in `pool/pool.json`; only repositories with a permissive licence were admitted (D3-01).
