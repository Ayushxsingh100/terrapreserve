"""The released test split (R2-01): checks shared by the tests that used to assert the split was withheld.

Not a test module (no ``test_`` prefix). Every check works on the committed files only; the integrity guard is the
frozen pin of ``V1_MANIFEST_PRIVATE.json`` in ``scenarios/V1_MANIFEST.sha256`` (D6-04). Messages give counts, not ids.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = REPO_ROOT / "scenarios"
TEST_SPLIT = SCENARIOS / "test"
PRIVATE_MANIFEST = TEST_SPLIT / "V1_MANIFEST_PRIVATE.json"
# The DAIL main run's test generation (TP-L2); its candidates are released under llm_candidates/test/ (R2-02).
MAIN_RUN_GENERATION = "40e2052b-b489-552d-8c27-88785414a4b1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(directory: Path) -> str:
    """D4-09: SHA-256 of the path-sorted lines ``"<relative POSIX path>:<sha256 of the bytes>"``."""
    files = sorted((p.relative_to(directory).as_posix(), p) for p in directory.rglob("*") if p.is_file())
    return sha256("\n".join(f"{rel}:{sha256(p.read_bytes())}" for rel, p in files).encode("utf-8"))


def pinned_private_manifest_sha256() -> str:
    for line in (SCENARIOS / "V1_MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if name == "V1_MANIFEST_PRIVATE.json":
            return digest
    raise AssertionError("V1_MANIFEST.sha256 has no V1_MANIFEST_PRIVATE.json line")


def committed_split_problems() -> list[str]:
    """Every way the committed test split differs from the pinned manifest; empty when it equals it."""
    if not PRIVATE_MANIFEST.is_file():
        return ["scenarios/test/V1_MANIFEST_PRIVATE.json is missing"]
    raw = PRIVATE_MANIFEST.read_bytes()
    problems = []
    if sha256(raw) != pinned_private_manifest_sha256():
        problems.append("V1_MANIFEST_PRIVATE.json does not have the pinned sha256")
    entries = json.loads(raw)["test"]
    ids = {e["scenario_id"] for e in entries}
    folders = {d.name for d in TEST_SPLIT.iterdir() if d.is_dir() and d.name != "__pycache__"}
    if folders != ids:
        problems.append(f"{len(folders - ids)} extra and {len(ids - folders)} missing scenario folders")
    bad_json = bad_steps = extra_steps = 0
    for e in entries:
        d = TEST_SPLIT / e["scenario_id"]
        if not d.is_dir():
            continue
        sj = d / "scenario.json"
        bad_json += not sj.is_file() or sha256(sj.read_bytes()) != e["scenario_json_sha256"]
        want = {f"step_{s['step']}": s["content_hash"] for s in e["steps"]}
        have = {s.name for s in d.iterdir() if s.is_dir() and s.name.startswith("step_")}
        extra_steps += len(have - set(want))
        bad_steps += sum(name not in have or content_hash(d / name) != h for name, h in want.items())
    if bad_json:
        problems.append(f"{bad_json} scenario.json files differ from the manifest")
    if bad_steps:
        problems.append(f"{bad_steps} step folders missing or differing from the manifest")
    if extra_steps:
        problems.append(f"{extra_steps} step folders not in the manifest")
    return problems


def released_id_directory(path: Path, ids: set[str]) -> bool:
    """True when ``path`` (a directory named after a test id) is where R2 releases it: ``scenarios/test/<id>`` or a
    candidate folder ``llm_candidates/test/<main-run generation>/<model>/<id>``."""
    rel = path.relative_to(REPO_ROOT).parts
    if path.name not in ids:
        return False
    return rel[:2] == ("scenarios", "test") and len(rel) == 3 or (
        rel[:3] == ("llm_candidates", "test", MAIN_RUN_GENERATION) and len(rel) == 5)


def scenarios_sha256_without_test_split() -> str:
    """``tools/label_llm.scenarios_sha256`` over ``scenarios/`` with ``scenarios/test/`` left out: the v1.0 tree."""
    files = sorted((p.relative_to(SCENARIOS).as_posix(), p) for p in SCENARIOS.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts and p.relative_to(SCENARIOS).parts[0] != "test")
    return sha256("\n".join(f"{rel}:{sha256(p.read_bytes())}" for rel, p in files).encode("utf-8"))
