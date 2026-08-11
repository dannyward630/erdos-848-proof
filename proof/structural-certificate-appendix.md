# Structural-certificate appendix and verification challenge

This appendix extracts the proof obligations that are easiest to obscure in a
large computer-assisted interval argument. It is meant to be read with
[`final-proof.md`](final-proof.md), the exact semantics in
[`../docs/computation-spec.md`](../docs/computation-spec.md), and ART-005 at
immutable revision
[`1afd7c722cae5ee7dd0fd1fde64427537394f749`](https://github.com/ipitchford/erdos-848-all-n/tree/1afd7c722cae5ee7dd0fd1fde64427537394f749).

The purpose is not to replace the row tables or executable verifier. It is to
make clear which mathematical implications turn an accepted row into a theorem
for every integer in its declared interval. In particular, §8 repairs a real
normalization gap in the upstream prose without changing the computation.

## 1. Exact target and diagonal reduction

For $N\ge1$, an admissible set $A\subseteq[N]$ satisfies

$$
 \forall a,b\in A,\qquad ab+1\text{ is not squarefree},
$$

with $a=b$ included. The diagonal therefore puts every selected element in

$$
 D_N=\{a\le N:a^2+1\text{ is not squarefree}\}.
$$

The compatibility graph on $D_N$ joins distinct $a,b$ when $ab+1$ is
nonsquarefree. Admissible sets are exactly its cliques. A proper coloring with
$B_7(N)=\lfloor(N+18)/25\rfloor$ colors proves the upper bound.

Challenge: try to omit the diagonal or replace all witness primes by $5$.
The statement and every finite checker explicitly reject both changes.

## 2. Finite endpoint induction

The benchmark is constant and equal to $i$ on

$$
 25i-18\le N\le25i+6.
$$

It is therefore enough to certify an $i$-coloring at endpoint $25i+6$.
The base stream gives every state through endpoint $100006$; the compact
stream gives every later transition through $100000006$.

At a compact transition, the only bins that can change are the new bin, the
old bin involved in the optional $18\bmod25$ anchor swap, the new location of
that anchor, and bins receiving newly exposed outsiders. The certificate names
all of them. The independent checker refactors every same-color pair in every
changed bin. All other bins contain literally the same integers as before, so
their previously proved invariant persists.

The endpoint-401 mutation in `computations/mutate_finite_endpoint401.py`
demonstrates why sampling is insufficient: it introduces
$18\cdot382+1=13\cdot23^2$, repairs the later state, and leaves the final
state unchanged. The exhaustive checker rejects it at the affected endpoint.

## 3. Exact terminal-factor certification

For every accepted pair value, the independent finite checker:

1. factors by exact integer arithmetic;
2. verifies that the terminal multiset multiplies back to the original value;
3. rejects duplicate terminal factors; and
4. exports every terminal leaf used by an accepted cache entry.

Let $m=9999932500113877$ be the maximum leaf and
$L=\lfloor\sqrt m\rfloor=99999662$. An exact sieve proves every leaf at most
$L$ prime. If $P$ is the product of all larger leaves and $M$ the
primorial through $L$, exact GMP arithmetic gives $\gcd(P,M)=1$. A
composite larger leaf would have a prime divisor at most $L$, contradicting
that gcd. Thus the Miller–Rabin predicate used during splitting is not a
primality premise.

## 4. Exhaustive outsider split

The roots of $-1\pmod{25}$ are $7$ and $18$. An outsider is a member of
$D_N$ in neither principal class. Its least prime-square diagonal witness is
not $2$, not $5$, and is $1\pmod4$; hence it is $13$ or at least $17$.
Every admissible set therefore lies in exactly one of three branches:

1. no outsider;
2. globally least outsider witness $13$; or
3. globally least outsider witness at least $17$.

This is a partition, not a heuristic choice of a convenient witness.

## 5. Joint structural-rank lemma

Fix the globally least outsider witness $p$, let $T=A\cap W_{p,N}$, and
write $t=|T|$. For every $z\in T$, let $s_N(z)$ be the exact bipartite
independent-set cap on the two principal classes compatible with $z$, and
let $c_{>p,N}(z)$ count higher-witness outsiders compatible with that same
$z$. Both inequalities hold simultaneously for each fixed $z\in T$:

$$
 |A_{\rm principal}|\le s_N(z),\qquad
 |A_{>p}|\le c_{>p,N}(z).
$$

Consequently

$$
 |A|\le t+\min_{z\in T}\bigl(s_N(z)+c_{>p,N}(z)\bigr).
$$

If the ambient joint scores are sorted decreasingly as
$g^\downarrow(1),g^\downarrow(2),\ldots$, the minimum score in any
$t$-element subset is at most $g^\downarrow(t)$. Hence

$$
 |A|\le\max_t\bigl(t+g^\downarrow(t)\bigr).
$$

No step replaces a joint minimum by independently incompatible maxima.

## 6. Higher-outsider collisions and CRT cases

For a higher-witness outsider $w$, the diagonal prime $q$ satisfying
$q^2\mid w^2+1$ need not equal a prime $r$ satisfying
$r^2\mid zw+1$. The certificates split these cases.

- If $q=r$, subtracting the congruences forces
  $w\equiv z\pmod{q^2}$. This is the reciprocal-square collision term.
- If $q\ne r$, the verifier counts the two-prime CRT classes separately;
  it does not identify the two witnesses.

For the $p=13$ branch, excluding two principal classes modulo $25$ and
two diagonal-root classes modulo $13^2$ leaves the density

$$
 \frac{23}{25}\frac{167}{169}=\frac{3841}{4225}.
$$

The endpoint discrepancy $+9$ in a collision progression comes from one
raw progression, two mod-$25$ exclusions, two mod-$169$ exclusions, and
four intersections. The two-root $q\ne r$ count has the corresponding
$+18$ allowance.

## 7. Translated masks and population conservation

For the lower $p=13$ interval, the exact translated machinery uses masks for
compatibility with $z$, compatibility with $z+d$, and squarefreeness of
the translated pair. The Boolean identity

$$
 A+B-ABC
 =\mathbf1_{A\lor B}+\mathbf1_{A\land B\land\neg C}
$$

is applied pointwise. The mask generator sieves through the square root of the
largest actual value among $zx+1$, $z(x+d)+1$, and $x(x+d)+1$, rather
than stopping at prime squares below $N$.

Every translated exceptional anchor is removed from its ordinary selected-
factor block before being inserted as a singleton. The verifier checks that
the capacities of all resulting blocks sum to the exact census population.
Geometric rank compression assigns later ranks the score of the first rank in
their block; because scores decrease with rank, this only enlarges the upper
bound.

## 8. Generalized-Pell orbit bound and corrected normalization

For a translated pair, set

$$
 u=2x+d,\qquad \Delta=d^2-4.
$$

If $x(x+d)+1=m\ell^2$, then

$$
 u^2-4m\ell^2=\Delta.
$$

In $\mathbf Q(\sqrt m)$, the principal ideal generated by
$u+2\ell\sqrt m$ divides the ideal generated by $\Delta$. For each
rational prime power dividing $\Delta$, the exponent can be distributed
between conjugate prime ideals in at most $e+1$ ways; inert or ramified
primes do no worse. Thus there are at most
$\tau(|\Delta|)$ initial ideal classes/orbits.

Two totally positive generators of the same ideal differ by a totally
positive norm-one unit. A nontrivial such unit has integral trace at least
$3$, and therefore size at least
$(3+\sqrt5)/2>2$. Each orbit contributes at most
$K(B)=1+\lceil\log_2(4B)\rceil$ solutions in the interval. When $m$ is a
square, the separate factorization
$(u-2r\ell)(u+2r\ell)=\Delta$ gives no larger count.

The normalization must retain the actual $N$ until cancellation. Since
$x,x+d\le N$,

$$
 x(x+d)+1\le N^2+1<2N^2.
$$

For $\ell>Y$, this implies $m<2N^2/Y^2$, so the absolute count is at most

$$
 \frac{2\tau(|\Delta|)K(B)N^2}{Y^2}.
$$

Dividing by $M=N/25$ and then using $N\le B$ gives

$$
 \frac{50\tau(|\Delta|)K(B)N}{Y^2}
 \le\frac{50\tau(|\Delta|)K(B)B}{Y^2}.
$$

This is the verifier's term. The upstream note's direct passage from an
absolute $B^2$ count to the final $B$ term is invalid because it drops
$B/N$. The corrected actual-$N$ proof above is the load-bearing argument.

## 9. Interval-uniform row semantics

Every accepted row declares a closed interval $[A,B]$. Positive population,
collision, Pell, and endpoint-error terms are evaluated at endpoints that
uniformly maximize them. Subtractive gains are evaluated where they are
weakest. Translation remainders are maximized over the complete period modulo
$25$. All arithmetic is integer or exact rational.

The resulting upper bound is compared with $B_7(A)$. Since $B_7$ is
nondecreasing, one accepted row proves every integer in $[A,B]$, not merely
the two endpoints or a sample.

## 10. High range and the admissibility correction

Sothanaphan's explicit theorem covers
$N\ge264000000000000000$. Its printed Corollary 2 omits the hypothesis that
$A$ is admissible. The proof uses
$\mu(x^2+1)=0$ for $x\in A^*$, which follows from the diagonal condition
only for admissible $A$. The corrected corollary in `final-proof.md` includes
that hypothesis, and every use in the source theorem supplies it.

The exact numerical audit bounds the 23-class total errors by
$0.0019726958486\ldots$ and $0.0019726957985\ldots$, both strictly below
$0.001973$, uniformly from the stated threshold onward.

## 11. Exact interval stitch

The certified closed ranges are

$$
\begin{aligned}
 &[1,100000006],\\
 &[100000000,10^9],\\
 &[10^9,10^{12}],\\
 &[10^{12},264000000000000000],\\
 &[264000000000000000,\infty).
\end{aligned}
$$

The first two overlap and every later pair shares its endpoint. There is no
integer between certificate regimes.

## 12. Formal evidence is independent of the mathematical stitch

ART-006 is not a premise of the argument above. Its pinned endpoint is useful
independent evidence because it expands to the exact interval, ordered-pair,
diagonal-inclusive statement, and its certificate interfaces have separate
soundness theorems rather than fields containing the final conclusion.

This repository nevertheless keeps formal completion open until a clean
source build, trust-zero replay, live axiom reports, and exact dependency audit
are captured on the documented host. An upstream publication claim is not
silently promoted into a locally reproduced result.

## Suggested hostile-referee checks

The highest-value independent attacks are:

1. Re-derive the joint rank lemma without reading the implementation.
2. Try to construct a higher outsider missed by the $q=r$/$q\ne r$ split.
3. Recompute the $3841/4225$, $+9$, and $+18$ CRT terms.
4. Check translated-mask population conservation on a mutated singleton.
5. Re-derive the ideal-orbit count, including the square-$m$ branch.
6. Verify the actual-$N$ Pell normalization in §8.
7. Recompute the tight first $10^{12}$ block with independent rationals.
8. Run the endpoint-401 finite mutation and require its exact rejection.
9. Check the admissibility hypothesis at every use of high-range Corollary 2.
10. Rebuild ART-006 from clean source and compare the literal theorem and live
    axiom/dependency reports.

Any failure should be recorded with an exact counterexample or certificate,
its affected interval, and one of the retry classifications in `AGENTS.md`.
