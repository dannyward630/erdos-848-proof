# Lean host diagnostics

These programs investigate whether the pending ART-006 clean source build can
be executed on standard GitHub-hosted Windows machines.  They are diagnostics,
not proof receipts.  A successful diagnostic must not promote `LROOT`, `L1`,
`L2`, `RCLEAN`, `V0`, or `P848`.

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
segment's OLeans plus a canonical receipt.  The receipt binds the plan, source
pin, parent receipt hashes, source hashes, OLean hashes and lengths, compiler
flags, runtime, and zero-OLean genesis observation.

The manual `Lean source checkpoint pilot` workflow deliberately exercises only
this two-module chain:

```text
Erdos848.ProblemCore -> Erdos848.SharpnessCore
```

The child job starts from another fresh checkout and receives `ProblemCore`
only through the authenticated genesis artifact.  This demonstrates the
checkpoint mechanism; it does not build the 30,638-module publication closure,
compile the final root theorem, run the complete trust-zero replay, or print
the publication axioms.

Run the bounded local mutation suite with:

```sh
python3 -B diagnostics/test_lean_checkpoint_plan.py
```

The suite uses a synthetic two-module Git repository and rejects noncanonical
plans, Boolean indices, missing dependency edges, key reordering, source drift,
parent receipt substitution, a self-consistent counterfeit parent chain,
OLean mutation, unexpected files, symlinks, a missing parent, and a parent
attached to the genesis segment.
