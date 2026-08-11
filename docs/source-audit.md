# Source audit

Status terms here mean only that the cited statement was inspected. They do not
certify a cited proof.

## Primary and maintained statements

| ID | Source | Exact claim inspected | Status | Stable evidence |
|---|---|---|---|---|
| SRC-001 | Paul Erdős, “Some of my favourite problems in various branches of combinatorics,” *Le Matematiche* XLVII (1992), Fasc. II, 231–240, Problem 23 on printed p. 239 | For a positive-integer sequence bounded by \(n\), asks whether the \(7\bmod25\) construction is maximal when every \(a_i a_j+1\) is nonsquarefree; no sufficiently-large qualifier appears | verified from official scan | <https://lematematiche.dmi.unict.it/index.php/lematematiche/article/view/587>; cached PDF SHA-256 `bbf669b3ef3885fffa50830845aa6633c1673476462fb0e6a6f67a37478d3ff9` |
| SRC-002 | Maintained Erdős Problems page 848 | States \(A\subseteq\{1,\ldots,N\}\), quantifies “for all \(a,b\in A\),” asks for maximum size, and separately reports Sawhney's sufficiently-large result | verified; live status rechecked 2026-08-11 | <https://www.erdosproblems.com/848>; inspected snapshot SHA-256 `dd32e3ca0adf2a9563fee03975c487e424aecff9fa7964cf53427a1e85ac5055` |
| SRC-003 | Maintained LaTeX statement | Machine-readable maintained statement corresponding to SRC-002 | verified | <https://www.erdosproblems.com/latex/848>; cached HTML SHA-256 `492d3c24fedcd794f7a6e5d2a4978640855d027fa0dce6659a5d21fc5fe22ba0` |
| SRC-004 | Maintained revision history | A 2025-10-20 version inserted “Let \(N\) be a large integer”; the current version removes it | verified | <https://www.erdosproblems.com/history/848>; cached HTML SHA-256 `74950ff91bf522133fe3447ae98a47a7114a354e11c68f3cccf6316ad87edd8d` |
| SRC-005 | Maintained discussion, especially posts 238, 1264, 4695, and 4700 | Records the original-scope correction, the \(7/18\) alternatives, and confirmation that the intended quantifier includes \(a=b\) | verified as discussion evidence | <https://www.erdosproblems.com/forum/thread/848>; cached HTML SHA-256 `efaeee6bd0ab9eef83e6a40753bca5a42650f2fa90d05fdf1e6174de46071a9e` |
| SRC-006 | Mehtaab Sawhney, “Problem 848” | Proposition 1.1 proves only existence of \(N_0\) such that the bound holds for \(N\ge N_0\); the note also describes large-\(N\) equality alternatives | statement and four-page note inspected; proof not yet independently certified | <https://www.math.columbia.edu/~msawhney/Problem_848.pdf>; cached PDF SHA-256 `112deb12350ea812e5a8e140f2df00b72d2a848c5dc0d2000de738e948e637ba` |
| SRC-007 | Nat Sothanaphan, “An Explicit Threshold in Erdős Problem #848,” 24 March 2026 | Theorem 1 proves the exact upper bound for every \(N\ge264000000000000000\) | theorem and all twelve pages independently audited; exact-rational numerical replay passed; printed Corollary 2 requires the admissibility hypothesis already present at every theorem call site | cached PDF SHA-256 `8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f`; canonical numerical-claims SHA-256 `4726814d80fc63353a77c18bac8691bc917efd5ef1c7dcf10a14aed03674b215` |
| SRC-008 | Denis Hanson, “On the Product of the Primes,” *Canadian Mathematical Bulletin* 15(1) (1972), 33–37 | For real \(x>1\), \(\pi(x)/(x/\log x)\) is maximized at \(x=113\), hence \(\pi(x)<1.25506x/\log x\) | first and last pages visually inspected; exact ART-005 use and range audited | <https://doi.org/10.4153/CMB-1972-007-7>; cached PDF SHA-256 `ba350b2ce48e0ddb0751d8a60bcfe310683bc88df4fcf1b6a91029297688689c` |

## Statement-resolution notes

The 1992 scan omits an explicit lower bound `1 <= a_1` while saying “integers.”
A literal all-integer reading is impossible: arbitrarily many negative integers
congruent to \(7\bmod25\) would remain at most \(n\). The maintained source
resolves the intended domain as positive integers in `[N]`.

The original source does not separately define squarefree. The standard
definition, the maintained page's diagonal deduction, and Sawhney's proof all
support the prime-square formulation in `docs/problem-spec.md`.

The current maintained label “DECIDABLE — Resolved up to a finite check” is a
status report, not a proof or certificate. No all-\(N\) conclusion is accepted
from that label.

The four maintained HTML responses include dynamic server fields. Their listed
digests authenticate the exact audit-time snapshots but are not expected to
match a later live download byte-for-byte. A fresh audit authenticates the URL
and access date, compares the mathematical statement/history/status, and keeps
new bytes separately. The PDF digests remain exact clean-retrieval gates.

## Formal and proof artifacts under audit

| ID | Artifact | Pinned revision / digest | Current audit status |
|---|---|---|---|
| ART-001 | `FormalConjectures/ErdosProblems/848.lean` | repository `9af1d7101d82b0c6ff5e6aab4151ca3786de15b1` | unproved (`sorry`); uses `Finset.range N`, so fixed-\(N\) documentation is shifted; universal shift equivalence still needs an explicit proof |
| ART-002 | Sawhney large-\(N\) Lean development (`erdos-banger`) | `48e9c1aeb13a6e075d78ecf42dc1f2839d5ff071` | pending clean build, theorem-interface, axiom, and dependency audit; cannot by itself cover all \(N\) |
| ART-003 | `sproutseeds/erdos-problems`, Problem 848 workspace | `b727b478b6e13b51e93beb45435fdd6e96b056c7` | explicitly incomplete; useful adversarial analysis and finite experiments only |
| ART-004 | `hjyuh/erdos` outsider-clique verifier | `78e2092cceef9e85595669417f582253c2dea3ad` | disputed; claimed handoff and competitor coverage require independent audit |
| ART-005 | `ipitchford/erdos-848-all-n` | `1afd7c722cae5ee7dd0fd1fde64427537394f749` | accepted as a complete computer-assisted mathematical proof at this pin after applying the local FL-013 actual-(N) normalization repair: statement, structural/rank/interval mathematics, 19-stage replay, exhaustive separately implemented finite checking, both batch-primality arguments, gapless coverage, and internal adversarial review passed; the certificate rows are unchanged and the separate ART-006 formal-completion gate remains open |
| ART-006 | `crabsatellite/erdos-848-squarefree-product` | `ede0151a35c86b6395cf67dd034811d22a92c7ba` | exact statement, noncircular proof-carrying certificate semantics, dependency graph, and static trust audit passed; clean build and live axiom replay are resource-blocked and therefore unverified |

## Explicit-threshold lineage

The following cached notes successively claim operational thresholds. The
first four remain evidence leads. The final \(2.64\cdot10^{17}\) note has now
passed a detailed independent audit as recorded in SRC-007.

| Claimed threshold | Cached SHA-256 |
|---:|---|
| \(\exp(1958)\) | `12506fc5c9d63c0ae9337d216917cfba0dbe8ac13dfb6eed062c3bb8ef5dddef` |
| \(\exp(1420)\) | `dba5e022533362affff3019a5ad8c806c6a08dd149b24c9808f4e6c235f91ca7` |
| \(7\cdot10^{17}\) | `a5d3f686e524d8e04e33dc87796db42c975949acaabcd73cb2a008b8c3409c66` |
| \(3.3\cdot10^{17}\) | `a9f1970fb84d8e4a92778f506b6f4be20cc4c26c80f0c3f086964cd81d5859a8` |
| \(2.64\cdot10^{17}\) | `8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f` (audited) |

The SRC-007 audit independently checked the CRT root count, squarefree
progression estimate, both progression corollaries, the directed Euler-product
bound, the diagonal/Pell estimate, all four residue cases, monotonicity at the
threshold, and the final strict-density-to-integer conversion. Prachar and
Hooley are background citations only; the note does not import a theorem from
either source. The exact statement defect and correction are recorded as
FL-007 in `docs/failed-lemmas.md`.

ART-005 uses SRC-008 only through the weaker exact-rational routine
`prime_count_upper`: it handles `x < 17` by the trivial bound \(\pi(x)\le x\),
and otherwise replaces \(\log x\) by the smaller rational quantity
\(\lfloor\log_2x\rfloor(2/3)\). Thus the strict analytic bound's hypothesis
`x > 1` is satisfied at every nontrivial call.

The lower-\(p=13\) transcript's generator and original verifier share a
seven-base Miller--Rabin routine. That routine is not accepted as an
independent citation. Instead, `computations/check_p13_factor_primality.py`
proves every authenticated factor prime by an exact sieve and batch
primorial-gcd argument. Its canonical receipt `cb67a19e...cfc64`, semantic
mutations, and a second full `gmpy2 2.2.1` / GMP 6.3.0 execution passed. This
removes both the optimized-witness record and any pseudoprime-bound paper from
the load-bearing source chain for that transcript.

Cached source files are intentionally ignored by Git. Their retrieval and hash
checks are documented in `sources/README.md` and `REPRODUCE.md`.
