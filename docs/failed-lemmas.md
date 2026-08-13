# Failed lemmas and approaches

## FL-001 — ascending greedy coloring is benchmark-optimal

- **Exact claim:** Ordering eligible vertices increasingly and greedily placing
  each into the first compatibility-graph independent color class always gives
  at most \(B_7(N)\) colors.
- **Smallest known exact counterexample:** \(N=43\). The heuristic produces
  `{7,18,38}`, `{32,41}`, `{43}` (three colors), while
  `{7,38,43}`, `{18,32,41}` is a proper two-coloring and \(B_7(43)=2\).
- **Verification method:** Exact integer square-divisor tests on every pair in
  each displayed class.
- **Impact:** The ascending heuristic cannot be used as a certificate generator
  without an independent validation of its output count. This does not refute
  the original conjecture.
- **Retry classification:** `AUDIT_COMPUTATION`.
- **Replacement direction:** Store an explicit coloring and validate every
  vertex assignment and every same-color nonedge; never infer soundness from
  the greedy rule.

## FL-002 — Python numeric equality enforces the JSON certificate schema

- **Exact claim:** Comparing parsed JSON values with expected Python integers
  is sufficient to ensure that vertices, endpoints, counts, and benchmarks are
  JSON integers and that canonical top-level key order is fixed.
- **Exact counterexamples:** Python treats `7.0 == 7` and `True == 1`; the first
  checker version also accepted a compact JSON object whose top-level keys were
  reordered. These malformed payloads could pass semantic equality checks when
  no expected digest was supplied.
- **Verification method:** Independent adversarial code review and direct
  mutated-payload tests.
- **Impact:** The pinned certificate remained sound because its strict bytes and
  SHA-256 were fixed, but the generic checker was not fail-closed as specified.
- **Retry classification:** `AUDIT_COMPUTATION`.
- **Replacement direction:** Resolved: the checker now enforces exact key order
  and `isinstance(x, int) and not isinstance(x, bool)` for every integer field;
  float, Boolean, and reordered-key mutations are mandatory negative controls.

## FL-003 — one fixed coloring is prefix-optimal by restriction

- **Exact claim:** A single proper coloring at a later endpoint can restrict to
  at most \(B_7(N)\) colors at every earlier critical endpoint.
- **Exact counterexample:** Optimality at \(N=31\) forces \(7\) and \(18\) to
  share the sole color. At \(N=56\), the two cliques `{7,32}` and `{18,43}`
  then force \(32\) and \(43\) to share the second color, but
  \(32\cdot43+1=1377=3^4\cdot17\), so that color is not independent.
- **Impact:** Finite extension must allow certified recolorings/root swaps; a
  single global coloring cannot supply the bridge.
- **Retry classification:** `REWRITE_APPROACH`.
- **Replacement direction:** Endpoint or transition certificates with every
  recoloring checked explicitly.

## FL-004 — diagonal witnesses always satisfy \(p^2\le N\)

- **Exact claim:** When enumerating diagonal outsiders \(a\le N\), it suffices
  to construct witness roots only for primes with \(p^2\le N\).
- **Exact counterexample:** \(a=515\) is outside the two mod-25 base classes and
  \(515^2+1=26\cdot101^2\). Thus at \(N=515\), its least diagonal witness has
  \(101^2>N\). The defective implementation omitted 17 outsiders by
  \(N=7600\) and 47 by \(N=100006\).
- **Impact:** Any diagonal census using that cutoff is incomplete.
- **Retry classification:** `DISPROVE_HELPER`.
- **Replacement direction:** Enumerate all \(p\le N\), equivalently all
  \(p^2\le N^2+1\), or factor every diagonal value exactly.

## FL-005 — a fixed finite offset menu always supplies a squarefree mate

- **Exact claim:** A bounded set of offsets between the \(7\) and \(18\bmod25\)
  progressions can support a universal translation matching.
- **Exact counterexample:** For offsets `{-1,0,1}`, take \(t=386003\) and
  \(Y_t=9650093\). The three proposed products are respectively divisible by
  \(49\), \(289\), and \(121\). The general finite-menu claim fails by choosing
  simple prime-square roots for each offset polynomial and applying CRT.
- **Impact:** Fixed-radius translation rules cannot prove the all-\(N\) bridge.
- **Retry classification:** `REWRITE_APPROACH`.
- **Replacement direction:** Adaptive matchings or interval-uniform density and
  rank bounds.

## FL-006 — finitely many fixed anchors obstruct every outsider

- **Exact claim:** A prescribed finite anchor list always contains an anchor
  whose product plus one with a diagonal outsider is squarefree.
- **Exact counterexample:** For anchors `7,32,57,82`,
  \(n=987046881800\) satisfies
  \(9\mid7n+1\), \(121\mid32n+1\), \(169\mid57n+1\),
  \(289\mid82n+1\), and \(841\mid n^2+1\), with \(n\equiv0\pmod{25}\).
  CRT gives the same obstruction for every fixed finite nonzero anchor list.
- **Impact:** A finite-anchor lift cannot close the infinite range.
- **Retry classification:** `REWRITE_APPROACH`.
- **Replacement direction:** Quantitative bounds whose anchor set grows or
  whose exceptional CRT classes are amortized.

## FL-007 — Sothanaphan Corollary 2 without admissibility

- **Exact claim as printed:** For arbitrary \(A\subseteq[N]\) and
  \(N\ge264000000000000000\), the outside part \(A^*\) obeys the displayed
  small diagonal-density bound.
- **Exact counterexamples:** At \(N=264000000000000000\), take \(A=[N]\).
  Then \(|A^*|/N=23/25\), while printed part (a) is less than
  `0.0271319548`. For printed part (b), take every odd integer in `[N]`; then
  \(A^*\) is odd and \(|A^*|/N=23/50\), while the displayed bound is less than
  `0.0145524774`. The proof uses \(\mu(a^2+1)=0\), which follows only when
  \(A\) is admissible.
- **Impact:** The standalone corollary is false, but the main theorem applies it
  only to admissible \(A\), so the corrected implication remains available.
- **Retry classification:** `AUDIT_STATEMENT`.
- **Replacement direction:** Add “assume \(A\) is admissible” to the corollary
  and require that hypothesis at every call site.

## FL-008 — the \(18\bmod25\) class is always extremal

- **Exact claim:** The truncated \(18\bmod25\) class always has the conjectured
  maximum size.
- **Smallest counterexample:** At \(N=7\), the \(18\)-class is empty while
  `{7}` is admissible, so the maximum is at least one.
- **Impact:** Equality classifications that ignore the exact tie residues are
  false; the cardinality target itself is unaffected.
- **Retry classification:** `AUDIT_STATEMENT`.
- **Replacement direction:** Use the exact tie table in
  `docs/problem-spec.md`.

## FL-009 — the eventual extremal value is exactly natural division \(N/25\)

- **Exact claim:** An axiomatized external formalization assumes the eventual
  maximum equals Lean natural-number division `N / 25`.
- **Counterexample family:** For every \(N=25k+7\), the admissible \(7\)-class
  has \(k+1\) members while `N / 25 = k`.
- **Impact:** The axiom is false and no theorem depending on it is evidence for
  Problem 848.
- **Retry classification:** `AUDIT_STATEMENT`.
- **Replacement direction:** Use \(\lfloor(N+18)/25\rfloor\).

## FL-010 — Euler-product density with accumulated \(O(P)\) endpoint error

- **Exact claim:** Exact inclusion-exclusion over \(k\) small prime-square
  progressions preserves the Euler-product main term while accumulating only
  an \(O(P)\) interval error.
- **Failure certificate:** The absolute endpoint errors sum as
  \(\sum_{\varnothing\ne S}2^{|S|}=3^k-1\), not linearly in the prime cutoff.
  Overlaps are real; for example
  \(3141^2+1=2\cdot101\cdot13^2\cdot17^2\).
- **Impact:** The proposed analytic handoff did not yield a finite overlap.
- **Retry classification:** `REVISE_DECOMPOSITION`.
- **Replacement direction:** Use a sound union bound for asymptotics and a
  separate structural/certificate bridge for the finite interval.

## FL-011 — sampled delta-stream checks certify every intermediate endpoint

- **Exact claim:** Checking the first 400 base endpoints, sampled compact
  transitions, and the final state suffices to certify the full finite coloring
  stream.
- **Exact counterexample:** In the base delta stream, change vertex `18` to
  color `15` at endpoint index `401`. The canonical member `382` is already in
  that class, and
  \[
  18\cdot382+1=6877=13\cdot23^2.
  \]
  Restore vertex `18` to its original color `306` at endpoint `402`. The final
  state is unchanged. Both the default sampled and `--factor-sampled` modes of
  the exploratory clean-room checker accept this stream; exhaustive `--full`
  rejects it with `endpoint pair is nonsquarefree`.
- **Impact:** Sampled pair checking cannot prove the finite endpoint theorem,
  even when every stream record and the final coloring shape are checked.
- **Retry classification:** `AUDIT_COMPUTATION`.
- **Replacement direction:** The durable verifier must expose only exhaustive
  endpoint and transition checking, with an exact checked-pair total and this
  intermediate-only mutation as a mandatory negative control.

## FL-012 — same-class products are divisible by $7^2+1=50$

- **Exact claim:** If $a,b\equiv7\pmod{25}$, then $50\mid ab+1$.
- **Smallest counterexample:** With $a=7$ and $b=32$,
  $ab+1=225$, which is divisible by $25$ but not by $50$.
- **Impact:** The first Markdown proof draft overstated the elementary lower
  bound. The required conclusion remains true because
  $ab+1\equiv7^2+1\equiv0\pmod{25}$.
- **Retry classification:** `REPAIR_EXECUTION`.
- **Replacement direction:** Use the congruence modulo $25$, never a
  divisibility claim by the representative integer $50$.

## FL-013 — the endpoint-square Pell count normalizes by dropping $B/N$

- **Exact claim:** From an absolute large-root bound
  $2\tau(|\Delta|)K(B)B^2/Y^2$, division by $M=N/25$ and the inequalities
  $N\ge A$, $N\le B$ give $50\tau(|\Delta|)K(B)B/Y^2$.
- **Exact failure:** Literal division gives
  $50\tau(|\Delta|)K(B)B^2/(NY^2)$; the factor $B/N$ cannot be discarded.
  For the scalar choices $B=2$, $N=1$, and
  $\tau(|\Delta|)K(B)/Y^2=1$, the former expression is $200$ while the
  claimed upper bound is $100$.
- **Impact:** This is a genuine gap in the prose of the pinned
  `P13_RANK_ENVELOPE.md`, but not in the verifier's numerical term. At the
  actual $N$, $x,x+d\le N$ gives $x(x+d)+1<2N^2$, so the absolute count is
  $2\tau(|\Delta|)K(B)N^2/Y^2$. Dividing by $N/25$ and only then using
  $N\le B$ gives exactly the verifier's bound
  $50\tau(|\Delta|)K(B)B/Y^2$.
- **Retry classification:** `REPAIR_EXECUTION`.
- **Replacement direction:** Retain the actual-$N$ square through
  normalization; use the interval endpoint only after cancellation.

## FL-014 — the published ART-006 OLean cache is byte-reproducible from the exact source builder

- **Exact claim:** Recompiling an authenticated ART-006 module at the pinned
  source and toolchain with the upstream builder's exact command produces the
  byte-identical OLean stored in release `v1.0.5-kernel`, so the release cache
  can serve as a content-addressed clean-build checkpoint.
- **Exact counterexample:** On Windows x86-64 with Lean `v4.30.0-rc2`, six
  compilations of `Erdos848/ProblemCore.lean` using
  `--trust=0 -q -M <cap> -D compiler.postponeCompile=true` at caps 6,144,
  12,288, 15,360, 24,576 twice, and 32,768 MiB all produced 95,616 bytes with
  SHA-256
  `e1455c5e0883259cc895c07681378570954d8e1fc7c6cbc22a9e162c1ea9635a`.
  The authenticated release OLean is 95,664 bytes with SHA-256
  `324f23465ac359c47291515bb3faaed5be7046341ad580bb46613eec81e47a4d`.
  The repeated 24,576-MiB outputs were byte-identical, so output-path drift
  does not explain the mismatch.
- **Verification method:** GitHub Actions run `31538242639` at diagnostic
  commit `d9aaedb7d80a950971bb59d44cd8dc073f986923`; canonical diagnostic receipt
  SHA-256
  `0a36d2d52679d694a579908b98f332d14bf08a07b169f62e81558a7cbceb3c72`.
- **Impact:** The published cache may support a separately labelled live
  trust-zero/axiom canary, but it cannot discharge `L1`, establish
  source-to-OLean correspondence, or replace a zero-project-OLean source
  build.
- **Retry classification:** `AUDIT_COMPUTATION`.
- **Replacement direction:** Use a genesis-anchored, hash-chained distributed
  source build in topological order; every project OLean must trace to an
  authenticated trust-zero compilation, followed by a full source-built
  finalizer and independent receipt review.

For each future entry, record the exact claim, smallest known exact counterexample, verification method, impact on the proof DAG, retry classification, and replacement direction.
