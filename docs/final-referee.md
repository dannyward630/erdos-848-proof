# Internal final referee record

Date: 11 August 2026.

## Scope

This record separates review of the mathematical computer-assisted proof from
the repository's additional Lean completion gate. The reviewed target is the
literal statement in `docs/problem-spec.md`: every positive integer `N`, every
ordered pair including `a=b`, and the exact benchmark
`floor((N + 18) / 25)`. The proof-construction lane did not certify its own
work.

“Independent” below means a separately assigned implementation or review lane
inside the multi-agent project; it is not a claim of outside peer review or
external scholarly acceptance. See `PROVENANCE.md`.

## Finite-certificate promotion review

- **Claim attempted:** `IP_FIN`, the exact upper bound for every
  `1 <= N <= 100000006`.
- **Exact result:** PASS. An independent referee rebuilt the current C++
  checker, replayed all 4,000 base endpoints and 3,996,000 compact
  transitions, regenerated the factor-leaf stream and both Java products,
  obtained exact GMP gcd 1 and injected-control gcd 2, reconstructed the
  canonical 704-byte receipt byte-for-byte, and observed the endpoint-401
  mutation fail for `endpoint pair is nonsquarefree` with no leaf output.
- **Proof and certificate locations:**
  `computations/independent_check_finite_stream.cpp`,
  `computations/CertifyLeavesExport.java`,
  `computations/gcd_finite_factor_products.py`,
  `computations/mutate_finite_endpoint401.py`,
  `scripts/independent_check.py`,
  `certificates/finite-factor-leaves.json`, and
  `certificates/finite-stream-replay-2026-08-10.md`.
- **Dependencies:** authenticated base and compact streams; complete
  endpoint/changed-bin induction; exact diagonal reconstruction; exact factor
  products and duplicate rejection; sieve and primorial-gcd leaf
  certification; ordinary compiler, zlib, Java `BigInteger`, CPython, gmpy2,
  and GMP execution.
- **Unresolved gap:** none for `IP_FIN`.
- **Discovered counterexample:** the endpoint-401 mutation refutes sampled
  endpoint checking, recorded as FL-011; it does not refute the exhaustive
  checker.
- **Recommended action:** promote `IP_FIN` only with the exact audited sources
  and receipts committed together.

## All-N mathematical review

- **Claim attempted:** `M0`, the source-faithful theorem for every positive
  integer `N`.
- **Exact result:** PASS. The independent final mathematical referee approved
  `IP_FIN`, `IP_LOWER`, `IP_LOW`, `IP_MIDDLE`, `F0`, `C0`, and `M0` for
  promotion. The reviewed proof establishes
  `f(N) = floor((N + 18) / 25)` for every `N >= 1`.
- **Proof locations:** `proof/final-proof.md`, `proof/final-proof.tex`,
  `certificates/ipitchford-all-n-replay-2026-08-10.md`, the finite receipt
  above, the lower-`p=13` batch-primality receipt, the pinned ART-005 proof
  notes, and the authenticated Hanson and Sothanaphan sources.
- **Dependencies:** the elementary residue-class lower construction; exact
  graph/coloring equivalence; `IP_FIN`; the least-witness structural rank
  reduction; exact closed-interval structural certificates; Hanson's
  prime-count estimate in its valid range; Sothanaphan's corrected
  admissible-set high theorem; and the exact gapless coverage ledger.
- **Unresolved mathematical gap:** none.
- **Discovered counterexample:** the draft sentence claiming divisibility by
  50 for every same-class pair is false at `(7,32)` because `7*32+1=225`.
  The proof needs only divisibility by 25; the manuscript is corrected and
  the failed claim is recorded as FL-012.
- **Post-review repair:** a later reviewer found FL-013 in the upstream
  generalized-Pell prose: normalizing an endpoint-square $B^2$ estimate
  illegally discarded $B/N$. The final proof instead uses
  $x,x+d\le N$, obtains the absolute bound
  $2\tau(|\Delta|)K(B)N^2/Y^2$, divides by $N/25$, and only then uses
  $N\le B$. A separately assigned review lane re-derived this implication,
  matched it to the verifier's exact `pair_tail_ratio` term, and found no
  counterexample. The certificate rows are unchanged.
- **Recommended action:** promote the mathematical nodes and keep formal
  completion separate.

## Final statement and reproduction audit

- **Claim attempted:** compare both final proof formats line-by-line with the
  authoritative statement, receipts, constants, hashes, and closed coverage.
- **Exact result:** PASS for statement and closed coverage; project-level clean
  reproduction remains unverified. Both formats quantify every positive `N`, include the
  diagonal, use the exact benchmark, and state the same five gapless ranges.
  Every displayed certificate identity agrees with the computation spec and
  receipts. The final Markdown SHA-256 is
  `781b04ab93da07e6eb87224b76f15f8841d61f58d03143e2c6d443ec5cd091d5`;
  the TeX SHA-256 is
  `49c4e10ca2343c49808060bd0ba5ae11792d467a7a88bdc54fbaa98d5b30a448`;
  and the compiled PDF SHA-256 is
  `00c9750f7312c2e735a4795f8ea555722ee4b37face8daefb50bb15b5a789c5a`.
  Tectonic 0.16.9 produced the five-page PDF; its only diagnostics were the
  expected first-pass cross-reference rerun notices, and the automatic second
  pass was clean. All five final pages were rendered and visually inspected
  after the link-style change.
- **Unresolved gap at that snapshot:** the original audit predated the required
  root `scripts/check_certificate.py` and `lean/` packaging. Those sources now
  exist. The fresh six-stage root replay has since passed independent review as
  recorded below; the clean Lean replay and complete clean-checkout success
  path remain open. The stale expected ART-006 missing-script line in
  `REPRODUCE.md` was corrected during the completion audit.
- **Discovered counterexamples:** none to the theorem; every documentation
  defect found during this audit was repaired before the PASS.

## Formal-completion review

- **Claim attempted:** complete ART-006's clean source build, trust-zero replay,
  live `#print axioms`, and declaration-dependency audit on this host.
- **Exact result:** `REPAIR_EXECUTION`. The unconditional provider cone has
  30,636 modules; the full publication closure has 30,638. The exact OLean
  cache expands to 129,476,102,424 bytes, required assemblies are documented
  above 8 GiB, and the unmodified direct-Lean gate is Windows-only. This
  16 GiB macOS host, now with only about 16 GiB free, cannot safely execute
  the gate.
- **Evidence locations:** `docs/lean-audit.md`, `docs/artifact-audit.md`, and
  the exact external-host commands in `REPRODUCE.md`.
- **Unresolved gap:** `L1`, `L2`, and therefore final combined review `V0`
  remain unverified. No formal proof defect or mathematical counterexample was
  found.
- **Recommended action:** use a persistent Windows x86-64 host with 64 GiB RAM
  and at least 200 GiB free disk, build serially at the pinned revisions, then
  capture trust-zero and all 15 upstream plus four root live axiom outputs.

## Promotion disposition

The mathematical theorem `M0`, its independent mathematical-review node
`VM0`, and the fresh root computational node `CD0` are proved. ART-005 is
accepted as the pinned computer-assisted mathematical proof. The repository
target `P848` remains open because the completion bar still requires a compiled
root Lean deliverable (`LROOT`), clean build and axiom nodes `L1` and `L2`,
clean-checkout reproduction (`RCLEAN`), and final combined review `V0`. No
integer interval or mathematical lemma remains uncovered.

## Completion-deliverable audit amendment

An independent 11 August completion audit classified the missing DAG/package
obligations as `REVISE_DECOMPOSITION` and the external Lean build as
`REPAIR_EXECUTION`. It confirmed that the earlier mathematical PASS did not by
itself establish the named root checker, root Lean entrypoint, or
clean-environment success. DAG version 8 introduced these separate nodes, and
version 9 records the later independent `CD0` promotion. The Lean sources must
still receive their execution-level adversarial review; this amendment is not
that future PASS.

The root checker now treats checkpoint resumption as operational recovery only.
Because local unsigned logs and receipts cannot attest that a command executed,
a resumed chain cannot emit the theorem-grade PASS or promote `CD0`; only one
fresh uninterrupted six-stage run can do so. Link, reparse-point, stale-partial,
unexpected-entry, and output-redirection controls fail closed.

## Root computational completion review

- **Claim attempted:** verify one fresh, uninterrupted, non-resumed execution
  of all six stages of `scripts/check_certificate.py` at the public source pin.
- **Exact result:** PASS. The run at public commit `cd4c728...d705d7` and
  ART-005 commit `1afd7c7...f749` ended with
  `ALL-N COMPUTATIONAL CERTIFICATE PASSED` after 8,487.79 seconds.
- **Certificate:**
  `certificates/all-n-computational-receipt-2026-08-11.json`, SHA-256
  `222c5313ed2f287fc5d2d3ee3e2d96938571838635518f19ee1f433bf0a71009`.
- **Independent verification:** a separately assigned referee reconstructed
  canonicality, all six stage fingerprints and receipt dependencies, every
  log/output hash, both clean Git identities, all 19 ART-005 substage results,
  the required negative controls, and gapless coverage. No real stage used
  resume; the only `RESUME` text was the mandatory fake-stage rejection test.
- **Provenance boundary:** the receipt says `local-unattested`; it is a
  cryptographically bound local execution record, not a signed third-party or
  CI attestation. This matches the declared `CD0` specification.
- **Disposition:** promote `CD0`. Do not promote any Lean or combined
  completion node from this result. Exact stage and raw-log identities are in
  `certificates/all-n-root-replay-2026-08-11.md`.

## Additional deep-review feedback and response

A further reviewer reported no mathematical flaw after independently checking
the exact statement and graph reduction, endpoint induction, finite-verifier
semantics, structural-rank lemma, collision/noncollision split, generalized
Pell bound, Lemma A, all outsider branches, interval monotonicity, one tight
middle-range row, and the ART-006 theorem interface. The reviewer explicitly
did **not** execute the full multi-hour release replay, reconstruct every line
of the high-range source, or independently rebuild Lean, so that feedback was
corroboration rather than a promotion decision. The later dedicated
root-replay referee promoted `CD0`; `L1`, `L2`, and `V0` remain outside both
reviews.

Three requested corrections/checks were resolved:

1. The Markdown diagonal census already restricted to primes
   `p congruent to 1 mod 4`; the TeX sentence did not. The TeX now states the
   same relevant-prime restriction as the code and proof.
2. Both proof formats now state and prove the corrected admissible-set form of
   Sothanaphan's Corollary 2, including the diagonal use, 23 residue classes,
   choice of `R`, and certified error sum. The exact source pages 8--9 were
   re-read from PDF SHA-256 `8162113a...796f` before the edit.
3. The assurance boundary now distinguishes ART-006's upstream-reported closed
   kernel theorem from the still-missing independent clean source rebuild. The
   two statements are therefore no longer presented as contradictory.

Two exact spot checks from the feedback were reproduced locally. At `N=5006`,
the generator and independent factor checker both give 526 diagonal vertices,
63,102 graph edges, and the endpoint target 200. For
`d=863167536`, direct integer arithmetic gives
`d^2-4 = 2^2*31*13922057*431583769`, all displayed odd factors prime,
`tau(d^2-4)=24`, `d mod 25=11`, and divisibility by `4,9,49,121`.
