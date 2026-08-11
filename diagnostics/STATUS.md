# Diagnostic execution status

Status frozen at 2026-08-11 22:19 UTC. These are public execution records, not
proof-DAG promotions.

## Fresh all-N computation

The first fresh run terminated externally inside ART-005 without a final
receipt and was rejected as `REPAIR_EXECUTION`. The second fresh, non-resumed
run is active in a detached local session. Its prefix, lower-p13 primality,
exhaustive finite-stream, and high-numerics receipts have sealed; ART-005 is
active. `CD0` remains open until all six stages seal and an independent referee
validates the final receipt.

Public tracker: <https://github.com/dannyward630/erdos-848-proof/issues/1>.

## Lean diagnostics

- Exact NTFS census: run
  <https://github.com/dannyward630/erdos-848-proof/actions/runs/31529016420>.
  All 30,638 cached OLeans occupy 129,476,102,424 logical bytes and
  52,860,335,936 NTFS-allocated bytes.
- FL-014 source/cache mismatch: run
  <https://github.com/dannyward630/erdos-848-proof/actions/runs/31538242639>.
  The published cache is not a clean-build substitute.
- Hardened cache-backed trust-zero canary: run
  <https://github.com/dannyward630/erdos-848-proof/actions/runs/31540801403>.
  Even a pass cannot promote `L1`, `L2`, `RCLEAN`, `V0`, or `P848`.
- Two-module zero-project-OLean source-checkpoint pilot: replacement run
  <https://github.com/dannyward630/erdos-848-proof/actions/runs/31541505450>.
  `ProblemCore` has passed; the dependent `SharpnessCore` job is active.
  Its receipts are byte-integrity records, not independent execution
  attestations, and the experiment cannot promote a formal node.

Public tracker: <https://github.com/dannyward630/erdos-848-proof/issues/2>.
Draft diagnostic integration: <https://github.com/dannyward630/erdos-848-proof/pull/4>.

## Remaining completion boundary

Completion still requires a genesis-anchored clean source build of all 30,636
provider modules, source-built root compilation, trust-zero replay, all 15
upstream plus four root live axiom reports, exact dependency audit, clean
reproduction, and independent final receipt review. Until then `LROOT`, `L1`,
`L2`, `RCLEAN`, `V0`, and `P848` remain open.
