#!/usr/bin/env python3
"""Check every computational certificate used by the all-N proof.

The default profile is theorem-grade: it authenticates the exact statement,
the pinned ART-005 tree, every local checker and committed receipt, then runs
all positive replays and semantic negative controls.  It emits a final receipt
only after all six stages pass.  The conclusion certifies the computational
nodes; the human structural lemmas and high-range proof remain separate
mathematical dependencies documented in ``docs/computation-spec.md``.

Completed stages can be resumed from a caller-supplied work directory.  A
checkpoint is accepted only when its manifest, dependency, command, tool,
output, and log digests still match.  Such an unsigned local checkpoint does
not attest that a command ran: resumed execution therefore never emits the
theorem-grade certificate PASS.  That PASS requires one fresh uninterrupted
six-stage run.  ``--preflight-only`` performs authentication but never prints
a certificate PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import shlex
import shutil
import stat
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "certificates" / "all-n-manifest-v1.json"
DEFAULT_CANDIDATE = ROOT / "external" / "erdos-848-all-n"
EXPECTED_MANIFEST_VERSION = 1
EXPECTED_STATEMENT_SHA256 = (
    "1a50dd45f495ae08d98d79200154e54a946d1e6d9c36259c5226eb8ce4885f5b"
)
EXPECTED_ART005_URL = "https://github.com/ipitchford/erdos-848-all-n.git"
EXPECTED_ART005_REVISION = "1afd7c722cae5ee7dd0fd1fde64427537394f749"
EXPECTED_ART005_TREE = "6dedab80313f06e232b0ca47c29ebaf39ce35b17"
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "6f197f0d5bef00c97275915ee21dcf8891543eab54dda9312c4227bbde927573"
)
EXPECTED_PREFIX_SHA256 = (
    "693ce882fb3f3786caf8eb502dd0677f42a4ed687adaa71a613b27ad7ef49727"
)
EXPECTED_P13_SHA256 = (
    "cb67a19e9edfc21206b6ec0c886bf6aa67b97a110296f7e20bf00bdf818cfc64"
)
EXPECTED_HIGH_SHA256 = (
    "8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f"
)
EXPECTED_HIGH_CLAIMS_SHA256 = (
    "4726814d80fc63353a77c18bac8691bc917efd5ef1c7dcf10a14aed03674b215"
)
EXPECTED_COVERAGE_SHA256 = (
    "b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1"
)
EXPECTED_STAGES = (
    "prefix",
    "p13-primality",
    "finite-independent",
    "high-numerics",
    "art005-release",
    "coverage",
)
WORK_SENTINEL = ".erdos848-all-n-work-v1.json"
EXPECTED_CERTIFICATES = (
    (
        "certificates/prefix-10000.json",
        "693ce882fb3f3786caf8eb502dd0677f42a4ed687adaa71a613b27ad7ef49727",
    ),
    (
        "certificates/p13-factor-primality.json",
        "cb67a19e9edfc21206b6ec0c886bf6aa67b97a110296f7e20bf00bdf818cfc64",
    ),
    (
        "certificates/finite-factor-leaves.json",
        "4fc75b0ed263df81c07c5997c915511351ea61fff085d3ac95159c524ca9aad6",
    ),
)
EXPECTED_CHECKER_SOURCES = (
    (
        "computations/generate_prefix_certificate.py",
        "fdf19172564868946ff26916cda76c4ad47574ddeda0242bd71d05b4caad46dd",
    ),
    (
        "computations/check_prefix_certificate.py",
        "615bd9a0d4a4c5ed6c45fcde2854131001c86c6feafbbdf0dab326d2728b2576",
    ),
    (
        "computations/test_prefix_checker.py",
        "3cdce143570e5dcb06b622c892dbe414195ba877749b0a0c9faa27140c304903",
    ),
    (
        "computations/exhaustive_small_prefix.py",
        "f68e61c73cdc4566bceac4bfb84af11933daf50cdea71b2bf60aff9d9f078f1d",
    ),
    (
        "computations/check_p13_factor_primality.py",
        "71403895bd9a06a131a4ca84bf5d7260e7be8484488e9dfc7514364921581899",
    ),
    (
        "scripts/independent_check.py",
        "f54b8dcbafd07178d18df8b3cd6b16652c30ae41ef7ee1c968d874a046f6bf0b",
    ),
    (
        "computations/test_all_n_manifest.py",
        "9b4bab29a149941144b19ea17d4921dc2b2813a63e4228d5a3d99390c031259b",
    ),
    (
        "computations/test_all_n_resume.py",
        "ee6157eca435ae3b55cba93cb6f1871e60b50314d540ae95f44169452d9ba2c3",
    ),
)


class CheckFailure(RuntimeError):
    """A fail-closed certificate or environment error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode("ascii")


def reject_float(value: str) -> None:
    raise CheckFailure(f"floating-point JSON value is forbidden: {value}")


def reject_constant(value: str) -> None:
    raise CheckFailure(f"non-finite JSON value is forbidden: {value}")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CheckFailure(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_canonical_json(path: Path) -> Any:
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw,
            object_pairs_hook=unique_object,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckFailure(f"invalid JSON in {path}: {error}") from error
    if raw != canonical_json(value):
        raise CheckFailure(f"JSON is not in the required canonical form: {path}")
    return value


def require_keys(value: Any, keys: Sequence[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise CheckFailure(f"{label} must be an object")
    if list(value) != list(keys):
        raise CheckFailure(
            f"{label} keys/order mismatch: expected {list(keys)}, got {list(value)}"
        )
    return value


def require_string(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise CheckFailure(f"{label} must be a nonempty string")
    return value


def require_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise CheckFailure(f"{label} must be an integer")
    return value


def safe_repo_path(raw: Any, label: str) -> Path:
    text = require_string(raw, label)
    relative = PurePosixPath(text)
    if (
        relative.is_absolute()
        or not relative.parts
        or "." in relative.parts
        or ".." in relative.parts
        or text != relative.as_posix()
    ):
        raise CheckFailure(f"unsafe repository path for {label}: {text!r}")
    path = ROOT.joinpath(*relative.parts)
    root_resolved = ROOT.resolve(strict=True)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (FileNotFoundError, ValueError) as error:
        raise CheckFailure(f"missing or escaping path for {label}: {text}") from error
    if not path.is_file() or path.is_symlink():
        raise CheckFailure(f"{label} must name a regular non-symlink file: {text}")
    return path


def validate_manifest(path: Path) -> tuple[dict[str, Any], str]:
    manifest = require_keys(
        read_canonical_json(path),
        (
            "version",
            "statement",
            "art005",
            "high_source",
            "certificates",
            "checker_sources",
            "coverage",
            "coverage_sha256",
            "stages",
        ),
        "manifest",
    )
    if require_int(manifest["version"], "manifest.version") != EXPECTED_MANIFEST_VERSION:
        raise CheckFailure("unsupported all-N manifest version")

    statement = require_keys(manifest["statement"], ("path", "sha256"), "statement")
    if statement["path"] != "docs/problem-spec.md":
        raise CheckFailure("unexpected statement path in manifest")
    if statement["sha256"] != EXPECTED_STATEMENT_SHA256:
        raise CheckFailure("unexpected source-statement digest in manifest")
    statement_path = safe_repo_path(statement["path"], "statement.path")
    require_digest(statement_path, require_string(statement["sha256"], "statement.sha256"))

    art005 = require_keys(
        manifest["art005"],
        ("url", "revision", "tree", "release_manifest_sha256"),
        "art005",
    )
    if require_string(art005["url"], "art005.url") != EXPECTED_ART005_URL:
        raise CheckFailure("unexpected ART-005 URL in manifest")
    if art005["revision"] != EXPECTED_ART005_REVISION:
        raise CheckFailure("unexpected ART-005 revision in manifest")
    if art005["tree"] != EXPECTED_ART005_TREE:
        raise CheckFailure("unexpected ART-005 tree in manifest")
    if art005["release_manifest_sha256"] != EXPECTED_RELEASE_MANIFEST_SHA256:
        raise CheckFailure("unexpected ART-005 release-manifest digest")

    high = require_keys(
        manifest["high_source"],
        ("path", "sha256", "claims_sha256"),
        "high_source",
    )
    high_path = safe_repo_path(high["path"], "high_source.path")
    if high["sha256"] != EXPECTED_HIGH_SHA256:
        raise CheckFailure("unexpected high-range source digest in manifest")
    if high["claims_sha256"] != EXPECTED_HIGH_CLAIMS_SHA256:
        raise CheckFailure("unexpected high-range claims digest in manifest")
    if high["path"] != "sources/cache/sothanaphan-2.64e17.pdf":
        raise CheckFailure("unexpected high-range source path in manifest")
    require_digest(high_path, EXPECTED_HIGH_SHA256)

    for field, exact_entries in (
        ("certificates", EXPECTED_CERTIFICATES),
        ("checker_sources", EXPECTED_CHECKER_SOURCES),
    ):
        entries = manifest[field]
        if type(entries) is not list or not entries:
            raise CheckFailure(f"manifest.{field} must be a nonempty list")
        seen: set[str] = set()
        observed_entries: list[tuple[str, str]] = []
        for index, raw_entry in enumerate(entries):
            entry = require_keys(raw_entry, ("path", "sha256"), f"{field}[{index}]")
            relative = require_string(entry["path"], f"{field}[{index}].path")
            if relative in seen:
                raise CheckFailure(f"duplicate manifest path: {relative}")
            seen.add(relative)
            input_path = safe_repo_path(relative, f"{field}[{index}].path")
            digest = require_string(entry["sha256"], f"{field}[{index}].sha256")
            require_digest(input_path, digest)
            observed_entries.append((relative, digest))
        if tuple(observed_entries) != exact_entries:
            raise CheckFailure(f"manifest.{field} entries/order mismatch")

    coverage = manifest["coverage"]
    if type(coverage) is not list or len(coverage) != 5:
        raise CheckFailure("manifest.coverage must contain exactly five ranges")
    expected_ranges = (
        ("IP_FIN", 1, 100000006),
        ("IP_LOWER", 100000000, 1000000000),
        ("IP_LOW", 1000000000, 1000000000000),
        ("IP_MIDDLE", 1000000000000, 264000000000000000),
        ("H0", 264000000000000000, None),
    )
    observed_ranges: list[tuple[str, int, int | None]] = []
    for index, raw_entry in enumerate(coverage):
        entry = require_keys(raw_entry, ("id", "lower", "upper"), f"coverage[{index}]")
        identifier = require_string(entry["id"], f"coverage[{index}].id")
        lower = require_int(entry["lower"], f"coverage[{index}].lower")
        upper_raw = entry["upper"]
        upper = None if upper_raw is None else require_int(upper_raw, f"coverage[{index}].upper")
        observed_ranges.append((identifier, lower, upper))
    if tuple(observed_ranges) != expected_ranges:
        raise CheckFailure("all-N interval manifest is not the audited exact cover")
    if manifest["coverage_sha256"] != EXPECTED_COVERAGE_SHA256:
        raise CheckFailure("unexpected range-ledger digest")
    if type(manifest["stages"]) is not list or tuple(manifest["stages"]) != EXPECTED_STAGES:
        raise CheckFailure("manifest stage list/order mismatch")
    return manifest, sha256_file(path)


def require_digest(path: Path, expected: str) -> None:
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise CheckFailure(f"invalid expected SHA-256 for {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise CheckFailure(
            f"digest mismatch for {path}: expected {expected}, got {observed}"
        )


def capture(command: Sequence[str], *, cwd: Path, timeout: int = 60) -> str:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise CheckFailure(
            f"command failed ({result.returncode}): {shlex.join(command)}\n{result.stdout}"
        )
    return result.stdout.strip()


def authenticate_release_inventory(candidate: Path) -> None:
    manifest_path = candidate / "MANIFEST.sha256"
    expected: dict[PurePosixPath, str] = {}
    for line_number, raw_line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        try:
            digest, raw_path = raw_line.split("  ", 1)
        except ValueError as error:
            raise CheckFailure(
                f"malformed ART-005 manifest line {line_number}"
            ) from error
        relative = PurePosixPath(raw_path)
        if (
            len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or relative.is_absolute()
            or not relative.parts
            or "." in relative.parts
            or ".." in relative.parts
            or raw_path != relative.as_posix()
            or relative in expected
        ):
            raise CheckFailure(
                f"invalid ART-005 manifest entry on line {line_number}"
            )
        expected[relative] = digest
    if len(expected) != 131 or list(expected) != sorted(expected, key=str):
        raise CheckFailure("unexpected ART-005 manifest entry count or order")

    observed: set[PurePosixPath] = set()
    for path in candidate.rglob("*"):
        relative = path.relative_to(candidate)
        if ".git" in relative.parts:
            continue
        if path.is_file() or path.is_symlink():
            observed.add(PurePosixPath(relative.as_posix()))
    expected_inventory = set(expected) | {PurePosixPath("MANIFEST.sha256")}
    if observed != expected_inventory:
        missing = sorted(expected_inventory - observed, key=str)
        extra = sorted(observed - expected_inventory, key=str)
        raise CheckFailure(
            "ART-005 release inventory mismatch: "
            f"missing={[str(path) for path in missing]!r} "
            f"extra={[str(path) for path in extra]!r}"
        )
    for relative, digest in expected.items():
        path = candidate.joinpath(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise CheckFailure(f"unsafe ART-005 manifest path: {relative}")
        require_digest(path, digest)


def authenticate_candidate(candidate: Path) -> None:
    if not candidate.is_dir() or candidate.is_symlink():
        raise CheckFailure(f"ART-005 checkout is missing or unsafe: {candidate}")
    revision = capture(("git", "rev-parse", "HEAD"), cwd=candidate)
    tree = capture(("git", "rev-parse", "HEAD^{tree}"), cwd=candidate)
    dirty = capture(("git", "status", "--porcelain"), cwd=candidate)
    if revision != EXPECTED_ART005_REVISION:
        raise CheckFailure(f"ART-005 revision mismatch: {revision}")
    if tree != EXPECTED_ART005_TREE:
        raise CheckFailure(f"ART-005 tree mismatch: {tree}")
    if dirty:
        raise CheckFailure("ART-005 checkout is not clean")
    require_digest(candidate / "MANIFEST.sha256", EXPECTED_RELEASE_MANIFEST_SHA256)
    authenticate_release_inventory(candidate)


def tool_identity(command: Sequence[str]) -> str:
    return capture(command, cwd=ROOT, timeout=30).splitlines()[0]


def tool_fingerprint(cxx: str, javac: str, java: str) -> dict[str, str]:
    for executable in (cxx, javac, java):
        if shutil.which(executable) is None:
            raise CheckFailure(f"required executable not found: {executable}")
    try:
        import gmpy2
    except ImportError as error:
        raise CheckFailure("gmpy2==2.2.1 backed by GMP 6.3.0 is required") from error
    if gmpy2.version() != "2.2.1" or gmpy2.mp_version() != "GMP 6.3.0":
        raise CheckFailure(
            f"unexpected exact-integer backend: {gmpy2.version()} / {gmpy2.mp_version()}"
        )
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": str(Path(sys.executable).resolve()),
        "gmpy2": gmpy2.version(),
        "gmp": gmpy2.mp_version(),
        "cxx": tool_identity((cxx, "--version")),
        "javac": tool_identity((javac, "-version")),
        "java": tool_identity((java, "-version")),
        "platform": platform.platform(),
    }


def command_block(command: Sequence[str]) -> str:
    return f"COMMAND {shlex.join(command)}\n"


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Stop a command and all descendants after timeout or interruption."""

    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ("taskkill", "/PID", str(process.pid), "/T", "/F"),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired as error:
        raise CheckFailure(f"failed to terminate process tree {process.pid}") from error


def run_commands(
    commands: Sequence[Sequence[str]],
    *,
    cwd: Path,
    partial_log: Path,
    timeouts: Sequence[int],
    environment: dict[str, str] | None = None,
) -> str:
    if len(commands) != len(timeouts):
        raise CheckFailure("internal command/timeout mismatch")
    partial_log.parent.mkdir(parents=True, exist_ok=True)
    with partial_log.open("w", encoding="utf-8", newline="\n") as log:
        for command, timeout in zip(commands, timeouts):
            heading = command_block(command)
            print(heading, end="", flush=True)
            log.write(heading)
            log.flush()
            popen_options: dict[str, Any] = {}
            if sys.platform == "win32":
                popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_options["start_new_session"] = True
            process = subprocess.Popen(
                list(command),
                cwd=cwd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                env=environment,
                **popen_options,
            )
            assert process.stdout is not None
            reader_error: list[BaseException] = []

            def copy_output() -> None:
                try:
                    for line in process.stdout:
                        print(line, end="", flush=True)
                        log.write(line)
                        log.flush()
                except BaseException as error:
                    reader_error.append(error)

            reader = threading.Thread(target=copy_output, daemon=True)
            reader.start()
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired as error:
                terminate_process_tree(process)
                reader.join(timeout=10)
                raise CheckFailure(
                    f"command timed out after {timeout}s: {shlex.join(command)}"
                ) from error
            except BaseException:
                terminate_process_tree(process)
                reader.join(timeout=10)
                raise
            reader.join(timeout=30)
            if reader.is_alive():
                raise CheckFailure(f"output reader did not finish: {shlex.join(command)}")
            if reader_error:
                raise CheckFailure(
                    f"failed while capturing command output: {reader_error[0]}"
                )
            if returncode != 0:
                raise CheckFailure(
                    f"command failed ({returncode}): {shlex.join(command)}"
                )
        log.flush()
        os.fsync(log.fileno())
    return partial_log.read_text(encoding="utf-8")


def is_link_or_reparse(path: Path) -> bool:
    """Return true for POSIX links and Windows reparse-point entries."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & reparse_flag)


def require_owned_work_tree(work_dir: Path) -> None:
    """Reject links or escaping entries anywhere in an owned work tree."""

    if not work_dir.is_dir() or is_link_or_reparse(work_dir):
        raise CheckFailure("owned work directory is missing or unsafe")
    root = work_dir.resolve(strict=True)
    for current_raw, directories, files in os.walk(root, followlinks=False):
        current = Path(current_raw)
        for name in (*directories, *files):
            entry = current / name
            if is_link_or_reparse(entry):
                raise CheckFailure(f"owned work directory contains a link: {entry}")
            try:
                entry.resolve(strict=False).relative_to(root)
            except ValueError as error:
                raise CheckFailure(
                    f"owned work-directory entry escapes its root: {entry}"
                ) from error


def require_owned_target(path: Path, work_dir: Path) -> None:
    """Require a lexical and resolved target below a symlink-free work root."""

    require_owned_work_tree(work_dir)
    root = work_dir.resolve(strict=True)
    try:
        relative = path.relative_to(work_dir)
    except ValueError as error:
        raise CheckFailure(
            f"output path is outside the owned work directory: {path}"
        ) from error
    if not relative.parts:
        raise CheckFailure("output path must not be the work-directory root")
    parent = root
    for part in relative.parts[:-1]:
        parent /= part
        if parent.exists():
            if not parent.is_dir() or is_link_or_reparse(parent):
                raise CheckFailure(f"unsafe output parent in work directory: {parent}")
        else:
            parent.mkdir()
    try:
        path.parent.resolve(strict=True).relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise CheckFailure(
            f"output parent escapes the owned work directory: {path}"
        ) from error
    if is_link_or_reparse(path):
        raise CheckFailure(f"output target must not be a link: {path}")


def atomic_write(path: Path, payload: bytes, *, work_dir: Path) -> None:
    require_owned_target(path, work_dir)
    if path.exists():
        raise CheckFailure(f"refusing to overwrite an existing owned output: {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    require_owned_target(temporary, work_dir)
    try:
        stream = temporary.open("xb")
    except FileExistsError as error:
        raise CheckFailure(f"refusing unsafe or stale temporary output: {temporary}") from error
    with stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    require_owned_target(temporary, work_dir)
    temporary.replace(path)
    require_owned_work_tree(work_dir)


def initialize_work_dir(
    requested: Path, *, manifest_sha256: str, orchestrator_sha256: str
) -> Path:
    absolute = requested if requested.is_absolute() else Path.cwd() / requested
    if absolute.exists() and is_link_or_reparse(absolute):
        raise CheckFailure("--work-dir itself must not be a link or reparse point")
    work_dir = absolute.resolve(strict=False)
    root = ROOT.resolve(strict=True)
    if (
        work_dir == Path(work_dir.anchor)
        or work_dir == root
        or root in work_dir.parents
        or work_dir in root.parents
    ):
        raise CheckFailure(
            "--work-dir must not be the filesystem root, repository, "
            "or an ancestor/descendant of the repository"
        )
    if work_dir.exists() and not work_dir.is_dir():
        raise CheckFailure("--work-dir must be a directory")
    work_dir.mkdir(parents=True, exist_ok=True)
    sentinel = work_dir / WORK_SENTINEL
    expected = {
        "version": 1,
        "manifest_sha256": manifest_sha256,
        "orchestrator_sha256": orchestrator_sha256,
    }
    entries = list(work_dir.iterdir())
    if not entries:
        atomic_write(sentinel, canonical_json(expected), work_dir=work_dir)
    elif not sentinel.is_file() or is_link_or_reparse(sentinel):
        raise CheckFailure(
            "nonempty --work-dir is not owned by this checker; use a fresh path"
        )
    elif sentinel.read_bytes() != canonical_json(expected):
        raise CheckFailure("work-directory ownership sentinel is stale or corrupt")
    require_owned_work_tree(work_dir)
    return work_dir


def require_expected_work_layout(work_dir: Path) -> None:
    """Reject caller-injected names outside the checker's fixed work schema."""

    require_owned_work_tree(work_dir)
    allowed_root = {
        WORK_SENTINEL,
        "stages",
        "generated-prefix-10000.json",
        "generated-p13-factor-primality.json",
        "all-n-computational-receipt.json",
        "all-n-resume-receipt.json",
    }
    for entry in work_dir.iterdir():
        if entry.name not in allowed_root:
            raise CheckFailure(f"unexpected entry in owned work directory: {entry.name}")
    stage_dir = work_dir / "stages"
    if not stage_dir.exists():
        return
    if not stage_dir.is_dir() or is_link_or_reparse(stage_dir):
        raise CheckFailure("work-directory stages entry is unsafe")
    allowed_stage_names = {
        f"{stage}{suffix}"
        for stage in EXPECTED_STAGES
        for suffix in (".log", ".partial.log", ".json")
    }
    for entry in stage_dir.iterdir():
        if entry.name not in allowed_stage_names:
            raise CheckFailure(f"unexpected entry in stages directory: {entry.name}")


def stage_fingerprint(
    *,
    stage: str,
    manifest_sha256: str,
    commands: Sequence[Sequence[str]],
    tools: dict[str, str],
    dependency_receipts: Sequence[str],
) -> str:
    value = {
        "stage": stage,
        "manifest_sha256": manifest_sha256,
        "commands": [list(command) for command in commands],
        "tools": tools,
        "dependency_receipts": list(dependency_receipts),
    }
    return hashlib.sha256(canonical_json(value)).hexdigest()


def validate_markers(log_text: str, markers: Sequence[str], stage: str) -> None:
    missing = [marker for marker in markers if marker not in log_text]
    if missing:
        raise CheckFailure(f"{stage} log is missing decisive markers: {missing}")


def expected_stage_receipt(
    *,
    stage: str,
    fingerprint: str,
    dependencies: Sequence[str],
    commands: Sequence[Sequence[str]],
    manifest_sha256: str,
    tools: dict[str, str],
    log_sha256: str,
    outputs: dict[str, str],
) -> dict[str, Any]:
    return {
        "version": 1,
        "stage": stage,
        "status": "passed",
        "fingerprint": fingerprint,
        "manifest_sha256": manifest_sha256,
        "tools": tools,
        "dependency_receipts": list(dependencies),
        "commands": [list(command) for command in commands],
        "log_sha256": log_sha256,
        "outputs": outputs,
    }


def completion_receipt_status(*, resumed: bool) -> str:
    """Keep operational resume receipts distinct from theorem-grade receipts."""

    if resumed:
        return "resumed-checkpoint-chain-validated"
    return "all-n-computational-certificate-passed"


def run_stage(
    *,
    stage: str,
    commands: Sequence[Sequence[str]],
    cwd: Path,
    work_dir: Path,
    timeouts: Sequence[int],
    markers: Sequence[str],
    expected_outputs: dict[Path, str],
    manifest_sha256: str,
    tools: dict[str, str],
    dependency_receipts: Sequence[str],
    resume: bool,
    precheck: Callable[[], None] | None = None,
    postcheck: Callable[[], None] | None = None,
    environment: dict[str, str] | None = None,
) -> str:
    require_owned_work_tree(work_dir)
    if precheck is not None:
        precheck()
    stage_dir = work_dir / "stages"
    require_owned_target(stage_dir / ".path-check", work_dir)
    log_path = stage_dir / f"{stage}.log"
    partial_log = stage_dir / f"{stage}.partial.log"
    receipt_path = stage_dir / f"{stage}.json"
    fingerprint = stage_fingerprint(
        stage=stage,
        manifest_sha256=manifest_sha256,
        commands=commands,
        tools=tools,
        dependency_receipts=dependency_receipts,
    )

    def observed_outputs() -> dict[str, str]:
        result: dict[str, str] = {}
        for output, expected in expected_outputs.items():
            require_owned_target(output, work_dir)
            if not output.is_file() or is_link_or_reparse(output):
                raise CheckFailure(f"{stage} output is missing or unsafe: {output}")
            require_digest(output, expected)
            result[str(output.relative_to(work_dir))] = expected
        return result

    if resume and receipt_path.is_file():
        require_owned_work_tree(work_dir)
        log_text = log_path.read_text(encoding="utf-8")
        validate_markers(log_text, markers, stage)
        outputs = observed_outputs()
        if postcheck is not None:
            postcheck()
        require_owned_work_tree(work_dir)
        expected = expected_stage_receipt(
            stage=stage,
            fingerprint=fingerprint,
            dependencies=dependency_receipts,
            commands=commands,
            manifest_sha256=manifest_sha256,
            tools=tools,
            log_sha256=sha256_file(log_path),
            outputs=outputs,
        )
        if receipt_path.read_bytes() != canonical_json(expected):
            raise CheckFailure(f"stale or corrupt checkpoint for {stage}")
        digest = sha256_file(receipt_path)
        print(f"RESUME verified stage={stage} receipt_sha256={digest}")
        return digest

    if receipt_path.exists() or log_path.exists():
        raise CheckFailure(
            f"existing {stage} state requires --resume or a fresh --work-dir"
        )
    if partial_log.exists() or is_link_or_reparse(partial_log):
        raise CheckFailure(f"unsafe or stale partial stage log: {partial_log}")
    for output in expected_outputs:
        require_owned_target(output, work_dir)
        if output.exists():
            raise CheckFailure(f"fresh stage output already exists: {output}")
    log_text = run_commands(
        commands,
        cwd=cwd,
        partial_log=partial_log,
        timeouts=timeouts,
        environment=environment,
    )
    validate_markers(log_text, markers, stage)
    require_owned_target(partial_log, work_dir)
    if log_path.exists() or is_link_or_reparse(log_path):
        raise CheckFailure(f"refusing to replace unsafe stage log: {log_path}")
    partial_log.replace(log_path)
    require_owned_work_tree(work_dir)
    outputs = observed_outputs()
    if postcheck is not None:
        postcheck()
    receipt = expected_stage_receipt(
        stage=stage,
        fingerprint=fingerprint,
        dependencies=dependency_receipts,
        commands=commands,
        manifest_sha256=manifest_sha256,
        tools=tools,
        log_sha256=sha256_file(log_path),
        outputs=outputs,
    )
    atomic_write(receipt_path, canonical_json(receipt), work_dir=work_dir)
    digest = sha256_file(receipt_path)
    print(f"PASS stage={stage} receipt_sha256={digest}")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="persistent, caller-owned directory for logs and verified checkpoints",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--stop-after",
        choices=EXPECTED_STAGES[:-1],
        help="stop after a verified intermediate stage without emitting final PASS",
    )
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    parser.add_argument("--javac", default="javac")
    parser.add_argument("--java", default="java")
    args = parser.parse_args()

    if sys.flags.optimize:
        raise CheckFailure("optimized Python is forbidden for theorem-grade replay")
    if args.jobs < 1:
        raise CheckFailure("--jobs must be positive")
    manifest_path = args.manifest.resolve(strict=True)
    manifest, manifest_sha256 = validate_manifest(manifest_path)
    candidate = args.candidate_root.resolve(strict=True)
    authenticate_candidate(candidate)
    tools = tool_fingerprint(args.cxx, args.javac, args.java)
    tools["orchestrator_sha256"] = sha256_file(Path(__file__).resolve())
    child_environment = dict(os.environ)
    child_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    tools["child_python_dont_write_bytecode"] = "1"
    root_top = Path(capture(("git", "rev-parse", "--show-toplevel"), cwd=ROOT))
    if root_top.resolve(strict=True) != ROOT.resolve(strict=True):
        raise CheckFailure("checker is not running from the expected Git repository")
    root_identity = {
        "head": capture(("git", "rev-parse", "HEAD"), cwd=ROOT),
        "tree": capture(("git", "rev-parse", "HEAD^{tree}"), cwd=ROOT),
    }
    tools["root_head"] = root_identity["head"]
    tools["root_tree"] = root_identity["tree"]
    print(f"manifest_sha256={manifest_sha256}")
    print(f"art005_revision={EXPECTED_ART005_REVISION}")
    print(f"art005_tree={EXPECTED_ART005_TREE}")
    print(f"python={tools['python']} gmpy2={tools['gmpy2']} gmp={tools['gmp']}")

    work_dir = initialize_work_dir(
        args.work_dir,
        manifest_sha256=manifest_sha256,
        orchestrator_sha256=tools["orchestrator_sha256"],
    )
    require_expected_work_layout(work_dir)
    if args.preflight_only:
        print("PREFLIGHT ONLY: inputs authenticated; no computational theorem certified")
        return 0

    def reauthenticate_inputs() -> None:
        require_expected_work_layout(work_dir)
        _, observed_manifest = validate_manifest(manifest_path)
        if observed_manifest != manifest_sha256:
            raise CheckFailure("root manifest changed during replay")
        if sha256_file(Path(__file__).resolve()) != tools["orchestrator_sha256"]:
            raise CheckFailure("primary orchestrator changed during replay")
        observed_root = {
            "head": capture(("git", "rev-parse", "HEAD"), cwd=ROOT),
            "tree": capture(("git", "rev-parse", "HEAD^{tree}"), cwd=ROOT),
        }
        dirty = capture(
            ("git", "status", "--porcelain", "--untracked-files=all"), cwd=ROOT
        )
        if observed_root != root_identity or dirty:
            raise CheckFailure("root repository changed or is dirty during replay")
        authenticate_candidate(candidate)

    reauthenticate_inputs()

    python = sys.executable
    high_source = ROOT / manifest["high_source"]["path"]
    generated_prefix = work_dir / "generated-prefix-10000.json"
    generated_p13 = work_dir / "generated-p13-factor-primality.json"
    p13_transcript = candidate / "audit" / "p13_interval_factors_1000000000.tsv.gz"
    dependencies: list[str] = []

    stage_specs: list[dict[str, Any]] = [
        {
            "stage": "prefix",
            "cwd": ROOT,
            "commands": (
                (
                    python,
                    "-B",
                    str(ROOT / "computations" / "generate_prefix_certificate.py"),
                    "--limit",
                    "10000",
                    "--output",
                    str(generated_prefix),
                ),
                (
                    python,
                    "-B",
                    str(ROOT / "computations" / "check_prefix_certificate.py"),
                    str(generated_prefix),
                    "--expected-sha256",
                    EXPECTED_PREFIX_SHA256,
                ),
                (
                    python,
                    "-B",
                    str(ROOT / "computations" / "test_prefix_checker.py"),
                    str(generated_prefix),
                ),
                (
                    python,
                    "-B",
                    str(ROOT / "computations" / "exhaustive_small_prefix.py"),
                    "--limit",
                    "100",
                ),
                (
                    python,
                    "-B",
                    str(ROOT / "computations" / "test_all_n_manifest.py"),
                ),
                (
                    python,
                    "-B",
                    str(ROOT / "computations" / "test_all_n_resume.py"),
                ),
            ),
            "timeouts": (300, 300, 600, 600, 60, 60),
            "markers": (
                f"sha256={EXPECTED_PREFIX_SHA256}",
                "VERIFIED exact prefix certificate",
                "statement_controls=passed",
                "ALL PREFIX CHECKER MUTATION CONTROLS PASSED",
                "VERIFIED exhaustive subsets for every 1 <= N <= 100",
                "ALL ALL-N MANIFEST MUTATION CONTROLS PASSED",
                "ALL ALL-N RESUME MUTATION CONTROLS PASSED",
            ),
            "outputs": {generated_prefix: EXPECTED_PREFIX_SHA256},
            "postcheck": lambda: require_digest(
                ROOT / "certificates" / "prefix-10000.json", EXPECTED_PREFIX_SHA256
            ),
        },
        {
            "stage": "p13-primality",
            "cwd": ROOT,
            "commands": (
                (
                    python,
                    "-B",
                    str(ROOT / "computations" / "check_p13_factor_primality.py"),
                    str(p13_transcript),
                    "--certificate-output",
                    str(generated_p13),
                ),
            ),
            "timeouts": (1800,),
            "markers": (
                "batch primality negative controls: PASS",
                "gcd=1",
                f"canonical_certificate_sha256={EXPECTED_P13_SHA256}",
                "INDEPENDENT P13 FACTOR PRIMALITY AUDIT PASSED",
            ),
            "outputs": {generated_p13: EXPECTED_P13_SHA256},
            "postcheck": lambda: require_digest(
                ROOT / "certificates" / "p13-factor-primality.json", EXPECTED_P13_SHA256
            ),
        },
        {
            "stage": "finite-independent",
            "cwd": ROOT,
            "commands": (
                (
                    python,
                    "-B",
                    str(ROOT / "scripts" / "independent_check.py"),
                    "--candidate-root",
                    str(candidate),
                    "--cxx",
                    args.cxx,
                    "--javac",
                    args.javac,
                    "--java",
                    args.java,
                ),
            ),
            "timeouts": (2400,),
            "markers": (
                "INDEPENDENT FINITE STREAM AUDIT PASSED",
                "large_primorial_gcd=1",
                "injected_factor_control_gcd=2",
                "INDEPENDENT AUDIT FAILED: endpoint pair is nonsquarefree",
                "INDEPENDENT THEOREM-GRADE FINITE PIPELINE PASSED",
            ),
            "outputs": {},
            "postcheck": None,
        },
        {
            "stage": "high-numerics",
            "cwd": candidate,
            "commands": (
                (
                    python,
                    "-B",
                    str(candidate / "audit" / "verify_high_threshold_numerics_v1.py"),
                    "--source-pdf",
                    str(high_source),
                    "--self-test",
                ),
            ),
            "timeouts": (900,),
            "markers": (
                f'"canonical_claims_sha256": "{EXPECTED_HIGH_CLAIMS_SHA256}"',
                '"reduced_prime_cutoff_rejected": "passed"',
                '"source_hash_control": "passed"',
            ),
            "outputs": {},
            "postcheck": None,
        },
        {
            "stage": "art005-release",
            "cwd": candidate,
            "commands": (
                (
                    python,
                    "-u",
                    str(candidate / "audit" / "run_release_replay.py"),
                    "--source-pdf",
                    str(high_source),
                    "--cxx",
                    args.cxx,
                    "--jobs",
                    str(args.jobs),
                ),
            ),
            "timeouts": (10800,),
            "markers": (
                "PASS complete_all_n_local_replay profile=full stages=19",
                f"source_pdf_sha256={EXPECTED_HIGH_SHA256}",
                f"PASS release_manifest_postflight files=131 inventory=132 manifest_sha256={EXPECTED_RELEASE_MANIFEST_SHA256}",
                f"PASS complete_fresh_extraction_release_replay files=131 manifest_sha256={EXPECTED_RELEASE_MANIFEST_SHA256}",
            ),
            "outputs": {},
            "postcheck": lambda: authenticate_candidate(candidate),
        },
        {
            "stage": "coverage",
            "cwd": candidate,
            "commands": (
                (
                    python,
                    "-B",
                    str(candidate / "audit" / "verify_all_n_coverage.py"),
                ),
            ),
            "timeouts": (300,),
            "markers": (
                f"coverage_manifest_sha256={EXPECTED_COVERAGE_SHA256}",
                "PASS status_json_matches_coverage",
                "PASS all_n_branch_coverage_is_gapless",
            ),
            "outputs": {},
            "postcheck": None,
        },
    ]

    for spec in stage_specs:
        stage_postcheck = spec["postcheck"]

        def combined_postcheck(
            stage_postcheck: Callable[[], None] | None = stage_postcheck,
        ) -> None:
            if stage_postcheck is not None:
                stage_postcheck()
            reauthenticate_inputs()

        receipt = run_stage(
            stage=spec["stage"],
            commands=spec["commands"],
            cwd=spec["cwd"],
            work_dir=work_dir,
            timeouts=spec["timeouts"],
            markers=spec["markers"],
            expected_outputs=spec["outputs"],
            manifest_sha256=manifest_sha256,
            tools=tools,
            dependency_receipts=tuple(dependencies),
            resume=args.resume,
            precheck=reauthenticate_inputs,
            postcheck=combined_postcheck,
            environment=child_environment,
        )
        dependencies.append(receipt)
        if args.stop_after == spec["stage"]:
            print(
                f"PARTIAL REPLAY STOPPED after {spec['stage']}: "
                "no all-N computational certificate emitted"
            )
            return 0

    reauthenticate_inputs()
    resumed = bool(args.resume)
    final_receipt = {
        "version": 1,
        "status": completion_receipt_status(resumed=resumed),
        "execution_provenance": "local-unattested",
        "manifest_sha256": manifest_sha256,
        "orchestrator_sha256": tools["orchestrator_sha256"],
        "tools": tools,
        "art005_revision": EXPECTED_ART005_REVISION,
        "art005_tree": EXPECTED_ART005_TREE,
        "root_repository": root_identity,
        "stage_receipts": dependencies,
        "coverage_sha256": EXPECTED_COVERAGE_SHA256,
    }
    final_path = work_dir / (
        "all-n-resume-receipt.json" if resumed else "all-n-computational-receipt.json"
    )
    atomic_write(final_path, canonical_json(final_receipt), work_dir=work_dir)
    print(f"final_receipt={final_path}")
    print(f"final_receipt_sha256={sha256_file(final_path)}")
    if resumed:
        print(
            "RESUMED CHECKPOINT CHAIN VALIDATED: operational recovery only; "
            "no theorem-grade certificate PASS"
        )
    else:
        print("ALL-N COMPUTATIONAL CERTIFICATE PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        CheckFailure,
        OSError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        print(f"ALL-N COMPUTATIONAL CERTIFICATE FAILED: {error}", file=sys.stderr)
        raise SystemExit(1) from error
