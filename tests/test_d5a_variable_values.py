"""D5a Step 2 (D5-01): variable values in the scenario record. Written before the code (test-first).

Every test runs over all of ``scenarios/dev/`` and, when ``TERRAPRESERVE_PRIVATE`` names an existing
directory, over the withheld test split too (skipped with a printed reason otherwise).

Rules:
1. Every scenario records ``variable_values`` (an object) and ``variable_values_rule == "vv-1"``, plus
   ``variable_values_unresolved`` (an object, possibly empty).
2. Every variable declared without a ``default`` (in any step) has exactly one entry, in ``variable_values``
   or in ``variable_values_unresolved`` (with a non-empty reason); no variable with a default is listed.
3. Values follow rule vv-1. Expected values below were worked out by hand from the step files.
4. Every step-directory hash is unchanged since the D4b merge (``5fc927e``): only ``scenario.json`` changes.
5. The test split is written only to ``$TERRAPRESERVE_PRIVATE``: no manifest id has a directory in the repo.
6. Generator versions are ``d4a-5`` (controlled) and ``d4b-6`` (real-world).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

from realworld import modread  # noqa: E402

PH = "tp-placeholder"

# Digest of every (scenario_id, step, content_hash) of the dev scenario records and of
# scenarios/test_manifest.json, measured at the D4b merge commit 5fc927e (935 steps).
STEP_HASH_DIGEST_5FC927E = "d55acbf7cde2f8eba90060a9cbc8616b02d3610f56694d6aeb0cb4d91e2a4284"
STEP_COUNT_5FC927E = 935

# Worked out by hand from the step files (rule vv-1). Unresolved: names only (the reason wording is free).
EXPECTED: dict[str, tuple[dict, set[str]]] = {
    # Controlled: every template declares only db_password (type string, sensitive, validation
    # length(var.db_password) > 0, which "tp-placeholder" satisfies).
    "tp-v1-F1-0001": ({"db_password": PH}, set()),
    "tp-v1-F2-0028": ({"db_password": PH}, set()),
    "tp-v1-F3-0064": ({"db_password": PH}, set()),
    "tp-v1-F6-0144": ({"db_password": PH}, set()),
    "tp-v1-F8-0203": ({"db_password": PH}, set()),
    # Real-world.
    # string, list(string), sensitive string, number, bool:
    "tp-v1-F3-0274": ({"tp_db_password": PH, "resource_prefix": PH, "subnet_ids": [], "db_password": PH,
                       "instance_class": PH, "allocated_storage": 1, "multi_az": False}, set()),
    # untyped (as string), map(any), list(string):
    "tp-v1-F7-0369": ({"tp_db_password": PH, "region": PH, "aws_account_id": PH, "env": PH,
                       "default_tags": {}, "name": PH, "cidr_blocks": PH,
                       "private_subnet_cidr_blocks": []}, set()),
    # map(string), list(object(...)):
    "tp-v1-F5-0330": ({"tp_db_password": PH, "cidr_block": PH, "region": PH, "vpc_name": PH,
                       "tags": {}, "subnets": []}, set()),
    # number:
    "tp-v1-F5-0323": ({"tp_db_password": PH, "namespace": PH, "vpc_id": PH,
                       "private_subnets_cidr_blocks": [], "app_port": 1}, set()),
    # object with required attributes -> unresolved; map(object) with an alltrue validation -> {} accepted:
    "tp-v1-F8-0397": ({"tp_db_password": PH, "subnet_config": {}}, {"vpc_config"}),
    # a validation (contains(["tst","dev","acc","prd"], var.env)) rejects the placeholder -> unresolved:
    "tp-v1-F8-0405": ({"tp_db_password": PH, "name": PH}, {"env"}),
}


def roots() -> list[tuple[str, Path]]:
    out = [("dev", REPO_ROOT / "scenarios" / "dev")]
    env = os.environ.get("TERRAPRESERVE_PRIVATE")
    if env and Path(env).is_dir():
        out.append(("test", Path(env)))
    else:
        print("\n[d5a] TERRAPRESERVE_PRIVATE is not set to an existing directory: test-split checks skipped.",
              file=sys.stderr)
    return out


def scenarios() -> list[tuple[str, Path, dict]]:
    out = []
    for split, root in roots():
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append((split, p, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


def declared(p: Path) -> tuple[set[str], set[str]]:
    """(variables without a default, variables with a default) over every step."""
    no_default: set[str] = set()
    with_default: set[str] = set()
    for sd in sorted(x for x in p.glob("step_*") if x.is_dir()):
        mod = modread.read_module({f.name: f.read_text(encoding="utf-8") for f in sd.glob("*.tf")})
        for name, blk in mod.variables.items():
            (with_default if "default" in blk.attrs else no_default).add(name)
    return no_default, with_default


class TestVariableValues(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scs = scenarios()

    def test_01_fields_present(self) -> None:
        bad = [d["scenario_id"] for _s, _p, d in self.scs
               if not isinstance(d.get("variable_values"), dict)
               or d.get("variable_values_rule") != "vv-1"
               or not isinstance(d.get("variable_values_unresolved"), dict)]
        self.assertGreater(len(self.scs), 0)
        self.assertEqual(bad, [], f"{len(bad)} scenarios without vv-1 variable values: {bad[:10]}")

    def test_02_every_variable_without_default_has_one_entry(self) -> None:
        bad = []
        for _s, p, d in self.scs:
            vv = d.get("variable_values") or {}
            un = d.get("variable_values_unresolved") or {}
            no_default, with_default = declared(p)
            listed = set(vv) | set(un)
            if set(vv) & set(un):
                bad.append(f"{d['scenario_id']}: listed twice {sorted(set(vv) & set(un))}")
            if listed != no_default:
                bad.append(f"{d['scenario_id']}: listed {sorted(listed)} but no-default {sorted(no_default)}")
            if listed & (with_default - no_default):
                bad.append(f"{d['scenario_id']}: lists variables with a default {sorted(listed & with_default)}")
            empty = [k for k, v in un.items() if not str(v).strip()]
            if empty:
                bad.append(f"{d['scenario_id']}: unresolved without a reason {empty}")
        self.assertEqual(bad, [], f"{len(bad)} problems, first 10: {bad[:10]}")

    def test_03_values_follow_vv1_hand_worked(self) -> None:
        by_id = {d["scenario_id"]: d for _s, _p, d in self.scs}
        for sid, (values, unresolved) in EXPECTED.items():
            with self.subTest(scenario=sid):
                self.assertIn(sid, by_id)
                d = by_id[sid]
                self.assertEqual(d.get("variable_values"), values)
                self.assertEqual(set((d.get("variable_values_unresolved") or {}).keys()), unresolved)

    def test_04_step_hashes_unchanged_since_d4b(self) -> None:
        rows = []
        for p in sorted((REPO_ROOT / "scenarios" / "dev").glob("tp-v1-*")):
            d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
            rows += [f"{d['scenario_id']}|{s['step']}|{s['content_hash']}" for s in d["steps"]]
        manifest = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
        rows += [f"{e['scenario_id']}|{s['step']}|{s['content_hash']}" for e in manifest for s in e["steps"]]
        self.assertEqual(len(rows), STEP_COUNT_5FC927E)
        self.assertEqual(hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest(), STEP_HASH_DIGEST_5FC927E)

    def test_05_recorded_step_hashes_match_files(self) -> None:
        import writer  # noqa: PLC0415

        bad = []
        for _s, p, d in self.scs:
            for s in d["steps"]:
                sd = p / f"step_{s['step']}"
                files = {f.name: f.read_text(encoding="utf-8") for f in sorted(sd.iterdir()) if f.is_file()}
                if writer.compute_step_content_hash(files) != s["content_hash"]:
                    bad.append(f"{d['scenario_id']}/step_{s['step']}")
        self.assertEqual(bad, [], f"step hash mismatches: {bad[:10]}")

    def test_06_test_split_never_in_repository(self) -> None:
        manifest = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
        ids = {e["scenario_id"] for e in manifest}
        skip = {".git", ".venv", ".venv-tools", "__pycache__", ".terraform", "node_modules"}
        seen: set[str] = set()
        for dirpath, dirnames, _files in os.walk(REPO_ROOT):
            dirnames[:] = [x for x in dirnames if x not in skip]
            seen.update(x for x in dirnames if x in ids)
        in_repo = sorted(seen)
        self.assertEqual(in_repo, [])
        for split, _p, d in self.scs:
            self.assertEqual(split == "test", d["scenario_id"] in ids, d["scenario_id"])

    def test_08_recorded_values_and_reasons_match_a_recomputation(self) -> None:
        # The stored record (values and the reason wording of every unresolved variable) must be what rule
        # vv-1 gives now: a record left over from an earlier rule version fails here.
        import varvalues  # noqa: PLC0415

        bad = []
        for _s, p, d in self.scs:
            steps = [{f.name: f.read_text(encoding="utf-8") for f in (p / f"step_{s['step']}").glob("*.tf")}
                     for s in d["steps"]]
            values, unresolved = varvalues.compute(steps)
            if d.get("variable_values") != values or d.get("variable_values_unresolved") != unresolved:
                bad.append(d["scenario_id"])
        self.assertEqual(bad, [], f"{len(bad)} scenario records differ from a vv-1 recomputation: {bad[:10]}")

    def test_07_generator_versions(self) -> None:
        bad = [d["scenario_id"] for _s, _p, d in self.scs
               if d["generator_version"] != {"controlled": "d4a-5", "real_world": "d4b-6"}[d["source"]["tier"]]]
        self.assertEqual(bad, [], f"{len(bad)} scenarios with an old generator version: {bad[:5]}")


if __name__ == "__main__":
    unittest.main()
