#!/usr/bin/env python3
'''Guarded clean ART-006 build and final Lean completion audit.

The full command is Windows x86-64 only because the pinned upstream kernel
gate supports its direct-Lean path only there. ``--source-audit-only`` checks
the lock and source census, but never emits a completion receipt or PASS.
'''

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import signal
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


LEAN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = LEAN_ROOT.parent
LOCK_PATH = LEAN_ROOT / 'source-lock.json'
FINAL_SOURCE = LEAN_ROOT / 'Erdos848Completion' / 'Final.lean'
AUDIT_SOURCE = LEAN_ROOT / 'Erdos848Completion' / 'PublicationAxiomAudit.lean'
TEST_SOURCE = LEAN_ROOT / 'test_completion_gate.py'
DEFAULT_UPSTREAM = REPO_ROOT / 'external' / 'erdos-848-squarefree-product'

REVISION = 'ede0151a35c86b6395cf67dd034811d22a92c7ba'
TREE = '5b1253061e916513036d30d8275c9aeaddb0e771'
LEAN_TREE = '6b9794fafddd3e7780c6a10a442f2e4e9dc73c1a'
TOOLCHAIN = 'leanprover/lean4:v4.30.0-rc2'
LEAN_COMMIT = '3dc1a088b6d2d8eafe25a7cd7ec7b58d731bd7cc'
RUNTIME_ARCHIVE_SHA256 = (
    'cb0688631203ac7832e447a5791e51e88db938b6038ff788eea73491619988b2'
)
LEAN_EXECUTABLE_SHA256 = (
    '5bead9b39d9a23306507fb59277995b94e71787d86d76a9ed3fb248b1ed3f995'
)
LAKE_EXECUTABLE_SHA256 = (
    '9befc94126195bc2057109e2cfc1207962739ba1b5fc03b8b955be4e27210eed'
)
MATHLIB = '54e71fa9173471d591658f5380c46aaf050bbaae'
SOURCE_COUNT = 30638
SOURCE_BYTES = 2346175840
PROVIDER_MODULES = 30636
PROVIDER_MODULE_LIST_SHA256 = (
    '6cecc38e110c19024e2a397bd97fa06e31c12087366379e86e6c4e453df77643'
)
PUBLICATION_MODULE_LIST_SHA256 = (
    '51a073fd5cfe5eba801a1aa9cfa37a7917c14493283af13de41a46a21c420d67'
)
FINAL_SOURCE_SHA256 = (
    '74e36a06786ecda5b2bd5e3892b2513db7f19bb08084cc151319a67954f7edd6'
)
AUDIT_SOURCE_SHA256 = (
    'fdbad8d9dc8f084b8fa3acb86a3ef395d792f5622c5b5dfe070bdab4398d42c6'
)
TEST_SOURCE_SHA256 = (
    '21de8459302a5590d5a8b530a05a9ba3bf62d178154750795145f7344b4c5ede'
)
ALLOWED_AXIOMS = ('propext', 'Classical.choice', 'Quot.sound')
ENDPOINTS = (
    'Erdos848.NonSquarefreeProductProp',
    'Erdos848.OriginalProblem848Statement',
    'Erdos848.originalA7_has_property',
    'Erdos848.originalProblem_of_hallStatement',
    'Erdos848.erdos848HallStatement_iff_originalProblem',
    'Erdos848.erdos848_through_five_million',
    'Erdos848.PaperCertificateProvider.fiveToTenMillion',
    'Erdos848.PaperCertificateProvider.tenToTwentyMillion',
    'Erdos848.PaperCertificateProvider.twentyToFortyMillion',
    'Erdos848.erdos848FortyMillionClose_kernel',
    'Erdos848.PaperCertificateProvider.twoHundredToTwoBillion',
    'Erdos848.PaperCertificateProvider.twoBillionTail',
    'Erdos848.PaperCertificateProvider.fortyMillionTail',
    'Erdos848.erdos848_paper_tail_close',
    'Erdos848.PaperGeneratedCertificateProvider.all_N',
    'Erdos848Completion.erdos848_all_positive',
    'Erdos848Completion.residue_seven_witness',
    'Erdos848Completion.residue_eighteen_witness',
    'Erdos848Completion.residue_class_cardinalities',
)
FILE_HASHES = {
    'lean4/lean-toolchain':
        'ce4c4e3d87434b9663f46de25ce34b48a0cf0d392e0a320a0787b4674a2d7b61',
    'lean4/lake-manifest.json':
        'e016cb20d7f2f3b2bef02393f4b468fdd4f8fdeba9784aabb39e2889a87b5d4c',
    'lean4/lakefile.toml':
        '7479e2c461de9c48bcf32fc210ee2ce56d6d1a485c0a0d49d17f934082074912',
    'lean4/Erdos848/ProblemCore.lean':
        '3cc1f264149eaf99e18a04c8f57e4c6850c8571d0cb5b1de0fefdec087d5cfec',
    'lean4/Erdos848/PaperGeneratedCertificateProvider.lean':
        '74de90d4d6e3d2d0594740c24072b9fab8fcb25c693360229d74ec7b0e8f582b',
    'lean4/Erdos848/PublicationAxiomAudit.lean':
        'b0c280ff98b1ea5e5e91a0fc629e6f149dd2c28fbdc2be9ebac78f45c9cb8030',
}
FILE_ATTRIBUTE_REPARSE_POINT = getattr(
    stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400
)


class GateFailure(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('ascii')


def read_lock() -> dict[str, Any]:
    raw = LOCK_PATH.read_bytes()
    try:
        lock = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateFailure(f'invalid source lock: {error}') from error
    if type(lock) is not dict or raw != canonical_json(lock):
        raise GateFailure('source lock must be a canonical JSON object')
    root_sources = lock.get('root_sources')
    if type(root_sources) is not dict:
        raise GateFailure('source lock is missing root source identities')
    runner_digest = root_sources.get('runner_sha256')
    if (
        type(runner_digest) is not str
        or re.fullmatch(r'[0-9a-f]{64}', runner_digest) is None
    ):
        raise GateFailure('invalid runner digest in source lock')
    expected = {
        'version': 1,
        'status': 'unverified-pending-clean-replay',
        'upstream': {
            'url': 'https://github.com/crabsatellite/erdos-848-squarefree-product.git',
            'revision': REVISION,
            'tree': TREE,
            'lean_tree': LEAN_TREE,
        },
        'toolchain': {
            'lean': TOOLCHAIN,
            'lean_commit': LEAN_COMMIT,
            'runtime_archive_sha256': RUNTIME_ARCHIVE_SHA256,
            'lean_executable_sha256': LEAN_EXECUTABLE_SHA256,
            'lake_executable_sha256': LAKE_EXECUTABLE_SHA256,
            'lean_toolchain_sha256': FILE_HASHES['lean4/lean-toolchain'],
            'lake_manifest_sha256': FILE_HASHES['lean4/lake-manifest.json'],
            'lakefile_sha256': FILE_HASHES['lean4/lakefile.toml'],
            'mathlib_revision': MATHLIB,
        },
        'sources': {
            'problem_core_sha256': FILE_HASHES[
                'lean4/Erdos848/ProblemCore.lean'
            ],
            'provider_sha256': FILE_HASHES[
                'lean4/Erdos848/PaperGeneratedCertificateProvider.lean'
            ],
            'upstream_axiom_audit_sha256': FILE_HASHES[
                'lean4/Erdos848/PublicationAxiomAudit.lean'
            ],
        },
        'endpoint': {
            'declaration': 'Erdos848.PaperGeneratedCertificateProvider.all_N',
            'type': 'forall N, Erdos848.OriginalProblem848Statement N',
            'provider_modules': PROVIDER_MODULES,
            'publication_modules': SOURCE_COUNT,
            'publication_source_bytes': SOURCE_BYTES,
            'provider_module_list_sha256': PROVIDER_MODULE_LIST_SHA256,
            'publication_module_list_sha256': PUBLICATION_MODULE_LIST_SHA256,
            'upstream_axiom_endpoints': 15,
        },
        'root_sources': {
            'final_sha256': FINAL_SOURCE_SHA256,
            'axiom_audit_sha256': AUDIT_SOURCE_SHA256,
            'test_sha256': TEST_SOURCE_SHA256,
            'runner_sha256': runner_digest,
        },
        'allowed_axioms': list(ALLOWED_AXIOMS),
        'minimum_host': {
            'platform': 'windows-x86_64',
            'physical_memory_gib': 64,
            'free_storage_gib': 200,
            'build_memory_mib': 32768,
            'guard_reserve_mib': 1024,
        },
    }
    if raw != canonical_json(expected):
        raise GateFailure('source-lock schema, order, or value mismatch')
    require_hash(FINAL_SOURCE, FINAL_SOURCE_SHA256)
    require_hash(AUDIT_SOURCE, AUDIT_SOURCE_SHA256)
    require_hash(TEST_SOURCE, TEST_SOURCE_SHA256)
    require_hash(Path(__file__).resolve(), runner_digest)
    return lock


def capture(
    command: Sequence[str], cwd: Path, timeout: int = 60,
    env: dict[str, str] | None = None,
) -> str:
    result = subprocess.run(
        list(command), cwd=cwd, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        raise GateFailure(
            f'command failed ({result.returncode}): {shlex.join(command)}\n'
            f'{result.stdout}'
        )
    return result.stdout.strip()


def sanitized_lean_environment(
    base: dict[str, str] | None = None,
) -> dict[str, str]:
    """Remove caller-controlled Lean module paths before invoking Lake/Lean."""

    result = dict(os.environ if base is None else base)
    for name in ('LEAN_PATH', 'LEAN_SRC_PATH', 'LEAN_PKG_PATH'):
        result.pop(name, None)
    return result


def path_has_reparse_attribute(path: Path) -> bool:
    attributes = getattr(os.lstat(path), 'st_file_attributes', 0)
    return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)


def require_no_reparse_ancestors(path: Path) -> None:
    current = path
    while True:
        if current.exists() and (
            current.is_symlink() or path_has_reparse_attribute(current)
        ):
            raise GateFailure(f'runtime path contains a reparse point: {current}')
        parent = current.parent
        if parent == current:
            return
        current = parent


def resolved_runtime_executables(
    runtime_bin: Path, base_env: dict[str, str],
) -> tuple[Path, Path, Path]:
    """Bind sanitized PATH to the explicit authenticated runtime bin."""

    if not runtime_bin.is_absolute():
        raise GateFailure('--runtime-bin must be an absolute path')
    if runtime_bin.exists() and runtime_bin.is_symlink():
        raise GateFailure('--runtime-bin itself must not be a symlink')
    require_no_reparse_ancestors(runtime_bin)
    try:
        exact_bin = runtime_bin.resolve(strict=True)
    except OSError as error:
        raise GateFailure(f'--runtime-bin is unavailable: {runtime_bin}: {error}') from error
    if runtime_bin != exact_bin:
        raise GateFailure(
            f'--runtime-bin must be an exact canonical path: {runtime_bin} != {exact_bin}'
        )
    if (
        not exact_bin.is_dir()
        or exact_bin.is_symlink()
        or path_has_reparse_attribute(exact_bin)
        or exact_bin.name.lower() != 'bin'
    ):
        raise GateFailure(f'--runtime-bin is not a safe bin directory: {exact_bin}')
    require_no_reparse_ancestors(exact_bin)

    path_value = base_env.get('PATH')
    if type(path_value) is not str or not path_value:
        raise GateFailure('effective PATH is empty while resolving Lean/Lake')
    if sys.platform == 'win32':
        lean_name, lake_name = 'lean.exe', 'lake.exe'
    else:
        lean_name, lake_name = 'lean', 'lake'

    def resolve(name: str, label: str) -> Path:
        raw = shutil.which(name, path=path_value)
        if raw is None:
            raise GateFailure(f'{label} is missing from the effective PATH')
        try:
            executable = Path(raw).resolve(strict=True)
        except OSError as error:
            raise GateFailure(
                f'effective PATH resolved an unavailable {label}: {raw}: {error}'
            ) from error
        if not executable.is_file() or executable.is_symlink():
            raise GateFailure(
                f'effective PATH resolved an unsafe {label}: {executable}'
            )
        return executable

    lean = resolve(lean_name, 'Lean executable')
    lake = resolve(lake_name, 'Lake executable')
    lean_path = exact_bin / lean_name
    lake_path = exact_bin / lake_name
    if lean_path.is_symlink() or lake_path.is_symlink():
        raise GateFailure('explicit runtime contains a symlinked Lean or Lake')
    try:
        expected_lean = lean_path.resolve(strict=True)
        expected_lake = lake_path.resolve(strict=True)
    except OSError as error:
        raise GateFailure(
            f'explicit runtime bin omits Lean or Lake: {exact_bin}: {error}'
        ) from error
    if lean != expected_lean or lake != expected_lake:
        raise GateFailure(
            'effective PATH does not resolve the explicit runtime pair: '
            f'Lean={lean} Lake={lake} runtime_bin={exact_bin}'
        )
    for executable, expected_hash, label in (
        (lean, LEAN_EXECUTABLE_SHA256, 'Lean executable'),
        (lake, LAKE_EXECUTABLE_SHA256, 'Lake executable'),
    ):
        if executable.parent != exact_bin or path_has_reparse_attribute(executable):
            raise GateFailure(f'{label} is outside or unsafe under runtime bin')
        observed = sha256_file(executable)
        if observed != expected_hash:
            raise GateFailure(
                f'{label} digest mismatch: {observed} != {expected_hash}'
            )
    return exact_bin, lean, lake


def capture_lake_environment(
    lake_executable: Path, lean4: Path, base_env: dict[str, str],
    script: str, phase: str,
) -> str:
    """Run one Lake environment query through the already resolved executable."""

    try:
        lake = lake_executable.resolve(strict=True)
    except OSError as error:
        raise GateFailure(
            f'{phase}: Lake executable is unavailable: {lake_executable}: {error}'
        ) from error
    expected_name = 'lake.exe' if sys.platform == 'win32' else 'lake'
    if (
        not lake.is_file()
        or lake.is_symlink()
        or lake.name.lower() != expected_name
    ):
        raise GateFailure(f'{phase}: unsafe Lake executable: {lake}')
    try:
        return capture(
            (str(lake), 'env', sys.executable, '-c', script),
            lean4, env=base_env,
        )
    except OSError as error:
        raise GateFailure(
            f'{phase}: absolute Lake command could not start: {lake}: {error}'
        ) from error
    except GateFailure as error:
        raise GateFailure(f'{phase}: {error}') from error


def resolved_lean_executable(
    lean4: Path, base_env: dict[str, str], lake_executable: Path,
) -> Path:
    """Resolve Lake's Lean executable without trusting a caller module path."""

    which_script = (
        "import shutil; value = shutil.which('lean'); "
        "print(value if value is not None else '')"
    )
    executable_raw = capture_lake_environment(
        lake_executable, lean4, base_env, which_script,
        'resolve-Lake-Lean-executable',
    )
    try:
        executable = Path(executable_raw).resolve(strict=True)
    except OSError as error:
        raise GateFailure(
            'Lake returned an unavailable Lean executable: '
            f'{executable_raw!r}: {error}'
        ) from error
    if not executable.is_file() or executable.is_symlink():
        raise GateFailure(f'Lake resolved an unsafe Lean executable: {executable}')
    return executable


def resolved_lean_environment(
    lean4: Path, base_env: dict[str, str], lake_executable: Path,
) -> tuple[Path, tuple[Path, ...]]:
    """Resolve the Lean executable and Lake-computed module path exactly once."""

    executable = resolved_lean_executable(lean4, base_env, lake_executable)
    path_script = "import os; print(os.environ.get('LEAN_PATH', ''))"
    raw_path = capture_lake_environment(
        lake_executable, lean4, base_env, path_script,
        'resolve-Lake-module-path',
    )
    if not raw_path:
        raise GateFailure('Lake produced an empty LEAN_PATH')
    entries: list[Path] = []
    for raw_entry in raw_path.split(os.pathsep):
        if not raw_entry:
            raise GateFailure('Lake produced an empty LEAN_PATH entry')
        candidate = Path(raw_entry)
        if candidate.is_symlink():
            raise GateFailure(f'Lake produced an unsafe LEAN_PATH entry: {candidate}')
        if not candidate.exists():
            # Lake may include package build directories for packages that do
            # not export Lean modules.  A nonexistent entry cannot resolve a
            # module; omit it from the explicit environment used below.
            continue
        try:
            entry = candidate.resolve(strict=True)
        except OSError as error:
            raise GateFailure(
                f'Lake produced an unavailable LEAN_PATH entry: '
                f'{raw_entry!r}: {error}'
            ) from error
        if not entry.is_dir():
            raise GateFailure(f'Lake produced an unsafe LEAN_PATH entry: {entry}')
        if entry in entries:
            raise GateFailure(f'Lake produced a duplicate LEAN_PATH entry: {entry}')
        entries.append(entry)
    return executable, tuple(entries)


def require_namespace_provenance(
    entries: Sequence[Path], *, project_root: Path,
    completion_root: Path | None,
) -> None:
    """Reject project namespaces supplied by package or caller caches."""

    project = project_root.resolve(strict=True)
    completion = (
        None if completion_root is None else completion_root.resolve(strict=True)
    )
    resolved_entries = tuple(entry.resolve(strict=True) for entry in entries)
    if project not in resolved_entries:
        raise GateFailure('effective LEAN_PATH omits the exact project build root')
    for root in resolved_entries:
        for namespace, allowed in (
            ('Erdos848', project),
            ('Erdos848Completion', completion),
        ):
            candidate = root / namespace
            if not candidate.exists():
                continue
            if not candidate.is_dir() or candidate.is_symlink():
                raise GateFailure(f'unsafe {namespace} namespace root: {candidate}')
            for olean in candidate.rglob('*.olean'):
                if olean.is_symlink():
                    raise GateFailure(f'symlinked project OLean: {olean}')
                resolved = olean.resolve(strict=True)
                if allowed is None or not resolved.is_relative_to(allowed):
                    raise GateFailure(
                        f'{namespace} OLean comes from an untrusted root: {resolved}'
                    )


def explicit_lean_environment(
    base_env: dict[str, str], entries: Sequence[Path],
) -> dict[str, str]:
    result = sanitized_lean_environment(base_env)
    result['LEAN_PATH'] = os.pathsep.join(str(path) for path in entries)
    return result


def require_hash(path: Path, expected: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise GateFailure(f'required regular source is missing: {path}')
    observed = sha256_file(path)
    if observed != expected:
        raise GateFailure(f'digest mismatch for {path}: {observed}')


def source_snapshot(upstream: Path) -> dict[str, Any]:
    revision = capture(('git', 'rev-parse', 'HEAD'), upstream)
    tree = capture(('git', 'rev-parse', 'HEAD^{tree}'), upstream)
    lean_tree = capture(('git', 'rev-parse', 'HEAD:lean4'), upstream)
    dirty = capture(('git', 'status', '--porcelain'), upstream)
    if (revision, tree, lean_tree) != (REVISION, TREE, LEAN_TREE):
        raise GateFailure(
            f'upstream pin mismatch: {revision} {tree} {lean_tree}'
        )
    if dirty:
        raise GateFailure('upstream checkout is not clean')
    for relative, digest in FILE_HASHES.items():
        require_hash(upstream / relative, digest)
    sources = sorted((upstream / 'lean4' / 'Erdos848').rglob('*.lean'))
    if any(path.is_symlink() for path in sources):
        raise GateFailure('project Lean closure contains a symlink')
    source_bytes = sum(path.stat().st_size for path in sources)
    if len(sources) != SOURCE_COUNT or source_bytes != SOURCE_BYTES:
        raise GateFailure(
            f'project source census mismatch: {len(sources)} / {source_bytes}'
        )
    lean4 = upstream / 'lean4'
    publication_names = tuple(sorted(module_name(lean4, path) for path in sources))
    publication_digest = module_list_digest(publication_names)
    provider_names = project_module_closure(
        lean4, 'Erdos848.PaperGeneratedCertificateProvider'
    )
    if (
        len(provider_names) != PROVIDER_MODULES
        or module_list_digest(provider_names) != PROVIDER_MODULE_LIST_SHA256
    ):
        raise GateFailure('provider source dependency closure mismatch')
    wrappers = set(publication_names) - set(provider_names)
    if wrappers != {
        'Erdos848.PublicationTheoremMap',
        'Erdos848.PublicationAxiomAudit',
    }:
        raise GateFailure(f'unexpected publication wrapper set: {sorted(wrappers)}')
    if publication_digest != PUBLICATION_MODULE_LIST_SHA256:
        raise GateFailure('publication source module-list digest mismatch')
    return {
        'revision': revision,
        'tree': tree,
        'lean_tree': lean_tree,
        'modules': len(sources),
        'bytes': source_bytes,
        'provider_modules': len(provider_names),
        'provider_module_list_sha256': PROVIDER_MODULE_LIST_SHA256,
        'publication_module_list_sha256': publication_digest,
    }


def project_imports(source: Path) -> tuple[str, ...]:
    imports: list[str] = []
    block_comment_depth = 0
    with source.open('r', encoding='utf-8-sig') as stream:
        for line in stream:
            stripped = line.strip()
            block_comment_depth += stripped.count('/-')
            if block_comment_depth:
                block_comment_depth -= stripped.count('-/')
                continue
            if not stripped or stripped.startswith('--') or stripped == 'prelude':
                continue
            match = re.match(r'import\s+(.+?)\s*$', stripped)
            if match is None:
                break
            imports.extend(
                module for module in match.group(1).split()
                if module.startswith('Erdos848')
            )
    return tuple(imports)


def module_path(lean4: Path, module: str) -> Path:
    return lean4.joinpath(*module.split('.')).with_suffix('.lean')


def module_name(lean4: Path, source: Path) -> str:
    return '.'.join(source.relative_to(lean4).with_suffix('').parts)


def project_module_closure(lean4: Path, root_module: str) -> tuple[str, ...]:
    seen: set[str] = set()
    stack = [root_module]
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        source = module_path(lean4, module)
        if not source.is_file() or source.is_symlink():
            raise GateFailure(f'missing or unsafe project import: {module}')
        seen.add(module)
        stack.extend(project_imports(source))
    return tuple(sorted(seen))


def module_list_digest(modules: Sequence[str]) -> str:
    payload = ('\n'.join(modules) + '\n').encode('ascii')
    return hashlib.sha256(payload).hexdigest()


def root_snapshot(*, require_clean: bool) -> dict[str, Any]:
    top = Path(capture(('git', 'rev-parse', '--show-toplevel'), REPO_ROOT))
    if top.resolve(strict=True) != REPO_ROOT.resolve(strict=True):
        raise GateFailure(f'root entrypoint is not in the expected repository: {top}')
    head = capture(('git', 'rev-parse', 'HEAD'), REPO_ROOT)
    tree = capture(('git', 'rev-parse', 'HEAD^{tree}'), REPO_ROOT)
    dirty = capture(
        ('git', 'status', '--porcelain', '--untracked-files=all'), REPO_ROOT
    )
    if require_clean and dirty:
        raise GateFailure('root completion repository is not clean')
    if project_imports(FINAL_SOURCE) != (
        'Erdos848.PaperGeneratedCertificateProvider',
        'Erdos848.HallReduction',
        'Erdos848.SharpnessCore',
    ):
        raise GateFailure('literal root theorem has unexpected direct imports')
    if project_imports(AUDIT_SOURCE) != ('Erdos848Completion.Final',):
        raise GateFailure('root axiom audit has unexpected direct imports')
    return {
        'head': head,
        'tree': tree,
        'clean': not bool(dirty),
        'final_sha256': sha256_file(FINAL_SOURCE),
        'axiom_audit_sha256': sha256_file(AUDIT_SOURCE),
        'test_sha256': sha256_file(TEST_SOURCE),
        'runner_sha256': sha256_file(Path(__file__).resolve()),
    }


def prepare_receipt_dir(requested: Path, upstream: Path) -> Path:
    absolute = requested if requested.is_absolute() else Path.cwd() / requested
    if absolute.exists() and absolute.is_symlink():
        raise GateFailure('receipt directory itself must not be a symlink')
    receipt_dir = absolute.resolve(strict=False)
    repo = REPO_ROOT.resolve(strict=True)
    upstream = upstream.resolve(strict=True)
    if (
        receipt_dir == Path(receipt_dir.anchor)
        or receipt_dir == repo
        or repo in receipt_dir.parents
        or receipt_dir in repo.parents
        or receipt_dir == upstream
        or upstream in receipt_dir.parents
        or receipt_dir in upstream.parents
    ):
        raise GateFailure(
            'receipt directory must be external to, and not above, either source tree'
        )
    if receipt_dir.exists() and not receipt_dir.is_dir():
        raise GateFailure('receipt path must be a directory')
    if receipt_dir.exists() and any(receipt_dir.iterdir()):
        raise GateFailure('receipt directory must be absent or empty')
    receipt_dir.mkdir(parents=True, exist_ok=True)
    return receipt_dir


def require_fresh_build(upstream: Path) -> None:
    build = upstream / 'lean4' / '.lake' / 'build' / 'lib' / 'lean' / 'Erdos848'
    existing = sorted(build.rglob('*.olean')) if build.exists() else []
    if existing:
        raise GateFailure(
            f'clean build requires zero project OLeans; found {len(existing)}'
        )


class MemoryStatus(ctypes.Structure):
    _fields_ = [
        ('length', ctypes.c_ulong), ('memory_load', ctypes.c_ulong),
        ('total_phys', ctypes.c_ulonglong), ('avail_phys', ctypes.c_ulonglong),
        ('total_page_file', ctypes.c_ulonglong),
        ('avail_page_file', ctypes.c_ulonglong),
        ('total_virtual', ctypes.c_ulonglong),
        ('avail_virtual', ctypes.c_ulonglong),
        ('avail_extended_virtual', ctypes.c_ulonglong),
    ]


def require_host(upstream: Path) -> dict[str, Any]:
    machine = platform.machine().lower()
    if sys.platform != 'win32' or machine not in {'amd64', 'x86_64'}:
        raise GateFailure(
            f'full gate requires Windows x86-64; got {sys.platform}/{machine}'
        )
    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise GateFailure('GlobalMemoryStatusEx failed')
    free_storage = shutil.disk_usage(upstream).free
    gib = 1 << 30
    if status.total_phys < 64 * gib:
        raise GateFailure(f'physical memory below 64 GiB: {status.total_phys}')
    if status.avail_phys < (32768 + 1024) * (1 << 20):
        raise GateFailure(f'available memory below guard requirement: {status.avail_phys}')
    if free_storage < 200 * gib:
        raise GateFailure(f'free storage below 200 GiB: {free_storage}')
    return {
        'system': platform.system(), 'machine': platform.machine(),
        'platform': platform.platform(), 'python': platform.python_version(),
        'total_memory_bytes': int(status.total_phys),
        'available_memory_bytes': int(status.avail_phys),
        'free_storage_bytes': free_storage,
    }


def lake_package_specs(lean4: Path) -> tuple[dict[str, str], ...]:
    manifest_path = lean4 / 'lake-manifest.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise GateFailure(f'invalid pinned Lake manifest: {error}') from error
    if manifest.get('packagesDir') != '.lake/packages':
        raise GateFailure('unexpected Lake packages directory')
    raw_packages = manifest.get('packages')
    if type(raw_packages) is not list or len(raw_packages) != 9:
        raise GateFailure('unexpected Lake package count')
    specs: list[dict[str, str]] = []
    names: set[str] = set()
    for raw in raw_packages:
        if type(raw) is not dict:
            raise GateFailure('malformed Lake package entry')
        name = raw.get('name')
        url = raw.get('url')
        revision = raw.get('rev')
        if (
            type(name) is not str
            or re.fullmatch(r'[A-Za-z0-9_-]+', name) is None
            or name in names
            or type(url) is not str
            or not url.startswith('https://github.com/')
            or type(revision) is not str
            or re.fullmatch(r'[0-9a-f]{40}', revision) is None
            or raw.get('type') != 'git'
            or raw.get('subDir') is not None
        ):
            raise GateFailure(f'unsafe or unsupported Lake package entry: {raw!r}')
        names.add(name)
        specs.append({'name': name, 'url': url, 'revision': revision})
    if next(item for item in specs if item['name'] == 'mathlib')['revision'] != MATHLIB:
        raise GateFailure('mathlib revision differs from the pinned lock')
    return tuple(specs)


def normalized_git_url(value: str) -> str:
    return value.rstrip('/').removesuffix('.git')


def dependency_snapshot(lean4: Path) -> dict[str, dict[str, str]]:
    packages_root = lean4 / '.lake' / 'packages'
    if not packages_root.is_dir() or packages_root.is_symlink():
        raise GateFailure('Lake package directory is missing or unsafe')
    specs = lake_package_specs(lean4)
    expected_names = {item['name'] for item in specs}
    observed_names = {path.name for path in packages_root.iterdir()}
    if observed_names != expected_names:
        raise GateFailure(
            'Lake package inventory mismatch: '
            f'missing={sorted(expected_names - observed_names)} '
            f'extra={sorted(observed_names - expected_names)}'
        )
    result: dict[str, dict[str, str]] = {}
    for item in specs:
        package = packages_root / item['name']
        if not package.is_dir() or package.is_symlink():
            raise GateFailure(f'unsafe Lake package checkout: {item["name"]}')
        revision = capture(('git', 'rev-parse', 'HEAD'), package)
        tree = capture(('git', 'rev-parse', 'HEAD^{tree}'), package)
        dirty = capture(
            ('git', 'status', '--porcelain', '--untracked-files=all'), package
        )
        remote = capture(('git', 'remote', 'get-url', 'origin'), package)
        if revision != item['revision'] or dirty:
            raise GateFailure(
                f'dirty or mispinned Lake package: {item["name"]}'
            )
        if normalized_git_url(remote) != normalized_git_url(item['url']):
            raise GateFailure(f'Lake package remote mismatch: {item["name"]}')
        result[item['name']] = {
            'revision': revision,
            'tree': tree,
            'url': item['url'],
        }
    return result


def prepare_dependencies(
    lean4: Path, receipt_dir: Path, logs: dict[str, str]
) -> dict[str, dict[str, str]]:
    packages_root = lean4 / '.lake' / 'packages'
    if packages_root.exists() and (
        not packages_root.is_dir() or packages_root.is_symlink()
    ):
        raise GateFailure('Lake packages path is not a safe directory')
    packages_root.mkdir(parents=True, exist_ok=True)
    specs = lake_package_specs(lean4)
    expected_names = {item['name'] for item in specs}
    extras = {path.name for path in packages_root.iterdir()} - expected_names
    if extras:
        raise GateFailure(f'unexpected pre-existing Lake packages: {sorted(extras)}')
    for index, item in enumerate(specs, start=1):
        package = packages_root / item['name']
        if package.exists():
            continue
        clone_log = run_logged(
            f'00-{index:02d}-{item["name"]}-clone',
            ('git', 'clone', '--no-checkout', item['url'], str(package)),
            lean4, receipt_dir, 7200,
        )
        logs[clone_log.name] = sha256_file(clone_log)
        checkout_log = run_logged(
            f'00-{index:02d}-{item["name"]}-checkout',
            ('git', '-C', str(package), 'checkout', '--detach', item['revision']),
            lean4, receipt_dir, 1800,
        )
        logs[checkout_log.name] = sha256_file(checkout_log)
    return dependency_snapshot(lean4)


def observed_lean_version(
    executable: Path, lean4: Path, env: dict[str, str]
) -> str:
    output = capture((str(executable), '--version'), lean4, env=env)
    expected = (
        f'Lean (version 4.30.0-rc2, '
    )
    if not output.startswith(expected) or f'commit {LEAN_COMMIT},' not in output:
        raise GateFailure(f'unexpected observed Lean version: {output}')
    return output


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Stop a guarded command and every descendant on failure/interruption."""

    if process.poll() is not None:
        return
    if sys.platform == 'win32':
        subprocess.run(
            ('taskkill', '/PID', str(process.pid), '/T', '/F'),
            check=False, stdout=subprocess.DEVNULL,
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
        raise GateFailure(f'failed to terminate process tree {process.pid}') from error


def run_logged(
    name: str, command: Sequence[str], cwd: Path, receipt_dir: Path,
    timeout: int, env: dict[str, str] | None = None,
) -> Path:
    log_path = receipt_dir / f'{name}.log'
    partial = receipt_dir / f'{name}.partial.log'
    if log_path.exists() or partial.exists():
        raise GateFailure(f'refusing to overwrite gate log: {name}')
    heading = f'COMMAND {shlex.join(command)}\nCWD {cwd}\n'
    with partial.open('w', encoding='utf-8', newline='\n') as log:
        log.write(heading)
        log.flush()
        print(heading, end='', flush=True)
        popen_options: dict[str, Any] = {}
        if sys.platform == 'win32':
            popen_options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_options['start_new_session'] = True
        process = subprocess.Popen(
            list(command), cwd=cwd, text=True,
            stdout=log, stderr=subprocess.STDOUT, env=env,
            **popen_options,
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            terminate_process_tree(process)
            raise GateFailure(
                f'gate command timed out after {timeout}s: '
                f'{shlex.join(command)}; inspect {partial}'
            ) from error
        except BaseException:
            terminate_process_tree(process)
            raise
        finally:
            log.flush()
            os.fsync(log.fileno())
    if returncode != 0:
        raise GateFailure(
            f'gate command failed ({returncode}): {shlex.join(command)}; '
            f'inspect {partial}'
        )
    partial.replace(log_path)
    print(f'LOG {log_path}', flush=True)
    return log_path


def require_log_marker(path: Path, marker: str, label: str) -> None:
    with path.open('r', encoding='utf-8', errors='strict') as stream:
        if any(marker in line for line in stream):
            return
    raise GateFailure(f'{label} lacks its final marker: {marker}')


def built_project_modules(lean4: Path) -> tuple[str, ...]:
    library = lean4 / '.lake' / 'build' / 'lib' / 'lean'
    project = library / 'Erdos848'
    if not project.is_dir() or project.is_symlink():
        raise GateFailure('built project OLean directory is missing or unsafe')
    modules: list[str] = []
    for path in sorted(project.rglob('*.olean')):
        if path.is_symlink():
            raise GateFailure(f'built project OLean is a symlink: {path}')
        modules.append('.'.join(path.relative_to(library).with_suffix('').parts))
    return tuple(modules)


def module_from_olean_path(path: Path) -> str | None:
    parts = path.parts
    for namespace in ('Erdos848', 'Erdos848Completion'):
        if namespace not in parts:
            continue
        index = len(parts) - 1 - tuple(reversed(parts)).index(namespace)
        suffix = list(parts[index:])
        suffix[-1] = Path(suffix[-1]).stem
        return '.'.join(suffix)
    return None


def require_direct_dependencies(
    output: str, *, expected: dict[str, Path], label: str
) -> None:
    observed: dict[str, Path] = {}
    for raw_line in output.splitlines():
        raw_path = raw_line.strip()
        if not raw_path.lower().endswith('.olean'):
            continue
        path = Path(raw_path).resolve(strict=False)
        module = module_from_olean_path(path)
        if module is None:
            continue
        if module in observed:
            raise GateFailure(f'{label} repeated direct import: {module}')
        observed[module] = path
    if set(observed) != set(expected):
        raise GateFailure(
            f'{label} direct-import mismatch: '
            f'missing={sorted(set(expected) - set(observed))} '
            f'extra={sorted(set(observed) - set(expected))}'
        )
    for module, expected_path in expected.items():
        actual = observed[module]
        wanted = expected_path.resolve(strict=True)
        if actual != wanted:
            raise GateFailure(
                f'{label} imported {module} from {actual}, expected {wanted}'
            )


def parse_axioms(output: str) -> dict[str, list[str]]:
    reports: dict[str, list[str]] = {}
    lines = output.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^'([^']+)' (.*)$", line.strip())
        if match is None or match.group(1) not in ENDPOINTS:
            continue
        declaration, remainder = match.groups()
        if declaration in reports:
            raise GateFailure(f'duplicate axiom report: {declaration}')
        if remainder == 'does not depend on any axioms':
            reports[declaration] = []
            continue
        if not remainder.startswith('depends on axioms:'):
            raise GateFailure(f'unrecognized axiom output: {line}')
        payload = remainder[len('depends on axioms:'):].strip()
        cursor = index + 1
        while ']' not in payload and cursor < len(lines):
            payload += lines[cursor].strip()
            cursor += 1
        bracket = re.fullmatch(r'\[([^]]*)\]', payload)
        if bracket is None:
            raise GateFailure(f'malformed axiom list for {declaration}')
        axioms = [part.strip() for part in bracket.group(1).split(',') if part.strip()]
        forbidden = sorted(set(axioms) - set(ALLOWED_AXIOMS))
        if forbidden:
            raise GateFailure(f'forbidden axioms for {declaration}: {forbidden}')
        reports[declaration] = axioms
    missing = sorted(set(ENDPOINTS) - set(reports))
    if missing:
        raise GateFailure(f'missing live axiom reports: {missing}')
    return reports


def atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream-root', type=Path, default=DEFAULT_UPSTREAM)
    parser.add_argument('--receipt-dir', type=Path)
    parser.add_argument('--runtime-bin', type=Path)
    parser.add_argument('--source-audit-only', action='store_true')
    parser.add_argument('--memory-mib', type=int, default=32768)
    args = parser.parse_args()

    lock = read_lock()
    root_before = root_snapshot(require_clean=not args.source_audit_only)
    upstream = args.upstream_root.resolve(strict=True)
    before = source_snapshot(upstream)
    print(f'source_lock_sha256={sha256_file(LOCK_PATH)}')
    print(f'root_head={root_before["head"]} clean={root_before["clean"]}')
    print(f'upstream_revision={before["revision"]}')
    print(f'publication_sources={before["modules"]} bytes={before["bytes"]}')
    if args.source_audit_only:
        print('SOURCE AUDIT ONLY: no Lean build, kernel replay, or axiom gate executed')
        return 0
    if args.memory_mib != lock['minimum_host']['build_memory_mib']:
        raise GateFailure('full gate requires the locked 32768 MiB ceiling')
    if args.receipt_dir is None:
        raise GateFailure('--receipt-dir is required for the full gate')
    if args.runtime_bin is None:
        raise GateFailure('--runtime-bin is required for the full gate')
    require_fresh_build(upstream)
    host = require_host(upstream)

    receipt_dir = prepare_receipt_dir(args.receipt_dir, upstream)
    olean_root = receipt_dir / 'root-oleans'
    final_olean = olean_root / 'Erdos848Completion' / 'Final.olean'
    final_olean.parent.mkdir(parents=True)

    try:
        import psutil
    except ImportError as error:
        raise GateFailure('psutil==7.2.2 is required') from error
    if psutil.__version__ != '7.2.2':
        raise GateFailure(f'unexpected psutil version: {psutil.__version__}')

    logs: dict[str, str] = {}
    lean4 = upstream / 'lean4'
    base_env = sanitized_lean_environment()
    runtime_bin, lean_executable, lake_executable = resolved_runtime_executables(
        args.runtime_bin, base_env
    )
    lean_version = observed_lean_version(lean_executable, lean4, base_env)
    dependencies_before = prepare_dependencies(lean4, receipt_dir, logs)
    print(
        f'LEAN_GATE_PHASE absolute-mathlib-cache-bootstrap '
        f'lake={lake_executable}',
        flush=True,
    )
    cache_log = run_logged(
        '01-mathlib-cache',
        (str(lake_executable), 'exe', 'cache', 'get'), lean4,
        receipt_dir, 7200, base_env,
    )
    logs[cache_log.name] = sha256_file(cache_log)
    print('LEAN_GATE_PHASE verify-post-cache-dependency-snapshot', flush=True)
    try:
        dependencies_after_cache = dependency_snapshot(lean4)
    except (GateFailure, OSError, subprocess.SubprocessError) as error:
        raise GateFailure(
            f'verify-post-cache-dependency-snapshot: {error}'
        ) from error
    if dependencies_after_cache != dependencies_before:
        raise GateFailure('Lake dependency checkout changed during cache setup')
    print('LEAN_GATE_PHASE verify-zero-project-oleans-after-cache', flush=True)
    require_fresh_build(upstream)
    print('LEAN_GATE_PHASE absolute-mathlib-cache-bootstrap-complete', flush=True)
    lean_executable_after_cache = resolved_lean_executable(
        lean4, base_env, lake_executable
    )
    if lean_executable_after_cache != lean_executable:
        raise GateFailure('resolved Lean executable changed during cache setup')

    build_command = (
        sys.executable, '-B',
        str(upstream / 'scripts' / 'build_generated_certificate.py'),
        '--kind', 'generic', '--module-prefix', 'Erdos848',
        '--generic-target', 'Erdos848.PaperGeneratedCertificateProvider',
        '--workers', '1', '--max-active-leaves', '1',
        '--max-memory-mib', '15360', '--final-max-memory-mib', '32768',
        '--core-max-memory-mib', '32768',
        '--leaf-timeout-seconds', '1800',
        '--final-timeout-seconds', '7200',
        '--core-timeout-seconds', '3600',
        '--preflight-leaves', '0', '--stage', 'all',
    )
    build_log = run_logged(
        '02-clean-source-build', build_command, upstream, receipt_dir, 172800,
        base_env,
    )
    require_log_marker(build_log, 'passed status=', 'clean build')
    logs[build_log.name] = sha256_file(build_log)

    lean_executable_after, lake_entries = resolved_lean_environment(
        lean4, base_env, lake_executable
    )
    if lean_executable_after != lean_executable:
        raise GateFailure('resolved Lean executable changed during build')
    project_olean_root = (lean4 / '.lake' / 'build' / 'lib' / 'lean').resolve(
        strict=True
    )
    provider_modules = project_module_closure(
        lean4, 'Erdos848.PaperGeneratedCertificateProvider'
    )
    project_oleans = built_project_modules(lean4)
    if project_oleans != provider_modules:
        expected_set = set(provider_modules)
        observed_set = set(project_oleans)
        raise GateFailure(
            'post-build provider OLean inventory mismatch: '
            f'missing={sorted(expected_set - observed_set)[:20]} '
            f'extra={sorted(observed_set - expected_set)[:20]}'
        )
    require_namespace_provenance(
        lake_entries, project_root=project_olean_root, completion_root=None
    )
    direct_env = explicit_lean_environment(base_env, lake_entries)

    kernel_log = run_logged(
        '03-upstream-kernel-gates',
        (sys.executable, '-B', str(upstream / 'scripts' / 'run_kernel_gates.py'),
         '--memory-mib', str(args.memory_mib)),
        upstream, receipt_dir, 86400, base_env,
    )
    require_log_marker(
        kernel_log,
        '[kernel-gate:ok] paper-machine version, trust=0, and axioms',
        'upstream kernel gate',
    )
    logs[kernel_log.name] = sha256_file(kernel_log)

    final_log = run_logged(
        '04-root-final-build',
        (str(lean_executable), '--trust=0', f'--memory={args.memory_mib}',
         '--threads=1', f'--root={LEAN_ROOT}', f'--o={final_olean}',
         str(FINAL_SOURCE)),
        lean4, receipt_dir, 86400, direct_env,
    )
    if not final_olean.is_file():
        raise GateFailure('root final theorem did not produce its OLean')
    logs[final_log.name] = sha256_file(final_log)

    audit_entries = (olean_root.resolve(strict=True), *lake_entries)
    require_namespace_provenance(
        audit_entries,
        project_root=project_olean_root,
        completion_root=olean_root,
    )
    audit_env = explicit_lean_environment(base_env, audit_entries)
    audit_log = run_logged(
        '05-root-trust-zero-axioms',
        (str(lean_executable), '--trust=0', f'--memory={args.memory_mib}',
         '--threads=1', f'--root={LEAN_ROOT}', str(AUDIT_SOURCE)),
        lean4, receipt_dir, 86400, audit_env,
    )
    axiom_reports = parse_axioms(audit_log.read_text(encoding='utf-8'))
    logs[audit_log.name] = sha256_file(audit_log)

    final_deps_log = run_logged(
        '06-root-final-dependencies',
        (str(lean_executable), '--deps', f'--root={LEAN_ROOT}',
         str(FINAL_SOURCE)),
        lean4, receipt_dir, 7200, direct_env,
    )
    require_direct_dependencies(
        final_deps_log.read_text(encoding='utf-8'),
        expected={
            module: project_olean_root.joinpath(*module.split('.')).with_suffix(
                '.olean'
            )
            for module in (
                'Erdos848.PaperGeneratedCertificateProvider',
                'Erdos848.HallReduction',
                'Erdos848.SharpnessCore',
            )
        },
        label='root final theorem',
    )
    logs[final_deps_log.name] = sha256_file(final_deps_log)

    audit_deps_log = run_logged(
        '07-root-audit-dependencies',
        (str(lean_executable), '--deps', f'--root={LEAN_ROOT}',
         str(AUDIT_SOURCE)),
        lean4, receipt_dir, 7200, audit_env,
    )
    require_direct_dependencies(
        audit_deps_log.read_text(encoding='utf-8'),
        expected={'Erdos848Completion.Final': final_olean},
        label='root axiom audit',
    )
    logs[audit_deps_log.name] = sha256_file(audit_deps_log)

    after = source_snapshot(upstream)
    if after != before:
        raise GateFailure('upstream tracked source changed during build')
    if built_project_modules(lean4) != project_oleans:
        raise GateFailure('project OLean inventory changed during completion gate')
    dependencies_after = dependency_snapshot(lean4)
    if dependencies_after != dependencies_before:
        raise GateFailure('Lake dependency checkout changed during completion gate')
    root_after = root_snapshot(require_clean=True)
    if root_after != root_before:
        raise GateFailure('root completion source changed during gate')

    receipt = {
        'version': 1,
        'status': 'lean-completion-gate-passed',
        'source_lock_sha256': sha256_file(LOCK_PATH),
        'root_repository': root_after,
        'upstream': after,
        'lake_dependencies': dependencies_after,
        'host': host,
        'toolchain': {
            'lean': TOOLCHAIN, 'observed_lean_version': lean_version,
            'runtime_archive_sha256': RUNTIME_ARCHIVE_SHA256,
            'runtime_bin': str(runtime_bin),
            'resolved_lean_executable': str(lean_executable),
            'lean_executable_sha256': LEAN_EXECUTABLE_SHA256,
            'resolved_lake_executable': str(lake_executable),
            'lake_executable_sha256': LAKE_EXECUTABLE_SHA256,
            'lean_commit': LEAN_COMMIT, 'mathlib_revision': MATHLIB,
            'psutil': psutil.__version__,
        },
        'effective_lean_path': [str(path) for path in audit_entries],
        'provider_olean_count': len(project_oleans),
        'provider_module_list_sha256': module_list_digest(project_oleans),
        'publication_source_count': SOURCE_COUNT,
        'root_final_olean_sha256': sha256_file(final_olean),
        'allowed_axioms': list(ALLOWED_AXIOMS),
        'axiom_reports': axiom_reports,
        'logs': logs,
    }
    receipt_path = receipt_dir / 'lean-completion-receipt.json'
    atomic_write(receipt_path, canonical_json(receipt))
    print(f'receipt={receipt_path}')
    print(f'receipt_sha256={sha256_file(receipt_path)}')
    print('LEAN COMPLETION GATE PASSED')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (GateFailure, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'LEAN COMPLETION GATE FAILED: {error}', file=sys.stderr)
        raise SystemExit(1) from error
