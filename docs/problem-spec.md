# Problem specification

## Audit status

`AUDIT_STATEMENT` completed on 2026-08-10. The target below agrees with the
1992 source's intended positive-integer sequence formulation and the current
maintained Problem 848 formulation. Source evidence and formulation caveats are
in `docs/source-audit.md`.

## Authoritative target

For every positive integer \(N\), let
\[
[N]=\{1,2,\ldots,N\},\qquad
A_7(N)=\{n\in[N]:n\equiv7\pmod{25}\}.
\]
If \(A\subseteq[N]\) and \(ab+1\) is not squarefree for every \(a,b\in A\),
including \(a=b\), then
\[
|A|\le |A_7(N)|.
\]

Equivalently, the hypothesis is
\[
\forall a,b\in A\;\exists p\text{ prime}:p^2\mid ab+1.
\]
The witness prime may depend on the pair.

## Definitions and exact conventions

- An integer \(m\ge1\) is squarefree when no prime square divides \(m\).
- The universal quantifier over \(a,b\) includes the diagonal. Consequently,
  each member \(a\in A\) must itself satisfy that \(a^2+1\) is not squarefree.
- The target is a cardinality bound. It does not assert uniqueness of the
  extremal set.
- The original and maintained problem asks for \(N\ge1\). A formal extension
  to \(N=0\) is permitted only if `[0]` is explicitly defined as empty and the
  extra case is proved trivially.
- Ordered versus unordered pairs makes no difference because the predicate is
  symmetric, but no distinct-pair restriction is permitted.

## Benchmark arithmetic and the second construction

For \(N=25q+r\), where \(0\le r<25\), define
\[
B_7(N)=|A_7(N)|=\left\lfloor\frac{N+18}{25}\right\rfloor
=q+\mathbf1_{r\ge7}.
\]
The other root of \(x^2\equiv-1\pmod{25}\) gives
\[
A_{18}(N)=\{n\in[N]:n\equiv18\pmod{25}\},\qquad
B_{18}(N)=\left\lfloor\frac{N+7}{25}\right\rfloor
=q+\mathbf1_{r\ge18}.
\]

Thus \(B_{18}(N)=B_7(N)\) exactly when
\[
r\in\{0,1,\ldots,6\}\cup\{18,19,\ldots,24\};
\]
for \(7\le r\le17\), \(B_{18}(N)=B_7(N)-1\). Both residue classes are
individually admissible because every same-class product plus one is divisible
by \(25\). Their union is not generally admissible: \(7\cdot18+1=127\) is
squarefree.

## Accepted equivalent finite graph formulation

Let \(G_N\) have vertex set
\[
V_N=\{a\in[N]:a^2+1\text{ is not squarefree}\}
\]
and an edge between distinct \(a,b\in V_N\) precisely when \(ab+1\) is not
squarefree. Then admissible sets are exactly cliques of \(G_N\), and the target
is
\[
\omega(G_N)\le B_7(N)\quad(N\ge1).
\]
Because \(A_7(N)\) is a clique of size \(B_7(N)\), the desired conclusion is
equivalently \(\omega(G_N)=B_7(N)\).

## Rejected variants

- “For sufficiently large \(N\)” is strictly weaker than the target.
- Quantifying only over distinct \(a,b\) is strictly weaker; the exact negative
  control in `docs/computation-spec.md` witnesses the difference.
- Replacing \([N]\) by `Finset.range N = {0,...,N-1}` is a fixed-\(N\) shift.
  A universal theorem may be shift-equivalent only after proving that \(0\)
  cannot occur and relating the two bounds explicitly.
- A classification of every equality case is stronger than required and must
  not be assumed in a proof of the cardinality bound.
