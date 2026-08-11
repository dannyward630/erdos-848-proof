#!/usr/bin/env python3
"""Adversarial schema controls for the all-N computational manifest."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_certificate.py"
MANIFEST = ROOT / "certificates" / "all-n-manifest-v1.json"


def load_checker() -> Any:
    spec = importlib.util.spec_from_file_location("all_n_certificate_checker", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load all-N checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode("ascii")


def expect_rejected(checker: Any, path: Path, label: str) -> None:
    try:
        checker.validate_manifest(path)
    except checker.CheckFailure:
        print(f"REJECTED {label}")
        return
    raise RuntimeError(f"manifest checker accepted negative control: {label}")


def main() -> int:
    checker = load_checker()
    valid, _digest = checker.validate_manifest(MANIFEST)
    print("ACCEPTED canonical manifest")

    temp_parent = ROOT / "tmp"
    temp_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="all-n-manifest-controls-", dir=temp_parent
    ) as raw_temp:
        temp = Path(raw_temp)

        def write(name: str, value: Any) -> Path:
            path = temp / name
            path.write_bytes(canonical(value))
            return path

        reordered = {"statement": valid["statement"], "version": valid["version"]}
        reordered.update(
            (key, value)
            for key, value in valid.items()
            if key not in {"statement", "version"}
        )
        expect_rejected(checker, write("reordered.json", reordered), "reordered keys")

        boolean_version = copy.deepcopy(valid)
        boolean_version["version"] = True
        expect_rejected(
            checker, write("boolean-version.json", boolean_version), "Boolean integer"
        )

        float_path = temp / "float-version.json"
        float_path.write_bytes(canonical(valid).replace(b'"version": 1', b'"version": 1.0', 1))
        expect_rejected(checker, float_path, "floating-point integer")

        extra = copy.deepcopy(valid)
        extra["unexpected"] = "field"
        expect_rejected(checker, write("extra.json", extra), "extra field")

        duplicate_path = temp / "duplicate.json"
        duplicate_path.write_bytes(
            canonical(valid).replace(
                b'{\n  "version": 1,',
                b'{\n  "version": 1,\n  "version": 1,',
                1,
            )
        )
        expect_rejected(checker, duplicate_path, "duplicate key")

        escaping = copy.deepcopy(valid)
        escaping["statement"]["path"] = "../docs/problem-spec.md"
        expect_rejected(checker, write("escape.json", escaping), "path escape")

        wrong_digest = copy.deepcopy(valid)
        wrong_digest["statement"]["sha256"] = "0" * 64
        expect_rejected(checker, write("digest.json", wrong_digest), "digest drift")

        gap = copy.deepcopy(valid)
        gap["coverage"][2]["lower"] += 1
        expect_rejected(checker, write("gap.json", gap), "coverage gap")

        missing_stage = copy.deepcopy(valid)
        missing_stage["stages"].pop()
        expect_rejected(checker, write("stage.json", missing_stage), "missing stage")

        symlink = temp / "statement-link.md"
        symlink.symlink_to(ROOT / "docs" / "problem-spec.md")
        symlinked = copy.deepcopy(valid)
        symlinked["statement"]["path"] = symlink.relative_to(ROOT).as_posix()
        expect_rejected(checker, write("symlink.json", symlinked), "symlink input")

    print("ALL ALL-N MANIFEST MUTATION CONTROLS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
