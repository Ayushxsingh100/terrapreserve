#!/usr/bin/env python3
"""D6-04 and D6-05: the frozen v1.0 manifests and the oracle evidence archives.

* ``scenarios/V1_MANIFEST.json`` (public): every dev scenario's id, ``v1_role``, ``scenario.json`` sha256 and step
  content hashes; for the test split ids, ``v1_role`` and hashes only (as ``scenarios/test_manifest.json``).
* ``$TERRAPRESERVE_PRIVATE/V1_MANIFEST_PRIVATE.json``: the same for the test scenarios, plus ``v1_role_reason``,
  family, intent class, oracle ``gt_class`` and tier.
* ``scenarios/V1_MANIFEST.sha256``: the sha256 of both manifest files (``<sha256>  <name>`` lines).
* Evidence (registry 2.10 run records of every scenario the oracle decided) per split, as deterministic
  ``.tar.gz`` archives (sorted entries, mtime 0, uid/gid 0, mode 0644, gzip mtime 0). Both are kept outside the
  repository (D6-05 as changed by the user, 11 Nov 2026): dev under ``~/.terrapreserve-cache/v1.0/``, test under
  ``$TERRAPRESERVE_PRIVATE/v1.0/``. Their sha256 and sizes go into ``docs/D6_FREEZE.md`` (computed part).

Standard library only. Test-split ids are never printed.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "generator"))

import writer  # noqa: E402

CACHE = Path.home() / ".terrapreserve-cache"
MANIFEST = REPO_ROOT / "scenarios" / "V1_MANIFEST.json"
SUMS = REPO_ROOT / "scenarios" / "V1_MANIFEST.sha256"
PRIVATE_MANIFEST_NAME = "V1_MANIFEST_PRIVATE.json"
FREEZE_DOC = REPO_ROOT / "docs" / "D6_FREEZE.md"
MARKER = "<!-- computed below by tools/freeze_v1.py; the part above is written by hand -->"


def _priv() -> Path | None:
    p = os.environ.get("TERRAPRESERVE_PRIVATE")
    return Path(p) if p and Path(p).is_dir() else None


RECORDS = {"dev": CACHE / "d5b-records", "test": (_priv() or Path("/nonexistent")) / "d5b-records"}
ARCHIVE_DIR = {"dev": CACHE / "v1.0", "test": (_priv() or Path("/nonexistent")) / "v1.0"}


def build_archive(records: Path, out: Path, prefix: str) -> tuple[str, int]:
    """Pack ``records/*.json`` into ``out`` deterministically; returns (sha256, size in bytes)."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for f in sorted(records.glob("*.json")):
            data = f.read_bytes()
            info = tarfile.TarInfo(f"{prefix}/{f.name}")
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(raw.getvalue())
    data = buf.getvalue()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return hashlib.sha256(data).hexdigest(), len(data)


def entry(path: Path, d: dict) -> dict[str, Any]:
    return {"scenario_id": d["scenario_id"], "v1_role": d["v1_role"],
            "scenario_json_sha256": writer.sha256_text((path / "scenario.json").read_text(encoding="utf-8")),
            "steps": [{"step": s["step"], "content_hash": s["content_hash"]} for s in d["steps"]]}


def manifests(scs) -> tuple[dict, dict | None]:
    """(public manifest, private manifest or None) from the loaded scenarios (``check_freeze_gates.Sc``)."""
    dev = [entry(sc.path, sc.data) for sc in scs if sc.split == "dev"]
    tm = json.loads((REPO_ROOT / "scenarios" / "test_manifest.json").read_text(encoding="utf-8"))
    test_roles = {sc.id: sc.data["v1_role"] for sc in scs if sc.split == "test"}
    public = {"dataset_version": "1.0", "decision": "D6-04",
              "dev": sorted(dev, key=lambda e: e["scenario_id"]),
              "test": sorted(({"scenario_id": e["scenario_id"], "v1_role": test_roles.get(e["scenario_id"]),
                               "scenario_json_sha256": e["scenario_json_sha256"], "steps": e["steps"]} for e in tm),
                             key=lambda e: e["scenario_id"])}
    private = None
    if test_roles:
        private = {"dataset_version": "1.0", "decision": "D6-04", "test": sorted(
            (dict(entry(sc.path, sc.data), v1_role_reason=sc.data.get("v1_role_reason"), family=sc.data["family"],
                  intent_class=sc.data["intent"]["class"], gt_class=sc.data.get("gt_class"),
                  tier=sc.data["source"]["tier"]) for sc in scs if sc.split == "test"),
            key=lambda e: e["scenario_id"])}
    return public, private


def verify_manifests(scs) -> list[str]:
    """Gate 8: the written manifests against the scenarios and against ``V1_MANIFEST.sha256``."""
    problems = []
    public, private = manifests(scs)
    if json.loads(MANIFEST.read_text(encoding="utf-8")) != public:
        problems.append("scenarios/V1_MANIFEST.json does not match the scenarios")
    sums = dict(reversed(ln.split("  ", 1)) for ln in SUMS.read_text(encoding="utf-8").splitlines())
    if sums.get(MANIFEST.name) != hashlib.sha256(MANIFEST.read_bytes()).hexdigest():
        problems.append("V1_MANIFEST.sha256 does not match V1_MANIFEST.json")
    priv = _priv()
    if private is not None and priv is not None:
        pm = priv / PRIVATE_MANIFEST_NAME
        if not pm.is_file() or json.loads(pm.read_text(encoding="utf-8")) != private:
            problems.append("the private manifest does not match the withheld scenarios")
        elif sums.get(PRIVATE_MANIFEST_NAME) != hashlib.sha256(pm.read_bytes()).hexdigest():
            problems.append("V1_MANIFEST.sha256 does not match the private manifest")
    return problems


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import check_freeze_gates as g  # noqa: PLC0415
    priv = _priv()
    if priv is None:
        raise SystemExit("TERRAPRESERVE_PRIVATE is not set")
    scs = g.load(REPO_ROOT / "scenarios" / "dev", priv)
    public, private = manifests(scs)
    MANIFEST.write_text(writer.canonical_json(public), encoding="utf-8", newline="\n")
    pm = priv / PRIVATE_MANIFEST_NAME
    pm.write_text(writer.canonical_json(private), encoding="utf-8", newline="\n")
    SUMS.write_text(f"{hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}  {MANIFEST.name}\n"
                    f"{hashlib.sha256(pm.read_bytes()).hexdigest()}  {PRIVATE_MANIFEST_NAME}\n",
                    encoding="utf-8", newline="\n")
    lines = [MARKER, "", "## Computed (`tools/freeze_v1.py`)", ""]
    for name, path in ((MANIFEST.name, MANIFEST), (PRIVATE_MANIFEST_NAME, pm), (SUMS.name, SUMS)):
        where = "`$TERRAPRESERVE_PRIVATE` (withheld)" if path == pm else f"`scenarios/{name}` (committed)"
        lines.append(f"- `{name}`: sha256 `{hashlib.sha256(path.read_bytes()).hexdigest()}`, "
                     f"{path.stat().st_size} bytes; {where}")
    for split in ("dev", "test"):
        name = f"oracle-evidence-{split}-v1.0.tar.gz"
        recs = sorted(RECORDS[split].glob("*.json"))
        decided = {sc.id for sc in scs if sc.split == split and (sc.data.get("labels") or (
            (sc.data.get("excluded_from_v1") or {}).get("by") == "oracle-1.0"))}
        missing = sorted(decided - {f.stem for f in recs})
        extra = sorted({f.stem for f in recs} - decided)
        if missing or extra:
            raise SystemExit(f"{split}: records do not match the oracle-decided scenarios "
                             f"({len(missing)} missing, {len(extra)} extra)")
        sha, size = build_archive(RECORDS[split], ARCHIVE_DIR[split] / name, name[:-7])
        home = ("`~/.terrapreserve-cache/v1.0/`" if split == "dev" else "`$TERRAPRESERVE_PRIVATE/v1.0/`")
        lines.append(f"- `{name}`: sha256 `{sha}`, {size} bytes; {len(recs)} run records; kept outside the "
                     f"repository in {home} for the Zenodo release")
    text = FREEZE_DOC.read_text(encoding="utf-8") if FREEZE_DOC.is_file() else MARKER + "\n"
    head = text.split(MARKER)[0].rstrip("\n") + "\n"
    FREEZE_DOC.write_text(head + "\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[3:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
