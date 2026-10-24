"""D1 Prompt C: RESOLUTION.md answers every marker in INVENTORY.md, with an allowed outcome and real evidence paths.

Also: no probe configuration contains credentials (Prompt C hard rule 1), and the checker can fail
(a self-test feeds it broken documents).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = REPO_ROOT / "validation" / "d1_to_verify"
ALLOWED_OUTCOMES = {"CONFIRMED", "CHANGED", "UNRESOLVED"}
REQUIRED_FIELDS = ("Marker:", "Outcome:", "Verified fact:", "Evidence E1:", "Evidence E2:", "Consequence for DAIL / TerraPreserve:", "Open question for authors")
SECTION = re.compile(r"^### ([VX]\d\d) — (.+)$", re.M)
OUTCOME = re.compile(r"^Outcome: (\S+)\s*$", re.M)
CREDENTIAL_ATTRIBUTES = re.compile(r"^\s*(access_key|secret_key|token|shared_credentials_file|profile)\s*=", re.M)


def inventory_items(text: str) -> set[str]:
    """Item ids of the inventory table, without the definition and aggregate rows."""
    items = set()
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(r"[VX]\d\d", cells[0]):
            items.add(cells[0])
    return items


def sections(text: str) -> dict[str, str]:
    """Map item id -> section body of RESOLUTION.md (up to the next section or the summary)."""
    found = list(SECTION.finditer(text))
    bodies = {}
    for index, match in enumerate(found):
        end = found[index + 1].start() if index + 1 < len(found) else len(text)
        body = text[match.end():end]
        body = body.split("\n---\n", 1)[0] if index + 1 == len(found) else body
        bodies[match.group(1)] = body
    return bodies


def problems_in(resolution: str, inventory: str) -> list[str]:
    """Everything wrong with a resolution document, as readable strings (empty = fine)."""
    problems = []
    wanted = inventory_items(inventory)
    bodies = sections(resolution)
    for item in sorted(wanted - set(bodies)):
        problems.append(f"{item}: marker in the inventory has no section")
    for item in sorted(set(bodies) - wanted):
        problems.append(f"{item}: section without an inventory marker")
    summary_rows = dict(re.findall(r"^\| ([VX]\d\d) \| (\w+) \|", resolution.split("## Summary", 1)[-1], re.M))
    for item, body in sorted(bodies.items()):
        outcomes = OUTCOME.findall(body)
        if len(outcomes) != 1:
            problems.append(f"{item}: expected exactly one Outcome line, found {len(outcomes)}")
            continue
        if outcomes[0] not in ALLOWED_OUTCOMES:
            problems.append(f"{item}: outcome {outcomes[0]!r} is not one of {sorted(ALLOWED_OUTCOMES)}")
        for field in REQUIRED_FIELDS:
            if field not in body:
                problems.append(f"{item}: missing {field!r}")
        if summary_rows.get(item) != outcomes[0]:
            problems.append(f"{item}: summary table says {summary_rows.get(item)!r}, section says {outcomes[0]!r}")
        if outcomes[0] in ("CONFIRMED", "CHANGED"):
            evidence = re.search(r"Evidence E1:(.*?)\n\n", body, re.S)
            e1_none = evidence is not None and evidence.group(1).strip().lower().startswith("none")
            e2 = re.search(r"Evidence E2:(.*?)\n\n", body, re.S)
            e2_none = e2 is not None and e2.group(1).strip().lower().startswith("none")
            if e1_none and e2_none:
                problems.append(f"{item}: {outcomes[0]} without any evidence")
    if set(summary_rows) != set(bodies):
        problems.append("summary table items differ from the sections")
    return problems


def evidence_paths(resolution: str) -> set[str]:
    """Repository paths cited in backticks that point into validation/ (or tests/)."""
    cited = set(re.findall(r"`((?:validation|tests|sources)/[A-Za-z0-9_./-]+)`", resolution))
    return {c for c in cited if "*" not in c and "<" not in c}


class TestResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = (BASE / "INVENTORY.md").read_text(encoding="utf-8")
        cls.resolution = (BASE / "RESOLUTION.md").read_text(encoding="utf-8")

    def test_inventory_lists_the_expected_items(self) -> None:
        expected = {f"V{n:02d}" for n in range(1, 15)}
        self.assertTrue(expected <= inventory_items(self.inventory))

    def test_one_section_per_marker_with_allowed_outcome(self) -> None:
        self.assertEqual(problems_in(self.resolution, self.inventory), [])

    def test_cited_evidence_paths_exist(self) -> None:
        missing = [p for p in sorted(evidence_paths(self.resolution)) if not (REPO_ROOT / p).exists()]
        self.assertEqual(missing, [])


class TestProbeHygiene(unittest.TestCase):
    def test_no_credentials_in_terraform_files(self) -> None:
        offenders = []
        for path in sorted(BASE.rglob("*.tf")):
            if CREDENTIAL_ATTRIBUTES.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [])

    def test_every_provider_block_sets_the_skip_flags(self) -> None:
        flags = ("skip_credentials_validation", "skip_requesting_account_id", "skip_metadata_api_check", "skip_region_validation")
        missing = []
        for path in sorted(BASE.rglob("main.tf")):
            text = path.read_text(encoding="utf-8")
            if 'provider "aws"' in text and "control_network_on" not in path.parts:
                missing += [f"{path.relative_to(REPO_ROOT)}: {f}" for f in flags if f not in text]
        self.assertEqual(missing, [])

    def test_probe_provider_pins_match_the_smoke_configuration(self) -> None:
        smoke = (REPO_ROOT / "validation" / "smoke" / "versions.tf").read_text(encoding="utf-8")
        for path in sorted(BASE.rglob("versions.tf")):
            self.assertEqual(path.read_text(encoding="utf-8"), smoke, str(path.relative_to(REPO_ROOT)))


class TestCheckerCanFail(unittest.TestCase):
    """Self-test: the document checker reports each kind of defect."""

    INVENTORY = "| Item | File:line | Marker text |\n|---|---|---|\n| V01 | `a.md:1` | [TO VERIFY] |\n| X01 | `a.md:2` | [TO VERIFY] |\n"

    @staticmethod
    def section(item: str, outcome: str, e1: str = "`validation/x`") -> str:
        return (
            f"### {item} — title\n\nMarker: m\n\nOutcome: {outcome}\n\nVerified fact: f\n\nEvidence E1: {e1}\n\n"
            "Evidence E2: e\n\nConsequence for DAIL / TerraPreserve: c\n\nOpen question for authors: none\n\n"
        )

    def document(self, *sections: str, rows: str = "| V01 | CONFIRMED |\n| X01 | CONFIRMED |\n") -> str:
        return "".join(sections) + "---\n\n## Summary\n\n| Item | Outcome |\n|---|---|\n" + rows

    def test_good_document_passes(self) -> None:
        doc = self.document(self.section("V01", "CONFIRMED"), self.section("X01", "CONFIRMED"))
        self.assertEqual(problems_in(doc, self.INVENTORY), [])

    def test_missing_section_is_reported(self) -> None:
        doc = self.document(self.section("V01", "CONFIRMED"), rows="| V01 | CONFIRMED |\n")
        self.assertTrue(any("X01" in p and "no section" in p for p in problems_in(doc, self.INVENTORY)))

    def test_extra_section_is_reported(self) -> None:
        doc = self.document(self.section("V01", "CONFIRMED"), self.section("X01", "CONFIRMED"), self.section("V02", "CONFIRMED"))
        self.assertTrue(any("V02" in p for p in problems_in(doc, self.INVENTORY)))

    def test_outcome_outside_the_three_words_is_reported(self) -> None:
        doc = self.document(self.section("V01", "PARTIAL"), self.section("X01", "CONFIRMED"), rows="| V01 | PARTIAL |\n| X01 | CONFIRMED |\n")
        self.assertTrue(any("PARTIAL" in p for p in problems_in(doc, self.INVENTORY)))

    def test_summary_mismatch_is_reported(self) -> None:
        doc = self.document(self.section("V01", "CONFIRMED"), self.section("X01", "CONFIRMED"), rows="| V01 | CHANGED |\n| X01 | CONFIRMED |\n")
        self.assertTrue(any("summary table says" in p for p in problems_in(doc, self.INVENTORY)))

    def test_confirmed_without_evidence_is_reported(self) -> None:
        bad = self.section("V01", "CONFIRMED", e1="none").replace("Evidence E2: e", "Evidence E2: none")
        doc = self.document(bad, self.section("X01", "CONFIRMED"))
        self.assertTrue(any("without any evidence" in p for p in problems_in(doc, self.INVENTORY)))

    def test_credential_pattern_matches(self) -> None:
        self.assertTrue(CREDENTIAL_ATTRIBUTES.search('  access_key = "x"\n'))
        self.assertFalse(CREDENTIAL_ATTRIBUTES.search('  skip_credentials_validation = true\n'))


if __name__ == "__main__":
    unittest.main()
