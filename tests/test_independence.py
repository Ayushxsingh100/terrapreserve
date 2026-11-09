"""D0 gate 1 / DAIL ADR-010 / ADR-013: nothing here may import or depend on DAIL.

Walks every ``*.py`` file with ``ast`` (nothing is imported or executed) and
every dependency file, and fails on any DAIL reference. A self-test feeds in
synthetic sources, so a checker that can no longer fail is itself caught.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# DAIL top-level names, read from https://github.com/Ayushxsingh100/DAIL at 7ed7aaf:
#   pyproject.toml:57  [tool.setuptools.packages.find] include = ["core*", "evidence*", "llm*"]
#                      (the importable top-level packages)
#   pyproject.toml:2   name = "cloudspartanx"  (the distribution name)
# "dail" is the project's own name and is forbidden as well.
FORBIDDEN = frozenset({"dail", "cloudspartanx", "core", "evidence", "llm"})
DAIL_REPO_URL = "github.com/ayushxsingh100/dail"

SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        ".venv-tools",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".terraform",
        "node_modules",
        "cache",
        "_cache",
    }
)


def imported_top_levels(source: str) -> set[str]:
    """Top-level names of every absolute import in ``source``."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".", 1)[0])
    return found


def forbidden_imports(source: str) -> set[str]:
    return imported_top_levels(source) & FORBIDDEN


def _requirement_name(spec: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)", spec)
    return re.sub(r"[-_.]+", "-", match.group(1)).lower() if match else ""


def dependency_violations(filename: str, text: str) -> list[str]:
    """DAIL mentions in a dependency file (requirements*.txt or pyproject.toml)."""
    lowered = text.lower()
    problems = []
    if DAIL_REPO_URL in lowered:
        problems.append(f"{filename}: mentions {DAIL_REPO_URL}")
    for name in ("dail", "cloudspartanx"):
        if name in lowered:
            problems.append(f"{filename}: mentions {name!r}")
    # The generic package names (core, evidence, llm) are only flagged when they
    # appear as a requirement name, not as an ordinary word.
    if filename.endswith(".toml"):
        specs = [a or b for a, b in re.findall(r"\"([^\"\n]+)\"|'([^'\n]+)'", text)]
    else:
        specs = [line.split("#", 1)[0] for line in text.splitlines()]
    for spec in specs:
        name = _requirement_name(spec)
        if name in FORBIDDEN:
            problems.append(f"{filename}: depends on {name!r}")
    return sorted(set(problems))


def _walk(patterns: tuple[str, ...]) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if any(Path(name).match(p) for p in patterns):
                found.append(Path(dirpath) / name)
    return sorted(found)


class TestIndependence(unittest.TestCase):
    def test_no_python_file_imports_dail(self) -> None:
        files = _walk(("*.py",))
        self.assertIn(Path(__file__).resolve(), [f.resolve() for f in files])
        violations = []
        for path in files:
            source = path.read_text(encoding="utf-8")
            rel = path.relative_to(REPO_ROOT)
            try:
                bad = forbidden_imports(source)
            except SyntaxError as exc:
                violations.append(f"{rel}: cannot parse ({exc})")
                continue
            violations.extend(f"{rel}: imports {name}" for name in sorted(bad))
        self.assertEqual(violations, [])

    def test_no_dependency_file_mentions_dail(self) -> None:
        violations = []
        for path in _walk(("requirements*.txt", "pyproject.toml")):
            text = path.read_text(encoding="utf-8")
            violations.extend(dependency_violations(str(path.relative_to(REPO_ROOT)), text))
        self.assertEqual(violations, [])


class TestPoolIsCovered(unittest.TestCase):
    """D3: the pool builder must sit under the same independence check (D0 gate 1)."""

    def test_walk_reaches_every_pool_module(self) -> None:
        walked = {f.resolve() for f in _walk(("*.py",))}
        pool_files = sorted((REPO_ROOT / "pool").glob("*.py"))
        self.assertGreaterEqual(len(pool_files), 9)
        self.assertEqual([f for f in pool_files if f.resolve() not in walked], [])

    def test_pool_module_importing_dail_would_be_caught(self) -> None:
        self.assertEqual(forbidden_imports("import core\n"), {"core"})
        self.assertEqual(forbidden_imports("from evidence.x import y\n"), {"evidence"})


class TestGeneratorIsCovered(unittest.TestCase):
    """D4: the scenario generator must sit under the same independence check (D0 gate 1)."""

    def test_walk_reaches_every_generator_module(self) -> None:
        walked = {f.resolve() for f in _walk(("*.py",))}
        gen_files = sorted((REPO_ROOT / "generator").glob("*.py"))
        self.assertGreaterEqual(len(gen_files), 5)
        self.assertEqual([f for f in gen_files if f.resolve() not in walked], [])

    def test_generator_module_importing_dail_would_be_caught(self) -> None:
        self.assertEqual(forbidden_imports("import core\n"), {"core"})
        self.assertEqual(forbidden_imports("from core.impact import x\n"), {"core"})
        self.assertEqual(forbidden_imports("from core.verification import y\n"), {"core"})
        self.assertEqual(forbidden_imports("from core.promotion import z\n"), {"core"})


class TestCheckerCanFail(unittest.TestCase):
    """Self-test: the checker catches DAIL imports and ignores innocent ones."""

    def test_catches_import_dail_core(self) -> None:
        self.assertEqual(forbidden_imports("import dail.core\n"), {"dail"})

    def test_catches_from_import_of_every_dail_package(self) -> None:
        for name in sorted(FORBIDDEN):
            with self.subTest(package=name):
                self.assertEqual(forbidden_imports(f"from {name} import x\n"), {name})
                self.assertEqual(forbidden_imports(f"from {name}.sub import x\n"), {name})

    def test_catches_import_nested_in_function(self) -> None:
        self.assertEqual(forbidden_imports("def f():\n    import evidence\n"), {"evidence"})

    def test_does_not_flag_innocent_imports(self) -> None:
        self.assertEqual(forbidden_imports("import json\nfrom pathlib import Path\n"), set())

    def test_does_not_flag_relative_imports(self) -> None:
        self.assertEqual(forbidden_imports("from . import core\nfrom .llm import x\n"), set())

    def test_dependency_checker_catches_dail(self) -> None:
        self.assertTrue(dependency_violations("requirements.txt", "dail==1.0\n"))
        self.assertTrue(dependency_violations("requirements.txt", "cloudspartanx>=0.1\n"))
        self.assertTrue(dependency_violations("requirements.txt", "core==1.0\n"))
        url = "git+https://" + "github.com/Ayushxsingh100/" + "DAIL" + ".git\n"
        self.assertTrue(dependency_violations("requirements-dev.txt", url))
        toml = '[project]\ndependencies = ["llm==1.0"]\n'
        self.assertTrue(dependency_violations("pyproject.toml", toml))

    def test_dependency_checker_ignores_innocent_files(self) -> None:
        self.assertEqual(dependency_violations("requirements.txt", "requests==2.32.0\n"), [])
        self.assertEqual(
            dependency_violations("requirements.txt", "azure-core==1.0  # core library\n"), []
        )
        toml = '[project]\nname = "terrapreserve"\ndependencies = []\n'
        self.assertEqual(dependency_violations("pyproject.toml", toml), [])


# ---------------------------------------------------------------------------
# D5-03: the oracle's own independence (D5a). ``TP_INDEPENDENCE_ROOT`` points these checks at a scratch
# copy of the repository, so a planted violation can be shown to fail without touching the real tree.
# ---------------------------------------------------------------------------

ORACLE_FORBIDDEN_DIRS = ("generator", "pool", "sources", "tests", "tools")
GROUND_TRUTH_FIELDS = ("labels", "gt_class", "oracle")
GROUND_TRUTH_WRITERS = ("oracle", "tools")  # top-level directories allowed to write non-null ground truth


def _root() -> Path:
    return Path(os.environ.get("TP_INDEPENDENCE_ROOT", str(REPO_ROOT)))


def _module_names(root: Path) -> set[str]:
    """Importable names that live in the forbidden directories (modules, packages, the directory names)."""
    names = set(ORACLE_FORBIDDEN_DIRS)
    for d in ORACLE_FORBIDDEN_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            names.update(Path(f).stem for f in filenames if f.endswith(".py") and f != "__init__.py")
            names.update(dirnames)
    return names


def oracle_import_violations(root: Path) -> list[str]:
    """Imports under ``oracle/`` that are not the standard library or ``oracle`` itself; sys.path edits."""
    out: list[str] = []
    forbidden_local = _module_names(root)
    stdlib = set(sys.stdlib_module_names)
    for path in sorted((root / "oracle").rglob("*.py")):
        rel = path.relative_to(root)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".", 1)[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".", 1)[0]]
            for n in names:
                if n == "oracle":
                    continue
                if n in FORBIDDEN:
                    out.append(f"{rel}: imports DAIL name {n} ")
                elif n in forbidden_local:
                    out.append(f"{rel}: imports {n} (a name from generator/, pool/, sources/, tests/ or tools/)")
                elif n not in stdlib:
                    out.append(f"{rel}: imports {n} (only the standard library and oracle are allowed)")
            if isinstance(node, ast.Attribute) and node.attr == "path" and isinstance(node.value, ast.Name) \
                    and node.value.id == "sys":
                out.append(f"{rel}: touches sys.path (line {node.lineno})")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
                out.append(f"{rel}: uses __import__ (line {node.lineno})")
    return out


def _non_null(node: ast.AST) -> bool:
    return not (isinstance(node, ast.Constant) and node.value is None)


def ground_truth_write_violations(root: Path) -> list[str]:
    """Python outside ``oracle/`` and ``tools/`` that writes a non-null labels, gt_class or oracle field."""
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = Path(dirpath).relative_to(root)
        if rel_dir.parts and rel_dir.parts[0] in GROUND_TRUTH_WRITERS:
            continue
        for name in filenames:
            if not name.endswith(".py"):
                continue
            path = Path(dirpath) / name
            rel = path.relative_to(root)
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Dict):
                    for k, v in zip(node.keys, node.values):
                        if isinstance(k, ast.Constant) and k.value in GROUND_TRUTH_FIELDS and _non_null(v):
                            out.append(f"{rel}:{node.lineno}: writes {k.value!r} with a non-null value")
                elif isinstance(node, (ast.Assign, ast.AugAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for t in targets:
                        if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) \
                                and t.slice.value in GROUND_TRUTH_FIELDS and _non_null(node.value):
                            out.append(f"{rel}:{node.lineno}: assigns {t.slice.value!r} a non-null value")
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("update", "setdefault"):
                        for kw in node.keywords:
                            if kw.arg in GROUND_TRUTH_FIELDS and _non_null(kw.value):
                                out.append(f"{rel}:{node.lineno}: {node.func.attr}({kw.arg}=...) non-null")
                    if node.func.attr == "setdefault" and len(node.args) > 1 \
                            and isinstance(node.args[0], ast.Constant) and node.args[0].value in GROUND_TRUTH_FIELDS \
                            and _non_null(node.args[1]):
                        out.append(f"{rel}:{node.lineno}: setdefault({node.args[0].value!r}, ...) non-null")
    return out


def committed_ground_truth_violations(root: Path) -> list[str]:
    out = []
    for p in sorted((root / "scenarios" / "dev").glob("tp-v1-*/scenario.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for f in GROUND_TRUTH_FIELDS:
            if d.get(f, None) is not None:
                out.append(f"{p.parent.name}: {f} is not null")
    return out


class TestOracleIndependence(unittest.TestCase):
    """D5-03 (DAIL ADR-010; CLAUDE.md rules 5 and 7)."""

    def test_oracle_imports_only_stdlib_and_itself(self) -> None:
        root = _root()
        self.assertTrue((root / "oracle").is_dir())
        self.assertEqual(oracle_import_violations(root), [])

    def test_oracle_never_imports_generator_reader_or_self_checks(self) -> None:
        root = _root()
        banned = {"modread", "varvalues", "screen", "test_d4b_review_round4", "test_d4b_review_round5",
                  "realworld", "generator"}
        known = _module_names(root)
        self.assertEqual(sorted(banned - known), [], "every banned name must be a known module name")
        hits = [v for v in oracle_import_violations(root) if any(f"imports {b} " in v for b in banned)]
        self.assertEqual(hits, [])

    def test_only_oracle_and_tools_write_ground_truth(self) -> None:
        self.assertEqual(ground_truth_write_violations(_root()), [])

    def test_committed_scenarios_carry_no_ground_truth(self) -> None:
        self.assertEqual(committed_ground_truth_violations(_root()), [])


class TestOracleIndependenceCanFail(unittest.TestCase):
    """Self-test on synthetic trees: each D5-03 checker catches what it must."""

    def _tree(self, files: dict[str, str]) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="tp-indep-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel, text in files.items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_text(text, encoding="utf-8")
        return tmp

    def test_catches_generator_import_in_oracle(self) -> None:
        root = self._tree({"oracle/a.py": "from realworld import modread\n", "generator/realworld/modread.py": ""})
        self.assertEqual(len(oracle_import_violations(root)), 1)

    def test_catches_third_party_and_sys_path(self) -> None:
        root = self._tree({"oracle/a.py": "import requests\nimport sys\nsys.path.insert(0, 'x')\n"})
        self.assertEqual(len(oracle_import_violations(root)), 2)

    def test_allows_stdlib_and_oracle(self) -> None:
        root = self._tree({"oracle/a.py": "import json\nfrom oracle import inputs\nfrom . import record\n"})
        self.assertEqual(oracle_import_violations(root), [])

    def test_catches_ground_truth_write_outside_oracle(self) -> None:
        root = self._tree({"generator/g.py": "d = {'labels': [1]}\nd['gt_class'] = 'safe'\nd.update(oracle={})\n",
                           "oracle/o.py": "d = {'labels': [1]}\n", "tools/t.py": "d = {'oracle': {}}\n",
                           "generator/ok.py": "d = {'labels': None, 'gt_class': None}\n"})
        self.assertEqual(len(ground_truth_write_violations(root)), 3)


if __name__ == "__main__":
    unittest.main()
