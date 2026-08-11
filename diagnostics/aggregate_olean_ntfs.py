#!/usr/bin/env python3
"""Aggregate exact per-file NTFS allocation reports from Windows runners."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_MANIFEST_SHA256 = (
    "3cbde25db4c5eac8209dd428cc5d95eab648766023db87418c8ea8c66353c527"
)
EXPECTED_ARCHIVE_BYTES = 32_249_316_999
EXPECTED_LOGICAL_BYTES = 129_476_102_424
EXPECTED_MODULES = 30_638
GIB = 1024**3
GATE_PHYSICAL_MEMORY_BYTES = 64 * GIB
GATE_FREE_STORAGE_BYTES = 200 * GIB


def load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("ntfs-parts-*.json"))
    if not paths:
        raise SystemExit(f"no reports found beneath {root}")
    reports = []
    for path in paths:
        with path.open("r", encoding="utf-8-sig") as handle:
            report = json.load(handle)
        if report.get("schema_version") != 1:
            raise SystemExit(f"unexpected schema in {path}")
        if report.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256:
            raise SystemExit(f"manifest mismatch in {path}")
        reports.append(report)
    return reports


def scratch_free(snapshot: dict[str, Any], drive: str) -> int:
    matches = [
        int(disk["free_bytes"])
        for disk in snapshot["fixed_disks"]
        if disk["device_id"].casefold() == drive.casefold()
    ]
    if len(matches) != 1:
        raise SystemExit(f"cannot resolve drive {drive} in snapshot")
    return matches[0]


def all_snapshots(report: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = [report["initial_snapshot"]]
    for part in report["parts"]:
        snapshots.extend(part["snapshots"])
        snapshots.append(part["cleanup_snapshot"])
    snapshots.append(report["final_snapshot"])
    return snapshots


def pagefile_totals(snapshot: dict[str, Any]) -> dict[str, int]:
    keys = ("allocated_base_bytes", "current_usage_bytes", "peak_usage_bytes")
    return {
        key: sum(int(pagefile[key]) for pagefile in snapshot["pagefiles"])
        for key in keys
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    reports = load_reports(args.report_root)
    parts = [part for report in reports for part in report["parts"]]
    part_numbers = [int(part["part"]) for part in parts]
    if sorted(part_numbers) != list(range(1, 76)):
        raise SystemExit(f"part coverage is not exactly 1..75: {sorted(part_numbers)}")
    if len(part_numbers) != len(set(part_numbers)):
        raise SystemExit("duplicate part report")

    totals = {
        "archives": len(parts),
        "archive_bytes": sum(int(part["archive_bytes"]) for part in parts),
        "files": sum(int(part["file_count"]) for part in parts),
        "logical_bytes": sum(int(part["logical_bytes"]) for part in parts),
        "ntfs_allocated_bytes": sum(
            int(part["ntfs_allocated_bytes"]) for part in parts
        ),
    }
    if totals["archives"] != 75:
        raise SystemExit("archive count mismatch")
    if totals["archive_bytes"] != EXPECTED_ARCHIVE_BYTES:
        raise SystemExit(f"archive byte mismatch: {totals['archive_bytes']}")
    if totals["files"] != EXPECTED_MODULES:
        raise SystemExit(f"module count mismatch: {totals['files']}")
    if totals["logical_bytes"] != EXPECTED_LOGICAL_BYTES:
        raise SystemExit(f"logical byte mismatch: {totals['logical_bytes']}")
    totals["ntfs_allocation_ratio"] = (
        totals["ntfs_allocated_bytes"] / totals["logical_bytes"]
    )

    worker_summaries = []
    all_initial_free = []
    all_physical_memory = []
    all_cluster_sizes = []
    for report in reports:
        runner = report["runner"]
        drive = runner["scratch_drive"]
        snapshots = all_snapshots(report)
        free_values = [scratch_free(snapshot, drive) for snapshot in snapshots]
        page_values = [pagefile_totals(snapshot) for snapshot in snapshots]
        initial_page = pagefile_totals(report["initial_snapshot"])
        final_page = pagefile_totals(report["final_snapshot"])
        initial_free = scratch_free(report["initial_snapshot"], drive)
        all_initial_free.append(initial_free)
        all_physical_memory.append(int(runner["physical_memory_bytes"]))
        all_cluster_sizes.append(int(runner["scratch_cluster_bytes"]))
        worker_summaries.append(
            {
                "range": report["range"],
                "runner_name": runner["name"],
                "image_os": runner["image_os"],
                "image_version": runner["image_version"],
                "physical_memory_bytes": int(runner["physical_memory_bytes"]),
                "logical_processors": int(runner["logical_processors"]),
                "scratch_drive": drive,
                "scratch_filesystem": runner["scratch_filesystem"],
                "scratch_cluster_bytes": int(runner["scratch_cluster_bytes"]),
                "scratch_capacity_bytes": int(runner["scratch_capacity_bytes"]),
                "initial_scratch_free_bytes": initial_free,
                "minimum_scratch_free_bytes_seen": min(free_values),
                "maximum_transient_scratch_consumption_bytes": initial_free
                - min(free_values),
                "pagefile_initial": initial_page,
                "pagefile_final": final_page,
                "pagefile_allocated_change_bytes": final_page[
                    "allocated_base_bytes"
                ]
                - initial_page["allocated_base_bytes"],
                "pagefile_max_current_usage_bytes": max(
                    page["current_usage_bytes"] for page in page_values
                ),
                "pagefile_max_peak_usage_bytes": max(
                    page["peak_usage_bytes"] for page in page_values
                ),
            }
        )

    if any(report["runner"]["scratch_filesystem"] != "NTFS" for report in reports):
        raise SystemExit("at least one worker did not use NTFS")
    if len(set(all_cluster_sizes)) != 1:
        raise SystemExit(f"workers used different NTFS cluster sizes: {all_cluster_sizes}")

    minimum_observed_initial_free = min(all_initial_free)
    minimum_observed_physical_memory = min(all_physical_memory)
    compressed_only_fits_observed = (
        totals["ntfs_allocated_bytes"] <= minimum_observed_initial_free
    )
    compressed_plus_zips_fits_observed = (
        totals["ntfs_allocated_bytes"] + totals["archive_bytes"]
        <= minimum_observed_initial_free
    )
    gate_resources_met = (
        minimum_observed_physical_memory >= GATE_PHYSICAL_MEMORY_BYTES
        and minimum_observed_initial_free >= GATE_FREE_STORAGE_BYTES
    )

    combined = {
        "schema_version": 1,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "github_run_ids": sorted(
            {str(report["github"]["run_id"]) for report in reports}
        ),
        "worker_count": len(reports),
        "totals": totals,
        "observed_standard_windows_2025": {
            "ntfs_cluster_bytes": all_cluster_sizes[0],
            "minimum_initial_scratch_free_bytes": minimum_observed_initial_free,
            "minimum_physical_memory_bytes": minimum_observed_physical_memory,
            "compressed_oleans_fit_initial_scratch_free": compressed_only_fits_observed,
            "compressed_oleans_plus_all_release_zips_fit_initial_scratch_free": compressed_plus_zips_fits_observed,
            "meets_completion_gate_64_gib_ram_and_200_gib_free": gate_resources_met,
        },
        "pagefile_accounting": {
            "method": (
                "Per-file OLean allocation is summed only with "
                "GetCompressedFileSizeW after explicit NTFS compression. "
                "Pagefile allocation and usage are reported separately per worker "
                "from Win32_PageFileUsage and are never included in the OLean sum."
            ),
            "workers": worker_summaries,
        },
        "parts": sorted(parts, key=lambda part: int(part["part"])),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(combined, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("NTFS OLEAN AGGREGATE PASSED")
    print(f"archives={totals['archives']}")
    print(f"files={totals['files']}")
    print(f"logical_bytes={totals['logical_bytes']}")
    print(f"ntfs_allocated_bytes={totals['ntfs_allocated_bytes']}")
    print(f"ntfs_allocation_ratio={totals['ntfs_allocation_ratio']:.9f}")
    print(f"archive_bytes={totals['archive_bytes']}")
    print(f"minimum_initial_scratch_free_bytes={minimum_observed_initial_free}")
    print(f"minimum_physical_memory_bytes={minimum_observed_physical_memory}")
    print(f"compressed_oleans_fit={compressed_only_fits_observed}")
    print(f"compressed_oleans_plus_zips_fit={compressed_plus_zips_fits_observed}")
    print(f"completion_gate_resources_met={gate_resources_met}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
