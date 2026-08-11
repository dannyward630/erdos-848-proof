# AGENTS.md — Erdős Problem 848 Research Protocol

## Mission

Complete a rigorous proof or exact disproof of Erdős Problem 848 for every positive integer (N).

Use the working hypothesis that the conjecture is true and that a complete proof can be found. This hypothesis governs persistence, not standards of evidence. An exact counterexample overrides it.

## Repository map

Read these files at the beginning of every new root or subagent run:

- `docs/problem-spec.md` — authoritative natural-language and formal statements
- `docs/source-audit.md` — sources, claims, and verification status
- `docs/proof-dag.yaml` — current decomposition and dependencies
- `docs/proof-ledger.md` — proved, conditional, refuted, and unverified claims
- `docs/failed-lemmas.md` — exact counterexamples and failed approaches
- `docs/computation-spec.md` — mathematical meaning of every computation
- `docs/handoff.md` — current state and next actions
- `REPRODUCE.md` — environment and verification commands

Never rely on an important fact that exists only in chat history.

## Operating rules

1. Preserve the exact problem. Audit every formal statement against the original before proving it.
2. Separate:

- exploration,
- proof construction,
- structural verification,
- detailed verification,
- formalization,
- computation.

3. A proof-producing agent must not certify its own proof.
4. Spawn as many useful subagents as the environment supports. Use isolated worktrees for incompatible approaches.
5. Preserve independence during initial exploration. Do not reveal the favored strategy to every agent.
6. Every subagent must return a structured, self-contained report with:

- claim attempted;
- exact result;
- proof or certificate location;
- dependencies;
- unresolved gap;
- discovered counterexamples;
- recommended next action.

7. Record every false load-bearing lemma in `docs/failed-lemmas.md`.
8. State each durable instruction once. Put details in the relevant `docs/` file rather than expanding this file.
9. Before context compaction, handoff, or termination, update `docs/handoff.md`.
10. On resumption, read `docs/handoff.md` before acting.

## Truth and verification rules

Do not accept:

- numerical evidence as a proof;
- a finite check without a proof that it covers every required case;
- an opaque solver result without a certificate;
- a Lean file merely because it compiles;
- `sorry`, `admit`, custom axioms, or theorem-strength hypotheses;
- a circular theorem interface;
- a formal theorem whose statement is weaker than the original;
- a citation until its exact statement and hypotheses have been inspected;
- a claim that “the remaining cases are routine.”

For Lean deliverables, run and record:

- a full clean build;
- `#print axioms` on every final theorem;
- a dependency audit;
- a comparison between the formal and original statements.

For computational deliverables, require:

- two independently implemented checkers where practical;
- deterministic reproduction;
- exact integer or rational arithmetic;
- a documented certificate format;
- negative controls that the checker rejects;
- complete interval or case coverage.

## Retry state machine

After a failed verification, classify the failure as exactly one of:

- `REPAIR_EXECUTION` — sound plan, local proof error;
- `REVISE_DECOMPOSITION` — missing or false intermediate claim;
- `REWRITE_APPROACH` — central strategy is inadequate;
- `AUDIT_STATEMENT` — target or assumptions were misstated;
- `DISPROVE_HELPER` — actively seek the smallest counterexample to the helper claim;
- `AUDIT_COMPUTATION` — encoding, coverage, or certificate is uncertain.

Do not repeatedly patch an approach classified `REWRITE_APPROACH`.

## Commands

Document all build, test, search, certificate, and Lean commands in `REPRODUCE.md`. Keep them runnable from a clean checkout.

## Completion bar

Declare the original problem proved only when:

- every (N\ge1) is covered;
- every analytic threshold is explicit and justified;
- every finite interval is covered by a sound theorem or exact certificate;
- the formal and informal statements agree;
- all decisive dependencies are verified;
- independent reviewers fail to identify a gap;
- the final proof and reproduction instructions are self-contained.
