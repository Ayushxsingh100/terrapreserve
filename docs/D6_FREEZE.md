# TerraPreserve v1.0: the freeze (D6)

Work package D6 (queue step 18). This part is written by hand; the hashes and sizes below the marker are written by `tools/freeze_v1.py`, and the gate results are in `docs/D6_GATES.md` (written by `tools/check_freeze_gates.py`).

## What is frozen

- **The frozen commit** is the merge commit of the D6 pull request into `main`. The user tags it `terrapreserve-v1.0` after the external review verdict; this pull request creates no tag.
- **Contents:** 416 scenarios (288 dev, 128 test) with `dataset_version: "1.0"`, of which 320 are v1.0 targets (`v1_role: "target"`, D6-02), 71 reserves and 25 excluded (`excluded_from_v1`). The dev split is committed under `scenarios/dev/`; the test split stays in `$TERRAPRESERVE_PRIVATE` and is described in the repository only by ids and hashes (`scenarios/test_manifest.json`, `scenarios/V1_MANIFEST.json`).
- **Manifests (D6-04):** `scenarios/V1_MANIFEST.json` (public), `$TERRAPRESERVE_PRIVATE/V1_MANIFEST_PRIVATE.json` (withheld) and `scenarios/V1_MANIFEST.sha256` (the sha256 of both).
- **Oracle evidence (D6-05):** the registry 2.10 run records of every scenario the oracle decided, one deterministic archive per split. Both archives are kept outside the repository (user, 11 Nov 2026: CLAUDE.md rule 6 keeps archives out of the repository) and go to the Zenodo release with the dataset; their sha256 and sizes are below.
- **Release (D0 Decision 9):** TerraPreserve is "kept internal until v1.0 is frozen, then released when the paper is submitted". At release, "our scenarios and labels are released under CC-BY-4.0. TerraGoat-derived files keep their Apache-2.0 notice. TerraDS-derived files keep their original repository's license, recorded per scenario." This package uploads nothing and makes no split public.

## After the freeze

- After the tag, any change to scenarios, labels or manifests goes to v1.1, never an edit to v1.0 (project plan, D6: "After freezing, fixes create v1.1, never edits.").
- **Regeneration warning.** The committed real-world tier was generated (generator `d4b-9`) with the screen reader of `49837f2`. Since D4c the reader is fixed (MIXED in any direction; TCP `from_port > to_port`), so regenerating the real-world tier would reject the hosts of tp-v1-F2-0250, tp-v1-F2-0252 and tp-v1-F3-0263 (excluded from v1.0 as `s0_not_clean`) and change the tier. v1.0 is the tier as committed; a regeneration is v1.1 work and needs a relabel.
- **DAIL follow-ups** (not TerraPreserve changes): the wording clarification of registry 2.9 in a new `INVARIANT_REGISTRY_v1.1.md` (C-85) so DAIL and the oracle read footprint comparison the same way, before P8 measures impact accuracy; and the "every move counts as a change" fix (P3b/P4).
- **Known limitations** are listed in the v1.0 section of `DATASHEET.md`.

<!-- computed below by tools/freeze_v1.py; the part above is written by hand -->

## Computed (`tools/freeze_v1.py`)

- `V1_MANIFEST.json`: sha256 `665b326a024d295f727cd5648ffc7e0d375b9300584871f238c6bfa48edd2e2d`, 209091 bytes; `scenarios/V1_MANIFEST.json` (committed)
- `V1_MANIFEST_PRIVATE.json`: sha256 `14ca1fff3af778a81d43f90e70a14cb7b56d6ebf5474648514169e8c2d376efe`, 82213 bytes; `$TERRAPRESERVE_PRIVATE` (withheld)
- `V1_MANIFEST.sha256`: sha256 `5e2369f44274cd6345d54c50ff4717a54cda742d5255e6901000f65d643ba1e2`, 174 bytes; `scenarios/V1_MANIFEST.sha256` (committed)
- `oracle-evidence-dev-v1.0.tar.gz`: sha256 `a3932458bab67d5fa0d4dacbe94be7bf2628c0d36edaf4542be65d539aa4d83f`, 100570 bytes; 272 run records; kept outside the repository in `~/.terrapreserve-cache/v1.0/` for the Zenodo release
- `oracle-evidence-test-v1.0.tar.gz`: sha256 `b31c6f78f31bc70c7bf107e597bd58db7af4ff124efb3ac1f73429941cafedf3`, 46126 bytes; 122 run records; kept outside the repository in `$TERRAPRESERVE_PRIVATE/v1.0/` for the Zenodo release
