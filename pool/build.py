"""Entry point of the D3 pool builder: ``py -3.12 -m pool.build <command>``.

Standard library and ``sources/*`` only; nothing here imports DAIL (D3-02, CLAUDE.md rule 5).

    filter    E01 to E08 over every candidate; stages the survivors in the work directory
    lineage   lineages over the staged survivors (E10 is applied later, to hosts only)
    process   E09, E11, E12 over the plan (natives, then sampled hosts); resumable
    terragoat redacted TerraGoat controlled tier into pool/terragoat/aws/
    assemble  write pool.json, exclusions.csv, funnel.json, lineages.json, the module directories and POOL_REPORT.md
    ...       (later steps add lineage, scan, licence, validate, terragoat and assemble)

All intermediate files go to the work directory (``<cache>/d3-work`` by default), never into the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import acquire

from pool import assemble, cascade, lineage, licence, redact, report, validate


def pinned_inputs() -> tuple[Path, Path]:
    """The pinned TerraDS database and archive in the cache, after checking size and sha256 against the manifest."""
    manifest = acquire.load_manifest()
    root = acquire.cache_root()
    paths = []
    for entry_id in ("terrads-sqlite", "terrads-tar-gz"):
        entry = acquire.entry_by_id(manifest, entry_id)
        path = root / entry["cache_path"]
        problem = acquire.verify_file(path, entry["sha256"], entry["size_bytes"])
        if problem:
            raise acquire.AcquireError(problem)
        paths.append(path)
    return paths[0], paths[1]


def default_work() -> Path:
    return acquire.cache_root() / "d3-work"


def cmd_filter(args: argparse.Namespace) -> int:
    if args.db and args.archive:
        db, archive = args.db, args.archive
    else:
        db, archive = pinned_inputs()
    summary = cascade.run_filter(db, archive, args.work)
    (args.work / "cheap_summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "funnel"}, indent=1, sort_keys=True))
    return 0


def load_staged(work: Path) -> list[lineage.ModuleInput]:
    """The modules that passed E01 to E08, read back from the staging directory."""
    repo_of = {}
    for line in (work / "cheap_results.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["code"] is None:
            repo_of[row["module_id"]] = row["repo_id"]
    modules = []
    for module_id, repo_id in sorted(repo_of.items()):
        files = {p.name: p.read_bytes().decode("utf-8", errors="replace") for p in sorted((work / "stage" / str(module_id)).glob("*.tf"))}
        modules.append(lineage.ModuleInput(module_id, repo_id, files))
    return modules


def cmd_lineage(args: argparse.Namespace) -> int:
    modules = load_staged(args.work)
    result = lineage.build_lineages(modules, min_shared_tokens=args.min_shared_tokens)
    out = {
        "method": {
            "rules": ["a same repository", "b identical normalised text", "c half of the files share a hash",
                      "d 5-token shingle Jaccard >= 0.8 (MinHash, exact-confirmed)"],
            "seed": lineage.SEED, "permutations": lineage.PERMUTATIONS, "bands": lineage.BANDS, "rows": lineage.ROWS,
            "shingle_tokens": lineage.SHINGLE, "min_shared_tokens": args.min_shared_tokens,
        },
        "stats": result.stats,
        "merges": result.merges,
        "lineage_of": {str(k): v for k, v in sorted(result.lineage_of.items())},
    }
    target = args.work / f"lineage_min{args.min_shared_tokens}.json"
    target.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"stats": result.stats, "merges": result.merges}, indent=1, sort_keys=True))
    return 0


def load_cheap(work: Path) -> list[dict]:
    return [json.loads(line) for line in (work / "cheap_results.jsonl").read_text(encoding="utf-8").splitlines()]


def load_lineage_of(work: Path, floor: int = lineage.FILE_TOKEN_FLOOR) -> dict[int, str]:
    doc = json.loads((work / f"lineage_min{floor}.json").read_text(encoding="utf-8"))
    return {int(k): v for k, v in doc["lineage_of"].items()}


def load_plan(work: Path) -> cascade.Plan:
    rows = load_cheap(work)
    passed = [r for r in rows if r["code"] is None]
    return cascade.make_plan(
        [r["module_id"] for r in passed if r["kind"] == "native"],
        [r["module_id"] for r in passed if r["kind"] == "host"],
        load_lineage_of(work),
    )


def load_records(path: Path) -> dict[int, dict]:
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            out[record["module_id"]] = record
    return out


class RealSteps:
    """E09, E11 and E12 for a staged module: gitleaks and the inventory, the upstream licence file, terraform validate."""

    def __init__(self, work: Path, candidates: dict[int, cascade.Candidate], binary: Path, harness: validate.Harness,
                 known: dict[int, licence.Check], checks_csv: Path) -> None:
        self.work, self.candidates, self.binary, self.harness = work, candidates, binary, harness
        self.known, self.checks_csv = known, checks_csv
        self.limiter = licence.RateLimiter()
        self.fetched = 0

    def _stage(self, module_id: int) -> Path:
        return self.work / "stage" / str(module_id)

    def secrets(self, module_id: int) -> redact.SecretsResult:
        return redact.scan_directory(self.binary, self._stage(module_id))

    def licence(self, module_id: int) -> licence.Check:
        c = self.candidates[module_id]
        check = licence.check_repository(c.repo_id, c.full_name, c.commit_sha, c.licence, limiter=self.limiter,
                                         cache_dir=self.work / "licence_cache", known=self.known)
        if self.known.get(c.repo_id) != check:
            self.known[c.repo_id] = check
            self.fetched += 1
            if self.fetched % 20 == 0:
                licence.write_checks(self.checks_csv, list(self.known.values()))
        return check

    def validate(self, module_id: int) -> validate.Result:
        files = {p.name: p.read_bytes().decode("utf-8", errors="replace") for p in sorted(self._stage(module_id).glob("*.tf"))}
        return self.harness.validate(files)


def cmd_process(args: argparse.Namespace) -> int:
    db, _archive = pinned_inputs()
    loaded = cascade.load_candidates(db)
    candidates = {c.module_id: c for c in loaded.candidates}
    plan = load_plan(args.work)
    binary = redact.gitleaks_binary()
    if binary is None:
        raise acquire.AcquireError("pinned gitleaks 8.30.1 is not installed: py -3.12 sources/tools.py gitleaks")
    try:
        harness = validate.Harness.default()
        harness.ensure_ready()
    except validate.HarnessError as exc:
        raise acquire.AcquireError(f"Terraform harness unavailable (stop and ask): {exc}") from exc
    checks_csv = acquire.REPO_ROOT / "pool" / "licence_checks.csv"
    known = licence.read_checks(checks_csv) if checks_csv.is_file() else {}
    steps = RealSteps(args.work, candidates, binary, harness, known, checks_csv)
    results = args.work / "process_results.jsonl"
    records = load_records(results)
    print(f"plan: {len(plan.natives)} natives, {len(plan.hosts)} hosts after E10 ({len(plan.e10)} dropped); "
          f"{len(records)} records already saved", flush=True)
    with results.open("a", encoding="utf-8", newline="\n") as handle:
        def append(record: dict) -> None:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            if len(records) % 10 == 0:
                print(f"  {len(records)} records; last {record['module_id']} {record['code']}", flush=True)

        cascade.process_all(plan, steps, records, append, args.accept_target, args.process_cap)
    licence.write_checks(checks_csv, list(known.values()))
    by_code = {}
    for r in records.values():
        by_code.setdefault((r["kind"], r["code"]), 0)
        by_code[(r["kind"], r["code"])] += 1
    print(json.dumps({f"{k}:{c}": n for (k, c), n in sorted(by_code.items(), key=str)}, indent=1))
    return 0


def terragoat_validate_result(work: Path, directory: Path) -> dict | None:
    """terraform validate of the redacted TerraGoat files as one configuration (cached in the work directory)."""
    cache = work / "terragoat_validate.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        harness = validate.Harness.default()
        harness.ensure_ready()
    except validate.HarnessError:
        return None
    files = {p.name: p.read_text(encoding="utf-8") for p in sorted(directory.glob("*.tf"))}
    r = harness.validate(files)
    result = {"status": r.status, "terraform_version": r.terraform_version, "provider_version": r.provider_version,
              "error_class": r.error_class}
    cache.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def cmd_assemble(args: argparse.Namespace) -> int:
    work = args.work
    pool_dir = acquire.REPO_ROOT / "pool"
    db, _archive = pinned_inputs()
    loaded = cascade.load_candidates(db)
    cheap = {r["module_id"]: (r["code"], r["detail"], r["group"]) for r in load_cheap(work) if r["code"] is not None}
    lin = json.loads((work / f"lineage_min{lineage.FILE_TOKEN_FLOOR}.json").read_text(encoding="utf-8"))
    comparison = {}
    for label, floor in (("floor 30 (used)", lineage.FILE_TOKEN_FLOOR), ("floor 0 (rule c as first written)", 0),
                         ("rule c off", 1_000_000_000)):
        path = work / f"lineage_min{floor}.json"
        if path.is_file():
            comparison[label] = json.loads(path.read_text(encoding="utf-8"))["stats"]
    records = load_records(work / "process_results.jsonl")
    checks = cascade.licence_checks_from_records(records, {c.module_id: c for c in loaded.candidates})
    goat_dir = pool_dir / "terragoat" / "aws"
    inp = assemble.Inputs(
        candidates=loaded.candidates, cheap=cheap, plan=load_plan(work),
        records=records,
        lineage_of={int(k): v for k, v in lin["lineage_of"].items()}, lineage_stats=lin["stats"],
        lineage_merges=lin["merges"], lineage_comparison=comparison, licence_checks=checks,
        stage_dir=work / "stage", licence_cache=work / "licence_cache", funnel_levels=loaded.funnel,
        e01_not_candidates=loaded.e01_not_candidates, terragoat_dir=goat_dir,
        terragoat_validate=terragoat_validate_result(work, goat_dir),
    )
    docs = assemble.write_pool(inp, pool_dir)
    root = acquire.REPO_ROOT
    datasheet = root / "DATASHEET.md"
    datasheet.write_bytes(report.update_datasheet(datasheet.read_bytes().decode("utf-8"),
                                                  report.datasheet_section(docs["view"])).encode("utf-8"))
    carryover = root / "docs" / "D4_CARRYOVER.md"
    carryover.write_bytes(report.d4_carryover(docs["view"]).encode("utf-8"))
    problems = report.verify_pool(pool_dir)
    print(json.dumps({"accepted": docs["funnel"]["accepted"], "ledger": docs["funnel"]["ledger"],
                      "problems": problems}, indent=1, sort_keys=True))
    return 1 if problems else 0


def cmd_terragoat(args: argparse.Namespace) -> int:
    root = acquire.cache_root()
    clone = root / "terragoat"
    manifest = acquire.load_manifest()
    commit = acquire.entry_by_id(manifest, "terragoat")["commit"]
    head = acquire.git("rev-parse", "HEAD", cwd=clone)
    if head != commit:
        raise acquire.AcquireError(f"clone is at {head}, manifest pins {commit}")
    listing = {}
    for line in acquire.TERRAGOAT_LISTING.read_text(encoding="utf-8").splitlines():
        digest, _size, path = line.split(None, 2)
        if path.startswith(acquire.TERRAGOAT_SUBDIR + "/") and path.count("/") == 2:
            listing[path.rsplit("/", 1)[1]] = digest
    binary = redact.gitleaks_binary()
    if binary is None:
        raise acquire.AcquireError("pinned gitleaks 8.30.1 is not installed: py -3.12 sources/tools.py gitleaks")
    dest = acquire.REPO_ROOT / "pool" / "terragoat" / "aws"
    try:
        summary = redact.build_terragoat(clone, dest, commit, listing=listing, binary=binary)
    except redact.RedactionError as exc:
        raise acquire.AcquireError(str(exc)) from exc
    final = redact.scan_directory(binary, dest)
    print(json.dumps({"build": summary, "rescan_of_pool_dir": {
        "gitleaks_findings": final.gitleaks_findings, "inventory_flagged": final.inventory_flagged}}, indent=1, sort_keys=True))
    return 0 if not redact.has_secrets(final) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pool.build", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", metavar="command")
    p = sub.add_parser("filter", help="E01 to E08 over all candidates")
    p.add_argument("--db", type=Path, help="TerraDS.sqlite (default: the pinned one in the cache)")
    p.add_argument("--archive", type=Path, help="TerraDS.tar.gz (default: the pinned one in the cache)")
    p.add_argument("--work", type=Path, default=None, help="work directory outside the repository")
    p.set_defaults(func=cmd_filter)
    p = sub.add_parser("lineage", help="lineages over the staged survivors")
    p.add_argument("--work", type=Path, default=None, help="work directory outside the repository")
    p.add_argument("--min-shared-tokens", type=int, default=lineage.FILE_TOKEN_FLOOR, help="token floor for a shared file under rule c")
    p.set_defaults(func=cmd_lineage)
    p = sub.add_parser("process", help="E09, E11, E12 (resumable)")
    p.add_argument("--work", type=Path, default=None, help="work directory outside the repository")
    p.add_argument("--accept-target", type=int, default=cascade.HOST_ACCEPT_TARGET)
    p.add_argument("--process-cap", type=int, default=cascade.HOST_PROCESS_CAP)
    p.set_defaults(func=cmd_process)
    p = sub.add_parser("terragoat", help="redacted TerraGoat controlled tier into pool/terragoat/aws/")
    p.add_argument("--work", type=Path, default=None, help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_terragoat)
    p = sub.add_parser("assemble", help="write the committed pool from the saved results")
    p.add_argument("--work", type=Path, default=None, help="work directory outside the repository")
    p.set_defaults(func=cmd_assemble)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    if args.work is None:
        args.work = default_work()
    try:
        return args.func(args)
    except acquire.AcquireError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
