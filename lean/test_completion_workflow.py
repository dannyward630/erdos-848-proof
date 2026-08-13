#!/usr/bin/env python3
"""Negative controls for the strict ART-006 workflow receipt boundary."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

import validate_completion_workflow as validator


def reject(action: Callable[[], Any], label: str) -> None:
    try:
        action()
    except validator.WorkflowFailure:
        print(f"REJECTED {label}")
        return
    raise RuntimeError(f"workflow validator accepted negative control: {label}")


def main() -> int:
    expected = {
        "run_id": "31541505450",
        "run_attempt": 1,
        "head_sha": "a" * 40,
        "runner_name": "isolated-art006",
    }
    handoff = {
        "schema": "erdos848-art006-workflow-handoff-v1",
        "status": "initialized-before-lean-completion-gate",
        **expected,
        "runner_os": "Windows",
        "runner_arch": "X64",
        "receipt_relative": "receipt",
    }
    with tempfile.TemporaryDirectory(prefix="erdos848-workflow-controls-") as raw:
        path = Path(raw) / "handoff.json"
        path.write_bytes(validator.gate.canonical_json(handoff))
        validator.validate_handoff(path, expected)
        print("ACCEPTED canonical strictly typed handoff")

        malformed = copy.deepcopy(handoff)
        malformed["run_attempt"] = True
        path.write_bytes(validator.gate.canonical_json(malformed))
        reject(lambda: validator.validate_handoff(path, expected), "Boolean run attempt")

        malformed = copy.deepcopy(handoff)
        malformed["unexpected"] = "extension"
        path.write_bytes(validator.gate.canonical_json(malformed))
        reject(lambda: validator.validate_handoff(path, expected), "extra handoff key")

        path.write_text(json.dumps(handoff), encoding="ascii")
        reject(lambda: validator.validate_handoff(path, expected), "noncanonical JSON")

        duplicate = validator.gate.canonical_json(handoff).decode("ascii").replace(
            '  "schema": ', '  "schema": "duplicate",\n  "schema": ', 1
        )
        path.write_text(duplicate, encoding="ascii")
        reject(lambda: validator.validate_handoff(path, expected), "duplicate JSON key")

        success_path = Path(raw) / "success.json"
        success = {
            "schema": "erdos848-art006-workflow-success-v1",
            **expected,
            "receipt_sha256": "b" * 64,
        }
        success_path.write_bytes(validator.gate.canonical_json(success))
        validator.validate_success(success_path, expected, "b" * 64)
        print("ACCEPTED canonical strictly typed success handoff")

        malformed = copy.deepcopy(success)
        malformed["receipt_sha256"] = "c" * 64
        success_path.write_bytes(validator.gate.canonical_json(malformed))
        reject(
            lambda: validator.validate_success(success_path, expected, "b" * 64),
            "wrong receipt digest",
        )

    reject(lambda: validator.exact_int("30636", 30636, "count"), "numeric string")
    reject(lambda: validator.exact_int(True, 1, "version"), "Boolean receipt integer")
    reject(
        lambda: validator.exact_keys(
            {key: None for key in reversed(validator.RECEIPT_KEYS)},
            validator.RECEIPT_KEYS,
            "receipt",
        ),
        "reordered receipt keys",
    )
    reject(
        lambda: validator.exact_keys(
            {**{key: None for key in validator.RECEIPT_KEYS}, "extra": None},
            validator.RECEIPT_KEYS,
            "receipt",
        ),
        "extra receipt key",
    )
    print("ALL WORKFLOW RECEIPT MUTATION CONTROLS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
