# Diagnostic execution status

Status reviewed on 13 August 2026. These are public execution records, not
proof-DAG promotions.

## Fresh all-N computation

The first fresh root run terminated externally inside ART-005 without a final
receipt and was rejected as `REPAIR_EXECUTION`. The second fresh, non-resumed
run completed all six stages in 8,487.79 seconds and ended with
`ALL-N COMPUTATIONAL CERTIFICATE PASSED`. A separately assigned referee
reconstructed its complete receipt chain and returned PASS. The canonical
receipt SHA-256 is
`222c5313ed2f287fc5d2d3ee3e2d96938571838635518f19ee1f433bf0a71009`.
`CD0` is proved; its execution provenance remains accurately labelled
`local-unattested`.

Public record: closed issue
[#1](https://github.com/dannyward630/erdos-848-proof/issues/1) and prerelease
[`v1.1.0-cd0`](https://github.com/dannyward630/erdos-848-proof/releases/tag/v1.1.0-cd0).

## Lean diagnostics

- Exact NTFS census, run
  [`31529016420`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31529016420):
  all 30,638 cached OLeans occupy 129,476,102,424 logical bytes and
  52,860,335,936 NTFS-allocated bytes.
- FL-014 source/cache mismatch, run
  [`31538242639`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31538242639):
  clean `ProblemCore.olean` differs from the authenticated release OLean.
  The published cache is therefore not a clean-build substitute.
- Two-module zero-project-OLean checkpoint pilot, run
  [`31541505450`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31541505450):
  both `ProblemCore` and dependent `SharpnessCore` passed. The pilot is a
  bounded mechanism test, not a 30,636-module source build, and promotes no
  formal node.
- Cache-backed trust-zero canary, run
  [`31707223170`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31707223170):
  all 75 cache shards and 30,638 OLean records authenticated, the exact target
  and nine Lake dependencies checked out, and `lake exe cache get` succeeded.
  It then failed closed before any Lean invocation because Lake listed the
  nonexistent `Cli/.lake/build/lib/lean` directory in `LEAN_PATH` and the
  wrapper treated every missing search entry as fatal. No canary receipt or
  PASS marker was emitted. The partial-log artifact is ID `9185290490`, ZIP
  SHA-256
  `62e35837a83061848c26abb6988ab047baa17157af4af8c781198c7f9a31437c`.
  Classification: `REPAIR_EXECUTION`. The reviewed
  source now omits nonexistent search entries from its explicit environment
  (they cannot resolve a module) while continuing to reject unsafe existing
  entries and audit every active namespace root. That repair passed local
  mutation controls but was deliberately not rerun.
- Full-source completion workflow: exact runtime binding, post-cache
  zero-project-OLean enforcement, canonical receipt validation, and negative
  controls independently passed review. The workflow is deliberately
  **unexecuted**.

Historical host, NTFS, checkpoint, and cache experiments are manual-only.
Ordinary pushes cannot allocate those Windows jobs.

## Remaining completion boundary

The maintainer has confirmed that no qualifying Windows host is available.
Completion still requires a clean source build of all 30,636 provider modules,
source-built root compilation, trust-zero replay, all 15 upstream plus four
root live axiom reports, exact dependency audit, clean reproduction, and an
independent final receipt review. Until then `LROOT`, `L1`, `L2`, `RCLEAN`,
`V0`, and protocol-level `P848` remain open.

This is an external formal-assurance boundary, not an uncovered positive
integer or a gap in the proved mathematical theorem `M0`. Public tracker:
issue [#2](https://github.com/dannyward630/erdos-848-proof/issues/2).
