"""S0 eligibility screen for real-world modules (D4b-07, extended by D4b-15 to the whole module).

Registry v1.0 C-64: "every security group is in scope, attached or not". A module is screened as a whole
(verbatim host files, plus the graft where there is one). Every rejection carries an exclusion code and a
reason. The screen is a generator self-check, not a label and not the oracle; it reads no DAIL code.
Standard library only.

Exclusion codes (documented in ``docs/D4B_DECISIONS.md``, D4b-15):

* ``RW-S0-UNSUP-TYPE``   a registry 2.7 relevant-unsupported type is present;
* ``RW-S0-MIXED``        a security group is MIXED (registry 2.6, C-84);
* ``RW-S0-SEC-001``      a group, alone or together for TCP 22, covers ``0.0.0.0/0`` or ``::/0``;
* ``RW-S0-SEC-002``      the same for TCP 5432;
* ``RW-S0-SEC-003``      an ``aws_db_instance`` has ``publicly_accessible = true``;
* ``RW-S0-UNDECIDABLE``  registry indeterminacy that can change a result: ``possible4``/``possible6`` for TCP
                         22 or 5432 over a configured or pseudo group (3.3, 3.4), an unresolved
                         ``publicly_accessible`` (5.4), or an indeterminate rule that could permit TCP/5432
                         in a pseudo-group (6.4 row 7). Unresolved values that cannot affect any of the four
                         results never reject a module (see ``modread.py``);
* ``RW-S0-FUNC``         a module without a graft (native) is not shown to satisfy INV-FUNC-001 at S0.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "sources"))

from realworld import modread  # noqa: E402

ALL_CODES = (
    "RW-S0-UNSUP-TYPE",
    "RW-S0-MIXED",
    "RW-S0-SEC-001",
    "RW-S0-SEC-002",
    "RW-S0-SEC-003",
    "RW-S0-UNDECIDABLE",
    "RW-S0-FUNC",
)


@dataclass
class ScreenResult:
    accepted: bool
    codes: list[str] = field(default_factory=list)  # every code triggered, in fixed priority order
    details: list[str] = field(default_factory=list)

    @property
    def primary(self) -> str:
        return self.codes[0] if self.codes else "accepted"


def screen_module(files: dict[str, str], is_native: bool = False) -> ScreenResult:
    """Screen the whole module. Hosts are never exempt for any invariant, whatever the scenario's target.

    ``files`` holds every ``.tf`` file that will be in ``step_0`` except the graft. The graft is clean
    by construction apart from the repair target and is checked by the round-5 tests on the generated
    step directories.
    """
    an = modread.analyse(files)
    codes = list(an.codes)
    details: list[str] = []
    details += [f"unsupported type {a}" for a in an.unsupported_types]
    details += [f"MIXED {a}" for a in an.mixed]
    for inv, wheres in sorted(an.violations.items()):
        details += [f"{inv} by {w}" for w in wheres]
    details += an.undecidable
    if is_native:
        status, row, why = modread.native_func_precheck(files)
        codes.append("RW-S0-FUNC")
        details.append(f"INV-FUNC-001 {status} (row {row}): {why}" if status != "PASS?"
                       else "INV-FUNC-001: E5 and E6 are not evaluated for natives")
    return ScreenResult(not codes, codes, details)


def screen_native_s0(files: dict[str, str], target_invariant: str | None = None) -> tuple[bool, str]:
    """Compatibility wrapper used for natives: (eligible, reason)."""
    res = screen_module(files, is_native=True)
    return res.accepted, ("eligible" if res.accepted else f"{res.primary}: {res.details[0] if res.details else ''}")
