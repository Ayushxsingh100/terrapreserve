"""Deterministic seeding for the D4a scenario generator (D4-12).

One master seed ``20261031``; every scenario's ``random.Random`` is derived
from ``(master_seed, scenario_index)`` by hashing (SHA-256 → integer), so
generating one scenario never depends on generating the others and two full
runs produce byte-identical output.

Standard library only.  No DAIL import (D0 gate 1, CLAUDE.md rule 5).
"""

from __future__ import annotations

import hashlib
import random

MASTER_SEED: int = 20261031


def scenario_rng(scenario_index: int, *, master_seed: int = MASTER_SEED) -> random.Random:
    """Return a seeded ``random.Random`` for scenario number ``scenario_index``.

    The seed is the SHA-256 of the UTF-8 encoding of
    ``f"{master_seed}:{scenario_index}"`` interpreted as a big-endian integer.
    This means each scenario's RNG is independent of every other.
    """
    key = f"{master_seed}:{scenario_index}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    seed_int = int.from_bytes(digest, "big")
    rng = random.Random(seed_int)
    return rng


def template_shuffle_order(
    template_ids: list[str],
    *,
    master_seed: int = MASTER_SEED,
) -> list[str]:
    """Return ``template_ids`` shuffled with ``random.Random(master_seed)`` (D4-03).

    The first 7 in the result are dev; the last 3 are test.
    """
    rng = random.Random(master_seed)
    shuffled = list(template_ids)
    rng.shuffle(shuffled)
    return shuffled

