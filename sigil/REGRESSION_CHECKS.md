# Regression workload integration checks

Local integration on 2026-10-28 adds `--workload regression` to the autoresearch
clone while retaining quadratic as the default. Both applications are pinned
to public SIGIL commit `ded373473fadedce69218cd161124ce403ea2db5`.
This record covers local validation. Hosted CI is intentionally skipped; no
admission change, branch-protection change or model-training modification is
included.

## Source and runtime identity

The new source pin contains seventeen quadratic and eighteen regression input
hashes. All match the local files. Both applications' SIGIL modules, transport,
contracts and API cards match their immutable upstream Git objects; the fixed
regression dataset does too. Regression's README and provenance are adapted to
this clone, with a new input inventory, manifest hashes and retained root lock.

All nine provider Git trees, exact versions and content hashes are unchanged.
The original quadratic application, root lock and generated cache retain their
bytes. Setup materializes dependencies from immutable Git objects into a fresh
temporary graph and refuses a different derived lock. Both actual clone
applications passed fresh solver verification:

- Quadratic artifact: `sha256:6faafd1e50f69e0055d6c2ae2f247a15661529881d20b2f3e421912a96a4583e`.
- Regression artifact: `sha256:81d750de45449994667e1297b5b2cc15e411eb3d63fd8319d2de458b53d2df90`.

The tested solver-enabled executable has SHA-256
`786e2844c95397928381c67c305e24e1700cea80d2938f58da0813f178e4368d`.
It is the previously built public compiler, reused because compiler and provider
sources are unchanged between the earlier pin and this revision. This was not
a fresh compiler build, full workspace/Lean run or new PyTorch oracle run.
The regression numerical implementation is unchanged from upstream.

## Integration test results

All seventeen tests passed with zero skips and ResourceWarning promoted to
error. The native source and executable variables were set. Tests ran in
separate local batches:

| Batch | Passed | Time |
| --- | --- | --- |
| Pin, selector and mandatory-check tests | 8 | 3.594 seconds |
| Quadratic native setup, search and resume | 3 | 663.869 seconds |
| Regression native setup, search, resume and refusal | 5 | 883.425 seconds |
| Corrupt checkpoint with a valid program identity | 1 | 29.025 seconds |

For each workload, discrete and hybrid uninterrupted searches matched their
five-transition interruption/resume checkpoints byte for byte. Hybrid CPU
exchange/resume matched the corresponding direct checkpoint. Regression tested
the full twelve-step horizon; quadratic retained its two-step workflow check.
Native regression summaries also matched MSE independently calculated from the
reported parameters and fixed observations.

Refusal checks cover cross-workload resumes in both directions, a foreign
checkpoint even with a valid regression sidecar, wrong dataset expectations,
changed dataset rows, over-limit steps, wrong seed/mode/job, existing output,
malformed checkpoints, source/lock/dependency drift and missing source commits.
The focused corruption test supplied a valid program sidecar and observed
native rejection without creating output or changing prior files. Fresh setup
and repeated setup preserved each retained lock and refused stale caches.

Python lint, whitespace checks, relative documentation links and all source,
metadata and preserved-state checks passed. The additional actual-clone run
below is retained separately from the temporary test directories.

## Actual clone search and resume

A hybrid run used seed 42, stream 54, one generation and twelve inner steps.
An uninterrupted run and a five-transition interruption followed by resume
produced byte-identical final checkpoints. The earlier partial directory's
files remained unchanged. Results are retained locally under
`results/sigil-regression-local-d0tri_rg/`, with `full`, `part` and `resumed`
directories. Both final checkpoints have SHA-256
`7e47fd3a452d7e333cba6bdfdcc464801151ba134170358a54b6469a86503f18`.

The complete run scored sixteen candidates in seventeen transitions, with
forty graph evaluations, twenty-four accepted fitting steps and zero rejected
steps. It reported slope `2.0984951477932623`, bias `0.9524349020185465`,
training MSE `0.11250566145041041` and validation MSE
`0.009704124864021734`. Validation observations are report-only, not a search
objective. These synthetic results do not establish improved model training.

## Preserved state and reproduction

The previous SIGIL integration, source pin, root lock and cache are retained in
the ignored `results/sigil-before-regression-pj2wawlg/` directory. All thirty-seven
files in the existing quadratic application/cache match that backup. Earlier
validation records, standalone SIGIL source and Windows launcher are unchanged.
`sigil/autoresearch.sigil` retains SHA-256
`04b30dcb1498258ce66e210cab31cc1120bd5c957c6ea1c0592c40d13ccbd54b`.

Reproduce the integration suite with an explicit solver-enabled executable and
a local checkout containing the pinned public commit:

```sh
SIGIL_INTEGRATION_CLI=/path/to/sigil SIGIL_SOURCE_CHECKOUT=/path/to/SIGIL python3 -W error::ResourceWarning sigil/test_library_search.py -v
```

The [usage guide](README.md) provides setup, workload selection and search/resume
commands. Use fresh output directories and retain identity sidecars. The clone
exposes file checkpoints and CPU exchange only, not KV, a GPU runner or an LLM
mutation service. Solver witnesses, capability checks, resource ceilings and
admission guards remain intact.
