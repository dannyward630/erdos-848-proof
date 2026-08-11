# Handoff

## Current state

The exact source-faithful statement is fixed in `docs/problem-spec.md`: every
positive integer `N`, every ordered pair including `a=b`, and the exact
benchmark `B_7(N)=floor((N+18)/25)`. The final computer-assisted proof is in
`proof/final-proof.md` and `proof/final-proof.tex`.

The mathematical theorem is complete. Separately assigned internal
finite-promotion, detailed mathematical, and final statement/coverage auditors
all returned PASS. This is not a claim of external scholarly peer review. The
proved all-`N` chain is:

- `IP_FIN`: exact coloring through `N=100000006`, with every one of 4,000
  base endpoints and 3,996,000 compact transitions checked;
- `IP_LOWER`: all structural branches on `[100000000,10^9]`;
- `IP_LOW`: all structural branches on `[10^9,10^12]`;
- `IP_MIDDLE`: all structural branches on
  `[10^12,264000000000000000]`;
- `H0`: Sothanaphan's audited high theorem from
  `264000000000000000` onward;
- `F0`, `C0`, and `M0`: the exact gapless stitch and sharp equality; and
- `VM0`: independent review of the mathematical and computational chain.

The finite certificate is durable under
`computations/independent_check_finite_stream.cpp`, the Java product exporter,
the GMP finisher, the endpoint-401 mutator, and `scripts/independent_check.py`.
The canonical leaf receipt is
`certificates/finite-factor-leaves.json` (SHA-256 `4fc75b0e...aad6`), and the
full receipt is `certificates/finite-stream-replay-2026-08-10.md`. The
independent checker reconstructed 10,515,898 diagonal vertices and checked all
18,049,789 base plus 14,458,371 compact pair occurrences. Exact sieve and
primorial-gcd certification proves all 11,108,162 accepted terminal leaves
prime. The endpoint-401 corruption is rejected for the intended nonsquarefree
pair and is recorded as the counterexample to sampled checking in FL-011.

The previously missing root certificate deliverable now exists as
`certificates/all-n-manifest-v1.json` and `scripts/check_certificate.py`.
Strict manifest and checkpoint mutation controls pass, including nested-link
and interruption controls. Resumption is operational only because an unsigned
caller-writable checkpoint cannot attest execution provenance; a resumed chain
never prints the theorem-grade PASS. The complete fresh uninterrupted
six-stage root replay has not yet been captured, so `CD0` remains unverified
even though each underlying component has a separately checked receipt.

The structural and high-range proof is pinned to ART-005 revision
`1afd7c722cae5ee7dd0fd1fde64427537394f749`. Its 19-stage fresh-extraction
replay passed in 5,523.791 seconds. The exact range-ledger digest is
`b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1`.
The lower-`p=13` factor transcript has its own exact sieve/primorial-gcd
certificate, so the candidate's shared seven-base Miller--Rabin routine is not
load-bearing. ART-005 is accepted as a complete computer-assisted
mathematical proof at the pinned revision.

A second deep review found FL-013: the upstream Pell prose invalidly passed
from a $B^2$ absolute count to a normalized $B$ term, dropping $B/N$.
The repaired proof retains the actual $N$: $x,x+d\le N$ gives an absolute
bound $2\tau(|\Delta|)K(B)N^2/Y^2$; division by $N/25$ and only then
$N\le B$ gives the verifier's exact term. A separate review lane re-derived
this repair and found no gap. The correction is load-bearing for `R-PELL` and
`IP_MIDDLE` and changes no certificate row.

`docs/final-referee.md`, `docs/artifact-audit.md`, `docs/proof-ledger.md`, and
`docs/proof-dag.yaml` record the independent verdicts and exact separation
between mathematical proof and formal completion.

## Active classification

The mathematical theorem remains complete, but project completion now has two
explicit classifications. `REVISE_DECOMPOSITION` added root-certificate,
root-Lean, and clean-reproduction nodes omitted before DAG version 8. The known
formal build failure remains `REPAIR_EXECUTION`. No mathematical lemma,
certificate interval, or positive integer remains uncovered.

## Formal completion blocker

ART-006 revision `ede0151a35c86b6395cf67dd034811d22a92c7ba` has passed exact
statement, static trust-surface, acyclic import-closure, and noncircular
certificate-semantic audits. It has not passed the required clean source build,
trust-zero replay, live `#print axioms`, or final declaration-dependency audit.

This 16 GiB macOS host cannot safely run those stages:

- the unconditional provider cone has 30,636 modules and the publication
  closure has 30,638;
- the exact OLean cache expands to 129,476,102,424 bytes;
- required build assemblies exceed the allowed 8 GiB local process budget and
  the documented final ceiling is 32,768 MiB; and
- the unmodified direct-Lean kernel runner is Windows-only.

The tracked `lean/` entrypoint now supplies a literal positive-`N` theorem,
both sharp residue witnesses, a 19-endpoint axiom audit, an immutable source
lock, and a guarded Windows completion runner. Its source-lock/census audit
passes locally, but it is deliberately unverified until compiled. Therefore
`CD0`, `LROOT`, `L1`, `L2`, `RCLEAN`, `V0`, and the protocol target `P848`
remain open. These are assurance/execution blockers, not a counterexample or a
gap in `M0`.

## Exact next actions

1. Run `scripts/check_certificate.py` through all six stages from a fresh
   external work directory without `--resume` and retain the canonical receipt;
   resumed completion is operational only and cannot promote `CD0`.
2. Use a persistent Windows x86-64 host with 64 GiB RAM and at least 200 GiB
   free disk (300 GiB preferred) and run `lean/run_completion_gate.py` exactly
   as documented, without `lake update`.
3. Capture the clean-build logs, trust-zero theorem replay, all 15 upstream
   plus four root live `#print axioms` outputs, source census, and dependency
   report; verify that only `propext`, `Classical.choice`, and `Quot.sound`
   occur.
4. Run the corrected `REPRODUCE.md` success path from a clean checkout and
   promote `LROOT`, `L1`, `L2`, and `RCLEAN` only from authenticated receipts.
5. Assign fresh structural and detailed reviewers to the exact final commit
   and raw logs; only their PASS may promote `V0` and then `P848`.

Do not retry progressively larger Lean caps on this Mac, substitute the
published OLean cache for the required clean source build, or treat either
preflight-only mode as a completion receipt.

An unexecuted diagnostic-only checkpoint pilot is implemented on the isolated
`lean-host-diagnostic` development line. It defines a canonical source-bound
topological plan, strict byte-integrity segment receipts, a Windows builder
that begins with zero project OLeans and accepts only same-run content-checked
parent assets, and a two-job `ProblemCore -> SharpnessCore` workflow. Receipts
do not independently attest execution; the exact workflow run and logs supply
that provenance. Its local synthetic mutation suite passes. The Windows
workflow has not yet been run at this exact implementation, so it is not
execution evidence and changes no DAG status.

## Decisive pins

- Original PDF: `bbf669b3ef3885fffa50830845aa6633c1673476462fb0e6a6f67a37478d3ff9`.
- Sothanaphan PDF: `8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f`.
- Hanson PDF: `ba350b2ce48e0ddb0751d8a60bcfe310683bc88df4fcf1b6a91029297688689c`.
- Finite canonical receipt: `4fc75b0ed263df81c07c5997c915511351ea61fff085d3ac95159c524ca9aad6`.
- ART-005 range ledger: `b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1`.
- All external repository pins and clean-checkout commands are in
  `docs/source-audit.md` and `REPRODUCE.md`.
