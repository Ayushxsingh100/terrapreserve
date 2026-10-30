"""pool/cascade.py: the cheap exclusion codes E01 to E08, the archive reader and the candidate loader (D3 step 3).

Every code fires on a hand-made case and not on its negative twin; first-match-wins is tested with modules
that trigger two codes. Synthetic inputs only (a tar.gz and a SQLite database are built at run time).
"""

from __future__ import annotations

import gzip
import io
import json
import sqlite3
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pool import cascade  # noqa: E402

GOOD = 'resource "aws_instance" "web" {\n  ami = "x"\n}\n'
ROWS = frozenset({("aws_instance", "web")})


def cand(**over) -> cascade.Candidate:
    base = dict(
        module_id=1, repo_id=10, path=".", full_name="o/r", commit_sha="c" * 40, licence="MIT",
        kind="native", has_diagnostics=False, n_calls=0, rows=ROWS,
    )
    base.update(over)
    return cascade.Candidate(**base)


def run(files, **over) -> cascade.Verdict:
    return cascade.evaluate(cand(**over), {k: v.encode() if isinstance(v, str) else v for k, v in files.items()}
                            if files is not None else None)


class TestCodes(unittest.TestCase):
    def test_the_code_list_is_the_one_in_the_work_package(self) -> None:
        self.assertEqual(
            cascade.CODES,
            (
                "E01_LICENCE_BUCKET", "E02_NOT_IN_ARCHIVE", "E03_ANALYSER_DIAGNOSTICS", "E04_LEXER_ANOMALY",
                "E05_METADATA_DISAGREES", "E06_MODULE_CALLS", "E07_DANGLING_REFERENCE", "E08_OVERSIZE",
                "E09_SECRET_FOUND", "E10_LINEAGE_DUPLICATE", "E11_LICENCE_UNVERIFIED", "E12_INVALID_UNDER_PIN",
            ),
        )

    def test_a_clean_module_passes_with_facts(self) -> None:
        v = run({"main.tf": GOOD})
        self.assertIsNone(v.code)
        self.assertEqual((v.n_files, v.total_bytes), (1, len(GOOD)))


class TestE01(unittest.TestCase):
    def test_non_permissive_licences_are_excluded(self) -> None:
        for lic in ("GPL-3.0", "MPL-2.0", "LGPL-2.1", "NOASSERTION", None, "WTFPL", "CC-BY-4.0", "EUPL-1.2"):
            with self.subTest(licence=lic):
                self.assertEqual(run({"main.tf": GOOD}, licence=lic).code, "E01_LICENCE_BUCKET")

    def test_permissive_licences_pass(self) -> None:
        for lic in ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Unlicense", "CC0-1.0",
                    "Zlib", "MIT-0", "BSL-1.0"):
            with self.subTest(licence=lic):
                self.assertIsNone(run({"main.tf": GOOD}, licence=lic).code)


class TestE02(unittest.TestCase):
    def test_repository_missing_from_the_archive(self) -> None:
        self.assertEqual(run(None).code, "E02_NOT_IN_ARCHIVE")

    def test_module_directory_without_tf_files(self) -> None:
        self.assertEqual(run({}).code, "E02_NOT_IN_ARCHIVE")

    def test_only_terraform_ignored_files(self) -> None:
        self.assertEqual(run({".hidden.tf": GOOD, "x.tf~": GOOD, "#y.tf#": GOOD}).code, "E02_NOT_IN_ARCHIVE")

    def test_one_real_file_among_ignored_ones_passes(self) -> None:
        self.assertIsNone(run({".hidden.tf": "garbage {", "main.tf": GOOD}).code)


class TestE03(unittest.TestCase):
    def test_diagnostics_exclude(self) -> None:
        self.assertEqual(run({"main.tf": GOOD}, has_diagnostics=True).code, "E03_ANALYSER_DIAGNOSTICS")

    def test_no_diagnostics_passes(self) -> None:
        self.assertIsNone(run({"main.tf": GOOD}, has_diagnostics=False).code)


class TestE04(unittest.TestCase):
    def test_unclosed_brace(self) -> None:
        self.assertEqual(run({"main.tf": 'resource "aws_instance" "web" {\n  ami = "x"\n'}).code, "E04_LEXER_ANOMALY")

    def test_stray_closing_brace(self) -> None:
        self.assertEqual(run({"main.tf": GOOD + "}\n"}).code, "E04_LEXER_ANOMALY")

    def test_malformed_header_with_one_label(self) -> None:
        self.assertEqual(run({"main.tf": 'resource "aws_instance" {\n}\n'}).code, "E04_LEXER_ANOMALY")

    def test_anomaly_in_any_file_counts(self) -> None:
        self.assertEqual(run({"a.tf": GOOD, "b.tf": "locals {\n"}).code, "E04_LEXER_ANOMALY")

    def test_balanced_braces_inside_strings_and_heredocs_are_fine(self) -> None:
        text = GOOD + 'locals {\n  s = "}{"\n  h = <<EOT\n}}}\nEOT\n}\n'
        self.assertIsNone(run({"main.tf": text}).code)


class TestE05(unittest.TestCase):
    def test_lexer_sees_a_resource_that_terraform_ds_does_not_list(self) -> None:
        text = GOOD + 'resource "aws_vpc" "v" {\n}\n'
        self.assertEqual(run({"main.tf": text}).code, "E05_METADATA_DISAGREES")

    def test_terraform_ds_lists_a_resource_the_lexer_does_not_see(self) -> None:
        rows = ROWS | {("aws_vpc", "v")}
        self.assertEqual(run({"main.tf": GOOD}, rows=rows).code, "E05_METADATA_DISAGREES")

    def test_same_type_different_name(self) -> None:
        self.assertEqual(run({"main.tf": GOOD}, rows=frozenset({("aws_instance", "other")})).code,
                         "E05_METADATA_DISAGREES")

    def test_agreeing_sets_pass(self) -> None:
        self.assertIsNone(run({"main.tf": GOOD + 'data "aws_ami" "a" {\n}\n'}).code)


class TestE06(unittest.TestCase):
    def test_module_block(self) -> None:
        text = GOOD + 'module "m" {\n  source = "./m"\n}\n'
        self.assertEqual(run({"main.tf": text}).code, "E06_MODULE_CALLS")

    def test_terraform_ds_reports_a_call_the_lexer_missed(self) -> None:
        self.assertEqual(run({"main.tf": GOOD}, n_calls=1).code, "E06_MODULE_CALLS")

    def test_word_module_in_a_comment_or_string_is_not_a_call(self) -> None:
        text = GOOD + '# module "m" {}\nlocals {\n  s = "module"\n}\n'
        self.assertIsNone(run({"main.tf": text}).code)


class TestE07(unittest.TestCase):
    def test_dangling_reference(self) -> None:
        text = 'resource "aws_instance" "web" {\n  vpc_security_group_ids = [aws_security_group.sg.id]\n}\n'
        v = run({"main.tf": text})
        self.assertEqual(v.code, "E07_DANGLING_REFERENCE")
        self.assertIn("aws_security_group.sg", v.detail)

    def test_dangling_reference_through_interpolation(self) -> None:
        text = 'resource "aws_instance" "web" {\n  subnet_id = "${aws_subnet.a.id}"\n}\n'
        self.assertEqual(run({"main.tf": text}).code, "E07_DANGLING_REFERENCE")

    def test_defined_reference_passes(self) -> None:
        text = ('resource "aws_instance" "web" {\n  subnet_id = aws_subnet.a.id\n}\n'
                'resource "aws_subnet" "a" {\n}\n')
        rows = frozenset({("aws_instance", "web"), ("aws_subnet", "a")})
        self.assertIsNone(run({"main.tf": text}, rows=rows).code)


class TestE08(unittest.TestCase):
    @staticmethod
    def files_of(n: int, pad: int = 0) -> tuple[dict[str, str], frozenset]:
        files = {f"f{i:02d}.tf": f'resource "aws_vpc" "v{i}" {{\n}}\n' for i in range(n)}
        if pad:
            files["f00.tf"] += "#" * pad
        return files, frozenset(("aws_vpc", f"v{i}") for i in range(n))

    def test_forty_files_pass_forty_one_fail(self) -> None:
        files, rows = self.files_of(40)
        self.assertIsNone(run(files, rows=rows).code)
        files, rows = self.files_of(41)
        self.assertEqual(run(files, rows=rows).code, "E08_OVERSIZE")

    def test_200_kib_passes_one_byte_more_fails(self) -> None:
        files, rows = self.files_of(1)
        pad = 200 * 1024 - len(files["f00.tf"])
        files["f00.tf"] += "#" * pad
        self.assertEqual(sum(len(t) for t in files.values()), 204800)
        self.assertIsNone(run(files, rows=rows).code)
        files["f00.tf"] += "#"
        self.assertEqual(run(files, rows=rows).code, "E08_OVERSIZE")

    def test_size_counts_bytes_not_characters(self) -> None:
        files, rows = self.files_of(1)
        files["f00.tf"] += "#" + "é" * 102_400  # 204,800 bytes of multi-byte text on its own
        self.assertEqual(run(files, rows=rows).code, "E08_OVERSIZE")


class TestFirstMatchWins(unittest.TestCase):
    def test_e01_beats_e02(self) -> None:
        self.assertEqual(run(None, licence="GPL-3.0").code, "E01_LICENCE_BUCKET")

    def test_e02_beats_e03(self) -> None:
        self.assertEqual(run({}, has_diagnostics=True).code, "E02_NOT_IN_ARCHIVE")

    def test_e03_beats_e04(self) -> None:
        self.assertEqual(run({"main.tf": "locals {\n"}, has_diagnostics=True).code, "E03_ANALYSER_DIAGNOSTICS")

    def test_e04_beats_e05(self) -> None:
        text = GOOD + 'resource "aws_vpc" "v" {\n'
        self.assertEqual(run({"main.tf": text}).code, "E04_LEXER_ANOMALY")

    def test_e05_beats_e06(self) -> None:
        text = GOOD + 'resource "aws_vpc" "v" {\n}\nmodule "m" {\n}\n'
        self.assertEqual(run({"main.tf": text}).code, "E05_METADATA_DISAGREES")

    def test_e06_beats_e07(self) -> None:
        text = GOOD.replace('ami = "x"', "ami = aws_vpc.v.id") + 'module "m" {\n}\n'
        self.assertEqual(run({"main.tf": text}).code, "E06_MODULE_CALLS")

    def test_e07_beats_e08(self) -> None:
        text = GOOD.replace('ami = "x"', "ami = aws_vpc.v.id") + "#" * 210_000
        self.assertEqual(run({"main.tf": text}).code, "E07_DANGLING_REFERENCE")


def make_archive(path: Path, repos: dict[int, dict[str, bytes]]) -> None:
    """An outer tar.gz of ``<repo id>.tar.gz`` files, each an inner tar.gz of ``<repo id>/<path>``."""
    with tarfile.open(path, "w:gz") as outer:
        for repo_id, members in repos.items():
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as inner:
                for name, data in members.items():
                    info = tarfile.TarInfo(f"{repo_id}/{name}")
                    info.size = len(data)
                    inner.addfile(info, io.BytesIO(data))
            blob = buf.getvalue()
            info = tarfile.TarInfo(f"{repo_id}.tar.gz")
            info.size = len(blob)
            outer.addfile(info, io.BytesIO(blob))


class TestArchiveReader(unittest.TestCase):
    def test_reads_only_wanted_repositories_and_tf_files_with_raw_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "a.tar.gz"
            make_archive(archive, {
                1: {"main.tf": b"a\r\nb\r\n", "sub/x.tf": b"x", "README.md": b"no", "sub/y.tf.json": b"{}"},
                2: {"main.tf": b"other"},
                3: {"net/m.tf": b"m"},
            })
            got = dict(cascade.iter_archive(archive, {1, 3, 99}))
        self.assertEqual(sorted(got), [1, 3])
        self.assertEqual(got[1], {".": {"main.tf": b"a\r\nb\r\n"}, "sub": {"x.tf": b"x"}})
        self.assertEqual(got[3], {"net": {"m.tf": b"m"}})


def make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE Repositories (Id INTEGER PRIMARY KEY, FullName TEXT, License TEXT, LatestCommitSha TEXT);
        CREATE TABLE Modules (Id INTEGER PRIMARY KEY, RepositoryId INTEGER, Path TEXT, ModuleCalls TEXT,
                              DiagnosticMessages TEXT);
        CREATE TABLE Resources (Id INTEGER PRIMARY KEY, ModuleId INTEGER, ResourceType TEXT, Name TEXT, Type TEXT);
        """
    )
    conn.executemany("INSERT INTO Repositories VALUES (?,?,?,?)", [
        (1, "o/mit", "MIT", "s1"), (2, "o/gpl", "GPL-3.0", "s2"), (3, "o/apache", "Apache-2.0", "s3"),
        (4, "o/none", None, "s4"),
    ])
    modules = [
        (10, 1, ".", "[]", None),  # native: instance + db instance, MIT
        (11, 2, ".", "[]", None),  # F3 but GPL: counted under E01, not a candidate
        (12, 3, "a", "[]", None),  # host: security group only, Apache-2.0
        (13, 4, ".", "[]", None),  # G but licence null: counted under E01
        (14, 1, "v", "[]", None),  # F2 (only a vpc) but neither F3 nor G
        (15, 3, "x", "[]", "diag"),  # host with diagnostics: still a candidate (E03 decides later)
        (16, 1, "k", "[]", None),  # not F2 (contains a type outside S)
    ]
    conn.executemany("INSERT INTO Modules VALUES (?,?,?,?,?)", modules)
    res = [
        (10, "aws_instance", "web"), (10, "aws_db_instance", "db"),
        (11, "aws_instance", "web"), (11, "aws_db_instance", "db"),
        (12, "aws_security_group", "sg"),
        (13, "aws_security_group", "sg"),
        (14, "aws_vpc", "v"),
        (15, "aws_subnet", "s"),
        (16, "aws_s3_bucket", "b"), (16, "aws_security_group", "sg"),
    ]
    conn.executemany(
        "INSERT INTO Resources (ModuleId, ResourceType, Name, Type) VALUES (?,?,?,?)",
        [(m, "Managed", n, t) for m, t, n in res],
    )
    conn.commit()
    conn.close()


class TestLoadCandidates(unittest.TestCase):
    def test_native_is_f3_and_permissive_host_is_g_and_permissive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.sqlite"
            make_db(db)
            loaded = cascade.load_candidates(db)
        by_id = {c.module_id: c for c in loaded.candidates}
        self.assertEqual(sorted(by_id), [10, 12, 15])
        self.assertEqual({k: c.kind for k, c in by_id.items()}, {10: "native", 12: "host", 15: "host"})
        self.assertEqual(by_id[10].rows, frozenset({("aws_instance", "web"), ("aws_db_instance", "db")}))
        self.assertEqual((by_id[10].full_name, by_id[10].commit_sha, by_id[10].licence), ("o/mit", "s1", "MIT"))
        self.assertTrue(by_id[15].has_diagnostics)
        self.assertFalse(by_id[12].has_diagnostics)

    def test_non_permissive_f3_and_g_are_counted_under_e01_but_are_not_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.sqlite"
            make_db(db)
            loaded = cascade.load_candidates(db)
        self.assertEqual(loaded.e01_not_candidates, {"native": 1, "host": 1})

    def test_funnel_levels_are_measured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.sqlite"
            make_db(db)
            loaded = cascade.load_candidates(db)
        self.assertEqual(loaded.funnel["F0"], {"modules": 7, "repos": 4})
        self.assertEqual(loaded.funnel["F2"]["modules"], 6)
        self.assertEqual(loaded.funnel["F3"]["modules"], 2)
        self.assertEqual(loaded.funnel["G"]["modules"], 3)


class TestRunFilter(unittest.TestCase):
    def test_end_to_end_on_a_synthetic_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db = tmp_path / "t.sqlite"
            make_db(db)
            native = (
                'resource "aws_instance" "web" {\n  ami = "x"\n}\n'
                'resource "aws_db_instance" "db" {\n  engine = "mysql"\n}\n'
            )
            host = 'resource "aws_security_group" "sg" {\n}\n'
            archive = tmp_path / "a.tar.gz"
            make_archive(archive, {1: {"main.tf": native.encode()}, 3: {"a/sg.tf": host.encode()}})
            work = tmp_path / "work"
            summary = cascade.run_filter(db, archive, work)
            results = [json.loads(line) for line in (work / "cheap_results.jsonl").read_text("utf-8").splitlines()]
            staged = sorted(p.relative_to(work / "stage").as_posix() for p in (work / "stage").rglob("*.tf"))
        by_id = {r["module_id"]: r for r in results}
        self.assertEqual(sorted(by_id), [10, 12, 15])
        self.assertIsNone(by_id[10]["code"])
        self.assertIsNone(by_id[12]["code"])
        self.assertEqual(by_id[15]["code"], "E02_NOT_IN_ARCHIVE")  # module path "x" is not in the archive
        self.assertEqual(staged, ["10/main.tf", "12/sg.tf"])
        self.assertEqual(summary["considered"], {"native": 1, "host": 2})
        self.assertEqual(summary["passed"], {"native": 1, "host": 1})
        self.assertEqual(summary["by_code"]["host"], {"E02_NOT_IN_ARCHIVE": 1})

    def test_module_with_diagnostics_in_the_archive_is_excluded_as_e03(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db = tmp_path / "t.sqlite"
            make_db(db)
            archive = tmp_path / "a.tar.gz"
            make_archive(archive, {
                1: {"main.tf": b'resource "aws_instance" "web" {}\nresource "aws_db_instance" "db" {}\n'},
                3: {"a/sg.tf": b'resource "aws_security_group" "sg" {}\n',
                    "x/s.tf": b'resource "aws_subnet" "s" {}\n'},
            })
            work = tmp_path / "work"
            summary = cascade.run_filter(db, archive, work)
        self.assertEqual(summary["by_code"]["host"], {"E03_ANALYSER_DIAGNOSTICS": 1})
        self.assertEqual(summary["passed"]["host"], 1)


class TestCli(unittest.TestCase):
    def test_filter_sub_command_exists_and_bare_call_prints_help(self) -> None:
        from pool import build

        args = build.build_parser().parse_args(["filter", "--work", "w"])
        self.assertEqual(args.command, "filter")
        self.assertEqual(build.main([]), 2)


if __name__ == "__main__":
    unittest.main()
