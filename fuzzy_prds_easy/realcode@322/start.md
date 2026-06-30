## Product Requirement Document

# Compact Token Issuance and Verification Service

## Project Goal

Build a library that issues and verifies **compact, URL-safe security tokens** that carry a set of assertions ("claims") about a subject. The library must let a caller:

- Describe and resolve **signature-algorithm metadata** by name.
- **Serialize** an unsecured token (no signature) into the canonical compact wire format.
- **Build** a claims set (registered + arbitrary custom claims) and round-trip it through serialization and parsing.
- **Sign** a token with a keyed-MAC algorithm and later **verify** it, recovering header and body.
- Optionally **compress** the body before signing and transparently decompress it on parse.
- **Parse** an arbitrary token, recovering the declared algorithm and the body.
- **Parse with a required shape** (signed vs. unsigned, claims vs. plaintext) and reject mismatches.
- Enforce **required claims** and **time-based validity** (expiration / not-before).
- **Reject malformed input and forgery attempts** with precise, language-neutral error categories.

The observable contract is a line-oriented `key=value` stdout stream produced by a thin adapter around the library. Every behavior below is specified purely as *input → output*.

## Background & Problem

Distributed systems need a way to pass trustworthy, self-contained assertions between parties without a shared session store. A compact token packs three dot-separated, base64url-encoded segments — a **header** (declaring the algorithm), a **body** (the payload or claims), and a **signature** — into a single ASCII string safe for use in URLs and HTTP headers.

The hard parts are not the happy paths but the guarantees around them:

- The wire format must be **byte-for-byte reproducible** so independent implementations interoperate.
- Parsing untrusted input must **fail safe**: every structurally or semantically invalid token must map to a *specific, predictable* failure category, never an ambiguous crash.
- The verifier must **resist algorithm-substitution forgery**, where an attacker re-signs a token using a public key's bytes as a MAC secret and hopes the verifier blindly accepts it.
- Claim-level policy (required claims, expiration, not-before) must be enforced **at parse time**, consistently.

This document specifies those behaviors as a deterministic input/output contract so that any implementation can be validated mechanically.

## Architecture & Engineering Constraints

- **Single process, single shot.** Each invocation reads exactly one JSON object from stdin and writes a deterministic, line-oriented `key=value` result to stdout. There is no network, no persistence, no clock-dependent output on the happy paths.
- **Stdin schema.** The input object always carries an `op` field selecting the operation. Remaining fields are operation-specific (documented per feature).
- **Stdout schema.** Output is zero or more `key=value` lines separated by `\n`. Lines are emitted in the order specified per feature. Registered claims use short keys (`iss`, `sub`, `aud`, `jti`, `exp`, `nbf`, `iat`); custom claims use the `claim.<name>` prefix and are emitted in ascending key order.
- **Keys.** Where a keyed-MAC secret is required it is provided as a base64url string and decoded to raw bytes; identical key + algorithm + body always yields an identical token.
- **Date claims** are normalized to **integer seconds since the Unix epoch** on output.
- **Algorithm names** are matched case-insensitively when resolving; the canonical `[a specific header constant (e.g., 'none','skip','null')]` algorithm's wire value is the lowercase string `[a specific header constant (e.g., 'none','skip','null')]`.
- **Error model (language-neutral).** Failures are rendered as a single primary line `error=<category>` optionally followed by a discriminator line (`reason=<...>` or `claim=<name>`). No host-language exception type names, stack traces, or runtime message text ever appear in output. The categories are:
  - `malformed` — structurally invalid token; `reason` ∈ {`period_count`, `missing_body`}.
  - `unsupported` — well-formed but wrong shape/key relationship; `reason` ∈ {`[valid error reasons related to shape mismatch]`, `[valid error reasons related to shape mismatch]`, `[valid error reasons related to shape mismatch]`, `algorithm_key_mismatch`}.
  - `signature_invalid` — signature verification failed or an unknown algorithm name was requested.
  - `expired` / `premature` — time-based validity failures (no wall-clock timestamps in output).
  - `incorrect_claim` / `missing_claim` — required-claim failures; carry a `claim=<name>` line.
  - `illegal_state` — an internally inconsistent build request.
  - `illegal_argument` — a null/blank input or an algorithm/key-type mismatch supplied at build time.
- **Adapter-only test surface.** The functional library is exercised unmodified; a thin dispatcher maps JSON ops onto the public API and renders results (including native errors) into the neutral contract above.
- **Reproducibility.** Asymmetric-key round-trips are non-deterministic by nature and are therefore only asserted via their *neutral failure category*, never via exact token bytes. All exact-token assertions use fixed MAC secrets.

## Core Features

### Feature 1: Signature-algorithm metadata

Resolve metadata for a signature algorithm by name.

- `op=algorithm_info`, field `name`: emit the canonical wire `value`, a human `description`, the `family`, a `jdk_standard` flag, and the family predicates `hmac` / `rsa` / `elliptic_curve`.
- `op=algorithm_for_name`, field `name`: case-insensitive resolution emitting `value` and `family`; an unrecognized name yields `error=signature_invalid`.

Example cases:

```json
{"op": "algorithm_info", "name": "HS256"}
```
→
```
value=HS256
description=HMAC using SHA-256
family=HMAC
jdk_standard=true
hmac=true
rsa=false
elliptic_curve=false
```

```json
{"op": "algorithm_info", "name": "RS256"}
```
→
```
value=RS256
description=RSASSA-PKCS-v1_5 using SHA-256
family=RSA
jdk_standard=true
hmac=false
rsa=true
elliptic_curve=false
```

```json
{"op": "algorithm_info", "name": "ES256"}
```
→
```
value=ES256
description=ECDSA using P-256 and SHA-256
family=Elliptic Curve
jdk_standard=false
hmac=false
rsa=false
elliptic_curve=true
```

```json
{"op": "algorithm_info", "name": "NONE"}
```
→
```
value=[a specific header constant (e.g., 'none','skip','null')]
description=No digital signature or MAC performed
family=None
jdk_standard=false
hmac=false
rsa=false
elliptic_curve=false
```

```json
{"op": "algorithm_for_name", "name": "hs256"}
```
→
```
value=HS256
family=HMAC
```

```json
{"op": "algorithm_for_name", "name": "foo"}
```
→
```
error=signature_invalid
```

### Feature 2: Unsecured token serialization

Serialize an unsecured token (algorithm `[a specific header constant (e.g., 'none','skip','null')]`) into the canonical compact form: header, base64url body, and an empty trailing signature segment. Output must match the specification example byte-for-byte.

- `op=build_plaintext`, field `payload` (string): emit `token=<compact string>`.

Example cases:

```json
{"op": "build_plaintext", "payload": "{\"iss\":\"joe\",\r\n \"exp\":1300819380,\r\n \"http://example.com/is_root\":true}"}
```
→
```
token=eyJhbGciOiJub25lIn0.eyJpc3MiOiJqb2UiLA0KICJleHAiOjEzMDA4MTkzODAsDQogImh0dHA6Ly9leGFtcGxlLmNvbS9pc19yb290Ijp0cnVlfQ.
```

```json
{"op": "build_plaintext", "payload": "Hello world!"}
```
→
```
token=eyJhbGciOiJub25lIn0.SGVsbG8gd29ybGQh.
```

### Feature 3: Claims round-trip

Build a claims token via registered-claim setters and arbitrary custom claims, then parse it back and recover the claim set. Setting a registered claim to null removes it. Date-valued claims are stored as integer seconds.

- `op=build_parse_claims`, field `claims` (object), optional `unset` (array of claim names to remove): emit recovered claims (registered first under short keys, then custom under `claim.<name>` sorted ascending).

Example cases:

```json
{"op": "build_parse_claims", "claims": {"iss": "Me"}}
```
→
```
iss=Me
```

```json
{"op": "build_parse_claims", "claims": {"iss": "Me", "sub": "Joe"}, "unset": ["iss"]}
```
→
```
sub=Joe
```

```json
{"op": "build_parse_claims", "claims": {"iss": "Iss", "sub": "Sub", "aud": "Aud", "jti": "Id"}}
```
→
```
iss=Iss
sub=Sub
aud=Aud
jti=Id
```

```json
{"op": "build_parse_claims", "claims": {"exp": 9999999999000, "nbf": 1000000000000, "iat": 1000000000000}}
```
→
```
exp=9999999999
nbf=1000000000
iat=1000000000
```

```json
{"op": "build_parse_claims", "claims": {"sub": "Joe", "role": "admin", "count": 5}}
```
→
```
sub=Joe
claim.count=5
claim.role=admin
```

### Feature 4: Keyed-MAC signing and verification

Sign with an HMAC-SHA algorithm using a fixed shared secret (deterministic output), then verify and recover the header algorithm and body. Works for claims bodies and arbitrary plaintext across the 256/384/512 family.

- `op=sign_verify`, fields `alg`, `key` (base64url secret), one of `claims` (object) or `payload` (string), optional `emit_token` (bool): emit optional `token=...` then `alg=<HS...>` then the recovered body/claims.

Example cases:

```json
{"op": "sign_verify", "alg": "HS256", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA", "claims": {"sub": "Joe"}, "emit_token": true}
```
→
```
token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJKb2UifQ.qs8rO_cGp7ctWsq-yGbVzJ-cjAhzdLh1jP0296AC9Ac
alg=HS256
sub=Joe
```

```json
{"op": "sign_verify", "alg": "HS384", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8w", "claims": {"sub": "Joe"}}
```
→
```
alg=HS384
sub=Joe
```

```json
{"op": "sign_verify", "alg": "HS512", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8PT4_QA", "payload": "Hello world!"}
```
→
```
alg=HS512
body=Hello world!
```

### Feature 5: Payload compression

Compress the body before signing and transparently decompress on parse; the header records the compression algorithm. Supports the two built-in codecs (`DEF`, `GZIP`) and a caller-supplied custom codec resolved by name during parsing.

- `op=compress_roundtrip`, fields `key`, `codec` (`DEF` | `GZIP` | `CUSTOM`), one of `claims` / `payload`: emit `calg=<codec>` then the recovered body/claims.

Example cases:

```json
{"op": "compress_roundtrip", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA", "codec": "DEF", "claims": {"sub": "Joe"}}
```
→
```
calg=DEF
sub=Joe
```

```json
{"op": "compress_roundtrip", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA", "codec": "GZIP", "claims": {"sub": "Joe"}}
```
→
```
calg=GZIP
sub=Joe
```

```json
{"op": "compress_roundtrip", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA", "codec": "CUSTOM", "claims": {"sub": "Joe"}}
```
→
```
calg=CUSTOM
sub=Joe
```

### Feature 6: Token parsing and structural validation

Parse an arbitrary compact token without asserting its shape: recover the declared header algorithm and the body. Structurally invalid strings are rejected with a neutral category and a `reason`; a null input is rejected as an invalid argument.

- `op=parse`, field `token` (string or null), optional `key`: emit `alg=<value>` then body/claims, or a neutral error.
- A well-formed token has exactly two separators (wrong count → `reason=period_count`); the body segment must be non-empty (→ `reason=missing_body`).

Example cases:

```json
{"op": "parse", "token": "foo"}
```
→
```
error=malformed
reason=period_count
```

```json
{"op": "parse", "token": "."}
```
→
```
error=malformed
reason=period_count
```

```json
{"op": "parse", "token": ".."}
```
→
```
error=malformed
reason=missing_body
```

```json
{"op": "parse", "token": "eyJhbGciOiJub25lIn0.SGVsbG8gd29ybGQh."}
```
→
```
alg=[a specific header constant (e.g., 'none','skip','null')]
body=Hello world!
```

```json
{"op": "parse", "token": "eyJhbGciOiJub25lIn0.eyJzdWIiOiJKb2UifQ."}
```
→
```
alg=[a specific header constant (e.g., 'none','skip','null')]
sub=Joe
```

```json
{"op": "parse", "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJKb2UifQ.qs8rO_cGp7ctWsq-yGbVzJ-cjAhzdLh1jP0296AC9Ac", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA"}
```
→
```
alg=HS256
sub=Joe
```

```json
{"op": "parse", "token": null}
```
→
```
error=illegal_argument
```

### Feature 7: Shape-asserting parsing

Parse while asserting an exact token shape (unsecured-plaintext, unsecured-claims, signed-plaintext, signed-claims). A token whose actual shape differs from the requested one is rejected with `error=unsupported` and a `reason`; a signed token verified with the wrong key is rejected as an invalid signature.

- `op=parse_typed`, fields `token`, `method` (`plaintext_jwt` | `claims_jwt` | `plaintext_jws` | `claims_jws`), optional `key`: emit `kind=<method>` then (for signed forms) `alg=...` then body/claims; or a neutral error.

Example cases:

```json
{"op": "parse_typed", "token": "eyJhbGciOiJub25lIn0.SGVsbG8gd29ybGQh.", "method": "plaintext_jwt"}
```
→
```
kind=plaintext_jwt
body=Hello world!
```

```json
{"op": "parse_typed", "token": "eyJhbGciOiJub25lIn0.eyJzdWIiOiJKb2UifQ.", "method": "claims_jwt"}
```
→
```
kind=claims_jwt
sub=Joe
```

```json
{"op": "parse_typed", "token": "eyJhbGciOiJIUzI1NiJ9.SGVsbG8gd29ybGQh.4Luu4D1QDg0vorxFuBy4sFq090uoZMwkkGfVFsOeqTw", "method": "plaintext_jws", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA"}
```
→
```
kind=plaintext_jws
alg=HS256
body=Hello world!
```

```json
{"op": "parse_typed", "token": "eyJhbGciOiJub25lIn0.SGVsbG8gd29ybGQh.", "method": "claims_jwt"}
```
→
```
error=unsupported
reason=[valid error reasons related to shape mismatch]
```

```json
{"op": "parse_typed", "token": "eyJhbGciOiJub25lIn0.eyJzdWIiOiJKb2UifQ.", "method": "plaintext_jwt"}
```
→
```
error=unsupported
reason=[valid error reasons related to shape mismatch]
```

```json
{"op": "parse_typed", "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJKb2UifQ.qs8rO_cGp7ctWsq-yGbVzJ-cjAhzdLh1jP0296AC9Ac", "method": "claims_jws", "key": "Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MGFiY2RlZmdoaWprbA"}
```
→
```
error=signature_invalid
```

### Feature 8: Required-claim enforcement

Assert that a parsed token contains required claims with expected values. A matching claim verifies and recovers the claim set; a present-but-wrong value is `incorrect_claim`; a required-but-absent claim is `missing_claim`. Works for registered and custom claims.

- `op=require_claim`, fields `key`, `claims` (object to sign), `require` (`{name, value}`): emit `verified=true` then claims, or a neutral error carrying `claim=<name>`.

Example cases:

```json
{"op": "require_claim", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA", "claims": {"sub": "Joe"}, "require": {"name": "sub", "value": "Joe"}}
```
→
```
verified=true
sub=Joe
```

```json
{"op": "require_claim", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA", "claims": {"sub": "Joe"}, "require": {"name": "sub", "value": "Wrong"}}
```
→
```
error=incorrect_claim
claim=sub
```

```json
{"op": "require_claim", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA", "claims": {"sub": "Joe"}, "require": {"name": "iss", "value": "Me"}}
```
→
```
error=missing_claim
claim=iss
```

```json
{"op": "require_claim", "key": "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA", "claims": {"role": "admin"}, "require": {"name": "role", "value": "admin"}}
```
→
```
verified=true
claim.role=admin
```

### Feature 9: Temporal validity enforcement

Enforce time-based validity on parse. A token with no temporal constraints (or with currently-satisfied constraints) verifies; a past expiration is `expired`; a future not-before is `premature`. Error outcomes carry only a neutral category — no wall-clock timestamps.

- `op=lifecycle`, field `sub`, optional `exp_offset_sec` / `nbf_offset_sec` (relative to now): emit `valid=true` then claims, or a neutral error.

Example cases:

```json
{"op": "lifecycle", "sub": "Joe"}
```
→
```
valid=true
sub=Joe
```

```json
{"op": "lifecycle", "sub": "Joe", "exp_offset_sec": -1000}
```
→
```
error=expired
```

```json
{"op": "lifecycle", "sub": "Joe", "nbf_offset_sec": 10000}
```
→
```
error=premature
```

### Feature 10: Build-request validation

Reject internally inconsistent build requests before any token is produced.

- `op=builder_validate`, field `mode`:
  - `empty` — compacting an empty builder → `error=illegal_state`.
  - `both_payload_and_claims` — supplying both a plaintext payload and claims → `error=illegal_state`.
  - `bytes_without_hmac` / `base64_bytes_without_hmac` — supplying raw key bytes with a non-HMAC algorithm → `error=illegal_argument`.

Example cases:

```json
{"op": "builder_validate", "mode": "empty"}
```
→
```
error=illegal_state
```

```json
{"op": "builder_validate", "mode": "both_payload_and_claims"}
```
→
```
error=illegal_state
```

```json
{"op": "builder_validate", "mode": "bytes_without_hmac"}
```
→
```
error=illegal_argument
```

### Feature 11: Algorithm-substitution forgery resistance

Resist a forgery where an attacker re-signs a token with HMAC using an asymmetric public key's encoded bytes as the MAC secret. When the token is verified with the asymmetric key, the library must refuse rather than accept the forgery, surfacing a neutral category.

- `op=forge_hmac_with_key`, field `key_type` (`rsa` | `ec`): always → `error=unsupported`, `reason=algorithm_key_mismatch`.

Example cases:

```json
{"op": "forge_hmac_with_key", "key_type": "rsa"}
```
→
```
error=unsupported
reason=algorithm_key_mismatch
```

```json
{"op": "forge_hmac_with_key", "key_type": "ec"}
```
→
```
error=unsupported
reason=algorithm_key_mismatch
```

## Deliverables

- A library exposing the operations above through a single stdin→stdout adapter, producing the exact deterministic `key=value` output specified per feature.
- A line-oriented, language-neutral **error contract** covering structural, semantic, signature, temporal, claim-policy, and build-time failures, with no host-language leakage.
- A contract test suite driven by `rcb_tests/test.sh`:
  - `rcb_tests/test_cases/featureN_*.json` — the full hidden evaluation set (one file per leaf feature).
  - `rcb_tests/public_test_cases/featureN_*.json` — the subset embedded in this document.
  - `rcb_tests/dispatcher/` — the adapter that maps JSON ops onto the library and renders the neutral contract.
  - The harness reads each case's `input`, feeds it to the adapter, captures raw stdout to `rcb_tests/stdout/<cases-dir>/<stem>@<NNN>.txt`, and compares against `expected_output`, reporting per-case PASS/FAIL and a final `test_cases: N/N pass` summary.


---
**Implementation notes:**
- follow the internal documentation order for standard claims
- a sample Unix timestamp value used for testing
