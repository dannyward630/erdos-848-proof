# Source cache manifest

`sources/cache/` is intentionally ignored. `REPRODUCE.md` contains public
retrieval commands for every source listed below. The PDF digests identify the
exact bytes that were inspected. The four Erdős Problems HTML digests
identify the snapshots inspected on 10--11 August 2026; those live responses
contain server-generated fields, so a new `curl` is not expected to reproduce
their raw hashes. Re-audit the visible statement/history and keep changed HTML
bytes as a separately dated snapshot.

| File | SHA-256 | Role |
|---|---|---|
| `erdos-1992-er92b.pdf` | `bbf669b3ef3885fffa50830845aa6633c1673476462fb0e6a6f67a37478d3ff9` | Original Problem 23 scan |
| `erdosproblems-848.html` | `dd32e3ca0adf2a9563fee03975c487e424aecff9fa7964cf53427a1e85ac5055` | Maintained statement/status snapshot |
| `erdosproblems-848-latex.html` | `492d3c24fedcd794f7a6e5d2a4978640855d027fa0dce6659a5d21fc5fe22ba0` | Maintained LaTeX statement snapshot |
| `erdosproblems-848-history.html` | `74950ff91bf522133fe3447ae98a47a7114a354e11c68f3cccf6316ad87edd8d` | Revision-history snapshot |
| `erdosproblems-848-discussion.html` | `efaeee6bd0ab9eef83e6a40753bca5a42650f2fa90d05fdf1e6174de46071a9e` | Discussion snapshot |
| `sawhney-problem-848.pdf` | `112deb12350ea812e5a8e140f2df00b72d2a848c5dc0d2000de738e948e637ba` | Sufficiently-large proof note |
| `openai-early-science-gpt5.pdf` | `5295c9c3584250c6bbea5845309c0659183362ba1eccc351a665f6f2f3675ab7` | Archival, non-load-bearing context/report containing Sawhney appendix |
| `arxiv-2511.16072.pdf` | `412e2ddc5f7f2141cb7481f83e9d41fbc239dbcbe34395b18caab748aaeb5e52` | Archival, non-load-bearing related report; audit pending |
| `sothanaphan-exp1958.pdf` | `12506fc5c9d63c0ae9337d216917cfba0dbe8ac13dfb6eed062c3bb8ef5dddef` | Archival, non-load-bearing threshold note; audit pending |
| `sothanaphan-exp1420.pdf` | `dba5e022533362affff3019a5ad8c806c6a08dd149b24c9808f4e6c235f91ca7` | Archival, non-load-bearing threshold note; audit pending |
| `sothanaphan-7e17.pdf` | `a5d3f686e524d8e04e33dc87796db42c975949acaabcd73cb2a008b8c3409c66` | Archival, non-load-bearing threshold note; audit pending |
| `sothanaphan-3.3e17.pdf` | `a9f1970fb84d8e4a92778f506b6f4be20cc4c26c80f0c3f086964cd81d5859a8` | Archival, non-load-bearing threshold note; audit pending |
| `sothanaphan-2.64e17.pdf` | `8162113a571dc2283fc77de1cdf36e7abf424eeec952aa27cf82a4f44b3a796f` | Explicit-threshold theorem, independently audited |
| `hanson-1972-product-primes.pdf` | `ba350b2ce48e0ddb0751d8a60bcfe310683bc88df4fcf1b6a91029297688689c` | Denis Hanson's proof of the \(1.25506x/\log x\) prime-count upper bound used by ART-005 |

HTML pages may change even when the mathematical content does not, including
through access timestamps or anti-forgery tokens. Their listed hashes are
snapshot identities, not a clean-checkout pass condition. If a fresh retrieval
differs, keep it separate, record the access date, compare the exact statement
and status fields, and only then update this manifest.
