"""sources/terrads/measure_yield.py on a tiny synthetic database with hand-checked counts.

Offline only. The database has the real TerraDS tables and the columns the script
reads; the nine modules below are chosen so that each funnel level has a known size.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources" / "terrads"))

import measure_yield as my  # noqa: E402

CALL_LOCAL = json.dumps([{"name": "child", "source": "./child"}])
CALL_REMOTE = json.dumps([{"name": "vpc", "source": "terraform-aws-modules/vpc/aws"}])

REPOS = [
    (1, "owner/one", "MIT", "sha1"),
    (2, "owner/two", "GPL-3.0", "sha2"),
    (3, "owner/three", "Apache-2.0", "sha3"),
    (4, "owner/four", "NOASSERTION", "sha4"),
    (5, "owner/five", None, "sha5"),
]
# (module id, repo id, path, module calls, diagnostics, managed types, data types)
MODULES = [
    (1, 1, "a", "[]", None, ["aws_vpc", "aws_subnet", "aws_kms_key"], []),  # non-S type: F1, not F2
    (2, 1, "b", "[]", None, ["aws_security_group"], ["aws_ami"]),  # S + data source: F2, not F2a
    (3, 2, ".", "[]", None, ["aws_db_subnet_group", "aws_db_instance"], []),  # C-67 type allowed
    (4, 3, "c", "[]", None, ["aws_instance", "aws_db_instance", "aws_security_group"], []),  # F3
    (5, 3, "d", CALL_LOCAL, "boom", ["aws_instance", "aws_db_instance", "aws_security_group_rule"], []),
    (6, 4, "e", "[]", None, ["aws_instance", "aws_db_instance", "aws_kms_key"], []),  # X only (and F1)
    (7, 4, "f", "[]", None, [], []),  # no resources at all
    (8, 2, "g", CALL_REMOTE, None, ["google_compute_instance"], []),  # not AWS
    (9, 5, "h", "[]", None, ["aws_subnet"], []),  # null licence
]


def build_database(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE Repositories (Id INTEGER PRIMARY KEY, FullName TEXT, License TEXT, LatestCommitSha TEXT);
        CREATE TABLE Modules (Id INTEGER PRIMARY KEY, RepositoryId INTEGER, Path TEXT,
                              ModuleCalls TEXT, DiagnosticMessages TEXT);
        CREATE TABLE Resources (Id INTEGER PRIMARY KEY AUTOINCREMENT, ModuleId INTEGER,
                                ResourceType TEXT, Name TEXT, Type TEXT, Provider TEXT);
        """
    )
    conn.executemany("INSERT INTO Repositories VALUES (?,?,?,?)", REPOS)
    for module_id, repo_id, mpath, calls, diag, managed, data in MODULES:
        conn.execute("INSERT INTO Modules VALUES (?,?,?,?,?)", (module_id, repo_id, mpath, calls, diag))
        for i, rtype in enumerate(managed):
            conn.execute(
                "INSERT INTO Resources (ModuleId, ResourceType, Name, Type, Provider) VALUES (?,?,?,?,?)",
                (module_id, "Managed", f"r{i}", rtype, rtype.split("_")[0]),
            )
        for i, rtype in enumerate(data):
            conn.execute(
                "INSERT INTO Resources (ModuleId, ResourceType, Name, Type, Provider) VALUES (?,?,?,?,?)",
                (module_id, "Data", f"d{i}", rtype, rtype.split("_")[0]),
            )
    # A second managed resource of an existing type: counted once in the type set.
    conn.execute(
        "INSERT INTO Resources (ModuleId, ResourceType, Name, Type, Provider) VALUES (4,'Managed','dup','aws_instance','aws')"
    )
    conn.commit()
    conn.close()


class SyntheticDatabaseCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.db = self.tmp / "synthetic.sqlite"
        build_database(self.db)
        self.conn = my.connect_readonly(self.db)
        self.addCleanup(self.conn.close)
        self.modules = my.load_modules(self.conn)
        self.repos = my.load_repos(self.conn)
        self.result = my.measure(self.modules, self.repos)


class TestFunnel(SyntheticDatabaseCase):
    def test_funnel_counts_match_hand_count(self) -> None:
        expected = {  # level: (modules, repositories)
            "F0": (9, 5),
            "F1": (7, 5),
            "F2": (5, 4),
            "F2a": (4, 3),
            "F2b": (4, 4),
            "F2ab": (3, 3),
            "F3": (2, 1),
            "F3ab": (1, 1),
            "F4": (2, 1),
            "G": (2, 2),
            "X": (3, 2),
        }
        got = {k: (v["modules"], v["repos"]) for k, v in self.result["funnel"].items()}
        self.assertEqual(got, expected)

    def test_module_with_non_s_type_is_excluded_from_f2(self) -> None:
        flags = my.flags(next(m for m in self.modules if m.module_id == 1))
        self.assertTrue(flags["F1"])
        self.assertFalse(flags["F2"])

    def test_data_source_keeps_f2_but_not_f2a(self) -> None:
        flags = my.flags(next(m for m in self.modules if m.module_id == 2))
        self.assertTrue(flags["F2"])
        self.assertFalse(flags["F2a"])
        self.assertTrue(flags["F2b"])

    def test_db_subnet_group_is_allowed(self) -> None:
        flags = my.flags(next(m for m in self.modules if m.module_id == 3))
        self.assertTrue(flags["F2"])
        self.assertFalse(flags["F3"])
        self.assertFalse(flags["G"])

    def test_f3_module(self) -> None:
        flags = my.flags(next(m for m in self.modules if m.module_id == 4))
        self.assertTrue(all(flags[k] for k in ("F2", "F2ab", "F3", "F3ab", "F4", "X")))
        self.assertFalse(flags["G"])

    def test_module_call_removes_f2b_and_f3ab_only(self) -> None:
        flags = my.flags(next(m for m in self.modules if m.module_id == 5))
        self.assertTrue(flags["F3"] and flags["F4"])
        self.assertFalse(flags["F2b"] or flags["F3ab"])

    def test_non_aws_module_is_not_even_f1(self) -> None:
        flags = my.flags(next(m for m in self.modules if m.module_id == 8))
        self.assertFalse(flags["F1"] or flags["F2"])

    def test_resource_with_no_managed_resource_is_not_f2(self) -> None:
        self.assertFalse(my.flags(next(m for m in self.modules if m.module_id == 7))["F2"])

    def test_licence_buckets_for_f2_and_f3(self) -> None:
        buckets = self.result["licence_buckets"]
        self.assertEqual(buckets["F2"]["permissive"], {"modules": 3, "repos": 2})
        self.assertEqual(buckets["F2"]["strong copyleft"], {"modules": 1, "repos": 1})
        self.assertEqual(buckets["F2"]["other/unknown"], {"modules": 1, "repos": 1})
        self.assertEqual(buckets["F2"]["weak copyleft"], {"modules": 0, "repos": 0})
        self.assertEqual(buckets["F3"]["permissive"], {"modules": 2, "repos": 1})
        self.assertEqual(buckets["G"]["permissive"], {"modules": 1, "repos": 1})
        self.assertEqual(buckets["G"]["other/unknown"], {"modules": 1, "repos": 1})

    def test_raw_licence_strings_are_listed_unmapped(self) -> None:
        self.assertEqual(
            self.result["licence_raw"]["F2"],
            {
                "Apache-2.0": {"modules": 2, "repos": 1},
                "GPL-3.0": {"modules": 1, "repos": 1},
                "MIT": {"modules": 1, "repos": 1},
                "<null>": {"modules": 1, "repos": 1},
            },
        )

    def test_diagnostics_and_call_variants(self) -> None:
        self.assertEqual(self.result["f2_modules_with_diagnostics"], 1)
        self.assertEqual(self.result["f2b_nonlocal_calls_only"], 5)  # the one call is local

    def test_database_is_opened_read_only(self) -> None:
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute("DELETE FROM Modules")


class TestOutputs(SyntheticDatabaseCase):
    def test_main_writes_candidates_and_yield_json(self) -> None:
        out = self.tmp / "out"
        code = my.main(
            [
                str(self.db), "--out-dir", str(out),
                "--manifest", str(self.tmp / "none.json"), "--published", str(self.tmp / "none2.json"),
            ]
        )
        self.assertEqual(code, 0)
        with (out / "candidates.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(sorted(int(r["module_id"]) for r in rows), [2, 3, 4, 5, 9])
        by_id = {int(r["module_id"]): r for r in rows}
        self.assertEqual(by_id[4]["managed_types"], "aws_db_instance;aws_instance;aws_security_group")
        self.assertEqual((by_id[4]["F3"], by_id[4]["F4"], by_id[4]["G"]), ("1", "1", "0"))
        self.assertEqual(by_id[2]["F2a"], "0")
        self.assertEqual(by_id[9]["licence_bucket"], "other/unknown")
        document = json.loads((out / "yield.json").read_text(encoding="utf-8"))
        self.assertEqual(document["funnel"]["F3"], {"modules": 2, "repos": 1})
        self.assertEqual(document["seed"], 20261023)
        self.assertIn("| F3 |", (out / "yield_report.md").read_text(encoding="utf-8"))
        inventory = (out / "licence_inventory.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(inventory), 1 + 4)  # header + repos 1, 2, 3, 5

    def test_schema_dump_lists_tables_columns_and_counts(self) -> None:
        tables = {t["name"]: t for t in my.dump_schema(self.conn)}
        self.assertEqual(tables["Modules"]["rows"], 9)
        self.assertEqual(tables["Repositories"]["rows"], 5)
        self.assertIn("ModuleCalls", [c["name"] for c in tables["Modules"]["columns"]])


class TestDefinitions(unittest.TestCase):
    def test_type_sets(self) -> None:
        self.assertEqual(len(my.T9), 9)
        self.assertEqual(
            my.T9,
            {
                "aws_vpc", "aws_subnet", "aws_route_table", "aws_route_table_association",
                "aws_internet_gateway", "aws_instance", "aws_security_group",
                "aws_security_group_rule", "aws_db_instance",
            },
        )
        self.assertEqual(my.S, my.T9 | {"aws_db_subnet_group"})

    def test_licence_buckets(self) -> None:
        cases = {
            "MIT": "permissive", "Zlib": "permissive", "0BSD": "permissive",
            "MPL-2.0": "weak copyleft", "LGPL-2.1": "weak copyleft", "EPL-2.0": "weak copyleft",
            "GPL-3.0": "strong copyleft", "AGPL-3.0": "strong copyleft",
            "NOASSERTION": "other/unknown", None: "other/unknown", "MIT-0": "other/unknown",
            "WTFPL": "other/unknown",
        }
        for licence, bucket in cases.items():
            with self.subTest(licence=licence):
                self.assertEqual(my.licence_bucket(licence), bucket)

    def test_module_call_parsing(self) -> None:
        self.assertEqual(my.parse_module_calls("[]"), (0, 0))
        self.assertEqual(my.parse_module_calls("null"), (0, 0))
        self.assertEqual(my.parse_module_calls(None), (0, 0))
        self.assertEqual(my.parse_module_calls(CALL_LOCAL), (1, 0))
        self.assertEqual(my.parse_module_calls(CALL_REMOTE), (1, 1))


if __name__ == "__main__":
    unittest.main()
