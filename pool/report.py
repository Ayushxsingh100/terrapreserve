"""POOL_REPORT.md and the offline integrity check of the committed pool (D3 step 6).

``verify_pool`` is the single definition of what a consistent pool is: every listed file exists with the listed
sha256 and size, nothing unlisted sits under ``pool/``, the ledger balances (considered = accepted + excluded +
not processed), every code is known, no accepted entry has a secret finding or a non-permissive licence, no two
accepted hosts share a lineage, ``lineages.json`` covers every accepted entry, sizes are within the caps, JSON is
canonical and every file is LF-only. The tests run it on a synthetic pool and on the committed one.

``render`` writes the report; every number in it is computed from the same documents. Standard library and
``sources/*`` only.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
from pathlib import Path

import measure_yield as my

from pool import cascade

MAX_TOTAL_BYTES = 30 * 1024 * 1024
MAX_FILE_BYTES = 5 * 1024 * 1024
ROOT_FILES = ("README.md", "pool.json", "exclusions.csv", "funnel.json", "lineages.json", "licence_checks.csv",
              "validate_results.csv", "POOL_REPORT.md")
TERRADS_KINDS = ("native", "host")


def _canonical(text: str) -> bool:
    try:
        return text == json.dumps(json.loads(text), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    except ValueError:
        return False


def verify_pool(pool_dir: Path, max_total: int = MAX_TOTAL_BYTES, max_file: int = MAX_FILE_BYTES) -> list[str]:
    """Every way in which ``pool_dir`` is inconsistent; an empty list means consistent."""
    problems: list[str] = []
    pool_json = pool_dir / "pool.json"
    if not pool_json.is_file():
        return ["pool.json missing"]
    files_on_disk = {p.relative_to(pool_dir).as_posix(): p for p in sorted(pool_dir.rglob("*")) if p.is_file()}

    # sizes and line endings: every file under pool/
    total = 0
    for rel, path in files_on_disk.items():
        data = path.read_bytes()
        total += len(data)
        if len(data) > max_file:
            problems.append(f"{rel}: {len(data)} bytes exceeds {max_file}")
        if b"\r" in data:
            problems.append(f"{rel}: contains CR (pool files are stored with LF)")
    if total > max_total:
        problems.append(f"total size {total} bytes exceeds {max_total}")

    for rel in ("pool.json", "funnel.json", "lineages.json"):
        path = pool_dir / rel
        if not path.is_file():
            problems.append(f"{rel} missing")
        elif not _canonical(path.read_text(encoding="utf-8")):
            problems.append(f"{rel}: not canonical JSON (sorted keys, indent 1, trailing newline)")

    pool = json.loads(pool_json.read_text(encoding="utf-8"))
    entries = pool["entries"]
    listed: set[str] = set()
    pool_ids = [e["pool_id"] for e in entries]
    for dup in {i for i in pool_ids if pool_ids.count(i) > 1}:
        problems.append(f"pool_id {dup} appears twice")

    for e in entries:
        pid = e["pool_id"]
        for group in ("files", "extra_files"):
            for f in e[group]:
                rel = f"{e['dir']}/{f['path']}"
                listed.add(rel)
                path = pool_dir / rel
                if not path.is_file():
                    problems.append(f"{rel}: missing")
                    continue
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != f["sha256"] or len(data) != f["bytes"]:
                    problems.append(f"{rel}: sha256 or size differs from pool.json")
        extra = {f["path"]: f for f in e["extra_files"]}
        if e["licence_file"] not in extra or extra[e["licence_file"]]["sha256"] != e["licence_file_sha256"]:
            problems.append(f"{pid}: licence_file_sha256 does not match the listed licence file")
        if e["module_hash"] != _module_hash(e["files"]):
            problems.append(f"{pid}: module_hash does not match the listed files")
        if e["secrets"] != {"gitleaks_findings": 0, "inventory_flagged": 0}:
            problems.append(f"{pid}: secrets are not 0/0")
        if my.licence_bucket(e["licence_spdx"]) != "permissive":
            problems.append(f"{pid}: licence {e['licence_spdx']!r} is not in the permissive bucket")
        if e["kind"] in TERRADS_KINDS:
            if e["validate"]["status"] != "valid":
                problems.append(f"{pid}: validate status is {e['validate']['status']!r}, not 'valid'")
            if not e.get("lineage_id"):
                problems.append(f"{pid}: no lineage id")

    for rel in files_on_disk:
        if rel.startswith(("terrads/", "terragoat/")) and rel not in listed:
            problems.append(f"{rel}: unlisted file (not in pool.json)")
    entry_dirs = {e["dir"] for e in entries}
    for rel in files_on_disk:
        if rel.startswith("terrads/") and not any(rel.startswith(d + "/") for d in entry_dirs):
            problems.append(f"{rel}: directory not in pool.json")
    for rel in files_on_disk:
        if "/" not in rel and rel not in ROOT_FILES:
            problems.append(f"{rel}: unexpected file at the top of pool/")

    hosts = collections.defaultdict(list)
    for e in entries:
        if e["kind"] == "host":
            hosts[e["lineage_id"]].append(e["pool_id"])
    for lid, ids in hosts.items():
        if len(ids) > 1:
            problems.append(f"lineage {lid} has {len(ids)} accepted hosts: {', '.join(sorted(ids))}")

    # lineages.json covers every accepted entry
    lineages_path = pool_dir / "lineages.json"
    if lineages_path.is_file():
        lineages = json.loads(lineages_path.read_text(encoding="utf-8"))["lineages"]
        for e in entries:
            if e["kind"] not in TERRADS_KINDS:
                continue
            members = lineages.get(e["lineage_id"], {}).get("modules", [])
            if not any(m["module_id"] == e["module_id"] and m["accepted"] for m in members):
                problems.append(f"lineages.json does not cover {e['pool_id']} in lineage {e['lineage_id']}")

    problems += _verify_ledger(pool_dir, entries)
    return problems


def _module_hash(files: list[dict]) -> str:
    lines = "".join(f"{f['path']}:{f['sha256']}\n" for f in sorted(files, key=lambda f: f["path"]))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def _verify_ledger(pool_dir: Path, entries: list[dict]) -> list[str]:
    problems: list[str] = []
    funnel_path, excl_path = pool_dir / "funnel.json", pool_dir / "exclusions.csv"
    if not funnel_path.is_file() or not excl_path.is_file():
        return ["funnel.json or exclusions.csv missing"]
    funnel = json.loads(funnel_path.read_text(encoding="utf-8"))
    with excl_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    unknown = sorted({r["code"] for r in rows} - set(cascade.LEDGER_CODES))
    for code in unknown:
        problems.append(f"exclusions.csv: unknown code {code}")
    ids = [(r["kind"], r["module_id"]) for r in rows]
    for dup in {i for i in ids if ids.count(i) > 1}:
        problems.append(f"exclusions.csv lists {dup[0]} module {dup[1]} twice")
    accepted_ids = {str(e["module_id"]) for e in entries if e["kind"] in TERRADS_KINDS}
    for r in rows:
        if r["module_id"] in accepted_ids and r["kind"] in TERRADS_KINDS:
            problems.append(f"module {r['module_id']} is both accepted and excluded")
    for kind in TERRADS_KINDS:
        ledger = funnel["ledger"][kind]
        accepted = sum(1 for e in entries if e["kind"] == kind)
        excluded = sum(1 for r in rows if r["kind"] == kind and r["status"] == "excluded")
        not_processed = sum(1 for r in rows if r["kind"] == kind and r["status"] == "not_processed")
        if ledger["considered"] != ledger["accepted"] + ledger["excluded"] + ledger["not_processed"]:
            problems.append(f"funnel.json: {kind} considered {ledger['considered']} != accepted + excluded + not_processed")
        for name, from_files in (("accepted", accepted), ("excluded", excluded), ("not_processed", not_processed)):
            if ledger[name] != from_files:
                problems.append(f"exclusions.csv/pool.json do not balance with funnel.json: {kind} {name} {from_files} != {ledger[name]}")
        by_code = collections.Counter(r["code"] for r in rows if r["kind"] == kind)
        if dict(by_code) != funnel["by_code"][kind]:
            problems.append(f"exclusions.csv does not balance with funnel.json by_code for {kind}")
    return problems


# --------------------------------------------------------------------------- the report


def _n(value: int) -> str:
    return f"{value:,}"


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def _table(header: list[str], rows: list[list], align: list[str] | None = None) -> list[str]:
    align = align or ["---"] * len(header)
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return out + [""]


def render(docs: dict) -> str:
    """The text of ``POOL_REPORT.md``. ``docs`` is what ``assemble.write_pool`` returns."""
    pool, rows, funnel, lineages, inp = docs["pool"], docs["rows"], docs["funnel"], docs["lineages"], docs["inputs"]
    entries = pool["entries"]
    terrads = [e for e in entries if e["kind"] in TERRADS_KINDS]
    natives = [e for e in terrads if e["kind"] == "native"]
    hosts = [e for e in terrads if e["kind"] == "host"]
    goat = next((e for e in entries if e["kind"] == "terragoat"), None)
    levels = funnel["terrads_levels"]
    ledger = funnel["ledger"]
    out: list[str] = [
        "# Pool report",
        "",
        "Generated by `pool/report.py` from the saved results of `pool/build.py`; **every number below is computed**, "
        "none is typed. Anything the work could not measure says `not yet established`.",
        "",
        f"- TerraDS Zenodo record `{pool['source']['terrads']['record_id']}` (DOI `{pool['source']['terrads']['doi']}`), "
        "pinned in `sources/manifest.json`",
        f"- pins recorded for every step: Terraform `{pool['pins']['terraform_required_version']}` (run with "
        f"`{pool['pins']['terraform_ci_version']}`), `hashicorp/aws` exactly `{pool['pins']['aws_provider']}`, "
        f"gitleaks `{pool['pins']['gitleaks']}`",
        f"- sampling: seed {funnel['sampling']['seed']}, host target {funnel['sampling']['host_accept_target']} accepted or "
        f"{_n(funnel['sampling']['host_process_cap'])} processed, whichever comes first",
        "- **Selection bias.** The pool favours small, self-contained modules that use only ten resource types, carry no "
        "literal credential-like attribute, have a verifiable permissive licence file and validate under the pinned "
        "Terraform and provider. It is not claimed to be representative of Terraform in the wild.",
        "",
        "## Funnel",
        "",
        "TerraDS levels (D1; modules and repositories):",
        "",
    ]
    out += _table(["Level", "Modules", "Repositories"],
                  [[lv, _n(levels[lv]["modules"]), _n(levels[lv]["repos"])] for lv in ("F0", "F1", "F2", "F3", "G")],
                  ["---", "---:", "---:"])
    for kind, title in (("native", "Natives (F3, permissive)"), ("host", "Graft hosts (G, permissive)")):
        cs = funnel["candidate_sets"][kind]
        out += [f"### {title}", "",
                f"{cs['level']} has {_n(cs['modules_at_level'])} modules; {_n(cs['removed_by_E01_licence_bucket'])} are outside the "
                f"permissive bucket (E01), leaving {_n(cs['considered'])} candidates.", ""]
        out += _table(["Stage", "Excluded here", "Remaining"],
                      [[s["stage"], _n(s["excluded"]), _n(s["remaining"])] for s in funnel["stages"][kind]],
                      ["---", "---:", "---:"])
        c = ledger[kind]
        out += [f"Ledger: considered {_n(c['considered'])} = accepted {_n(c['accepted'])} + excluded {_n(c['excluded'])} + "
                f"not processed {_n(c['not_processed'])}.", ""]
    out += ["Processing order is E01, E02 to E08, then E10 (hosts only), then E09, E11, E12 (D3-10): a host that is a "
            "lineage duplicate is recorded as E10 even if it would also have failed a later check.", ""]

    repos = {e["repo_id"] for e in terrads}
    lins = {e["lineage_id"] for e in terrads}
    accepted_real = len(terrads)
    short = max(0, 160 - accepted_real)
    out += ["## Accepted against the 160 real-world slots", ""]
    out += _table(["", "Count"], [
        ["native modules (already hold aws_instance and aws_db_instance)", _n(len(natives))],
        ["graft hosts (no EC2 and RDS pair)", _n(len(hosts))],
        ["real-world modules accepted", _n(accepted_real)],
        ["distinct repositories", _n(len(repos))],
        ["distinct lineages", _n(len(lins))],
        ["real-world slots (8 families x 20, D0 Decision 3)", "160"],
        ["shortfall in modules (not filled, not padded)", _n(short)],
        ["shortfall in lineages", _n(max(0, 160 - len(lins)))],
        ["controlled tier (TerraGoat directory)", "1" if goat else "0"],
    ], ["---", "---:"])

    out += ["## Exclusions per code", ""]
    codes = [c for c in cascade.LEDGER_CODES]
    by = funnel["by_code"]
    out += _table(["Code", "Natives", "Hosts"], [[c, _n(by["native"].get(c, 0)), _n(by["host"].get(c, 0))] for c in codes],
                  ["---", "---:", "---:"])
    reasons = collections.Counter((r["code"], r["group"]) for r in rows if r["status"] == "excluded")
    out += ["### The 20 largest exclusion reasons by detail", ""]
    out += _table(["Count", "Code", "Detail (generalised)"],
                  [[_n(n), code, (group or "-").replace("|", "/")] for (code, group), n in reasons.most_common(20)],
                  ["---:", "---", "---"])

    out += ["## Licences of the accepted modules", ""]
    per_licence = collections.defaultdict(lambda: [0, set()])
    for e in terrads:
        per_licence[e["licence_spdx"]][0] += 1
        per_licence[e["licence_spdx"]][1].add(e["repo_id"])
    out += _table(["Licence (SPDX)", "Modules", "Repositories"],
                  [[k, _n(v[0]), _n(len(v[1]))] for k, v in sorted(per_licence.items(), key=lambda kv: (-kv[1][0], kv[0]))],
                  ["---", "---:", "---:"])
    checks = [inp.licence_checks[r] for r in sorted({c.repo_id for c in inp.candidates
                                                     if c.module_id in inp.records and inp.records[c.module_id]["licence"]})]
    outcomes = collections.Counter(c.outcome for c in checks)
    out += ["### Upstream licence-file fetches (E11), one per repository", ""]
    out += _table(["Outcome", "Repositories"], [[k, _n(outcomes.get(k, 0))] for k in ("found", "mismatch", "missing", "error")],
                  ["---", "---:"])
    mism = collections.Counter((c.detected_spdx or "(unrecognised)", c.terrads_spdx) for c in checks if c.outcome == "mismatch")
    if mism:
        out += _table(["File says", "TerraDS says", "Repositories"], [[a, b, _n(n)] for (a, b), n in mism.most_common(10)],
                      ["---", "---", "---:"])

    ls, merges = lineages["stats"], lineages["merges_by_rule"]
    out += ["## Lineages", "",
            f"Computed over the {_n(ls['modules'])} candidates that passed E01 to E08 ({_n(ls['repositories'])} repositories).", ""]
    out += _table(["", "Value"], [
        ["lineages", _n(ls["lineages"])],
        ["largest lineage (modules)", _n(ls["largest_lineage_modules"])],
        ["largest lineage (repositories)", _n(ls["largest_lineage_repositories"])],
        ["lineages that span more than one repository", _n(ls["multi_repository_lineages"])],
        ["repositories merged by content alone (rules b to d)", _n(ls["repositories_merged_by_content"])],
        ["unions made by rule a / b / c / d", " / ".join(_n(merges[k]) for k in "abcd")],
    ], ["---", "---:"])
    out += ["Comparison runs over the same modules (kept for the record):", ""]
    out += _table(["Variant", "Lineages", "Largest (modules)", "Largest (repositories)"],
                  [[name, _n(s["lineages"]), _n(s["largest_lineage_modules"]), _n(s["largest_lineage_repositories"])]
                   for name, s in lineages["comparison"].items()], ["---", "---:", "---:", "---:"])
    out += ["Limits:", ""] + [f"- {x}" for x in lineages["limits"]] + [""]

    reached = [r for r in inp.records.values() if r.get("validate")]
    status = collections.Counter(r["validate"]["status"] for r in reached)
    classes = collections.Counter(r["validate"]["error_class"] for r in reached if r["validate"]["status"] != "valid")
    versions = sorted({(r["validate"]["terraform_version"], r["validate"]["provider_version"]) for r in reached})
    out += ["## terraform validate (E12)", "",
            "Versions used: " + (", ".join(f"Terraform {t}, hashicorp/aws {p}" for t, p in versions) or "not yet established")
            + ". The provider came from a local filesystem mirror; the committed files are verbatim and the validated copy was "
            "neutralised (`pool/validate.py`).", ""]
    out += _table(["Status", "Modules"], [[k, _n(status.get(k, 0))] for k in ("valid", "invalid", "error")], ["---", "---:"])
    out += [f"Pass rate among modules that reached E12: {_pct(status.get('valid', 0), len(reached))} "
            f"({_n(status.get('valid', 0))} of {_n(len(reached))}).", ""]
    out += _table(["Count", "Top error classes (first diagnostic summary)"],
                  [[_n(n), (k or "-").replace("|", "/")] for k, n in classes.most_common(10)], ["---:", "---"])

    secret_rows = [r for r in inp.records.values() if r["code"] == "E09_SECRET_FOUND"]
    both = sum(1 for r in secret_rows if r["secrets"]["gitleaks_findings"] and r["secrets"]["inventory_flagged"])
    only_g = sum(1 for r in secret_rows if r["secrets"]["gitleaks_findings"] and not r["secrets"]["inventory_flagged"])
    only_i = sum(1 for r in secret_rows if r["secrets"]["inventory_flagged"] and not r["secrets"]["gitleaks_findings"])
    attrs = collections.Counter(a for r in secret_rows for a in r["secrets"]["attributes"])
    out += ["## Secrets (E09)", "",
            f"{_n(len(secret_rows))} modules that reached E09 were excluded: {_n(both)} by both scanners, {_n(only_g)} by gitleaks "
            f"alone, {_n(only_i)} by the attribute inventory alone. Accepted entries have 0 findings from both.", ""]
    out += _table(["Count", "Inventory flag (attribute:value kind)"], [[_n(n), k] for k, n in attrs.most_common(10)], ["---:", "---"])

    out += ["## Constructs and graft facts of the accepted modules", ""]
    flag_names = ["has_data_sources", "has_count", "has_for_each", "has_dynamic", "has_locals", "has_lifecycle",
                  "has_provisioner", "has_terraform_block", "has_backend", "has_provider_block"]
    out += _table(["Flag", "Natives", "Hosts"],
                  [[f, _n(sum(e["flags"][f] for e in natives)), _n(sum(e["flags"][f] for e in hosts))] for f in flag_names],
                  ["---", "---:", "---:"])
    fact_names = ["has_vpc", "has_subnet", "has_security_group", "has_security_group_rule", "has_igw", "has_route_table",
                  "has_db_subnet_group", "ec2_rds_pair"]
    out += _table(["Graft fact", "Natives", "Hosts"],
                  [[f, _n(sum(e["graft_facts"][f] for e in natives)), _n(sum(e["graft_facts"][f] for e in hosts))] for f in fact_names]
                  + [["address collides with the canonical core", _n(sum(1 for e in natives if e["graft_facts"]["colliding_addresses"])),
                      _n(sum(1 for e in hosts if e["graft_facts"]["colliding_addresses"]))]],
                  ["---", "---:", "---:"])

    out += ["## TerraGoat (controlled tier)", ""]
    if goat:
        redactions = json.loads((Path(inp.terragoat_dir) / "SOURCE.json").read_text(encoding="utf-8"))["redactions"]
        out += [f"{_n(len(goat['files']))} `.tf` files from commit `{goat['commit_sha']}`, licence {goat['licence_spdx']} "
                f"(`NOTICE` and `LICENSE.upstream` kept). {_n(redactions)} credential-like attributes deleted and logged without "
                "values in `pool/terragoat/aws/REDACTION_LOG.md`; rescan by gitleaks and the attribute inventory: 0 findings. "
                f"terraform validate under the pins: `{goat['validate']['status']}`"
                + (f" ({goat['validate']['error_class']})" if goat["validate"]["error_class"] else "") + ".", ""]
    else:
        out += ["not yet established", ""]

    out += ["## Limits", "",
            "- **Yield (R1).** The checks E05 to E07, E09 and E12 remove many modules; the counts above are the measured yield.",
            "- **Lineage (R3).** TerraDS has no fork flag; forks that diverged below the thresholds are not detected "
            "(number: not yet established).",
            "- **Licence text (R4).** TerraDS carries no licence files; each file was fetched from raw.githubusercontent.com at "
            "the pinned commit. Repositories deleted since the crawl, or whose file is not one of the six names, are E11.",
            "- **Selection bias (R5).** See the top of this report.",
            "- **Not measured here:** whether DAIL can parse a pooled module (measured later, in the DAIL repository, and never "
            "fed back); behaviour of the pooled modules under `terraform plan`; the number of undetected forks.",
            ""]
    return "\n".join(out)
