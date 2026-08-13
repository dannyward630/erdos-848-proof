# Lean host diagnostics

These programs investigate the resources, cache behavior, runtime provenance,
and checkpoint designs relevant to the pending ART-006 clean source build.
They are diagnostics, not proof receipts. A successful diagnostic must not
promote `LROOT`, `L1`, `L2`, `RCLEAN`, `V0`, or `P848`.

## Execution map

| Experiment | Exact result | Boundary |
|---|---|---|
| NTFS OLean census, run [`31529016420`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31529016420) | All 30,638 authenticated cached OLeans occupy 129,476,102,424 logical bytes and 52,860,335,936 NTFS-allocated bytes | Resource evidence only |
| ProblemCore source/cache pilot, run [`31538242639`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31538242639) | A clean source build and the release cache produce different OLean bytes; recorded as FL-014 | The cache cannot substitute for a clean source build |
| Two-module source checkpoint, run [`31541505450`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31541505450) | `ProblemCore -> SharpnessCore` built from zero project OLeans and its same-run byte receipts passed | Two modules only; the pilot is not safely scalable as written |
| Cache-backed trust-zero canary, run [`31707223170`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31707223170) | Authenticated every cache shard and dependency, then failed closed before Lean on a nonexistent Lake search-path entry; the bounded portability repair is locally tested but unexecuted | Uses published OLeans and can never discharge the clean-build nodes |
| Full-source completion workflow | Implementation and fail-closed receipt path independently reviewed | Unexecuted; requires the unavailable large Windows host |

The maintainer has confirmed that no qualifying Windows host is available.
Issue [#2](https://github.com/dannyward630/erdos-848-proof/issues/2)
therefore remains the public external-infrastructure boundary.

## Genesis-anchored source checkpoint pilot

`lean_checkpoint_plan.py` deterministically closes a selected ART-006 module
under local `Erdos848` imports, topologically orders that closure, divides it
into immutable segments, and binds the plan to the exact upstream revision,
root tree, Lean subtree, toolchain files, source bytes, and import headers.
Its JSON parser requires canonical bytes, exact key order, strict integer
types, exact dependency parents, and one assignment for every module.
The committed two-module plan is `lean-checkpoint-pilot-plan.json`, SHA-256
`6459fb1dd7094bbe4763d4b0350104e26408242dcc9a662641d85de0f2cd211c`;
the workflow regenerates it and requires byte-for-byte equality before either
build job starts.

`build_lean_checkpoint_segment.ps1` runs each segment in a distinct fresh
ART-006 checkout.  After downloading only the pinned third-party Mathlib cache,
it requires the project OLean inventory to be empty.  It then verifies and
imports exactly the source-built OLeans named by the plan's parent segments,
compiles the current sources with `--trust=0`, and emits only the current
segment's OLeans plus a canonical byte-integrity receipt.  The receipt binds
the plan, source pin, parent receipt hashes, source hashes, OLean hashes and
lengths, exact compiler flags, exact runtime identity, and the claimed
zero-OLean genesis observation.  A receipt does not by itself prove that its
bytes were produced by the workflow: execution provenance remains in the
exact GitHub run and logs.  The pilot therefore must not be used as a durable
or independently self-authenticating source-build certificate.

The manual `Lean source checkpoint pilot` workflow deliberately exercises only
this two-module chain:

```text
Erdos848.ProblemCore -> Erdos848.SharpnessCore
```

The child job starts from another fresh checkout and receives `ProblemCore`
only through the same-run, content-checked genesis artifact.  This exercises
the checkpoint mechanism; it does not build the 30,638-module publication closure,
compile the final root theorem, run the complete trust-zero replay, or print
the publication axioms.

Run the bounded local mutation suite with:

```sh
python3 -B diagnostics/test_lean_checkpoint_plan.py
```

The suite uses a synthetic two-module Git repository and rejects noncanonical
plans, Boolean indices, missing dependency edges, key reordering, source drift,
parent receipt substitution, a self-consistent counterfeit parent chain,
unaudited compiler/runtime metadata, OLean mutation, unexpected files,
symlinks, a missing parent, and a parent attached to the genesis segment.

## Reviewed full-source route

[`FULL_SOURCE_COMPLETION_ROUTE.md`](FULL_SOURCE_COMPLETION_ROUTE.md) and
`.github/workflows/art006-full-source-completion.yml` specify the only current
completion route: one isolated Windows x64 host with at least 64 GiB RAM and
200 GiB free SSD. The gate is bound to an exact authenticated Lean archive and
Lean/Lake executable hashes, rechecks zero project OLeans after cache
bootstrap, builds the entire provider from source, and emits a strictly
validated receipt for a second-job audit.

That workflow has not run. Its presence on the default branch is future
verification infrastructure, not a Lean theorem result. Historical diagnostic
workflows are manual-only to avoid spending hosted-runner resources on ordinary
documentation changes.
