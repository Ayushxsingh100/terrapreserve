"""Assemble the committed pool from the saved results (D3 step 6). No network, no Terraform, no gitleaks.

Writes ``pool/terrads/<kind>/<module_id>/`` (verbatim ``.tf`` files, ``SOURCE.json``, ``LICENSE.upstream``),
``pool.json``, ``exclusions.csv``, ``funnel.json``, ``lineages.json`` and ``validate_results.csv`` from the work
directory's saved results; ``report.py`` writes ``POOL_REPORT.md`` from the same data. Every number is
computed here, none is typed.

Pool ``.tf`` files are verbatim copies of the archive text with one normalisation: CRLF line endings become LF
(``.gitattributes`` stores text with LF, and a hash must survive a checkout). The sha256 of the archive bytes is
kept in each ``SOURCE.json``. Standard library and ``sources/*`` only.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import hcl_lex
import measure_yield as my

from pool import cascade, licence

SCHEMA = "D3-08"
TERRADS_RECORD = {"record_id": "20339474", "doi": "10.5281/zenodo.20339474", "concept_doi": "10.5281/zenodo.14217385"}
PINS = {"terraform_required_version": "~> 1.15.0", "terraform_ci_version": "1.15.8", "aws_provider": "6.53.0",
        "python": "3.12", "gitleaks": "8.30.1"}
TYPES = sorted(my.S)  # the nine supported types plus aws_db_subnet_group (C-67)
# Canonical core addresses: Doc 04 Appendix B as the D2 fixture names them (a constant list, not an import).
CORE_ADDRESSES = (
    "aws_vpc.main", "aws_internet_gateway.igw", "aws_route_table.public", "aws_route_table_association.app",
    "aws_subnet.app", "aws_subnet.db_a", "aws_subnet.db_b", "aws_db_subnet_group.db", "aws_security_group.app",
    "aws_security_group.db", "aws_security_group_rule.app_ssh_public", "aws_security_group_rule.app_to_db_5432",
    "aws_security_group_rule.app_egress_all", "aws_instance.app", "aws_db_instance.database",
)
KIND_ORDER = {"native": 0, "host": 1, "terragoat": 2}
SLOTS = 160  # real-world slots: 8 families x 20 (D0 Decision 3)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(document) -> str:
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


# --------------------------------------------------------------------------- facts


def module_hash(file_entries: list[dict]) -> str:
    """sha256 of the sorted ``<path>:<sha256>`` lines of the committed files (an integrity hash of the module)."""
    lines = "".join(f"{f['path']}:{f['sha256']}\n" for f in sorted(file_entries, key=lambda f: f["path"]))
    return sha256_bytes(lines.encode("utf-8"))


def module_facts(texts: dict[str, str]) -> dict:
    """Resources, type counts, construct flags and graft facts of one module, read lexically."""
    parts = [hcl_lex.headers_from_hcl(t) for _, t in sorted(texts.items())]
    merged = hcl_lex.merge(parts)
    constructs = hcl_lex.merge_constructs([hcl_lex.constructs_from_hcl(t) for _, t in sorted(texts.items())])
    resources = sorted(f"{t}.{n}" for t, n in merged.managed)
    types = collections.Counter(t for t, _ in merged.managed)
    present = {t for t, _ in merged.managed}
    data_sources = sorted(f"{t}.{n}" for t, n in merged.data)
    return {
        "resources": resources,
        "type_counts": {t: types.get(t, 0) for t in TYPES},
        "flags": {
            "has_data_sources": bool(data_sources), "data_sources": data_sources,
            "has_count": constructs.has_count, "has_for_each": constructs.has_for_each,
            "has_dynamic": constructs.has_dynamic, "has_locals": constructs.has_locals,
            "has_lifecycle": constructs.has_lifecycle, "has_provisioner": constructs.has_provisioner,
            "has_terraform_block": constructs.has_terraform_block, "has_backend": constructs.has_backend,
            "has_provider_block": constructs.has_provider_block,
            "provider_constraints": sorted(constructs.provider_constraints),
            "terraform_required_version": constructs.terraform_required_version,
        },
        "graft_facts": {
            "has_vpc": "aws_vpc" in present, "has_subnet": "aws_subnet" in present,
            "has_security_group": "aws_security_group" in present,
            "has_security_group_rule": "aws_security_group_rule" in present,
            "has_igw": "aws_internet_gateway" in present, "has_route_table": "aws_route_table" in present,
            "has_db_subnet_group": "aws_db_subnet_group" in present,
            "colliding_addresses": sorted(set(resources) & set(CORE_ADDRESSES)),
            "ec2_rds_pair": {"aws_instance", "aws_db_instance"} <= present,
        },
    }


# --------------------------------------------------------------------------- inputs


@dataclass
class Inputs:
    candidates: list[cascade.Candidate]
    cheap: dict[int, tuple[str, str, str]]  # module id -> (code, detail, group) for those that failed E01..E08
    plan: cascade.Plan
    records: dict[int, dict]
    lineage_of: dict[int, str]
    lineage_stats: dict
    lineage_merges: dict
    lineage_comparison: dict[str, dict]
    licence_checks: dict[int, licence.Check]
    stage_dir: Path
    licence_cache: Path
    funnel_levels: dict
    e01_not_candidates: dict[str, int]
    terragoat_dir: Path | None = None
    terragoat_validate: dict | None = None
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- entries


def _terrads_entry(inp: Inputs, c: cascade.Candidate, pool_dir: Path) -> dict:
    record = inp.records[c.module_id]
    check = inp.licence_checks[c.repo_id]
    raw = {p.name: p.read_bytes() for p in sorted((inp.stage_dir / str(c.module_id)).glob("*.tf"))}
    normalised = {name: data.replace(b"\r\n", b"\n") for name, data in raw.items()}
    rel = f"terrads/{c.kind}/{c.module_id}"
    target = pool_dir / rel
    target.mkdir(parents=True, exist_ok=True)
    files = []
    for name, data in normalised.items():
        (target / name).write_bytes(data)
        files.append({"path": name, "sha256": sha256_bytes(data), "bytes": len(data)})
    licence_raw = licence.cached_text(inp.licence_cache, check)
    if licence_raw is None or sha256_bytes(licence_raw) != check.sha256:
        raise RuntimeError(f"module {c.module_id}: the licence file of repository {c.repo_id} is not in the cache "
                           f"or its sha256 differs from licence_checks.csv")
    licence_bytes = licence_raw.replace(b"\r\n", b"\n")
    (target / "LICENSE.upstream").write_bytes(licence_bytes)
    source = {
        "pool_id": f"terrads-{c.kind}-{c.module_id}", "kind": c.kind, "module_id": c.module_id, "repo_id": c.repo_id,
        "repo_full_name": c.full_name, "module_path": c.path, "commit_sha": c.commit_sha,
        "terrads": TERRADS_RECORD, "licence_spdx": c.licence,
        "licence_source_file": check.file_name,
        "licence_upstream_sha256": check.sha256,
        "archive_sha256": {name: sha256_bytes(data) for name, data in sorted(raw.items())},
        "crlf_normalised": sorted(name for name in raw if raw[name] != normalised[name]),
        "note": "Verbatim copy of the TerraDS archive text (CRLF read as LF). The terraform validate step used the "
                "neutralised copy described in pool/validate.py; these files are not neutralised.",
    }
    write_text(target / "SOURCE.json", canonical_json(source))
    extra = []
    for name in ("LICENSE.upstream", "SOURCE.json"):
        data = (target / name).read_bytes()
        extra.append({"path": name, "sha256": sha256_bytes(data), "bytes": len(data)})
    texts = {name: data.decode("utf-8", errors="replace") for name, data in normalised.items()}
    facts = module_facts(texts)
    secrets = record["secrets"]
    return {
        "pool_id": source["pool_id"], "kind": c.kind, "dir": rel, "module_id": c.module_id, "repo_id": c.repo_id,
        "repo_full_name": c.full_name, "module_path": c.path, "commit_sha": c.commit_sha,
        "licence_spdx": c.licence, "licence_file": "LICENSE.upstream",
        "licence_file_sha256": sha256_bytes(licence_bytes),
        "lineage_id": inp.lineage_of[c.module_id],
        "files": files, "extra_files": extra, "module_hash": module_hash(files),
        **facts,
        "secrets": {"gitleaks_findings": secrets["gitleaks_findings"], "inventory_flagged": secrets["inventory_flagged"]},
        "validate": dict(record["validate"]),
    }


def _terragoat_entry(inp: Inputs, pool_dir: Path) -> dict | None:
    if inp.terragoat_dir is None or not (inp.terragoat_dir / "SOURCE.json").is_file():
        return None
    source = json.loads((inp.terragoat_dir / "SOURCE.json").read_text(encoding="utf-8"))
    rel = inp.terragoat_dir.relative_to(pool_dir).as_posix()
    files = [{"path": f["path"], "sha256": f["sha256"], "bytes": f["bytes"]} for f in source["files"]]
    texts = {f["path"]: (inp.terragoat_dir / f["path"]).read_text(encoding="utf-8") for f in files}
    extra = []
    for name in ("LICENSE.upstream", "NOTICE", "REDACTION_LOG.md", "SOURCE.json"):
        data = (inp.terragoat_dir / name).read_bytes()
        extra.append({"path": name, "sha256": sha256_bytes(data), "bytes": len(data)})
    return {
        "pool_id": "terragoat-aws", "kind": "terragoat", "dir": rel, "module_id": None, "repo_id": None,
        "repo_full_name": "bridgecrewio/terragoat", "module_path": source["directory"], "commit_sha": source["commit"],
        "licence_spdx": source["licence_spdx"], "licence_file": "LICENSE.upstream",
        "licence_file_sha256": source["licence_file_sha256"],
        "lineage_id": None,  # controlled tier: the lineage split (D0 Decision 7) applies to the real-world tier
        "files": files, "extra_files": extra, "module_hash": module_hash(files),
        **module_facts(texts),
        "secrets": {"gitleaks_findings": 0, "inventory_flagged": 0},
        "validate": inp.terragoat_validate or {"status": "not yet established", "terraform_version": "",
                                               "provider_version": "", "error_class": ""},
    }


# --------------------------------------------------------------------------- documents


def lineages_document(inp: Inputs, accepted_ids: set[int]) -> dict:
    by_id = {c.module_id: c for c in inp.candidates}
    members: dict[str, list[int]] = collections.defaultdict(list)
    for mid, lid in inp.lineage_of.items():
        members[lid].append(mid)
    lineages = {}
    for lid in sorted(members):
        mids = sorted(members[lid])
        repos = sorted({by_id[m].repo_id for m in mids})
        lineages[lid] = {
            "repositories": [{"repo_id": r, "full_name": next(by_id[m].full_name for m in mids if by_id[m].repo_id == r)}
                             for r in repos],
            "modules": [{"module_id": m, "kind": by_id[m].kind, "accepted": m in accepted_ids} for m in mids],
        }
    return {
        "method": {
            "rules": [
                "a: same repository",
                "b: identical normalised module text (comments and whitespace stripped; per-file hashes combined in sorted order)",
                "c: for modules with two or more files each, at least 50 percent of the files share a normalised hash; "
                "a file counts only from 30 normalised tokens up (user decision, 30 Oct 2026)",
                "d: 5-token shingle Jaccard of at least 0.8, found with MinHash (64 permutations, 16 bands of 4 rows, "
                "seed 20261030) and confirmed by exact Jaccard",
            ],
            "id": "lin- + the smallest repository id of the component, zero-padded to 12 digits",
            "computed_over": "every candidate that passed E01 to E08 (natives and hosts together)",
        },
        "limits": [
            "TerraDS has no fork flag. A fork that diverged below Jaccard 0.8 in every rule is not detected: "
            "how many such forks exist is not yet established.",
            "Copies whose files were renamed or split are found only through rules b, c and d.",
            "Rule d compares token windows of the module's own files; a copy that reorders or inlines "
            "its files into another structure is not recognised unless the windows still overlap.",
        ],
        "merges_by_rule": inp.lineage_merges,
        "stats": inp.lineage_stats,
        "comparison": inp.lineage_comparison,
        "lineages": lineages,
    }


def funnel_document(inp: Inputs, rows: list[dict], accepted: dict[str, int]) -> dict:
    counts = cascade.ledger_counts(rows, {k: sum(1 for c in inp.candidates if c.kind == k) for k in cascade.KINDS})
    by_code = {k: collections.Counter(r["code"] for r in rows if r["kind"] == k and r["status"] != "accepted")
               for k in cascade.KINDS}
    order = ["E02_NOT_IN_ARCHIVE", "E03_ANALYSER_DIAGNOSTICS", "E04_LEXER_ANOMALY", "E05_METADATA_DISAGREES",
             "E06_MODULE_CALLS", "E07_DANGLING_REFERENCE", "E08_OVERSIZE", "E10_LINEAGE_DUPLICATE",
             "E09_SECRET_FOUND", "E11_LICENCE_UNVERIFIED", "E12_INVALID_UNDER_PIN", cascade.NOT_PROCESSED]
    stages = {}
    for kind in cascade.KINDS:
        remaining = counts[kind]["considered"]
        steps = [{"stage": "considered (permissive, in the candidate set)", "excluded": 0, "remaining": remaining}]
        for code in order:
            n = by_code[kind].get(code, 0)
            remaining -= n
            steps.append({"stage": code, "excluded": n, "remaining": remaining})
        stages[kind] = steps
    return {
        "terrads_levels": inp.funnel_levels,
        "candidate_sets": {
            kind: {
                "level": level,
                "modules_at_level": inp.funnel_levels[level]["modules"],
                "removed_by_E01_licence_bucket": inp.e01_not_candidates[kind],
                "considered": counts[kind]["considered"],
            }
            for kind, level in (("native", "F3"), ("host", "G"))
        },
        "processing_order": "E01, E02..E08, then E10 (hosts only), then E09, E11, E12 (D3-10)",
        "stages": stages,
        "ledger": counts,
        "by_code": {k: dict(sorted(v.items())) for k, v in by_code.items()},
        "accepted": accepted,
        "sampling": {"seed": cascade.SEED, "host_accept_target": cascade.HOST_ACCEPT_TARGET,
                     "host_process_cap": cascade.HOST_PROCESS_CAP,
                     "hosts_after_E10": len(inp.plan.hosts),
                     "hosts_processed": sum(1 for h in inp.plan.hosts if h in inp.records),
                     "hosts_not_processed": counts["host"]["not_processed"]},
    }


def write_pool(inp: Inputs, pool_dir: Path) -> dict:
    """Write the module directories and the documents. Returns the documents (for the report)."""
    shutil.rmtree(pool_dir / "terrads", ignore_errors=True)
    by_id = {c.module_id: c for c in inp.candidates}
    rows = cascade.ledger(inp.candidates, inp.cheap, inp.plan, inp.records)
    entries = [_terrads_entry(inp, by_id[r["module_id"]], pool_dir) for r in rows if r["status"] == "accepted"]
    terragoat = _terragoat_entry(inp, pool_dir)
    if terragoat is not None:
        entries.append(terragoat)
    entries.sort(key=lambda e: (KIND_ORDER[e["kind"]], e["module_id"] or 0))
    accepted = {k: sum(1 for e in entries if e["kind"] == k) for k in KIND_ORDER}
    pool = {"schema": SCHEMA, "pins": PINS, "source": {"terrads": TERRADS_RECORD}, "entries": entries}
    write_text(pool_dir / "pool.json", canonical_json(pool))
    write_csv(pool_dir / "exclusions.csv",
              ["module_id", "repo_id", "repo_full_name", "module_path", "kind", "status", "code", "detail", "group"],
              [[r["module_id"], r["repo_id"], r["repo_full_name"], r["module_path"], r["kind"], r["status"], r["code"],
                r["detail"], r["group"]] for r in rows if r["status"] != "accepted"])
    funnel = funnel_document(inp, rows, accepted)
    write_text(pool_dir / "funnel.json", canonical_json(funnel))
    accepted_ids = {e["module_id"] for e in entries if e["module_id"] is not None}
    lineages = lineages_document(inp, accepted_ids)
    write_text(pool_dir / "lineages.json", canonical_json(lineages))
    validate_rows = []
    for mid in sorted(inp.records):
        v = inp.records[mid].get("validate")
        if v:
            validate_rows.append([mid, inp.records[mid]["kind"], by_id[mid].repo_id, v["status"], v["terraform_version"],
                                  v["provider_version"], v["error_class"]])
    if terragoat is not None:
        v = terragoat["validate"]
        validate_rows.append(["", "terragoat", "", v["status"], v["terraform_version"], v["provider_version"], v["error_class"]])
    write_csv(pool_dir / "validate_results.csv",
              ["module_id", "kind", "repo_id", "status", "terraform_version", "provider_version", "error_class"],
              validate_rows)
    checks = sorted({c.repo_id for c in inp.candidates if c.module_id in inp.records and inp.records[c.module_id]["licence"]})
    licence.write_checks(pool_dir / "licence_checks.csv", [inp.licence_checks[r] for r in checks])
    docs = {"pool": pool, "rows": rows, "funnel": funnel, "lineages": lineages, "inputs": inp}
    from pool import report  # imported late: report imports cascade, assemble is imported by build

    write_text(pool_dir / "POOL_REPORT.md", report.render(docs))
    return docs
