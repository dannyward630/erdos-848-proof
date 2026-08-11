#!/usr/bin/env python3
"""Independent direct-factorization checker for the prefix certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


class CertificateError(ValueError):
    pass


def trial_primes(limit: int) -> list[int]:
    primes: list[int] = []
    for candidate in range(2, limit + 1):
        is_prime = True
        for prime in primes:
            if prime * prime > candidate:
                break
            if candidate % prime == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(candidate)
    return primes


def is_squarefree(value: int, primes: list[int]) -> bool:
    remaining = value
    for prime in primes:
        if prime * prime > remaining:
            break
        exponent = 0
        while remaining % prime == 0:
            remaining //= prime
            exponent += 1
            if exponent == 2:
                return False
    return True


def expected_endpoints(limit: int) -> list[int]:
    endpoints = [min(limit, 6)]
    colours = 1
    while 25 * (colours - 1) + 7 <= limit:
        endpoints.append(min(limit, 25 * colours + 6))
        colours += 1
    return list(dict.fromkeys(endpoints))


def validate_payload(payload: object) -> dict[str, int]:
    if not isinstance(payload, dict) or list(payload) != ["limit", "vertices", "records"]:
        raise CertificateError("top-level schema mismatch")
    limit = payload["limit"]
    vertices = payload["vertices"]
    records = payload["records"]
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise CertificateError("invalid limit")
    if not isinstance(vertices, list) or not isinstance(records, list):
        raise CertificateError("vertices and records must be lists")
    if any(not isinstance(vertex, int) or isinstance(vertex, bool) for vertex in vertices):
        raise CertificateError("vertices must be strict JSON integers")

    primes = trial_primes(limit)
    expected_vertices = [
        value
        for value in range(1, limit + 1)
        if not is_squarefree(value * value + 1, primes)
    ]
    if vertices != expected_vertices:
        raise CertificateError("vertex list is not the exact diagonal set")

    endpoints = expected_endpoints(limit)
    if len(records) != len(endpoints):
        raise CertificateError("record count leaves a coverage gap")

    checked_pairs = 0
    prefix_count = 0
    for expected_endpoint, record in zip(endpoints, records):
        if not isinstance(record, list) or len(record) != 4:
            raise CertificateError("record schema mismatch")
        endpoint, declared_count, benchmark, colours = record
        if any(
            not isinstance(field, int) or isinstance(field, bool)
            for field in (endpoint, declared_count, benchmark)
        ):
            raise CertificateError("record scalars must be strict JSON integers")
        if endpoint != expected_endpoint:
            raise CertificateError("endpoint sequence is not gapless and canonical")
        while prefix_count < len(vertices) and vertices[prefix_count] <= endpoint:
            prefix_count += 1
        if declared_count != prefix_count:
            raise CertificateError("wrong prefix vertex count")
        expected_benchmark = (endpoint + 18) // 25
        if benchmark != expected_benchmark:
            raise CertificateError("wrong benchmark")
        if not isinstance(colours, list) or len(colours) != prefix_count:
            raise CertificateError("wrong colour-vector length")
        if any(
            not isinstance(colour, int)
            or isinstance(colour, bool)
            or colour < 0
            or colour >= benchmark
            for colour in colours
        ):
            raise CertificateError("colour outside benchmark range")

        classes: dict[int, list[int]] = defaultdict(list)
        for vertex, colour in zip(vertices[:prefix_count], colours):
            classes[colour].append(vertex)
        for members in classes.values():
            for index, left in enumerate(members):
                for right in members[index + 1 :]:
                    checked_pairs += 1
                    if not is_squarefree(left * right + 1, primes):
                        raise CertificateError(
                            f"same-colour nonsquarefree pair {left},{right}"
                        )

    if endpoints[0] != min(limit, 6) or endpoints[-1] != limit:
        raise CertificateError("certificate does not cover every claimed prefix")
    return {
        "limit": limit,
        "vertices": len(vertices),
        "records": len(records),
        "same_colour_pairs": checked_pairs,
    }


def run_statement_controls() -> None:
    primes = trial_primes(10_000)

    def admissible(values: set[int], include_diagonal: bool = True) -> bool:
        return all(
            not is_squarefree(left * right + 1, primes)
            for left in values
            for right in values
            if include_diagonal or left != right
        )

    if admissible({1}):
        raise CertificateError("negative control {1} was accepted")
    if admissible({7, 18}):
        raise CertificateError("negative control {7,18} was accepted")
    if not admissible({7, 32, 57}):
        raise CertificateError("positive control {7,32,57} was rejected")
    diagonal_variant = {19, 33, 35, 46, 53}
    if not admissible(diagonal_variant, include_diagonal=False):
        raise CertificateError("distinct-pair variant control should be accepted")
    if admissible(diagonal_variant, include_diagonal=True):
        raise CertificateError("diagonal-inclusive variant control was accepted")
    if is_squarefree(50, primes) or not is_squarefree(127, primes):
        raise CertificateError("squarefree classification controls failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    encoded = args.certificate.read_bytes()
    digest = hashlib.sha256(encoded).hexdigest()
    if args.expected_sha256 and digest != args.expected_sha256:
        raise SystemExit(
            f"digest mismatch: expected {args.expected_sha256}, got {digest}"
        )
    try:
        decoded = encoded.decode("ascii")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid canonical JSON: {exc}") from exc
    canonical = json.dumps(payload, separators=(",", ":")).encode("ascii")
    if canonical != encoded:
        raise SystemExit("certificate is not canonical ASCII JSON")
    try:
        result = validate_payload(payload)
        run_statement_controls()
    except CertificateError as exc:
        raise SystemExit(f"REJECTED: {exc}") from exc
    print("VERIFIED exact prefix certificate")
    for key, value in result.items():
        print(f"{key}={value}")
    print(f"bytes={len(encoded)}")
    print(f"sha256={digest}")
    print("statement_controls=passed")


if __name__ == "__main__":
    main()
