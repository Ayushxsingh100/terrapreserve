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
    # pool/ also holds the builder's Python modules and their bytecode; they are code, not pool data
    # D4b derived natives (pool/terrads/derived/) and their records are verified separately from the D3 pool
    derived_root = {"derived.json", "derived_exclusions.csv", "DERIVED_REPORT.md"}
    files_on_disk = {
        p.relative_to(pool_dir).as_posix(): p
        for p in sorted(pool_dir.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and not (p.parent == pool_dir and p.suffix == ".py")
        and not (p.relative_to(pool_dir).parts[:2] == ("terrads", "derived"))
        and p.relative_to(pool_dir).as_posix() not in derived_root
    }

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


# --------------------------------------------------------------------------- helpers

SLOTS = 160  # real-world slots: 8 families x 20 (D0 Decision 3)


def _n(value: int) -> str:
    return f"{value:,}"


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def _table(header: list[str], rows: list[list], align: list[str] | None = None) -> list[str]:
    align = align or ["---"] * len(header)
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return out + [""]


# --------------------------------------------------------------------------- the committed pool as a view


def load_view(pool_dir: Path) -> dict:
    """Everything the generated documents are computed from: the committed pool files, nothing else."""
    from pool import licence

    def read_csv(name: str) -> list[dict]:
        path = pool_dir / name
        if not path.is_file():
            return []
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def read_json(name: str) -> dict:
        return json.loads((pool_dir / name).read_text(encoding="utf-8"))

    pool = read_json("pool.json")
    goat_dir = pool_dir / "terragoat" / "aws"
    goat_source = json.loads((goat_dir / "SOURCE.json").read_text(encoding="utf-8")) if (goat_dir / "SOURCE.json").is_file() else None
    return {
        "pool": pool, "funnel": read_json("funnel.json"), "lineages": read_json("lineages.json"),
        "exclusions": read_csv("exclusions.csv"), "validate_rows": read_csv("validate_results.csv"),
        "licence_checks": list(licence.read_checks(pool_dir / "licence_checks.csv").values())
        if (pool_dir / "licence_checks.csv").is_file() else [],
        "terragoat_source": goat_source,
    }


def _kinds(view: dict) -> tuple[list[dict], list[dict], list[dict], dict | None]:
    entries = view["pool"]["entries"]
    terrads = [e for e in entries if e["kind"] in TERRADS_KINDS]
    return (terrads, [e for e in terrads if e["kind"] == "native"], [e for e in terrads if e["kind"] == "host"],
            next((e for e in entries if e["kind"] == "terragoat"), None))


def render(view: dict) -> str:
    """The text of ``POOL_REPORT.md`` (computed from ``load_view``)."""
    pool, funnel, lineages = view["pool"], view["funnel"], view["lineages"]
    terrads, natives, hosts, goat = _kinds(view)
    rows = [r for r in view["exclusions"] if r["status"] == "excluded"]
    levels, ledger = funnel["terrads_levels"], funnel["ledger"]
    out: list[str] = [
        "# Pool report",
        "",
        "Generated by `pool/report.py` from the committed pool files (`py -3.12 -m pool.build assemble`); **every number "
        "below is computed**, none is typed. Anything the work could not measure says `not yet established`.",
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
    out += ["## Accepted against the 160 real-world slots", ""]
    out += _table(["", "Count"], [
        ["native modules (already hold aws_instance and aws_db_instance)", _n(len(natives))],
        ["graft hosts (no EC2 and RDS pair)", _n(len(hosts))],
        ["real-world modules accepted", _n(len(terrads))],
        ["distinct repositories", _n(len(repos))],
        ["distinct lineages", _n(len(lins))],
        ["real-world slots (8 families x 20, D0 Decision 3)", str(SLOTS)],
        ["shortfall in modules (not filled, not padded)", _n(max(0, SLOTS - len(terrads)))],
        ["shortfall in lineages", _n(max(0, SLOTS - len(lins)))],
        ["controlled tier (TerraGoat directory)", "1" if goat else "0"],
    ], ["---", "---:"])
    if funnel["sampling"]["hosts_not_processed"]:
        out += [f"The host stop rule ended the run with {_n(funnel['sampling']['hosts_not_processed'])} hosts not processed "
                f"({_n(funnel['sampling']['hosts_processed'])} of {_n(funnel['sampling']['hosts_after_E10'])} hosts after E10 were processed).", ""]

    out += ["## Exclusions per code", ""]
    by = funnel["by_code"]
    out += _table(["Code", "Natives", "Hosts"],
                  [[c, _n(by["native"].get(c, 0)), _n(by["host"].get(c, 0))] for c in cascade.LEDGER_CODES], ["---", "---:", "---:"])
    reasons = collections.Counter((r["code"], r["group"]) for r in rows)
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
    checks = view["licence_checks"]
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

    reached = [r for r in view["validate_rows"] if r["kind"] in TERRADS_KINDS]
    status = collections.Counter(r["status"] for r in reached)
    classes = collections.Counter(r["error_class"] for r in reached if r["status"] != "valid")
    versions = sorted({(r["terraform_version"], r["provider_version"]) for r in reached})
    out += ["## terraform validate (E12)", "",
            "Versions used: " + (", ".join(f"Terraform {t}, hashicorp/aws {p}" for t, p in versions) or "not yet established")
            + ". The provider came from a local filesystem mirror; the committed files are verbatim and the validated copy was "
            "neutralised (`pool/validate.py`).", ""]
    out += _table(["Status", "Modules"], [[k, _n(status.get(k, 0))] for k in ("valid", "invalid", "error")], ["---", "---:"])
    out += [f"Pass rate among modules that reached E12: {_pct(status.get('valid', 0), len(reached))} "
            f"({_n(status.get('valid', 0))} of {_n(len(reached))}).", ""]
    out += _table(["Count", "Top error classes (first diagnostic summary)"],
                  [[_n(n), (k or "-").replace("|", "/")] for k, n in classes.most_common(10)], ["---:", "---"])

    secret_rows = [r for r in rows if r["code"] == "E09_SECRET_FOUND"]
    has_g = lambda r: "gitleaks " in r["group"]  # noqa: E731
    has_i = lambda r: "inventory " in r["group"]  # noqa: E731
    both = sum(1 for r in secret_rows if has_g(r) and has_i(r))
    only_g = sum(1 for r in secret_rows if has_g(r) and not has_i(r))
    only_i = sum(1 for r in secret_rows if has_i(r) and not has_g(r))
    attrs = collections.Counter(part[len("inventory "):] for r in secret_rows for part in r["group"].split("; ")
                                if part.startswith("inventory "))
    out += ["## Secrets (E09)", "",
            f"{_n(len(secret_rows))} modules that reached E09 were excluded: {_n(both)} by both scanners, {_n(only_g)} by gitleaks "
            f"alone, {_n(only_i)} by the attribute inventory alone. Accepted entries have 0 findings from both.", ""]
    out += _table(["Modules", "Inventory flag (attribute:value kind)"], [[_n(n), k] for k, n in attrs.most_common(10)], ["---:", "---"])

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
    if goat and view["terragoat_source"]:
        src = view["terragoat_source"]
        out += [f"{_n(len(goat['files']))} `.tf` files from commit `{goat['commit_sha']}`, licence {goat['licence_spdx']} "
                f"(`NOTICE` and `LICENSE.upstream` kept). {_n(src['redactions'])} credential-like attributes deleted and logged "
                "without values in `pool/terragoat/aws/REDACTION_LOG.md`; rescan by gitleaks and the attribute inventory: "
                f"0 findings. {_n(len(src['not_copied']))} non-`.tf` files under `terraform/aws/` were not copied. "
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


# --------------------------------------------------------------------------- DATASHEET section and the D4 carry-over

DATASHEET_BEGIN = "<!-- POOL:BEGIN (generated by pool/report.py; do not edit by hand) -->"
DATASHEET_END = "<!-- POOL:END -->"


def datasheet_section(view: dict) -> str:
    """The Pool section of ``DATASHEET.md``: measured numbers only, computed from the committed pool."""
    terrads, natives, hosts, goat = _kinds(view)
    funnel, lineages = view["funnel"], view["lineages"]
    lic = collections.Counter(e["licence_spdx"] for e in terrads)
    reached = [r for r in view["validate_rows"] if r["kind"] in TERRADS_KINDS]
    valid = sum(1 for r in reached if r["status"] == "valid")
    lines = [
        DATASHEET_BEGIN,
        "## Pool (D3)",
        "",
        "Measured by `pool/build.py`; the full account, with every exclusion, is in `pool/POOL_REPORT.md`, "
        "`pool/funnel.json` and `pool/exclusions.csv`.",
        "",
        f"- Real-world modules accepted: {_n(len(terrads))} ({_n(len(natives))} native, holding both `aws_instance` and "
        f"`aws_db_instance`; {_n(len(hosts))} graft hosts), from {_n(len({e['repo_id'] for e in terrads}))} repositories in "
        f"{_n(len({e['lineage_id'] for e in terrads}))} lineages. Real-world slots: {SLOTS}; shortfall in modules: "
        f"{_n(max(0, SLOTS - len(terrads)))} (not filled).",
        "- Candidates considered: " + f"{_n(funnel['ledger']['native']['considered'])} native, {_n(funnel['ledger']['host']['considered'])} "
        f"host; hosts not processed after the stop rule: {_n(funnel['ledger']['host']['not_processed'])}.",
        "- Licences of accepted modules: " + ", ".join(f"{k} {_n(v)}" for k, v in sorted(lic.items(), key=lambda kv: (-kv[1], kv[0]))) + ".",
        f"- `terraform validate` under Terraform 1.15.x and `hashicorp/aws` 6.53.0: {_n(valid)} of {_n(len(reached))} modules that "
        "reached that step were valid.",
        f"- Lineages over the candidates that passed the cheap filters: {_n(lineages['stats']['lineages'])}; largest "
        f"{_n(lineages['stats']['largest_lineage_modules'])} modules. Undetected forks: not yet established.",
        "- Controlled tier: " + (f"TerraGoat, {_n(len(goat['files']))} `.tf` files, Apache-2.0 notice kept, "
                                 f"{_n(view['terragoat_source']['redactions'])} credential-like attributes deleted and logged." if goat and view["terragoat_source"] else "not yet established."),
        "- Secrets: every accepted real-world module has 0 gitleaks findings and 0 flagged attributes; real-world modules with a "
        "finding were excluded, never edited.",
        "- Selection bias: small, self-contained, secret-free, permissively licensed modules that validate under the pins; "
        "the pool is not representative of Terraform in the wild.",
        DATASHEET_END,
        "",
    ]
    return "\n".join(lines)


def d4_carryover(view: dict) -> str:
    """``docs/D4_CARRYOVER.md``: facts D4 inherits, each citing a committed file. It decides nothing."""
    from pool import validate

    terrads, natives, hosts, goat = _kinds(view)
    funnel, lineages = view["funnel"], view["lineages"]
    collisions = [e for e in terrads if e["graft_facts"]["colliding_addresses"]]
    excluded_e12 = [r for r in view["exclusions"] if r["code"] == "E12_INVALID_UNDER_PIN"]
    e12_classes = collections.Counter(r["group"] for r in excluded_e12)
    native_e09 = [r for r in view["exclusions"] if r["code"] == "E09_SECRET_FOUND" and r["kind"] == "native"]
    out = [
        "# D4 carry-over",
        "",
        "Facts that D4 (scenario construction) inherits from D3. Facts only: each item cites the committed file that shows it, "
        "and decides nothing. Where a value was not measured the item says `not yet established`. Counts are computed from "
        "the committed pool files by `pool/report.py`.",
        "",
        "## 1. The neutralisation that `terraform validate` was run on (D3-09)",
        "",
        "Pool files are verbatim; the copy that Terraform read was transformed as follows. D3-09 records that D4 must "
        "reproduce this transformation when it builds scenarios, so that a scenario step is validated under the same conditions. "
        "Implementation: `pool/validate.py` (`neutralise`, `PINS_TF`, `Harness`).",
        "",
        "- every top-level `terraform` block and every top-level `provider` block is removed from every `.tf` file (found by brace depth with `sources/hcl_lex.py`); "
        "nested blocks such as `provider = aws.alias` inside a resource are kept, so a reference to a removed provider alias is invalid.",
        f"- one extra file `{validate.PIN_FILE_NAME}` is added (not `versions.tf`, because a module may own that name) with exactly the text of `validation/smoke/versions.tf`: "
        "Terraform `~> 1.15.0` and `hashicorp/aws` `6.53.0`.",
        "- `terraform init -backend=false` against a local filesystem mirror of `hashicorp/aws` 6.53.0, then `terraform validate -json`; "
        "the result's `error_class` is the first error diagnostic's summary, at most 200 characters.",
        "- results per module: `pool/validate_results.csv`; versions used: "
        + ", ".join(sorted({f"Terraform {r['terraform_version']}, hashicorp/aws {r['provider_version']}" for r in view['validate_rows']}))
        + ".",
        "",
        "## 2. Pool entries (`pool/pool.json`, schema D3-08)",
        "",
        f"- {_n(len(natives))} native and {_n(len(hosts))} host entries, plus {1 if goat else 0} TerraGoat entry (`kind: terragoat`, `module_id: null`, "
        "`lineage_id: null`: the lineage split of D0 Decision 7 applies to the real-world tier).",
        "- each entry carries identity, source commit, licence and its file hash, lineage id, file hashes, resources, type counts, construct flags, graft facts, "
        "secrets (0/0) and the validate result; it carries no scenario field, no label and no judgement of safety.",
        "- text files are stored with LF; where the archive had CRLF the original sha256 is kept in the module's `SOURCE.json` (`archive_sha256`, `crlf_normalised`).",
        "",
        "## 3. Canonical-core collisions per host (graft facts)",
        "",
        "The canonical core addresses are `pool/assemble.py` `CORE_ADDRESSES` (Doc 04 Appendix B as the D2 fixture names them). "
        f"{_n(len(collisions))} of {_n(len(terrads))} accepted real-world modules define at least one of them (`graft_facts.colliding_addresses` in `pool/pool.json`):",
        "",
    ]
    out += _table(["Pool id", "Colliding addresses"], [[e["pool_id"], ", ".join(f"`{a}`" for a in e["graft_facts"]["colliding_addresses"])] for e in collisions])
    out += [
        "## 4. Construct flags",
        "",
        "Counts of accepted modules with each flag are in `pool/POOL_REPORT.md` (section \"Constructs and graft facts\") and per entry in `pool/pool.json` (`flags`). "
        "Data sources, `count`, `for_each`, `dynamic`, `locals`, `lifecycle` and provisioners are flags, not exclusions (D3-06).",
        "",
        "## 5. Lineages",
        "",
        f"- {_n(lineages['stats']['lineages'])} lineages over the candidates that passed E01 to E08; ids and members in `pool/lineages.json`; at most one accepted host per lineage; natives keep all lineage members.",
        "- method: `pool/lineages.json` (`method`); rule c counts a file only from 30 normalised tokens up (user decision, 30 Oct 2026; effect in `comparison`).",
        "- limits: " + " ".join(lineages["limits"]),
        "",
        "## 6. What E12 excluded",
        "",
        f"- {_n(len(excluded_e12))} candidates were excluded by `terraform validate` under the pins (rows with code `E12_INVALID_UNDER_PIN` in `pool/exclusions.csv`); first error classes:",
        "",
    ]
    out += _table(["Count", "Status and first error summary"], [[_n(n), k.replace("|", "/")] for k, n in e12_classes.most_common(10)], ["---:", "---"])
    out += [
        "## 7. Yield facts",
        "",
        f"- Natives considered {_n(funnel['ledger']['native']['considered'])}, accepted {_n(funnel['ledger']['native']['accepted'])}; hosts considered "
        f"{_n(funnel['ledger']['host']['considered'])}, accepted {_n(funnel['ledger']['host']['accepted'])}, not processed {_n(funnel['ledger']['host']['not_processed'])} "
        "(`pool/funnel.json`).",
        "- Real-world slots are 160 (D0 Decision 3); the shortfall, if any, is in `pool/POOL_REPORT.md` and was not filled.",
        f"- Natives excluded at E09: {_n(sum(1 for r in native_e09))} of {_n(funnel['ledger']['native']['considered'])}; "
        f"{_n(sum(1 for r in native_e09 if 'password:literal' in r['group']))} of those have a flagged literal `password` attribute "
        "(`pool/exclusions.csv`, code `E09_SECRET_FOUND`, column `group`). Real-world text was not edited.",
        "",
        "## 8. Not yet established",
        "",
        "- how many forks diverged below the lineage thresholds and so are not detected;",
        "- whether DAIL parses any pooled module (measured later in the DAIL repository; never fed back into selection);",
        "- behaviour of any pooled module under `terraform plan` (not run: no credentials);",
        "- the GitHub repository id of TerraGoat (its entry has no repository id and no lineage id);",
        "- whether the modules excluded by `terraform validate` would validate under a different provider version (not tested).",
        "",
    ]
    return "\n".join(out)


def update_datasheet(text: str, section: str) -> str:
    """``DATASHEET.md`` with the generated Pool section replaced between its markers, or inserted before ``## Uses``."""
    if DATASHEET_BEGIN in text:
        head, rest = text.split(DATASHEET_BEGIN, 1)
        _old, tail = rest.split(DATASHEET_END, 1)
        return head + section.rstrip("\n") + tail
    marker = "## Uses"
    index = text.index(marker)
    return text[:index] + section + "\n" + text[index:]
