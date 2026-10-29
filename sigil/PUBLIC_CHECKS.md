# Public-source integration checks

Local validation on 2026-10-28 for the public SIGIL source revision
`976fd697ae2251207fc8e2a4479b45f9954638bf`, available in
[SIGIL draft PR #7](https://github.com/nxrobins/sigil/pull/7).
This record supersedes the development pin for setup, while
[LOCAL_CHECKS.md](LOCAL_CHECKS.md) retains the earlier measurements separately.

## Source and build identity

The checkout used for the integration test was cloned from
`https://github.com/nxrobins/sigil.git`, on `codex/public-library-revisions`,
with no access to the private SIGIL repository required. Its HEAD matches the
full source pin. All nine dependency Git trees and seventeen application
file hashes match `sigil-source.json`. Bytes is `0.1.0-public.5`; the other
eight providers are `0.1.0-public.1`.

The solver-enabled CLI was built from that public source tree, using the
existing local toolchain and cached external Lean dependencies checked against
the lockfile. This was not a cold dependency rebuild or a full Lean proof run.
The executable's SHA-256 is
`786e2844c95397928381c67c305e24e1700cea80d2938f58da0813f178e4368d`.
This identifies the locally tested binary, not a portable executable pin.

Fresh setup in the actual autoresearch clone passed. The native checker
reported a fresh solver witness and artifact identity
`sha256:6faafd1e50f69e0055d6c2ae2f247a15661529881d20b2f3e421912a96a4583e`.
The application lock was retained, not silently regenerated during setup.

## Execution results

All nine tests passed in 662.551 seconds, with zero skips and ResourceWarning
promoted to error. Both native environment variables were set, and the source
checkout was a fresh clone of the public branch. The direct discrete and hybrid
runs each matched their interrupted/resumed final checkpoint byte for byte;
the hybrid CPU-exchange resume matched the same expected checkpoint.

Reproduce it from the autoresearch clone root:

```sh
SIGIL_INTEGRATION_CLI=/path/to/sigil SIGIL_SOURCE_CHECKOUT=/path/to/SIGIL python3 -W error::ResourceWarning sigil/test_library_search.py -v
```

Both variables must be set. The three native tests cover fresh dependency
materialization, both search arms, byte-identical interrupted/resumed
checkpoints, CPU exchange, missing revision, changed dependencies and
wrong/corrupt/existing-output refusal. The six unit tests cover consumer and
lock hashes, exact versions, canonical paths, symlink refusal, mandatory solver
witnesses, unchanged prior state and forbidden package/storage overrides.

Python lint, whitespace checks and relative documentation links pass. All
seventeen files in the preserved pre-upgrade application also match its old
source-pin hashes. No generated cache or experiment output is staged.

No PyTorch oracle was regenerated for this packaging change. The numerical
and search implementations remain unchanged from the upstream source; this
suite exercises the new public metadata and graph identities in real execution.

## Preserved state and limits

The previous application, pin, root lock and dependency cache were preserved
locally under the ignored `results/sigil-before-public-ccvd32kp/` directory.
Earlier search archives were not modified. The original standalone source and
Windows launcher are unchanged; `sigil/autoresearch.sigil` retains SHA-256
`04b30dcb1498258ce66e210cab31cc1120bd5c957c6ea1c0592c40d13ccbd54b`.

These are experimental source revisions, not admitted registry releases.
Hosted CI is intentionally skipped; no merge, branch-protection change,
admission bypass, resource-ceiling reduction or training-workflow change is
part of this delivery. The clone exposes file checkpoints and CPU exchange,
not the optional KV host, a GPU runner or LLM mutation. Proxy fitness does not
establish an improvement in model training.
