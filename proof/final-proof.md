# A computer-assisted proof of Erdős Problem 848

Danny Ward, with computer-assisted research and verification using OpenAI
Codex. This public proof candidate is unrefereed; “independent” checks below
mean separately implemented or assigned internal project lanes, not external
scholarly peer review.

## Status and theorem

This document gives the complete mathematical argument, including the exact
meaning of its finite and interval certificates. The separate project
completion bar also asks for a clean replay of the independent Lean artifact;
that execution is identified in the assurance section and is not used as a
premise of this proof.

For a positive integer $N$, call $A\subseteq[N]=\{1,\ldots,N\}$
*admissible* if $ab+1$ is not squarefree for every ordered pair $a,b\in A$,
including $a=b$. Define $f(N)$ to be the maximum size of an admissible set and
put $B_7(N)=\lfloor(N+18)/25\rfloor$.

Theorem. For every positive integer $N$, $f(N)=B_7(N)$. The statement is
exactly the audited target in `docs/problem-spec.md`; it does not assert
uniqueness of an extremal set.

## 1. The sharp lower bound

Let $A_7(N)=\{a\in[N]:a\equiv7\pmod {25}\}$ and
$A_{18}(N)=\{a\in[N]:a\equiv18\pmod {25}\}$. For $a,b\in A_7(N)$,
$ab+1\equiv7^2+1=50\equiv0\pmod {25}$; this includes the diagonal.
Thus $A_7(N)$ is admissible. Writing $N=25q+r$,
$0\le r<25$, gives
$|A_7(N)|=q+\mathbf 1_{r\ge7}=\lfloor(N+18)/25\rfloor=B_7(N)$.
Therefore $f(N)\ge B_7(N)$ for all positive $N$.

## 2. Graph and coloring reduction

Put $D_N=\{a\in[N]:a^2+1\text{ is not squarefree}\}$. Let $G_N$ have
vertex set $D_N$, with an edge between distinct $a,b$ exactly when $ab+1$
is not squarefree. The diagonal-inclusive hypothesis first forces every
member of an admissible set into $D_N$; its distinct pairs are then exactly
the edges of a clique. Conversely every clique is admissible. Hence
admissible sets are precisely the cliques of $G_N$.

A proper coloring partitions $D_N$ into classes in which every distinct
product plus one is squarefree. Consequently $\chi(G_N)\le B_7(N)$ implies
$f(N)=\omega(G_N)\le B_7(N)$. It remains to produce this upper bound for
every $N$.

## 3. The exact finite theorem

For $i\ge1$, set $e_i=25i+6$. Then $B_7(N)=i$ throughout
$25i-18\le N\le25i+6$. Thus an $i$-coloring of $G_{e_i}$ restricts to
every prefix in that block. There are no diagonal-eligible vertices for
$1\le N\le6$, so the blocks starting at $i=1$ cover the entire positive
range.

### 3.1 Exact diagonal census

If a prime square divides $a^2+1$, then the prime is not $2$, is congruent
to $1\pmod4$, and is at most $a$, because $p^2\le a^2+1<(a+1)^2$.
For every prime $p\le100000006$ congruent to $1\pmod4$, the independent
checker obtains both roots of $x^2\equiv-1\pmod p$ by generic
Tonelli--Shanks and uniquely Hensel-lifts them modulo $p^2$. Marking both
root progressions therefore gives exactly all diagonal vertices through the
finite limit. The exact count is 10,515,898.

### 3.2 Endpoint certificate induction

At endpoint $e_i$, a certificate state consists of $i$ color bins. The base
stream gives complete update states for $1\le i\le4000$. At every one of
these endpoints, the checker requires every diagonal vertex to have a color
below $i$ and verifies every same-color pair.

The compact stream covers $4001\le i\le4000000$. Each step adds the new
canonical residues $7$ and $18\pmod{25}$, performs either no swap or one
old-bin swap of an 18-anchor, and places the complete list of newly exposed
diagonal outsiders. Every changed bin is recorded and all of its one or three
pair obligations are checked. Every unchanged bin retains the preceding
invariant. Induction therefore proves a proper $i$-coloring at every
endpoint; this is not endpoint sampling.

The exhaustive replay checked 4,915,348 base changes, all 18,049,789 base
same-color pair occurrences, 3,996,000 compact transitions, 1,379,312 swaps,
2,513,387 outsider placements, and all 14,458,371 compact affected-bin pair
occurrences.

### 3.3 Exact squarefreeness of every accepted pair

For each pair value, the independent checker performs small-prime division
and deterministic Brent splitting, checks that the terminal factors multiply
exactly back to the original integer, and rejects a repeated factor. A
Miller--Rabin predicate only proposes terminal leaves; every leaf used by an
accepted computation is exported. Cache hits reuse a computation whose
leaves were already exported.

There are 11,108,162 distinct leaves. Their maximum is
$m=9999932500113877$, so $L=\lfloor\sqrt m\rfloor=99999662$. An exact
sieve proves all 2,328,675 leaves at most $L$ prime. Let $M$ be the primorial
of all 5,761,441 primes at most $L$, and let $P$ be the product of the
8,779,487 larger leaves. Exact GMP arithmetic gives $\gcd(P,M)=1$.

If a larger leaf were composite, it would have a prime divisor at most its
square root and hence at most $L$; that divisor would divide both $P$ and
$M$, a contradiction. Every leaf is therefore prime. The product and
no-duplicate checks prove every accepted pair value squarefree.

The canonical finite receipt is `certificates/finite-factor-leaves.json`,
SHA-256
`4fc75b0ed263df81c07c5997c915511351ea61fff085d3ac95159c524ca9aad6`.
The complete replay receipt and trusted execution boundary are in
`certificates/finite-stream-replay-2026-08-10.md`.

It follows that $f(N)\le B_7(N)$ for every
$1\le N\le100000006$.

## 4. Exhaustive structural reduction

Fix a positive integer $N$. The roots of $x^2\equiv-1\pmod{25}$ are 7 and
18. Put
$O_N=D_N\setminus(A_7(N)\cup A_{18}(N))$ and call its elements
*outsiders*. For $z\in O_N$, let
$w(z)=\min\{p:p\text{ prime and }p^2\mid z^2+1\}$.
The prime 2 is impossible because $4\nmid z^2+1$, and witness 5 would put
$z$ in a principal class. Every remaining witness is 1 modulo 4. Hence
$w(z)$ is either 13 or at least 17.

For a possible least witness $p$, write
$W_{p,N}=\{z\in O_N:w(z)=p\}$ and
$U_{>p,N}=\bigcup_{q>p}W_{q,N}$, where the union is over primes $q$.
Fix $z\in W_{p,N}$. Let $L_{z,N}$ and $R_{z,N}$ be, respectively, the
elements of the 7 and 18 modulo 25
principal classes whose product plus one with $z$ is nonsquarefree. Form the
bipartite graph $H_{z,N}$ on $L_{z,N}\sqcup R_{z,N}$, joining
$x\in L_{z,N}$ to $y\in R_{z,N}$ precisely when $xy+1$ is squarefree. Put
$s_N(z)=|L_{z,N}|+|R_{z,N}|-\nu(H_{z,N})$, where $\nu$ is matching
number. By König's theorem, $s_N(z)$ is the largest independent-set size in
$H_{z,N}$.

Finally define
$c_{>p,N}(z)=|\{u\in U_{>p,N}:zu+1\text{ is nonsquarefree}\}|$ and
$g_{p,N}(z)=s_N(z)+c_{>p,N}(z)$.

### Structural rank lemma

Suppose an admissible set $A\subseteq[N]$ has globally least outsider witness
$p$. Let $T=A\cap W_{p,N}$ and $t=|T|\ge1$. For every $z\in T$, the
principal part $A\cap(A_7(N)\cup A_{18}(N))$ lies in
$L_{z,N}\cup R_{z,N}$ and is independent in $H_{z,N}$, so it has size at
most $s_N(z)$. Every member of $A\cap U_{>p,N}$ is counted by
$c_{>p,N}(z)$. Therefore
$|A|\le t+\min_{z\in T}g_{p,N}(z)$.

Order the values on $W_{p,N}$ decreasingly as
$g_{p,N}^\downarrow(1)\ge g_{p,N}^\downarrow(2)\ge\cdots$. Any
$t$-element set $T$ has minimum score at most $g_{p,N}^\downarrow(t)$, and
hence
$|A|\le\max_{1\le t\le|W_{p,N}|}(t+g_{p,N}^\downarrow(t))$.

This is exhaustive: an admissible set has no outsider, least outsider witness
13, or least outsider witness at least 17. The no-outsider case is the same
principal bipartite independent-set argument without a chosen outsider.

## 5. Exact structural interval certificates

Each structural certificate row is a closed interval $[A,B]$. The verifier
bounds every population, collision burden, Pell tail, and other positive term
uniformly at its worst valid endpoint, evaluates every subtractive gain at its
weakest valid endpoint, maximizes every translation remainder over the complete
25-periodic cycle, and compares the resulting integer or exact rational with
$B_7(A)$. Since $B_7$ is nondecreasing, an accepted row proves every integer
in the row, not only the endpoints.

The mathematical envelope inputs were audited independently of their
implementation:

- the root and least-witness censuses are exact residue-class counts;
- CRT intersections are counted with their exact moduli and conservative
  endpoint discrepancies;
- the $p=17$ orientation cap, the $p\ge29$ domination bound, and the
  no-outsider two-degree bound cover all non-13 branches;
- the generalized-Pell tail follows by grouping solutions into ideals of norm
  dividing the fixed discriminant; two generators in one ideal differ by a
  totally positive norm-one unit, whose trace is at least 3, so successive
  positive solutions grow by more than $(3+\sqrt5)/2>2$;
- the rank merge is exactly the decreasing-order statistic inequality proved
  above; and
- every use of the prime-count estimate satisfies its range hypothesis. The
  imported bound is Hanson's strict $\pi(x)<1.25506x/\log x$ for $x>1$;
  the verifier uses a weaker exact-rational lower bound for the logarithm and
  a trivial count below 17.

The normalization of the generalized-Pell large-root tail deserves an
explicit correction to the wording in the pinned `P13_RANK_ENVELOPE.md`.
For a translated pair $x,x+d\in[N]$, put $\Delta=d^2-4$. If

$$
 x(x+d)+1=m\ell^2,\qquad \ell>Y,
$$

then $x(x+d)+1\le N^2+1<2N^2$, and therefore
$m<2N^2/Y^2$. For each fixed $m$, the ideal-orbit argument above gives at
most $\tau(|\Delta|)K(B)$ solutions, where
$K(B)=1+\lceil\log_2(4B)\rceil$. Thus the absolute large-root count at the
actual $N$ is at most

$$
 \frac{2\tau(|\Delta|)K(B)N^2}{Y^2}.
$$

Normalizing by the principal-class scale $M=N/25$ gives

$$
 \frac{2\tau(|\Delta|)K(B)N^2/Y^2}{N/25}
 =\frac{50\tau(|\Delta|)K(B)N}{Y^2}
 \le\frac{50\tau(|\Delta|)K(B)B}{Y^2}.
$$

This is exactly the term evaluated by the verifier. The upstream prose first
replaced $N^2$ by $B^2$ and then dropped the resulting factor $B/N$; that
displayed implication is invalid. The actual-$N$ derivation above repairs the
proof chain without changing a certificate row or computation. The failed
inference is retained as FL-013.

These lemmas turn each accepted row into a theorem for its closed interval.
The exact replay then certifies all three exhaustive branches on the following
cover:

| Closed range | Certificate evidence |
|---|---|
| $[10^8,10^9]$ | 37 lower-$p=13$ rows, digest `58498260302d6c45e2c965dc78843d0e6cea3722fee3e2d2829638c1143d2ab5`; $p=17$, $p\ge29$, and no-outsider digests `fcc0e45dc0c3a5b8c8935c93fe44f392bbef9fedfc22e2614510743fbbc11824`, `9a5e4c0db4dfe905c6c65ad107e79e3ad6c11711041e23b13a4a55fc570759bc`, and `6350904a63ab798a4b82262c807ec352dfff8645a142986bb664702c5bae6806` |
| $[10^9,10^{12}]$ | lower-$p=13$ digest `8e91da4b5ea840cd4f2a4c7cbbed0b6aad4e8b95ab8cf7ffc64f830b19f39c02`; other-branch digests `d5674d768789cc8d9fe9c931675be3c753f096306ba3bda9d624c1cc0f66dbe9` and `94fc3028544b36c6286f550045731893e146ffa1a2fb0c6911d38f5251e713b6` |
| $[10^{12},264000000000000000]$ | 1,255 exact-rational blocks, digests `cb6be132fad245b9a7c7658100bc5db6513b617be41e6b0966ec4b632a96be42` and `0897900002f65c1deb63612cca1f0e984e5fd37ad71b8686af7505de14d7134d` |

The load-bearing formulas, endpoint choices, and row soundness derivations are
given in the ART-005 notes at exact revision
`1afd7c722cae5ee7dd0fd1fde64427537394f749`:
[`P13_INTERVAL_100M_1B.md`](https://github.com/ipitchford/erdos-848-all-n/blob/1afd7c722cae5ee7dd0fd1fde64427537394f749/proofs/P13_INTERVAL_100M_1B.md),
[`P17_EXACT_HYBRID.md`](https://github.com/ipitchford/erdos-848-all-n/blob/1afd7c722cae5ee7dd0fd1fde64427537394f749/proofs/P17_EXACT_HYBRID.md),
[`P13_DIRECT_RESIDUAL.md`](https://github.com/ipitchford/erdos-848-all-n/blob/1afd7c722cae5ee7dd0fd1fde64427537394f749/proofs/P13_DIRECT_RESIDUAL.md),
[`LOW_RANGE_DIRECT_ENVELOPES.md`](https://github.com/ipitchford/erdos-848-all-n/blob/1afd7c722cae5ee7dd0fd1fde64427537394f749/proofs/LOW_RANGE_DIRECT_ENVELOPES.md),
[`P13_RANK_ENVELOPE.md`](https://github.com/ipitchford/erdos-848-all-n/blob/1afd7c722cae5ee7dd0fd1fde64427537394f749/proofs/P13_RANK_ENVELOPE.md), and
[`P17PLUS_AND_BASE_ENVELOPES.md`](https://github.com/ipitchford/erdos-848-all-n/blob/1afd7c722cae5ee7dd0fd1fde64427537394f749/proofs/P17PLUS_AND_BASE_ENVELOPES.md).
Their assembly and exact interval stitch are in
[`ALL_N_THEOREM.md`](https://github.com/ipitchford/erdos-848-all-n/blob/1afd7c722cae5ee7dd0fd1fde64427537394f749/proofs/ALL_N_THEOREM.md).
`REPRODUCE.md` materializes those same paths under the authenticated checkout.
The local [`structural-certificate-appendix.md`](structural-certificate-appendix.md)
extracts the main proof obligations and the corrected normalization in one
referee-oriented checklist.

The lower-$p=13$ transcript contains 1,439,686 exact factorizations and
8,373,490 factor occurrences. An independent parser authenticates both
compressed and raw bytes, checks every product back to $z^2+1$, and finds
1,357,591 distinct factors. An exact sieve through 54,392,469 proves all
small factors prime; the product of the larger factors has gcd 1 with the
primorial through that limit. Thus every claimed factor is prime and the
selected collision states are exact. The original shared Miller--Rabin
routine is not load-bearing.

The public release's 19-stage full replay regenerated the required censuses,
factor states, masks, rational rows, negative controls, sanitizers, and
postflight coverage in a fresh extraction. It passed in 5,523.791 seconds.
The exact receipt is
`certificates/ipitchford-all-n-replay-2026-08-10.md`. Together with the
structural rank lemma and the audited envelope inputs, these rows prove
$f(N)\le B_7(N)$ for every $100000000\le N\le264000000000000000$.

## 6. The explicit high range

Nat Sothanaphan's source-pinned theorem proves the same upper bound for every
$N\ge264000000000000000$. Its twelve-page analytic chain, four exhaustive
cases, endpoint constants, monotonicity reductions, and strict
density-to-integer conversion were independently checked. The exact-rational
claims digest is
`4726814d80fc63353a77c18bac8691bc917efd5ef1c7dcf10a14aed03674b215`.

For clarity, here is the corrected form of the note's misprinted intermediate
statement. Put

$$
C_{\mathrm{quad}}=1-
 \prod_{\substack{p\equiv1\pmod4\\p\ge13}}
 \left(1-\frac2{p^2}\right).
$$

**Corrected Corollary 2.** Let $N\ge264000000000000000$, let
$A\subseteq[N]$ be admissible, and put
$A^*=A\setminus(A_7(N)\cup A_{18}(N))$. Then

$$
 \frac{|A^*|}{N}\le \frac{23}{25}C_{\mathrm{quad}}+0.001973.
$$

If $A^*$ consists only of odd elements, then

$$
 \frac{|A^*|}{N}\le \frac{23}{50}C_{\mathrm{quad}}+0.001973.
$$

Indeed, admissibility applied to the diagonal pair $(x,x)$ gives
$\mu(x^2+1)=0$ for every $x\in A^*$. The set $A^*$ lies in the 23
nonprincipal residue classes modulo 25; in the odd case it lies in their 23
odd lifts modulo 50. Apply Proposition 2 of the note to each such class. If
$q$ is 25 or 50, respectively, and
$R=\lceil(259/200)N^{2/3}\rceil$, the sum of the main terms is at most
$23(N/q+1)C_{\mathrm{quad}}$. The exact monotonicity calculation in the pinned
numerical audit bounds the remaining normalized error per class by
$8.577\mathbin{\times}10^{-5}$ at the threshold and thereafter, while
$23C_{\mathrm{quad}}/N<3\mathbin{\times}10^{-18}$. Summing 23 classes and
rounding upward gives $0.001973$, proving both inequalities.

The note's printed Corollary 2 omits the admissibility hypothesis, as recorded
in FL-007. The displayed proof shows exactly where it is needed, and every use
in Theorem 1 supplies it. The corrected statement above is the one used here.

## 7. Gapless coverage and conclusion

The closed certified ranges are:

- $[1,100000006]$ by exact coloring;
- $[100000000,10^9]$ by the lower structural replay;
- $[10^9,10^{12}]$ by the low exact-rational replay;
- $[10^{12},264000000000000000]$ by the middle replay; and
- $[264000000000000000,\infty)$ by the explicit high theorem.

The first two overlap on $[100000000,100000006]$; each later pair shares its
displayed endpoint. Their union is every positive integer. The independently
replayed range-ledger digest is
`b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1`.

Therefore $f(N)\le B_7(N)$ for every positive integer $N$. Section 1 gives
the reverse inequality, so
$f(N)=\lfloor(N+18)/25\rfloor$ for every positive integer $N$.

## 8. Decisive external references

- Denis Hanson, “On the Product of the Primes,” *Canadian Mathematical
  Bulletin* 15(1) (1972), 33–37, proves the strict prime-count estimate used
  in Section 5 for every real $x>1$: <https://doi.org/10.4153/CMB-1972-007-7>.
  The audited cached PDF is `sources/cache/hanson-1972-product-primes.pdf`,
  SHA-256
  `ba350b2ce48e0ddb0751d8a60bcfe310683bc88df4fcf1b6a91029297688689c`.
- Nat Sothanaphan, “An Explicit Threshold in Erdős Problem #848,” 24 March
  2026, proves the upper bound used in Section 6 for every
  $N\ge264000000000000000$:
  <https://drive.usercontent.google.com/download?id=1ujhm4_WYpgRV_rd1rJXIfHyvx16COEKe&export=download&confirm=t>.
  The audited cached PDF is `sources/cache/sothanaphan-2.64e17.pdf`, SHA-256
  `8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f`.

The exact retrieval and authentication commands are in `REPRODUCE.md`.

## 9. Assurance boundary

This is a computer-assisted proof. Its decisive computations use exact
integer or rational arithmetic, authenticated certificate bytes, explicit
coverage, independently implemented finite checking, exact batch primality
certificates, and negative controls. Numerical evidence alone is nowhere used
as a proof.

The mathematical dependencies and their status are recorded in
`docs/proof-ledger.md`. Reproduction commands and decisive hashes are in
`REPRODUCE.md`; complete run identities and receipts are in `certificates/`.
The ART-005 mathematical proof does not depend on the separate ART-006 Lean
artifact. ART-006's own publication state reports a closed kernel theorem and
an axiom closure of `propext`, `Classical.choice`, and `Quot.sound`; our source
and interface audits found that report coherent and noncircular. That is strong
upstream evidence, but it is not the independent clean rebuild required by
this repository's protocol. Final project certification therefore remains
pending until a suitably provisioned Windows host builds the exact 30,636-
module provider from source, performs trust-zero replay, and captures the live
`#print axioms` and dependency audit. This distinction is a formal-assurance
boundary, not an uncovered integer or a gap in the argument above.

Research, implementation, and review provenance is recorded in
`PROVENANCE.md`.
