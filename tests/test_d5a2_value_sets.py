"""D5a-2 (D5-07 value rule vv-2, D5-08 data-source variables). Written before the code (test-first).

Every test runs over all of ``scenarios/dev/`` and, when ``TERRAPRESERVE_PRIVATE`` names an existing
directory, over the withheld test split too (skipped with a printed reason otherwise).

(a) Every variable declared without a default (in any step), ``tp_ds_*`` variables included, has a value in
    both sets (``variable_values`` and ``variable_values_alt``) and a ``variable_values_kinds`` entry, or is
    listed in ``variable_values_unresolved`` as ``unresolved`` or ``conflict`` with a reason.
(b) The two sets differ for every variable, except where the record states one of the recorded exceptions.
(c) Values follow vv-2 for 5 controlled and 10 real-world scenarios worked out by hand from the step files.
(d) No ``data`` block (and no ``data.<type>.<name>`` reference) remains in any step of any scenario.
(e) Every ``host_transform`` entry of kind ``data_source_to_variable`` matches, by sha256, a ``data`` block of
    the scenario's pool module, every such block has an entry, and its variable is declared without a default
    in ``terrapreserve_data_variables.tf`` of every step.
(f) Controlled step files are byte-identical to ``e96c017`` (only ``scenario.json`` changes there).
(g) The test split is written only to ``$TERRAPRESERVE_PRIVATE``.
Plus: the stored record equals a fresh computation, recorded step hashes match the files, and the
generator versions are current.

D5a-3 (D5-10): vv-3 keeps vv-2 whole and adds rejected-default overrides and backup candidates. These tests
therefore read the current rule: a variable whose declared default was overridden (its kinds entry has a
``reason``) is valued like one without a default; the hand-worked values of (c) are checked where the recorded
candidate index is 0 (the vv-2 value); the recomputation passes the recorded vv-3 search result; the versions are
those of ``tests/test_d5a3_vv3.py``. The vv-3 additions themselves are tested there.
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
sys.path.insert(0, str(REPO_ROOT / "sources"))
sys.path.insert(0, str(REPO_ROOT / "generator"))

import hcl_lex  # noqa: E402
from realworld import modread  # noqa: E402

RECORD_FIELDS = ("variable_values", "variable_values_alt", "variable_values_rule", "variable_values_kinds",
                 "variable_values_unresolved")
CURRENT_RULE = "vv-3"  # D5-10 (D5a-3); vv-2 (D5-07) is kept whole inside it
SAME_IN_BOTH_REASONS = {"kind region: the provider pin us-east-1 in both sets",
                        "object with no attributes used",
                        "the validation admits only one candidate"}

# D5-07 table: (primary, alternate) by kind.
K = {
    "ipv4_cidr": ("10.201.0.0/16", "192.168.77.0/24"),
    "vpc_id": ("vpc-0201201201201201a", "vpc-0777777777777777b"),
    "subnet_id": ("subnet-0201201201201201a", "subnet-0777777777777777b"),
    "sg_id": ("sg-0201201201201201a", "sg-0777777777777777b"),
    "ami": ("ami-0201201201201201a", "ami-0777777777777777b"),
    "az": ("us-east-1a", "us-east-1b"),
    "instance_type": ("t3.micro", "t3.small"),
    "key_name": ("tp-key-primary", "tp-key-alt"),
    "string": ("tp-primary", "tp-alt"),
    "secret": ("tp-secret-primary", "tp-secret-alt"),
}
SECRET = K["secret"]


def P(kind: str) -> str:
    return K[kind][0]


def A(kind: str) -> str:
    return K[kind][1]


# Controlled: every template declares only db_password (type string, sensitive, validation
# length(var.db_password) > 0, which both secret values satisfy).
CONTROLLED_EXPECTED = {sid: {"db_password": SECRET}
                       for sid in ("tp-v1-F1-0001", "tp-v1-F2-0028", "tp-v1-F3-0064", "tp-v1-F6-0144",
                                   "tp-v1-F8-0203")}

# Real-world, worked out by hand from the step files. Each entry maps a variable to (primary, alternate).
# "complete" scenarios list every valued variable; the others list the variables checked.
# A collection that the configuration indexes (directly, through tolist(...)[i] or element(...)) is not
# empty-able and gets 3 elements in both sets; an empty-able one is [] / {} (primary) and one element (alternate).
RW_EXPECTED: dict[str, tuple[bool, dict[str, tuple]]] = {
    # aws_key_pair; untyped variables reaching ami, instance_type, vpc_id, subnet_id, security_groups (sg ids).
    "tp-v1-F7-0388": (True, {
        "tp_db_password": SECRET,
        "ami_id": K["ami"], "instance_type": K["instance_type"], "vpc_id": K["vpc_id"],
        "subnet_id": K["subnet_id"], "controller_sg_id": K["sg_id"],
        "tp_ds_aws_key_pair_ansible_controller_key_pair": ({"key_name": P("key_name")}, {"key_name": A("key_name")}),
    }),
    # aws_instance (outputs only: string) and aws_security_group (id -> security_group_id: sg_id).
    "tp-v1-F7-0367": (True, {
        "tp_db_password": SECRET,
        "tp_ds_aws_security_group_selected": ({"id": P("sg_id")}, {"id": A("sg_id")}),
        "tp_ds_aws_instance_node_vm": ({"public_ip": P("string")}, {"public_ip": A("string")}),
        "tp_ds_aws_instance_bigip": ({"private_ip": P("string"), "public_ip": P("string")},
                                     {"private_ip": A("string"), "public_ip": A("string")}),
    }),
    # aws_ip_ranges: cidr_blocks passed whole (empty-able list of ipv4_cidr); create_date, sync_token in tags.
    "tp-v1-F1-0213": (True, {
        "tp_db_password": SECRET,
        "tp_ds_aws_ip_ranges_ap_northeast": (
            {"cidr_blocks": [], "create_date": P("string"), "sync_token": P("string")},
            {"cidr_blocks": [A("ipv4_cidr")], "create_date": A("string"), "sync_token": A("string")}),
    }),
    # aws_availability_zones (names indexed through tolist(...)[each.value]) and an unreferenced aws_region.
    "tp-v1-F1-0210": (True, {
        "tp_db_password": SECRET,
        "tp_ds_aws_availability_zones_available": ({"names": [P("az")] * 3}, {"names": [A("az")] * 3}),
        "tp_ds_aws_region_current": ({}, {}),
    }),
    # aws_vpc (id -> vpc_id; cidr_block) and aws_subnets (ids passed whole: empty-able list of subnet ids).
    "tp-v1-F7-0379": (False, {
        "db_password": SECRET,
        "environment": K["string"],
        "tp_ds_aws_vpc_default": ({"cidr_block": P("ipv4_cidr"), "id": P("vpc_id")},
                                  {"cidr_block": A("ipv4_cidr"), "id": A("vpc_id")}),
        "tp_ds_aws_subnets_available": ({"ids": []}, {"ids": [A("subnet_id")]}),
    }),
    # terraform_remote_state: outputs.public_ip_addr only inside a template "${...}/32" -> string.
    "tp-v1-F6-0342": (False, {
        "tp_ds_terraform_remote_state_eip": ({"outputs": {"public_ip_addr": P("string")}},
                                             {"outputs": {"public_ip_addr": A("string")}}),
    }),
    # aws_ami: id -> ami ("${...}" with no literal text is a direct use).
    "tp-v1-F1-0227": (False, {
        "tp_ds_aws_ami_ubuntu": ({"id": P("ami")}, {"id": A("ami")}),
    }),
    # object with required attributes; map(object) used through for_each/each.value (empty-able map).
    "tp-v1-F1-0225": (True, {
        "tp_db_password": SECRET,
        "vpc_config": ({"cidr_block": P("ipv4_cidr"), "name": P("string")},
                       {"cidr_block": A("ipv4_cidr"), "name": A("string")}),
        "subnet_config": ({}, {A("string"): {"az": A("az"), "cidr_block": A("ipv4_cidr")}}),
    }),
    # validation contains(["tst","dev","acc","prd"], var.env): primary takes candidate 1 ("tst"), the
    # alternate the first accepted candidate that differs from the primary ("dev"); names via element(...).
    "tp-v1-F8-0405": (True, {
        "tp_db_password": SECRET,
        "name": K["string"],
        "env": ("tst", "dev"),
        "tp_ds_aws_availability_zones_available": ({"names": [P("az")] * 3}, {"names": [A("az")] * 3}),
    }),
    # aws_db_instance: db_parameter_groups[0] (indexed list of string).
    "tp-v1-F1-0214": (False, {
        "tp_ds_aws_db_instance_master": ({"db_parameter_groups": [P("string")] * 3},
                                         {"db_parameter_groups": [A("string")] * 3}),
    }),
}
KIND_EXPECTED = {
    ("tp-v1-F7-0388", "controller_sg_id"): "sg_id",
    ("tp-v1-F7-0388", "ami_id"): "ami",
    ("tp-v1-F7-0388", "tp_db_password"): "secret",
    ("tp-v1-F8-0405", "env"): "string",
    ("tp-v1-F1-0225", "vpc_config"): {"object": {"cidr_block": "ipv4_cidr", "name": "string"}},
}

# Digests of the controlled tier at e96c017 (only scenario.json may change there).
# Dev: every file under each controlled scenario directory except scenario.json, as "<relpath>|<sha256>".
CONTROLLED_DEV_FILES = 984
CONTROLLED_DEV_DIGEST_E96C017 = "db8526865230008f8aa84fb46c7bc22d7390a0ac23f73f3d1cc0ecc787597a7d"
# Test: the controlled entries of scenarios/test_manifest.json as "<id>|<step>|<content_hash>", sorted.
CONTROLLED_TEST_STEPS = 138
CONTROLLED_TEST_DIGEST_E96C017 = "47d59e577c31a69e08a0ec3573eebc8d881683325528dd978d04fb3277e1c820"
# Test, when the private split is present: the same file digest as for dev.
CONTROLLED_PRIVATE_FILES = 414
CONTROLLED_PRIVATE_DIGEST_E96C017 = "ad5380013b3ed78cf69d1165dd89fe4740723bcad23edb8800d82fe37041f233"


def private_root() -> Path | None:
    env = os.environ.get("TERRAPRESERVE_PRIVATE")
    if env and Path(env).is_dir():
        return Path(env)
    print("\n[d5a2] TERRAPRESERVE_PRIVATE is not set to an existing directory: test-split checks skipped.",
          file=sys.stderr)
    return None


def scenarios() -> list[tuple[str, Path, dict]]:
    out = []
    roots = [("dev", REPO_ROOT / "scenarios" / "dev")]
    priv = private_root()
    if priv is not None:
        roots.append(("test", priv))
    for split, root in roots:
        for p in sorted(root.glob("tp-v1-*")):
            if (p / "scenario.json").is_file():
                out.append((split, p, json.loads((p / "scenario.json").read_text(encoding="utf-8"))))
    return out


def shown(split: str, sid: str) -> str:
    """Test-split ids never appear in a message (they are reported as counts only)."""
    return sid if split == "dev" else "<test-split scenario>"


def step_dirs(p: Path) -> list[Path]:
    return sorted((x for x in p.glob("step_*") if x.is_dir()), key=lambda x: int(x.name.split("_")[1]))


def no_default_variables(p: Path) -> set[str]:
    out: set[str] = set()
    for sd in step_dirs(p):
        mod = modread.read_module({f.name: f.read_text(encoding="utf-8") for f in sd.glob("*.tf")})
        out |= {n for n, b in mod.variables.items() if "default" not in b.attrs}
    return out


def data_blocks(text: str) -> list[tuple[str, str, str]]:
    """(type, name, exact block text) of every top-level ``data`` block (independent of the generator)."""
    spans = [s for s in hcl_lex.tokenize_spans(text) if s[0].kind != "NEWLINE"]
    out = []
    depth = 0
    i = 0
    while i < len(spans):
        tok, start, _e = spans[i]
        if tok.kind == "PUNCT" and tok.text == "{":
            depth += 1
        elif tok.kind == "PUNCT" and tok.text == "}":
            depth -= 1
        elif depth == 0 and tok.kind == "IDENT" and tok.text == "data" and i + 3 < len(spans) \
                and spans[i + 1][0].kind == "STRING" and spans[i + 2][0].kind == "STRING" \
                and spans[i + 3][0].kind == "PUNCT" and spans[i + 3][0].text == "{":
            level = 0
            for k in range(i + 3, len(spans)):
                t = spans[k][0]
                if t.kind == "PUNCT" and t.text == "{":
                    level += 1
                elif t.kind == "PUNCT" and t.text == "}":
                    level -= 1
                    if level == 0:
                        out.append((spans[i + 1][0].text, spans[i + 2][0].text, text[start:spans[k][2]]))
                        i = k
                        break
        i += 1
    return out


def file_digest(root: Path, tier: str) -> tuple[int, str]:
    rows = []
    for p in sorted(root.glob("tp-v1-*")):
        d = json.loads((p / "scenario.json").read_text(encoding="utf-8"))
        if d["source"]["tier"] != tier:
            continue
        for f in sorted(x for x in p.rglob("*") if x.is_file() and x.name != "scenario.json"):
            rows.append(f"{f.relative_to(p.parent).as_posix()}|{hashlib.sha256(f.read_bytes()).hexdigest()}")
    return len(rows), hashlib.sha256("\n".join(rows).encode()).hexdigest()


class TestValueSets(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scs = scenarios()
        cls.by_id = {d["scenario_id"]: (p, d) for _s, p, d in cls.scs}

    def test_a_every_variable_has_both_values_or_a_reason(self) -> None:
        bad = []
        for split, p, d in self.scs:
            sid = shown(split, d["scenario_id"])
            if d.get("variable_values_rule") != CURRENT_RULE or any(not isinstance(d.get(f), dict)
                                                                     for f in RECORD_FIELDS
                                                                     if f != "variable_values_rule"):
                bad.append(f"{sid}: no {CURRENT_RULE} record")
                continue
            pri, alt, kinds, un = (d["variable_values"], d["variable_values_alt"], d["variable_values_kinds"],
                                   d["variable_values_unresolved"])
            need = no_default_variables(p) | {n for n, e in kinds.items() if "reason" in e}
            if set(pri) != set(alt):
                bad.append(f"{sid}: the two sets cover different variables")
            if set(pri) & set(un):
                bad.append(f"{sid}: valued and unresolved {sorted(set(pri) & set(un))}")
            if set(pri) | set(un) != need:
                bad.append(f"{sid}: listed {sorted(set(pri) | set(un))} but no-default {sorted(need)}")
            if set(kinds) != set(pri):
                bad.append(f"{sid}: kinds recorded for {sorted(kinds)} but valued {sorted(pri)}")
            for name, entry in un.items():
                if not isinstance(entry, dict) or entry.get("status") not in ("unresolved", "conflict") \
                        or not str(entry.get("reason", "")).strip():
                    bad.append(f"{sid}: {name} unresolved without a status and reason")
            for name, entry in kinds.items():
                if not entry.get("kind") or not entry.get("evidence"):
                    bad.append(f"{sid}: {name} has no kind or no evidence")
        self.assertGreater(len(self.scs), 0)
        self.assertEqual(bad, [], f"{len(bad)} problems, first 10: {bad[:10]}")

    def test_b_the_two_sets_differ_except_where_recorded(self) -> None:
        bad = []
        for split, _p, d in self.scs:
            sid = shown(split, d["scenario_id"])
            alt = d.get("variable_values_alt")
            if not isinstance(alt, dict):
                bad.append(f"{sid}: no alternate set")
                continue
            for name, value in (d.get("variable_values") or {}).items():
                same = (d.get("variable_values_kinds") or {}).get(name, {}).get("same_in_both_sets")
                if name not in alt:
                    bad.append(f"{sid}: {name} has no alternate value")
                elif value == alt[name] and same not in SAME_IN_BOTH_REASONS:
                    bad.append(f"{sid}: {name}")
                elif value != alt[name] and same is not None:
                    bad.append(f"{sid}: {name} records same_in_both_sets but the values differ")
        self.assertEqual(bad, [], f"{len(bad)} variables with equal values in both sets: {bad[:10]}")

    def test_c_values_follow_vv2_hand_worked(self) -> None:
        cases = {sid: (True, {n: v for n, v in exp.items()}) for sid, exp in CONTROLLED_EXPECTED.items()}
        cases.update(RW_EXPECTED)
        self.assertEqual(len(CONTROLLED_EXPECTED), 5)
        self.assertGreaterEqual(len(RW_EXPECTED), 10)
        for sid, (complete, exp) in cases.items():
            with self.subTest(scenario=sid):
                self.assertIn(sid, self.by_id)
                d = self.by_id[sid][1]
                pri = d.get("variable_values") or {}
                alt = d.get("variable_values_alt") or {}
                cand = d.get("variable_values_candidates") or {}
                for name, (want_p, want_a) in exp.items():
                    if (cand.get("primary") or {}).get(name, 0) == 0:
                        self.assertEqual(pri.get(name), want_p, f"{sid} primary {name}")
                    if (cand.get("alternate") or {}).get(name, 0) == 0:
                        self.assertEqual(alt.get(name), want_a, f"{sid} alternate {name}")
                if complete:
                    self.assertEqual(set(pri), set(exp), f"{sid}: valued variables")
                    self.assertEqual(d.get("variable_values_unresolved"), {}, f"{sid}: unresolved")
        for (sid, name), kind in KIND_EXPECTED.items():
            with self.subTest(kind=f"{sid}:{name}"):
                d = self.by_id[sid][1]
                self.assertEqual((d.get("variable_values_kinds") or {}).get(name, {}).get("kind"), kind)
        # the validation case records which candidate was taken in each set
        env = (self.by_id["tp-v1-F8-0405"][1].get("variable_values_kinds") or {}).get("env", {})
        self.assertEqual(env.get("validation"), {"primary": "tst", "alternate": "dev"})

    def test_d_no_data_block_or_reference_in_any_step(self) -> None:
        bad = []
        for split, p, d in self.scs:
            sid = shown(split, d["scenario_id"])
            for sd in step_dirs(p):
                for f in sorted(sd.glob("*.tf")):
                    text = f.read_text(encoding="utf-8")
                    if data_blocks(text):
                        bad.append(f"{sid}/{sd.name}/{f.name}: data block")
                    # comments are not configuration and stay verbatim; strings and heredocs are checked
                    spans = [s for s in hcl_lex.tokenize_spans(text) if s[0].kind != "NEWLINE"]
                    toks = [s[0] for s in spans]
                    in_strings = any(re.search(r"(?<![\w.\-])data\.[A-Za-z_]", text[a:b])
                                     for t, a, b in spans if t.kind in ("STRING", "HEREDOC"))
                    if any(t.kind == "IDENT" and t.text == "data" and k + 1 < len(toks) and toks[k + 1].text == "."
                           for k, t in enumerate(toks)) or in_strings:
                        bad.append(f"{sid}/{sd.name}/{f.name}: data reference")
        self.assertEqual(bad, [], f"{len(bad)} steps with data blocks or references: {bad[:10]}")

    def test_e_every_transform_matches_a_removed_block(self) -> None:
        bad = []
        n_entries = 0
        for split, p, d in self.scs:
            if d["source"]["tier"] != "real_world":
                continue
            sid = shown(split, d["scenario_id"])
            kind = d["parameters"]["kind"]
            sub = "host" if kind == "host" else ("derived" if d["derived"] else "native")
            mod_dir = REPO_ROOT / "pool" / "terrads" / sub / str(d["module_id"])
            want = set()
            for f in sorted(mod_dir.glob("*.tf")):
                for btype, bname, btext in data_blocks(f.read_text(encoding="utf-8", errors="replace")):
                    want.add((f.name, btype, bname, hashlib.sha256(btext.encode("utf-8")).hexdigest(),
                              f"tp_ds_{btype}_{bname}"))
            got = {(e.get("file"), e.get("data_type"), e.get("data_name"), e.get("block_sha256"), e.get("variable"))
                   for e in d.get("host_transform") or [] if e.get("kind") == "data_source_to_variable"}
            n_entries += len(got)
            if got != want:
                bad.append(f"{sid}: recorded {sorted(got - want)[:2]} missing {sorted(want - got)[:2]}")
            for sd in step_dirs(p):
                dv = sd / "terrapreserve_data_variables.tf"
                blocks = modread.read_module({dv.name: dv.read_text(encoding="utf-8")}).variables if dv.is_file() else {}
                for e in want:
                    if e[4] not in blocks or "default" in blocks[e[4]].attrs:
                        bad.append(f"{sid}/{sd.name}: {e[4]} not declared without a default")
                if not want and dv.exists():
                    bad.append(f"{sid}/{sd.name}: data variables file without a transform")
        self.assertGreater(n_entries, 0)
        self.assertEqual(bad, [], f"{len(bad)} transform problems: {bad[:10]}")

    def test_f_controlled_steps_byte_identical_to_e96c017(self) -> None:
        self.assertEqual(file_digest(REPO_ROOT / "scenarios" / "dev", "controlled"),
                         (CONTROLLED_DEV_FILES, CONTROLLED_DEV_DIGEST_E96C017))
        manifest = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
        rows = sorted(f"{e['scenario_id']}|{s['step']}|{s['content_hash']}" for e in manifest
                      if int(e["scenario_id"].split("-")[-1]) <= 208 for s in e["steps"])
        self.assertEqual((len(rows), hashlib.sha256("\n".join(rows).encode()).hexdigest()),
                         (CONTROLLED_TEST_STEPS, CONTROLLED_TEST_DIGEST_E96C017))
        priv = private_root()
        if priv is not None:
            self.assertEqual(file_digest(priv, "controlled"),
                             (CONTROLLED_PRIVATE_FILES, CONTROLLED_PRIVATE_DIGEST_E96C017))

    def test_g_test_split_only_in_private_dir(self) -> None:
        manifest = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
        ids = {e["scenario_id"] for e in manifest}
        skip = {".git", ".venv", ".venv-tools", "__pycache__", ".terraform", "node_modules"}
        seen: set[str] = set()
        for _dirpath, dirnames, filenames in os.walk(REPO_ROOT):
            dirnames[:] = [x for x in dirnames if x not in skip]
            seen.update(x for x in dirnames if x in ids)
        self.assertEqual(len(seen), 0, f"{len(seen)} test-split id directories inside the repository (ids withheld)")
        for split, _p, d in self.scs:
            self.assertEqual(split == "test", d["scenario_id"] in ids, shown(split, d["scenario_id"]))
        priv = private_root()
        if priv is not None:
            import writer  # noqa: PLC0415

            by_id = {e["scenario_id"]: e for e in manifest}
            bad = []
            for sid, e in sorted(by_id.items()):
                sj = priv / sid / "scenario.json"
                if not sj.is_file():
                    bad.append(f"{sid}: missing from the private split")
                    continue
                text = sj.read_text(encoding="utf-8")
                if writer.sha256_text(text) != e["scenario_json_sha256"]:
                    bad.append(f"{sid}: manifest sha256 differs")
                if json.loads(text).get("variable_values_rule") != CURRENT_RULE:
                    bad.append(f"{sid}: not {CURRENT_RULE}")
            self.assertEqual(len(bad), 0, f"{len(bad)} private-split scenarios fail (ids withheld)")

    def test_h_record_equals_a_fresh_computation(self) -> None:
        import varvalues  # noqa: PLC0415

        bad = []
        for split, p, d in self.scs:
            steps = [{f.name: f.read_text(encoding="utf-8") for f in sd.glob("*.tf")} for sd in step_dirs(p)]
            fresh = varvalues.compute(steps, varvalues.search_record(d["scenario_id"], split))
            if {k: d.get(k) for k in RECORD_FIELDS} != {k: fresh.get(k) for k in RECORD_FIELDS}:
                bad.append(shown(split, d["scenario_id"]))
        self.assertEqual(bad, [], f"{len(bad)} scenario records differ from a recomputation: {bad[:10]}")

    def test_i_recorded_step_hashes_match_files(self) -> None:
        import writer  # noqa: PLC0415

        bad = []
        for split, p, d in self.scs:
            for s in d["steps"]:
                sd = p / f"step_{s['step']}"
                files = {f.name: f.read_text(encoding="utf-8") for f in sorted(sd.iterdir()) if f.is_file()}
                if writer.compute_step_content_hash(files) != s["content_hash"]:
                    bad.append(f"{shown(split, d['scenario_id'])}/step_{s['step']}")
        self.assertEqual(bad, [], f"step hash mismatches: {bad[:10]}")

    def test_j_generator_versions(self) -> None:
        bad = [shown(split, d["scenario_id"]) for split, _p, d in self.scs
               if d["generator_version"] != {"controlled": "d4a-8", "real_world": "d4b-9"}[d["source"]["tier"]]]
        self.assertEqual(bad, [], f"{len(bad)} scenarios with an old generator version: {bad[:5]}")


if __name__ == "__main__":
    unittest.main()
