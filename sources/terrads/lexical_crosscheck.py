"""Lexical cross-check of the TerraDS module metadata (Prompt B review, R2).

    py -3.12 sources/terrads/lexical_crosscheck.py <TerraDS.sqlite> <TerraDS.tar.gz> [--out crosscheck.json]
        [--causes causes.json]

TerraDS's metadata was produced by terraform-config-inspect. This script re-derives
each sampled module's resource types, data sources and module calls **from the
module's own files**, with the standalone lexer in ``sources/hcl_lex.py``: comments
and heredoc bodies are removed and top-level ``resource``/``data``/``module`` block
headers are matched by brace depth; ``.tf.json`` files are read with ``json``. It
shares no code with terraform-config-inspect or with DAIL.

Files are read from the archive members in memory; nothing is written to disk.

Population (seed 20261023):
* every F3 module;
* 500 F2 modules: ``random.Random(20261023).sample(sorted(F2 module ids), 500)``;
* as a negative control (not requested by the review; it removes the one-sided
  selection of the two groups above), 500 modules with at least one managed ``aws_``
  resource that are not in F2: ``random.Random(20261023).sample(sorted(ids), 500)``.
"""

from __future__ import annotations

import argparse
import io
import json
import posixpath
import random
import sqlite3
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hcl_lex  # noqa: E402
import measure_yield as my  # noqa: E402

SEED = 20261023
SAMPLE_F2 = 500
SAMPLE_NEGATIVE = 500
COMPARISONS = ("types", "type_name_pairs", "has_data", "has_module_calls", "is_F2", "is_F3")
GROUPS = ("F3", "F2_sample", "negative_control")
# What the first runs showed, kept so the final numbers are not read as untouched first-try results.
DEVELOPMENT_HISTORY = (
    "Run 1 reported 19 disagreements; inspecting them showed a bug in the lexer's heredoc handling "
    "(HCL allows leading whitespace before the closing marker of a << heredoc as well as <<-), "
    "which swallowed later blocks. Fixed. "
    "Run 2 reported 7; one (module 291657) was a hidden file .wrapper.tf that Terraform ignores, so the "
    "reader now applies Terraform's file-selection rule. The 6 left are the final result below."
)


def ignored_by_terraform(name: str) -> bool:
    """Terraform skips configuration files that start with ".", end with "~" or are wrapped in "#"."""
    return name.startswith(".") or name.endswith("~") or (name.startswith("#") and name.endswith("#"))


def analyse_module(files: dict[str, str]) -> hcl_lex.Headers:
    """Lexical result for one module directory; ``files`` maps file name to text."""
    parts = []
    for name in sorted(files):
        if ignored_by_terraform(name):
            continue
        if name.endswith(".tf.json"):
            parts.append(hcl_lex.headers_from_json(files[name]))
        elif name.endswith(".tf"):
            parts.append(hcl_lex.headers_from_hcl(files[name]))
    return hcl_lex.merge(parts)


def lexical_flags(lex: hcl_lex.Headers) -> dict[str, object]:
    types = {t for t, _ in lex.managed}
    return {
        "types": types,
        "pairs": lex.managed,
        "has_data": bool(lex.data),
        "has_module_calls": bool(lex.modules),
        "is_F2": bool(types) and types <= my.S,
        "is_F3": bool(types) and types <= my.S and {"aws_instance", "aws_db_instance"} <= types,
    }


def compare(meta: dict, lex: dict) -> dict[str, bool]:
    """True where the lexical reading agrees with the TerraDS metadata."""
    return {
        "types": meta["types"] == lex["types"],
        "type_name_pairs": meta["pairs"] == lex["pairs"],
        "has_data": meta["has_data"] == lex["has_data"],
        "has_module_calls": meta["has_module_calls"] == lex["has_module_calls"],
        "is_F2": meta["is_F2"] == lex["is_F2"],
        "is_F3": meta["is_F3"] == lex["is_F3"],
    }


def choose_population(modules: list[my.ModuleRow], members: dict[str, list[my.ModuleRow]]) -> dict[str, list[int]]:
    f2_ids = sorted(m.module_id for m in members["F2"])
    f2_set = set(f2_ids)
    f3_ids = sorted(m.module_id for m in members["F3"])
    negative_ids = sorted(
        m.module_id for m in members["F1"] if m.module_id not in f2_set
    )
    return {
        "F3": f3_ids,
        "F2_sample": sorted(random.Random(SEED).sample(f2_ids, SAMPLE_F2)),
        "negative_control": sorted(random.Random(SEED).sample(negative_ids, SAMPLE_NEGATIVE)),
    }


def metadata_for(conn: sqlite3.Connection, rows: dict[int, my.ModuleRow]) -> dict[int, dict]:
    pairs: dict[int, set[tuple[str, str]]] = {i: set() for i in rows}
    for module_id, rtype, name in conn.execute("SELECT ModuleId, Type, Name FROM Resources WHERE ResourceType = 'Managed'"):
        if module_id in pairs:
            pairs[module_id].add((rtype, name))
    out = {}
    for module_id, row in rows.items():
        types = {t for t, _ in pairs[module_id]}
        out[module_id] = {
            "types": types,
            "pairs": pairs[module_id],
            "has_data": row.n_data > 0,
            "has_module_calls": row.n_calls > 0,
            "is_F2": my.flags(row)["F2"],
            "is_F3": my.flags(row)["F3"],
        }
    return out


def read_modules(archive: Path, wanted: dict[int, dict[str, int]]) -> tuple[dict[int, dict[str, str]], int, int]:
    """Stream the archive once. ``wanted[repo_id][module_path] = module_id``. Returns the files of
    each wanted module (in memory), and how many ``.tf`` and ``.tf.json`` files were read."""
    found: dict[int, dict[str, str]] = {}
    n_tf = n_json = 0
    with tarfile.open(archive, "r|gz") as outer:
        for member in outer:
            if not member.isfile() or not member.name.endswith(".tar.gz"):
                continue
            repo_id = int(member.name.removesuffix(".tar.gz").rsplit("/", 1)[-1])
            if repo_id not in wanted:
                continue
            data = outer.extractfile(member).read()
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as inner:
                for item in inner:
                    if not item.isfile() or "/" not in item.name:
                        continue
                    base = posixpath.basename(item.name)
                    if not (base.endswith(".tf") or base.endswith(".tf.json")):
                        continue
                    rel = item.name.split("/", 1)[1]
                    directory = posixpath.dirname(rel) or "."
                    module_id = wanted[repo_id].get(directory)
                    if module_id is None:
                        continue
                    handle = inner.extractfile(item)
                    found.setdefault(module_id, {})[base] = handle.read().decode("utf-8", errors="replace")
                    if base.endswith(".tf.json"):
                        n_json += 1
                    else:
                        n_tf += 1
    return found, n_tf, n_json


def summarise(results: dict[int, dict], population: dict[str, list[int]]) -> dict:
    def rates(ids: list[int]) -> dict:
        table = {}
        for name in COMPARISONS:
            agree = sum(1 for i in ids if results[i]["agree"][name])
            table[name] = {"agree": agree, "total": len(ids), "rate": round(agree / len(ids), 6) if ids else None}
        return table

    positive = sorted(set(population["F3"]) | set(population["F2_sample"]))
    return {
        "F3": rates(population["F3"]),
        "F2_sample": rates(population["F2_sample"]),
        "positive_population_F3_union_F2_sample": rates(positive),
        "negative_control": rates(population["negative_control"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("database", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "crosscheck.json")
    parser.add_argument("--causes", type=Path, default=Path(__file__).resolve().parent / "crosscheck_causes.json")
    args = parser.parse_args(argv)

    conn = my.connect_readonly(args.database)
    repos = my.load_repos(conn)
    modules = my.load_modules(conn)
    members = my.measure(modules, repos)["members"]
    by_id = {m.module_id: m for m in modules}
    population = choose_population(modules, members)
    needed = sorted({i for ids in population.values() for i in ids})
    meta = metadata_for(conn, {i: by_id[i] for i in needed})
    conn.close()

    wanted: dict[int, dict[str, int]] = {}
    for module_id in needed:
        row = by_id[module_id]
        wanted.setdefault(row.repo_id, {})[row.path] = module_id
    files, n_tf, n_json = read_modules(args.archive, wanted)

    results: dict[int, dict] = {}
    for module_id in needed:
        headers = analyse_module(files.get(module_id, {}))
        lex = lexical_flags(headers)
        results[module_id] = {
            "lex": lex,
            "agree": compare(meta[module_id], lex),
            "anomalies": headers.anomalies,
            "n_files": len(files.get(module_id, {})),
        }

    causes = json.loads(args.causes.read_text(encoding="utf-8")) if args.causes.is_file() else {}
    disagreements = []
    for module_id in needed:
        bad = [name for name, ok in results[module_id]["agree"].items() if not ok]
        if not bad:
            continue
        row = by_id[module_id]
        disagreements.append(
            {
                "module_id": module_id,
                "groups": sorted(g for g, ids in population.items() if module_id in ids),
                "repo": repos[row.repo_id]["full_name"],
                "path": row.path,
                "disagrees_on": bad,
                "terrads_types": sorted(meta[module_id]["types"]),
                "lexical_types": sorted(results[module_id]["lex"]["types"]),
                "terrads_has_data": meta[module_id]["has_data"],
                "lexical_has_data": results[module_id]["lex"]["has_data"],
                "terrads_has_module_calls": meta[module_id]["has_module_calls"],
                "lexical_has_module_calls": results[module_id]["lex"]["has_module_calls"],
                "likely_cause": causes.get(str(module_id), "not yet inspected"),
            }
        )
    document = {
        "status": "OK",
        "title": "Lexical cross-check (independent implementation)",
        "seed": SEED,
        "method": (
            "sources/hcl_lex.py: comments (#, //, /* */) and heredoc bodies removed, quoted strings skipped "
            "including ${...} interpolation; top-level resource/data/module headers matched by brace depth; "
            ".tf.json read with json. Files read in memory from TerraDS.tar.gz members; nothing written to disk."
        ),
        "population": {
            "F3": len(population["F3"]),
            "F2_sample": len(population["F2_sample"]),
            "F3_in_F2_sample": len(set(population["F3"]) & set(population["F2_sample"])),
            "negative_control": len(population["negative_control"]),
            "distinct_modules": len(needed),
            "sampling": {
                "F2_sample": f"random.Random({SEED}).sample(sorted(F2 module ids), {SAMPLE_F2})",
                "negative_control": f"random.Random({SEED}).sample(sorted(F1-not-F2 module ids), {SAMPLE_NEGATIVE})",
            },
        },
        "development_history": DEVELOPMENT_HISTORY,
        "files_read": {".tf": n_tf, ".tf.json": n_json},
        "modules_without_any_file_found": sum(1 for i in needed if results[i]["n_files"] == 0),
        "modules_with_lexer_anomalies": sum(1 for i in needed if results[i]["anomalies"]),
        "lexer_anomaly_module_ids": [i for i in needed if results[i]["anomalies"]],
        "agreement": summarise(results, population),
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
        "terraform_config_inspect": (
            "UNRESOLVED: go.exe is blocked by a Windows Application Control policy (not bypassed). "
            "It would not have been independent: TerraDS's analyser calls tfconfig.LoadModule "
            "(terraform-config-inspect v0.0.0-20240801114854-6714b46f5fe4)."
        ),
    }
    args.out.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for group, table in document["agreement"].items():
        print(group, {k: f"{v['agree']}/{v['total']}" for k, v in table.items()})
    print("disagreements:", len(disagreements), "files read:", document["files_read"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
