#!/usr/bin/env python3
"""Generate an exact proper-colouring certificate for Erdős 848 prefixes.

The generator uses modular prime-square adjacency.  Soundness does not depend
on this implementation: ``check_prefix_certificate.py`` reconstructs vertices
by direct factorization and checks each same-colour pair independently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sieve_primes(limit: int) -> list[int]:
    composite = bytearray(limit + 1)
    primes: list[int] = []
    for value in range(2, limit + 1):
        if composite[value]:
            continue
        primes.append(value)
        if value * value <= limit:
            composite[value * value : limit + 1 : value] = b"\x01" * (
                (limit - value * value) // value + 1
            )
    return primes


def has_prime_square_factor(value: int, primes: list[int]) -> bool:
    for prime in primes:
        square = prime * prime
        if square > value:
            return False
        if value % square == 0:
            return True
    return False


def eligible_vertices(limit: int, primes: list[int]) -> list[int]:
    return [
        value
        for value in range(1, limit + 1)
        if has_prime_square_factor(value * value + 1, primes)
    ]


def modular_adjacency(
    limit: int, vertices: list[int], primes: list[int]
) -> tuple[dict[int, set[int]], int]:
    vertex_set = set(vertices)
    adjacency = {vertex: set() for vertex in vertices}
    edges: set[tuple[int, int]] = set()
    for prime in primes:
        modulus = prime * prime
        for left in vertices:
            if left % prime == 0:
                continue
            residue = (-pow(left, -1, modulus)) % modulus
            right = residue if residue else modulus
            if right <= left:
                right += ((left - right) // modulus + 1) * modulus
            while right <= limit:
                if right in vertex_set:
                    edge = (left, right)
                    edges.add(edge)
                right += modulus
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    return adjacency, len(edges)


def expected_endpoints(limit: int) -> list[int]:
    endpoints = [min(limit, 6)]
    colour_count = 1
    while 25 * (colour_count - 1) + 7 <= limit:
        endpoints.append(min(limit, 25 * colour_count + 6))
        colour_count += 1
    return list(dict.fromkeys(endpoints))


def greedy_record(
    endpoint: int, vertices: list[int], adjacency: dict[int, set[int]]
) -> list[object]:
    prefix = [vertex for vertex in vertices if vertex <= endpoint]
    benchmark = (endpoint + 18) // 25
    colours: dict[int, int] = {}
    for vertex in reversed(prefix):
        used = {
            colours[neighbour]
            for neighbour in adjacency[vertex]
            if neighbour in colours
        }
        colour = 0
        while colour in used:
            colour += 1
        colours[vertex] = colour
    vector = [colours[vertex] for vertex in prefix]
    used_count = max(vector, default=-1) + 1
    if used_count > benchmark:
        raise RuntimeError(
            f"descending first-fit used {used_count} colours at {endpoint}, "
            f"benchmark is {benchmark}"
        )
    for left in prefix:
        for right in adjacency[left]:
            if left < right <= endpoint and colours[left] == colours[right]:
                raise RuntimeError(f"invalid colour class at edge {left},{right}")
    return [endpoint, len(prefix), benchmark, vector]


def build_payload(limit: int) -> tuple[dict[str, object], int]:
    primes = sieve_primes(limit)
    vertices = eligible_vertices(limit, primes)
    adjacency, edge_count = modular_adjacency(limit, vertices, primes)
    records = [
        greedy_record(endpoint, vertices, adjacency)
        for endpoint in expected_endpoints(limit)
    ]
    return {"limit": limit, "vertices": vertices, "records": records}, edge_count


def canonical_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    payload, edge_count = build_payload(args.limit)
    encoded = canonical_bytes(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    print(f"limit={args.limit}")
    print(f"vertices={len(payload['vertices'])}")
    print(f"edges={edge_count}")
    print(f"records={len(payload['records'])}")
    print(f"bytes={len(encoded)}")
    print(f"sha256={hashlib.sha256(encoded).hexdigest()}")


if __name__ == "__main__":
    main()
