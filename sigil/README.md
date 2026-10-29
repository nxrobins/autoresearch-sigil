# Library based autoresearch in this clone

The library-backed CPU search is available through `library_search.py`.
Application code lives in `library-search/src`; reusable libraries come from
the pinned SIGIL revision. The original `autoresearch.sigil` and Windows
`run.cmd` remain unchanged as the standalone Q16 reference.

## Setup

Use Python 3.10 or later on macOS or Linux, Git, a solver-enabled SIGIL CLI,
and a local SIGIL checkout containing commit
`976fd697ae2251207fc8e2a4479b45f9954638bf` from the public [SIGIL repository](https://github.com/nxrobins/sigil).
The CPU search needs no Torch installation, GPU or network access.
This guide assumes commands run from the autoresearch clone root.

The source revision is currently on the public
[draft PR #7](https://github.com/nxrobins/sigil/pull/7), not on `main`.
For a new checkout, use a new destination directory:

```sh
git clone --single-branch --branch codex/public-library-revisions https://github.com/nxrobins/sigil.git /path/to/SIGIL
git -C /path/to/SIGIL checkout --detach 976fd697ae2251207fc8e2a4479b45f9954638bf
```

Build the solver-enabled CLI at that revision using its
[public library workflow](https://github.com/nxrobins/sigil/blob/976fd697ae2251207fc8e2a4479b45f9954638bf/library/WORKFLOW.md#build-the-compiler).
Then install and verify this application's pinned dependency cache:

```sh
python3 sigil/library_search.py setup --sigil-checkout /path/to/SIGIL --sigil /path/to/sigil
```

Setup reads the pinned Git objects even if the SIGIL checkout is on another
branch or has local edits. It never fetches, resets or modifies that checkout.
It derives the package graph in temporary storage, compares it with the
retained `library-search/sigil-package.lock.json`, and requires fresh solver
verification. Only the generated dependency cache is installed in
`library-search/.sigil`, which is ignored by Git.

Subsequent setup calls validate existing state without replacing it. Source,
lock or dependency drift refuses rather than being repaired or upgraded
silently. An interrupted setup can leave an incomplete cache; retain it for
inspection and set up a fresh copy of the application instead of overwriting
the old state. Run setup and search sequentially in an owned local directory.
The source pin is an integrity record, not publisher authentication.

## Search and resume

The following small hybrid run stops after five transitions, then resumes
with the same configuration into a new directory:

```sh
mkdir -p results
python3 sigil/library_search.py search --sigil /path/to/sigil --generations 1 --steps 2 --transitions 5 --out-dir results/sigil-part
python3 sigil/library_search.py search --sigil /path/to/sigil --generations 1 --steps 2 --resume results/sigil-part/checkpoint-0005.json --out-dir results/sigil-resumed
```

Each output directory must be new. To run uninterrupted, omit `--transitions` and `--resume`
and choose another output directory. The final checkpoint should match the
resumed run byte for byte. Earlier files are never replaced.

Both `--arm hybrid` (the default) and `--arm discrete` run native mutation,
crossover, ranking and selection. Hybrid also fits candidate constants.
Resume requires the original seed, stream, generations, steps, arm and budget;
defaults are seed 42, stream 54, twelve generations and twenty steps.
The one-generation/two-step commands above are a quick workflow check, not a
research-quality experiment. For the original task horizon, use `--steps 20`.

Each JSON summary reports completion, checkpoint path, scored candidates,
graph evaluations and accepted/rejected fitting steps. A complete one-generation
search scores sixteen candidates in seventeen transitions. The bounded search
supports up to forty generations; CPU scores concern a two-coordinate quadratic
proxy, not language-model training or transfer to real training results.

## CPU evaluation exchange

Add `--evaluation exchange --job-id` with a chosen 32-byte lowercase hex value
to use the versioned CPU request/response protocol. The same job ID and mode
must be supplied on resume, and the `evaluation-identity.hex` sidecar must stay
with its checkpoint. The driver records requests and replies alongside the
checkpoints; native SIGIL still performs the scoring. This is not a remote
worker or an authenticated score.

The clone launcher intentionally exposes file checkpoints and CPU exchange,
not the optional upstream KV host, GPU execution or an LLM mutation service.
No storage Public-import opt-in is needed for this file workflow. These
libraries remain experimental and unadmitted, and execution keeps existing
SIGIL capability, solver, resource and admission checks.

## Pins and explicit upgrades

`sigil-source.json` records the full SIGIL commit, nine dependency Git trees,
exact package versions/content hashes and all seventeen application input
hashes, including the retained root lock. Search validates those files and
freshly checks the package before running. There is no network lookup or
floating branch dependency. `SIGIL_ALLOW_UNVERIFIED_CERT` is not passed through.

An upgrade requires a deliberate update to the source pin, application inputs,
metadata and root lock, followed by the native regression suite below. Preserve
existing archives and start a new experiment on upgrade; do not assume old
checkpoints can migrate to changed code. The file workflow validates schema
and configuration; exchange mode additionally binds the program identity.

The imported SIGIL source is licensed MIT OR Apache-2.0; copies are retained
in [LICENSE-SIGIL-MIT](LICENSE-SIGIL-MIT) and
[LICENSE-SIGIL-APACHE](LICENSE-SIGIL-APACHE). See
[provenance](library-search/PROVENANCE.md) for the numerical migration boundary.

## Local tests

```sh
SIGIL_INTEGRATION_CLI=/path/to/sigil SIGIL_SOURCE_CHECKOUT=/path/to/SIGIL python3 -W error::ResourceWarning sigil/test_library_search.py -v
```

With both variables set, the suite executes fresh dependency setup, both
search arms, interrupted/resumed equality and CPU exchange. It also checks
wrong-configuration, corrupt-checkpoint, existing-output, source/lock drift,
missing-revision and solver-witness refusal, preserving prior state.
Without those variables, three native tests are explicitly skipped; that
smaller run does not establish working search. No CI workflow is added or run.
See [public-pin checks](PUBLIC_CHECKS.md) for this revision and
[earlier local checks](LOCAL_CHECKS.md) for the preserved development run.
