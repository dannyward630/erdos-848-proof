# Lean completion entrypoint

`Erdos848Completion/Final.lean` restates the exact positive-`N`,
diagonal-inclusive source theorem and records both sharp residue constructions
without asserting uniqueness. `Erdos848Completion/PublicationAxiomAudit.lean`
prints the axiom closure of all 15 upstream publication endpoints and the four
root deliverable theorems.

The proof source is locked by `source-lock.json` to ART-006 revision
`ede0151a35c86b6395cf67dd034811d22a92c7ba`, Lean `v4.30.0-rc2`, and the
committed Lake dependency graph. The upstream checkout is retrieved under
`external/erdos-848-squarefree-product` by `REPRODUCE.md`; gigabytes of
generated source are not duplicated here.

`test_completion_gate.py` supplies bounded fail-closed controls for the lock,
live axiom parser, inherited `LEAN_PATH`, wrong-root/cache-shadowed project
OLeans, exact direct-import paths, and timed-out subprocess trees. The full
runner clears caller Lean paths, inventories the exact 30,636 provider OLeans,
uses a directly resolved pinned Lean executable, and accepts `Erdos848` and
`Erdos848Completion` modules only from their authenticated build roots.

## Status

**Unverified pending clean replay.** Source fidelity, import closure, and
certificate semantics have passed independent static audits, but this root
entrypoint does not turn those audits into a kernel result. There is no valid
receipt in `receipts/`, and `P848` remains open.

The full gate requires Windows x86-64, at least 64 GiB physical RAM, and at
least 200 GiB genuinely free storage. Run the guarded command documented in
`REPRODUCE.md`. A successful run must create an external receipt directory;
only after independent review may its canonical receipt be copied here and the
proof DAG be promoted.
