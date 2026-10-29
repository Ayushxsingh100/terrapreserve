"""pool/assemble.py and pool/report.verify_pool: the committed pool is internally consistent (D3 step 6).

A tiny synthetic pool is assembled in a temporary directory from a hand-built work directory, verified, and then
tampered with in turn. Every tamper must be reported by ``verify_pool``; these are the offline integrity rules of the
work package (hashes, listing, accounting, licence bucket, secrets, one host per lineage, lineage coverage, sizes,
canonical JSON, LF only).
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pool import assemble, cascade, licence, report  # noqa: E402

MIT_TEXT = ("MIT License\r\n\r\nPermission is hereby granted, free of charge, to any person obtaining a copy of this "
            "software and associated documentation files (the \"Software\"), to deal in the Software.\r\n"
            "The above copyright notice and this permission notice shall be included in all copies.\r\n")
NATIVE_TF = (
    'resource "aws_instance" "app" {\r\n  ami = "x"\r\n  subnet_id = aws_subnet.app.id\r\n}\r\n'
    'resource "aws_db_instance" "database" {\r\n  engine = "mysql"\r\n}\r\n'
    'resource "aws_subnet" "app" {\r\n  count = 2\r\n}\r\n'
)
HOST_TF = ('terraform {\n  required_version = ">= 0.12"\n}\nresource "aws_security_group" "sg" {\n  lifecycle {\n'
           '    create_before_destroy = true\n  }\n}\ndata "aws_ami" "a" {\n}\n')
HOST3_TF = 'resource "aws_vpc" "main" {\n}\nresource "aws_subnet" "other" {\n}\n'


STATS = {"modules": 6, "repositories": 6, "lineages": 5, "largest_lineage_modules": 2,
         "largest_lineage_repositories": 2, "multi_repository_lineages": 1, "repositories_merged_by_content": 2}


def cand(mid: int, repo: int, kind: str, licence_id: str = "MIT") -> cascade.Candidate:
    return cascade.Candidate(mid, repo, ".", f"o/r{repo}", f"{mid:040d}", licence_id, kind, False, 0, frozenset())


def record(mid: int, kind: str, code=None, detail="", group="") -> dict:
    ok = code is None
    return {
        "module_id": mid, "kind": kind, "code": code, "detail": detail, "group": group,
        "secrets": {"gitleaks_findings": 0 if ok or code != "E09_SECRET_FOUND" else 1, "inventory_flagged": 0,
                    "rules": [], "attributes": []},
        "licence": None if code == "E09_SECRET_FOUND" else {"outcome": "found"},
        "validate": {"status": "valid", "terraform_version": "1.15.8", "provider_version": "6.53.0", "error_class": ""}
        if ok else None,
    }


def build(tmp: Path) -> tuple[Path, assemble.Inputs, dict]:
    work = tmp / "work"
    stage = work / "stage"
    cache = work / "licence_cache"
    texts = {1: NATIVE_TF, 2: HOST_TF, 3: HOST3_TF, 5: HOST_TF, 6: HOST3_TF, 7: NATIVE_TF}
    for mid, text in texts.items():
        (stage / str(mid)).mkdir(parents=True)
        (stage / str(mid) / "main.tf").write_bytes(text.encode("utf-8"))
    checks = {}
    for repo, name in ((10, "LICENSE"), (20, "LICENSE.md"), (30, "LICENSE"), (70, "LICENSE")):
        (cache / str(repo)).mkdir(parents=True)
        (cache / str(repo) / name).write_bytes(MIT_TEXT.encode("utf-8"))
        checks[repo] = licence.Check(repo, f"o/r{repo}", f"{repo:040d}", name, 200, len(MIT_TEXT),
                                     hashlib.sha256(MIT_TEXT.encode("utf-8")).hexdigest(), "MIT", "MIT", "found", "")
    candidates = [cand(1, 10, "native"), cand(7, 70, "native"), cand(2, 20, "host"), cand(3, 30, "host"),
                  cand(4, 40, "host"), cand(5, 50, "host"), cand(6, 60, "host")]
    records = {
        1: record(1, "native"), 7: record(7, "native", "E09_SECRET_FOUND", "gitleaks 1", "gitleaks x"),
        2: record(2, "host"), 3: record(3, "host"),
    }
    inp = assemble.Inputs(
        candidates=candidates,
        cheap={4: ("E06_MODULE_CALLS", "1 module block(s) read, 0 recorded by TerraDS", "module call")},
        plan=cascade.Plan([1, 7], [2, 3, 6], {5: 2}),
        records=records,
        lineage_of={1: "lin-000000000010", 2: "lin-000000000020", 3: "lin-000000000030", 5: "lin-000000000020",
                    6: "lin-000000000060", 7: "lin-000000000070"},
        lineage_stats=STATS, lineage_merges={"a": 0, "b": 1, "c": 0, "d": 0},
        lineage_comparison={"floor_0_as_written": dict(STATS, lineages=4)},
        licence_checks=checks, stage_dir=stage, licence_cache=cache,
        funnel_levels={lvl: {"modules": 10, "repos": 5} for lvl in cascade.my.LEVELS},
        e01_not_candidates={"native": 2, "host": 3},
    )
    pool = tmp / "pool"
    docs = assemble.write_pool(inp, pool)
    return pool, inp, docs


class TestAssembleAndVerify(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.pool, self.inp, self.docs = build(self.tmp)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def problems(self, **kw) -> list[str]:
        return report.verify_pool(self.pool, **kw)

    def pool_json(self) -> dict:
        return json.loads((self.pool / "pool.json").read_text(encoding="utf-8"))

    def save_pool_json(self, doc: dict) -> None:
        (self.pool / "pool.json").write_bytes(assemble.canonical_json(doc).encode("utf-8"))

    # ---- what assemble writes

    def test_synthetic_pool_verifies_clean(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_accepted_entries_and_ledger(self) -> None:
        entries = self.pool_json()["entries"]
        self.assertEqual([(e["kind"], e["module_id"]) for e in entries], [("native", 1), ("host", 2), ("host", 3)])
        funnel = json.loads((self.pool / "funnel.json").read_text(encoding="utf-8"))
        self.assertEqual(funnel["ledger"]["native"], {"considered": 2, "accepted": 1, "excluded": 1, "not_processed": 0})
        self.assertEqual(funnel["ledger"]["host"], {"considered": 5, "accepted": 2, "excluded": 2, "not_processed": 1})
        self.assertEqual(funnel["by_code"]["host"], {"E06_MODULE_CALLS": 1, "E10_LINEAGE_DUPLICATE": 1, "NOT_PROCESSED": 1})
        with (self.pool / "exclusions.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({(r["module_id"], r["code"]) for r in rows},
                         {("7", "E09_SECRET_FOUND"), ("4", "E06_MODULE_CALLS"), ("5", "E10_LINEAGE_DUPLICATE"),
                          ("6", "NOT_PROCESSED")})

    def test_files_are_lf_copies_with_the_archive_hash_kept_in_source_json(self) -> None:
        entry = self.pool_json()["entries"][0]
        text = (self.pool / entry["dir"] / "main.tf").read_bytes()
        self.assertEqual(text, NATIVE_TF.replace("\r\n", "\n").encode("utf-8"))
        source = json.loads((self.pool / entry["dir"] / "SOURCE.json").read_text(encoding="utf-8"))
        self.assertEqual(source["archive_sha256"]["main.tf"], hashlib.sha256(NATIVE_TF.encode("utf-8")).hexdigest())
        self.assertEqual(source["crlf_normalised"], ["main.tf"])
        self.assertEqual(entry["files"][0]["sha256"], hashlib.sha256(text).hexdigest())

    def test_the_licence_file_is_copied_next_to_the_module(self) -> None:
        entry = self.pool_json()["entries"][0]
        copied = (self.pool / entry["dir"] / "LICENSE.upstream").read_bytes()
        self.assertEqual(copied, MIT_TEXT.replace("\r\n", "\n").encode("utf-8"))
        self.assertEqual(entry["licence_file_sha256"], hashlib.sha256(copied).hexdigest())

    def test_entry_facts_native(self) -> None:
        e = self.pool_json()["entries"][0]
        self.assertEqual(e["resources"], ["aws_db_instance.database", "aws_instance.app", "aws_subnet.app"])
        self.assertEqual(e["type_counts"]["aws_instance"], 1)
        self.assertEqual(e["type_counts"]["aws_vpc"], 0)
        self.assertEqual(sorted(e["type_counts"]), sorted(assemble.TYPES))
        self.assertTrue(e["flags"]["has_count"])
        self.assertFalse(e["flags"]["has_data_sources"])
        self.assertTrue(e["graft_facts"]["ec2_rds_pair"])
        self.assertTrue(e["graft_facts"]["has_subnet"])
        self.assertFalse(e["graft_facts"]["has_vpc"])
        self.assertEqual(e["graft_facts"]["colliding_addresses"],
                         ["aws_db_instance.database", "aws_instance.app", "aws_subnet.app"])
        self.assertEqual(e["secrets"], {"gitleaks_findings": 0, "inventory_flagged": 0})
        self.assertEqual(e["validate"]["status"], "valid")
        self.assertEqual(e["lineage_id"], "lin-000000000010")

    def test_entry_facts_host_flags(self) -> None:
        e = self.pool_json()["entries"][1]
        self.assertTrue(e["flags"]["has_terraform_block"])
        self.assertTrue(e["flags"]["has_lifecycle"])
        self.assertTrue(e["flags"]["has_data_sources"])
        self.assertEqual(e["flags"]["data_sources"], ["aws_ami.a"])
        self.assertEqual(e["flags"]["terraform_required_version"], ">= 0.12")
        self.assertTrue(e["graft_facts"]["has_security_group"])
        self.assertFalse(e["graft_facts"]["ec2_rds_pair"])
        self.assertEqual(e["graft_facts"]["colliding_addresses"], [])

    def test_no_scenario_labels_or_judgement_fields(self) -> None:
        banned = {"label", "labels", "scenario", "grafted", "safe", "split", "dev", "test", "invariant"}
        for entry in self.pool_json()["entries"]:
            self.assertEqual(banned & set(entry), set())

    def test_json_is_canonical_and_documents_have_no_carriage_returns(self) -> None:
        for name in ("pool.json", "funnel.json", "lineages.json"):
            raw = (self.pool / name).read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertEqual(raw.decode("utf-8"), assemble.canonical_json(json.loads(raw)))
        for name in ("exclusions.csv", "licence_checks.csv", "validate_results.csv"):
            self.assertNotIn(b"\r", (self.pool / name).read_bytes())

    def test_lineages_document_covers_every_module_and_marks_the_accepted(self) -> None:
        doc = json.loads((self.pool / "lineages.json").read_text(encoding="utf-8"))
        flat = {m["module_id"]: m["accepted"] for ln in doc["lineages"].values() for m in ln["modules"]}
        self.assertEqual(flat, {1: True, 2: True, 3: True, 5: False, 6: False, 7: False})
        self.assertEqual(doc["lineages"]["lin-000000000020"]["modules"], [
            {"module_id": 2, "kind": "host", "accepted": True}, {"module_id": 5, "kind": "host", "accepted": False}])
        self.assertIn("not yet established", " ".join(doc["limits"]))

    def test_report_is_written_and_every_number_in_it_is_the_computed_one(self) -> None:
        text = (self.pool / "POOL_REPORT.md").read_text(encoding="utf-8")
        self.assertNotIn("\r", text)
        for needle in (
            "Ledger: considered 5 = accepted 2 + excluded 2 + not processed 1.",
            "Ledger: considered 2 = accepted 1 + excluded 1 + not processed 0.",
            "| real-world modules accepted | 3 |",
            "| native modules (already hold aws_instance and aws_db_instance) | 1 |",
            "| shortfall in modules (not filled, not padded) | 157 |",
            "| E09_SECRET_FOUND | 1 | 0 |",
            "| E10_LINEAGE_DUPLICATE | 0 | 1 |",
            "| NOT_PROCESSED | 0 | 1 |",
            "| MIT | 3 | 3 |",
            "Selection bias",
            "not yet established",
        ):
            self.assertIn(needle, text)

    def test_assembling_twice_gives_identical_bytes(self) -> None:
        first = {p.relative_to(self.pool).as_posix(): p.read_bytes() for p in self.pool.rglob("*") if p.is_file()}
        second_pool = self.tmp / "pool2"
        assemble.write_pool(self.inp, second_pool)
        second = {p.relative_to(second_pool).as_posix(): p.read_bytes() for p in second_pool.rglob("*") if p.is_file()}
        self.assertEqual(first, second)

    # ---- generated documents are pure functions of the committed pool files

    def test_report_is_reproduced_exactly_from_the_pool_files_alone(self) -> None:
        view = report.load_view(self.pool)
        self.assertEqual(report.render(view), (self.pool / "POOL_REPORT.md").read_text(encoding="utf-8"))

    def test_datasheet_section_carries_computed_numbers_and_is_idempotent(self) -> None:
        view = report.load_view(self.pool)
        section = report.datasheet_section(view)
        self.assertIn("Real-world modules accepted: 3 (1 native", section)
        self.assertIn("2 graft hosts", section)
        self.assertIn("shortfall in modules: 157 (not filled)", section)
        self.assertIn("hosts not processed after the stop rule: 1", section)
        self.assertIn("Licences of accepted modules: MIT 3.", section)
        base = "# Datasheet\n\n## Composition\n\nx\n\n## Uses\n\ny\n"
        once = report.update_datasheet(base, section)
        self.assertLess(once.index(report.DATASHEET_BEGIN), once.index("## Uses"))
        self.assertEqual(report.update_datasheet(once, section), once)
        changed = report.update_datasheet(once, section.replace("3 (1 native", "9 (1 native"))
        self.assertIn("9 (1 native", changed)
        self.assertNotIn("3 (1 native", changed)
        self.assertEqual(changed.count(report.DATASHEET_BEGIN), 1)

    def test_d4_carryover_states_facts_and_cites_files(self) -> None:
        text = report.d4_carryover(report.load_view(self.pool))
        self.assertIn("terrapreserve_versions.tf", text)
        self.assertIn("`~> 1.15.0`", text)
        self.assertIn("`6.53.0`", text)
        self.assertIn("terrads-native-1", text)  # the native defines core addresses
        self.assertIn("`aws_instance.app`", text)
        self.assertIn("pool/validate_results.csv", text)
        self.assertIn("pool/lineages.json", text)
        self.assertIn("Not yet established", text)
        for deciding_word in ("should", "recommend", "we propose", "D4 will"):
            self.assertNotIn(deciding_word, text.lower())

    # ---- tampering: each must be caught

    def first_module_file(self) -> Path:
        return self.pool / self.pool_json()["entries"][0]["dir"] / "main.tf"

    def test_the_builders_own_python_files_and_their_bytecode_are_not_pool_data(self) -> None:
        (self.pool / "build.py").write_text("x = 1" + chr(10), encoding="utf-8")
        (self.pool / "__pycache__").mkdir()
        (self.pool / "__pycache__" / "build.cpython-312.pyc").write_bytes(bytes([13, 10, 0, 1]) * 100)
        self.assertEqual(self.problems(), [])
        total = sum(p.stat().st_size for p in self.pool.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                    and p.suffix != ".py")
        self.assertEqual(self.problems(max_total=total), [])  # neither the .py file nor the bytecode counts

    def test_a_stray_data_file_at_the_top_of_the_pool_is_still_caught(self) -> None:
        (self.pool / "notes.txt").write_text("x", encoding="utf-8")
        self.assertTrue(any("notes.txt" in p for p in self.problems()), self.problems())

    def test_a_pool_file_edited_after_hashing_is_caught(self) -> None:
        path = self.first_module_file()
        path.write_bytes(path.read_bytes() + b"# edited\n")
        self.assertTrue(any("sha256" in p for p in self.problems()), self.problems())

    def test_a_file_that_pool_json_does_not_list_is_caught(self) -> None:
        (self.first_module_file().parent / "stray.tf").write_text("x", encoding="utf-8")
        self.assertTrue(any("stray.tf" in p for p in self.problems()), self.problems())

    def test_a_whole_unlisted_directory_is_caught(self) -> None:
        stray = self.pool / "terrads" / "host" / "999"
        stray.mkdir(parents=True)
        (stray / "main.tf").write_text("x", encoding="utf-8")
        self.assertTrue(any("999" in p for p in self.problems()), self.problems())

    def test_a_missing_listed_file_is_caught(self) -> None:
        self.first_module_file().unlink()
        self.assertTrue(any("missing" in p for p in self.problems()), self.problems())

    def test_a_dropped_exclusion_row_breaks_the_accounting(self) -> None:
        path = self.pool / "exclusions.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_bytes(("\n".join(lines[:-1]) + "\n").encode("utf-8"))
        self.assertTrue(any("exclusions" in p and ("account" in p or "balance" in p or "!=" in p) for p in self.problems()),
                        self.problems())

    def test_a_wrong_considered_count_is_caught(self) -> None:
        funnel = json.loads((self.pool / "funnel.json").read_text(encoding="utf-8"))
        funnel["ledger"]["host"]["considered"] += 1
        (self.pool / "funnel.json").write_bytes(assemble.canonical_json(funnel).encode("utf-8"))
        self.assertTrue(any("considered" in p for p in self.problems()), self.problems())

    def test_an_unknown_exclusion_code_is_caught(self) -> None:
        path = self.pool / "exclusions.csv"
        path.write_bytes(path.read_bytes().replace(b"E06_MODULE_CALLS", b"E99_MADE_UP", 1))
        self.assertTrue(any("E99_MADE_UP" in p for p in self.problems()), self.problems())

    def test_an_accepted_module_that_is_also_excluded_is_caught(self) -> None:
        path = self.pool / "exclusions.csv"
        with path.open("a", encoding="utf-8", newline="") as handle:
            handle.write("2,20,o/r20,.,host,excluded,E06_MODULE_CALLS,x,x\n")
        self.assertTrue(any("both accepted and excluded" in p or "twice" in p for p in self.problems()), self.problems())

    def test_a_secret_finding_in_an_accepted_entry_is_caught(self) -> None:
        doc = self.pool_json()
        doc["entries"][0]["secrets"]["gitleaks_findings"] = 1
        self.save_pool_json(doc)
        self.assertTrue(any("secrets" in p for p in self.problems()), self.problems())

    def test_a_non_permissive_licence_is_caught(self) -> None:
        doc = self.pool_json()
        doc["entries"][1]["licence_spdx"] = "GPL-3.0"
        self.save_pool_json(doc)
        self.assertTrue(any("permissive" in p for p in self.problems()), self.problems())

    def test_two_hosts_in_one_lineage_are_caught(self) -> None:
        doc = self.pool_json()
        doc["entries"][2]["lineage_id"] = doc["entries"][1]["lineage_id"]
        self.save_pool_json(doc)
        self.assertTrue(any("lineage" in p and "host" in p for p in self.problems()), self.problems())

    def test_an_accepted_entry_missing_from_lineages_json_is_caught(self) -> None:
        path = self.pool / "lineages.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        del doc["lineages"]["lin-000000000030"]
        path.write_bytes(assemble.canonical_json(doc).encode("utf-8"))
        self.assertTrue(any("lineages.json" in p for p in self.problems()), self.problems())

    def test_an_invalid_validate_result_in_an_accepted_entry_is_caught(self) -> None:
        doc = self.pool_json()
        doc["entries"][0]["validate"]["status"] = "invalid"
        self.save_pool_json(doc)
        self.assertTrue(any("validate" in p for p in self.problems()), self.problems())

    def test_carriage_returns_are_caught(self) -> None:
        path = self.pool / "exclusions.csv"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertTrue(any("CR" in p or "LF" in p for p in self.problems()), self.problems())

    def test_non_canonical_json_is_caught(self) -> None:
        path = self.pool / "funnel.json"
        path.write_text(json.dumps(json.loads(path.read_text(encoding="utf-8"))), encoding="utf-8")
        self.assertTrue(any("canonical" in p for p in self.problems()), self.problems())

    def test_size_limits_are_enforced(self) -> None:
        self.assertTrue(any("total" in p for p in self.problems(max_total=100)), self.problems(max_total=100))
        self.assertTrue(any("exceeds" in p for p in self.problems(max_file=50)), self.problems(max_file=50))

    def test_a_missing_pool_json_is_a_problem_not_a_pass(self) -> None:
        (self.pool / "pool.json").unlink()
        self.assertTrue(self.problems())


if __name__ == "__main__":
    unittest.main()
