#!/usr/bin/env python3
"""Run the theorem-grade independent finite certificate pipeline.

This wrapper does not supply mathematical semantics of its own.  It pins and
orchestrates the independently audited C++ stream verifier, Java exact-product
exporter, GMP gcd checker, and endpoint-401 negative control, then compares the
result with the committed canonical receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CANDIDATE_REVISION = "1afd7c722cae5ee7dd0fd1fde64427537394f749"
EXPECTED_BASE_SHA256 = (
    "3380a6778d237a3fd2a1f01c7ea72292e470a845b09eea99beb66ca85434ba98"
)
EXPECTED_COMPACT_SHA256 = (
    "9917ec4590f69efd8c6f7d30d54ecf5284e92f185ec70a4d14657acb02551b12"
)
EXPECTED_CPP_SHA256 = (
    "b891896e89b943eda2baa0bfe2903ffecc0806c53a301206f18bdd74b78bdc5d"
)
EXPECTED_JAVA_SHA256 = (
    "45c0d97ab1469a9ab63b4a18905ee59b559907b73f3dca70cbd3212823c2a9e5"
)
EXPECTED_GCD_SHA256 = (
    "e686dcaa7c2b668324d83227dbdc36846f1ea5787be3cb1f6aed7daa1c792ac5"
)
EXPECTED_MUTATOR_SHA256 = (
    "5c885ef83783080e1edc28b198686a4107efa0608f05cf0cca39fc26a0c1ee76"
)
EXPECTED_MUTANT_SHA256 = (
    "735a1af16019f98dff145a6655eec331917cbcfe5e4eb023fae4c2e45844e2ae"
)
EXPECTED_LEAF_SHA256 = (
    "56720662876aaddcf5c0706d672d450f85db4f0606c00ba3875c514af7be22fa"
)
EXPECTED_PRIMORIAL_SHA256 = (
    "ab0de48740f26f26ec98f4a636f22ae8d5dd02ec5d189c735bfd989e1ea5b105"
)
EXPECTED_LARGE_PRODUCT_SHA256 = (
    "f4203a24bce785438eaffeea4801f604da010b753bfab0c58415791a2283c64a"
)
EXPECTED_RECEIPT_SHA256 = (
    "4fc75b0ed263df81c07c5997c915511351ea61fff085d3ac95159c524ca9aad6"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require_hash(path: Path, expected: str) -> None:
    observed = sha256_file(path)
    if observed != expected:
        raise RuntimeError(
            f"digest mismatch for {path}: expected {expected}, got {observed}"
        )


def run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    timeout: int,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print("RUN", shlex.join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed with exit {result.returncode}: {shlex.join(command)}"
        )
    return result


def parse_key_values(output: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in output.splitlines():
        if line.count("=") != 1:
            continue
        key, value = line.split("=", 1)
        if not key or key in result:
            raise RuntimeError(f"duplicate or empty output key: {line}")
        result[key] = value
    return result


def require_lines(output: str, expected: set[str]) -> None:
    lines = set(output.splitlines())
    missing = expected - lines
    if missing:
        raise RuntimeError(f"missing decisive output lines: {sorted(missing)}")


def canonical_receipt(
    *,
    leaf_path: Path,
    primorial_path: Path,
    large_product_path: Path,
    export: dict[str, str],
    gcd: dict[str, str],
) -> bytes:
    receipt = {
        "batch": {
            "gcd": int(gcd["large_primorial_gcd"]),
            "large_leaf_count": int(export["large_leaf_count"]),
            "large_product_bits": int(export["large_product_bit_length"]),
            "large_product_bytes": large_product_path.stat().st_size,
            "large_product_sha256": sha256_file(large_product_path),
            "primorial_bits": int(export["primorial_bit_length"]),
            "primorial_bytes": primorial_path.stat().st_size,
            "primorial_sha256": sha256_file(primorial_path),
            "sieve_limit": int(export["sieve_limit"]),
            "sieve_prime_count": int(export["sieve_prime_count"]),
            "small_leaf_count": int(export["small_leaf_count"]),
        },
        "controls": {
            "injected_factor": 2,
            "injected_gcd": int(gcd["injected_factor_control_gcd"]),
            "small_composite": 49,
        },
        "leaf_stream": {
            "bytes": leaf_path.stat().st_size,
            "count": int(export["leaf_count"]),
            "max": int(export["leaf_max"]),
            "min": int(export["leaf_min"]),
            "sha256": sha256_file(leaf_path),
        },
        "method": "exact-sieve-and-batch-primorial-gcd",
        "version": 1,
    }
    return (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "ascii"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-root",
        type=Path,
        default=ROOT / "external" / "erdos-848-all-n",
    )
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    parser.add_argument("--javac", default="javac")
    parser.add_argument("--java", default="java")
    parser.add_argument(
        "--ubsan",
        action="store_true",
        help="also repeat the full C++ replay under undefined-behavior sanitizer",
    )
    args = parser.parse_args()

    for executable in (args.cxx, args.javac, args.java):
        if shutil.which(executable) is None:
            raise RuntimeError(f"required executable not found: {executable}")

    try:
        import gmpy2
    except ImportError as error:
        raise RuntimeError("gmpy2==2.2.1 is required") from error
    if gmpy2.version() != "2.2.1" or gmpy2.mp_version() != "GMP 6.3.0":
        raise RuntimeError(
            "unexpected exact-integer backend: "
            f"gmpy2={gmpy2.version()} GMP={gmpy2.mp_version()}"
        )

    candidate = args.candidate_root.resolve()
    base = candidate / "erdos848_colour_delta_to_100006.bin.gz"
    compact = candidate / "audit" / "erdos848_sparse_compact_100007_100000006.bin.gz"
    cpp = ROOT / "computations" / "independent_check_finite_stream.cpp"
    java_source = ROOT / "computations" / "CertifyLeavesExport.java"
    gcd_source = ROOT / "computations" / "gcd_finite_factor_products.py"
    mutator = ROOT / "computations" / "mutate_finite_endpoint401.py"
    committed_receipt = ROOT / "certificates" / "finite-factor-leaves.json"

    revision = run(
        ["git", "-C", str(candidate), "rev-parse", "HEAD"],
        timeout=30,
    ).stdout.strip()
    if revision != EXPECTED_CANDIDATE_REVISION:
        raise RuntimeError(
            f"candidate revision mismatch: expected {EXPECTED_CANDIDATE_REVISION}, "
            f"got {revision}"
        )

    for path, digest in (
        (base, EXPECTED_BASE_SHA256),
        (compact, EXPECTED_COMPACT_SHA256),
        (cpp, EXPECTED_CPP_SHA256),
        (java_source, EXPECTED_JAVA_SHA256),
        (gcd_source, EXPECTED_GCD_SHA256),
        (mutator, EXPECTED_MUTATOR_SHA256),
        (committed_receipt, EXPECTED_RECEIPT_SHA256),
    ):
        require_hash(path, digest)

    with tempfile.TemporaryDirectory(prefix="erdos848-independent-") as raw_temp:
        temp = Path(raw_temp)
        checker = temp / "independent_check_finite_stream"
        leaves = temp / "finite_factor_leaves.bin"
        classes = temp / "java-classes"
        classes.mkdir()
        primorial = temp / "primorial.bin"
        large_product = temp / "large_product.bin"

        run(
            [
                args.cxx,
                "-O3",
                "-std=c++20",
                "-Wall",
                "-Wextra",
                "-Wconversion",
                "-pedantic",
                str(cpp),
                "-lz",
                "-o",
                str(checker),
            ],
            timeout=180,
        )
        finite_result = run(
            [str(checker), str(base), str(compact), str(leaves)],
            timeout=1200,
        )
        require_lines(
            finite_result.stdout,
            {
                "independent_base_changes=4915348",
                "independent_base_endpoint_pairs=18049789 endpoint_count=4000",
                "independent_base_top_pairs=9022",
                "independent_compact_steps=3996000 swaps=1379312 placements=2513387",
                "independent_compact_pair_occurrences=14458371 checked=14458371",
                "independent_factor_leaf_count=11108162",
                "independent_factor_leaf_max=9999932500113877",
                "independent_total_diagonal=10515898",
                "independent_pair_computations=17376578",
                "independent_pair_queries_hits_overwrites=32517182/15140604/10124496",
                "independent_mode=full-with-factor-leaves",
                "INDEPENDENT FINITE STREAM AUDIT PASSED",
            },
        )
        require_hash(leaves, EXPECTED_LEAF_SHA256)
        if leaves.stat().st_size != 88_865_312:
            raise RuntimeError("unexpected factor-leaf byte length")

        run(
            [args.javac, "-Xlint:all", "-d", str(classes), str(java_source)],
            timeout=180,
        )
        export_result = run(
            [
                args.java,
                "-Xms256m",
                "-Xmx1200m",
                "-cp",
                str(classes),
                "CertifyLeavesExport",
                str(leaves),
                str(primorial),
                str(large_product),
            ],
            timeout=1200,
        )
        require_lines(
            export_result.stdout,
            {
                "leaf_count=11108162",
                "leaf_min=2",
                "leaf_max=9999932500113877",
                "sieve_limit=99999662",
                "sieve_prime_count=5761441",
                "small_leaf_count=2328675",
                "large_leaf_count=8779487",
                "primorial_bit_length=144251431",
                "large_product_bit_length=327379849",
                "small_negative_control=passed",
                "BATCH FACTOR-LEAF PRODUCTS EXPORTED",
            },
        )
        require_hash(primorial, EXPECTED_PRIMORIAL_SHA256)
        require_hash(large_product, EXPECTED_LARGE_PRODUCT_SHA256)

        gcd_result = run(
            [
                sys.executable,
                "-B",
                str(gcd_source),
                str(primorial),
                str(large_product),
                "99999662",
            ],
            timeout=600,
        )
        require_lines(
            gcd_result.stdout,
            {
                f"primorial_sha256={EXPECTED_PRIMORIAL_SHA256}",
                f"large_product_sha256={EXPECTED_LARGE_PRODUCT_SHA256}",
                "primorial_bytes=18031429",
                "large_product_bytes=40922482",
                "sieve_limit=99999662",
                "gmpy2_version=2.2.1",
                "gmp_version=GMP 6.3.0",
                "large_primorial_gcd=1",
                "injected_factor_control_gcd=2",
                "negative_control=passed",
                "BATCH FACTOR-LEAF CERTIFICATE PASSED",
            },
        )

        export_values = parse_key_values(export_result.stdout)
        gcd_values = parse_key_values(gcd_result.stdout)
        receipt = canonical_receipt(
            leaf_path=leaves,
            primorial_path=primorial,
            large_product_path=large_product,
            export=export_values,
            gcd=gcd_values,
        )
        if hashlib.sha256(receipt).hexdigest() != EXPECTED_RECEIPT_SHA256:
            raise RuntimeError("generated finite receipt digest mismatch")
        if receipt != committed_receipt.read_bytes():
            raise RuntimeError("generated finite receipt is not byte-identical")

        mutant = temp / "endpoint401-mutant.bin.gz"
        mutation_result = run(
            [sys.executable, "-B", str(mutator), str(base), str(mutant)],
            timeout=120,
        )
        require_hash(mutant, EXPECTED_MUTANT_SHA256)
        require_lines(
            mutation_result.stdout,
            {
                f"source_sha256={EXPECTED_BASE_SHA256}",
                f"mutant_sha256={EXPECTED_MUTANT_SHA256}",
                "original_colour18_after_402=306",
                "mutation_endpoint=401 vertex=18 colour=15 conflict=382*18+1=13*23^2",
            },
        )
        rejected_leaves = temp / "rejected-leaves.bin"
        rejected = run(
            [str(checker), str(mutant), str(compact), str(rejected_leaves)],
            timeout=180,
            check=False,
        )
        if rejected.returncode == 0:
            raise RuntimeError("endpoint-401 mutation was accepted")
        if "INDEPENDENT AUDIT FAILED: endpoint pair is nonsquarefree" not in rejected.stderr:
            raise RuntimeError("endpoint-401 mutation failed for the wrong reason")
        if rejected_leaves.exists():
            raise RuntimeError("rejected run unexpectedly wrote a leaf certificate")

        if args.ubsan:
            sanitizer = temp / "independent_check_finite_stream_ubsan"
            sanitizer_leaves = temp / "finite_factor_leaves_ubsan.bin"
            run(
                [
                    args.cxx,
                    "-O1",
                    "-g",
                    "-std=c++20",
                    "-Wall",
                    "-Wextra",
                    "-Wconversion",
                    "-pedantic",
                    "-fsanitize=undefined",
                    "-fno-sanitize-recover=undefined",
                    str(cpp),
                    "-lz",
                    "-o",
                    str(sanitizer),
                ],
                timeout=180,
            )
            sanitizer_result = run(
                [str(sanitizer), str(base), str(compact), str(sanitizer_leaves)],
                timeout=1800,
            )
            require_lines(
                sanitizer_result.stdout,
                {"INDEPENDENT FINITE STREAM AUDIT PASSED"},
            )
            require_hash(sanitizer_leaves, EXPECTED_LEAF_SHA256)

    print("INDEPENDENT THEOREM-GRADE FINITE PIPELINE PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"INDEPENDENT FINITE PIPELINE FAILED: {error}", file=sys.stderr)
        raise SystemExit(1) from error
