# Independent finite-stream replay receipt

## Scope

This receipt records an independent exhaustive verification of ART-005 at
revision `1afd7c722cae5ee7dd0fd1fde64427537394f749`. It certifies
`omega(G_N) <= B_7(N)` for every `1 <= N <= 100000006`.

The checker imports no candidate implementation. It reconstructs the exact
diagonal vertex set, parses every transition, verifies every changed color
class, and emits every terminal factor leaf used by an accepted squarefree
decision. A separate Java/GMP certificate proves all emitted leaves prime.

## Authenticated inputs and sources

| Object | SHA-256 |
|---|---|
| base stream | `3380a6778d237a3fd2a1f01c7ea72292e470a845b09eea99beb66ca85434ba98` |
| compact stream | `9917ec4590f69efd8c6f7d30d54ecf5284e92f185ec70a4d14657acb02551b12` |
| C++ verifier | `b891896e89b943eda2baa0bfe2903ffecc0806c53a301206f18bdd74b78bdc5d` |
| Java exporter | `45c0d97ab1469a9ab63b4a18905ee59b559907b73f3dca70cbd3212823c2a9e5` |
| GMP finisher | `e686dcaa7c2b668324d83227dbdc36846f1ea5787be3cb1f6aed7daa1c792ac5` |
| endpoint-401 mutator | `5c885ef83783080e1edc28b198686a4107efa0608f05cf0cca39fc26a0c1ee76` |
| orchestrator | `f54b8dcbafd07178d18df8b3cd6b16652c30ae41ef7ee1c968d874a046f6bf0b` |
| canonical JSON receipt | `4fc75b0ed263df81c07c5997c915511351ea61fff085d3ac95159c524ca9aad6` |

The host was arm64 macOS 26.6.1. The replay used Apple clang 21.0.0,
OpenJDK 25.0.3, CPython 3.12.13, gmpy2 2.2.1, GMP 6.3.0, and zlib 1.2.12.

## Exhaustive coloring replay

The exact commands are in `REPRODUCE.md`. The optimized checker binary had
SHA-256
`5b2e508e4b7bf3c1ed91469215af7764f6eb272cb7749a10d0e0f0d01521b57c`.
Its full log had SHA-256
`38adb6bc9897185e6758ffde895c5c423c5020360ca43c5faf95aca5cc7e911e`
and reported:

```text
independent_base_changes=4915348
independent_base_endpoint_pairs=18049789 endpoint_count=4000
independent_base_top_pairs=9022
independent_compact_steps=3996000 swaps=1379312 placements=2513387
independent_compact_pair_occurrences=14458371 checked=14458371
independent_factor_leaf_count=11108162
independent_factor_leaf_max=9999932500113877
independent_total_diagonal=10515898
independent_pair_computations=17376578
independent_pair_queries_hits_overwrites=32517182/15140604/10124496
independent_mode=full-with-factor-leaves
INDEPENDENT FINITE STREAM AUDIT PASSED
```

Exit status was zero. The run took 275.69 seconds real, with maximum RSS
1,001,635,840 bytes and zero OS swap operations. The 88,865,312-byte leaf stream had
SHA-256
`56720662876aaddcf5c0706d672d450f85db4f0606c00ba3875c514af7be22fa`.

## Exact factor-leaf certificate

The Java exporter class had SHA-256
`7390f1ff9d7813231e1b979e78452202f1cd401a93fc70476e725b1c0cd55d3c`;
its log had SHA-256
`6b8087b3b9fb23614f8224866881750d1d7ddaa94cf806a0ffab7b504b74866c`.
It reported 11,108,162 strictly increasing leaves, from 2 through
9,999,932,500,113,877, and the exact split 2,328,675 small plus 8,779,487
large leaves at `L = 99999662`. It sieved 5,761,441 primes through `L`.

The 18,031,429-byte primorial had SHA-256
`ab0de48740f26f26ec98f4a636f22ae8d5dd02ec5d189c735bfd989e1ea5b105`;
the 40,922,482-byte large-leaf product had SHA-256
`f4203a24bce785438eaffeea4801f604da010b753bfab0c58415791a2283c64a`.
The patched exporter reproduced both files byte-for-byte in 367.69 seconds
with maximum RSS 944,029,696 bytes and zero OS swap operations.

The durable GMP finisher reported `large_primorial_gcd=1`; its injected
factor control reported `injected_factor_control_gcd=2`. The log SHA-256 was
`16fc5fa17ca9fb4baa73d50b8f15e45995ffc3ada0460886c1488c2b71a59187`.
It ran for 71.65 seconds with maximum RSS 682,262,528 bytes and zero OS swap
operations.
The generated JSON compared byte-for-byte with
`certificates/finite-factor-leaves.json`.

If a leaf larger than `L` were composite, it would have a prime divisor at
most its square root and hence at most `L`, contradicting the gcd with the
primorial through `L`. Thus every leaf is prime. The C++ exact-product and
no-duplicate checks therefore prove every accepted pair value squarefree.

## Negative control and sanitizer

The endpoint-401 mutant had SHA-256
`735a1af16019f98dff145a6655eec331917cbcfe5e4eb023fae4c2e45844e2ae`.
It temporarily puts 18 with 382, where
`18 * 382 + 1 = 6877 = 13 * 23^2`, and restores the original state at the
next endpoint. The exhaustive checker rejected it specifically with
`endpoint pair is nonsquarefree`, exited nonzero after 5.82 seconds, and
created no leaf file. The rejection log SHA-256 was
`83373a2535c05c6143b4ef4dc742984b5651401c8fe0c7812ec1362b84a2fd95`.
The sampled modes that accept this mutation are quarantined as FL-011.

The committed orchestrator was then run end-to-end from a fresh temporary
directory. It authenticated every input/source, rebuilt and reran the C++
checker, regenerated both Java products, completed the GMP certificate,
reconstructed the canonical JSON byte-for-byte, and rejected endpoint 401 for
the required reason. Its log had SHA-256
`fc39ef2ffc1227366959c59837f37e488b2943c110cb3b22b81b829b209c1e68`
and ended with `INDEPENDENT THEOREM-GRADE FINITE PIPELINE PASSED`.
The run took 862.60 seconds real with maximum RSS 1,010,745,344 bytes and
zero OS swap operations.

The UBSan binary had SHA-256
`4a76956ff6d7a07c5cafd384532ea03031eac4eff3f5813e0bd62e30e3464b39`.
A full replay exited zero, reproduced every decisive counter and the canonical
leaf hash, and emitted no sanitizer diagnostic. The log SHA-256 was
`c7849901b29988147eb9e89e7678cb0516f057168015e5a58afc50ae8e70d90d`.
It ran for 270.72 seconds with maximum RSS 1,175,339,008 bytes and zero OS
swap operations. This is implementation hardening, not a mathematical premise.

## Retry classifications and review

- Sampled endpoint checking is `AUDIT_COMPUTATION` and is absent from the
  durable checker.
- The exporter's former unconditional tiny-fixture access at index 49 was
  `REPAIR_EXECUTION`; guarding the control leaves the production computation
  byte-identical.
- A slow direct Java binary-gcd attempt was `REPAIR_EXECUTION`; GMP completed
  the same exact product gcd.

The independent batch reviewer reproduced the leaf partition, products, gcd,
controls, and patched exporter, reviewed the full UBSan receipt, and found no
remaining factor-primality or encoding gap. A separate promotion referee then
performed a fresh end-to-end run from the current sources: exhaustive O3
checking, Java product export, pinned CPython/gmpy2/GMP gcd, canonical-receipt
reconstruction, and the endpoint-401 negative control all passed with the
identities above. That referee found no mathematical or encoding gap and
approved `IP_FIN` for promotion once these exact sources and receipts are
committed together.

Hashes authenticate bytes; `docs/computation-spec.md` supplies the
mathematical meaning. The trusted execution base is the pinned source plus
the ordinary C++ compiler/zlib runtime, Java exact `BigInteger` arithmetic,
CPython, gmpy2, and GMP.
