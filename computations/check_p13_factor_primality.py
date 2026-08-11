#!/usr/bin/env python3
"""Independently certify every factor in the p=13 interval transcript.

This checker deliberately does not use Miller--Rabin, the transcript generator,
or any module from the candidate repository.  It proves primality in one exact
batch:

* sieve every prime q <= floor(sqrt(max_factor));
* check each claimed factor at most that limit directly in the sieve;
* multiply every larger distinct claimed factor into P;
* multiply every sieved prime into M; and
* require gcd(P, M) = 1.

If a larger claimed factor were composite, it would have a prime divisor at
most its square root, hence at most floor(sqrt(max_factor)); that divisor would
divide M and P.  Therefore the final gcd equality certifies every large factor.
Every transcript row is also authenticated, parsed canonically, and multiplied
back to z^2 + 1 using exact Python integers.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


EXPECTED_GZIP_SHA256 = (
    "15eba52d6d019d5730647adf5b7066663155b364a54222831fa2e90a96e901b3"
)
EXPECTED_RAW_SHA256 = (
    "75f5ad855fd6cbf54aef07b19b7d1910d2c30d5d78371fb86ae77b4e41202c42"
)
EXPECTED_ROWS = 1_439_686
EXPECTED_FACTOR_OCCURRENCES = 8_373_490
EXPECTED_DISTINCT_FACTORS = 1_357_591
EXPECTED_MAX_ANCHOR = 999_999_941
EXPECTED_MAX_FACTOR = 2_958_540_704_271_709
HEADER = b"z\tz2_plus_1_factors\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def canonical_positive_decimal(field: bytes, label: str) -> int:
    if not field:
        raise RuntimeError(f"empty {label}")
    if field == b"0" or field[0] == ord("0"):
        raise RuntimeError(f"nonpositive or noncanonical {label}")
    if any(byte < ord("0") or byte > ord("9") for byte in field):
        raise RuntimeError(f"nondecimal {label}")
    value = int(field)
    if str(value).encode("ascii") != field:
        raise RuntimeError(f"noncanonical {label}")
    return value


def parse_transcript(path: Path) -> tuple[set[int], dict[str, int | str]]:
    compressed = sha256_file(path)
    if compressed != EXPECTED_GZIP_SHA256:
        raise RuntimeError(
            "factor gzip digest mismatch: "
            f"expected {EXPECTED_GZIP_SHA256}, got {compressed}"
        )

    raw_digest = hashlib.sha256()
    factors_seen: set[int] = set()
    rows = 0
    occurrences = 0
    previous_anchor = 0
    maximum_factor = 0

    with gzip.open(path, "rb") as handle:
        header = handle.readline()
        raw_digest.update(header)
        if header != HEADER:
            raise RuntimeError("unexpected factor transcript header")

        for line in handle:
            raw_digest.update(line)
            if not line.endswith(b"\n") or b"\r" in line:
                raise RuntimeError("noncanonical factor transcript line ending")
            body = line[:-1]
            if body.count(b"\t") != 1:
                raise RuntimeError("factor row does not have two fields")
            anchor_field, factor_field = body.split(b"\t")
            anchor = canonical_positive_decimal(anchor_field, "anchor")
            if anchor <= previous_anchor:
                raise RuntimeError("factor anchors are not strictly increasing")
            previous_anchor = anchor
            if not factor_field:
                raise RuntimeError(f"empty factorization at z={anchor}")

            product = 1
            previous_factor = 0
            for factor_bytes in factor_field.split(b"*"):
                factor = canonical_positive_decimal(factor_bytes, "factor")
                if factor < previous_factor:
                    raise RuntimeError(
                        f"factors are not nondecreasing at z={anchor}"
                    )
                previous_factor = factor
                product *= factor
                factors_seen.add(factor)
                occurrences += 1
                if factor > maximum_factor:
                    maximum_factor = factor

            expected_product = anchor * anchor + 1
            if product != expected_product:
                raise RuntimeError(
                    f"factor product mismatch at z={anchor}: "
                    f"expected {expected_product}, got {product}"
                )
            rows += 1

    raw = raw_digest.hexdigest()
    exact = {
        "gzip_sha256": compressed,
        "raw_sha256": raw,
        "rows": rows,
        "factor_occurrences": occurrences,
        "distinct_factors": len(factors_seen),
        "max_anchor": previous_anchor,
        "max_factor": maximum_factor,
    }
    expected = {
        "gzip_sha256": EXPECTED_GZIP_SHA256,
        "raw_sha256": EXPECTED_RAW_SHA256,
        "rows": EXPECTED_ROWS,
        "factor_occurrences": EXPECTED_FACTOR_OCCURRENCES,
        "distinct_factors": EXPECTED_DISTINCT_FACTORS,
        "max_anchor": EXPECTED_MAX_ANCHOR,
        "max_factor": EXPECTED_MAX_FACTOR,
    }
    if exact != expected:
        raise RuntimeError(
            f"transcript summary mismatch: expected {expected}, got {exact}"
        )
    return factors_seen, exact


def prime_sieve(limit: int) -> bytearray:
    if limit < 1:
        return bytearray(limit + 1)
    flags = bytearray(b"\x01") * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for prime in range(2, math.isqrt(limit) + 1):
        if not flags[prime]:
            continue
        start = prime * prime
        count = (limit - start) // prime + 1
        flags[start : limit + 1 : prime] = b"\x00" * count
    return flags


def iter_sieved_primes(flags: bytearray) -> Iterator[int]:
    for value in range(2, len(flags)):
        if flags[value]:
            yield value


@dataclass(frozen=True)
class IntegerBackend:
    name: str
    integer: Callable[[int], Any]
    gcd: Callable[[Any, Any], Any]


def load_backend(name: str) -> IntegerBackend:
    if name == "python":
        return IntegerBackend(name="python", integer=int, gcd=math.gcd)
    if name != "gmpy2":
        raise RuntimeError(f"unknown integer backend: {name}")
    try:
        import gmpy2
    except ImportError as error:
        raise RuntimeError(
            "gmpy2 backend unavailable; install the pinned gmpy2 dependency"
        ) from error
    return IntegerBackend(
        name=f"gmpy2-{gmpy2.version()}-gmp-{gmpy2.mp_version()}",
        integer=gmpy2.mpz,
        gcd=gmpy2.gcd,
    )


def balanced_product(
    values: Iterable[int],
    backend: IntegerBackend,
    block_size: int = 4096,
) -> Any:
    if block_size < 2:
        raise RuntimeError("invalid product block size")
    blocks: list[int] = []
    block: list[int] = []
    for value in values:
        if value < 1:
            raise RuntimeError("product input must be positive")
        block.append(value)
        if len(block) == block_size:
            blocks.append(math.prod(block, start=backend.integer(1)))
            block.clear()
    if block:
        blocks.append(math.prod(block, start=backend.integer(1)))
    if not blocks:
        return backend.integer(1)
    while len(blocks) > 1:
        blocks = [
            blocks[index] * blocks[index + 1]
            if index + 1 < len(blocks)
            else blocks[index]
            for index in range(0, len(blocks), 2)
        ]
    return blocks[0]


def integer_sha256(value: Any) -> str:
    if value < 0:
        raise RuntimeError("cannot hash a negative integer")
    length = max(1, (value.bit_length() + 7) // 8)
    return hashlib.sha256(value.to_bytes(length, "big")).hexdigest()


def certify_factor_set(
    factors: set[int],
    backend: IntegerBackend,
) -> dict[str, int | str]:
    if not factors:
        raise RuntimeError("empty factor set")
    maximum = max(factors)
    limit = math.isqrt(maximum)
    flags = prime_sieve(limit)

    small = sorted(factor for factor in factors if factor <= limit)
    large = sorted(factor for factor in factors if factor > limit)
    for factor in small:
        if not flags[factor]:
            raise RuntimeError(f"composite small claimed factor: {factor}")

    large_product = balanced_product(large, backend)
    primorial = balanced_product(iter_sieved_primes(flags), backend)
    common = backend.gcd(large_product, primorial)
    if common != 1:
        raise RuntimeError(
            "composite large claimed factor detected by batch gcd; "
            f"nontrivial common divisor has {common.bit_length()} bits"
        )

    return {
        "integer_backend": backend.name,
        "sieve_limit": limit,
        "sieve_prime_count": sum(flags),
        "small_factor_count": len(small),
        "large_factor_count": len(large),
        "large_product_bits": large_product.bit_length(),
        "primorial_bits": primorial.bit_length(),
        "large_product_sha256": integer_sha256(large_product),
        "primorial_sha256": integer_sha256(primorial),
        "gcd": int(common),
    }


def run_self_tests(backend: IntegerBackend) -> None:
    prime_case = {2, 3, 5, 37, 101, 1_000_003}
    result = certify_factor_set(prime_case, backend)
    if result["gcd"] != 1:
        raise RuntimeError("prime control failed")

    for composite in (4, 49, 341, 101 * 103):
        try:
            certify_factor_set(prime_case | {composite}, backend)
        except RuntimeError as error:
            if "composite" not in str(error):
                raise RuntimeError(
                    f"unexpected negative-control failure for {composite}: {error}"
                ) from error
        else:
            raise RuntimeError(f"accepted composite negative control: {composite}")

    if balanced_product(range(1, 101), backend) != math.factorial(100):
        raise RuntimeError("balanced-product control failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--skip-self-tests", action="store_true")
    parser.add_argument(
        "--backend",
        choices=("gmpy2", "python"),
        default="gmpy2",
        help=(
            "exact big-integer backend; gmpy2 is theorem-grade default,"
            " while python is a slow reference path"
        ),
    )
    parser.add_argument(
        "--certificate-output",
        type=Path,
        help="write the deterministic batch-certificate summary as JSON",
    )
    args = parser.parse_args()

    started = time.monotonic()
    backend = load_backend(args.backend)
    if not args.skip_self_tests:
        run_self_tests(backend)
        print("batch primality negative controls: PASS", flush=True)

    factors, transcript = parse_transcript(args.transcript)
    print(
        "transcript exact parse: PASS"
        f" rows={transcript['rows']}"
        f" occurrences={transcript['factor_occurrences']}"
        f" distinct={transcript['distinct_factors']}"
        f" max_factor={transcript['max_factor']}",
        flush=True,
    )
    certificate = certify_factor_set(factors, backend)
    for key, value in certificate.items():
        print(f"{key}={value}")
    canonical_certificate = {
        "version": 1,
        "method": "sieve-small-and-batch-primorial-gcd",
        "transcript": transcript,
        "batch": {
            key: value
            for key, value in certificate.items()
            if key != "integer_backend"
        },
    }
    payload = (
        json.dumps(
            canonical_certificate,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")
    certificate_digest = hashlib.sha256(payload).hexdigest()
    print(f"canonical_certificate_sha256={certificate_digest}")
    if args.certificate_output is not None:
        args.certificate_output.write_bytes(payload)
        print(f"certificate_output={args.certificate_output}")
    print(f"elapsed_seconds={time.monotonic() - started:.6f}")
    print("INDEPENDENT P13 FACTOR PRIMALITY AUDIT PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, EOFError, ValueError, RuntimeError) as error:
        print(f"INDEPENDENT P13 FACTOR PRIMALITY AUDIT FAILED: {error}", file=sys.stderr)
        raise SystemExit(1) from error
