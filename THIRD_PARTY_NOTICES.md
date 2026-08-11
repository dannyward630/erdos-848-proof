# Third-party notices

This repository does not vendor the decisive third-party repositories or
source papers. `REPRODUCE.md` retrieves them at exact revisions or hashes.

## ART-005

The structural and finite-certificate proof is based on
[`ipitchford/erdos-848-all-n`](https://github.com/ipitchford/erdos-848-all-n)
at commit `1afd7c722cae5ee7dd0fd1fde64427537394f749`. That repository declares
CC0 1.0 Universal. This project records a correction to one prose
normalization step as FL-013; it does not change ART-005's certificate rows.

## ART-006

The optional formal-verification route interoperates with
[`crabsatellite/erdos-848-squarefree-product`](https://github.com/crabsatellite/erdos-848-squarefree-product)
at commit `ede0151a35c86b6395cf67dd034811d22a92c7ba`. Its Lean sources,
verification scripts, machine-readable proof metadata, and repository
documentation are licensed under Apache-2.0; its manuscript is CC BY 4.0.

`lean/Erdos848Completion/PublicationAxiomAudit.lean` adapts and extends the
upstream publication axiom list, and `lean/Erdos848Completion/Final.lean`
provides this repository's literal positive-$N$ wrapper. Both files are
distributed under Apache-2.0 and identify the immutable upstream revision in
`lean/source-lock.json`.

## Papers and public pages

The cited Erdős--Sárközy, Sawhney, Sothanaphan, and Hanson papers and the
Erdős Problems pages remain subject to their authors' and publishers' terms.
Only bibliographic metadata, short mathematical summaries, and cryptographic
identities are tracked here. Downloaded copies live in ignored local cache
directories and are not part of the public repository snapshot.
