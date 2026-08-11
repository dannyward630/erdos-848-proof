# Independent ART-005 all-N replay receipt

## Scope

This receipt records an independent full-profile replay of
`ipitchford/erdos-848-all-n` at exact revision

```text
1afd7c722cae5ee7dd0fd1fde64427537394f749
```

on 2026-08-10. The authenticated explicit-threshold source was
`sources/cache/sothanaphan-2.64e17.pdf`, SHA-256

```text
8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f
```

The public release wrapper had 19 stages. This was the default full profile,
not `--positive-only`; mutation and sanitizer stages were enabled.

## Command

Run from `external/erdos-848-all-n`:

```sh
python3 -u audit/run_release_replay.py \
  --source-pdf \
  ../../sources/cache/sothanaphan-2.64e17.pdf \
  --jobs 4
```

The replay used CPython 3.9.6 and the system C++ compiler on arm64 macOS.

## Exact stage summary

```text
coverage-preflight                    0.240
lightweight-audit                     0.240
python-optimization-fail-closed       0.468
finite-original-positive             29.685
finite-original-mutations            63.998
finite-original-ubsan                19.367
finite-compact-build                  2.165
finite-compact-positive             444.945
finite-compact-diagonal-census       43.463
finite-compact-mutations             88.502
lower-p13-continuous               2986.179
lower-p17plus-and-base              382.599
lower-p17-census-mutations            4.763
low-p13-continuous                  785.627
low-p17plus-and-base                372.024
middle-p13                           49.313
middle-p17plus-and-base              80.796
high-threshold-numerics-and-source  169.220
coverage-postflight                   0.196
total_seconds                      5523.791
```

Exact final lines:

```text
PASS complete_all_n_local_replay profile=full stages=19 source_pdf_sha256=8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f
PASS release_manifest_postflight files=131 inventory=132 manifest_sha256=6f197f0d5bef00c97275915ee21dcf8891543eab54dda9312c4227bbde927573
PASS complete_fresh_extraction_release_replay files=131 manifest_sha256=6f197f0d5bef00c97275915ee21dcf8891543eab54dda9312c4227bbde927573
```

The full raw terminal stream was not separately redirected to a durable log;
the exact final stage table and decisive outputs above were captured directly
from the live PTY. A clean rerun is the authoritative way to reproduce the
receipt.

## Decisive certificate identities

```text
finite original certificate:
3380a6778d237a3fd2a1f01c7ea72292e470a845b09eea99beb66ca85434ba98

finite compact certificate:
9917ec4590f69efd8c6f7d30d54ecf5284e92f185ec70a4d14657acb02551b12

lower p=13 rows:
58498260302d6c45e2c965dc78843d0e6cea3722fee3e2d2829638c1143d2ab5

lower p=17 rows:
fcc0e45dc0c3a5b8c8935c93fe44f392bbef9fedfc22e2614510743fbbc11824

lower p>=29 rows:
9a5e4c0db4dfe905c6c65ad107e79e3ad6c11711041e23b13a4a55fc570759bc

lower no-outsider rows:
6350904a63ab798a4b82262c807ec352dfff8645a142986bb664702c5bae6806

low p=13 rows:
8e91da4b5ea840cd4f2a4c7cbbed0b6aad4e8b95ab8cf7ffc64f830b19f39c02

low p>=17 rows:
d5674d768789cc8d9fe9c931675be3c753f096306ba3bda9d624c1cc0f66dbe9

low no-outsider rows:
94fc3028544b36c6286f550045731893e146ffa1a2fb0c6911d38f5251e713b6

middle p=13 rows:
cb6be132fad245b9a7c7658100bc5db6513b617be41e6b0966ec4b632a96be42

middle p>=17 and no-outsider rows:
0897900002f65c1deb63612cca1f0e984e5fd37ad71b8686af7505de14d7134d

high-range numerical claims:
4726814d80fc63353a77c18bac8691bc917efd5ef1c7dcf10a14aed03674b215

closed range ledger:
b28760bca88b3f4a356f5212f5aa3711df00ee527606058a9aefc193e715ebe1
```

## Coverage reported by the postflight

```text
finite:  [1, 100000006]
lower:   [100000000, 1000000000]
low:     [1000000000, 1000000000000]
middle:  [1000000000000, 264000000000000000]
high:    [264000000000000000, infinity)
```

The finite/lower ranges overlap on `[100000000,100000006]`. The other
junctions share their displayed endpoints. The postflight reported
`PASS all_n_branch_coverage_is_gapless`.

## Independent strengthening outside the release wrapper

The release's lower-`p=13` generator and verifier share a seven-base
Miller--Rabin routine. This receipt does not treat that shared routine as an
independent primality proof. The authenticated factor transcript was
separately checked by `computations/check_p13_factor_primality.py`, which uses
an exact sieve and batch primorial-gcd certificate and no pseudoprime theorem.
Its deterministic receipt is `certificates/p13-factor-primality.json`,
SHA-256

```text
cb67a19e9edfc21206b6ec0c886bf6aa67b97a110296f7e20bf00bdf818cfc64
```

That strengthening must itself pass independent source and mutation review
before the lower-range DAG node is promoted.
