#!/usr/bin/env python3
"""Run the cache-backed ART-006 Lean canary on a standard Windows runner.

This is deliberately not the clean completion gate.  It authenticates the
published OLean cache at its own public commit, proves that commit and the
pinned ART-006 target have the same ``lean4`` tree, installs one authenticated
shard at a time under NTFS compression, and performs live trust-zero provider,
root-theorem, axiom, and dependency checks.  A pass never certifies a clean
source build and never emits ``LEAN COMPLETION GATE PASSED``.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
from typing import Any, Iterable, Sequence
import urllib.parse
import warnings
import zipfile


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
LEAN_AUDIT_ROOT = REPO_ROOT / "lean"
sys.path.insert(0, str(LEAN_AUDIT_ROOT))
import run_completion_gate as gate  # noqa: E402


CACHE_RELEASE_TAG = "v1.0.5-kernel"
CACHE_RELEASE_BASE = (
    "https://github.com/crabsatellite/erdos-848-squarefree-product/"
    f"releases/download/{CACHE_RELEASE_TAG}"
)
CACHE_MANIFEST_NAME = "ERDOS848_OLEAN_CACHE_MANIFEST.json"
CACHE_MANIFEST_SHA256 = (
    "3cbde25db4c5eac8209dd428cc5d95eab648766023db87418c8ea8c66353c527"
)
CACHE_PUBLIC_COMMIT = "bb8e1b10b0066639ee3440ba983c3f9774667d42"
CACHE_PUBLIC_TREE = "e8584652ddb279a766e284f21bb33448181d0e0e"
CACHE_PUBLICATION_MANIFEST_SHA256 = (
    "e4689ced3e48208e7f6a1175541d6c29f357c1d2e5b75e85c91101c52840b56a"
)
CACHE_INTERNAL_SOURCE_COMMIT = "39e745357846c9024af598efd07fd79711a46b52"
CACHE_PROVIDER_BUILD_SIGNATURE = (
    "c1364c0f0ce047c87564846aea09c1deb27de2b2044a8a0e8de98536cdcc4ea9"
)
TARGET_COMMIT = "ede0151a35c86b6395cf67dd034811d22a92c7ba"
TARGET_TREE = "5b1253061e916513036d30d8275c9aeaddb0e771"
LEAN_TREE = "6b9794fafddd3e7780c6a10a442f2e4e9dc73c1a"
UPSTREAM_URL = "https://github.com/crabsatellite/erdos-848-squarefree-product.git"
LEAN_TOOLCHAIN = "leanprover/lean4:v4.30.0-rc2"
LEAN_COMMIT = "3dc1a088b6d2d8eafe25a7cd7ec7b58d731bd7cc"
RUNTIME_ARCHIVE_NAME = "lean-4.30.0-rc2-windows.zip"
RUNTIME_ARCHIVE_SHA256 = (
    "cb0688631203ac7832e447a5791e51e88db938b6038ff788eea73491619988b2"
)
EXPECTED_ARCHIVES = 75
EXPECTED_MODULES = 30_638
EXPECTED_ARCHIVE_BYTES = 32_249_316_999
EXPECTED_LOGICAL_BYTES = 129_476_102_424
EXPECTED_PROVIDER_MODULES = 30_636
MEMORY_MIB = 24_576
COMMIT_GUARD_MIB = 2_048
TRIM_WORKING_SET_MIB = 12_000
MIN_POST_CACHE_FREE_BYTES = 40 * (1 << 30)
MAX_COMPRESSED_CACHE_BYTES = 60 * (1 << 30)
MAX_ASSET_BYTES = 2 * (1 << 30)
FILE_ATTRIBUTE_COMPRESSED = 0x800
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


class CanaryFailure(RuntimeError):
    """A fail-closed canary check failed."""


class MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_phys", ctypes.c_ulonglong),
        ("avail_phys", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("avail_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("avail_virtual", ctypes.c_ulonglong),
        ("avail_extended_virtual", ctypes.c_ulonglong),
    ]


class ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("page_fault_count", ctypes.c_ulong),
        ("peak_working_set_size", ctypes.c_size_t),
        ("working_set_size", ctypes.c_size_t),
        ("quota_peak_paged_pool_usage", ctypes.c_size_t),
        ("quota_paged_pool_usage", ctypes.c_size_t),
        ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
        ("quota_non_paged_pool_usage", ctypes.c_size_t),
        ("pagefile_usage", ctypes.c_size_t),
        ("peak_pagefile_usage", ctypes.c_size_t),
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode("ascii")


def strict_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CanaryFailure(f"{label} must be an integer at least {minimum}")
    return value


def strict_hex(value: Any, length: int, label: str) -> str:
    if type(value) is not str or re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is None:
        raise CanaryFailure(f"{label} is not a lowercase {length}-digit hex string")
    return value


def safe_posix_path(value: Any, label: str) -> PurePosixPath:
    if type(value) is not str or not value or "\\" in value or ":" in value:
        raise CanaryFailure(f"unsafe {label}: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or any(part in {"", ".", "..", ".git"} for part in path.parts)
        or value != path.as_posix()
    ):
        raise CanaryFailure(f"unsafe {label}: {value!r}")
    return path


def source_to_olean(source_path: str) -> str:
    source = safe_posix_path(source_path, "source path")
    if source.parts[0] != "lean4" or source.suffix != ".lean":
        raise CanaryFailure(f"not a publication Lean source: {source_path}")
    relative = PurePosixPath(*source.parts[1:]).with_suffix(".olean")
    return (PurePosixPath("lean4/.lake/build/lib/lean") / relative).as_posix()


def safe_destination(root: Path, relative: str) -> Path:
    pure = safe_posix_path(relative, "archive path")
    candidate = root.joinpath(*pure.parts).resolve(strict=False)
    resolved_root = root.resolve(strict=True)
    try:
        candidate.relative_to(resolved_root)
    except ValueError as error:
        raise CanaryFailure(f"archive path escaped staging root: {relative}") from error
    return candidate


def require_no_reparse_ancestors(path: Path, stop: Path) -> None:
    stop = stop.resolve(strict=True)
    current = path.resolve(strict=False)
    while current != stop:
        if current.exists():
            attributes = getattr(current.stat(follow_symlinks=False), "st_file_attributes", 0)
            if current.is_symlink() or attributes & FILE_ATTRIBUTE_REPARSE_POINT:
                raise CanaryFailure(f"reparse point in controlled path: {current}")
        parent = current.parent
        if parent == current:
            raise CanaryFailure(f"controlled path escaped root: {path}")
        current = parent


def prepare_empty_external_dir(path: Path, upstream: Path, label: str) -> Path:
    requested = path if path.is_absolute() else Path.cwd() / path
    if requested.exists() and requested.is_symlink():
        raise CanaryFailure(f"{label} itself must not be a symlink")
    resolved = requested.resolve(strict=False)
    repo = REPO_ROOT.resolve(strict=True)
    upstream = upstream.resolve(strict=True)
    if (
        resolved == Path(resolved.anchor)
        or resolved in {repo, upstream}
        or repo in resolved.parents
        or upstream in resolved.parents
        or resolved in repo.parents
        or resolved in upstream.parents
    ):
        raise CanaryFailure(f"{label} must be external to both repositories")
    if resolved.exists() and (not resolved.is_dir() or any(resolved.iterdir())):
        raise CanaryFailure(f"{label} must be absent or empty: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    attributes = getattr(
        resolved.stat(follow_symlinks=False), "st_file_attributes", 0
    )
    if resolved.is_symlink() or attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        raise CanaryFailure(f"{label} must not be a reparse point: {resolved}")
    return resolved


def run_capture(command: Sequence[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        list(command), cwd=cwd, env=env, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="strict",
    )
    if completed.returncode != 0:
        raise CanaryFailure(
            f"command failed ({completed.returncode}): {shlex.join(command)}\n"
            f"{completed.stdout}"
        )
    return completed.stdout.strip()


def git_identity(repository: Path) -> dict[str, str]:
    revision = run_capture(("git", "rev-parse", "HEAD"), repository)
    tree = run_capture(("git", "rev-parse", "HEAD^{tree}"), repository)
    lean_tree = run_capture(("git", "rev-parse", "HEAD:lean4"), repository)
    status = run_capture(
        ("git", "status", "--porcelain", "--untracked-files=all"), repository
    )
    remote = run_capture(("git", "remote", "get-url", "origin"), repository)
    if status:
        raise CanaryFailure(f"repository is dirty: {repository}")
    if gate.normalized_git_url(remote) != gate.normalized_git_url(UPSTREAM_URL):
        raise CanaryFailure(f"unexpected upstream remote: {remote}")
    return {
        "revision": revision,
        "tree": tree,
        "lean_tree": lean_tree,
        "remote": remote,
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CanaryFailure(f"invalid {label}: {error}") from error
    if type(value) is not dict:
        raise CanaryFailure(f"{label} must be a JSON object")
    return value


def publication_sources(publication: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if publication.get("schema_version") != 1:
        raise CanaryFailure("unsupported publication manifest schema")
    if publication.get("package_role") != "clean-public-kernel-source":
        raise CanaryFailure("unexpected publication package role")
    if publication.get("internal_source_commit") != CACHE_INTERNAL_SOURCE_COMMIT:
        raise CanaryFailure("cache-origin internal source commit mismatch")
    if publication.get("main_theorem") != gate.ENDPOINTS[14]:
        raise CanaryFailure("cache-origin main theorem mismatch")
    if publication.get("allowed_axioms") != list(gate.ALLOWED_AXIOMS):
        raise CanaryFailure("cache-origin allowed-axiom list mismatch")
    records = publication.get("files")
    if type(records) is not list:
        raise CanaryFailure("publication files must be a list")
    sources: dict[str, dict[str, Any]] = {}
    for item in records:
        if type(item) is not dict:
            raise CanaryFailure("malformed publication file record")
        path = item.get("path")
        if not (type(path) is str and path.startswith("lean4/") and path.endswith(".lean")):
            continue
        safe_posix_path(path, "publication source path")
        digest = strict_hex(item.get("sha256"), 64, f"source digest for {path}")
        size = strict_int(item.get("bytes"), f"source size for {path}")
        if path in sources:
            raise CanaryFailure(f"duplicate publication source: {path}")
        sources[path] = {"sha256": digest, "bytes": size}
    if len(sources) != EXPECTED_MODULES:
        raise CanaryFailure(f"publication source count mismatch: {len(sources)}")
    return sources


def validate_cache_manifest(
    manifest: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    expected_scalars = {
        "schema_version": 1,
        "package_role": "derived-olean-cache",
        "cache_scope": "exact-publication-source-closure",
        "public_commit": CACHE_PUBLIC_COMMIT,
        "internal_source_commit": CACHE_INTERNAL_SOURCE_COMMIT,
        "lean_toolchain": LEAN_TOOLCHAIN,
        "producer_platform": "windows-x86_64",
        "main_theorem": gate.ENDPOINTS[14],
        "allowed_axioms": list(gate.ALLOWED_AXIOMS),
        "provider_build_input_signature": CACHE_PROVIDER_BUILD_SIGNATURE,
        "publication_manifest": {
            "path": "PUBLICATION_MANIFEST.json",
            "sha256": CACHE_PUBLICATION_MANIFEST_SHA256,
        },
    }
    for key, expected in expected_scalars.items():
        if manifest.get(key) != expected:
            raise CanaryFailure(f"cache manifest field mismatch: {key}")
    summary = manifest.get("summary")
    if type(summary) is not dict:
        raise CanaryFailure("cache manifest summary is missing")
    expected_summary = {
        "archives": EXPECTED_ARCHIVES,
        "modules": EXPECTED_MODULES,
        "archive_bytes": EXPECTED_ARCHIVE_BYTES,
        "raw_bytes": EXPECTED_LOGICAL_BYTES,
    }
    if summary != expected_summary:
        raise CanaryFailure(f"cache summary mismatch: {summary!r}")
    compression = manifest.get("compression")
    if (
        type(compression) is not dict
        or compression.get("format") != "zip"
        or compression.get("method") != "deflate"
        or compression.get("github_asset_limit_bytes") != MAX_ASSET_BYTES
    ):
        raise CanaryFailure("unsupported cache compression metadata")
    dependency_bootstrap = manifest.get("dependency_bootstrap")
    if dependency_bootstrap != {
        "command": "lake exe cache get",
        "forbidden_command": "lake update",
        "manifest": "lean4/lake-manifest.json",
    }:
        raise CanaryFailure("cache dependency-bootstrap contract mismatch")

    raw_archives = manifest.get("archives")
    raw_files = manifest.get("files")
    if type(raw_archives) is not list or type(raw_files) is not list:
        raise CanaryFailure("cache archives/files must be lists")
    archives: list[dict[str, Any]] = []
    archive_names: set[str] = set()
    part_numbers: list[int] = []
    for record in raw_archives:
        if type(record) is not dict:
            raise CanaryFailure("malformed cache archive record")
        name = record.get("archive")
        if type(name) is not str or Path(name).name != name or name in archive_names:
            raise CanaryFailure(f"unsafe or duplicate archive name: {name!r}")
        match = re.fullmatch(
            r"erdos848-olean-cache-lean-4[.]30[.]0-rc2-windows-x86_64-"
            r"e0dd18260bd4-part-([0-9]{3})-of-075[.]zip",
            name,
        )
        if match is None:
            raise CanaryFailure(f"unexpected archive name: {name}")
        number = int(match.group(1))
        archive_bytes = strict_int(record.get("archive_bytes"), f"archive bytes {name}")
        raw_bytes = strict_int(record.get("raw_bytes"), f"raw bytes {name}")
        if archive_bytes >= MAX_ASSET_BYTES:
            raise CanaryFailure(f"archive exceeds GitHub asset ceiling: {name}")
        digest = strict_hex(record.get("archive_sha256"), 64, f"archive digest {name}")
        archive_names.add(name)
        part_numbers.append(number)
        archives.append(
            {
                "archive": name,
                "archive_bytes": archive_bytes,
                "archive_sha256": digest,
                "raw_bytes": raw_bytes,
            }
        )
    if sorted(part_numbers) != list(range(1, EXPECTED_ARCHIVES + 1)):
        raise CanaryFailure("cache archive parts do not cover exactly 001..075")
    archives.sort(key=lambda item: item["archive"])
    if sum(item["archive_bytes"] for item in archives) != EXPECTED_ARCHIVE_BYTES:
        raise CanaryFailure("cache archive-byte total mismatch")
    if sum(item["raw_bytes"] for item in archives) != EXPECTED_LOGICAL_BYTES:
        raise CanaryFailure("cache raw-byte total mismatch")

    files: dict[str, dict[str, Any]] = {}
    seen_sources: set[str] = set()
    for record in raw_files:
        if type(record) is not dict:
            raise CanaryFailure("malformed cache file record")
        cache_path_value = record.get("cache_path")
        source_path_value = record.get("source_path")
        archive = record.get("archive")
        cache_path = safe_posix_path(cache_path_value, "cache path").as_posix()
        source_path = safe_posix_path(source_path_value, "source path").as_posix()
        if (
            archive not in archive_names
            or cache_path in files
            or source_path in seen_sources
            or cache_path != source_to_olean(source_path)
        ):
            raise CanaryFailure(f"invalid cache/source/archive binding: {cache_path}")
        source = sources.get(source_path)
        if source is None:
            raise CanaryFailure(f"cache record has no publication source: {source_path}")
        source_digest = strict_hex(
            record.get("source_sha256"), 64, f"cache source digest {source_path}"
        )
        if source_digest != source["sha256"]:
            raise CanaryFailure(f"cache source digest mismatch: {source_path}")
        files[cache_path] = {
            "archive": archive,
            "cache_bytes": strict_int(
                record.get("cache_bytes"), f"cache bytes {cache_path}"
            ),
            "cache_sha256": strict_hex(
                record.get("cache_sha256"), 64, f"cache digest {cache_path}"
            ),
            "source_path": source_path,
            "source_sha256": source_digest,
        }
        seen_sources.add(source_path)
    if len(files) != EXPECTED_MODULES or seen_sources != set(sources):
        raise CanaryFailure("cache files do not cover the exact publication sources")
    if sum(item["cache_bytes"] for item in files.values()) != EXPECTED_LOGICAL_BYTES:
        raise CanaryFailure("cache file-byte total mismatch")
    return archives, files


def authenticate_sources(upstream: Path, sources: dict[str, dict[str, Any]]) -> None:
    total = 0
    for index, (relative, record) in enumerate(sorted(sources.items()), start=1):
        path = upstream.joinpath(*PurePosixPath(relative).parts)
        if not path.is_file() or path.is_symlink():
            raise CanaryFailure(f"missing or unsafe publication source: {relative}")
        if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise CanaryFailure(f"publication source content mismatch: {relative}")
        total += path.stat().st_size
        if index % 1000 == 0:
            print(f"SOURCE_AUTHENTICATED {index}/{len(sources)}", flush=True)
    if total != gate.SOURCE_BYTES:
        raise CanaryFailure(f"publication source-byte total mismatch: {total}")


def download(url: str, destination: Path) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise CanaryFailure(f"download URL is not HTTPS: {url}")
    partial = destination.with_suffix(destination.suffix + ".partial")
    if destination.exists() or partial.exists():
        raise CanaryFailure(f"refusing to overwrite download: {destination}")
    command = (
        "curl.exe", "--proto", "=https", "--tlsv1.2", "--location",
        "--fail", "--silent", "--show-error", "--retry", "5",
        "--retry-delay", "5", "--retry-all-errors", "--output",
        str(partial), url,
    )
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise CanaryFailure(f"curl failed ({completed.returncode}): {url}")
    os.replace(partial, destination)


def zip_member_map(
    bundle: zipfile.ZipFile, expected: set[str]
) -> dict[str, zipfile.ZipInfo]:
    result: dict[str, zipfile.ZipInfo] = {}
    for info in bundle.infolist():
        name = safe_posix_path(info.filename, "ZIP member").as_posix()
        unix_mode = (info.external_attr >> 16) & 0xFFFF
        if (
            name in result
            or info.is_dir()
            or info.flag_bits & 0x1
            or stat.S_IFMT(unix_mode) == stat.S_IFLNK
            or info.compress_type != zipfile.ZIP_DEFLATED
        ):
            raise CanaryFailure(f"unsafe ZIP member: {name}")
        result[name] = info
    if set(result) != expected:
        raise CanaryFailure(
            "ZIP member set mismatch: "
            f"missing={sorted(expected - set(result))[:3]} "
            f"extra={sorted(set(result) - expected)[:3]}"
        )
    return result


def run_compact(path: Path) -> None:
    completed = subprocess.run(
        ("compact.exe", "/C", "/I", "/F", "/Q", f"/S:{path}", "*.olean"),
        cwd=path, check=False,
    )
    if completed.returncode != 0:
        raise CanaryFailure(f"compact.exe failed ({completed.returncode}): {path}")


def mark_directory_compressed(path: Path) -> None:
    completed = subprocess.run(
        ("compact.exe", "/C", "/I", "/Q", str(path)), check=False
    )
    if completed.returncode != 0:
        raise CanaryFailure(
            f"compact.exe could not mark directory compressed ({completed.returncode}): {path}"
        )
    attributes = getattr(
        path.stat(follow_symlinks=False), "st_file_attributes", 0
    )
    if not attributes & FILE_ATTRIBUTE_COMPRESSED:
        raise CanaryFailure(f"directory did not acquire NTFS compression: {path}")


def is_compressed(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & FILE_ATTRIBUTE_COMPRESSED)


def compressed_size(path: Path) -> int:
    high = ctypes.c_ulong(0)
    low = ctypes.windll.kernel32.GetCompressedFileSizeW(str(path), ctypes.byref(high))
    if low == 0xFFFFFFFF:
        error = ctypes.windll.kernel32.GetLastError()
        if error:
            raise CanaryFailure(f"GetCompressedFileSizeW failed ({error}): {path}")
    return (int(high.value) << 32) | int(low)


def install_cache(
    upstream: Path,
    scratch: Path,
    archives: list[dict[str, Any]],
    files: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    target_root = upstream / "lean4" / ".lake" / "build" / "lib" / "lean"
    project_root = target_root / "Erdos848"
    if project_root.exists() and any(project_root.rglob("*.olean")):
        raise CanaryFailure("cache installation requires zero project OLeans")
    target_root.mkdir(parents=True, exist_ok=True)
    if target_root.stat().st_dev != scratch.stat().st_dev:
        raise CanaryFailure("cache staging and destination must share one NTFS volume")
    mark_directory_compressed(target_root)
    reports: list[dict[str, Any]] = []
    for index, archive in enumerate(archives, start=1):
        name = archive["archive"]
        assigned = {
            path: record for path, record in files.items()
            if record["archive"] == name
        }
        if not assigned:
            raise CanaryFailure(f"manifest archive has no assigned files: {name}")
        zip_path = scratch / name
        stage = scratch / f"stage-{index:03d}"
        if stage.exists():
            raise CanaryFailure(f"staging directory unexpectedly exists: {stage}")
        stage.mkdir()
        mark_directory_compressed(stage)
        print(f"CACHE_SHARD {index}/{len(archives)} download {name}", flush=True)
        download(f"{CACHE_RELEASE_BASE}/{name}", zip_path)
        if zip_path.stat().st_size != archive["archive_bytes"]:
            raise CanaryFailure(f"archive size mismatch: {name}")
        if sha256_file(zip_path) != archive["archive_sha256"]:
            raise CanaryFailure(f"archive SHA-256 mismatch: {name}")
        logical_bytes = 0
        try:
            with zipfile.ZipFile(zip_path, "r") as bundle:
                members = zip_member_map(bundle, set(assigned))
                for member_name, info in members.items():
                    if info.file_size != assigned[member_name]["cache_bytes"]:
                        raise CanaryFailure(
                            f"ZIP member declares the wrong size: {member_name}"
                        )
                    destination = safe_destination(stage, member_name)
                    require_no_reparse_ancestors(destination.parent, stage)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    temporary = destination.with_name(f".{destination.name}.partial")
                    digest = hashlib.sha256()
                    copied = 0
                    with bundle.open(info, "r") as source, temporary.open("xb") as target:
                        for block in iter(lambda: source.read(1 << 20), b""):
                            target.write(block)
                            digest.update(block)
                            copied += len(block)
                        target.flush()
                        os.fsync(target.fileno())
                    record = assigned[member_name]
                    if copied != record["cache_bytes"] or digest.hexdigest() != record["cache_sha256"]:
                        raise CanaryFailure(f"decompressed OLean mismatch: {member_name}")
                    os.replace(temporary, destination)
                    logical_bytes += copied
            if logical_bytes != archive["raw_bytes"]:
                raise CanaryFailure(f"archive raw-byte mismatch: {name}")
            run_compact(stage)
            allocated_bytes = 0
            for member_name in sorted(assigned):
                staged = safe_destination(stage, member_name)
                if not staged.is_file() or staged.is_symlink() or not is_compressed(staged):
                    raise CanaryFailure(f"staged OLean is not a compressed regular file: {member_name}")
                allocated_bytes += compressed_size(staged)
                destination = upstream.joinpath(*PurePosixPath(member_name).parts).resolve(strict=False)
                expected_root = target_root.resolve(strict=True)
                try:
                    destination.relative_to(expected_root)
                except ValueError as error:
                    raise CanaryFailure(f"cache destination escaped OLean root: {member_name}") from error
                require_no_reparse_ancestors(destination.parent, upstream.resolve(strict=True))
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise CanaryFailure(f"cache destination already exists: {member_name}")
                os.replace(staged, destination)
                if not is_compressed(destination):
                    raise CanaryFailure(f"installed OLean lost compression: {member_name}")
            reports.append(
                {
                    "archive": name,
                    "archive_bytes": archive["archive_bytes"],
                    "archive_sha256": archive["archive_sha256"],
                    "files": len(assigned),
                    "logical_bytes": logical_bytes,
                    "ntfs_allocated_bytes": allocated_bytes,
                }
            )
        finally:
            if zip_path.exists():
                zip_path.unlink()
            if stage.exists():
                resolved_stage = stage.resolve(strict=True)
                if resolved_stage.parent != scratch.resolve(strict=True) or stage.is_symlink():
                    raise CanaryFailure(f"refusing unsafe staging cleanup: {stage}")
                shutil.rmtree(resolved_stage)
        print(
            f"CACHE_SHARD {index}/{len(archives)} installed files={len(assigned)} "
            f"logical={logical_bytes}",
            flush=True,
        )
    return reports


def set_cache_mtimes(upstream: Path, files: dict[str, dict[str, Any]]) -> int:
    newest_source = max(
        upstream.joinpath(*PurePosixPath(record["source_path"]).parts).stat().st_mtime_ns
        for record in files.values()
    )
    installed_mtime = max(time.time_ns(), newest_source + 2_000_000_000)
    for cache_path in files:
        path = upstream.joinpath(*PurePosixPath(cache_path).parts)
        os.utime(path, ns=(installed_mtime, installed_mtime))
    return installed_mtime


def publication_module_name(cache_path: str) -> str:
    prefix = PurePosixPath("lean4/.lake/build/lib/lean")
    path = safe_posix_path(cache_path, "cache path")
    relative = PurePosixPath(*path.parts[len(prefix.parts):]).with_suffix("")
    return ".".join(relative.parts)


def verify_cache_inventory(
    upstream: Path, files: dict[str, dict[str, Any]], *, hash_contents: bool
) -> dict[str, Any]:
    names: list[str] = []
    logical_bytes = 0
    allocated_bytes = 0
    inventory = hashlib.sha256()
    for index, (cache_path, record) in enumerate(sorted(files.items()), start=1):
        path = upstream.joinpath(*PurePosixPath(cache_path).parts)
        if not path.is_file() or path.is_symlink() or not is_compressed(path):
            raise CanaryFailure(f"installed OLean is missing, unsafe, or uncompressed: {cache_path}")
        if path.stat().st_size != record["cache_bytes"]:
            raise CanaryFailure(f"installed OLean size mismatch: {cache_path}")
        if hash_contents and sha256_file(path) != record["cache_sha256"]:
            raise CanaryFailure(f"installed OLean SHA-256 mismatch: {cache_path}")
        logical_bytes += path.stat().st_size
        allocated_bytes += compressed_size(path)
        names.append(publication_module_name(cache_path))
        inventory.update(
            f"{cache_path}\t{record['cache_bytes']}\t{record['cache_sha256']}\n".encode("ascii")
        )
        if hash_contents and index % 1000 == 0:
            print(f"OLEAN_POSTFLIGHT {index}/{len(files)}", flush=True)
    names.sort()
    observed_names = gate.built_project_modules(upstream / "lean4")
    if tuple(names) != observed_names:
        raise CanaryFailure("installed project OLean module inventory mismatch")
    if len(names) != EXPECTED_MODULES or logical_bytes != EXPECTED_LOGICAL_BYTES:
        raise CanaryFailure("installed OLean count or logical-byte total mismatch")
    if gate.module_list_digest(names) != gate.PUBLICATION_MODULE_LIST_SHA256:
        raise CanaryFailure("installed publication module-list digest mismatch")
    if allocated_bytes > MAX_COMPRESSED_CACHE_BYTES:
        raise CanaryFailure(f"compressed cache exceeds 60 GiB ceiling: {allocated_bytes}")
    return {
        "modules": len(names),
        "module_list_sha256": gate.module_list_digest(names),
        "logical_bytes": logical_bytes,
        "ntfs_allocated_bytes": allocated_bytes,
        "inventory_sha256": inventory.hexdigest(),
        "content_hashes_verified": hash_contents,
        "compressed_files": len(names),
    }


def memory_snapshot() -> dict[str, int]:
    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise CanaryFailure("GlobalMemoryStatusEx failed")
    return {
        "total_physical_bytes": int(status.total_phys),
        "available_physical_bytes": int(status.avail_phys),
        "total_commit_bytes": int(status.total_page_file),
        "available_commit_bytes": int(status.avail_page_file),
        "total_virtual_bytes": int(status.total_virtual),
        "available_virtual_bytes": int(status.avail_virtual),
    }


def resource_snapshot(upstream: Path, phase: str) -> dict[str, Any]:
    usage = shutil.disk_usage(upstream)
    return {
        "phase": phase,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "memory": memory_snapshot(),
        "storage": {
            "root": str(Path(upstream.anchor)),
            "capacity_bytes": usage.total,
            "free_bytes": usage.free,
        },
    }


def probe_available_commit(bytes_to_probe: int) -> None:
    kernel32 = ctypes.windll.kernel32
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    pointer = kernel32.VirtualAlloc(None, ctypes.c_size_t(bytes_to_probe), 0x3000, 0x04)
    if not pointer:
        raise CanaryFailure(
            "VirtualAlloc commit probe failed "
            f"({kernel32.GetLastError()}): {bytes_to_probe}"
        )
    try:
        pass
    finally:
        if not kernel32.VirtualFree(ctypes.c_void_p(pointer), 0, 0x8000):
            raise CanaryFailure("VirtualFree failed after commit probe")


def process_working_set(process: subprocess.Popen[str]) -> int:
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(
        ctypes.c_void_p(process._handle), ctypes.byref(counters), counters.cb
    ):
        raise CanaryFailure("GetProcessMemoryInfo failed")
    return int(counters.working_set_size)


def run_lean_commit_guarded(
    name: str,
    command: Sequence[str],
    cwd: Path,
    receipt_dir: Path,
    env: dict[str, str],
    *,
    timeout_seconds: int = 7200,
) -> tuple[Path, dict[str, int]]:
    log_path = receipt_dir / f"{name}.log"
    partial = receipt_dir / f"{name}.partial.log"
    if log_path.exists() or partial.exists():
        raise CanaryFailure(f"refusing to overwrite Lean canary log: {name}")
    heading = f"COMMAND {shlex.join(command)}\nCWD {cwd}\n"
    print(heading, end="", flush=True)

    def terminate_tree(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        subprocess.run(
            ("taskkill", "/PID", str(process.pid), "/T", "/F"),
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired as error:
            raise CanaryFailure(
                f"could not terminate Lean process tree for {name}"
            ) from error

    with partial.open("w", encoding="utf-8", newline="\n") as log:
        log.write(heading)
        log.flush()
        process = subprocess.Popen(
            list(command), cwd=cwd, env=env, text=True,
            stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        peak = 0
        trims = 0
        deadline = time.monotonic() + timeout_seconds
        next_report = time.monotonic() + 30
        try:
            while process.poll() is None:
                try:
                    working_set = process_working_set(process)
                except CanaryFailure:
                    if process.poll() is not None:
                        break
                    raise
                peak = max(peak, working_set)
                if working_set > TRIM_WORKING_SET_MIB * (1 << 20):
                    if ctypes.windll.psapi.EmptyWorkingSet(ctypes.c_void_p(process._handle)):
                        trims += 1
                now = time.monotonic()
                if now >= next_report:
                    print(
                        f"LEAN_MONITOR {name} working_set_mib={working_set / (1 << 20):.1f} "
                        f"peak_mib={peak / (1 << 20):.1f} trims={trims}",
                        flush=True,
                    )
                    next_report = now + 30
                if now >= deadline:
                    raise CanaryFailure(
                        f"Lean command timed out after {timeout_seconds}s: {name}"
                    )
                time.sleep(1)
        except BaseException:
            terminate_tree(process)
            raise
        returncode = process.returncode
        log.write(f"CANARY_PEAK_WORKING_SET_BYTES {peak}\n")
        log.write(f"CANARY_WORKING_SET_TRIMS {trims}\n")
        log.flush()
        os.fsync(log.fileno())
    if returncode != 0:
        raise CanaryFailure(f"Lean command failed ({returncode}): {name}; inspect {partial}")
    os.replace(partial, log_path)
    return log_path, {"peak_working_set_bytes": peak, "working_set_trims": trims}


def runtime_binaries(runtime_root: Path, runtime_archive: Path) -> tuple[Path, Path]:
    if sha256_file(runtime_archive) != RUNTIME_ARCHIVE_SHA256:
        raise CanaryFailure("Lean runtime archive SHA-256 mismatch")
    lean = [
        path for path in runtime_root.rglob("lean.exe")
        if path.is_file() and not path.is_symlink() and path.parent.name == "bin"
    ]
    lake = [
        path for path in runtime_root.rglob("lake.exe")
        if path.is_file() and not path.is_symlink() and path.parent.name == "bin"
    ]
    if len(lean) != 1 or len(lake) != 1 or lean[0].parent != lake[0].parent:
        raise CanaryFailure("could not resolve one authenticated Lean/Lake runtime")
    return lean[0].resolve(strict=True), lake[0].resolve(strict=True)


def endpoint_expected_paths(project_root: Path, modules: Iterable[str]) -> dict[str, Path]:
    return {
        module: project_root.joinpath(*module.split(".")).with_suffix(".olean")
        for module in modules
    }


def run_self_tests() -> int:
    assert strict_int(0, "zero") == 0
    for invalid in (True, 1.0, "1", -1):
        try:
            strict_int(invalid, "invalid")
        except CanaryFailure:
            pass
        else:
            raise AssertionError(f"strict_int accepted {invalid!r}")
    assert safe_posix_path("lean4/Erdos848/Foo.olean", "test").as_posix().endswith("Foo.olean")
    for invalid in ("", "/x", "../x", "a/../x", "a\\b", "C:/x", ".git/x"):
        try:
            safe_posix_path(invalid, "test")
        except CanaryFailure:
            pass
        else:
            raise AssertionError(f"safe_posix_path accepted {invalid!r}")
    assert source_to_olean("lean4/Erdos848/Foo.lean") == (
        "lean4/.lake/build/lib/lean/Erdos848/Foo.olean"
    )
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        archive = root / "good.zip"
        member = "lean4/.lake/build/lib/lean/Erdos848/Foo.olean"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr(member, b"olean")
        with zipfile.ZipFile(archive, "r") as bundle:
            assert set(zip_member_map(bundle, {member})) == {member}
        with zipfile.ZipFile(archive, "r") as bundle:
            try:
                zip_member_map(bundle, {member, member + ".missing"})
            except CanaryFailure:
                pass
            else:
                raise AssertionError("ZIP member coverage mutation was accepted")
        duplicate = root / "duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(duplicate, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr(member, b"one")
                bundle.writestr(member, b"two")
        with zipfile.ZipFile(duplicate, "r") as bundle:
            try:
                zip_member_map(bundle, {member})
            except CanaryFailure:
                pass
            else:
                raise AssertionError("duplicate ZIP member was accepted")
    print("CACHED LEAN CANARY SELF-TESTS PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--receipt-dir", type=Path)
    parser.add_argument("--scratch-dir", type=Path)
    parser.add_argument("--memory-mib", type=int, default=MEMORY_MIB)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_tests()
    required = {
        "--upstream-root": args.upstream_root,
        "--runtime-root": args.runtime_root,
        "--runtime-archive": args.runtime_archive,
        "--receipt-dir": args.receipt_dir,
        "--scratch-dir": args.scratch_dir,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error(f"required outside --self-test: {', '.join(missing)}")
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise CanaryFailure(f"cache canary requires Windows x86-64, got {sys.platform}/{platform.machine()}")
    if args.memory_mib != MEMORY_MIB:
        raise CanaryFailure(f"cache canary requires the audited {MEMORY_MIB} MiB ceiling")

    upstream = args.upstream_root.resolve(strict=True)
    receipt_dir = prepare_empty_external_dir(args.receipt_dir, upstream, "receipt directory")
    scratch = prepare_empty_external_dir(args.scratch_dir, upstream, "scratch directory")
    runtime_root = args.runtime_root.resolve(strict=True)
    runtime_archive = args.runtime_archive.resolve(strict=True)
    root_before = gate.root_snapshot(require_clean=True)
    lock = gate.read_lock()
    lean_executable, lake_executable = runtime_binaries(runtime_root, runtime_archive)
    runtime_bin = lean_executable.parent
    base_env = gate.sanitized_lean_environment()
    base_env["PATH"] = str(runtime_bin) + os.pathsep + base_env.get("PATH", "")
    base_env["PYTHONDONTWRITEBYTECODE"] = "1"
    if Path(run_capture(("where.exe", "lean.exe"), REPO_ROOT, base_env).splitlines()[0]).resolve() != lean_executable:
        raise CanaryFailure("authenticated Lean runtime is not first on PATH")
    version = run_capture((str(lean_executable), "--version"), REPO_ROOT, base_env)
    if not version.startswith("Lean (version 4.30.0-rc2,") or f"commit {LEAN_COMMIT}," not in version:
        raise CanaryFailure(f"unexpected Lean runtime version: {version}")
    if not lake_executable.is_file():
        raise CanaryFailure("authenticated Lake executable is missing")

    cache_identity = git_identity(upstream)
    if (
        cache_identity["revision"],
        cache_identity["tree"],
        cache_identity["lean_tree"],
    ) != (CACHE_PUBLIC_COMMIT, CACHE_PUBLIC_TREE, LEAN_TREE):
        raise CanaryFailure(f"cache-origin checkout mismatch: {cache_identity}")
    publication_path = upstream / "PUBLICATION_MANIFEST.json"
    if sha256_file(publication_path) != CACHE_PUBLICATION_MANIFEST_SHA256:
        raise CanaryFailure("cache-origin publication manifest SHA-256 mismatch")
    publication = load_json(publication_path, "publication manifest")
    sources = publication_sources(publication)
    authenticate_sources(upstream, sources)

    cache_manifest_path = receipt_dir / CACHE_MANIFEST_NAME
    download(f"{CACHE_RELEASE_BASE}/{CACHE_MANIFEST_NAME}", cache_manifest_path)
    if sha256_file(cache_manifest_path) != CACHE_MANIFEST_SHA256:
        raise CanaryFailure("cache manifest SHA-256 mismatch")
    cache_manifest = load_json(cache_manifest_path, "cache manifest")
    archives, files = validate_cache_manifest(cache_manifest, sources)

    initial_resources = resource_snapshot(upstream, "before-cache-install")
    maximum_archive = max(item["archive_bytes"] for item in archives)
    minimum_initial_free = (
        MAX_COMPRESSED_CACHE_BYTES + maximum_archive + MIN_POST_CACHE_FREE_BYTES
    )
    if initial_resources["storage"]["free_bytes"] < minimum_initial_free:
        raise CanaryFailure(
            "insufficient storage for compressed cache, one shard, and reserve: "
            f"{initial_resources['storage']['free_bytes']} < {minimum_initial_free}"
        )
    shard_reports = install_cache(upstream, scratch, archives, files)
    preliminary_inventory = verify_cache_inventory(upstream, files, hash_contents=False)

    logs: dict[str, str] = {}
    checkout_log = gate.run_logged(
        "00-target-checkout",
        ("git", "checkout", "--detach", TARGET_COMMIT),
        upstream,
        receipt_dir,
        1800,
        base_env,
    )
    logs[checkout_log.name] = sha256_file(checkout_log)
    target_identity = git_identity(upstream)
    if (
        target_identity["revision"], target_identity["tree"], target_identity["lean_tree"]
    ) != (TARGET_COMMIT, TARGET_TREE, LEAN_TREE):
        raise CanaryFailure(f"target ART-006 checkout mismatch: {target_identity}")
    before = gate.source_snapshot(upstream)
    installed_mtime = set_cache_mtimes(upstream, files)

    lean4 = upstream / "lean4"
    dependencies_before = gate.prepare_dependencies(lean4, receipt_dir, logs)
    resolved_lean, lake_entries = gate.resolved_lean_environment(lean4, base_env)
    if resolved_lean != lean_executable:
        raise CanaryFailure(
            f"Lake resolved {resolved_lean}, expected authenticated runtime {lean_executable}"
        )
    cache_log = gate.run_logged(
        "01-mathlib-cache",
        (str(lake_executable), "exe", "cache", "get"),
        lean4,
        receipt_dir,
        7200,
        base_env,
    )
    logs[cache_log.name] = sha256_file(cache_log)
    if gate.dependency_snapshot(lean4) != dependencies_before:
        raise CanaryFailure("Lake dependencies changed during cache bootstrap")

    project_olean_root = (lean4 / ".lake" / "build" / "lib" / "lean").resolve(strict=True)
    gate.require_namespace_provenance(
        lake_entries, project_root=project_olean_root, completion_root=None
    )
    direct_env = gate.explicit_lean_environment(base_env, lake_entries)
    after_dependencies = resource_snapshot(upstream, "after-dependencies")
    if after_dependencies["storage"]["free_bytes"] < MIN_POST_CACHE_FREE_BYTES:
        raise CanaryFailure("less than 40 GiB free before trust-zero canary")
    commit_probe_bytes = (MEMORY_MIB + COMMIT_GUARD_MIB) * (1 << 20)
    probe_available_commit(commit_probe_bytes)
    after_probe = resource_snapshot(upstream, "after-commit-probe")

    provider_source = lean4 / "Erdos848" / "PaperGeneratedCertificateProvider.lean"
    provider_command = (
        str(lean_executable), "--trust=0", "-M", str(MEMORY_MIB), "-j", "1",
        f"--root={lean4}", str(provider_source),
    )
    provider_log, provider_memory = run_lean_commit_guarded(
        "02-provider-trust-zero", provider_command, lean4, receipt_dir, direct_env
    )
    logs[provider_log.name] = sha256_file(provider_log)

    olean_root = receipt_dir / "root-oleans"
    final_olean = olean_root / "Erdos848Completion" / "Final.olean"
    final_olean.parent.mkdir(parents=True)
    final_command = (
        str(lean_executable), "--trust=0", "-M", str(MEMORY_MIB), "-j", "1",
        f"--root={LEAN_AUDIT_ROOT}", "-o", str(final_olean), str(gate.FINAL_SOURCE),
    )
    final_log, final_memory = run_lean_commit_guarded(
        "03-root-final-trust-zero", final_command, lean4, receipt_dir, direct_env
    )
    logs[final_log.name] = sha256_file(final_log)
    if not final_olean.is_file() or final_olean.is_symlink():
        raise CanaryFailure("root theorem did not produce a safe OLean")

    audit_entries = (olean_root.resolve(strict=True), *lake_entries)
    gate.require_namespace_provenance(
        audit_entries, project_root=project_olean_root, completion_root=olean_root
    )
    audit_env = gate.explicit_lean_environment(base_env, audit_entries)
    audit_command = (
        str(lean_executable), "--trust=0", "-M", str(MEMORY_MIB), "-j", "1",
        f"--root={LEAN_AUDIT_ROOT}", str(gate.AUDIT_SOURCE),
    )
    audit_log, audit_memory = run_lean_commit_guarded(
        "04-root-live-axioms", audit_command, lean4, receipt_dir, audit_env
    )
    logs[audit_log.name] = sha256_file(audit_log)
    axiom_reports = gate.parse_axioms(audit_log.read_text(encoding="utf-8"))

    provider_deps_log = gate.run_logged(
        "05-provider-dependencies",
        (str(lean_executable), "--deps", f"--root={lean4}", str(provider_source)),
        lean4, receipt_dir, 7200, direct_env,
    )
    provider_imports = gate.project_imports(provider_source)
    gate.require_direct_dependencies(
        provider_deps_log.read_text(encoding="utf-8"),
        expected=endpoint_expected_paths(project_olean_root, provider_imports),
        label="provider source",
    )
    logs[provider_deps_log.name] = sha256_file(provider_deps_log)

    final_deps_log = gate.run_logged(
        "06-root-final-dependencies",
        (str(lean_executable), "--deps", f"--root={LEAN_AUDIT_ROOT}", str(gate.FINAL_SOURCE)),
        lean4, receipt_dir, 7200, direct_env,
    )
    gate.require_direct_dependencies(
        final_deps_log.read_text(encoding="utf-8"),
        expected=endpoint_expected_paths(
            project_olean_root,
            (
                "Erdos848.PaperGeneratedCertificateProvider",
                "Erdos848.HallReduction",
                "Erdos848.SharpnessCore",
            ),
        ),
        label="root final theorem",
    )
    logs[final_deps_log.name] = sha256_file(final_deps_log)

    audit_deps_log = gate.run_logged(
        "07-root-audit-dependencies",
        (str(lean_executable), "--deps", f"--root={LEAN_AUDIT_ROOT}", str(gate.AUDIT_SOURCE)),
        lean4, receipt_dir, 7200, audit_env,
    )
    gate.require_direct_dependencies(
        audit_deps_log.read_text(encoding="utf-8"),
        expected={"Erdos848Completion.Final": final_olean},
        label="root axiom audit",
    )
    logs[audit_deps_log.name] = sha256_file(audit_deps_log)

    after = gate.source_snapshot(upstream)
    if after != before:
        raise CanaryFailure("target ART-006 tracked sources changed during canary")
    dependencies_after = gate.dependency_snapshot(lean4)
    if dependencies_after != dependencies_before:
        raise CanaryFailure("Lake dependencies changed during canary")
    root_after = gate.root_snapshot(require_clean=True)
    if root_after != root_before:
        raise CanaryFailure("root diagnostic repository changed during canary")
    final_inventory = verify_cache_inventory(upstream, files, hash_contents=True)
    if final_inventory["inventory_sha256"] != preliminary_inventory["inventory_sha256"]:
        raise CanaryFailure("cache inventory binding changed during canary")
    final_resources = resource_snapshot(upstream, "after-canary")

    receipt = {
        "version": 1,
        "status": "cache-backed-lean-canary-passed",
        "claim": {
            "verifies": [
                "exact cache-origin authentication",
                "identical lean4-tree bridge to the pinned ART-006 target",
                "sequential authenticated NTFS-compressed cache installation",
                "live trust-zero provider elaboration",
                "live trust-zero root theorem compilation",
                "nineteen live axiom reports",
                "source, OLean, direct-import, and Lake dependency provenance",
            ],
            "does_not_verify": [
                "clean source build of the 30638-module closure",
                "deterministic source-to-OLean reproduction",
                "proof-DAG node L1",
                "proof-DAG node L2 as dependency-ordered after L1",
                "proof-DAG nodes RCLEAN, V0, or P848",
            ],
        },
        "github": {
            "repository": os.environ.get("GITHUB_REPOSITORY", ""),
            "sha": os.environ.get("GITHUB_SHA", ""),
            "ref": os.environ.get("GITHUB_REF", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        },
        "runner": {
            "script_sha256": sha256_file(SCRIPT_PATH),
            "workflow_sha256": sha256_file(
                REPO_ROOT / ".github" / "workflows" / "cached-lean-canary.yml"
            ),
        },
        "source_lock_sha256": sha256_file(gate.LOCK_PATH),
        "root_repository": root_after,
        "cache_origin": {
            **cache_identity,
            "publication_manifest_sha256": CACHE_PUBLICATION_MANIFEST_SHA256,
            "cache_manifest_sha256": CACHE_MANIFEST_SHA256,
        },
        "target_upstream": after,
        "cache": {
            "release_tag": CACHE_RELEASE_TAG,
            "install_mode": "one authenticated ZIP downloaded, installed, and deleted before the next",
            "manifest_summary": cache_manifest["summary"],
            "shards": shard_reports,
            "preliminary_inventory": preliminary_inventory,
            "final_inventory": final_inventory,
            "installed_mtime_ns": installed_mtime,
        },
        "toolchain": {
            "lean": LEAN_TOOLCHAIN,
            "lean_commit": LEAN_COMMIT,
            "runtime_archive": RUNTIME_ARCHIVE_NAME,
            "runtime_archive_sha256": RUNTIME_ARCHIVE_SHA256,
            "observed_lean_version": version,
            "lean_executable": str(lean_executable),
            "lake_executable": str(lake_executable),
        },
        "lake_dependencies": dependencies_after,
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "memory_mib": MEMORY_MIB,
            "commit_guard_mib": COMMIT_GUARD_MIB,
            "working_set_trim_mib": TRIM_WORKING_SET_MIB,
            "commit_probe_bytes": commit_probe_bytes,
            "snapshots": [initial_resources, after_dependencies, after_probe, final_resources],
        },
        "effective_lean_path": [str(path) for path in audit_entries],
        "provider": {
            "declaration": gate.ENDPOINTS[14],
            "source_sha256": sha256_file(provider_source),
            "trust_zero_log": provider_log.name,
            "dependency_log": provider_deps_log.name,
            "direct_project_imports": list(provider_imports),
            "memory": provider_memory,
        },
        "root_final": {
            "source_sha256": sha256_file(gate.FINAL_SOURCE),
            "olean_sha256": sha256_file(final_olean),
            "trust_zero_log": final_log.name,
            "dependency_log": final_deps_log.name,
            "memory": final_memory,
        },
        "axiom_audit": {
            "source_sha256": sha256_file(gate.AUDIT_SOURCE),
            "trust_zero_log": audit_log.name,
            "dependency_log": audit_deps_log.name,
            "memory": audit_memory,
        },
        "allowed_axioms": list(gate.ALLOWED_AXIOMS),
        "axiom_reports": axiom_reports,
        "logs": logs,
    }
    receipt_path = receipt_dir / "cached-lean-canary-receipt.json"
    gate.atomic_write(receipt_path, canonical_json(receipt))
    print(f"receipt={receipt_path}")
    print(f"receipt_sha256={sha256_file(receipt_path)}")
    print("CACHE-BACKED LEAN CANARY PASSED")
    print("CACHE CANARY LIMITATION: no clean source build was performed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        CanaryFailure,
        gate.GateFailure,
        OSError,
        ValueError,
        subprocess.SubprocessError,
        zipfile.BadZipFile,
    ) as error:
        print(f"CACHE-BACKED LEAN CANARY FAILED: {error}", file=sys.stderr)
        raise SystemExit(1) from error
