# Library based autoresearch CPU search

This package is the runnable search application imported into the autoresearch
clone from the public nxrobins/sigil source revision. It imports nine reusable SIGIL libraries instead of
implementing its own numeric storage, reverse-mode gradients, update rollback,
random generator, byte copying and checkpoint encoding.

Use the clone's [setup and search guide](../README.md). The application and
Python transport are pinned by `../sigil-source.json`; the native root lock
pins exact package versions, content hashes and the compiler standard library.
Dependencies are materialized offline from the pinned SIGIL Git commit.

Both discrete and hybrid search use eight candidates, two elites, mutation and
crossover. Hybrid search fits eight constants with reverse-mode gradients.
Complete population, RNG, lineage, counters and history can be saved between
bounded native calls and restored into a fresh output directory. The CPU
evaluation exchange uses the same fitter through versioned messages.

The task is the bounded two-coordinate quadratic proxy, not model training.
This migration uses binary64 and PCG, not the original Q16 arithmetic and LCG.
The original `sigil/autoresearch.sigil` remains unchanged. Python transports
native requests and writes returned checkpoints; it does not evaluate, mutate,
fit, rank or construct search state.

The supported clone launcher exposes file checkpoints and CPU exchange only.
The upstream optional KV host is not installed here. No GPU, network worker,
LLM mutation operator or package admission is implied. Existing SIGIL checks
and execution limits remain in force; a fresh solver witness is required.

See [the native contract](API.md), [search protocol](SEARCH_API.md) and
[provenance](PROVENANCE.md). SIGIL licensing is retained in the parent directory.
