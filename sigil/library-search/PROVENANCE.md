# Library search provenance

Imported from [nxrobins/sigil](https://github.com/nxrobins/sigil) at commit
`976fd697ae2251207fc8e2a4479b45f9954638bf`. The eight `src/*.sigil` modules, `search.py`, API contract,
search contract and API card are unchanged from `library/programs/autoresearch` at that revision.
The single-candidate `run.py` wrapper is not imported; the clone entry point
is `../library_search.py`. README and this provenance are adapted for this
location, with freshly rebound metadata and a new root lock.

The original implementation remains `sigil/autoresearch.sigil`, SHA-256
`04b30dcb1498258ce66e210cab31cc1120bd5c957c6ea1c0592c40d13ccbd54b`.
Population policy, instruction meanings and the quadratic objective derive
from it. Binary64 reverse mode replaces Q16 dual numbers, and PCG replaces the
LCG. Historical random or numerical trajectory equivalence is not claimed.
The upstream implementation has independent synthetic PyTorch/C tests.

`../sigil-source.json` pins the public commit, nine dependency Git trees,
exact versions/content hashes and application files. Setup reads those Git
objects, not mutable working files, and refuses a different root lock.
The public provider revisions retain their preceding SIGIL implementation
bytes while giving them self-contained docs and new metadata identities.
Old locks and experiments are not silently migrated or overwritten.

Imported SIGIL work is MIT OR Apache-2.0, with license copies in the parent
directory. These are experimental source packages, not admitted registry
releases. The original training workflow remains unchanged.
