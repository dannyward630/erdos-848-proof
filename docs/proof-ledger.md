# Proof ledger

## Proved

| ID | Claim | Proof / evidence | Dependencies |
|---|---|---|---|
| S0 | The exact target is the all-positive-\(N\), all-pairs (including diagonal) cardinality statement in `docs/problem-spec.md` | Original scan plus maintained statement/history/discussion, audited in `docs/source-audit.md` | SRC-001 through SRC-005 |
| E1 | \(B_7(N)=\lfloor(N+18)/25\rfloor\), and the corresponding formula for \(B_{18}\) and tie residues is exact | Write \(N=25q+r\) and count the representatives in the final partial block | S0 |
| E2 | \(A_7(N)\) and \(A_{18}(N)\) are individually admissible | If \(a,b\equiv7\) or both \(18\pmod{25}\), then \(ab+1\equiv0\pmod{25}\) | S0 |
| E3 | Admissible subsets of `[N]` are exactly cliques of the compatibility graph \(G_N\) defined in `docs/problem-spec.md` | Diagonal nonsquarefreeness selects vertices; the remaining pair conditions select edges | S0 |
| F-10K | \(\omega(G_N)=B_7(N)\) for every \(1\le N\le10{,}000\) | Pinned proper-coloring certificate `693ce882...49727`; modular generator; independent direct-factorization checker; third exhaustive oracle through 100; 12 malformed/semantic/coverage mutations; independent code review | E2, E3, `docs/computation-spec.md` |
| H-SOTH | The target upper bound holds for every \(N\ge264000000000000000\) | Independent twelve-page proof audit of SRC-007; exact-rational replay and self-tests; claims digest `4726814d...b215`; printed Corollary 2 corrected to admissible \(A\), exactly as used by Theorem 1 | S0, SRC-007, FL-007 |
| R-IP | The least-outsider-witness split, structural rank lemma, CRT collision estimate, generalized-Pell/ideal-orbit estimate, rank merging, and interval-uniform semantics used by ART-005 are valid | Separately assigned derivations; exact maximal-clique checks through 500; exact state/collision/Pell stress tests through 100,000; source-to-code review | S0, E3, ART-005 |
| R-PELL | The translated large-root tail has normalized bound $50\tau(|\Delta|)K(B)B/Y^2$ on a row $[A,B]$ | Since $x,x+d\le N$, first bound the absolute count by $2\tau(|\Delta|)K(B)N^2/Y^2$; divide by $N/25$, then use $N\le B$. The exact final manuscripts and verifier term were independently rechecked after FL-013. | R-IP, FL-013, ART-005 |
| P13-PRIME | Every claimed factor in ART-005's authenticated lower-\(p=13\) transcript is prime, and every row multiplies exactly to \(z^2+1\) | Canonical transcript parsing; exact sieve through 54,392,469; batch primorial gcd equal to 1; receipt `cb67a19e...cfc64`; independent source/mutation review and full GMP replay | ART-005, `docs/computation-spec.md` |
| IP-FIN | The target upper bound holds for every \(1\le N\le100000006\) | Exhaustive independent replay of all 4,000 base endpoints and 3,996,000 compact transitions; exact diagonal census; 11,108,162-leaf sieve/primorial-gcd certificate; endpoint-401 negative control; canonical receipt `4fc75b0e...aad6`; independent promotion referee PASS | S0, E2, E3, `certificates/finite-stream-replay-2026-08-10.md` |
| IP-LOWER | All three structural branches obey the target for every \(100000000\le N\le10^9\) | Exact 37-row least-13 replay plus exact \(p=17\), \(p\ge29\), and no-outsider certificates; all factor states independently certified; 19-stage release replay and mathematical referee PASS | R-IP, P13-PRIME, ART-005 |
| IP-LOW | All three structural branches obey the target for every \(10^9\le N\le10^{12}\) | Exact-rational short-shift envelopes, complete branch coverage, mutation controls, source-to-proof audit, and 19-stage replay | R-IP, ART-005 |
| IP-MIDDLE | All three structural branches obey the target for every \(10^{12}\le N\le264000000000000000\) | 1,255 exact-rational blocks with interval-uniform soundness, complete branch coverage, mutation controls, and 19-stage replay | R-IP, R-PELL, ART-005, SRC-008 |
| F0 | The target upper bound holds for every \(1\le N<264000000000000000\) | Union of IP-FIN, IP-LOWER, IP-LOW, and IP-MIDDLE, including the finite/structural overlap | IP-FIN, IP-LOWER, IP-LOW, IP-MIDDLE |
| C0 | F0 and H-SOTH cover every positive integer with no endpoint gap | Exact range-ledger replay, digest `b28760bc...ebe1`; overlaps/shared endpoints checked literally | F0, H-SOTH |
| M0 | For every positive integer \(N\), the maximum admissible cardinality is \(\lfloor(N+18)/25\rfloor\) | `proof/final-proof.md` and `.tex`; C0 gives the upper bound and E2/E1 give sharpness | C0, E1, E2 |
| VM0 | Separately assigned internal reviewers found no unresolved mathematical, statement, certificate, or coverage gap in M0 | Finite promotion, detailed mathematical, FL-013 repair, and final statement audits recorded in `docs/final-referee.md`; this is not external peer review | M0 |
| X-IP | ART-005 contains a complete all-\(N\) computer-assisted mathematical proof at revision `1afd7c7...f749` | Exact 19-stage replay, independent exhaustive finite checker and batch primality, structural review, final proof, and independent referees | M0, VM0, ART-005 |
| L-STMT | ART-006's final Lean endpoint is literally equivalent to the source-faithful upper-bound statement | Independent inspection of `ProblemCore`, `SharpnessCore`, `HallReduction`, final provider, and the 30,638-module acyclic import graph | S0, ART-006 |
| L-SEM | ART-006's five proof-carrying certificate families have noncircular semantic paths to the exact Hall/original statement | Independent trace of finite prefix, normal/twist masks, root rows, high QR, coverage, factor/prime trees, and the unbounded consumer; no field stores an ambient Hall, interval-close, or original theorem | L-STMT, ART-006 |

## Conditional

| ID | Claim | Condition not yet discharged | Impact |
|---|---|---|---|
| H-SAW | Sawhney's original note proves P848 for all sufficiently large \(N\) | Its proof was inspected but not independently certified line-by-line | Superseded for completion by the explicit proved node H-SOTH |

## Refuted

| ID | Claim | Exact counterexample | Classification |
|---|---|---|---|
| R-GREEDY-ASC | Ascending greedy independent-set coloring always uses at most \(B_7(N)\) colors | At \(N=43\), it uses three classes `{7,18,38}`, `{32,41}`, `{43}`, while two valid classes `{7,38,43}`, `{18,32,41}` exist and \(B_7(43)=2\) | `AUDIT_COMPUTATION` |
| R-PELL-B2 | Dividing the endpoint-square bound $2\tau K(B)B^2/Y^2$ by $N/25$ directly yields $50\tau K(B)B/Y^2$ | Literal division leaves the extra factor $B/N$; e.g. $B=2$, $N=1$, and $\tau K/Y^2=1$ give 200, not 100 | `REPAIR_EXECUTION` (FL-013) |

## Unverified

| ID | Claim | Dependencies | Verification needed |
|---|---|---|---|
| P848 | The source-faithful conjecture is completion-certified under every requirement in `AGENTS.md` | M0, VM0, CD0, LROOT, L1, L2, RCLEAN, V0 | Mathematical proof is complete; the root six-stage replay, clean ART-006 build, trust-zero/live-axiom/dependency audit, clean-checkout reproduction, and combined final review remain |
| X-CRAB | ART-006 contains a completed independently certified all-\(N\) Lean proof | Faithful source and theorem interface, formal certificate sources | Clean source build, live trust-zero replay, live axiom output, and independent certificate-semantic verification |
| CD0 | The tracked primary checker provides one fresh uninterrupted authenticated replay of every all-\(N\) computational stage and negative control | `certificates/all-n-manifest-v1.json`, `scripts/check_certificate.py`, proved component nodes | Static authentication plus manifest/checkpoint controls pass; run and retain a fresh six-stage theorem-grade receipt. Resumed checkpoint chains are operational only. |
| LROOT | The tracked literal positive-\(N\) Lean theorem and 19-endpoint root axiom audit compile against ART-006 | L-SEM, `lean/` | Source lock/census audit passes; compilation is part of the pending clean external replay |
| RCLEAN | `REPRODUCE.md` succeeds from a clean checkout for the complete mathematical, certificate, and Lean package | CD0, L2 | Execute the corrected success path and retain authenticated logs; the ART-006 missing-release-script diagnostic is intentionally not a passing gate |
