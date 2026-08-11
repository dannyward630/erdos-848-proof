#!/usr/bin/env python3
"""Mutation controls for the independent prefix-certificate checker."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from check_prefix_certificate import CertificateError, validate_payload


def require_rejection(label: str, payload: object, expected: str) -> None:
    try:
        validate_payload(payload)
    except CertificateError as exc:
        if expected not in str(exc):
            raise SystemExit(
                f"wrong rejection for {label}: expected {expected!r}, got {exc!r}"
            ) from exc
        print(f"PASS rejected {label}: {exc}")
        return
    raise SystemExit(f"mutation was accepted: {label}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path)
    args = parser.parse_args()
    original = json.loads(args.certificate.read_text(encoding="ascii"))
    validate_payload(original)
    print("PASS unmodified certificate")

    mutated = copy.deepcopy(original)
    mutated["vertices"].pop()
    require_rejection("missing-vertex", mutated, "exact diagonal set")

    mutated = copy.deepcopy(original)
    mutated["vertices"][0] = float(mutated["vertices"][0])
    require_rejection("float-vertex", mutated, "strict JSON integers")

    mutated = {
        "records": copy.deepcopy(original["records"]),
        "vertices": copy.deepcopy(original["vertices"]),
        "limit": original["limit"],
    }
    require_rejection("reordered-top-level-keys", mutated, "top-level schema")

    mutated = copy.deepcopy(original)
    mutated["records"][1][1] += 1
    require_rejection("wrong-prefix-count", mutated, "wrong prefix vertex count")

    mutated = copy.deepcopy(original)
    mutated["records"][1][0] = float(mutated["records"][1][0])
    require_rejection("float-endpoint", mutated, "record scalars")

    mutated = copy.deepcopy(original)
    mutated["records"][1][1] = True
    require_rejection("boolean-prefix-count", mutated, "record scalars")

    mutated = copy.deepcopy(original)
    mutated["records"][1][2] = True
    require_rejection("boolean-benchmark", mutated, "record scalars")

    mutated = copy.deepcopy(original)
    record = next(record for record in mutated["records"] if record[1] > 0)
    record[3][0] = record[2]
    require_rejection("out-of-range-colour", mutated, "colour outside")

    mutated = copy.deepcopy(original)
    record = next(record for record in mutated["records"] if record[0] >= 56)
    prefix = mutated["vertices"][: record[1]]
    left_index = prefix.index(7)
    right_index = prefix.index(32)
    record[3][right_index] = record[3][left_index]
    require_rejection("same-colour-edge", mutated, "same-colour nonsquarefree pair")

    mutated = copy.deepcopy(original)
    mutated["records"][1][0] += 1
    require_rejection("altered-endpoint", mutated, "endpoint sequence")

    mutated = copy.deepcopy(original)
    mutated["records"][1][2] += 1
    require_rejection("altered-benchmark", mutated, "wrong benchmark")

    mutated = copy.deepcopy(original)
    mutated["records"].pop(len(mutated["records"]) // 2)
    require_rejection("coverage-gap", mutated, "record count")

    print("ALL PREFIX CHECKER MUTATION CONTROLS PASSED")


if __name__ == "__main__":
    main()
