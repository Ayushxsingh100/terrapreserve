"""D0 gate 1 / DAIL ADR-010 / ADR-013: nothing here may import or depend on DAIL.

Walks every ``*.py`` file with ``ast`` (nothing is imported or executed) and
every dependency file, and fails on any DAIL reference. A self-test feeds in
synthetic sources, so a checker that can no longer fail is itself caught.
"""

from __future__ import annotations

import ast
import os
import re
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


if __name__ == "__main__":
    unittest.main()
