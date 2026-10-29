"""Secret scans (E09) and the TerraGoat redaction (D3-12).

Two scanners run on every module, because gitleaks is pattern-based and missed 3 of the 4 TerraGoat secrets
(docs/D3_CARRYOVER.md item 1):

* **gitleaks 8.30.1** (``gitleaks dir``, run with ``--redact``; only rule id, file and line are read);
* the **attribute inventory** of ``sources/terragoat/attribute_inventory.py``: any attribute whose name matches
  ``password|passwd|secret|access_key|secret_key|token|private_key|api_key|user_data|connection_string``
  and whose value is a literal.

A real-world (TerraDS) module with any finding is **excluded**, never edited (D3-11b). TerraGoat is the one
source that is edited: the flagged attributes are deleted, each deletion is logged by file, line, resource
address and attribute name (never a value), and the result is rescanned.

No secret value is ever kept: flags hold names and line numbers, and the gitleaks report is deleted after its
rule ids and positions are read. Standard library and ``sources/*`` only.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import acquire
import attribute_inventory
import tools

GITLEAKS_VERSION = tools.GITLEAKS_VERSION


@dataclass(frozen=True)
class Flag:
    """A credential-like attribute holding a literal. Names and positions only."""

    file: str
    line: int
    end_line: int
    address: str
    attribute: str
    kind: str  # literal | heredoc | call-with-literal


@dataclass(frozen=True)
class SecretsResult:
    gitleaks_findings: int
    inventory_flagged: int
    rules: tuple[str, ...]  # gitleaks rule ids
    attributes: tuple[str, ...]  # "<attribute name>:<value kind>" of the inventory flags


def has_secrets(result: SecretsResult) -> bool:
    return result.gitleaks_findings > 0 or result.inventory_flagged > 0


# --------------------------------------------------------------------------- inventory


def inventory_flags(files: dict[str, str]) -> list[Flag]:
    """Every flagged attribute of every file (``name -> text``), in file and line order."""
    out: list[Flag] = []
    for name in sorted(files):
        flagged, _rest = attribute_inventory.split_flagged(attribute_inventory.matching_attributes(files[name]))
        out.extend(Flag(name, a.line, a.end_line, a.top_level, a.name, a.value_kind) for a in flagged)
    return out


# --------------------------------------------------------------------------- gitleaks


def gitleaks_binary() -> Path | None:
    """The pinned gitleaks in the cache, or ``None`` if it is not installed (``py -3.12 sources/tools.py gitleaks``)."""
    try:
        path = acquire.cache_root() / "tools" / f"gitleaks-{GITLEAKS_VERSION}" / (
            "gitleaks.exe" if platform.system() == "Windows" else "gitleaks")
    except acquire.AcquireError:
        return None
    if not path.is_file():
        return None
    try:
        out = subprocess.run([str(path), "version"], capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return path if out.stdout.strip() == GITLEAKS_VERSION else None


def gitleaks_findings(binary: Path, directory: Path) -> list[tuple[str, str, int]]:
    """``(rule id, file name, start line)`` of each finding under ``directory``. The report, which holds the
    (redacted) matches, is read for those three fields only and then deleted."""
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.json"
        proc = subprocess.run(
            [str(binary), "dir", str(directory), "--redact", "--no-banner", "--exit-code", "0",
             "--report-format", "json", "--report-path", str(report)],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            raise acquire.AcquireError(f"gitleaks exited {proc.returncode}: {proc.stderr[-300:]}")
        raw = json.loads(report.read_text(encoding="utf-8") or "[]")
    return [(f["RuleID"], Path(f["File"]).name, f["StartLine"]) for f in raw]


def scan_directory(binary: Path, directory: Path) -> SecretsResult:
    """Both scanners over the ``*.tf`` files in ``directory``."""
    files = {p.name: p.read_bytes().decode("utf-8", errors="replace") for p in sorted(directory.glob("*.tf"))}
    flags = inventory_flags(files)
    findings = gitleaks_findings(binary, directory)
    return SecretsResult(
        len(findings), len(flags),
        tuple(sorted({rule for rule, _f, _l in findings})),
        tuple(sorted({f"{f.attribute}:{f.kind}" for f in flags})),
    )


# --------------------------------------------------------------------------- TerraGoat redaction


def plan_redactions(files: dict[str, str]) -> list[Flag]:
    """What to delete: every flagged attribute (the whole attribute, heredoc body included)."""
    return inventory_flags(files)


def apply_redactions(files: dict[str, str], plan: list[Flag]) -> dict[str, str]:
    """``files`` with the planned line ranges deleted and nothing else changed."""
    drop: dict[str, set[int]] = {}
    for r in plan:
        drop.setdefault(r.file, set()).update(range(r.line, r.end_line + 1))
    out = {}
    for name, text in files.items():
        gone = drop.get(name)
        if not gone:
            out[name] = text
            continue
        out[name] = "\n".join(line for number, line in enumerate(text.split("\n"), start=1) if number not in gone)
    return out


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redaction_log(plan: list[Flag], before: dict[str, str], after: dict[str, str], commit: str) -> str:
    """Markdown log: file, line, resource address and attribute name of each deletion, plus the sha256 of every
    file before and after. It holds no attribute value."""
    lines = [
        "# TerraGoat redaction log",
        "",
        "Generated by `pool/redact.py`. **No value appears here**: each row names the file, the upstream line "
        "range, the resource address and the attribute that was deleted; nothing else in any file was changed.",
        "",
        f"- source: `bridgecrewio/terragoat` at commit `{commit}`, directory `terraform/aws/`, licence Apache-2.0",
        f"- attributes deleted: {len(plan)} in {len({r.file for r in plan})} file(s)",
        "- rule: delete every attribute that `sources/terragoat/attribute_inventory.py` flags (a credential-like "
        "name holding a literal, a heredoc or a function call wrapping a literal); the rest of each block is intact",
        "",
        "| File | Upstream lines | Lines removed | Resource address | Attribute | Value kind |",
        "|---|---|---:|---|---|---|",
    ]
    for r in plan:
        span = f"{r.line}" if r.line == r.end_line else f"{r.line}-{r.end_line}"
        lines.append(f"| `{r.file}` | {span} | {r.end_line - r.line + 1} | `{r.address}` | `{r.attribute}` | {r.kind} |")
    lines += ["", "| File | sha256 upstream | sha256 in pool | Changed |", "|---|---|---|---|"]
    for name in sorted(before):
        a, b = sha256_text(before[name]), sha256_text(after[name])
        lines.append(f"| `{name}` | `{a}` | `{b}` | {'yes' if a != b else 'no'} |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- the TerraGoat pool directory

TERRAGOAT_URL = "https://github.com/bridgecrewio/terragoat"
TERRAGOAT_SUBDIR = "terraform/aws"


class RedactionError(RuntimeError):
    """The TerraGoat build refused to publish: an upstream file differs from the pin, or the rescan is not clean."""


def _notice(commit: str) -> str:
    return "\n".join([
        "TerraGoat-derived files",
        "=======================",
        "",
        f"The .tf files in this directory are derived from TerraGoat ({TERRAGOAT_URL}), commit {commit},",
        f"directory {TERRAGOAT_SUBDIR}/, which is licensed under the Apache License, Version 2.0. The licence text",
        "is in LICENSE.upstream and applies to these files.",
        "",
        "Changes made to the upstream files (Apache License, Version 2.0, section 4(b)): attributes that hold",
        "credential-like literals were deleted so that the dataset contains no secrets. Nothing else was changed.",
        "Each deleted attribute is listed in REDACTION_LOG.md by file, line, resource address and attribute name;",
        "the log holds no values. SOURCE.json gives the sha256 of every file before and after.",
        "",
    ])


def build_terragoat(clone: Path, dest: Path, commit: str, *, listing: dict[str, str] | None,
                    binary: Path | None) -> dict:
    """Copy the ``terraform/aws/*.tf`` files of a TerraGoat clone to ``dest`` with the flagged attributes deleted.

    ``listing`` maps file name to the sha256 recorded when the source was pinned (``None`` skips that check).
    The redacted text is rescanned (inventory, and gitleaks when ``binary`` is given) in a scratch directory
    **before** anything is written to ``dest``; a finding raises ``RedactionError`` and ``dest`` is untouched.
    """
    source = clone / TERRAGOAT_SUBDIR
    raw = {p.name: p.read_bytes() for p in sorted(source.glob("*.tf"))}
    if not raw:
        raise RedactionError(f"no .tf files under {source}")
    before = {name: data.decode("utf-8") for name, data in raw.items()}
    if listing is not None:
        wrong = [n for n in sorted(raw) if hashlib.sha256(raw[n]).hexdigest() != listing.get(n)]
        if wrong:
            raise RedactionError(f"upstream files differ from the pinned listing: {', '.join(wrong)}")
    plan = plan_redactions(before)
    after = apply_redactions(before, plan)
    leftover = inventory_flags(after)
    if leftover:
        raise RedactionError(f"rescan: {len(leftover)} flagged attribute(s) remain after redaction")
    if binary is not None:
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in after.items():
                (Path(tmp) / name).write_text(text, encoding="utf-8", newline="\n")
            findings = gitleaks_findings(binary, Path(tmp))
        if findings:
            raise RedactionError(f"rescan: gitleaks reports {len(findings)} finding(s) after redaction")
    licence_text = (clone / "LICENSE").read_text(encoding="utf-8")
    not_copied = sorted(
        p.relative_to(clone).as_posix() for p in source.rglob("*") if p.is_file() and p.suffix != ".tf"
    )
    dest.mkdir(parents=True, exist_ok=True)
    for stale in dest.glob("*"):
        if stale.is_file():
            stale.unlink()
    for name, text in after.items():
        (dest / name).write_text(text, encoding="utf-8", newline="\n")
    (dest / "REDACTION_LOG.md").write_text(redaction_log(plan, before, after, commit), encoding="utf-8", newline="\n")
    (dest / "NOTICE").write_text(_notice(commit), encoding="utf-8", newline="\n")
    (dest / "LICENSE.upstream").write_text(licence_text, encoding="utf-8", newline="\n")
    document = {
        "kind": "terragoat",
        "repository": TERRAGOAT_URL,
        "commit": commit,
        "directory": TERRAGOAT_SUBDIR,
        "licence_spdx": "Apache-2.0",
        "licence_file": "LICENSE.upstream",
        "licence_file_sha256": sha256_text(licence_text),
        "files": [
            {"path": name, "sha256": sha256_text(after[name]), "bytes": len(after[name].encode("utf-8")),
             "upstream_sha256": hashlib.sha256(raw[name]).hexdigest()}
            for name in sorted(after)
        ],
        "not_copied": not_copied,
        "not_copied_reason": "not .tf files; the secret inventory covers .tf files only",
        "redactions": len(plan),
        "scanners": {"gitleaks": GITLEAKS_VERSION if binary is not None else "not run", "attribute_inventory": "run"},
    }
    (dest / "SOURCE.json").write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return {"redactions": len(plan), "files": len(after), "not_copied": len(not_copied)}
