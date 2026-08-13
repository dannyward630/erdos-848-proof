#!/usr/bin/env python3
"""Strict, fail-closed handoff validation for the ART-006 workflow.

The completion runner creates the mathematical receipt.  This wrapper binds it
to one GitHub run and runner, rejects JSON coercions and schema extensions, and
checks every uploaded byte before the second job publishes the receipt tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PureWindowsPath
from typing import Any, NoReturn

import run_completion_gate as gate


HANDOFF_KEYS = (
    "schema", "status", "run_id", "run_attempt", "head_sha", "runner_name",
    "runner_os", "runner_arch", "receipt_relative",
)
SUCCESS_KEYS = (
    "schema", "run_id", "run_attempt", "head_sha", "runner_name",
    "receipt_sha256",
)
RECEIPT_KEYS = (
    "version", "status", "source_lock_sha256", "root_repository", "upstream",
    "lake_dependencies", "host", "toolchain", "effective_lean_path",
    "provider_olean_count", "provider_module_list_sha256",
    "publication_source_count", "root_final_olean_sha256", "allowed_axioms",
    "axiom_reports", "logs",
)
ROOT_KEYS = (
    "head", "tree", "clean", "final_sha256", "axiom_audit_sha256",
    "test_sha256", "runner_sha256",
)
UPSTREAM_KEYS = (
    "revision", "tree", "lean_tree", "modules", "bytes", "provider_modules",
    "provider_module_list_sha256", "publication_module_list_sha256",
)
HOST_KEYS = (
    "system", "machine", "platform", "python", "total_memory_bytes",
    "available_memory_bytes", "free_storage_bytes",
)
TOOLCHAIN_KEYS = (
    "lean", "observed_lean_version", "runtime_archive_sha256", "runtime_bin",
    "resolved_lean_executable", "lean_executable_sha256",
    "resolved_lake_executable", "lake_executable_sha256", "lean_commit",
    "mathlib_revision", "psutil",
)
DEPENDENCY_KEYS = ("revision", "tree", "url")
DEPENDENCIES = (
    ("mathlib", "https://github.com/leanprover-community/mathlib4", gate.MATHLIB),
    ("plausible", "https://github.com/leanprover-community/plausible", "293af9b2a383eed4d04d66b898d608d0a44b750f"),
    ("LeanSearchClient", "https://github.com/leanprover-community/LeanSearchClient", "c5d5b8fe6e5158def25cd28eb94e4141ad97c843"),
    ("importGraph", "https://github.com/leanprover-community/import-graph", "fd70b40073aeca8fa60fe0fb492f189d3b12c0ef"),
    ("proofwidgets", "https://github.com/leanprover-community/ProofWidgets4", "2db6054a44326f8c0230ee0570e2ddb894816511"),
    ("aesop", "https://github.com/leanprover-community/aesop", "f0c6e183ea26531e82773feb4b73ab6595ca17a5"),
    ("Qq", "https://github.com/leanprover-community/quote4", "1cc7e819b9b9bc1e87c9edcccb62e0269e00a809"),
    ("batteries", "https://github.com/leanprover-community/batteries", "5c57f3857ba81924a88b2cdf4f062e34ec04ff11"),
    ("Cli", "https://github.com/leanprover/lean4-cli", "13567aed1ac4f12aea9484178e07e51f8c9f7658"),
)
REQUIRED_GATE_LOGS = (
    "01-mathlib-cache.log", "02-clean-source-build.log",
    "03-upstream-kernel-gates.log", "04-root-final-build.log",
    "05-root-trust-zero-axioms.log", "06-root-final-dependencies.log",
    "07-root-audit-dependencies.log",
)
EXPECTED_LOGS = tuple(
    name
    for index, (package, _, _) in enumerate(DEPENDENCIES, start=1)
    for name in (
        f"00-{index:02d}-{package}-clone.log",
        f"00-{index:02d}-{package}-checkout.log",
    )
) + REQUIRED_GATE_LOGS
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")


class WorkflowFailure(RuntimeError):
    pass


def fail(message: str) -> NoReturn:
    raise WorkflowFailure(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_canonical_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"invalid JSON at {path}: {error}")
    if type(value) is not dict or raw != gate.canonical_json(value):
        fail(f"noncanonical JSON object: {path}")
    return value


def write_canonical_object(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        fail(f"refusing to overwrite workflow metadata: {path}")
    gate.atomic_write(path, gate.canonical_json(value))


def exact_keys(value: Any, keys: tuple[str, ...], label: str) -> dict[str, Any]:
    if type(value) is not dict or tuple(value) != keys:
        fail(f"{label} has the wrong type, keys, or key order")
    return value


def exact_string(value: Any, expected: str, label: str) -> None:
    if type(value) is not str or value != expected:
        fail(f"{label} mismatch")


def string_matching(value: Any, pattern: re.Pattern[str], label: str) -> None:
    if type(value) is not str or pattern.fullmatch(value) is None:
        fail(f"{label} has the wrong type or format")


def exact_int(value: Any, expected: int, label: str) -> None:
    if type(value) is not int or value != expected:
        fail(f"{label} mismatch")


def strict_object_equal(observed: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Compare JSON values without Python's Boolean/integer coercion."""

    return gate.canonical_json(observed) == gate.canonical_json(expected)


def minimum_int(value: Any, minimum: int, label: str) -> None:
    if type(value) is not int or value < minimum:
        fail(f"{label} is below its exact-type minimum")


def git_value(repository: Path, expression: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(repository), "rev-parse", expression), check=False,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        fail(f"git rev-parse failed: {result.stdout.strip()}")
    return result.stdout.strip()


def metadata_expectations(args: argparse.Namespace) -> dict[str, Any]:
    if type(args.run_attempt) is not int or args.run_attempt < 1:
        fail("run attempt must be a positive integer")
    string_matching(args.run_id, re.compile(r"[1-9][0-9]*"), "run id")
    string_matching(args.head_sha, HEX40, "head SHA")
    if not args.runner_name:
        fail("runner name must be nonempty")
    return {
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "head_sha": args.head_sha,
        "runner_name": args.runner_name,
    }


def validate_handoff(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    handoff = exact_keys(read_canonical_object(path), HANDOFF_KEYS, "handoff")
    wanted = {
        "schema": "erdos848-art006-workflow-handoff-v1",
        "status": "initialized-before-lean-completion-gate",
        **expected,
        "runner_os": "Windows",
        "runner_arch": "X64",
        "receipt_relative": "receipt",
    }
    if not strict_object_equal(handoff, wanted):
        fail("handoff values or strict JSON types do not match this run")
    return handoff


def validate_success(path: Path, expected: dict[str, Any], digest: str) -> None:
    success = exact_keys(read_canonical_object(path), SUCCESS_KEYS, "success")
    wanted = {
        "schema": "erdos848-art006-workflow-success-v1",
        **expected,
        "receipt_sha256": digest,
    }
    if not strict_object_equal(success, wanted):
        fail("success values or strict JSON types do not match this run")


def validate_root(receipt: dict[str, Any], repository: Path) -> None:
    root = exact_keys(receipt["root_repository"], ROOT_KEYS, "root snapshot")
    current = gate.root_snapshot(require_clean=True)
    if not strict_object_equal(root, current):
        fail("receipt root snapshot differs from the clean verifier checkout")
    string_matching(root["head"], HEX40, "root head")
    string_matching(root["tree"], HEX40, "root tree")
    if type(root["clean"]) is not bool or root["clean"] is not True:
        fail("root clean flag is not literal true")
    if root["head"] != git_value(repository, "HEAD"):
        fail("receipt head differs from verifier checkout")
    if root["tree"] != git_value(repository, "HEAD^{tree}"):
        fail("receipt tree differs from verifier checkout")


def validate_upstream(value: Any) -> None:
    upstream = exact_keys(value, UPSTREAM_KEYS, "upstream snapshot")
    wanted = {
        "revision": gate.REVISION,
        "tree": gate.TREE,
        "lean_tree": gate.LEAN_TREE,
        "modules": gate.SOURCE_COUNT,
        "bytes": gate.SOURCE_BYTES,
        "provider_modules": gate.PROVIDER_MODULES,
        "provider_module_list_sha256": gate.PROVIDER_MODULE_LIST_SHA256,
        "publication_module_list_sha256": gate.PUBLICATION_MODULE_LIST_SHA256,
    }
    if not strict_object_equal(upstream, wanted):
        fail("upstream snapshot values or strict JSON types mismatch")


def validate_dependencies(value: Any) -> None:
    if type(value) is not dict or tuple(value) != tuple(item[0] for item in DEPENDENCIES):
        fail("Lake dependency inventory or ordering mismatch")
    for name, url, revision in DEPENDENCIES:
        item = exact_keys(value[name], DEPENDENCY_KEYS, f"dependency {name}")
        exact_string(item["revision"], revision, f"dependency revision {name}")
        string_matching(item["tree"], HEX40, f"dependency tree {name}")
        exact_string(item["url"], url, f"dependency URL {name}")


def validate_host(value: Any) -> None:
    host = exact_keys(value, HOST_KEYS, "host snapshot")
    exact_string(host["system"], "Windows", "host system")
    if type(host["machine"]) is not str or host["machine"].lower() not in {"amd64", "x86_64"}:
        fail("host machine is not Windows x86-64")
    if type(host["platform"]) is not str or not host["platform"].startswith("Windows-"):
        fail("host platform is not a Windows platform string")
    exact_string(host["python"], "3.12.10", "host Python patch")
    minimum_int(host["total_memory_bytes"], 64 << 30, "physical memory")
    minimum_int(host["available_memory_bytes"], 33792 << 20, "available memory")
    minimum_int(host["free_storage_bytes"], 200 << 30, "free storage")


def validate_toolchain(value: Any) -> None:
    toolchain = exact_keys(value, TOOLCHAIN_KEYS, "toolchain snapshot")
    exact_string(toolchain["lean"], gate.TOOLCHAIN, "Lean toolchain")
    observed = toolchain["observed_lean_version"]
    if (
        type(observed) is not str
        or not observed.startswith("Lean (version 4.30.0-rc2, ")
        or f"commit {gate.LEAN_COMMIT}," not in observed
    ):
        fail("observed Lean version mismatch")
    exact_string(
        toolchain["runtime_archive_sha256"],
        gate.RUNTIME_ARCHIVE_SHA256,
        "Lean runtime archive digest",
    )
    runtime_bin_value = toolchain["runtime_bin"]
    if type(runtime_bin_value) is not str:
        fail("runtime bin is not a string")
    runtime_bin = PureWindowsPath(runtime_bin_value)
    if not runtime_bin.is_absolute() or runtime_bin.name.lower() != "bin":
        fail("runtime bin is not an absolute Windows bin directory")
    executable = toolchain["resolved_lean_executable"]
    if type(executable) is not str:
        fail("resolved Lean executable is not a string")
    pure = PureWindowsPath(executable)
    if (
        not pure.is_absolute()
        or pure.name.lower() != "lean.exe"
        or pure.parent != runtime_bin
    ):
        fail("resolved Lean executable is not an absolute Windows bin/lean.exe")
    exact_string(
        toolchain["lean_executable_sha256"],
        gate.LEAN_EXECUTABLE_SHA256,
        "Lean executable digest",
    )
    lake_executable = toolchain["resolved_lake_executable"]
    if type(lake_executable) is not str:
        fail("resolved Lake executable is not a string")
    lake = PureWindowsPath(lake_executable)
    if (
        not lake.is_absolute()
        or lake.name.lower() != "lake.exe"
        or lake.parent != runtime_bin
        or lake.parent != pure.parent
    ):
        fail("resolved Lake executable is not the paired Windows bin/lake.exe")
    exact_string(
        toolchain["lake_executable_sha256"],
        gate.LAKE_EXECUTABLE_SHA256,
        "Lake executable digest",
    )
    exact_string(toolchain["lean_commit"], gate.LEAN_COMMIT, "Lean commit")
    exact_string(toolchain["mathlib_revision"], gate.MATHLIB, "mathlib revision")
    exact_string(toolchain["psutil"], "7.2.2", "psutil version")


def validate_paths(value: Any) -> None:
    if type(value) is not list or len(value) < 3:
        fail("effective Lean path has the wrong type or is implausibly short")
    if any(type(item) is not str or not PureWindowsPath(item).is_absolute() for item in value):
        fail("effective Lean path contains a non-string or relative path")
    if len(set(value)) != len(value):
        fail("effective Lean path contains duplicates")


def validate_axioms(receipt: dict[str, Any]) -> None:
    allowed = receipt["allowed_axioms"]
    if type(allowed) is not list or allowed != list(gate.ALLOWED_AXIOMS):
        fail("allowed-axiom list or strict JSON type mismatch")
    reports = receipt["axiom_reports"]
    if type(reports) is not dict or tuple(reports) != gate.ENDPOINTS:
        fail("axiom report endpoint set or ordering mismatch")
    for endpoint, axioms in reports.items():
        if type(axioms) is not list or any(type(item) is not str for item in axioms):
            fail(f"axiom report has the wrong type: {endpoint}")
        if len(set(axioms)) != len(axioms) or any(item not in gate.ALLOWED_AXIOMS for item in axioms):
            fail(f"axiom report is duplicate-bearing or forbidden: {endpoint}")


def validate_logs(receipt: dict[str, Any], receipt_root: Path) -> None:
    logs = receipt["logs"]
    if type(logs) is not dict or tuple(logs) != EXPECTED_LOGS:
        fail("completion log inventory or ordering mismatch")
    for name, digest in logs.items():
        string_matching(digest, HEX64, f"log digest {name}")
        path = receipt_root / name
        if not path.is_file() or path.is_symlink() or sha256_file(path) != digest:
            fail(f"completion log byte mismatch: {name}")
    if "passed status=" not in (receipt_root / "02-clean-source-build.log").read_text(encoding="utf-8"):
        fail("source-build terminal marker is missing")
    kernel_marker = "[kernel-gate:ok] paper-machine version, trust=0, and axioms"
    if kernel_marker not in (receipt_root / "03-upstream-kernel-gates.log").read_text(encoding="utf-8"):
        fail("upstream kernel-gate terminal marker is missing")
    if list(receipt_root.rglob("*.partial.log")):
        fail("successful receipt tree contains a partial log")


def validate_receipt(receipt_root: Path, repository: Path) -> tuple[dict[str, Any], str]:
    path = receipt_root / "lean-completion-receipt.json"
    receipt = exact_keys(read_canonical_object(path), RECEIPT_KEYS, "completion receipt")
    exact_int(receipt["version"], 1, "receipt version")
    exact_string(receipt["status"], "lean-completion-gate-passed", "receipt status")
    exact_string(receipt["source_lock_sha256"], sha256_file(repository / "lean/source-lock.json"), "source-lock digest")
    validate_root(receipt, repository)
    validate_upstream(receipt["upstream"])
    validate_dependencies(receipt["lake_dependencies"])
    validate_host(receipt["host"])
    validate_toolchain(receipt["toolchain"])
    validate_paths(receipt["effective_lean_path"])
    exact_int(receipt["provider_olean_count"], gate.PROVIDER_MODULES, "provider OLean count")
    exact_string(receipt["provider_module_list_sha256"], gate.PROVIDER_MODULE_LIST_SHA256, "provider module-list digest")
    exact_int(receipt["publication_source_count"], gate.SOURCE_COUNT, "publication source count")
    root_olean = receipt_root / "root-oleans/Erdos848Completion/Final.olean"
    if not root_olean.is_file() or root_olean.is_symlink():
        fail("root final OLean is missing or unsafe")
    exact_string(receipt["root_final_olean_sha256"], sha256_file(root_olean), "root final OLean digest")
    validate_axioms(receipt)
    validate_logs(receipt, receipt_root)
    expected_files = set(EXPECTED_LOGS) | {
        "lean-completion-receipt.json",
        "root-oleans/Erdos848Completion/Final.olean",
    }
    observed_files = {
        path.relative_to(receipt_root).as_posix()
        for path in receipt_root.rglob("*") if path.is_file()
    }
    if observed_files != expected_files:
        fail("successful receipt tree contains missing or untracked files")
    return receipt, sha256_file(path)


def initialize(args: argparse.Namespace) -> None:
    expected = metadata_expectations(args)
    run_root = args.run_root.resolve(strict=True)
    value = {
        "schema": "erdos848-art006-workflow-handoff-v1",
        "status": "initialized-before-lean-completion-gate",
        **expected,
        "runner_os": "Windows",
        "runner_arch": "X64",
        "receipt_relative": "receipt",
    }
    write_canonical_object(run_root / "handoff.json", value)
    validate_handoff(run_root / "handoff.json", expected)


def seal(args: argparse.Namespace) -> None:
    expected = metadata_expectations(args)
    run_root = args.run_root.resolve(strict=True)
    validate_handoff(run_root / "handoff.json", expected)
    _, digest = validate_receipt(run_root / "receipt", args.repository.resolve(strict=True))
    value = {
        "schema": "erdos848-art006-workflow-success-v1",
        **expected,
        "receipt_sha256": digest,
    }
    write_canonical_object(run_root / "success.json", value)
    validate_success(run_root / "success.json", expected, digest)
    print(f"ART006 FULL SOURCE EXECUTION SEALED receipt_sha256={digest}")


def validate(args: argparse.Namespace) -> None:
    expected = metadata_expectations(args)
    run_root = args.run_root.resolve(strict=True)
    validate_handoff(run_root / "handoff.json", expected)
    receipt_path = run_root / "receipt/lean-completion-receipt.json"
    success_path = run_root / "success.json"
    if args.build_result == "success":
        _, digest = validate_receipt(run_root / "receipt", args.repository.resolve(strict=True))
        validate_success(success_path, expected, digest)
        print(f"LEAN COMPLETION HANDOFF VERIFIED receipt_sha256={digest}")
        return
    if success_path.exists() or receipt_path.exists():
        fail("failed build produced success metadata or a completion receipt")
    print(f"DIAGNOSTIC FAILURE HANDOFF VERIFIED result={args.build_result}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name, action in (("initialize", initialize), ("seal", seal), ("validate", validate)):
        command = commands.add_parser(name)
        command.set_defaults(action=action)
        command.add_argument("--run-root", type=Path, required=True)
        command.add_argument("--run-id", required=True)
        command.add_argument("--run-attempt", type=int, required=True)
        command.add_argument("--head-sha", required=True)
        command.add_argument("--runner-name", required=True)
        if name in {"seal", "validate"}:
            command.add_argument("--repository", type=Path, required=True)
        if name == "validate":
            command.add_argument(
                "--build-result", choices=("success", "failure", "cancelled", "skipped"),
                required=True,
            )
    return result


def main() -> int:
    args = parser().parse_args()
    args.action(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (WorkflowFailure, gate.GateFailure, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ART006 WORKFLOW RECEIPT REJECTED: {error}", file=sys.stderr)
        raise SystemExit(1) from error
