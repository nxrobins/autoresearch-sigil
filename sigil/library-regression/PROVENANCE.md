# Regression search provenance

Imported from [public SIGIL](https://github.com/nxrobins/sigil/tree/ded373473fadedce69218cd161124ce403ea2db5/library/programs/autoresearch-regression)
at commit `ded373473fadedce69218cd161124ce403ea2db5`. All nine SIGIL modules, `search.py`, `dataset.json`,
`API.md` and `api-card.json` are byte-identical to that revision.
README and this provenance are adapted for the clone; the source inventory,
manifest evidence hashes and root lock are rebound to those local documents.

The nine provider versions, content hashes and Git trees are unchanged from
the quadratic integration. `../sigil-source.json` records their shared public
commit and each application's file hashes. Setup reads immutable Git objects,
derives and compares the retained lock, and requires fresh solver verification.
The quadratic application's source, metadata, root lock and prior archives are
preserved. A workload change is a new experiment, not a checkpoint migration.

The upstream [PyTorch reference and tests](https://github.com/nxrobins/sigil/tree/ded373473fadedce69218cd161124ce403ea2db5/library/tests/fixtures/autoresearch-regression)
cover the regression numerics independently. The clone's integration tests
exercise selection, setup, native search, resume and refusal without Torch at
runtime. SIGIL source is MIT OR Apache-2.0; license copies are in the parent
directory. These are experimental source packages, not admitted releases.
