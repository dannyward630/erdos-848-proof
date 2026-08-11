# All-\(N\) proof-artifact audit

## Scope and acceptance rule

This file records independent checks of public artifacts that claim to settle
the source-faithful statement in `docs/problem-spec.md`. A repository's own
status label, hash gate, compilation claim, or replay receipt is evidence, not
certification. An artifact is accepted only when its mathematical interfaces,
case coverage, computation semantics, and (when applicable) formal trust
boundary have all been checked independently.

Exact audited revisions:

| ID | Repository | Revision | Role |
|---|---|---|---|
| ART-005 | `ipitchford/erdos-848-all-n` | `1afd7c722cae5ee7dd0fd1fde64427537394f749` | accepted all-\(N\) computer-assisted mathematical proof |
| ART-006 | `crabsatellite/erdos-848-squarefree-product` | `ede0151a35c86b6395cf67dd034811d22a92c7ba` | candidate paper plus Lean proof |

## ART-006: paper and Lean package

### Statement and theorem interface

The final endpoint is

```lean
Erdos848.PaperGeneratedCertificateProvider.all_N :
  ∀ N, Erdos848.OriginalProblem848Statement N
```

`lean4/Erdos848/ProblemCore.lean` defines the statement using
`Finset.Icc 1 N`, quantifies over every ordered pair in the set (so the
diagonal is included), uses `¬ Squarefree (a * b + 1)`, and compares against
the exact cardinality of the class `7 mod 25` in the same interval. The extra
formal case `N = 0` is separately trivial and does not weaken the positive-\(N\)
source theorem. `SharpnessCore.lean` proves the lower construction, and
`HallReduction.lean` proves a biconditional with the original statement.

**Result:** statement fidelity passed.

### Structural closure

The final provider dependency cone has 30,636 project modules and 77,600 local
import edges. Adding the publication theorem-map and axiom-audit wrappers gives
30,638 modules and 77,602 edges. The audit found no missing local import and no
cycle. Only the two publication wrappers import the final provider.

The range assembly is gapless:

- \(N\le5{,}000{,}000\);
- \([5{,}000{,}000,10{,}000{,}000)\);
- \([10{,}000{,}000,20{,}000{,}000)\);
- \([20{,}000{,}000,40{,}000{,}000)\);
- \([40{,}000{,}000,200{,}000{,}000)\);
- \([200{,}000{,}000,2{,}000{,}000{,}000)\);
- \([2{,}000{,}000{,}000,500{,}000{,}000{,}000)\);
- \(N\ge500{,}000{,}000{,}000\).

The final `NumericalCertificates` object contains five **proof-carrying**
certificate families. Their structures include `Prop` and equality fields,
including quantified finite Bool equalities, mask/scan semantics, row-local
prime-count inequalities, and exact coverage proofs. It is therefore
inaccurate to describe them as having “no theorem-valued assumptions.” The
correct noncircularity claim is narrower: no field has type
`OriginalProblem848Statement`, `Erdos848HallStatement`, an interval-close
theorem, or an equivalent all-\(N\) conclusion. Generated instances supply
explicit finite or local semantic proofs, and the Hall/original theorem is
derived afterward. The final theorem has no hypotheses or certificate
parameters.

**Result:** source-level structural and noncircularity audit passed.

### Certificate-semantics audit

All five certificate families were traced through representative generated
instances and their consumers:

- `fiveSharp` carries finite Bool equalities, discharged by exhaustive
  generated leaves and then interpreted by a proved Bool-list checker;
- `middleNormal` and `middleTwist` carry support, mask, and scan semantics;
  their masks are proved supersets of every actual modular square, so extra
  bits can only weaken an upper bound;
- `middleRoot` rows carry explicit prime-count inequalities, exact row checks,
  and a contiguous-coverage proof;
- `highTail` carries proof-bearing QR rows below 500 billion, while the
  unbounded branch invokes an independently proved analytic theorem rather
  than retrieving the desired result from a certificate field.

The finite-prefix trace through five million was followed from Pratt-certified
factor payloads and exact diagonal coverage, through a proper coloring, to the
literal original statement. The six high-QR intervals cover exactly
\([2\text{B},500\text{B})\), and the unbounded branch starts at 500B. No mask,
factor-tree, prime-tree, or row-coverage encoding was found that could create a
false upper bound: incomplete search structures reject or overcount, and
coverage recursion requires the next lower endpoint to equal the prior
`upper + 1`.

**Result:** certificate-interface semantics passed source review; clean
elaboration and live axiom replay remain required.

### Static trust audit

The exact final closure contains no operative project declaration or use of
`axiom`, `sorry`, `admit`, `native_decide`, `bv_decide`, `bv_check`, `opaque`,
`unsafe`, `extern`, `run_tac`, `Lean.ofReduceBool`, `Lean.trustCompiler`,
`partial def`, `partial_fixpoint`, `implemented_by`, `mkSorry`, `sorryAx`,
`Declaration.axiomDecl`, or `addDecl`. Ordinary kernel-checked `by decide`
proofs do occur.

`PublicationAxiomAudit.lean` asks for every one of the 15 publication
endpoints and declares only `propext`, `Classical.choice`, and `Quot.sound` as
acceptable. This source interface is appropriate, but its reported output has
not yet been reproduced live.

**Result:** static audit passed; live axiom replay pending.

### Repository-authored gates

The following gates passed at the pinned revision:

```sh
python3 -B scripts/verify_public_repository.py
python3 -B scripts/verify_paper_math_implementation.py
python3 -B scripts/verify_paper_lean_correspondence.py
python3 -B scripts/verify_paper_lean_numbers.py
python3 -B scripts/verify_four_range_paper_arithmetic.py
python3 -B scripts/verify_reference_evidence.py \
  --require-cited-coverage --require-entry-checks
```

They reported 15 endpoints, 24 numbered paper results, 31 exact source files,
49 declaration anchors, 33 numeric claims, and a 30,638-module closure. These
are consistency and arithmetic gates; they do not replace kernel replay or an
independent proof of the encoded certificate semantics.

The positive and fail-closed logic in `scripts/test_publication_contract.py`
passed all 12 tests under a runtime-only redirection of its requested root
temporary directory to `/private/tmp`. The unmodified command fails on macOS
before the tests because it explicitly requests `mkdtemp(..., dir=/)`, and `/`
is sealed. Classification: `REPAIR_EXECUTION`.

### Release self-containment defects

The release manifest and `RELEASE.md` require
`scripts/build_release_package.py` and
`scripts/verify_publication_package.py`, but neither file exists. The stronger
source-list gate fails exactly with:

```text
[proof-state:error] release source is missing: .../scripts/build_release_package.py
[proof-state:ok] contract=erdos-848-all-n-four-range-v1 machine=closed
manuscript=complete alignment=aligned paper_endpoints=15 lean_closure=30638
```

The public package also excludes the generator programs named in its
certificate-pipeline metadata. Its generated Lean certificate sources are
available for checking, but the published tree cannot regenerate all of them
from upstream inputs. These are reproducibility defects, not demonstrated
logical counterexamples.

### Detailed paper audit

The paper gives the global reduction and maps results to Lean declarations,
but it is not by itself a self-contained detailed proof. Several decisive
finite constants, root cases, and terminal inequalities are discharged only
as “finite calculation” or “substitution” without the underlying table or
derivation. The formal/certificate layer therefore remains load-bearing.

**Result:** conditional structural pass; standalone detailed-paper proof not
accepted.

### Clean build and kernel replay

Pinned dependencies were prepared with Lean `v4.30.0-rc2` and mathlib revision
`54e71fa9173471d591658f5380c46aaf050bbaae`. A small
`PublicationContract.lean` trust-zero replay succeeded at 922 MiB. Guarded
`ProblemCore.lean` attempts failed closed because of available memory:

| memory cap | observed result |
|---:|---|
| 2,048 MiB | killed at 2,201.7 MiB |
| 3,000 MiB | killed at 3,042.5 MiB |
| 3,200 MiB | killed at 3,230.9 MiB |
| 4,600 MiB | not launched; only 3,369 MiB available |
| 3,500 MiB | not launched; only 3,608 MiB available |

No failed attempt installed a partial `ProblemCore.olean` or left a Lean
process. The documented final source-build stages allow 32 GiB RAM.

The published cache contains 75 Windows-x86_64 ZIP shards totaling
32,249,316,999 bytes and expands to 129,476,102,424 bytes. This host has only
about 31 GiB free. The cache is pinned to revision `bb8e1b10...`, but that
revision and the audited `ede0151a...` revision have the identical `lean4`
tree object `6b9794fafddd3e7780c6a10a442f2e4e9dc73c1a`, identical toolchain and
dependency manifest, and exact hash agreement for all 30,638 Lean sources.
A successful `--trust=0` cache replay would therefore recheck the same proof
terms, but it has not been run here and would still not replace a clean source
build.

A noninstalling APFS compression probe authenticated shard 1
(`800a092f...46c8`), validated all 653 ZIP paths as relative nonsymlink files,
and measured 1,709,044 KiB apparent versus 543,436 KiB allocated after a
transparent-compression copy: 31.8% physical storage. Extrapolating that
representative ratio to the 120.58 GiB cache still requires about 38.3 GiB,
before installation overhead and with only about 31 GiB available. Transparent
compression therefore does not unblock the cache route on this host.

**Result:** `REPAIR_EXECUTION`; no proof defect found, but final Lean
certification is incomplete.

### ART-006 disposition

ART-006 is strong source-level evidence for an exact formal proof. Its literal
statement, noncircular structure, and representative certificate semantics
have passed independent review. It is not accepted as the independently
certified solution until a suitably provisioned machine completes a clean
source build, live trust-zero replay, `#print axioms` capture, and final
dependency/statement comparison.

## ART-005: independent computer-assisted candidate

The literal theorem statement, lower construction, graph interpretation, and
closed range ledger agree with `docs/problem-spec.md`. Its proposed cover is:

| Closed range | Method |
|---|---|
| \(1\le N\le100{,}000{,}006\) | exact coloring and compact endpoint induction |
| \(10^8\le N\le10^9\) | exhaustive least-witness structural split |
| \(10^9\le N\le10^{12}\) | exact-rational short-shift envelopes |
| \(10^{12}\le N\le264{,}000{,}000{,}000{,}000{,}000\) | exact-rational rank envelopes |
| \(N\ge264{,}000{,}000{,}000{,}000{,}000\) | Sothanaphan's explicit theorem |

The finite and first structural ranges overlap on
\([100{,}000{,}000,100{,}000{,}006]\); the remaining junctions are shared
closed endpoints. The range-ledger digest is
`b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1`.

The public `HEAD` release wrapper has 19 stages. An independent full-profile
replay completed all 19 positive, mutation, sanitizer, source-authentication,
and coverage stages in 5,523.791 seconds. It ended with a fresh-extraction
manifest pass (`6f197f0d...7573`) and the closed range-ledger digest
`b28760bc...ebe1`; the exact receipt is
`certificates/ipitchford-all-n-replay-2026-08-10.md`.

A clean-room exhaustive verifier also accepted every one of the 4,000 base
endpoints and all 3,996,000 compact transitions, checking 18,049,789 base and
14,458,371 compact pair occurrences. Its deliberately sampled modes are not
theorem-grade: an endpoint-401 mutation can pass them and later repair the
state. The mutation is rejected by the exhaustive mode. The durable checker
exports every accepted factor leaf. An exact sieve and batch primorial-gcd
certificate proves all 11,108,162 leaves prime; an independent referee rebuilt
the current sources, regenerated the exact products and canonical receipt,
obtained gcd 1 and injected-control gcd 2, and approved `IP_FIN`.

The structural rank reduction, all three exhaustive outsider branches,
CRT/collision bounds, generalized-Pell orbit bound, exact interval semantics,
and endpoint choices passed independent mathematical review. The authenticated
lower-\(p=13\) transcript was separately parsed product-by-product, and its
1,357,591 distinct claimed factors were certified prime by an exact sieve and
primorial-gcd argument. The original shared Miller--Rabin routine is therefore
not load-bearing.

A later review found FL-013 in the generalized-Pell prose: direct normalization
of the endpoint-square $B^2$ estimate dropped $B/N$. The repaired
load-bearing argument keeps the actual $N$: $x,x+d\le N$ gives the absolute
tail $2\tau(|\Delta|)K(B)N^2/Y^2$; division by $N/25$, followed by
$N\le B$, gives exactly the verifier's existing
$50\tau(|\Delta|)K(B)B/Y^2$ term. A separate review lane re-derived the repair.
No row, digest, or interval changed.

The final mathematical referee rechecked the literal statement, finite and
structural certificate semantics, Hanson range hypothesis, Sothanaphan high
theorem, and all interval junctions. No unresolved mathematical or encoding
gap remained. Exact reports and proof locations are in
`docs/final-referee.md` and `proof/final-proof.md`.

**Result:** ART-005 is accepted at the pinned revision as a complete
computer-assisted mathematical proof of the source-faithful all-\(N\) theorem.
This disposition does not waive the repository protocol's separate ART-006
clean-build and live-axiom gate.

## Other public artifacts

| Artifact | Exact disposition |
|---|---|
| `FormalConjectures` | statement/reference only; all-\(N\) theorem is `sorry`, and the fixed-\(N\) interface uses `Finset.range N` |
| `erdos-banger` | asymptotic theorem only; cannot cover all positive \(N\) |
| `hjyuh/erdos` | author-acknowledged threshold gap and missing certificate/checker; rejected |
| `SproutSeeds/erdos-problems` | useful research dossier and finite evidence, but no all-\(N\) bridge |
| `lean-genius` | theorem-strength axiom; its eventual `N / 25` equality is false at every \(N=25k+7\) |

## Current conclusion

No exact counterexample to the original problem has been found. ART-005 is now
accepted as a complete mathematical computer-assisted proof, with an
independently replayed finite certificate and gapless exact structural/high
cover. ART-006 remains strong source-level formal evidence but is not accepted
as independently certified until a sufficiently provisioned host completes
its clean build, trust-zero replay, live axiom capture, and dependency audit.
