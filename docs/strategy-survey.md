# Completion-strategy survey

This survey records mathematically distinct routes considered before accepting
any all-\(N\) proof architecture. Evidence from one route is not allowed to
silently certify another. The current favored route is a hybrid only because
its analytic, structural, and exact-certificate interfaces can be checked
separately.

## A. Explicitize analytic stability

**Idea.** Track every constant in the known sufficiently-large argument until
it yields an explicit integer threshold, then certify the entire lower range
separately.

**Result.** Successful for the high range. Independent review of Sothanaphan's
explicit note proves the target for every
\(N\ge264000000000000000\). Its progression, diagonal-density, Pell, and
four-case constants are exact. The printed Corollary 2 required an
admissibility hypothesis; every main-theorem use already has it.

**Remaining role.** Supplies H0 only. It cannot prove any smaller case without
an exact bridge.

## B. Sharpen the outsider mechanism

**Idea.** Split diagonal-eligible elements into the two principal
\(5^2\)-root classes and outsiders, label an outsider by its least prime-square
witness, and bound how a set of outsiders constrains the principal classes and
higher-witness outsiders.

**Result.** The exhaustive no-outsider / least witness 13 / least witness at
least 17 split is sound. For \(t\) outsiders of the least witness, the
order-statistic inequality

\[
|A|\le \max_t\bigl(t+g_p^\downarrow(t)\bigr)
\]

has been independently rederived and stress-tested. A fixed finite anchor
version is false by CRT (FL-006); the rank/envelope replacement avoids that
failure.

**Final role.** This is the mathematical reduction underlying ART-005's
structural intervals. The complete score and interval replay has passed.

## C. Compatibility-graph coloring

**Idea.** Use diagonal nonsquarefreeness to select vertices, join compatible
distinct pairs, and prove the clique upper bound by a proper coloring at every
critical constant-benchmark endpoint.

**Result.** Independently proved through \(N=100{,}000{,}006\). The durable
checker replays every one of 4,000 base endpoints and 3,996,000 compact
transitions, reconstructs the exact diagonal set, checks every affected pair,
and exports every accepted factor leaf for independent batch primality.
Ascending greedy is false already at \(N=43\) (FL-001), so only exhaustive
checked colorings, not a greedy theorem, are used.

**Final role.** Supplies the proved finite base `IP_FIN`.

## D. Residue-signature compression

**Idea.** Replace individual outsiders by finite signatures recording the
mandatory witness, selected small-prime factors, \(5\)-adic state, and bounded
collision data. Prove that each signature capacity is an upper bound for all
integers in the interval.

**Result.** ART-005's state-capacity formulas and selected/generic partition
passed independent semantic review, exact small-range census tests, and the
complete authenticated replay. The capacities deliberately count supersets.
The earlier claim that a fixed offset menu suffices is false by CRT (FL-005).

**Final role.** Compresses the proved large structural calculation to finite
rank rows.

## E. Direct interval certificates

**Idea.** Certify a closed interval \([A,B]\) by evaluating every positive
population, tail, and collision term conservatively at \(B\), every subtractive
gain at its weakest valid endpoint, and the benchmark at \(A\). Use complete
periodic endpoint cycles for translation remainders.

**Result.** The monotonicity and endpoint directions passed independent
mathematical review. Exact ART-005 certificates cover
\([10^8,10^9]\), \([10^9,10^{12}]\), and
\([10^{12},2.64\cdot10^{17}]\). The full exact-rational replay proves every
row inequality, and the gapless range ledger verifies their closed union.

**Final role.** Supplies the proved bridge between compact coloring and H0.

## F. Kernel-checked Hall/certificate assembly

**Idea.** Formalize the graph/Hall reduction and every finite and analytic
certificate consumer in Lean, then assemble a literal all-\(N\) theorem.

**Result.** ART-006 has a faithful, hypothesis-free endpoint, an acyclic
30,638-module source closure, no detected proof escape, and a noncircular
finite-certificate record. The paper/source gates pass. This host cannot yet
perform the required clean 32-GiB source build or 120.58-GiB cache replay, so
the route is not independently certified.

**Remaining role.** Strong independent formal route and eventual final
kernel-level assurance. It cannot currently replace the executable ART-005
bridge on this machine.

## G. Exact disproof search

**Idea.** Search directly for an admissible clique exceeding \(B_7(N)\), and
simultaneously seek the smallest counterexample to every proposed helper.

**Result.** No original counterexample was found through \(N=10{,}000\), with
an independent factor-exponent brute force through 200. Numerous false helper
claims were found and preserved in `docs/failed-lemmas.md`; those failures
materially changed the proof architecture.

**Remaining role.** Continue adversarially against every new structural or
certificate claim. An exact original counterexample overrides the affirmative
working hypothesis immediately.

## Selected hybrid and rejection rule

The completed mathematical proof uses A for H0, B for the exhaustive
reduction, C for the finite base, and D/E for the explicit finite bridge. F is
an independent formal candidate and the repository's remaining protocol gate,
not a premise of the mathematical proof. G remains available for adversarial
checking.

If the aggregate certificate replay or independent checker exposes an
encoding/coverage problem, classify D/E as `AUDIT_COMPUTATION` and stop using
the affected range. If the mathematical rank or interval bridge itself is
false, classify B or E as `REWRITE_APPROACH`; do not repeatedly patch it.
