#!/usr/bin/env python3
"""Plan, seal, and verify diagnostic ART-006 source-build segments.

This is deliberately not a Lean completion gate.  It establishes a small,
genesis-anchored checkpoint protocol that can later be scaled and audited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


SCHEMA = "erdos848-lean-source-checkpoint-plan-v1"
RECEIPT_SCHEMA = "erdos848-lean-source-checkpoint-receipt-v1"
STATUS = "diagnostic-only-not-an-art006-completion-receipt"
RECEIPT_STATUS = "diagnostic-byte-integrity-only-not-execution-attestation"
REQUIRED_MEMORY_MIB = 24_576
REQUIRED_COMPILE_FLAGS = [
    "--trust=0", "-q", "-M", str(REQUIRED_MEMORY_MIB),
    "-D", "compiler.postponeCompile=true",
]
REQUIRED_RUNNER_OS = "Windows"
REQUIRED_RUNNER_ARCH = "X64"
REQUIRED_LEAN_COMMIT = "3dc1a088b6d2d8eafe25a7cd7ec7b58d731bd7cc"
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
MODULE = re.compile(r"Erdos848(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


class CheckpointFailure(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode("ascii")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_json(path: Path) -> Any:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckpointFailure(f"invalid JSON in {path}: {error}") from error
    if raw != canonical_json(value):
        raise CheckpointFailure(f"JSON is not canonical in {path}")
    return value


def exact_keys(value: Any, keys: Sequence[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or list(value) != list(keys):
        raise CheckpointFailure(f"{label} has wrong type, keys, or key order")
    return value


def exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CheckpointFailure(f"{label} must be an integer >= {minimum}")
    return value


def exact_string(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise CheckpointFailure(f"{label} must be a nonempty string")
    return value


def exact_sha(value: Any, label: str) -> str:
    text = exact_string(value, label)
    if HEX64.fullmatch(text) is None:
        raise CheckpointFailure(f"{label} must be a lowercase SHA-256")
    return text


def exact_git_oid(value: Any, label: str) -> str:
    text = exact_string(value, label)
    if HEX40.fullmatch(text) is None:
        raise CheckpointFailure(f"{label} must be a lowercase 40-character Git id")
    return text


def exact_module(value: Any, label: str) -> str:
    text = exact_string(value, label)
    if MODULE.fullmatch(text) is None:
        raise CheckpointFailure(f"{label} is not a safe Erdos848 module name")
    return text


def run(command: Sequence[str], cwd: Path) -> str:
    result = subprocess.run(
        list(command), cwd=cwd, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if result.returncode:
        raise CheckpointFailure(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}"
        )
    return result.stdout.strip()


def module_path(source_root: Path, module: str) -> Path:
    exact_module(module, "module")
    return source_root / "lean4" / Path(*module.split(".")).with_suffix(".lean")


def module_name(source_root: Path, source: Path) -> str:
    return ".".join(source.relative_to(source_root / "lean4").with_suffix("").parts)


def project_imports(source: Path) -> tuple[str, ...]:
    imports: list[str] = []
    depth = 0
    with source.open("r", encoding="utf-8-sig") as stream:
        for raw in stream:
            line = raw.strip()
            depth += line.count("/-")
            if depth:
                depth -= line.count("-/")
                continue
            if not line or line.startswith("--") or line == "prelude":
                continue
            match = re.fullmatch(r"import\s+(.+?)\s*", line)
            if match is None:
                break
            imports.extend(
                item for item in match.group(1).split()
                if item == "Erdos848" or item.startswith("Erdos848.")
            )
    return tuple(imports)


def read_lock(path: Path) -> dict[str, Any]:
    lock = exact_json(path)
    exact_keys(
        lock,
        ["version", "status", "upstream", "toolchain", "sources", "endpoint",
         "root_sources", "allowed_axioms", "minimum_host"],
        "source lock",
    )
    if lock["version"] != 1:
        raise CheckpointFailure("unsupported source-lock version")
    exact_string(lock["status"], "source-lock status")
    exact_keys(lock["upstream"], ["url", "revision", "tree", "lean_tree"],
               "source-lock upstream")
    exact_string(lock["upstream"]["url"], "source-lock upstream URL")
    for key in ("revision", "tree", "lean_tree"):
        exact_git_oid(lock["upstream"][key], f"source-lock upstream {key}")
    exact_keys(lock["toolchain"], ["lean", "lean_commit", "lean_toolchain_sha256",
                                   "lake_manifest_sha256", "lakefile_sha256",
                                   "mathlib_revision"], "source-lock toolchain")
    exact_string(lock["toolchain"]["lean"], "source-lock Lean toolchain")
    exact_git_oid(lock["toolchain"]["lean_commit"], "source-lock Lean commit")
    exact_git_oid(lock["toolchain"]["mathlib_revision"], "source-lock Mathlib revision")
    for key in ("lean_toolchain_sha256", "lake_manifest_sha256", "lakefile_sha256"):
        exact_sha(lock["toolchain"][key], f"source-lock {key}")
    return lock


def source_identity(source_root: Path, lock: dict[str, Any]) -> dict[str, Any]:
    root = source_root.resolve(strict=True)
    if (root / ".git").is_symlink():
        raise CheckpointFailure("source .git path must not be a symlink")
    upstream = lock["upstream"]
    toolchain = lock["toolchain"]
    expected = {
        "url": upstream["url"],
        "revision": upstream["revision"],
        "tree": upstream["tree"],
        "lean_tree": upstream["lean_tree"],
        "toolchain": toolchain["lean"],
        "lean_commit": toolchain["lean_commit"],
        "lean_toolchain_sha256": toolchain["lean_toolchain_sha256"],
        "lake_manifest_sha256": toolchain["lake_manifest_sha256"],
        "lakefile_sha256": toolchain["lakefile_sha256"],
        "mathlib_revision": toolchain["mathlib_revision"],
    }
    observed = {
        "revision": run(("git", "rev-parse", "HEAD"), root),
        "tree": run(("git", "rev-parse", "HEAD^{tree}"), root),
        "lean_tree": run(("git", "rev-parse", "HEAD:lean4"), root),
        "lean_toolchain_sha256": sha256_file(root / "lean4" / "lean-toolchain"),
        "lake_manifest_sha256": sha256_file(root / "lean4" / "lake-manifest.json"),
        "lakefile_sha256": sha256_file(root / "lean4" / "lakefile.toml"),
    }
    for key, value in observed.items():
        if value != expected[key]:
            raise CheckpointFailure(f"source identity mismatch for {key}: {value}")
    dirty = run(("git", "status", "--porcelain"), root)
    if dirty:
        raise CheckpointFailure("source checkout is dirty")
    return expected


def dependency_closure(source_root: Path, target: str) -> dict[str, tuple[str, ...]]:
    graph: dict[str, tuple[str, ...]] = {}
    visiting: set[str] = set()

    def visit(module: str) -> None:
        if module in graph:
            return
        if module in visiting:
            raise CheckpointFailure(f"cyclic project import at {module}")
        source = module_path(source_root, module)
        if not source.is_file() or source.is_symlink():
            raise CheckpointFailure(f"missing or unsafe source for {module}")
        visiting.add(module)
        imports = project_imports(source)
        for imported in imports:
            visit(imported)
        visiting.remove(module)
        graph[module] = imports

    visit(target)
    return graph


def topological_order(graph: dict[str, tuple[str, ...]]) -> list[str]:
    remaining = set(graph)
    done: set[str] = set()
    ordered: list[str] = []
    while remaining:
        ready = sorted(module for module in remaining if set(graph[module]) <= done)
        if not ready:
            raise CheckpointFailure("project import graph is cyclic")
        for module in ready:
            ordered.append(module)
            done.add(module)
            remaining.remove(module)
    return ordered


def generate_plan(
    source_root: Path, lock_path: Path, target: str, modules_per_segment: int,
) -> dict[str, Any]:
    if modules_per_segment < 1:
        raise CheckpointFailure("modules per segment must be positive")
    exact_module(target, "target module")
    lock = read_lock(lock_path)
    identity = source_identity(source_root, lock)
    graph = dependency_closure(source_root, target)
    ordered = topological_order(graph)
    assignment: dict[str, int] = {}
    chunks = [ordered[i:i + modules_per_segment]
              for i in range(0, len(ordered), modules_per_segment)]
    segments: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        for module in chunk:
            assignment[module] = index
        parents = sorted({assignment[dependency]
                          for module in chunk for dependency in graph[module]
                          if assignment[dependency] != index})
        records = []
        for module in chunk:
            source = module_path(source_root, module)
            records.append({
                "name": module,
                "source_path": source.relative_to(source_root).as_posix(),
                "source_sha256": sha256_file(source),
                "project_imports": list(graph[module]),
            })
        segments.append({
            "index": index,
            "id": f"segment-{index:04d}",
            "parents": parents,
            "modules": records,
        })
    module_digest = sha256_bytes(("\n".join(sorted(graph)) + "\n").encode("ascii"))
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source": identity,
        "target_module": target,
        "modules_per_segment": modules_per_segment,
        "module_list_sha256": module_digest,
        "segments": segments,
    }


def validate_plan_shape(plan: Any) -> dict[str, Any]:
    exact_keys(plan, ["schema", "status", "source", "target_module",
                      "modules_per_segment",
                      "module_list_sha256", "segments"], "plan")
    if plan["schema"] != SCHEMA or plan["status"] != STATUS:
        raise CheckpointFailure("wrong plan schema or status")
    exact_keys(
        plan["source"],
        ["url", "revision", "tree", "lean_tree", "toolchain", "lean_commit",
         "lean_toolchain_sha256", "lake_manifest_sha256", "lakefile_sha256",
         "mathlib_revision"],
        "plan source",
    )
    for key in ("revision", "tree", "lean_tree", "lean_commit",
                "lean_toolchain_sha256", "lake_manifest_sha256", "lakefile_sha256",
                "mathlib_revision"):
        value = plan["source"][key]
        if key.endswith("sha256"):
            exact_sha(value, f"plan source {key}")
        else:
            exact_git_oid(value, f"plan source {key}")
    exact_string(plan["source"]["url"], "plan source url")
    exact_string(plan["source"]["toolchain"], "plan source toolchain")
    exact_module(plan["target_module"], "target module")
    exact_int(plan["modules_per_segment"], "modules per segment", minimum=1)
    exact_sha(plan["module_list_sha256"], "module list digest")
    if type(plan["segments"]) is not list or not plan["segments"]:
        raise CheckpointFailure("plan must contain at least one segment")
    names: set[str] = set()
    assignment: dict[str, int] = {}
    all_imports: dict[str, list[str]] = {}
    for expected_index, segment in enumerate(plan["segments"]):
        exact_keys(segment, ["index", "id", "parents", "modules"], "segment")
        index = exact_int(segment["index"], "segment index")
        if index != expected_index or segment["id"] != f"segment-{index:04d}":
            raise CheckpointFailure("segment numbering or id is not canonical")
        if type(segment["parents"]) is not list:
            raise CheckpointFailure("segment parents must be a list")
        parents = [exact_int(item, "parent index") for item in segment["parents"]]
        if parents != sorted(set(parents)) or any(item >= index for item in parents):
            raise CheckpointFailure("segment parents are not canonical predecessors")
        if type(segment["modules"]) is not list or not segment["modules"]:
            raise CheckpointFailure("segment modules must be a nonempty list")
        for record in segment["modules"]:
            exact_keys(record, ["name", "source_path", "source_sha256",
                                "project_imports"], "module record")
            name = exact_module(record["name"], "module name")
            if name in names:
                raise CheckpointFailure(f"duplicate module {name}")
            names.add(name)
            assignment[name] = index
            exact_string(record["source_path"], "module source path")
            exact_sha(record["source_sha256"], "module source digest")
            if type(record["project_imports"]) is not list:
                raise CheckpointFailure("project imports must be a list")
            imports = [exact_module(item, "project import")
                       for item in record["project_imports"]]
            if imports != list(dict.fromkeys(imports)):
                raise CheckpointFailure("project imports contain duplicates")
            all_imports[name] = imports
    if plan["target_module"] not in names:
        raise CheckpointFailure("target module is absent from plan")
    if sha256_bytes(("\n".join(sorted(names)) + "\n").encode("ascii")) != plan["module_list_sha256"]:
        raise CheckpointFailure("module-list digest mismatch")
    for index, segment in enumerate(plan["segments"]):
        required: set[int] = set()
        for record in segment["modules"]:
            for dependency in all_imports[record["name"]]:
                if dependency not in assignment:
                    raise CheckpointFailure(f"unplanned project import {dependency}")
                dep_index = assignment[dependency]
                if dep_index > index:
                    raise CheckpointFailure("dependency appears after importer")
                if dep_index < index:
                    required.add(dep_index)
        if segment["parents"] != sorted(required):
            raise CheckpointFailure("segment parent list is not the exact dependency set")
    return plan


def verify_plan(plan_path: Path, source_root: Path, lock_path: Path) -> dict[str, Any]:
    plan = validate_plan_shape(exact_json(plan_path))
    # Exact widths are part of the immutable plan; all but the final segment
    # must therefore have the declared width.
    widths = [len(item["modules"]) for item in plan["segments"]]
    width = plan["modules_per_segment"]
    if any(item != width for item in widths[:-1]) or widths[-1] > width:
        raise CheckpointFailure("segment widths are not canonical")
    regenerated = generate_plan(source_root, lock_path, plan["target_module"], width)
    if plan != regenerated:
        raise CheckpointFailure("plan does not exactly match authenticated sources")
    return plan


def segment_modules(plan: dict[str, Any], index: int) -> list[dict[str, Any]]:
    if index >= len(plan["segments"]):
        raise CheckpointFailure("segment index is outside the plan")
    return plan["segments"][index]["modules"]


def validate_receipt_shape(receipt: Any) -> dict[str, Any]:
    exact_keys(receipt, ["schema", "status", "plan_sha256", "segment_index",
                         "segment_id", "source", "parents", "modules", "command",
                         "environment", "genesis"], "receipt")
    if receipt["schema"] != RECEIPT_SCHEMA or receipt["status"] != RECEIPT_STATUS:
        raise CheckpointFailure("wrong receipt schema or status")
    exact_sha(receipt["plan_sha256"], "receipt plan digest")
    exact_int(receipt["segment_index"], "receipt segment index")
    exact_string(receipt["segment_id"], "receipt segment id")
    exact_keys(receipt["source"], ["revision", "tree", "lean_tree"], "receipt source")
    for key in receipt["source"]:
        exact_string(receipt["source"][key], f"receipt source {key}")
    if type(receipt["parents"]) is not list or type(receipt["modules"]) is not list:
        raise CheckpointFailure("receipt parents and modules must be lists")
    for parent in receipt["parents"]:
        exact_keys(parent, ["segment_index", "segment_id", "receipt_sha256"], "parent receipt")
        exact_int(parent["segment_index"], "parent receipt index")
        exact_string(parent["segment_id"], "parent receipt id")
        exact_sha(parent["receipt_sha256"], "parent receipt digest")
    for module in receipt["modules"]:
        exact_keys(module, ["name", "source_sha256", "olean_path", "olean_sha256",
                            "olean_bytes"], "receipt module")
        exact_string(module["name"], "receipt module name")
        exact_sha(module["source_sha256"], "receipt source digest")
        exact_string(module["olean_path"], "receipt OLean path")
        exact_sha(module["olean_sha256"], "receipt OLean digest")
        exact_int(module["olean_bytes"], "receipt OLean bytes", minimum=1)
    exact_keys(receipt["command"], ["compile_flags", "memory_mib"], "receipt command")
    if receipt["command"]["compile_flags"] != REQUIRED_COMPILE_FLAGS:
        raise CheckpointFailure("receipt does not record the exact audited compile flags")
    if exact_int(receipt["command"]["memory_mib"], "memory MiB", minimum=1) \
            != REQUIRED_MEMORY_MIB:
        raise CheckpointFailure("receipt does not record the exact audited memory cap")
    exact_keys(receipt["environment"], ["runner_os", "runner_arch", "lean_version"],
               "receipt environment")
    if receipt["environment"]["runner_os"] != REQUIRED_RUNNER_OS:
        raise CheckpointFailure("receipt runner OS is not the audited Windows host")
    if receipt["environment"]["runner_arch"] != REQUIRED_RUNNER_ARCH:
        raise CheckpointFailure("receipt runner architecture is not X64")
    lean_version = exact_string(
        receipt["environment"]["lean_version"], "environment Lean version"
    )
    if (not lean_version.startswith("Lean (version 4.30.0-rc2,")
            or f"commit {REQUIRED_LEAN_COMMIT}," not in lean_version):
        raise CheckpointFailure("receipt Lean version is not the audited runtime")
    exact_keys(receipt["genesis"], ["project_oleans_before_parent_import",
                                    "parent_segments_imported",
                                    "parent_oleans_imported"], "genesis record")
    if exact_int(receipt["genesis"]["project_oleans_before_parent_import"],
                 "pre-parent OLean count") != 0:
        raise CheckpointFailure("segment did not start from zero project OLeans")
    if type(receipt["genesis"]["parent_segments_imported"]) is not list:
        raise CheckpointFailure("imported parent segments must be a list")
    for item in receipt["genesis"]["parent_segments_imported"]:
        exact_int(item, "imported parent index")
    exact_int(receipt["genesis"]["parent_oleans_imported"], "imported parent OLeans")
    return receipt


def receipt_file(root: Path) -> Path:
    return root / "receipt.json"


def verify_receipt(
    plan_path: Path, asset_root: Path, parent_roots: Sequence[Path],
    expected_segment: int | None = None,
) -> dict[str, Any]:
    if not asset_root.is_dir() or asset_root.is_symlink():
        raise CheckpointFailure("checkpoint asset root must be a real directory")
    if any(path.is_symlink() for path in asset_root.rglob("*")):
        raise CheckpointFailure("checkpoint asset tree must not contain symlinks")
    plan = validate_plan_shape(exact_json(plan_path))
    plan_digest = sha256_file(plan_path)
    receipt = validate_receipt_shape(exact_json(receipt_file(asset_root)))
    index = receipt["segment_index"]
    if expected_segment is not None and index != expected_segment:
        raise CheckpointFailure("receipt is for the wrong segment")
    segment = plan["segments"][index]
    if (receipt["plan_sha256"] != plan_digest or receipt["segment_id"] != segment["id"]
            or receipt["source"] != {key: plan["source"][key]
                                      for key in ("revision", "tree", "lean_tree")}):
        raise CheckpointFailure("receipt plan, segment, or source binding mismatch")
    expected_parent_indices = segment["parents"]
    if len(parent_roots) != len(expected_parent_indices):
        raise CheckpointFailure("wrong number of parent artifact roots")
    observed_parents = []
    parent_module_count = 0
    for parent_index, parent_root in zip(expected_parent_indices, parent_roots):
        if plan["segments"][parent_index]["parents"]:
            raise CheckpointFailure(
                "this bounded pilot requires every supplied parent to be genesis-anchored"
            )
        parent = verify_receipt(plan_path, parent_root, (), parent_index)
        parent_module_count += len(parent["modules"])
        observed_parents.append({
            "segment_index": parent_index,
            "segment_id": parent["segment_id"],
            "receipt_sha256": sha256_file(receipt_file(parent_root)),
        })
    if receipt["parents"] != observed_parents:
        raise CheckpointFailure("parent receipt chain mismatch")
    expected_modules = segment["modules"]
    if [item["name"] for item in receipt["modules"]] != [item["name"] for item in expected_modules]:
        raise CheckpointFailure("receipt module list mismatch")
    allowed = {"receipt.json"}
    for expected, observed in zip(expected_modules, receipt["modules"]):
        relpath = f"oleans/{expected['name'].replace('.', '/')}.olean"
        if (observed["source_sha256"] != expected["source_sha256"]
                or observed["olean_path"] != relpath):
            raise CheckpointFailure("receipt module source or path mismatch")
        path = asset_root / relpath
        if (not path.is_file() or path.is_symlink()
                or path.stat().st_size != observed["olean_bytes"]
                or sha256_file(path) != observed["olean_sha256"]):
            raise CheckpointFailure("receipt module OLean mismatch")
        allowed.add(relpath)
    actual = {path.relative_to(asset_root).as_posix()
              for path in asset_root.rglob("*") if path.is_file()}
    if actual != allowed:
        raise CheckpointFailure(f"unexpected checkpoint files: {sorted(actual ^ allowed)}")
    if receipt["genesis"]["parent_segments_imported"] != expected_parent_indices:
        raise CheckpointFailure("genesis parent segment record mismatch")
    if receipt["genesis"]["parent_oleans_imported"] != parent_module_count:
        raise CheckpointFailure("genesis parent OLean count mismatch")
    return receipt


def seal_receipt(args: argparse.Namespace) -> dict[str, Any]:
    plan = verify_plan(args.plan, args.source_root, args.lock)
    index = args.segment_index
    segment = plan["segments"][index]
    parents = []
    parent_count = 0
    if len(args.parent_root) != len(segment["parents"]):
        raise CheckpointFailure("wrong number of parent roots while sealing")
    for parent_index, root in zip(segment["parents"], args.parent_root):
        parent = verify_receipt(args.plan, root, (), parent_index)
        parent_count += len(parent["modules"])
        parents.append({
            "segment_index": parent_index,
            "segment_id": parent["segment_id"],
            "receipt_sha256": sha256_file(receipt_file(root)),
        })
    modules = []
    for record in segment["modules"]:
        relpath = f"oleans/{record['name'].replace('.', '/')}.olean"
        path = args.asset_root / relpath
        if not path.is_file() or path.is_symlink():
            raise CheckpointFailure(f"missing or unsafe built OLean: {relpath}")
        modules.append({
            "name": record["name"],
            "source_sha256": record["source_sha256"],
            "olean_path": relpath,
            "olean_sha256": sha256_file(path),
            "olean_bytes": path.stat().st_size,
        })
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": RECEIPT_STATUS,
        "plan_sha256": sha256_file(args.plan),
        "segment_index": index,
        "segment_id": segment["id"],
        "source": {key: plan["source"][key] for key in ("revision", "tree", "lean_tree")},
        "parents": parents,
        "modules": modules,
        "command": {
            "compile_flags": REQUIRED_COMPILE_FLAGS,
            "memory_mib": args.memory_mib,
        },
        "environment": {
            "runner_os": args.runner_os,
            "runner_arch": args.runner_arch,
            "lean_version": args.lean_version,
        },
        "genesis": {
            "project_oleans_before_parent_import": 0,
            "parent_segments_imported": segment["parents"],
            "parent_oleans_imported": parent_count,
        },
    }
    validate_receipt_shape(receipt)
    args.output.write_bytes(canonical_json(receipt))
    verify_receipt(args.plan, args.asset_root, args.parent_root, index)
    return receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--source-root", type=Path, required=True)
    generate.add_argument("--lock", type=Path, required=True)
    generate.add_argument("--target", required=True)
    generate.add_argument("--modules-per-segment", type=int, default=1)
    generate.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify-plan")
    verify.add_argument("--plan", type=Path, required=True)
    verify.add_argument("--source-root", type=Path, required=True)
    verify.add_argument("--lock", type=Path, required=True)
    seal = commands.add_parser("seal-receipt")
    seal.add_argument("--plan", type=Path, required=True)
    seal.add_argument("--source-root", type=Path, required=True)
    seal.add_argument("--lock", type=Path, required=True)
    seal.add_argument("--segment-index", type=int, required=True)
    seal.add_argument("--asset-root", type=Path, required=True)
    seal.add_argument("--parent-root", type=Path, action="append", default=[])
    seal.add_argument("--memory-mib", type=int, required=True)
    seal.add_argument("--runner-os", required=True)
    seal.add_argument("--runner-arch", required=True)
    seal.add_argument("--lean-version", required=True)
    seal.add_argument("--output", type=Path, required=True)
    receipt = commands.add_parser("verify-receipt")
    receipt.add_argument("--plan", type=Path, required=True)
    receipt.add_argument("--asset-root", type=Path, required=True)
    receipt.add_argument("--parent-root", type=Path, action="append", default=[])
    receipt.add_argument("--segment-index", type=int)
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "generate":
        plan = generate_plan(args.source_root, args.lock, args.target,
                             args.modules_per_segment)
        args.output.write_bytes(canonical_json(plan))
        verify_plan(args.output, args.source_root, args.lock)
        print(f"PLAN GENERATED sha256={sha256_file(args.output)} segments={len(plan['segments'])}")
    elif args.command == "verify-plan":
        plan = verify_plan(args.plan, args.source_root, args.lock)
        print(f"PLAN VERIFIED sha256={sha256_file(args.plan)} segments={len(plan['segments'])}")
    elif args.command == "seal-receipt":
        receipt = seal_receipt(args)
        print(f"RECEIPT SEALED segment={receipt['segment_index']} sha256={sha256_file(args.output)}")
    else:
        receipt = verify_receipt(args.plan, args.asset_root, args.parent_root,
                                 args.segment_index)
        print(f"RECEIPT VERIFIED segment={receipt['segment_index']} sha256={sha256_file(receipt_file(args.asset_root))}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CheckpointFailure, OSError, ValueError, IndexError, KeyError, TypeError) as error:
        print(f"checkpoint:error: {error}", file=sys.stderr)
        raise SystemExit(1)
