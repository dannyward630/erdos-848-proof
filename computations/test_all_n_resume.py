#!/usr/bin/env python3
"""Negative controls for all-N stage checkpoints and resume validation."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_certificate.py"


def load_checker() -> Any:
    spec = importlib.util.spec_from_file_location("all_n_certificate_checker", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load all-N checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(checker: Any, action: Any, label: str) -> None:
    try:
        action()
    except checker.CheckFailure:
        print(f"REJECTED {label}")
        return
    raise RuntimeError(f"resume checker accepted negative control: {label}")


def main() -> int:
    checker = load_checker()
    tools = {"test_runtime": sys.version.split()[0]}
    payload = b"exact fake output\n"
    payload_sha256 = hashlib.sha256(payload).hexdigest()

    with tempfile.TemporaryDirectory(prefix="all-n-resume-controls-") as raw_temp:
        work = Path(raw_temp)
        output = work / "output.bin"
        command = (
            sys.executable,
            "-c",
            (
                "from pathlib import Path;"
                f"Path({str(output)!r}).write_bytes({payload!r});"
                "print('FAKE STAGE PASSED')"
            ),
        )
        common = {
            "stage": "fake-stage",
            "commands": (command,),
            "cwd": ROOT,
            "work_dir": work,
            "timeouts": (30,),
            "markers": ("FAKE STAGE PASSED",),
            "expected_outputs": {output: payload_sha256},
            "manifest_sha256": "1" * 64,
            "tools": tools,
            "dependency_receipts": (),
            "postcheck": None,
        }
        first = checker.run_stage(**common, resume=False)
        resumed = checker.run_stage(**common, resume=True)
        if resumed != first:
            raise RuntimeError("verified resume changed the stage receipt")
        print("ACCEPTED exact checkpoint")

        log = work / "stages" / "fake-stage.log"
        receipt = work / "stages" / "fake-stage.json"
        original_log = log.read_bytes()
        original_receipt = receipt.read_bytes()

        log.write_bytes(original_log + b"corrupt\n")
        expect_rejected(
            checker,
            lambda: checker.run_stage(**common, resume=True),
            "corrupt log",
        )
        log.write_bytes(original_log)

        receipt.write_bytes(original_receipt + b" ")
        expect_rejected(
            checker,
            lambda: checker.run_stage(**common, resume=True),
            "corrupt checkpoint",
        )
        receipt.write_bytes(original_receipt)

        output.write_bytes(b"wrong output\n")
        expect_rejected(
            checker,
            lambda: checker.run_stage(**common, resume=True),
            "corrupt output",
        )
        output.write_bytes(payload)

        changed_dependencies = dict(common)
        changed_dependencies["dependency_receipts"] = ("2" * 64,)
        expect_rejected(
            checker,
            lambda: checker.run_stage(**changed_dependencies, resume=True),
            "dependency drift",
        )

        changed_manifest = dict(common)
        changed_manifest["manifest_sha256"] = "3" * 64
        expect_rejected(
            checker,
            lambda: checker.run_stage(**changed_manifest, resume=True),
            "manifest drift",
        )

    with tempfile.TemporaryDirectory(prefix="all-n-interrupt-control-") as raw_temp:
        work = Path(raw_temp)
        failing = (sys.executable, "-c", "print('PARTIAL'); raise SystemExit(7)")
        expect_rejected(
            checker,
            lambda: checker.run_stage(
                stage="interrupted",
                commands=(failing,),
                cwd=ROOT,
                work_dir=work,
                timeouts=(30,),
                markers=("SHOULD NOT PASS",),
                expected_outputs={},
                manifest_sha256="4" * 64,
                tools=tools,
                dependency_receipts=(),
                resume=False,
                postcheck=None,
            ),
            "interrupted stage",
        )
        if (work / "stages" / "interrupted.json").exists():
            raise RuntimeError("interrupted stage wrote a valid checkpoint")
        print("NO CHECKPOINT after interrupted stage")

    with tempfile.TemporaryDirectory(prefix="all-n-process-tree-control-") as raw_temp:
        work = Path(raw_temp)
        child_pid = work / "child.pid"
        spawn_tree = (
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
            checker,
            lambda: checker.run_stage(
                stage="timed-out-tree",
                commands=(spawn_tree,),
                cwd=ROOT,
                work_dir=work,
                timeouts=(1,),
                markers=(),
                expected_outputs={},
                manifest_sha256="4" * 64,
                tools=tools,
                dependency_receipts=(),
                resume=False,
            ),
            "timed-out process tree",
        )
        if not child_pid.is_file():
            raise RuntimeError("process-tree control did not record its child")
        pid = int(child_pid.read_text(encoding="utf-8"))
        time.sleep(0.2)
        try:
            os.kill(pid, 0)
        except OSError:
            pass
        else:
            raise RuntimeError("timed-out stage left a descendant process alive")
        print("NO DESCENDANT after timed-out stage")

    with tempfile.TemporaryDirectory(prefix="all-n-auth-control-") as raw_temp:
        work = Path(raw_temp)
        output = work / "must-not-exist.bin"
        command = (
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'bad')",
        )

        def reject_authentication() -> None:
            raise checker.CheckFailure("simulated source drift")

        expect_rejected(
            checker,
            lambda: checker.run_stage(
                stage="precheck-drift",
                commands=(command,),
                cwd=ROOT,
                work_dir=work,
                timeouts=(30,),
                markers=(),
                expected_outputs={},
                manifest_sha256="8" * 64,
                tools=tools,
                dependency_receipts=(),
                resume=False,
                precheck=reject_authentication,
                postcheck=None,
            ),
            "pre-stage source drift",
        )
        if output.exists() or (work / "stages" / "precheck-drift.json").exists():
            raise RuntimeError("failed precheck allowed command or checkpoint")
        print("NO COMMAND after failed precheck")

        post_output = work / "post-output.bin"
        post_payload = b"postcheck output\n"
        post_sha256 = hashlib.sha256(post_payload).hexdigest()
        post_command = (
            sys.executable,
            "-c",
            (
                "from pathlib import Path;"
                f"Path({str(post_output)!r}).write_bytes({post_payload!r});"
                "print('POSTCHECK STAGE PASSED')"
            ),
        )
        expect_rejected(
            checker,
            lambda: checker.run_stage(
                stage="postcheck-drift",
                commands=(post_command,),
                cwd=ROOT,
                work_dir=work,
                timeouts=(30,),
                markers=("POSTCHECK STAGE PASSED",),
                expected_outputs={post_output: post_sha256},
                manifest_sha256="9" * 64,
                tools=tools,
                dependency_receipts=(),
                resume=False,
                precheck=None,
                postcheck=reject_authentication,
            ),
            "post-stage source drift",
        )
        if (work / "stages" / "postcheck-drift.json").exists():
            raise RuntimeError("failed postcheck wrote a valid checkpoint")
        print("NO CHECKPOINT after failed postcheck")

    with tempfile.TemporaryDirectory(prefix="all-n-workdir-controls-") as raw_temp:
        base = Path(raw_temp)
        owner = base / "owned"
        accepted = checker.initialize_work_dir(
            owner, manifest_sha256="5" * 64, orchestrator_sha256="6" * 64
        )
        if accepted != owner.resolve():
            raise RuntimeError("work-directory owner path changed unexpectedly")
        checker.initialize_work_dir(
            owner, manifest_sha256="5" * 64, orchestrator_sha256="6" * 64
        )
        print("ACCEPTED owned work directory")

        expect_rejected(
            checker,
            lambda: checker.initialize_work_dir(
                owner,
                manifest_sha256="5" * 64,
                orchestrator_sha256="7" * 64,
            ),
            "stale work-directory owner",
        )

        foreign = base / "foreign"
        foreign.mkdir()
        (foreign / "unrelated.txt").write_text("do not overwrite\n")
        expect_rejected(
            checker,
            lambda: checker.initialize_work_dir(
                foreign,
                manifest_sha256="5" * 64,
                orchestrator_sha256="6" * 64,
            ),
            "foreign nonempty work directory",
        )

        target = base / "target"
        target.mkdir()
        link = base / "linked"
        link.symlink_to(target, target_is_directory=True)
        expect_rejected(
            checker,
            lambda: checker.initialize_work_dir(
                link,
                manifest_sha256="5" * 64,
                orchestrator_sha256="6" * 64,
            ),
            "symlink work directory",
        )

        for unsafe, label in (
            (Path(Path.cwd().anchor), "filesystem-root work directory"),
            (ROOT.parent, "repository-ancestor work directory"),
            (ROOT / "tmp" / "unsafe-work", "repository-descendant work directory"),
        ):
            expect_rejected(
                checker,
                lambda unsafe=unsafe: checker.initialize_work_dir(
                    unsafe,
                    manifest_sha256="5" * 64,
                    orchestrator_sha256="6" * 64,
                ),
                label,
            )

        redirected = base / "redirected"
        redirected.mkdir()
        stages_link = owner / "stages"
        stages_link.symlink_to(redirected, target_is_directory=True)
        marker_target = redirected / "should-not-appear"
        expect_rejected(
            checker,
            lambda: checker.run_stage(
                stage="symlinked-stages",
                commands=((sys.executable, "-c", "print('SHOULD NOT RUN')"),),
                cwd=ROOT,
                work_dir=owner,
                timeouts=(30,),
                markers=("SHOULD NOT RUN",),
                expected_outputs={},
                manifest_sha256="5" * 64,
                tools=tools,
                dependency_receipts=(),
                resume=False,
            ),
            "nested stages-directory symlink",
        )
        if marker_target.exists() or list(redirected.iterdir()):
            raise RuntimeError("nested stages symlink redirected a checker write")
        stages_link.unlink()

        stages_link.mkdir()
        external_log = base / "external.log"
        external_log.write_text("unchanged\n", encoding="utf-8")
        (stages_link / "linked-log.log").symlink_to(external_log)
        expect_rejected(
            checker,
            lambda: checker.run_stage(
                stage="linked-log",
                commands=((sys.executable, "-c", "print('SHOULD NOT RUN')"),),
                cwd=ROOT,
                work_dir=owner,
                timeouts=(30,),
                markers=("SHOULD NOT RUN",),
                expected_outputs={},
                manifest_sha256="5" * 64,
                tools=tools,
                dependency_receipts=(),
                resume=False,
            ),
            "stage-log symlink",
        )
        if external_log.read_text(encoding="utf-8") != "unchanged\n":
            raise RuntimeError("stage-log symlink modified its external target")
        (stages_link / "linked-log.log").unlink()

        external_temp = base / "external.tmp"
        external_temp.write_text("unchanged\n", encoding="utf-8")
        (owner / "probe.json.tmp").symlink_to(external_temp)
        expect_rejected(
            checker,
            lambda: checker.atomic_write(
                owner / "probe.json", b"unsafe\n", work_dir=owner
            ),
            "atomic temporary-output symlink",
        )
        if external_temp.read_text(encoding="utf-8") != "unchanged\n":
            raise RuntimeError("temporary-output symlink modified its external target")
        (owner / "probe.json.tmp").unlink()

        external_output = base / "external-output.bin"
        external_output.write_bytes(b"unchanged\n")
        linked_output = owner / "linked-output.bin"
        linked_output.symlink_to(external_output)
        expect_rejected(
            checker,
            lambda: checker.run_stage(
                stage="linked-output",
                commands=((sys.executable, "-c", "print('SHOULD NOT RUN')"),),
                cwd=ROOT,
                work_dir=owner,
                timeouts=(30,),
                markers=("SHOULD NOT RUN",),
                expected_outputs={linked_output: hashlib.sha256(b"unchanged\n").hexdigest()},
                manifest_sha256="5" * 64,
                tools=tools,
                dependency_receipts=(),
                resume=False,
            ),
            "generated-output symlink",
        )
        if external_output.read_bytes() != b"unchanged\n":
            raise RuntimeError("generated-output symlink modified its external target")
        linked_output.unlink()

        injected = owner / "caller-injected.txt"
        injected.write_text("not checker-owned\n", encoding="utf-8")
        expect_rejected(
            checker,
            lambda: checker.require_expected_work_layout(owner),
            "unexpected owned-work entry",
        )
        injected.unlink()

        if checker.is_link_or_reparse(owner):
            raise RuntimeError("ordinary owned directory misclassified as a link")
        print("REJECTED nested work-directory link controls")

    if checker.completion_receipt_status(resumed=True) != (
        "resumed-checkpoint-chain-validated"
    ):
        raise RuntimeError("resume could acquire theorem-grade receipt status")
    if checker.completion_receipt_status(resumed=False) != (
        "all-n-computational-certificate-passed"
    ):
        raise RuntimeError("fresh replay lost theorem-grade receipt status")
    print("RESUME receipts are operational only; fresh main run is theorem-grade")

    print("ALL ALL-N RESUME MUTATION CONTROLS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
