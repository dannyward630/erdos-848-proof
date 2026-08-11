#!/usr/bin/env python3
"""Create a syntax-valid base certificate bad only at endpoint 401."""

import gzip
import hashlib
import struct
import sys

EXPECTED_SOURCE_SHA256 = (
    "3380a6778d237a3fd2a1f01c7ea72292e470a845b09eea99beb66ca85434ba98"
)
EXPECTED_MUTANT_SHA256 = (
    "735a1af16019f98dff145a6655eec331917cbcfe5e4eb023fae4c2e45844e2ae"
)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: mutate SOURCE.gz OUTPUT.gz")
    source, output = sys.argv[1:]
    source_digest = sha256_file(source)
    if source_digest != EXPECTED_SOURCE_SHA256:
        raise SystemExit(
            f"source digest mismatch: expected {EXPECTED_SOURCE_SHA256}, "
            f"got {source_digest}"
        )
    with gzip.open(source, "rb") as stream:
        raw = stream.read()
    if raw[:8] != b"E848D1\0\0":
        raise SystemExit("bad magic")
    (endpoint_count,) = struct.unpack_from("<I", raw, 8)
    if endpoint_count != 4000:
        raise SystemExit("bad endpoint count")

    position = 12
    records: list[list[tuple[int, int]]] = []
    original_colour: dict[int, int] = {}
    colour18_after_402 = None
    for index in range(1, endpoint_count + 1):
        (count,) = struct.unpack_from("<I", raw, position)
        position += 4
        updates: list[tuple[int, int]] = []
        for _ in range(count):
            vertex, colour = struct.unpack_from("<IH", raw, position)
            position += 6
            updates.append((vertex, colour))
            original_colour[vertex] = colour
        if index == 401:
            if original_colour.get(382) != 15:
                raise SystemExit("canonical anchor 382 is not in colour 15")
            if original_colour.get(18) == 15:
                raise SystemExit("vertex 18 already has target colour")
        if index == 402:
            colour18_after_402 = original_colour.get(18)
        records.append(updates)
    if position != len(raw):
        raise SystemExit("trailing decompressed data")
    if colour18_after_402 is None:
        raise SystemExit("vertex 18 is uncoloured at endpoint 402")

    # 382*18+1 = 6877 = 13*23^2.  Endpoint 401 therefore becomes improper.
    records[400].append((18, 15))
    # Restore the original endpoint-402 state so all later endpoint states and
    # the final base state are bit-for-bit semantically unchanged.
    records[401].append((18, colour18_after_402))

    payload = bytearray(raw[:12])
    for updates in records:
        payload += struct.pack("<I", len(updates))
        for vertex, colour in updates:
            payload += struct.pack("<IH", vertex, colour)
    with open(output, "wb") as output_handle:
        with gzip.GzipFile(
            filename="erdos848_colour_delta_endpoint401_bad.bin",
            mode="wb",
            fileobj=output_handle,
            mtime=0,
        ) as stream:
            stream.write(payload)

    mutant_digest = sha256_file(output)
    if mutant_digest != EXPECTED_MUTANT_SHA256:
        raise SystemExit(
            f"mutant digest mismatch: expected {EXPECTED_MUTANT_SHA256}, "
            f"got {mutant_digest}"
        )
    print(f"source_sha256={source_digest}")
    print(f"mutant_sha256={mutant_digest}")
    print(f"original_colour18_after_402={colour18_after_402}")
    print("mutation_endpoint=401 vertex=18 colour=15 conflict=382*18+1=13*23^2")


if __name__ == "__main__":
    main()
