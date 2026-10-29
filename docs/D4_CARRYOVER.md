# D4 carry-over

Facts that D4 (scenario construction) inherits from D3. Facts only: each item cites the committed file that shows it, and decides nothing. Where a value was not measured the item says `not yet established`. Counts are computed from the committed pool files by `pool/report.py`.

## 1. The neutralisation that `terraform validate` was run on (D3-09)

Pool files are verbatim; the copy that Terraform read was transformed as follows. D3-09 records that D4 must reproduce this transformation when it builds scenarios, so that a scenario step is validated under the same conditions. Implementation: `pool/validate.py` (`neutralise`, `PINS_TF`, `Harness`).

- every top-level `terraform` block and every top-level `provider` block is removed from every `.tf` file (found by brace depth with `sources/hcl_lex.py`); nested blocks such as `provider = aws.alias` inside a resource are kept, so a reference to a removed provider alias is invalid.
- one extra file `terrapreserve_versions.tf` is added (not `versions.tf`, because a module may own that name) with exactly the text of `validation/smoke/versions.tf`: Terraform `~> 1.15.0` and `hashicorp/aws` `6.53.0`.
- `terraform init -backend=false` against a local filesystem mirror of `hashicorp/aws` 6.53.0, then `terraform validate -json`; the result's `error_class` is the first error diagnostic's summary, at most 200 characters.
- results per module: `pool/validate_results.csv`; versions used: Terraform 1.15.8, hashicorp/aws 6.53.0.

## 2. Pool entries (`pool/pool.json`, schema D3-08)

- 1 native and 400 host entries, plus 1 TerraGoat entry (`kind: terragoat`, `module_id: null`, `lineage_id: null`: the lineage split of D0 Decision 7 applies to the real-world tier).
- each entry carries identity, source commit, licence and its file hash, lineage id, file hashes, resources, type counts, construct flags, graft facts, secrets (0/0) and the validate result; it carries no scenario field, no label and no judgement of safety.
- text files are stored with LF; where the archive had CRLF the original sha256 is kept in the module's `SOURCE.json` (`archive_sha256`, `crlf_normalised`).

## 3. Canonical-core collisions per host (graft facts)

The canonical core addresses are `pool/assemble.py` `CORE_ADDRESSES` (Doc 04 Appendix B as the D2 fixture names them). 74 of 401 accepted real-world modules define at least one of them (`graft_facts.colliding_addresses` in `pool/pool.json`):

| Pool id | Colliding addresses |
|---|---|
| terrads-host-285149 | `aws_vpc.main` |
| terrads-host-304640 | `aws_internet_gateway.igw` |
| terrads-host-312811 | `aws_security_group.db` |
| terrads-host-318483 | `aws_internet_gateway.igw` |
| terrads-host-335802 | `aws_internet_gateway.igw` |
| terrads-host-339060 | `aws_vpc.main` |
| terrads-host-348050 | `aws_internet_gateway.igw` |
| terrads-host-365623 | `aws_vpc.main` |
| terrads-host-376193 | `aws_internet_gateway.igw` |
| terrads-host-381211 | `aws_vpc.main` |
| terrads-host-421433 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-424306 | `aws_vpc.main` |
| terrads-host-427724 | `aws_security_group.db` |
| terrads-host-428862 | `aws_vpc.main` |
| terrads-host-445018 | `aws_vpc.main` |
| terrads-host-447252 | `aws_vpc.main` |
| terrads-host-455597 | `aws_internet_gateway.igw` |
| terrads-host-459053 | `aws_vpc.main` |
| terrads-host-467559 | `aws_internet_gateway.igw` |
| terrads-host-471864 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-480850 | `aws_internet_gateway.igw` |
| terrads-host-483978 | `aws_vpc.main` |
| terrads-host-495011 | `aws_vpc.main` |
| terrads-host-498497 | `aws_vpc.main` |
| terrads-host-500370 | `aws_vpc.main` |
| terrads-host-500651 | `aws_route_table.public`, `aws_subnet.app`, `aws_vpc.main` |
| terrads-host-511406 | `aws_vpc.main` |
| terrads-host-542311 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-546940 | `aws_subnet.app`, `aws_vpc.main` |
| terrads-host-571528 | `aws_vpc.main` |
| terrads-host-572127 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-572557 | `aws_internet_gateway.igw`, `aws_route_table.public` |
| terrads-host-574140 | `aws_internet_gateway.igw`, `aws_vpc.main` |
| terrads-host-574168 | `aws_internet_gateway.igw`, `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-574664 | `aws_vpc.main` |
| terrads-host-578060 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-583351 | `aws_internet_gateway.igw` |
| terrads-host-584631 | `aws_vpc.main` |
| terrads-host-590936 | `aws_vpc.main` |
| terrads-host-598919 | `aws_instance.app`, `aws_route_table.public`, `aws_subnet.app`, `aws_vpc.main` |
| terrads-host-602000 | `aws_internet_gateway.igw` |
| terrads-host-603732 | `aws_vpc.main` |
| terrads-host-611628 | `aws_internet_gateway.igw`, `aws_vpc.main` |
| terrads-host-614864 | `aws_vpc.main` |
| terrads-host-614897 | `aws_instance.app` |
| terrads-host-615115 | `aws_internet_gateway.igw`, `aws_security_group.db`, `aws_vpc.main` |
| terrads-host-618950 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-621360 | `aws_route_table.public` |
| terrads-host-621457 | `aws_vpc.main` |
| terrads-host-622487 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-625782 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-626350 | `aws_vpc.main` |
| terrads-host-633390 | `aws_route_table.public` |
| terrads-host-636415 | `aws_route_table.public` |
| terrads-host-642459 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-642735 | `aws_internet_gateway.igw`, `aws_vpc.main` |
| terrads-host-654487 | `aws_internet_gateway.igw`, `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-656095 | `aws_vpc.main` |
| terrads-host-656404 | `aws_security_group.app`, `aws_security_group.db` |
| terrads-host-656854 | `aws_vpc.main` |
| terrads-host-658381 | `aws_security_group.app` |
| terrads-host-665769 | `aws_route_table.public` |
| terrads-host-667031 | `aws_security_group.db` |
| terrads-host-667306 | `aws_internet_gateway.igw` |
| terrads-host-669257 | `aws_internet_gateway.igw` |
| terrads-host-670362 | `aws_internet_gateway.igw`, `aws_route_table.public` |
| terrads-host-671242 | `aws_internet_gateway.igw`, `aws_security_group.app` |
| terrads-host-672445 | `aws_route_table.public` |
| terrads-host-673189 | `aws_security_group.db` |
| terrads-host-673677 | `aws_route_table.public` |
| terrads-host-674349 | `aws_internet_gateway.igw` |
| terrads-host-678923 | `aws_vpc.main` |
| terrads-host-680601 | `aws_route_table.public`, `aws_vpc.main` |
| terrads-host-682647 | `aws_security_group.app` |

## 4. Construct flags

Counts of accepted modules with each flag are in `pool/POOL_REPORT.md` (section "Constructs and graft facts") and per entry in `pool/pool.json` (`flags`). Data sources, `count`, `for_each`, `dynamic`, `locals`, `lifecycle` and provisioners are flags, not exclusions (D3-06).

## 5. Lineages

- 3,060 lineages over the candidates that passed E01 to E08; ids and members in `pool/lineages.json`; at most one accepted host per lineage; natives keep all lineage members.
- method: `pool/lineages.json` (`method`); rule c counts a file only from 30 normalised tokens up (user decision, 30 Oct 2026; effect in `comparison`).
- limits: TerraDS has no fork flag. A fork that diverged below Jaccard 0.8 in every rule is not detected: how many such forks exist is not yet established. Copies whose files were renamed or split are found only through rules b, c and d. Rule d compares token windows of the module's own files; a copy that reorders or inlines its files into another structure is not recognised unless the windows still overlap.

## 6. What E12 excluded

- 125 candidates were excluded by `terraform validate` under the pins (rows with code `E12_INVALID_UNDER_PIN` in `pool/exclusions.csv`); first error classes:

| Count | Status and first error summary |
|---:|---|
| 34 | invalid: Invalid quoted type constraints |
| 24 | invalid: Unsupported block type |
| 20 | invalid: Missing required provider |
| 9 | invalid: Reference to undeclared input variable |
| 7 | invalid: Unsupported argument |
| 5 | invalid: Error in function call |
| 3 | invalid: Incorrect attribute value type |
| 3 | invalid: Invalid function argument |
| 2 | invalid: Reference to undeclared resource |
| 2 | invalid: Unsupported attribute |

## 7. Yield facts

- Natives considered 133, accepted 1; hosts considered 8,542, accepted 400, not processed 2,381 (`pool/funnel.json`).
- Real-world slots are 160 (D0 Decision 3); the shortfall, if any, is in `pool/POOL_REPORT.md` and was not filled.
- Natives excluded at E09: 120 of 133; 114 of those have a flagged literal `password` attribute (`pool/exclusions.csv`, code `E09_SECRET_FOUND`, column `group`). Real-world text was not edited.

## 8. Not yet established

- how many forks diverged below the lineage thresholds and so are not detected;
- whether DAIL parses any pooled module (measured later in the DAIL repository; never fed back into selection);
- behaviour of any pooled module under `terraform plan` (not run: no credentials);
- the GitHub repository id of TerraGoat (its entry has no repository id and no lineage id);
- whether the modules excluded by `terraform validate` would validate under a different provider version (not tested).
