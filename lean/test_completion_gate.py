#!/usr/bin/env python3
"""Bounded negative controls for the guarded Lean completion runner."""

from __future__ import annotations

import copy
import importlib.util
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "lean" / "run_completion_gate.py"


def load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("erdos848_completion_gate", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Lean completion runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(runner: Any, action: Callable[[], None], label: str) -> None:
    try:
        action()
    except runner.GateFailure:
        print(f"REJECTED {label}")
        return
    raise RuntimeError(f"Lean completion gate accepted negative control: {label}")


def main() -> int:
    runner = load_runner()
    lock = runner.read_lock()
    print("ACCEPTED canonical source lock")

    original_lock_path = runner.LOCK_PATH
    with tempfile.TemporaryDirectory(prefix="erdos848-lean-lock-controls-") as raw:
        temporary_lock = Path(raw) / "source-lock.json"
        runner.LOCK_PATH = temporary_lock

        extra = copy.deepcopy(lock)
        extra["unexpected"] = "forbidden"
        temporary_lock.write_bytes(runner.canonical_json(extra))
        expect_rejected(runner, runner.read_lock, "extra source-lock key")

        reordered = {key: lock[key] for key in reversed(tuple(lock))}
        temporary_lock.write_bytes(runner.canonical_json(reordered))
        expect_rejected(runner, runner.read_lock, "reordered source-lock keys")

        boolean_count = copy.deepcopy(lock)
        boolean_count["endpoint"]["provider_modules"] = True
        temporary_lock.write_bytes(runner.canonical_json(boolean_count))
        expect_rejected(runner, runner.read_lock, "Boolean source-lock count")

        canonical_text = runner.canonical_json(lock).decode("ascii")
        duplicate = canonical_text.replace(
            '  "version": 1,\n', '  "version": 1,\n  "version": 1,\n', 1
        )
        temporary_lock.write_text(duplicate, encoding="ascii")
        expect_rejected(runner, runner.read_lock, "duplicate source-lock key")

    runner.LOCK_PATH = original_lock_path

    axiom_lines = [
        f"'{endpoint}' depends on axioms: [propext, Classical.choice, Quot.sound]"
        for endpoint in runner.ENDPOINTS
    ]
    reports = runner.parse_axioms("\n".join(axiom_lines))
    if set(reports) != set(runner.ENDPOINTS):
        raise RuntimeError("complete axiom report lost an endpoint")
    print("ACCEPTED complete allowed-axiom report")
    expect_rejected(
        runner,
        lambda: runner.parse_axioms("\n".join(axiom_lines[:-1])),
        "missing axiom endpoint",
    )
    expect_rejected(
        runner,
        lambda: runner.parse_axioms("\n".join((*axiom_lines, axiom_lines[0]))),
        "duplicate axiom endpoint",
    )
    forbidden = list(axiom_lines)
    forbidden[0] = forbidden[0].replace("Quot.sound", "Erdos848.customAxiom")
    expect_rejected(
        runner,
        lambda: runner.parse_axioms("\n".join(forbidden)),
        "forbidden axiom",
    )

    environment = runner.sanitized_lean_environment(
        {
            "LEAN_PATH": "/tmp/untrusted",
            "LEAN_SRC_PATH": "/tmp/untrusted-src",
            "LEAN_PKG_PATH": "/tmp/untrusted-pkg",
            "PATH": "/usr/bin",
        }
    )
    if set(environment) != {"PATH"}:
        raise RuntimeError("caller-controlled Lean path survived sanitization")
    print("REMOVED inherited Lean module paths")

    with tempfile.TemporaryDirectory(prefix="erdos848-lean-path-controls-") as raw:
        base = Path(raw)
        project = base / "project"
        completion = base / "completion"
        untrusted = base / "untrusted"
        provider = project / "Erdos848" / "PaperGeneratedCertificateProvider.olean"
        hall = project / "Erdos848" / "HallReduction.olean"
        sharp = project / "Erdos848" / "SharpnessCore.olean"
        final = completion / "Erdos848Completion" / "Final.olean"
        bad_provider = (
            untrusted / "Erdos848" / "PaperGeneratedCertificateProvider.olean"
        )
        for path in (provider, hall, sharp, final, bad_provider):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test olean\n")

        runner.require_namespace_provenance(
            (project,), project_root=project, completion_root=None
        )
        runner.require_namespace_provenance(
            (completion, project),
            project_root=project,
            completion_root=completion,
        )
        print("ACCEPTED exact project and completion namespace roots")
        expect_rejected(
            runner,
            lambda: runner.require_namespace_provenance(
                (project, untrusted),
                project_root=project,
                completion_root=None,
            ),
            "cache-shadowed Erdos848 namespace",
        )

        final_output = "\n".join(str(path) for path in (provider, hall, sharp))
        runner.require_direct_dependencies(
            final_output,
            expected={
                "Erdos848.PaperGeneratedCertificateProvider": provider,
                "Erdos848.HallReduction": hall,
                "Erdos848.SharpnessCore": sharp,
            },
            label="synthetic final",
        )
        runner.require_direct_dependencies(
            str(final),
            expected={"Erdos848Completion.Final": final},
            label="synthetic audit",
        )
        print("ACCEPTED exact direct-import roots")
        expect_rejected(
            runner,
            lambda: runner.require_direct_dependencies(
                str(bad_provider),
                expected={
                    "Erdos848.PaperGeneratedCertificateProvider": provider,
                },
                label="synthetic wrong-root",
            ),
            "right module from wrong OLean root",
        )

    with tempfile.TemporaryDirectory(prefix="erdos848-lean-tree-control-") as raw:
        receipt = Path(raw)
        child_pid = receipt / "child.pid"
        command = (
            sys.executable,
            "-c",
            (
                "import pathlib,subprocess,sys,time;"
                "child=subprocess.Popen([sys.executable,'-c',"
                "'import time; time.sleep(60)']);"
                f"pathlib.Path({str(child_pid)!r}).write_text(str(child.pid));"
                "time.sleep(60)"
            ),
        )
        expect_rejected(
            runner,
            lambda: runner.run_logged(
                "timed-out-tree", command, ROOT, receipt, 1
            ),
            "timed-out Lean process tree",
        )
        if not child_pid.is_file():
            raise RuntimeError("Lean process-tree control did not record its child")
        pid = int(child_pid.read_text(encoding="utf-8"))
        time.sleep(0.2)
        try:
            os.kill(pid, 0)
        except OSError:
            pass
        else:
            raise RuntimeError("Lean runner left a descendant process alive")
        print("NO DESCENDANT after timed-out Lean command")

    print("ALL LEAN COMPLETION GATE MUTATION CONTROLS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
