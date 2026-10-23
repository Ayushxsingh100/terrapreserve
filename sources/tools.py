"""Install the pinned helper tools into the external cache (D1 Prompt B).

    py -3.12 sources/tools.py gitleaks   # the CI gitleaks version, checksum-verified
    py -3.12 sources/tools.py go         # the Go toolchain, sha256 from go.dev
    py -3.12 sources/tools.py tci        # build terraform-config-inspect at a pinned commit

Standard library only. Everything lands under ``<cache>/tools`` and nothing is
added to the repository. The versions below are the ones this script verified;
a download whose hash differs from the published one is rejected.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acquire  # noqa: E402  (sibling script, not a package)

GITLEAKS_VERSION = "8.30.1"  # identical to GITLEAKS_VERSION in .github/workflows/ci.yml
GITLEAKS_BASE = f"https://github.com/gitleaks/gitleaks/releases/download/v{GITLEAKS_VERSION}"

GO_VERSION = "1.27.3"
# sha256 values as published at https://go.dev/dl/?mode=json on 2026-10-23.
GO_SHA256 = {
    "windows-amd64": "f26081f438319757f8a1b46d7d0b2c5ec7583d4038e485e0aa725cfde7885fff",
}

TCI_REPO = "https://github.com/hashicorp/terraform-config-inspect"
TCI_COMMIT = "75d64de68c31445dbe4ee8308350e0b6dda1571d"  # master head on 2026-10-23, committed 2026-09-04

IS_WINDOWS = platform.system() == "Windows"
EXE = ".exe" if IS_WINDOWS else ""
PLATFORM = "windows-amd64" if IS_WINDOWS else "linux-amd64"


def tools_dir() -> Path:
    path = acquire.cache_root() / "tools"
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch_verified(url: str, dest: Path, sha256: str) -> None:
    if not dest.is_file() or acquire.hash_file(dest)["sha256"] != sha256:
        acquire.download(url, dest, acquire.head_size(url))
    measured = acquire.hash_file(dest)["sha256"]
    if measured != sha256:
        raise acquire.AcquireError(f"{dest.name}: sha256 {measured} != expected {sha256}")


def install_gitleaks() -> Path:
    tools = tools_dir()
    asset = f"gitleaks_{GITLEAKS_VERSION}_{'windows_x64.zip' if IS_WINDOWS else 'linux_x64.tar.gz'}"
    sums = acquire.get_bytes(f"{GITLEAKS_BASE}/gitleaks_{GITLEAKS_VERSION}_checksums.txt").decode()
    expected = next(line.split()[0] for line in sums.splitlines() if line.endswith(f" {asset}"))
    archive = tools / asset
    fetch_verified(f"{GITLEAKS_BASE}/{asset}", archive, expected)
    out = tools / f"gitleaks-{GITLEAKS_VERSION}"
    out.mkdir(exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extract(f"gitleaks{EXE}", out)
    else:
        with tarfile.open(archive) as t:
            t.extract(f"gitleaks{EXE}", out, filter="data")
    binary = out / f"gitleaks{EXE}"
    print(f"{binary}  archive sha256 {expected}")
    return binary


def install_go() -> Path:
    tools = tools_dir()
    if PLATFORM not in GO_SHA256:
        raise acquire.AcquireError(f"no pinned Go archive hash for {PLATFORM}")
    archive = tools / f"go{GO_VERSION}.{PLATFORM}.zip"
    fetch_verified(f"https://go.dev/dl/{archive.name}", archive, GO_SHA256[PLATFORM])
    root = tools / f"go-{GO_VERSION}"
    if not (root / "go" / "bin" / f"go{EXE}").is_file():
        with zipfile.ZipFile(archive) as z:
            z.extractall(root)
    binary = root / "go" / "bin" / f"go{EXE}"
    print(f"{binary}  archive sha256 {GO_SHA256[PLATFORM]}")
    return binary


def go_env(go_bin: Path) -> dict[str, str]:
    tools = tools_dir()
    env = dict(os.environ)
    env.update(
        GOCACHE=str(tools / "go-build-cache"),
        GOPATH=str(tools / "gopath"),
        GOTOOLCHAIN="local",  # never download another toolchain behind our back
        GOFLAGS="-mod=readonly",
    )
    env["PATH"] = str(go_bin.parent) + os.pathsep + env["PATH"]
    return env


def build_tci() -> Path:
    go_bin = install_go()
    tools = tools_dir()
    src = tools / "terraform-config-inspect-src"
    if not (src / ".git").is_dir():
        acquire.git("clone", "--quiet", TCI_REPO, str(src))
    acquire.git("checkout", "--quiet", "--detach", TCI_COMMIT, cwd=src)
    head = acquire.git("rev-parse", "HEAD", cwd=src)
    if head != TCI_COMMIT:
        raise acquire.AcquireError(f"checked out {head}, wanted {TCI_COMMIT}")
    out = tools / "bin" / f"terraform-config-inspect{EXE}"
    out.parent.mkdir(exist_ok=True)
    env = go_env(go_bin)
    env["GOFLAGS"] = "-mod=mod"  # resolve and record module sums on first build
    try:
        result = subprocess.run(
            [str(go_bin), "build", "-o", str(out), "."], cwd=src, env=env, capture_output=True, text=True
        )
    except OSError as exc:  # e.g. a Windows Application Control policy blocking an unsigned go.exe
        raise acquire.AcquireError(f"could not run {go_bin.name}: {exc}") from exc
    if result.returncode != 0:
        raise acquire.AcquireError(f"go build failed:\n{result.stdout}{result.stderr}")
    print(f"{out}  built from {TCI_COMMIT}  sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("tool", choices=("gitleaks", "go", "tci"))
    args = parser.parse_args(argv)
    try:
        {"gitleaks": install_gitleaks, "go": install_go, "tci": build_tci}[args.tool]()
    except acquire.AcquireError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
