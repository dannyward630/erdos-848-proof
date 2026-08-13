# Reproduction guide

Run commands from the repository root.

## Repository-state audit

```sh
git status --short --branch
git rev-parse --show-toplevel
find docs -maxdepth 1 -type f -print | sort
```

## Protocol-file presence

```sh
test -f AGENTS.md
test -f docs/problem-spec.md
test -f docs/source-audit.md
test -f docs/proof-dag.yaml
test -f docs/proof-ledger.md
test -f docs/failed-lemmas.md
test -f docs/computation-spec.md
test -f docs/handoff.md
test -f REPRODUCE.md
test -f scripts/check_certificate.py
test -f scripts/independent_check.py
test -f certificates/all-n-manifest-v1.json
test -f lean/source-lock.json
test -f lean/Erdos848Completion/Final.lean
test -f lean/Erdos848Completion/PublicationAxiomAudit.lean
test -f lean/run_completion_gate.py
```

## Proof-DAG syntax

```sh
ruby - <<'RUBY'
require "yaml"
dag = YAML.safe_load(
  File.read("docs/proof-dag.yaml"),
  permitted_classes: [],
  aliases: false
)
nodes = dag.fetch("nodes")
ids = nodes.map { |node| node.fetch("id") }
abort "duplicate proof-DAG node" unless ids.uniq.length == ids.length
dependency_edges = nodes.flat_map do |node|
  node.fetch("dependencies").map { |dependency| [dependency, node.fetch("id")] }
end
declared_edges = dag.fetch("edges").map { |edge| [edge.fetch("from"), edge.fetch("to")] }
expected_edges = dependency_edges + [["V0", "P848"]]
abort "proof-DAG edge list disagrees with node dependencies" unless declared_edges.sort == expected_edges.sort
puts "PROOF DAG STRUCTURE PASSED"
RUBY
```

## Final proof document

The Markdown and TeX statements must agree literally on positive `N`, the
diagonal-inclusive pair quantifier, and the exact benchmark. With Tectonic
0.16.9 installed, compile the TeX directly:

```sh
mkdir -p "$PWD/tmp/final-proof-build"
tectonic -X compile \
  --outdir "$PWD/tmp/final-proof-build" \
  --outfmt pdf \
  --print \
  --untrusted \
  "$PWD/proof/final-proof.tex"
```

The audited build used Tectonic 0.16.9 and produced a five-page PDF. A clean
run must exit zero; inspect all warnings and compare the theorem statement
against `docs/problem-spec.md` before using the document.

## Retrieve and authenticate audited sources

```sh
mkdir -p sources/cache
curl -L --fail --silent --show-error \
  'https://lematematiche.dmi.unict.it/index.php/lematematiche/article/download/587/555/2271' \
  -o sources/cache/erdos-1992-er92b.pdf
curl -L --fail --silent --show-error \
  'https://www.math.columbia.edu/~msawhney/Problem_848.pdf' \
  -o sources/cache/sawhney-problem-848.pdf
curl -L --fail --silent --show-error \
  'https://cdn.openai.com/pdf/4a25f921-e4e0-479a-9b38-5367b47e8fd0/early-science-acceleration-experiments-with-gpt-5.pdf' \
  -o sources/cache/openai-early-science-gpt5.pdf
curl -L --fail --silent --show-error \
  'https://arxiv.org/pdf/2511.16072' \
  -o sources/cache/arxiv-2511.16072.pdf
curl -L --fail --silent --show-error \
  'https://drive.usercontent.google.com/download?id=1nYBzwaBcMVWWW_Ncn38TERGalpuPz2hW&export=download&confirm=t' \
  -o sources/cache/sothanaphan-exp1958.pdf
curl -L --fail --silent --show-error \
  'https://drive.usercontent.google.com/download?id=1lSEzb9l-ThEc4ygZUg6KQGIIYvedd6gx&export=download&confirm=t' \
  -o sources/cache/sothanaphan-exp1420.pdf
curl -L --fail --silent --show-error \
  'https://drive.usercontent.google.com/download?id=1-8Xo-CNtRA9LnLaSZslJjVMgMkOQIbPa&export=download&confirm=t' \
  -o sources/cache/sothanaphan-7e17.pdf
curl -L --fail --silent --show-error \
  'https://drive.usercontent.google.com/download?id=1SR1U_9Rp4B7nQwljjhCDvdCRZ7ln9Jtb&export=download&confirm=t' \
  -o sources/cache/sothanaphan-3.3e17.pdf
curl -L --fail --silent --show-error \
  'https://drive.usercontent.google.com/download?id=1ujhm4_WYpgRV_rd1rJXIfHyvx16COEKe&export=download&confirm=t' \
  -o sources/cache/sothanaphan-2.64e17.pdf
curl -L --fail --silent --show-error \
  'https://www.cambridge.org/core/services/aop-cambridge-core/content/view/EBCBB4096EBC2A145C743C4C0E123E69/S0008439500060835a.pdf/on_the_product_of_the_primes.pdf' \
  -o sources/cache/hanson-1972-product-primes.pdf
curl -L --fail --silent --show-error \
  'https://www.erdosproblems.com/848' \
  -o sources/cache/erdosproblems-848.html
curl -L --fail --silent --show-error \
  'https://www.erdosproblems.com/latex/848' \
  -o sources/cache/erdosproblems-848-latex.html
curl -L --fail --silent --show-error \
  'https://www.erdosproblems.com/history/848' \
  -o sources/cache/erdosproblems-848-history.html
curl -L --fail --silent --show-error \
  'https://www.erdosproblems.com/forum/thread/848?order=newest' \
  -o sources/cache/erdosproblems-848-discussion.html
shasum -a 256 sources/cache/erdos-1992-er92b.pdf \
  sources/cache/sawhney-problem-848.pdf \
  sources/cache/openai-early-science-gpt5.pdf \
  sources/cache/arxiv-2511.16072.pdf \
  sources/cache/sothanaphan-exp1958.pdf \
  sources/cache/sothanaphan-exp1420.pdf \
  sources/cache/sothanaphan-7e17.pdf \
  sources/cache/sothanaphan-3.3e17.pdf \
  sources/cache/sothanaphan-2.64e17.pdf \
  sources/cache/hanson-1972-product-primes.pdf \
  sources/cache/erdosproblems-848.html \
  sources/cache/erdosproblems-848-latex.html \
  sources/cache/erdosproblems-848-history.html \
  sources/cache/erdosproblems-848-discussion.html
```

Expected hashes are tabulated in `docs/source-audit.md` and
`sources/README.md`. The PDF hashes are exact byte gates. The four Erdős
Problems HTML hashes identify the 10--11 August 2026 audit snapshots; live
responses contain dynamic server fields and are not expected to reproduce
those raw hashes. For changed HTML, preserve the new download separately,
record its access date, and compare the statement, history, discussion, and
status content before relying on it.

## Check pinned external proof artifacts

The ignored `external/` directory contains read-only audit clones. For a clean
checkout, retrieve the two decisive candidates at their exact
revisions before running any audit:

```sh
mkdir -p external
git clone https://github.com/ipitchford/erdos-848-all-n.git \
  external/erdos-848-all-n
git -C external/erdos-848-all-n checkout --detach \
  1afd7c722cae5ee7dd0fd1fde64427537394f749

git clone https://github.com/crabsatellite/erdos-848-squarefree-product.git \
  external/erdos-848-squarefree-product
git -C external/erdos-848-squarefree-product checkout --detach \
  ede0151a35c86b6395cf67dd034811d22a92c7ba

test -z "$(git -C external/erdos-848-all-n status --porcelain)"
test -z "$(git -C external/erdos-848-squarefree-product status --porcelain)"
```

These commands intentionally fail if either destination already exists; inspect
an existing audit clone instead of overwriting it.

After retrieval, verify the exact revisions of the two decisive audit clones:

```sh
git -C external/erdos-848-all-n rev-parse HEAD
git -C external/erdos-848-squarefree-product rev-parse HEAD
```

Expected revisions and repository hashes are in `docs/source-audit.md`. The
commands above are the clean-checkout retrieval procedure for both decisive
external artifacts; do not substitute a moving branch tip.

## Static formalization guard

This is a triage check only; it is not a proof or dependency audit:

```sh
rg -n --glob '*.lean' \
  '(^|[^[:alnum:]_])(sorry|admit|axiom|unsafe|native_decide)([^[:alnum:]_]|$)' \
  external/erdos-848-squarefree-product/lean4
```

This broader source scan covers the exact publication closure's known trust
escapes. Hits in comments must be classified manually:

```sh
rg -n --glob '*.lean' \
  '(^|[^[:alnum:]_])(axiom|sorry|admit|native_decide|bv_decide|bv_check|opaque|unsafe|extern|run_tac|partial[[:space:]]+def|partial_fixpoint|implemented_by|mkSorry|sorryAx|addDecl)([^[:alnum:]_]|$)' \
  external/erdos-848-squarefree-product/lean4
```

At revision `ede0151a...`, every lexical hit was a comment; ordinary
kernel-checked `by decide` proofs remain. A static scan is still not a build or
dependency audit.

## Crabsatellite paper/source gates

Run from `external/erdos-848-squarefree-product`:

```sh
python3 -B scripts/verify_public_repository.py
python3 -B scripts/verify_paper_math_implementation.py
python3 -B scripts/verify_paper_lean_correspondence.py
python3 -B scripts/verify_paper_lean_numbers.py
python3 -B scripts/verify_four_range_paper_arithmetic.py
python3 -B scripts/verify_reference_evidence.py \
  --require-cited-coverage --require-entry-checks
```

The pinned revision passes these repository-authored consistency, mapping,
exact-rational arithmetic, and source-evidence gates. They do not replace a
clean Lean build.

The stronger declared-release source-list gate exposes the current missing
release file:

```sh
python3 -B scripts/check_proof_state.py \
  --require-release-ready --audit-sources --emit-source-list
```

Expected decisive output at `ede0151a...`:

```text
[proof-state:error] release source is missing: .../scripts/verify_publication_package.py
[proof-state:ok] contract=erdos-848-all-n-four-range-v1 machine=closed manuscript=complete alignment=aligned paper_endpoints=15 lean_closure=30638
```

This is an authenticated defect check, not a success gate. Both
`verify_publication_package.py` and `build_release_package.py` are absent at
the pin, but the checker reports the first missing path. A clean proof replay
must not treat this expected failure as completion evidence.

The plain publication-contract mutation suite currently fails on macOS before
testing because it requests a temporary tree under sealed `/`. The following
runtime-only shim leaves the repository sources and test logic unchanged while
redirecting only that request to `/private/tmp`:

```sh
E848_PYDEPS="$(mktemp -d)"
python3 -m pip install --quiet --target "${E848_PYDEPS:?}" psutil==7.2.2
PYTHONPATH="${E848_PYDEPS:?}" python3 -B - <<'PY'
import importlib.util
from pathlib import Path

path = Path("scripts/test_publication_contract.py").resolve()
spec = importlib.util.spec_from_file_location("e848_contract_test", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

real_mkdtemp = module.tempfile.mkdtemp
def redirected_mkdtemp(*args, **kwargs):
    if Path(kwargs.get("dir", ".")).resolve() == Path(module.ROOT.anchor):
        kwargs["dir"] = "/private/tmp"
    return real_mkdtemp(*args, **kwargs)

module.tempfile.mkdtemp = redirected_mkdtemp
raise SystemExit(module.main())
PY
```

All 12 positive and fail-closed cases pass under the shim. This is a
portability workaround, not the required unmodified clean-release test.

## Crabsatellite clean Lean build and axiom gate

The tracked root entrypoint is locked in `lean/source-lock.json`. Its static
source/census audit is safe on this host and deliberately does not compile the
proof:

```sh
python3 -B lean/test_completion_gate.py
python3 -B lean/run_completion_gate.py --source-audit-only
```

The bounded test rejects malformed locks and axiom reports, inherited Lean
module paths, wrong-root/cache-shadowed `Erdos848` OLeans, and surviving
descendant processes. The source audit authenticates the exact 30,638-source
census and root sources but does not load Lean.

Expected terminal line:

```text
SOURCE AUDIT ONLY: no Lean build, kernel replay, or axiom gate executed
```

The actual completion command must start from the fresh ART-006 checkout made
above, before any project OLean exists. On a persistent Windows x86-64 host
with at least 64 GiB RAM and 200 GiB genuinely free disk, install the pinned
runtime and run from this repository root in PowerShell:

```powershell
python -m pip install --disable-pip-version-check "psutil==7.2.2"
elan toolchain install leanprover/lean4:v4.30.0-rc2

$receipt = "D:\erdos848-receipts\clean-$([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))"
python -B lean/run_completion_gate.py `
  --upstream-root external/erdos-848-squarefree-product `
  --receipt-dir $receipt `
  --memory-mib 32768
```

The runner refuses a non-Windows host, a dirty or mispinned source tree,
pre-existing project OLeans, insufficient resources, a moving dependency, a
forbidden axiom, a missing endpoint report, source drift, or a nonempty receipt
directory. It never runs `lake update`. It compiles the literal theorem in
`lean/Erdos848Completion/Final.lean`, runs trust zero over the complete import
closure, checks all 15 upstream plus four root axiom reports, and records the
dependency output. Only the full success path prints:

```text
LEAN COMPLETION GATE PASSED
```

The emitted receipt is still subject to independent review before it may be
copied into `lean/receipts/` or used to promote `L1`, `L2`, or `V0`.

The tracked manual workflow wraps that exact gate for a uniquely labelled,
isolated self-hosted runner. It is currently unexecuted and therefore supplies
no proof evidence or node promotion. The workflow file must first exist on the default
branch because GitHub dispatches `workflow_dispatch` only for workflows on the
default branch. Register exactly one Windows/X64 runner with the custom label
`erdos848-art006`, pre-create `D:\erdos848-verification` on the large-volume
disk, and dispatch:

```sh
gh workflow run art006-full-source-completion.yml \
  -f confirm_full_gate=true \
  -f 'persistent_root=D:\erdos848-verification'
gh run list --workflow art006-full-source-completion.yml --limit 1
```

The build job writes outside the checkout to a run-id-bound persistent
directory. A dependent job on the same uniquely labelled host receives a fresh
job token, replays the strict receipt negative controls, verifies canonical
JSON, exact types and schemas, the receipt/log hash chain, the successful build
result, and all 19 axiom endpoints, then uploads the result. Python is fixed to
`3.12.10`; the Windows `psutil==7.2.2` wheel is authenticated by the hash in
`lean/requirements-completion.txt`; Git long-path support is supplied through
per-process environment config. This split is intentional because a
self-hosted job may run longer than the documented 24-hour `GITHUB_TOKEN`
lifetime. See
`diagnostics/FULL_SOURCE_COMPLETION_ROUTE.md` for the exact host assumptions,
pilot audit, exact distinction between mutation-tested and directly validated
properties, and promotion boundary.

The documented clean source route, run from the candidate root, is:

```sh
cd lean4
lake exe cache get
cd ..
python3 -B scripts/build_generated_certificate.py \
  --kind generic \
  --module-prefix Erdos848 \
  --generic-target Erdos848.PaperGeneratedCertificateProvider \
  --workers 2 \
  --max-active-leaves 2 \
  --max-memory-mib 15360 \
  --final-max-memory-mib 32768 \
  --core-max-memory-mib 32768 \
  --leaf-timeout-seconds 1800 \
  --final-timeout-seconds 7200 \
  --core-timeout-seconds 3600 \
  --preflight-leaves 0 \
  --stage all
python3 -B scripts/run_kernel_gates.py --memory-mib 32768
```

This route has **not** completed on the current 16 GiB host. It is recorded as
a required future command, not as a passing result. The published gate needs
32,768 MiB plus a 1,024 MiB guard reserve, so a nominal 32 GiB machine is too
small. Use a persistent Windows x86-64 host with 64 GiB RAM and at least 200
GiB genuinely free storage, preferably a 300 GiB-or-larger SSD and a short
checkout path. Install and record `psutil==7.2.2`; the release imports it but
does not pin it. The exact cone, disk calculation, portability defects, and
guarded failures are in `docs/artifact-audit.md` and `docs/lean-audit.md`.
The unmodified `--direct-lean` kernel gate is Windows-only.

### Diagnostic distributed source-build pilot

The diagnostic checkpoint implementation is separately testable without Lean:

```sh
python3 -B diagnostics/test_lean_checkpoint_plan.py
```

Expected final line:

```text
ALL LEAN CHECKPOINT PILOT MUTATION CONTROLS PASSED
```

The manual GitHub Actions workflow
`.github/workflows/lean-source-checkpoint-pilot.yml` then generates an exact
two-segment plan and source-builds `Erdos848.ProblemCore` followed by
`Erdos848.SharpnessCore` on two independent Windows checkouts. The second job
may import project OLeans only from the verified first-segment artifact. Its
terminal marker is:

```text
DIAGNOSTIC SOURCE CHECKPOINT SEGMENT PASSED index=1
```

The canonical segment receipts establish byte integrity and enforce the exact
declared compiler/runtime metadata. They are not independent execution
attestations: retain the exact GitHub run identity and compile logs with any
pilot result. A caller-created receipt and OLean pair is not source-build
evidence.

This marker is intentionally not `LEAN COMPLETION GATE PASSED`. The pilot does
not cover the publication closure, root theorem, live axiom reports, or final
dependency audit, and cannot promote any pending Lean or completion node.

Pilot run `31541505450` completed both segments. Its canonical plan digest is
`6459fb1d...211c`; segment receipts are `a77dda29...4640` and
`a976945c...e84`. Replaying the downloaded plan and receipts against the exact
source pin passed. The pilot verifier deliberately accepts only genesis
parents and its artifacts carry only their own segment OLeans, so it must not
be extended naively beyond dependency depth one. The complete route is the
single-host zero-OLean gate above, not a longer direct-parent artifact chain.

Optional noninstalling APFS capacity diagnostic, which transiently uses about
2.6 GiB and downloads one 448 MiB shard:

```sh
E848_CACHE_PROBE="$(mktemp -d /private/tmp/erdos848-cache-compression.XXXXXX)"
gh release download v1.0.5-kernel \
  --pattern 'erdos848-olean-cache-lean-4.30.0-rc2-windows-x86_64-e0dd18260bd4-part-001-of-075.zip' \
  --dir "${E848_CACHE_PROBE:?}"
shasum -a 256 "${E848_CACHE_PROBE:?}"/*.zip
mkdir "${E848_CACHE_PROBE:?}/plain"
ditto -x -k "${E848_CACHE_PROBE:?}"/*.zip "${E848_CACHE_PROBE:?}/plain"
ditto --hfsCompression \
  "${E848_CACHE_PROBE:?}/plain" \
  "${E848_CACHE_PROBE:?}/compressed"
du -sk "${E848_CACHE_PROBE:?}/compressed"
du -A -sk "${E848_CACHE_PROBE:?}/compressed"
```

The audited shard hash is
`800a092f91056fe4ea67cbe51ee438d2550a0673613ff17a900c8aaa124c46c8`.
Observed allocated/apparent sizes were 543,436/1,709,044 KiB. Validate archive
paths and remove the disposable probe after inspection; this diagnostic does
not install or replay an OLean.

## Top-level all-\(N\) computational certificate

The primary orchestrator authenticates the canonical all-`N` manifest, exact
statement, ART-005 tree, source PDF, local checker implementations, and all
committed receipts. Its default profile then runs the independent prefix,
lower-`p=13`, and finite checkers; high-range exact arithmetic; all 19 ART-005
positive and negative stages; and the final closed-range audit.

Use one Python interpreter consistently for the pinned GMP backend. A
theorem-grade run must use a fresh empty work directory outside the repository
and must not pass `--resume`:

```sh
E848_PYTHON="${E848_PYTHON:-python3}"
E848_ALLN_GMPY="$(mktemp -d /tmp/erdos848-all-n-gmpy.XXXXXX)"
test -d "${E848_ALLN_GMPY:?}"
"${E848_PYTHON:?}" -m pip install \
  --disable-pip-version-check \
  --target "${E848_ALLN_GMPY:?}" \
  'gmpy2==2.2.1'

E848_ALLN_WORK="${E848_ALLN_WORK:?set an absolute persistent path outside the repository}"
test "${E848_ALLN_WORK#/}" != "${E848_ALLN_WORK}"
mkdir -p "${E848_ALLN_WORK:?}"

PYTHONPATH="${E848_ALLN_GMPY:?}" "${E848_PYTHON:?}" -B \
  scripts/check_certificate.py \
  --work-dir "${E848_ALLN_WORK:?}"
```

Expected final line:

```text
ALL-N COMPUTATIONAL CERTIFICATE PASSED
```

After interruption, `--resume` may be used to finish diagnostic work from
verified stage boundaries. Every checkpoint is reauthenticated against the
manifest, dependency receipts, commands, tool versions, output hashes, and log
hash. These unsigned local checkpoints cannot attest execution provenance, so
a resumed chain emits only `resumed-checkpoint-chain-validated` and never the
theorem-grade PASS. To discharge `CD0`, start again in a new empty directory
and complete all six stages uninterrupted. Neither a partial stage,
`--preflight-only`, nor `--resume` emits the final theorem-grade PASS.

Fast schema, Boolean/float, path, symlink/reparse, coverage-gap, checkpoint,
output, dependency, interruption, process-tree, and provenance controls are
independently runnable:

```sh
python3 -B computations/test_all_n_manifest.py
python3 -B computations/test_all_n_resume.py
```

For an identity and environment audit that performs no decisive computation:

```sh
E848_PREFLIGHT_WORK="$(mktemp -d /tmp/erdos848-all-n-preflight.XXXXXX)"
PYTHONPATH="${E848_ALLN_GMPY:?}" "${E848_PYTHON:?}" -B \
  scripts/check_certificate.py \
  --work-dir "${E848_PREFLIGHT_WORK:?}" \
  --preflight-only
```

Its terminal line explicitly says that no computational theorem was
certified. The full stage commands below remain documented separately for
direct inspection and diagnosis.

## Independent ART-005 all-\(N\) release replay

Run from `external/erdos-848-all-n`, using the authenticated Sothanaphan PDF:

```sh
python3 -u audit/run_release_replay.py \
  --source-pdf ../../sources/cache/sothanaphan-2.64e17.pdf \
  --jobs 4
```

The public `HEAD` wrapper has 19 stages. Do not treat the repository's own
preserved 18-stage source receipt as an independent replay of this later tree;
the additional stage is the optimized-Python fail-closed control. The
independent full-profile replay completed successfully on 2026-08-10:

```text
PASS complete_all_n_local_replay profile=full stages=19 source_pdf_sha256=8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f
PASS release_manifest_postflight files=131 inventory=132 manifest_sha256=6f197f0d5bef00c97275915ee21dcf8891543eab54dda9312c4227bbde927573
PASS complete_fresh_extraction_release_replay files=131 manifest_sha256=6f197f0d5bef00c97275915ee21dcf8891543eab54dda9312c4227bbde927573
```

The replay covered the exact closed ranges `[1,100000006]`,
`[100000000,1000000000]`, `[1000000000,1000000000000]`,
`[1000000000000,264000000000000000]`, and
`[264000000000000000,infinity)`. Its range-ledger digest was
`b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1`.
See `certificates/ipitchford-all-n-replay-2026-08-10.md` for all stage timings,
decisive certificate identities, and the raw-log limitation.

## Independent lower-\(p=13\) factor primality

Install the exact accelerated integer backend into a disposable directory and
recreate the canonical certificate:

```sh
E848_GMPY_DIR="$(mktemp -d /tmp/erdos848-gmpy2.XXXXXX)"
test -n "${E848_GMPY_DIR:?}"
python3 -m pip install \
  --disable-pip-version-check \
  --target "${E848_GMPY_DIR:?}" \
  'gmpy2==2.2.1'

E848_P13_CERT="$(mktemp /tmp/erdos848-p13-certificate.XXXXXX)"
test -n "${E848_P13_CERT:?}"
PYTHONPATH="${E848_GMPY_DIR:?}" python3 -B \
  computations/check_p13_factor_primality.py \
  external/erdos-848-all-n/audit/p13_interval_factors_1000000000.tsv.gz \
  --certificate-output "${E848_P13_CERT:?}"
shasum -a 256 "${E848_P13_CERT:?}"
cmp "${E848_P13_CERT:?}" certificates/p13-factor-primality.json
```

Audited versions and identities:

```text
checker SHA-256:
71403895bd9a06a131a4ca84bf5d7260e7be8484488e9dfc7514364921581899

gmpy2 / GMP:
gmpy2 2.2.1 / GMP 6.3.0

canonical certificate SHA-256:
cb67a19e9edfc21206b6ec0c886bf6aa67b97a110296f7e20bf00bdf818cfc64

decisive result:
gcd=1
INDEPENDENT P13 FACTOR PRIMALITY AUDIT PASSED
```

The certificate must compare byte-for-byte. The pure-Python backend is exact
but is only a slow reference path; the command above is the reproduced
theorem-grade run.

## Independent finite stream through 100,000,006

The exact finite pipeline requires a C++20 compiler with zlib and
`unsigned __int128` support (GCC or Clang), a Java runtime, and one pinned
Python interpreter with `gmpy2==2.2.1` backed by GMP 6.3.0. Do not mix the
interpreter that installs the wheel with the interpreter that runs the
checker. Set `E848_PYTHON` to that interpreter, or allow the command to use
`python3`:

```sh
E848_PYTHON="${E848_PYTHON:-python3}"
"${E848_PYTHON:?}" -c 'import sys; assert sys.version_info >= (3, 9)'

E848_FINITE_GMPY="$(mktemp -d /tmp/erdos848-finite-gmpy.XXXXXX)"
test -d "${E848_FINITE_GMPY:?}"
"${E848_PYTHON:?}" -m pip install \
  --disable-pip-version-check \
  --target "${E848_FINITE_GMPY:?}" \
  'gmpy2==2.2.1'

PYTHONPATH="${E848_FINITE_GMPY:?}" "${E848_PYTHON:?}" -B \
  scripts/independent_check.py
```

A clean host must use the same `E848_PYTHON` value for both commands and record the
Python, gmpy2, GMP, compiler, zlib, Java, and platform versions.  The
orchestrator authenticates candidate revision
`1afd7c722cae5ee7dd0fd1fde64427537394f749`, both certificate streams, every
checker source, and the committed receipt before compiling anything.

Expected final line:

```text
INDEPENDENT THEOREM-GRADE FINITE PIPELINE PASSED
```

Decisive authenticated identities are:

```text
base stream:
3380a6778d237a3fd2a1f01c7ea72292e470a845b09eea99beb66ca85434ba98

compact stream:
9917ec4590f69efd8c6f7d30d54ecf5284e92f185ec70a4d14657acb02551b12

C++ verifier:
b891896e89b943eda2baa0bfe2903ffecc0806c53a301206f18bdd74b78bdc5d

factor leaves:
56720662876aaddcf5c0706d672d450f85db4f0606c00ba3875c514af7be22fa

Java exporter:
45c0d97ab1469a9ab63b4a18905ee59b559907b73f3dca70cbd3212823c2a9e5

GMP finisher:
e686dcaa7c2b668324d83227dbdc36846f1ea5787be3cb1f6aed7daa1c792ac5

canonical receipt:
4fc75b0ed263df81c07c5997c915511351ea61fff085d3ac95159c524ca9aad6
```

The positive run must report 4,000 fully checked base endpoints, 3,996,000
fully checked compact transitions, `18,049,789` base pair occurrences,
`14,458,371/14,458,371` compact pair occurrences, and `11,108,162` factor
leaves.  The exact leaf certificate must report `gcd=1`; its injected factor
control must report `gcd=2`.  The endpoint-401 repaired-state mutation must
fail specifically with `endpoint pair is nonsquarefree` and must not emit a
leaf file.

For optional undefined-behavior hardening, repeat the same command with:

```sh
PYTHONPATH="${E848_FINITE_GMPY:?}" "${E848_PYTHON:?}" -B \
  scripts/independent_check.py --ubsan
```

The sanitizer is not a mathematical premise; the exact full replay and leaf
certificate are.  The canonical mutation gzip is pinned to the audited
Python/zlib serialization and may fail closed on a platform that emits a
different but semantically equivalent gzip stream.  See
`certificates/finite-stream-replay-2026-08-10.md` for direct component
commands, counts, timings, and negative controls.

## Independently audited explicit high range

Authenticate and replay the numerical claims used in SRC-007:

```sh
E848_PYTHON="${E848_PYTHON:-python3}"
"${E848_PYTHON:?}" \
  -B external/erdos-848-all-n/audit/verify_high_threshold_numerics_v1.py \
  --source-pdf sources/cache/sothanaphan-2.64e17.pdf \
  --self-test
```

Expected identities:

```text
source PDF SHA-256:
8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f

script SHA-256:
48d4838137c9b2220a1a5c0677a2b3eb9f919f49e36da49b5f31cd654a0c52e9

canonical claims SHA-256:
4726814d80fc63353a77c18bac8691bc917efd5ef1c7dcf10a14aed03674b215
```

All exact-arithmetic self-tests and the deliberately weakened controls must
pass/fail in the declared directions. The four final strict upper bounds for
`|A| / N` at the threshold are:

```text
case 1   0.0399991921982178202
case 2a  0.0381332461716985859
case 2b  0.0358631467684126345
case 3   0.0297541013386074487
```

The numerical replay is paired with the line-by-line mathematical audit
recorded in `docs/source-audit.md`; numerics alone would not prove H0.

## Independent exact prefix certificate through 10,000

Generate the certificate from modular prime-square adjacency:

```sh
python3 -B computations/generate_prefix_certificate.py \
  --limit 10000 \
  --output certificates/prefix-10000.json
```

Expected summary:

```text
limit=10000
vertices=1048
edges=251854
records=401
bytes=696999
sha256=693ce882fb3f3786caf8eb502dd0677f42a4ed687adaa71a613b27ad7ef49727
```

Check the exact bytes with the independent direct-factorization implementation:

```sh
python3 -B computations/check_prefix_certificate.py \
  certificates/prefix-10000.json \
  --expected-sha256 \
  693ce882fb3f3786caf8eb502dd0677f42a4ed687adaa71a613b27ad7ef49727
```

Expected decisive lines:

```text
VERIFIED exact prefix certificate
same_colour_pairs=328521
statement_controls=passed
```

Run all malformed-schema, semantic, and interval-coverage mutations:

```sh
python3 -B computations/test_prefix_checker.py \
  certificates/prefix-10000.json
```

Expected final line:

```text
ALL PREFIX CHECKER MUTATION CONTROLS PASSED
```

Run the third, naive exhaustive oracle through 100:

```sh
python3 -B computations/exhaustive_small_prefix.py --limit 100
```

Expected output:

```text
VERIFIED exhaustive subsets for every 1 <= N <= 100; eligible_vertices=12
```

## Reviewer-feedback spot checks

Reproduce the independent-review checkpoint at endpoint `N=5006` without
altering the committed prefix certificate:

```sh
E848_REVIEW_PREFIX="$(mktemp /tmp/erdos848-review-5006.XXXXXX)"
python3 -B computations/generate_prefix_certificate.py \
  --limit 5006 \
  --output "${E848_REVIEW_PREFIX:?}"
python3 -B computations/check_prefix_certificate.py \
  "${E848_REVIEW_PREFIX:?}"
```

Expected generator counts are `vertices=526`, `edges=63102`, `records=201`,
and SHA-256
`c7a47b791149ddd8db369a967a1711a0282d68e2beefb609e9290bd94711ac4f`.
The independent checker must end with `statement_controls=passed`; the endpoint
benchmark is `(5006+18)/25=200`.

Recheck the translated-pair discriminant used in the middle-range Pell bound
using only exact integer arithmetic and trial-division primality:

```sh
python3 -B - <<'PY'
import math

d = 863_167_536
factors = [2, 2, 31, 13_922_057, 431_583_769]
assert math.prod(factors) == d * d - 4
for n in sorted(set(factors)):
    for p in range(2, math.isqrt(n) + 1):
        assert n % p, (n, p)
assert d % 25 == 11
assert all(d % modulus == 0 for modulus in (4, 9, 49, 121))
print("factorization=2^2*31*13922057*431583769")
print("all_distinct_non2_factors_prime=passed")
print("tau=24")
print("translation_congruences=passed")
PY
```

These are targeted corroboration checks, not replacements for the complete
structural replay.
