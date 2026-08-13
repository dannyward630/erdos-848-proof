# Computation specification

## Mathematical object

For an exact upper bound at a fixed \(N\), construct the graph \(G_N\) from
`docs/problem-spec.md`:

1. include \(a\in[N]\) as a vertex iff some prime \(p\) satisfies
   \(p^2\mid a^2+1\);
2. for distinct vertices \(a,b\), include edge \(\{a,b\}\) iff some prime
   \(p\) satisfies \(p^2\mid ab+1\).

A proper coloring of \(G_N\) with at most \(B_7(N)\) colors proves
\(\omega(G_N)\le B_7(N)\). Together with the explicit clique \(A_7(N)\), it
proves equality.

## Exact adjacency generation

The primary generator may enumerate prime squares \(p^2\) and, for each
eligible \(a\), generate candidates using
\[
b\equiv-a^{-1}\pmod{p^2}.
\]
For a finite limit \(L\), primes \(p\le L\) suffice because
\(p^2\mid ab+1\le L^2+1\) implies \(p\le L\). All divisibility, inverses,
factorization, counts, and certificate fields must use exact integers.

## Prefix-block coverage

Since \(B_7(N)\) is constant on
\[
7+25t\le N\le31+25t,
\]
a proper coloring at the right endpoint restricts to a proper coloring of every
earlier prefix in that block. The initial range \(1\le N\le6\) must be checked
separately, and a truncated final block must explicitly record its actual end.
The coverage checker must verify the union of certified intervals equals the
claimed finite range with no gaps.

## Certificate schema (candidate v1)

Canonical ASCII JSON:

```text
{"limit":L,"vertices":[...],"records":[[endpoint,prefix_vertex_count,benchmark,color_vector],...]}
```

- `vertices` is the globally ordered eligible-vertex list through `L`.
- `color_vector` assigns each prefix vertex an integer color.
- A checker must reconstruct eligibility and adjacency, verify the prefix count,
  verify that all colors are in `[0, benchmark)`, and reject every same-color
  edge.
- Serialization is
  `json.dumps(payload, separators=(",", ":")).encode("ascii")` and the release
  must record byte length and SHA-256.

The committed certificate `certificates/prefix-10000.json` contains 1,048
vertices, 401 records, 696,999 canonical bytes, and SHA-256
`693ce882fb3f3786caf8eb502dd0677f42a4ed687adaa71a613b27ad7ef49727`.
Its modular generator reconstructed 251,854 compatibility edges. The
certificate has been regenerated bit-for-bit from committed code and accepted
by the independent direct-factorization checker. Independent code review is
recorded in the proof ledger.

## Independent checker requirement

Where practical, the second implementation must not share the modular adjacency
generator. It should determine nonsquarefreeness by direct trial division or
factor-exponent extraction from each exact value \(ab+1\). For a small prefix,
an exhaustive subset or independent maximum-clique calculation must agree with
the certified optimum.

For the committed prefix certificate:

- `computations/generate_prefix_certificate.py` uses a prime sieve and modular
  inverse classes modulo \(p^2\) to generate compatibility edges, followed by
  descending first-fit coloring.
- `computations/check_prefix_certificate.py` independently constructs primes by
  trial division, factors every diagonal value directly, validates exact block
  coverage and strict JSON types, and directly factors all 328,521 same-color
  pair values. It does not trust edge labels or modular witnesses from the
  generator.
- `computations/test_prefix_checker.py` runs the schema, semantic, and coverage
  mutation controls below.
- `computations/exhaustive_small_prefix.py` is a third deliberately naive
  implementation. It tests square divisors by scanning every integer divisor
  and exhausts every eligible subset for each \(1\le N\le100\).

## Required controls

- Reject `{1}` because \(1^2+1=2\) is squarefree.
- Reject `{7,18}` because \(7\cdot18+1=127\) is squarefree.
- Accept `{7,32,57}`; all products plus one are divisible by \(25\).
- Classify `50` as nonsquarefree with witness prime `5`.
- Classify `127` as squarefree.
- In a distinct-pairs-only test harness, accept
  `{19,33,35,46,53}` but reject it under the authoritative diagonal-inclusive
  predicate. This detects an accidental weakening of the statement.
- Mutated certificates must be rejected for at least: missing vertex, wrong
  prefix count, out-of-range color, same-color edge, altered endpoint, altered
  benchmark, and a gap in interval coverage.

## Lower-\(p=13\) factor-primality certificate

ART-005's lower-range replay consumes an authenticated factor transcript with
1,439,686 rows and 8,373,490 factor occurrences. Its generator and original
verifier share a seven-base Miller--Rabin routine, so that routine is not used
as an independent primality proof here.

`computations/check_p13_factor_primality.py` first authenticates both the gzip
and decompressed bytes, enforces canonical decimal rows and exact products
back to \(z^2+1\), and obtains 1,357,591 distinct claimed factors. Let

\[
m=2{,}958{,}540{,}704{,}271{,}709,
\qquad L=\lfloor\sqrt m\rfloor=54{,}392{,}469.
\]

The checker constructs the exact Eratosthenes sieve through \(L\). Every
claimed factor at most \(L\) must be marked prime. It forms the exact product
\(P\) of every distinct claimed factor larger than \(L\), the primorial \(M\)
of every prime at most \(L\), and checks \(\gcd(P,M)=1\). If a large claimed
factor were composite, it would have a prime divisor at most its square root,
hence at most \(L\), contradicting the gcd. Thus every transcript factor is
prime without any pseudoprime theorem.

The deterministic canonical receipt is
`certificates/p13-factor-primality.json`, 719 bytes, SHA-256
`cb67a19e9edfc21206b6ec0c886bf6aa67b97a110296f7e20bf00bdf818cfc64`.
Its exact product hashes are
`9517fd5347a830cb6be1f6c8a600f925dd56f745600579d18d5d65a1cb923308`
for \(P\) and
`e7271b9931e968382377ef02b10f08a4b86c4fd3d4c739ddce0fa607ab9c3802`
for \(M\). Independent source review, semantic mutations, a naive sieve
comparison through 100,000, and a second full GMP replay all passed. Controls
reject small composites `4`, `49`, and `341`, and a large-branch composite
`101*103`; product-preserving real-row composite mutations were also rejected.

## Full finite stream through \(100{,}000{,}006\)

ART-005's two authenticated gzip streams encode a sequence of proper
colorings at the right endpoints

\[
e_i=25i+6,\qquad 1\le i\le4{,}000{,}000.
\]

At such an endpoint, \(B_7(e_i)=i\).  Restriction of its coloring therefore
covers the entire constant-benchmark block
\([25i-18,25i+6]\).  The first block begins at \(7\); an independent diagonal
sieve verifies that there is no eligible vertex for \(1\le N\le6\).

The theorem-grade verifier is
`computations/independent_check_finite_stream.cpp`, SHA-256
`b891896e89b943eda2baa0bfe2903ffecc0806c53a301206f18bdd74b78bdc5d`.
It imports no candidate code.  It enforces these schemas and exact EOF:

- the base stream has magic `E848D1\0\0`, the little-endian endpoint count
  `4000`, and for each endpoint a list of `(uint32 vertex, uint16 color)`
  updates whose state persists;
- the compact stream has magic `E848C3\0\0`, little-endian base/end/step
  indices, and for every later endpoint a no-swap/one-old-bin-swap code
  followed by the complete list of newly exposed outsider placements;
- the emitted leaf stream has magic `E848L1\0\0`, a little-endian count,
  and the strictly increasing distinct 64-bit terminal factors.

The verifier independently sieves primes through \(100{,}000{,}006\), solves
\(x^2\equiv-1\pmod p\) with generic Tonelli--Shanks, and Hensel-lifts the two
roots modulo \(p^2\).  These roots give exactly the diagonal-eligible vertices:
if \(p^2\mid a^2+1\), then \(p\equiv1\pmod4\), \(p\ge5\), and \(p\le a\).
The resulting exact diagonal count is `10,515,898`.

For every one of the first 4,000 endpoints, the verifier reconstructs every
diagonal vertex, requires a color below \(i\), and checks every same-color pair.
For each of the remaining 3,996,000 endpoints, it checks that the newly exposed
outsider list is exact and verifies every bin changed by the new anchors, swap,
or placement.  Unchanged bins inherit the preceding endpoint invariant.  This
is a complete induction, not a sample.  The accepted stream contains
4,915,348 base changes, 1,379,312 swaps, and 2,513,387 placements.  It checks
18,049,789 base pair occurrences and all 14,458,371 compact affected-bin pair
occurrences.

Each checked pair value \(ab+1\) is factored independently by small-prime
division and deterministic Brent splitting.  A Miller--Rabin predicate is used
only to propose terminal leaves: the verifier checks the exact factor product
and absence of duplicates, emits every terminal leaf used by every positive
cache computation, and never converts a split failure into acceptance.  Cache
hits reuse a factorization whose leaves were already emitted.

The canonical leaf stream has 11,108,162 distinct values, occupies 88,865,312
bytes, and has SHA-256
`56720662876aaddcf5c0706d672d450f85db4f0606c00ba3875c514af7be22fa`.
Its maximum is

\[
m=9{,}999{,}932{,}500{,}113{,}877,
\qquad L=\lfloor\sqrt m\rfloor=99{,}999{,}662.
\]

`computations/CertifyLeavesExport.java` exactly sieves through \(L\), requires
all 2,328,675 leaves at most \(L\) to be marked prime, and constructs the
primorial \(M\) of all 5,761,441 primes at most \(L\) and the product \(P\) of
the 8,779,487 larger leaves.  The product hashes are
`ab0de48740f26f26ec98f4a636f22ae8d5dd02ec5d189c735bfd989e1ea5b105`
for \(M\) and
`f4203a24bce785438eaffeea4801f604da010b753bfab0c58415791a2283c64a`
for \(P\).  `computations/gcd_finite_factor_products.py` verifies with exact
GMP integers that \(\gcd(P,M)=1\).  A composite large leaf would have a prime
divisor at most its square root and hence at most \(L\), a contradiction.
Thus every emitted leaf is prime and every accepted pair value is squarefree.

The canonical receipt is `certificates/finite-factor-leaves.json`, 704 bytes,
SHA-256
`4fc75b0ed263df81c07c5997c915511351ea61fff085d3ac95159c524ca9aad6`.
The endpoint-401 control changes only vertex 18, creating the same-color pair
with 382 for which
\(18\cdot382+1=6877=13\cdot23^2\), and restores the original state at endpoint
402.  Sampled verifiers accept this repaired-final-state mutation; the
theorem-grade verifier rejects it at endpoint 401.  Factor-oracle controls,
schema/EOF checks, exact-product checks, and an injected-factor gcd control
complete the negative controls.  A full undefined-behavior-sanitized replay
provides separate implementation hardening; it is not a mathematical premise.

## All-\(N\) manifest and primary checker

`certificates/all-n-manifest-v1.json` is the canonical root manifest for the
computational obligations. It pins the exact statement bytes, ART-005 commit
and tree, release manifest, Sothanaphan source and claims digest, every
subordinate local checker source, every committed root receipt, the five
closed ranges, the range-ledger digest, and the six required replay stages.
The primary orchestrator cannot self-pin in that manifest; its live SHA-256 is
instead bound into the owned-work-directory sentinel, every stage fingerprint
and receipt, and the final receipt.

`scripts/check_certificate.py` has the following semantics. A theorem-grade
PASS means that, at the pinned inputs:

1. the strict canonical schema and all authenticated identities passed;
2. the independently generated prefix certificate, direct-factor checker,
   mutation suite, and exhaustive oracle through 100 passed;
3. the independent lower-`p=13` parser, exact products, sieve, batch gcd, and
   composite controls passed and regenerated the committed receipt;
4. the independent finite-stream checker verified every base endpoint and
   compact transition, certified every factor leaf, and rejected the repaired
   endpoint-401 corruption for the intended reason;
5. the high-range exact-rational replay and weakened-constant controls passed;
6. all 19 full ART-005 positive, semantic-mutation, sanitizer, and fresh-
   extraction stages passed; and
7. the final exact range ledger again covered every positive integer with
   digest `b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1`.

Its conclusion is exactly `ALL-N COMPUTATIONAL CERTIFICATE PASSED`. This
discharges the computational evidence for `IP_FIN`, `IP_LOWER`, `IP_LOW`,
`IP_MIDDLE`, and `C0` only when combined with the separately proved structural
rank/envelope lemmas and the audited high-range theorem. The checker does not
claim that its own exit code proves those human lemmas or the final Lean gate.

The persistent work directory supplies operational stage-level recovery. It must be a
fresh directory outside and not above the repository, or contain the exact
manifest/orchestrator ownership sentinel written by the checker; a foreign,
symlinked, or stale directory is rejected before any fixed output name is
written. Child processes inherit `PYTHONDONTWRITEBYTECODE=1`, so the strict
ART-005 release inventory remains identical across resumed runs. A checkpoint
is written atomically only after exit zero, decisive output markers, exact
outputs, and stage postconditions pass. Its fingerprint includes the manifest,
complete command, tool identities, and all prior receipt hashes. `--resume`
rehashes the log, output files, receipt, dependencies, and fingerprint before
skipping a completed stage. Any drift fails closed; an interrupted stage has
no valid receipt. Because these local receipts are unsigned and caller-writable,
they attest consistency but not execution provenance. A resumed chain therefore
emits only `resumed-checkpoint-chain-validated`; it cannot print the
theorem-grade PASS or discharge `CD0`. Only one fresh uninterrupted run of all
six stages may do that. `computations/test_all_n_manifest.py` rejects floats,
Booleans-as-integers, duplicate/reordered/extra keys, path escape, symlink,
digest drift, interval gaps, and missing stages.
`computations/test_all_n_resume.py` rejects modified logs, checkpoints,
outputs, dependencies, manifests, interrupted-stage state, nested links,
unexpected work-tree entries, output redirection, and surviving child processes.

The root orchestrator has passed source authentication, schema controls, and
checkpoint controls. One complete fresh six-stage end-to-end replay at public
commit `cd4c728...d705d7` ran without `--resume`, ended with the theorem-grade
PASS after 8,487.79 seconds, and emitted canonical receipt SHA-256
`222c5313...a71009`. A separately assigned referee reconstructed every stage
fingerprint, log/output hash, dependency receipt, repository identity, and
coverage result. The canonical receipt and referee report are
`certificates/all-n-computational-receipt-2026-08-11.json` and
`certificates/all-n-root-replay-2026-08-11.md`. The receipt remains correctly
labelled `local-unattested`; it discharges the specified computational root
node `CD0`, not a human structural argument or any Lean node.

## Connection to an all-\(N\) proof

A finite certificate proves only its declared interval. The independent
high-range audit has now proved the target for every

\[
N\ge T=264000000000000000.
\]

The computational obligation of exact coverage for every `1 <= N < T` is now
discharged. ART-005 supplies a finite coloring through `100000006` followed by
exact structural interval certificates. Its mathematical rank and interval
semantics passed independent review, and its 19-stage full replay passed with
closed coverage digest
`b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1`.
The clean-room finite checker, exact factor-leaf certificate, mutation suite,
and independent reviews prove the first range. No sampled
verifier, asymptotic notation, or decimal approximation may bridge the later
ranges.
