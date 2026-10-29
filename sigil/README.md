# Library based autoresearch in this clone

`library_search.py` runs two bounded CPU workloads using the same nine pinned
SIGIL libraries. Select `--workload regression` to fit a line to fixed noisy
observations, or `--workload quadratic` for the original two-coordinate proxy.
Omitting the selector keeps quadratic as the default. Neither requires Torch,
a GPU or network access at runtime.

The original `autoresearch.sigil` and Windows `run.cmd` remain unchanged as the
standalone Q16 reference. Application code lives in `library-search/src` and
`library-regression/src`; reusable libraries come from immutable Git objects.

## Setup

Use Python 3.10 or later on macOS or Linux, Git, a solver-enabled SIGIL CLI,
and a local public SIGIL checkout containing commit
`ded373473fadedce69218cd161124ce403ea2db5`. Commands below run from this clone's
root. The pinned source is on [public SIGIL draft PR #8](https://github.com/nxrobins/sigil/pull/8),
stacked above #7, not on `main`. Clone into a new directory:

```sh
git clone --single-branch --branch codex/public-autoresearch-regression https://github.com/nxrobins/sigil.git /path/to/SIGIL
git -C /path/to/SIGIL checkout --detach ded373473fadedce69218cd161124ce403ea2db5
```

Build the solver-enabled CLI using its
[public library workflow](https://github.com/nxrobins/sigil/blob/ded373473fadedce69218cd161124ce403ea2db5/library/WORKFLOW.md#build-the-compiler).
Set up each workload you want to run:

```sh
python3 sigil/library_search.py setup --workload quadratic --sigil-checkout /path/to/SIGIL --sigil /path/to/sigil
python3 sigil/library_search.py setup --workload regression --sigil-checkout /path/to/SIGIL --sigil /path/to/sigil
```

Setup reads the exact pinned commit even if the checkout has local edits or is
on another branch. It never fetches, resets or modifies that checkout. It
materializes dependencies in temporary storage, derives and compares the
selected application's retained root lock, and requires fresh solver
verification. Only its ignored `.sigil` cache is installed. Repeated setup
validates existing state without replacing it; drift refuses instead of being
silently repaired. Preserve an interrupted cache for inspection and use a fresh
copy if needed. Run setup and search sequentially in an owned local directory.

## Search and resume

This regression example stops after five transitions and resumes into a new
directory. Use the same workload and configuration on both commands:

```sh
mkdir -p results
python3 sigil/library_search.py search --workload regression --sigil /path/to/sigil --generations 1 --steps 12 --transitions 5 --out-dir results/regression-part
python3 sigil/library_search.py search --workload regression --sigil /path/to/sigil --generations 1 --steps 12 --resume results/regression-part/checkpoint-0005.json --out-dir results/regression-resumed
```

For an uninterrupted comparison, omit `--transitions` and `--resume` and choose
another output directory. Final checkpoints must match byte for byte. Earlier
files are never replaced. Replace `regression` with `quadratic` and choose new
directories to run the other workload; existing commands without a selector
still run quadratic.

Both workloads support `--arm hybrid` (default) and `--arm discrete`. Hybrid
also fits candidate constants. Defaults are seed 42 and stream 54, with these
workload-specific limits:

| Workload | Default generations | Default and maximum steps | Report |
| --- | --- | --- | --- |
| quadratic | 12 | 20 | Completion, checkpoint and search/fitting counters |
| regression | 2 | 12 | The same counters, dataset identity, training/validation MSE, slope, bias and eight candidate gradients |

Each one-generation search scores sixteen candidates in seventeen transitions.
Search is bounded to forty generations. Resume requires the same seed, stream,
generations, steps, arm and budget. Workloads cannot resume each other's state.

Regression's [dataset](library-regression/dataset.json) contains four training
and two validation observations. Validation is report-only: it does not guide
fitting or ranking. Dataset identity is
`028b1578cc66135645d790d76337e6f047c2ebd013e40f61dde1c68fde907b98`.
Optional `--dataset-sha256` asserts this identity; it does not select new data.
Changing data requires an explicit source/metadata/lock upgrade and a new
experiment. These synthetic CPU scores do not establish better model training.

## CPU evaluation exchange

Add `--evaluation exchange --job-id` with a chosen 32-byte lowercase hex ID
to either workload. Native SIGIL still scores candidates; Python transports
versioned requests and replies. Use the same mode and job ID on resume and
retain the checkpoint's sidecar: `evaluation-identity.hex` for quadratic
exchange, `program-identity.hex` for regression in both modes. Regression also
requires the same program identity for local resume.

The launcher exposes file checkpoints and CPU exchange, not an optional KV
host, GPU runner, remote worker or LLM mutation service. No Public storage opt-in
is needed. Scores are not authenticated. Existing solver, capability, resource
and admission checks remain; packages are experimental and unadmitted.

## Pins and explicit upgrades

`sigil-source.json` version 2 records the full public SIGIL commit, shared
dependency Git trees and exact versions/content hashes, plus separate input
inventories for each workload: seventeen quadratic files and eighteen
regression files, including both retained root locks. Search checks the selected
inventory and freshly verifies its package. No branch dependency floats and
`SIGIL_ALLOW_UNVERIFIED_CERT` is not passed through.

This upgrade preserves all quadratic application bytes, its lock and provider
versions. The quadratic provenance still identifies its original import commit;
that source is unchanged at the newer shared revision. Prior experiments stay
untouched. Do not assume checkpoints can migrate after a future code upgrade:
quadratic file mode checks schema/configuration, exchange also binds program
identity, and regression binds program identity in both modes.

Imported SIGIL code is MIT OR Apache-2.0; license copies are retained in
[LICENSE-SIGIL-MIT](LICENSE-SIGIL-MIT) and [LICENSE-SIGIL-APACHE](LICENSE-SIGIL-APACHE).
See [quadratic provenance](library-search/PROVENANCE.md) and
[regression provenance](library-regression/PROVENANCE.md).

## Local tests

```sh
SIGIL_INTEGRATION_CLI=/path/to/sigil SIGIL_SOURCE_CHECKOUT=/path/to/SIGIL python3 -W error::ResourceWarning sigil/test_library_search.py -v
```

With both variables set, the suite runs real setup, both search arms for both
workloads, interrupted/resumed equality, CPU exchange, and cross-workload,
wrong-configuration, corrupt-checkpoint, dataset and source/lock drift refusals.
Prior files are checked for preservation. Without both variables the nine
native tests skip; the unit-only run is not evidence of working search.
No CI workflow is added or run.

See [REGRESSION_CHECKS.md](REGRESSION_CHECKS.md) for this local integration.
The earlier single-workload results remain in [PUBLIC_CHECKS.md](PUBLIC_CHECKS.md)
and [LOCAL_CHECKS.md](LOCAL_CHECKS.md); they describe their recorded revisions.
