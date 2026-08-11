#!/usr/bin/env python3
"""Finish the exact batch leaf certificate from independently exported products."""

import hashlib
import sys
import time

import gmpy2


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: gcd_products PRIMORIAL.bin LARGE_PRODUCT.bin LIMIT")
    started = time.monotonic()
    primorial_raw = open(sys.argv[1], "rb").read()
    large_raw = open(sys.argv[2], "rb").read()
    limit = int(sys.argv[3])
    if not primorial_raw or not large_raw or limit < 2:
        raise SystemExit("empty product or invalid limit")
    primorial = gmpy2.mpz.from_bytes(primorial_raw, "big", signed=False)
    large_product = gmpy2.mpz.from_bytes(large_raw, "big", signed=False)
    if primorial <= 0 or large_product <= 0:
        raise SystemExit("nonpositive product")
    common = gmpy2.gcd(primorial, large_product)
    if common != 1:
        raise SystemExit(f"large factor leaf has a small divisor; gcd={common}")

    # Inject the certified small prime 2 into the large product.  The same
    # exact gcd must reject this one-factor corruption.
    mutated_common = gmpy2.gcd(primorial, large_product * 2)
    if mutated_common == 1:
        raise SystemExit("negative control failed: injected factor 2 was missed")

    print(f"primorial_sha256={hashlib.sha256(primorial_raw).hexdigest()}")
    print(f"large_product_sha256={hashlib.sha256(large_raw).hexdigest()}")
    print(f"primorial_bytes={len(primorial_raw)}")
    print(f"large_product_bytes={len(large_raw)}")
    print(f"sieve_limit={limit}")
    print(f"gmpy2_version={gmpy2.version()}")
    print(f"gmp_version={gmpy2.mp_version()}")
    print(f"large_primorial_gcd={common}")
    print(f"injected_factor_control_gcd={mutated_common}")
    print("negative_control=passed")
    print(f"elapsed_seconds={time.monotonic() - started:.3f}")
    print("BATCH FACTOR-LEAF CERTIFICATE PASSED")


if __name__ == "__main__":
    main()
