# Contributing

Corrections, independent replays, formal-verification receipts, and simpler
proofs are welcome. Because this repository makes a universal mathematical
claim, changes must preserve a stricter evidence boundary than an ordinary
software project.

Before opening a pull request:

1. Read `AGENTS.md`, `docs/problem-spec.md`, `docs/proof-dag.yaml`,
   `docs/proof-ledger.md`, `docs/failed-lemmas.md`, and
   `docs/computation-spec.md`.
2. State the exact claim being changed and whether the work is exploration,
   proof, structural verification, detailed verification, formalization, or
   computation.
3. Include deterministic reproduction commands and exact input/output hashes.
4. Add a negative control for every new certificate or checker contract.
5. Record a false load-bearing lemma, with its smallest known exact
   counterexample, in `docs/failed-lemmas.md`.
6. Do not promote a DAG or ledger node until an independent reviewer has
   checked it.

At minimum, retrieve and authenticate the Sothanaphan source exactly as shown
in the README's quick-check block, then run the quick public checks:

```sh
python3 -B computations/test_all_n_manifest.py
python3 -B computations/test_all_n_resume.py
python3 -B computations/check_prefix_certificate.py \
  certificates/prefix-10000.json \
  --expected-sha256 \
  693ce882fb3f3786caf8eb502dd0677f42a4ed687adaa71a613b27ad7ef49727
python3 -B computations/test_prefix_checker.py \
  certificates/prefix-10000.json
python3 -B computations/exhaustive_small_prefix.py --limit 100
```

For Lean changes, a successful source audit is not sufficient. Retain the
clean source-build logs, trust-zero replay, all final `#print axioms` reports,
and exact dependency audit described in `REPRODUCE.md`.

Please distinguish a mathematical defect from an execution or packaging
failure using the retry classifications in `AGENTS.md`. A useful report names
the affected claim, exact counterexample or failed command, dependency, and
the smallest sound next action.
