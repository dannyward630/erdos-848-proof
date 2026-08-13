#!/usr/bin/env python3
"""Bounded positive and fail-closed tests for the checkpoint pilot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "lean_checkpoint_plan.py"
SPEC = importlib.util.spec_from_file_location("e848_checkpoint", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load checkpoint module")
checkpoint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checkpoint)


def run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.stdout.strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_bytes(checkpoint.canonical_json(value))


def expect_rejected(label: str, action) -> None:
    try:
        action()
    except (checkpoint.CheckpointFailure, OSError, ValueError, IndexError):
        print(f"REJECTED {label}")
        return
    raise RuntimeError(f"checkpoint verifier accepted negative control: {label}")


def source_lock(source: Path) -> dict[str, object]:
    revision = run(["git", "rev-parse", "HEAD"], source)
    tree = run(["git", "rev-parse", "HEAD^{tree}"], source)
    lean_tree = run(["git", "rev-parse", "HEAD:lean4"], source)
    return {
        "version": 1,
        "status": "unverified-pending-clean-replay",
        "upstream": {
            "url": "https://example.invalid/synthetic.git",
            "revision": revision,
            "tree": tree,
            "lean_tree": lean_tree,
        },
        "toolchain": {
            "lean": "leanprover/lean4:v4.30.0-rc2",
            "lean_commit": "3dc1a088b6d2d8eafe25a7cd7ec7b58d731bd7cc",
            "lean_toolchain_sha256": digest(source / "lean4/lean-toolchain"),
            "lake_manifest_sha256": digest(source / "lean4/lake-manifest.json"),
            "lakefile_sha256": digest(source / "lean4/lakefile.toml"),
            "mathlib_revision": "54e71fa9173471d591658f5380c46aaf050bbaae",
        },
        "sources": {},
        "endpoint": {},
        "root_sources": {},
        "allowed_axioms": [],
        "minimum_host": {},
    }


def seal_args(plan: Path, source: Path, lock: Path, index: int, assets: Path,
              parents: list[Path]) -> argparse.Namespace:
    return argparse.Namespace(
        plan=plan,
        source_root=source,
        lock=lock,
        segment_index=index,
        asset_root=assets,
        parent_root=parents,
        memory_mib=checkpoint.REQUIRED_MEMORY_MIB,
        runner_os=checkpoint.REQUIRED_RUNNER_OS,
        runner_arch=checkpoint.REQUIRED_RUNNER_ARCH,
        lean_version=(
            "Lean (version 4.30.0-rc2, x86_64-w64-windows-gnu, commit "
            f"{checkpoint.REQUIRED_LEAN_COMMIT}, Release)"
        ),
        output=assets / "receipt.json",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="e848-checkpoint-tests-") as raw:
        base = Path(raw)
        source = base / "source"
        (source / "lean4/Erdos848").mkdir(parents=True)
        (source / "lean4/lean-toolchain").write_text(
            "leanprover/lean4:v4.30.0-rc2\n", encoding="ascii")
        (source / "lean4/lake-manifest.json").write_text("{}\n", encoding="ascii")
        (source / "lean4/lakefile.toml").write_text("name = \"synthetic\"\n", encoding="ascii")
        base_source = "import Mathlib\n\nnamespace Erdos848\ndef base : Nat := 1\nend Erdos848\n"
        target_source = "import Erdos848.Base\n\nnamespace Erdos848\ntheorem target : base = 1 := rfl\nend Erdos848\n"
        (source / "lean4/Erdos848/Base.lean").write_text(base_source, encoding="utf-8")
        (source / "lean4/Erdos848/Target.lean").write_text(target_source, encoding="utf-8")
        run(["git", "init", "-q"], source)
        run(["git", "config", "user.name", "Checkpoint Test"], source)
        run(["git", "config", "user.email", "checkpoint@example.invalid"], source)
        run(["git", "add", "lean4"], source)
        run(["git", "commit", "-q", "-m", "synthetic source"], source)

        lock_path = base / "source-lock.json"
        write_json(lock_path, source_lock(source))
        plan_path = base / "plan.json"
        plan = checkpoint.generate_plan(source, lock_path, "Erdos848.Target", 1)
        write_json(plan_path, plan)
        checkpoint.verify_plan(plan_path, source, lock_path)
        assert len(plan["segments"]) == 2
        assert plan["segments"][0]["parents"] == []
        assert plan["segments"][1]["parents"] == [0]
        print("ACCEPTED canonical two-segment source plan")

        assets0 = base / "assets0"
        olean0 = assets0 / "oleans/Erdos848/Base.olean"
        olean0.parent.mkdir(parents=True)
        olean0.write_bytes(b"synthetic source-built base olean")
        checkpoint.seal_receipt(seal_args(plan_path, source, lock_path, 0, assets0, []))
        checkpoint.verify_receipt(plan_path, assets0, [], 0)

        assets1 = base / "assets1"
        olean1 = assets1 / "oleans/Erdos848/Target.olean"
        olean1.parent.mkdir(parents=True)
        olean1.write_bytes(b"synthetic source-built child olean")
        checkpoint.seal_receipt(seal_args(plan_path, source, lock_path, 1, assets1, [assets0]))
        checkpoint.verify_receipt(plan_path, assets1, [assets0], 1)
        print("ACCEPTED genesis-anchored child receipt")

        noncanonical = base / "plan-noncanonical.json"
        noncanonical.write_text(json.dumps(plan), encoding="ascii")
        expect_rejected("noncanonical plan bytes",
                        lambda: checkpoint.verify_plan(noncanonical, source, lock_path))

        boolean_plan = copy.deepcopy(plan)
        boolean_plan["segments"][0]["index"] = False
        boolean_path = base / "plan-boolean.json"
        write_json(boolean_path, boolean_plan)
        expect_rejected("Boolean segment index",
                        lambda: checkpoint.verify_plan(boolean_path, source, lock_path))

        wrong_parent = copy.deepcopy(plan)
        wrong_parent["segments"][1]["parents"] = []
        wrong_parent_path = base / "plan-parent.json"
        write_json(wrong_parent_path, wrong_parent)
        expect_rejected("omitted dependency parent",
                        lambda: checkpoint.verify_plan(wrong_parent_path, source, lock_path))

        reordered = copy.deepcopy(plan)
        reordered = {"status": reordered["status"], "schema": reordered["schema"],
                     **{key: value for key, value in reordered.items()
                        if key not in {"status", "schema"}}}
        reordered_path = base / "plan-reordered.json"
        write_json(reordered_path, reordered)
        expect_rejected("reordered plan keys",
                        lambda: checkpoint.verify_plan(reordered_path, source, lock_path))

        (source / "lean4/Erdos848/Base.lean").write_text(base_source + "-- drift\n",
                                                          encoding="utf-8")
        expect_rejected("dirty or drifted source",
                        lambda: checkpoint.verify_plan(plan_path, source, lock_path))
        (source / "lean4/Erdos848/Base.lean").write_text(base_source, encoding="utf-8")

        original_receipt = checkpoint.exact_json(assets1 / "receipt.json")
        bad_receipt = copy.deepcopy(original_receipt)
        bad_receipt["parents"][0]["receipt_sha256"] = "0" * 64
        write_json(assets1 / "receipt.json", bad_receipt)
        expect_rejected("mutated parent receipt binding",
                        lambda: checkpoint.verify_receipt(plan_path, assets1, [assets0], 1))
        write_json(assets1 / "receipt.json", original_receipt)

        original_parent_receipt = checkpoint.exact_json(assets0 / "receipt.json")
        for label, field, value in (
            ("unaudited compile flags", ("command", "compile_flags"), ["--trust=999"]),
            ("unaudited memory cap", ("command", "memory_mib"), 1),
            ("unaudited runner OS", ("environment", "runner_os"), "synthetic"),
            ("unaudited Lean runtime", ("environment", "lean_version"), "not Lean"),
        ):
            altered = copy.deepcopy(original_parent_receipt)
            altered[field[0]][field[1]] = value
            write_json(assets0 / "receipt.json", altered)
            expect_rejected(
                label,
                lambda: checkpoint.verify_receipt(plan_path, assets0, [], 0),
            )
        write_json(assets0 / "receipt.json", original_parent_receipt)
        counterfeit_parent = copy.deepcopy(original_parent_receipt)
        counterfeit_parent["plan_sha256"] = "0" * 64
        write_json(assets0 / "receipt.json", counterfeit_parent)
        counterfeit_child = copy.deepcopy(original_receipt)
        counterfeit_child["parents"][0]["receipt_sha256"] = digest(
            assets0 / "receipt.json")
        write_json(assets1 / "receipt.json", counterfeit_child)
        expect_rejected("self-consistent counterfeit parent chain",
                        lambda: checkpoint.verify_receipt(plan_path, assets1, [assets0], 1))
        write_json(assets0 / "receipt.json", original_parent_receipt)
        write_json(assets1 / "receipt.json", original_receipt)

        olean1.write_bytes(b"mutated child olean")
        expect_rejected("mutated child OLean",
                        lambda: checkpoint.verify_receipt(plan_path, assets1, [assets0], 1))
        olean1.write_bytes(b"synthetic source-built child olean")

        extra = assets1 / "unexpected.txt"
        extra.write_text("unexpected\n", encoding="ascii")
        expect_rejected("unexpected checkpoint file",
                        lambda: checkpoint.verify_receipt(plan_path, assets1, [assets0], 1))
        extra.unlink()

        link = assets1 / "olean-link"
        link.symlink_to(olean1)
        expect_rejected("symlink in checkpoint tree",
                        lambda: checkpoint.verify_receipt(plan_path, assets1, [assets0], 1))
        link.unlink()

        expect_rejected("missing parent artifact",
                        lambda: checkpoint.verify_receipt(plan_path, assets1, [], 1))
        expect_rejected("parent supplied to genesis",
                        lambda: checkpoint.verify_receipt(plan_path, assets0, [assets0], 0))
        checkpoint.verify_receipt(plan_path, assets1, [assets0], 1)

    print("ALL LEAN CHECKPOINT PILOT MUTATION CONTROLS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
