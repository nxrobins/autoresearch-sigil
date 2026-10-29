# Autoresearch clone integration checks

Historical development-run record. The current public pin and its separate
validation are recorded in [PUBLIC_CHECKS.md](PUBLIC_CHECKS.md); the results
below belong only to the earlier revision.

Validated locally on 2026-10-28. The clone now contains the library-based CPU
application, pinned to SIGIL commit
`10c7b58f8a8bc6311088374f1998f786eb291a71`. No commit, push or CI run was made
for this integration. Packages remain experimental and unadmitted.

## Application and dependency checks

All nine tests in `test_library_search.py` passed with both native environment
variables set, zero skips and ResourceWarning promoted to error, in 661.795
seconds. Tests created fresh temporary application roots; the delivered
application and test code were checked byte-for-byte against the tested files.
The three native tests exercised both search arms, interrupted/resumed equality,
CPU exchange, missing source revision and dependency drift. The six unit tests
covered file/lock pins, exact versions, symlinks and path traversal, mandatory
solver verification, state preservation and forbidden package/storage overrides.

Setup in the actual clone also passed with a fresh solver witness. Its lock
contains ten nodes: this application and nine dependencies. Bytes is pinned
to `0.1.0-dogfood.5`; the other eight libraries are `0.1.0-dogfood.1`.
Git tree identities, content hashes and seventeen application file hashes are
recorded in `sigil-source.json`. The existing root lock is never refreshed by
setup. A changed cached dependency was detected and left unchanged on refusal.

All eight SIGIL modules, the search driver, API contract, search protocol and
API card match the pinned upstream files. Only the clone-facing documentation
and its bound metadata were adapted; the single-candidate wrapper was omitted.
Python lint, whitespace and local documentation links passed.

## Retained run in this clone

The local sample is retained under the ignored directory
`results/sigil-library-20261028-d2po7a8x/` at the clone root. It uses seed 42,
stream 54, two generations, twenty task steps and the hybrid arm.

- `full/` completed 26 transitions, scoring 24 candidates with 60 graph
  evaluations, 9 accepted fitting steps and 27 rejected steps.
- `part/` stopped after transition 5; `resumed/` completed the same search.
- Final checkpoint files match byte for byte, and the interrupted checkpoint
  was preserved. Final checkpoint SHA-256:
  `19072e8cfe919838d782ae0cd11b5b28596176afc12ac2bd3eb2c8ab06f6ec88`.
- All 27 retained states match the pinned independent Torch/C trajectory for
  this configuration: structural fields exactly, floating fields within
  `1e-10` absolute/relative tolerance. Four planted mismatches demonstrated
  detection. This compared the existing oracle; it did not regenerate PyTorch
  results. Oracle SHA-256:
  `9e131635f1312abbc13873e3228624d574a61d5ae326f35c16c392107d2294ca`.

## Preserved state and limits

The original `autoresearch.sigil` remains unchanged, SHA-256
`04b30dcb1498258ce66e210cab31cc1120bd5c957c6ea1c0592c40d13ccbd54b`.
Its Windows launcher, training files and clone Git history are unchanged;
the SIGIL worktree remains clean. No admission guard, branch protection or
runtime ceiling was changed. No maintained library sources were duplicated
into this repository; generated dependencies live in the ignored cache.

The tested solver CLI has SHA-256
`e9d53800510c8a8608015c621a2a10fc8f3e4805a42775afab4e8cf0b2e6bb12`.
This uses the existing local toolchain, not a cold compiler rebuild. The
verified application artifact identity is
`sha256:f0605a9413e1d4ebf14b6320541a20822739a69a7743fadb0d54694f91ecbee7`.

This integration supports file checkpoints and the CPU exchange. The optional
KV host, GPU trials, remote-score authentication and LLM mutation are outside
this clone entry point. The quadratic proxy result is not a model-training
improvement claim. See [the usage guide](README.md) for reproduction commands.
