# A computer-assisted proof of Erdős Problem 848

This repository gives a source-faithful, computer-assisted proof of Erdős
Problem 848 for every positive integer, together with the exact certificates,
independent checkers, source audit, failed approaches, and reproduction
instructions used to verify it.

For $N\ge1$, let $A\subseteq\{1,\ldots,N\}$ and suppose that $ab+1$ is
not squarefree for every ordered pair $a,b\in A$, including $a=b$. Then

$$
 |A|\le \left|\{n\le N:n\equiv7\pmod{25}\}\right|
      =\left\lfloor\frac{N+18}{25}\right\rfloor.
$$

The bound is sharp: the class $7\pmod{25}$ attains it. The class
$18\pmod{25}$ can tie it for some $N$; the theorem is a cardinality bound,
not a uniqueness claim.

## What is established

- **Mathematical theorem:** the all-$N$ result is proved by a gapless union of
  an exact finite coloring certificate, explicit structural interval
  certificates, and an audited high-range theorem.
- **Computational evidence:** every decisive finite stream has an independent
  exact checker, authenticated inputs, complete interval semantics, and
  negative controls. Existing component replays are recorded in
  [`certificates/`](certificates/).
- **Formal evidence:** the pinned ART-006 Lean development has a literal,
  diagonal-inclusive endpoint and a coherent noncircular source/interface
  audit. Its own publication state reports a closed theorem with only
  `propext`, `Classical.choice`, and `Quot.sound`.
- **Remaining project-level gate:** this repository has not independently run
  ART-006's complete 30,636-module provider build and trust-zero replay on the
  required Windows host. The root six-stage computational orchestrator also
  awaits one fresh end-to-end receipt. These are reproducibility/formal-
  assurance tasks, not uncovered values of $N$.

The precise status of every dependency is recorded in
[`docs/proof-ledger.md`](docs/proof-ledger.md) and
[`docs/proof-dag.yaml`](docs/proof-dag.yaml). No static check, preflight, or
partial replay is presented as a completed theorem gate.

## Read the proof

- [Final proof in Markdown](proof/final-proof.md)
- [LaTeX source](proof/final-proof.tex)
- [Compiled PDF](proof/final-proof.pdf)
- [Structural-certificate appendix and verification challenge](proof/structural-certificate-appendix.md)
- [Exact problem and statement audit](docs/problem-spec.md)
- [Internal adversarial review record](docs/final-referee.md)
- [Complete reproduction guide](REPRODUCE.md)

## Proof map

| Closed range | Method | Decisive evidence |
|---|---|---|
| $1\le N\le100{,}000{,}006$ | Exact compatibility-graph colorings at every benchmark endpoint | Independent C++ stream replay and exact leaf-primality certificate |
| $10^8\le N\le10^9$ | Least-witness structural rank bounds, including the full $p=13$ interval | 37 exact rows, independent transcript primality audit, all other outsider branches |
| $10^9\le N\le10^{12}$ | Exact-rational short-shift envelopes | Authenticated ART-005 rows and semantic mutations |
| $10^{12}\le N\le264\cdot10^{15}$ | Exact-rational rank envelopes | 1,255 complete multiplicative blocks |
| $N\ge264\cdot10^{15}$ | Explicit analytic theorem | Source-pinned Sothanaphan proof and exact-rational numerical audit |

The first two ranges overlap; every later pair shares its displayed endpoint.
Their union is all positive integers. The canonical range-ledger SHA-256 is
`b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1`.

## Reproduce it

Start with the quick controls. The root-manifest mutation suite deliberately
fails closed unless the decisive high-range source is present and
authenticated, so retrieve that one ignored input first:

```sh
mkdir -p sources/cache
curl -L --fail --silent --show-error \
  'https://drive.usercontent.google.com/download?id=1ujhm4_WYpgRV_rd1rJXIfHyvx16COEKe&export=download&confirm=t' \
  -o sources/cache/sothanaphan-2.64e17.pdf
python3 -B - <<'PY'
from hashlib import sha256
from pathlib import Path

path = Path("sources/cache/sothanaphan-2.64e17.pdf")
expected = "8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f"
assert sha256(path.read_bytes()).hexdigest() == expected
print("HIGH-RANGE SOURCE AUTHENTICATED")
PY
python3 -B computations/test_all_n_manifest.py
python3 -B computations/test_all_n_resume.py
python3 -B computations/check_prefix_certificate.py \
  certificates/prefix-10000.json \
  --expected-sha256 \
  693ce882fb3f3786caf8eb502dd0677f42a4ed687adaa71a613b27ad7ef49727
python3 -B computations/test_prefix_checker.py \
  certificates/prefix-10000.json
python3 -B computations/exhaustive_small_prefix.py --limit 100
```

The full package requires two external repositories at exact immutable
revisions, plus Java, a C++20 compiler, Python, and `gmpy2==2.2.1` backed by
GMP 6.3.0. [`REPRODUCE.md`](REPRODUCE.md) contains the exact clone, hash,
build, replay, operational-resume, mutation, TeX, and Lean commands.

The primary entrypoints are:

```sh
# Theorem-grade six-stage computational replay. Use a fresh empty directory
# outside this repository and do not pass --resume.
python3 -B scripts/check_certificate.py --work-dir /absolute/external/path

# Bounded Lean-runner controls, then a static source audit. Neither compiles Lean.
python3 -B lean/test_completion_gate.py
python3 -B lean/run_completion_gate.py --source-audit-only
```

`--resume` is available only for operational recovery. Unsigned local
checkpoints cannot prove execution provenance, so a resumed run never emits the
theorem-grade completion PASS and cannot discharge `CD0`.

The full Lean completion gate intentionally refuses underprovisioned or
unsupported hosts. Its documented minimum is Windows x86-64, 64 GiB physical
RAM, 200 GiB free storage, and a 32 GiB guarded Lean ceiling.

## Repository layout

| Path | Purpose |
|---|---|
| [`proof/`](proof/) | Human-readable all-$N$ proof, TeX, and PDF |
| [`certificates/`](certificates/) | Canonical certificates and authenticated replay receipts |
| [`computations/`](computations/) | Independent exact checkers, generators, and negative controls |
| [`scripts/`](scripts/) | Primary all-$N$ and finite replay orchestrators |
| [`lean/`](lean/) | Literal final theorem, source lock, axiom audit, and guarded completion gate |
| [`docs/`](docs/) | Statement/source audits, proof DAG, ledger, failed lemmas, computation semantics, and handoff |
| [`sources/`](sources/) | Source manifest; downloaded third-party PDFs/pages are intentionally untracked |

## Verification policy

This project deliberately separates exploration, mathematical proof,
computation, structural review, detailed review, and formal verification.
It does not accept numerical evidence as proof, sampled endpoints as interval
coverage, opaque solver output, theorem-strength assumptions, or a Lean file
merely because it compiles. Exact counterexamples to failed helper claims are
preserved in [`docs/failed-lemmas.md`](docs/failed-lemmas.md).

See [`AGENTS.md`](AGENTS.md) for the complete research protocol and
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the standard expected of changes.

## Provenance and attribution

This repository is an audit, synthesis, and reproducibility package. It builds
on the original Erdős–Sárközy problem; the sufficiently-large-(N) work of
Mehtaab Sawhney; Nat Sothanaphan's explicit threshold; the pinned ART-005
all-$N$ certificate repository; the pinned ART-006 Lean development; and
Denis Hanson's prime-counting estimate. Exact URLs, revisions, retrieved-file
hashes, statements, and known defects are in
[`docs/source-audit.md`](docs/source-audit.md).

The research, code, proof drafting, and adversarial review were carried out in
a multi-agent OpenAI Codex workflow under Danny Ward's direction. “Independent”
in this repository means that separately assigned implementations or review
lanes did not certify their own work; it does **not** mean external scholarly
peer review. This first public release is unrefereed, and the public Erdős
Problems tracker had not incorporated it as a resolution on 11 August 2026.
See [`PROVENANCE.md`](PROVENANCE.md) for the authorship and evidence boundary.

No third-party source repository or PDF is silently vendored here. The
ignored `external/` and `sources/cache/` trees are reconstructed from immutable
identities in [`REPRODUCE.md`](REPRODUCE.md).

## Citation and licensing

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). Original code,
Lean files, and machine-readable verification material are under Apache-2.0;
original proof and documentation prose are under CC BY 4.0. Third-party works
retain their own terms. See [`LICENSE.md`](LICENSE.md) and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
