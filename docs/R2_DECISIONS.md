# R2 decisions: public release of TerraPreserve v1.0

Decisions for work package R2, the public release of TerraPreserve v1.0. Every decision below is written word for word as the work package gives it. TerraPreserve v1.0 (`terrapreserve-v1.0`, `27f0ee4`) stays frozen: no scenario file, label, oracle file or generator file changes, and every released test file is byte-identical to the frozen private copy.

## Decisions

- **R2-01: the test split is released.** The 128 test-split scenarios (96 targets, 32 reserves; the 6 excluded among them included, as frozen) and `V1_MANIFEST_PRIVATE.json` are added to the repository, byte for byte as frozen. DAIL's main run on this split is complete (DAIL `protocol-v1`, results in DAIL `docs/P10_RESULTS.md`), so withholding no longer protects a blind evaluation. From this release on, the test split is public: any later evaluation on it is not blind. The dataset version stays 1.0, because no content changes.

  Status: Decided (authors, 24 Nov 2026)

- **R2-02: what else is released.** The TP-L1 and TP-L2 oracle labels of the LLM candidates (dev and test), with the candidates' `.tf` files, so that the paper's LLM track can be checked. They live under `llm_candidates/`, in the layout that TP-L1 already uses for dev.

  Status: Decided (authors, 24 Nov 2026)

- **R2-03: what is not released.**
  - The private plan caches and the oracle's intermediate files.
  - The human-audit folder `audit/` (TP-V; no audit was performed; DAIL C-261).
  - The raw source archives (CLAUDE.md rule 6).

  Status: Decided (authors, 24 Nov 2026)

- **R2-04: the release tag.** After the merge, the authors tag the merge commit `terrapreserve-v1.0-public`. The tag `terrapreserve-v1.0` (`27f0ee4`) stays where it is: it marks the freeze.

  Status: Decided (authors, 24 Nov 2026)

- **R2-05: the datasheet answers given by the authors.**
  - **Maintenance:** the authors maintain the dataset.
  - **Contact:** through GitHub issues on the repository.
  - **Updates:** corrections are released as new versions (1.0.x for errata, 1.1 for new content), and old versions stay available through their tags and Zenodo.
  - **Contributions:** issues and pull requests, reviewed by the authors.
  - **Ethical review:** none was performed. The data are configuration files from public, permissively licensed repositories and synthetic templates, and contain no personal data about the authors or participants.
  - **Export controls:** none known.

  Status: Decided (authors, 24 Nov 2026)
