"""D5b Step 1 (D5-12): the registry 6.1 endpoint binding is written by the generator; step files are unchanged.

Registry v1.0 section 6.1: "Each scenario binds two endpoints by full instance address: the source S, an
``aws_instance``; the destination D, an ``aws_db_instance``." D5-12: every ``scenario.json`` carries
``endpoints: {"S": ..., "D": ...}`` written by the generator from what it built (controlled templates: the
application instance and the main database; grafts: ``aws_instance.tp_app`` and ``aws_db_instance.tp_db``). The
step files must be byte-identical to ``872b194`` (``origin/main`` before D5b). Test-split ids are never printed.
Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "generator"))
DEV = REPO_ROOT / "scenarios" / "dev"
# Digest of every file under scenarios/dev/*/step_*/ at 872b194 (3044 files), and of the withheld test split's
# step files before D5b (1354 files); computed as in step_digest() below.
DEV_STEPS_872B194 = (3044, "4694b5d302caabddecdfe12d624d7d4bf83c5428e31f38c264ac189dbdb4a085")
TEST_STEPS_872B194 = (1354, "c4eee35c8efdc6144551fbb841fce843202cd2628c2ef58edaa10cda0a7e1b18")
_RES = re.compile(r'^\s*resource\s+"(aws_instance|aws_db_instance)"\s+"([^"]+)"\s*\{', re.M)


def step_digest(root: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    n = 0
    for p in sorted(root.glob("tp-v1-*/step_*/**/*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
            n += 1
    return n, h.hexdigest()


def private_root() -> Path | None:
    priv = os.environ.get("TERRAPRESERVE_PRIVATE")
    return Path(priv) if priv and Path(priv).is_dir() else None


def scenario_dirs() -> list[tuple[str, Path]]:
    out = [("dev", p) for p in sorted(DEV.glob("tp-v1-*")) if (p / "scenario.json").is_file()]
    priv = private_root()
    if priv is not None:
        out += [("test", p) for p in sorted(priv.glob("tp-v1-*")) if (p / "scenario.json").is_file()]
    return out


class TestEndpointBinding(unittest.TestCase):
    def test_every_scenario_binds_S_and_D_declared_in_step_0(self) -> None:
        bad: list[str] = []
        n = 0
        for split, p in scenario_dirs():
            d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
            shown = d["scenario_id"] if split == "dev" else "<test-split scenario>"
            ep = d.get("endpoints")
            if not isinstance(ep, dict) or set(ep) != {"S", "D"}:
                bad.append(f"{shown}: no endpoints {{S, D}}")
                continue
            text = "\n".join(f.read_text(encoding="utf-8") for f in sorted((p / "step_0").glob("*.tf")))
            declared = {f"{t}.{n}" for t, n in _RES.findall(text)}
            if not ep["S"].startswith("aws_instance.") or ep["S"] not in declared:
                bad.append(f"{shown}: S {ep['S']} is not an aws_instance declared in step 0")
            if not ep["D"].startswith("aws_db_instance.") or ep["D"] not in declared:
                bad.append(f"{shown}: D {ep['D']} is not an aws_db_instance declared in step 0")
            n += 1
        self.assertGreater(n, 0)
        self.assertEqual(bad, [], f"{len(bad)} problems, first 10: {bad[:10]}")

    def test_binding_comes_from_what_the_generator_built(self) -> None:
        import templates  # noqa: E402  (generator/templates)
        bad = []
        for split, p in scenario_dirs():
            d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
            shown = d["scenario_id"] if split == "dev" else "<test-split scenario>"
            if d["source"]["tier"] == "controlled":
                want = templates.TEMPLATES[d["template_id"]].endpoints()
            else:
                want = {"S": "aws_instance.tp_app", "D": "aws_db_instance.tp_db"}
            if d.get("endpoints") != want:
                bad.append(f"{shown}: {d.get('endpoints')} != {want}")
        self.assertEqual(bad, [], f"{len(bad)} problems, first 10: {bad[:10]}")

    def test_step_files_byte_identical_to_872b194(self) -> None:
        self.assertEqual(step_digest(DEV), DEV_STEPS_872B194)
        priv = private_root()
        if priv is None:
            self.skipTest("TERRAPRESERVE_PRIVATE not set: the withheld test split is not checked")
        self.assertEqual(step_digest(priv), TEST_STEPS_872B194, "withheld step files changed (ids withheld)")

    def test_generator_versions(self) -> None:
        import VERSION  # noqa: E402
        from realworld import generate_rw  # noqa: E402
        self.assertEqual(VERSION.VERSION, "d4a-8")
        self.assertEqual(generate_rw.GENERATOR_VERSION, "d4b-9")


if __name__ == "__main__":
    unittest.main()
