# Lean audit

## Acceptance requirements

The final formal deliverable must provide a theorem equivalent to the exact
target in `docs/problem-spec.md`, cover every positive \(N\), build from a clean
checkout, contain no `sorry` or `admit`, introduce no custom theorem-strength
axioms, and expose no circular theorem interface. For every final theorem the
audit must record `#print axioms`, its import/dependency closure, and a
source-to-formal statement comparison.

Compilation is necessary but not sufficient. Opaque computation is accepted
only when its certificate semantics and trusted-code boundary are documented
and independently checked.

## FormalConjectures baseline

Pinned repository revision:
`9af1d7101d82b0c6ff5e6aab4151ca3786de15b1`.

`FormalConjectures/ErdosProblems/848.lean` defines its fixed-\(N\) set using
`Finset.range N = {0,...,N-1}` while its prose describes `{1,...,N}`. Its all-\(N\)
conjecture and asymptotic theorem contain `sorry`. Because zero cannot belong to
an admissible set, a universal shifted formulation may be equivalent after an
explicit index/bound proof, but the current fixed-\(N\) interface is not
literally the source statement. The cited `[Er92b]` metadata also requires
correction before use as a source reference.

**Status:** reference formalization only; not a proof artifact.

## Sawhney large-\(N\) formalization

The `erdos-banger` repository is pinned at
`48e9c1aeb13a6e075d78ecf42dc1f2839d5ff071`. It claims a formal version of the
sufficiently-large theorem. Clean build, theorem-strength hypothesis,
circularity, `native_decide`, axiom, and dependency audits are pending. Even a
successful audit would discharge only the high-range component of the original
all-\(N\) target.

## Principal all-\(N\) candidate

The `crabsatellite/erdos-848-squarefree-product` repository is pinned at
`ede0151a35c86b6395cf67dd034811d22a92c7ba`. Its unconditional endpoint is

```lean
Erdos848.PaperGeneratedCertificateProvider.all_N :
  ∀ N, Erdos848.OriginalProblem848Statement N
```

The independent source/interface audit passed:

- the formal statement literally uses `Finset.Icc 1 N`, all ordered pairs
  including the diagonal, the exact nonsquarefree predicate, and the exact
  `7 mod 25` benchmark;
- `SharpnessCore` proves the matching lower construction;
- `HallReduction` proves a biconditional with the original statement;
- the 30,638-module publication closure has no missing import or cycle;
- the final proof-carrying certificate structure has no original-problem,
  Hall, interval-close, or equivalent all-\(N\) theorem as a field;
- exhaustive static scans found no operative project axiom, `sorry`, `admit`,
  native/compiler-trust decision procedure, unsafe declaration, custom
  declaration injection, or other proof escape.

Repository-authored statement, paper-map, numeric, reference, and exact-rational
arithmetic gates passed. The publication-contract logic passed all 12 positive
and negative cases under a runtime-only macOS temporary-directory workaround;
the unmodified test's attempt to create under sealed `/` is a portability
defect classified `REPAIR_EXECUTION`.

An independent certificate-semantics audit traced all five object families
from representative generated instances through their finite Bool, mask,
trace, prime-bound, and coverage soundness theorems to Hall and then the
original statement. It found no circularity or false-accepting encoding. The
interfaces are not data-only: they contain many quantified `Prop` and equality
fields. External comments claiming “no theorem-valued assumption” are
literally inaccurate and should instead say that no ambient Hall,
interval-close, or original-problem theorem is a field. This is a documentation
defect, not a demonstrated logical gap.

Final certification remains incomplete. This 16 GiB host could not compile
`ProblemCore.lean` within the available 2.0--3.2 GiB guarded caps, and the
documented full build permits 32 GiB. The release cache expands to 120.58 GiB,
while only about 31 GiB is free. Consequently there is no independently
recorded clean build, live trust-zero final replay, or live `#print axioms`
capture. The source axiom-audit declares only `propext`, `Classical.choice`,
and `Quot.sound`, but its output is not accepted until replayed.

An authenticated representative cache shard compressed to 31.8% allocated
storage under APFS transparent compression. The corresponding full-cache
estimate is still about 38.3 GiB, so filesystem compression does not close the
storage gap.

The human paper also leaves decisive finite calculations to the generated
formal/certificate layer, and the public release is missing two scripts named
by its own release manifest. See `docs/artifact-audit.md` for exact commands,
resource measurements, and defects.

**Status:** faithful and noncircular at source level; strong evidence, but
unverified as a completed Lean deliverable because clean build and live axiom
replay remain outstanding.

## Root completion entrypoint

The main repository now tracks `lean/source-lock.json`, a literal
positive-`N` restatement in `lean/Erdos848Completion/Final.lean`, a live audit
of 15 upstream and four root declarations, and
`lean/run_completion_gate.py`. The final theorem visibly expands the original
interval, ordered-pair predicate (including the diagonal), and exact filtered
benchmark. Separate residue-7 and residue-18 witnesses avoid a uniqueness
overclaim.

The runner authenticates the ART-006 commit/tree, Lean tree, exact Windows
runtime archive and Lean/Lake executable digests, toolchain, mathlib pin, key
source hashes, and complete 30,638-file source census. Its
bounded mutation suite rejects malformed locks/axiom reports, inherited Lean
module paths, missing or shadowed explicit runtime directories, project OLeans
injected during cache bootstrap, package-cache namespace shadows, right-named
OLeans from the wrong root, and surviving child processes. The local `--source-audit-only`
mode passes, but that mode explicitly performs no build or kernel check. The
full Windows-only path refuses existing or unexpected project OLeans,
insufficient RAM/disk, dirty source, forbidden axioms, missing live reports,
wrong-root direct dependencies, or post-build source drift. It invokes the
observed pinned Lean executable with an explicit audited search path and emits
a receipt only after every gate succeeds. No such receipt exists yet, so
`LROOT`, `L1`, and `L2` all remain unverified.

## Exact execution-feasibility audit

The final theorem cone is not usefully reducible.  The final provider imports
30,636 project modules in 69 dependency layers, including 30,066 generated
modules and 2,346,174,067 bytes of Lean source.  The two publication wrappers
bring the declared closure to 30,638 modules.  The authenticated release cache
contains 129,476,099,768 raw bytes of OLean files for the provider and touches
all 75 shards; the full cache is 120.58 GiB raw and 30.03 GiB compressed.

On 2026-08-10 this host had 30.224 GiB free.  Even the measured APFS
compression extrapolation would allocate about 38.343 GiB for the OLeans,
8.119 GiB more than available, before checkout and dependency overhead.  A
source build has a raw-storage shortfall of about 90.36 GiB.  The published
kernel gate also requests 32,768 MiB plus a 1,024 MiB guard reserve, requiring
at least 33,792 MiB available memory; a nominal 32 GiB machine does not meet
that preflight.

The unmodified gate is Windows-specific: `run_kernel_gates.py` always passes
`--direct-lean`, while `run_lean_guarded.py` rejects that option unless
`sys.platform == "win32"`.  The guard additionally imports `psutil`, but the
release does not pin it.  These are `REPAIR_EXECUTION` portability and
environment defects, not evidence of a source-proof failure.

The smallest safe replay target is a persistent Windows x86-64 host with 64
GiB RAM and at least 170 GiB genuinely free storage, preferably a 300 GiB or
larger SSD and a short checkout path.  It must fresh-check out
`ede0151a35c86b6395cf67dd034811d22a92c7ba`, install the pinned Lean
`v4.30.0-rc2` and committed Lake dependencies without `lake update`, build the
30,636-module provider from source, and then run:

```text
python -B scripts/run_kernel_gates.py --memory-mib 32768
```

The resulting receipt must preserve the clean state, source hashes, full build
status, trust-zero theorem map, all 15 live `#print axioms` outputs, import
closure, and source-to-original statement comparison.  The Windows cache may
be used only as secondary kernel-term evidence; it cannot substitute for the
clean source build because its manifest self-asserts the source/OLean binding.
