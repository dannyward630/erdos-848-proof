#!/usr/bin/env python3
"""Third, naive oracle: exhaust every eligible subset through N=100."""

from __future__ import annotations

import argparse
from itertools import combinations
from math import isqrt


def is_squarefree_naive(value: int) -> bool:
    return all(value % (divisor * divisor) for divisor in range(2, isqrt(value) + 1))


def admissible(values: tuple[int, ...]) -> bool:
    return all(
        not is_squarefree_naive(left * right + 1)
        for left in values
        for right in values
    )


def maximum_size(vertices: list[int]) -> int:
    for size in range(len(vertices), -1, -1):
        for selected in combinations(vertices, size):
            if admissible(selected):
                return size
    raise AssertionError("empty set must be admissible")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        raise SystemExit("this deliberately naive oracle requires 1 <= limit <= 100")
    vertices = [
        value
        for value in range(1, args.limit + 1)
        if not is_squarefree_naive(value * value + 1)
    ]
    for endpoint in range(1, args.limit + 1):
        prefix = [value for value in vertices if value <= endpoint]
        maximum = maximum_size(prefix)
        benchmark = (endpoint + 18) // 25
        if maximum != benchmark:
            raise SystemExit(
                f"counterexample at N={endpoint}: omega={maximum}, benchmark={benchmark}"
            )
    print(
        f"VERIFIED exhaustive subsets for every 1 <= N <= {args.limit}; "
        f"eligible_vertices={len(vertices)}"
    )


if __name__ == "__main__":
    main()
