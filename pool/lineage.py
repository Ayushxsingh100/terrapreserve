"""Repository lineages (D3-07, E10).

TerraDS has no fork flag, so forks and copies are found from the text. Modules are joined into one lineage
(connected components, union-find) by four rules, applied in this order:

* **a** same repository;
* **b** identical normalised module text: comments and whitespace are stripped (heredoc bodies keep their
  words), each file is hashed, and the per-file hashes are combined in sorted order;
* **c** for modules with two or more files each, at least 50 percent of the files share a normalised hash
  (shared distinct hashes against the file count of the smaller module); a file counts as shared only if it
  has at least ``FILE_TOKEN_FLOOR`` (30) normalised tokens, so boilerplate does not chain unrelated modules;
* **d** 5-token shingle Jaccard of at least 0.8, proposed by MinHash (64 permutations, 16 bands of 4 rows,
  seeded) and **confirmed by exact Jaccard** before two modules are joined.

The lineage id is ``lin-`` plus the smallest repository id in the component, zero-padded to 12 digits.

Limit (stated in the report as ``not yet established``): a fork that diverged below Jaccard 0.8 in every
rule cannot be detected, and nothing here knows about forks that GitHub records.

Standard library and ``sources/hcl_lex`` only.
"""

from __future__ import annotations

import collections
import hashlib
import itertools
import random
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterator

import hcl_lex

SEED = 20261030
PERMUTATIONS = 64
BANDS = 16
ROWS = 4
SHINGLE = 5
JACCARD_NUM, JACCARD_DEN = 4, 5  # threshold 0.8, compared in integers
FILE_SHARE_NUM, FILE_SHARE_DEN = 1, 2  # 50 percent
# User decision, 30 Oct 2026: a file counts as shared under rule c only from this many normalised tokens up.
# As first written (floor 0) trivial files (a comment-only main.tf, a provider block) chained unrelated
# repositories into one lineage of 1,645 modules; see docs/D3_DECISIONS.md, D3-07.
FILE_TOKEN_FLOOR = 30
PRIME = (1 << 61) - 1
MASK64 = (1 << 64) - 1
MIX = 0x9E3779B97F4A7C15  # odd multiplier for combining token hashes


@dataclass(frozen=True)
class ModuleInput:
    module_id: int
    repo_id: int
    files: dict[str, str]  # file name -> text


@dataclass
class LineageResult:
    lineage_of: dict[int, str]
    members: dict[str, list[int]]
    stats: dict
    merges: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------- normalisation


def normalised_tokens(text: str) -> list[str]:
    """Tokens of one file with comments and whitespace gone. Heredoc bodies are kept, whitespace-collapsed."""
    out: list[str] = []
    for tok, start, end in hcl_lex.tokenize_spans(text):
        if tok.kind == "NEWLINE":
            continue
        if tok.kind == "HEREDOC":
            out.append("H:" + " ".join(text[start:end].split()))
        else:
            out.append(tok.kind[0] + ":" + tok.text)
    return out


def file_digest(text: str) -> str:
    return hashlib.sha256("\x1f".join(normalised_tokens(text)).encode("utf-8", errors="replace")).hexdigest()


def module_hash(files: dict[str, str]) -> str:
    return hashlib.sha256("\n".join(sorted(file_digest(t) for t in files.values())).encode("ascii")).hexdigest()


def _token_hash(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode("utf-8", errors="replace"), digest_size=8).digest(), "big")


def module_shingles(files: dict[str, str]) -> set[int]:
    """Hashes of every window of 5 consecutive normalised tokens, taken within each file."""
    shingles: set[int] = set()
    for text in files.values():
        hashes = [_token_hash(t) for t in normalised_tokens(text)]
        for i in range(len(hashes) - SHINGLE + 1):
            h = 0
            for t in hashes[i : i + SHINGLE]:
                h = (h * MIX + t) & MASK64
            shingles.add(h)
    return shingles


# --------------------------------------------------------------------------- similarity


def exact_jaccard(a: set[int], b: set[int]) -> float:
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def similar(a: set[int], b: set[int]) -> bool:
    """Exact Jaccard of at least 0.8, compared in integers so that exactly 0.8 counts."""
    union = len(a | b)
    return union > 0 and len(a & b) * JACCARD_DEN >= union * JACCARD_NUM


@lru_cache(maxsize=4)
def _params(seed: int) -> tuple[tuple[int, int], ...]:
    rng = random.Random(seed)
    return tuple((rng.randrange(1, PRIME), rng.randrange(0, PRIME)) for _ in range(PERMUTATIONS))


def signature(shingles: set[int], seed: int = SEED) -> tuple[int, ...]:
    xs = [s % PRIME for s in shingles]
    return tuple(min([(a * x + b) % PRIME for x in xs]) for a, b in _params(seed)) if xs else (PRIME,) * PERMUTATIONS


def _buckets(sigs: dict[int, tuple[int, ...]]) -> Iterator[list[int]]:
    for band in range(BANDS):
        table: dict[tuple[int, ...], list[int]] = collections.defaultdict(list)
        for key in sorted(sigs):
            table[sigs[key][band * ROWS : (band + 1) * ROWS]].append(key)
        for members in table.values():
            if len(members) > 1:
                yield members


def band_candidates(sigs: dict[int, tuple[int, ...]]) -> set[tuple[int, int]]:
    """Pairs of keys whose signatures agree on all rows of at least one band (before any exact check)."""
    pairs: set[tuple[int, int]] = set()
    for members in _buckets(sigs):
        pairs.update(itertools.combinations(sorted(members), 2))
    return pairs


# --------------------------------------------------------------------------- lineages


class _UnionFind:
    def __init__(self, keys) -> None:
        self.parent = {k: k for k in keys}

    def find(self, k):
        root = k
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[k] != root:
            self.parent[k], k = root, self.parent[k]
        return root

    def union(self, a, b) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if rb < ra:
            ra, rb = rb, ra
        self.parent[rb] = ra
        return True


def lineage_id(repo_id: int) -> str:
    return f"lin-{repo_id:012d}"


def build_lineages(
    modules: list[ModuleInput], seed: int = SEED, min_shared_tokens: int = FILE_TOKEN_FLOOR
) -> LineageResult:
    """Group ``modules`` into lineages. ``min_shared_tokens`` is the token floor for a file to count as
    shared under rule c (0 = the rule as first written, kept for comparison)."""
    mods = {m.module_id: m for m in sorted(modules, key=lambda m: m.module_id)}
    uf = _UnionFind(mods)
    merges = {"a": 0, "b": 0, "c": 0, "d": 0}

    anchor: dict[int, int] = {}
    for mid, m in mods.items():
        if m.repo_id in anchor:
            merges["a"] += uf.union(anchor[m.repo_id], mid)
        else:
            anchor[m.repo_id] = mid

    by_hash: dict[str, list[int]] = collections.defaultdict(list)
    for mid, m in mods.items():
        by_hash[module_hash(m.files)].append(mid)
    for group in by_hash.values():
        for other in group[1:]:
            merges["b"] += uf.union(group[0], other)

    # rule c: modules with two or more files each
    file_sets: dict[int, set[str]] = {}
    n_files: dict[int, int] = {}
    posting: dict[str, list[int]] = collections.defaultdict(list)
    for mid, m in mods.items():
        if len(m.files) < 2:
            continue
        n_files[mid] = len(m.files)
        keep = {file_digest(t) for t in m.files.values() if len(normalised_tokens(t)) >= min_shared_tokens}
        file_sets[mid] = keep
        for h in keep:
            posting[h].append(mid)
    shared: collections.Counter[tuple[int, int]] = collections.Counter()
    for ids in posting.values():
        if len(ids) > 1:
            shared.update(itertools.combinations(ids, 2))
    for (a, b), count in sorted(shared.items()):
        if count * FILE_SHARE_DEN >= min(n_files[a], n_files[b]) * FILE_SHARE_NUM:
            merges["c"] += uf.union(a, b)

    # rule d: one representative per identical text, MinHash banding, exact confirmation
    reps = {group[0]: mods[group[0]] for group in by_hash.values()}
    shingles = {mid: module_shingles(m.files) for mid, m in sorted(reps.items())}
    sigs = {mid: signature(s, seed) for mid, s in shingles.items() if s}
    seen: set[tuple[int, int]] = set()
    for members in _buckets(sigs):
        for a, b in itertools.combinations(sorted(members), 2):
            if (a, b) in seen:
                continue
            seen.add((a, b))
            if uf.find(a) == uf.find(b):
                continue
            if similar(shingles[a], shingles[b]):
                merges["d"] += uf.union(a, b)

    groups: dict[int, list[int]] = collections.defaultdict(list)
    for mid in mods:
        groups[uf.find(mid)].append(mid)
    lineage_of: dict[int, str] = {}
    members: dict[str, list[int]] = {}
    repo_sets: dict[str, set[int]] = {}
    for ids in groups.values():
        repos = {mods[i].repo_id for i in ids}
        lid = lineage_id(min(repos))
        members[lid] = sorted(ids)
        repo_sets[lid] = repos
        for i in ids:
            lineage_of[i] = lid
    multi = [lid for lid, r in repo_sets.items() if len(r) > 1]
    stats = {
        "modules": len(mods),
        "repositories": len(anchor),
        "lineages": len(members),
        "largest_lineage_modules": max((len(v) for v in members.values()), default=0),
        "largest_lineage_repositories": max((len(v) for v in repo_sets.values()), default=0),
        "multi_repository_lineages": len(multi),
        "repositories_merged_by_content": sum(len(repo_sets[lid]) for lid in multi),
    }
    return LineageResult(lineage_of, dict(sorted(members.items())), stats, merges)


def one_per_lineage(module_ids: list[int], lineage_of: dict[int, str]) -> tuple[list[int], dict[int, int]]:
    """Keep the smallest module id of each lineage. Returns (kept ids, {dropped id: the id kept in its place})."""
    kept: dict[str, int] = {}
    for mid in sorted(module_ids):
        kept.setdefault(lineage_of[mid], mid)
    dropped = {mid: kept[lineage_of[mid]] for mid in module_ids if kept[lineage_of[mid]] != mid}
    return sorted(kept.values()), dict(sorted(dropped.items()))
