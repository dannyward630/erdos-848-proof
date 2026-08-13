# ART-006 full source completion route

## Exact pilot result and boundary

GitHub Actions run
[`31541505450`](https://github.com/dannyward630/erdos-848-proof/actions/runs/31541505450)
completed successfully at diagnostic commit
`da76df98d1ab67826685444cf4bf3946fd783b50`.  An independent download and
replay against ART-006 revision
`ede0151a35c86b6395cf67dd034811d22a92c7ba` verified:

- canonical plan SHA-256
  `6459fb1dd7094bbe4763d4b0350104e26408242dcc9a662641d85de0f2cd211c`;
- zero-project-OLean `ProblemCore` output SHA-256
  `e1455c5e0883259cc895c07681378570954d8e1fc7c6cbc22a9e162c1ea9635a`
  and receipt SHA-256
  `a77dda290fe49a465dc04a2b3e901a8fa7c6c445cfb2c8a7de9dcb81cbc44640`;
- dependent `SharpnessCore` output SHA-256
  `4bbe814d36caf9bff3a4c5d5b51b8e4c0b8ce497b14e39dee7e35a72b4e4ede4`
  and receipt SHA-256
  `a976945c2e0130104483eec10978194081953958875dcb42478210c34b267e84`;
- exact compile flags `--trust=0 -q -M 24576 -D
  compiler.postponeCompile=true`, Windows/X64, and Lean
  `v4.30.0-rc2` commit `3dc1a088...`; and
- every committed checkpoint mutation control.

The GitHub artifact ZIP digests recorded by the run were
`7b322aeec889a2a0c4dc27677b62578138f1ba91af252e27c53505217c618513`
for the plan,
`9495eba7d6835b268351cb000b9281ec072274f783f3fddde2fadc6b766427cb`
for segment 0, and
`68ce5c92649ff6b1794656ced0c6fb4aff1504fa1f65f7114d260eff820de8ef`
for segment 1.  A fresh API download on 2026-08-13 produced a valid eight-file
run-log ZIP with SHA-256
`f62acc5c68cf938974282479ff3cf4edc98537f61c23389f8b1ee382612e643c`.

These receipts claim byte integrity only.  The GitHub run and its logs supply
the execution provenance.  The run compiled two of the 30,636 provider
modules and did not run the final theorem, trust-zero root replay, live axiom
gate, or dependency gate.  It cannot promote `LROOT`, `L1`, `L2`, `RCLEAN`,
`V0`, or `P848`.

## Why the pilot must not simply be lengthened

The bounded pilot deliberately accepts only a genesis parent.  Its verifier
rejects a parent that itself has parents, and each artifact carries only its
own segment OLeans.  At dependency depth two, importing only the direct parent
can omit transitive project OLeans.  Thus changing the target to the final
provider or raising `modules-per-segment` does not create a sound full-build
protocol.  This is `REVISE_DECOMPOSITION`, not a Lean or mathematical proof
failure.

Standard public GitHub-hosted Windows runners are also the wrong completion
host.  GitHub currently documents 16 GB RAM and a six-hour job limit for
standard hosted Windows jobs, while the authenticated gate requires 64 GiB
physical RAM, 33,792 MiB available at launch, 200 GiB free storage, a 32,768
MiB Lean ceiling, and permits 48 hours for the source-build subprocess.  The
provider closure is 30,636 modules; the published comparison cache occupies
129,476,102,424 logical bytes and about 52.9 GB when individually measured
under NTFS compression.  The cache is not source-build evidence because
FL-014 disproved source/cache byte equality.

Current platform limits are documented at:

- <https://docs.github.com/en/actions/reference/limits>
- <https://docs.github.com/en/actions/reference/runners/github-hosted-runners>
- <https://docs.github.com/en/actions/reference/runners/self-hosted-runners>

## Fastest sound execution

The workflow is prepared but has **not been executed**.  Its presence records
the exact next route and promotes no proof-DAG node.

As of 13 August 2026, the maintainer has confirmed that no qualifying host is
available. A live account and environment audit found zero registered
self-hosted runners and no configured cloud or VM route. The workflow is
published so an external verifier can execute the exact reviewed procedure;
its unexecuted state is the sole external infrastructure boundary for the
remaining formal nodes.

Use one isolated Windows x86-64 self-hosted runner with at least 64 GiB RAM
and 200 GiB genuinely free SSD storage.  Give exactly that runner the custom
label `erdos848-art006`, pre-create a large-volume directory such as
`D:\erdos848-verification`, and keep the runner offline except for this manual
dispatch.  The public-repository security implications of a self-hosted runner
must be respected; do not expose the label to pull-request-triggered workflows.

Dispatch `.github/workflows/art006-full-source-completion.yml` with
`confirm_full_gate=true`.  The workflow:

1. checks out both repositories at exact revisions without persisted GitHub
   credentials;
2. enables Git-for-Windows long-path handling without mutating host config,
   selects Python `3.12.10`, installs the hash-authenticated Windows
   `psutil==7.2.2` wheel, and authenticates the pinned Lean Windows ZIP before
   placing Lean/Lake on `PATH`;
3. initializes a fresh persistent run root bound to the run id, attempt,
   commit, and runner name;
4. runs the completion mutation suite and source-only census;
5. invokes `lean/run_completion_gate.py` from zero project OLeans;
6. source-builds the complete 30,636-module provider, runs the upstream
   trust-zero theorem map and 15 live axiom endpoints, compiles the literal
   positive-`N` root theorem, checks four root axiom endpoints, and records
   both dependency reports; and
7. uses a second job on the same uniquely labelled host to replay the bounded
   metadata/schema mutation controls, then strictly validates canonical JSON,
   exact types and schemas, the successful build result, every expected log
   byte, the root OLean, dependencies, and all 19 endpoint reports before
   uploading the persistent receipt tree with a fresh `GITHUB_TOKEN`.  This
   avoids the documented 24-hour token lifetime becoming an
   artifact-publication failure after a long source build.  The bounded
   mutation suite directly covers duplicate keys, noncanonical JSON, schema
   extensions and ordering, Boolean/integer coercions, and digest mutation; the
   other listed properties are validator checks, not separately mutated
   integration fixtures.

The equivalent direct command on a prepared host is:

```powershell
python -m pip install --disable-pip-version-check --only-binary=:all: `
  --require-hashes --requirement lean/requirements-completion.txt
# Download, SHA-256-check, and freshly extract the exact Windows runtime as in
# REPRODUCE.md, then set $runtimeBin to its canonical bin directory.

$receipt = "D:\erdos848-verification\manual-$([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))"
python -B lean/test_completion_gate.py
python -B lean/run_completion_gate.py `
  --upstream-root external/erdos-848-squarefree-product `
  --source-audit-only
python -B lean/run_completion_gate.py `
  --upstream-root external/erdos-848-squarefree-product `
  --runtime-bin $runtimeBin `
  --receipt-dir $receipt `
  --memory-mib 32768
```

The host must expose the exact archive-authenticated Lean `v4.30.0-rc2`
runtime through that explicit fresh extraction directory and must begin with
no `Erdos848` project OLeans. Do not run `lake update`.

## Promotion boundary

Only the full gate's terminal line `LEAN COMPLETION GATE PASSED`, canonical
receipt, authenticated raw logs, exact 30,636-module post-build inventory, all
19 live endpoint reports, root `Final.olean`, and both dependency reports can
be submitted to an independent reviewer.  The artifact deliberately does not
claim to contain the roughly 129 GB of provider OLean bytes; those remain in
the source checkout on the execution host.  Their evidentiary role is the
strictly guarded source-build, inventory, namespace-provenance, trust-zero,
axiom, and dependency execution, not a byte-for-byte published OLean archive.
The workflow's success and artifact upload are not self-certification.
`LROOT`, `L1`, `L2`, and `RCLEAN` remain unverified until that independent
review passes; `V0` and `P848` remain downstream of them.
