# Library based regression search

This application searches for a small optimizer program that fits slope and
bias to four fixed noisy observations. Its two validation observations are
report-only; fitting and ranking use training MSE and an instruction penalty.
It imports the same nine libraries as the quadratic search without changing
their versions or implementations.

Use the clone's [setup and search guide](../README.md) with
`--workload regression` for both setup and search. The default is two generations
and twelve inner steps; both discrete and hybrid arms are supported. File
checkpoints and CPU exchange preserve native search state across invocations.
Keep `program-identity.hex` with checkpoints when resuming, using the same
workload, configuration, mode and job ID. Output directories must be new.

[dataset.json](dataset.json) is fixed, hash-pinned and checked against native
bytes before any output is created. It is not an arbitrary-data input file.
Completed summaries report training/validation MSE, slope, bias and eight
candidate-constant gradients. Python only transports native requests, validates
identities and writes returned checkpoints; numerical work stays in SIGIL.

See [the native contract](API.md) and [provenance](PROVENANCE.md). This is an
experimental synthetic CPU workload, not an admitted package or evidence of
improved model training. No GPU, KV host or LLM mutation service is installed.
Existing solver, capability, resource and admission checks remain in force.
