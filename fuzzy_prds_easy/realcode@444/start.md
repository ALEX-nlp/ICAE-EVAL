## Product Requirement Document

# Browser-Side OAuth 2.0 / OpenID Connect Helper Library (Authorization Code Flow with PKCE)

## Project Goal

Build the deterministic, pure building blocks that a single-page web application needs in order to participate in the OAuth 2.0 / OpenID Connect **Authorization Code flow with PKCE** entirely from the browser, without a backend. These helpers cover the parts of the flow that do not require any live network call: assembling the parameters of an authorization request, generating and protecting the PKCE secret, encoding the opaque values that tie a request to its response, parsing and validating the identity token that comes back, and keying an in-memory token store. Each component is side-effect free (apart from value-derivation) and fully reproducible: given the same inputs it always produces the same output, so it can be exercised in isolation from any identity provider.

---

## Background & Problem

A browser-only application that authenticates users with an external identity provider must implement a security-sensitive handshake by hand: it has to build a correctly-encoded authorization URL, create a high-entropy secret (the *code verifier*) and its hashed public form (the *code challenge*), carry opaque anti-forgery values (*state*) and anti-replay values (*nonce*) across a redirect, then, on return, decode the response, validate the issued identity token against a strict set of rules, and cache the resulting tokens so they are not re-requested unnecessarily.

Getting any of these steps wrong is a security hazard: a malformed query string breaks the flow, a weak or leaked verifier defeats PKCE, an unvalidated token allows impersonation, and a cache that ignores the requested audience or scope can return a token that grants the wrong access. This library isolates those concerns into small, independently testable, deterministic units.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is acceptable, provided it keeps clean logical separation.
   - **For complex systems:** If the project spans multiple distinct responsibilities (e.g. request building, cryptographic helpers, token decoding/validation, caching), it MUST NOT collapse into one "god file". Use a clear multi-file layout that reflects a production-grade repository. This domain has several distinct responsibilities (scope normalization, query serialization, PKCE secret handling, base64url codecs, token decode/verify, cache keying) and should be organized into separate modules.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for an execution adapter, NOT the internal data model of the core system. The core logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter alone is responsible for translating JSON commands into idiomatic calls to the core code, and for translating thrown errors into the neutral `error=<category>` lines described below.

3. **Adherence to SOLID Design Principles:** scaled appropriately to the project's size — single responsibility per unit, small cohesive interfaces, and high-level logic that does not depend on low-level I/O details.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide internal complexity. Edge cases (empty/blank/missing inputs, invalid tokens) must be handled gracefully and modeled with proper error types rather than generic faults.

---

## Execution Adapter Contract

Every feature is driven through a thin adapter that reads **one JSON object from stdin** and writes plain text to **stdout**. The object always carries an `op` field selecting the behavior; the remaining fields are the operation's inputs. Output is a sequence of `key=value` lines, each terminated by a newline (`\n`). When an operation rejects its input, the adapter prints exactly one neutral line of the form `error=<category>` and nothing else. Output must contain only the program's own results — no test-runner metadata.

The authoritative, complete set of cases for each feature lives in `rcb_tests/test_cases/*.json`; the snippets below are illustrative.

---

## Core Features

### Feature 1: Effective Scope Set (`op: scope_set`)

**As a developer**, I want to combine several space-separated scope strings into one normalized scope string, so that the authorization request asks for exactly the right set of permissions with no duplicates.

**Expected Behavior:** The input field `scopes` is an ordered list of scope strings. Empty, blank, and null entries are ignored. Whitespace runs act as separators; duplicate scope tokens are removed keeping first-seen order; the result is a single space-joined string with no leading/trailing whitespace, emitted as `scope=<result>`.

```json
{
  "input": { "op": "scope_set", "scopes": ["openid profile", "openid email", "email"] },
  "expected_output": "scope=openid profile email\n"
}
```

---

### Feature 2: Authorization Request Query (`op: authorize_query`)

**As a developer**, I want to serialize the parameters of an authorization request into a URL query string, so I can build the URL the browser is sent to.

**Expected Behavior:** The input field `params` is an object of request parameters (e.g. requested scope, response type and mode, redirect target, API audience, opaque state, nonce, and the PKCE challenge fields). Keys are serialized in the order given, each value is URL-component-encoded, and pairs are joined with `&`. The result is emitted as `query=<query-string>`.

```json
{
  "input": { "op": "authorize_query", "params": { "scope": "openid profile email", "response_type": "code", "response_mode": "query", "redirect_uri": "https://app.example.com/callback", "audience": "https://api.example.com/v2/", "state": "c3RhdGU", "nonce": "n0nce-AbC", "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM", "code_challenge_method": "S256" } },
  "expected_output": "query=scope=openid%20profile%20email&response_type=code&response_mode=query&redirect_uri=https%3A%2F%2Fapp.example.com%2Fcallback&audience=https%3A%2F%2Fapi.example.com%2Fv2%2F&state=c3RhdGU&nonce=n0nce-AbC&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256\n"
}
```

---

### Feature 3: Callback Query Parsing (`op: parse_query`)

**As a developer**, I want to parse the query string returned to my redirect/callback target into a structured result, so I can read the authorization code (or error) and accompanying values.

**Expected Behavior:** The input field `query` is the query string with no leading separator. Each key/value pair is URL-decoded. A token-lifetime field, when present, is converted to an integer; when absent it is reported as a null lifetime. Both successful results and provider error responses are parsed identically. The result object is emitted as `result=<json>`.

```json
{
  "input": { "op": "parse_query", "query": "code=AUTH_CODE_123&state=c3RhdGU&expires_in=86400" },
  "expected_output": "result={\"code\":\"AUTH_CODE_123\",\"state\":\"c3RhdGU\",\"expires_in\":86400}\n"
}
```

---

### Feature 4: State Value Codec (`op: state_codec`)

**As a developer**, I want to encode an opaque transaction value into a transport-safe text form and decode it back exactly, so anti-forgery state survives the redirect round-trip.

**Expected Behavior:** The input field `state` is the value to encode. The adapter emits the encoded form as `encoded=<...>` and the value recovered by decoding it as `decoded=<...>`; decoding an encoded value reproduces the original input unchanged.

```json
{
  "input": { "op": "state_codec", "state": "opaque-STATE_value~123" },
  "expected_output": "encoded=b3BhcXVlLVNUQVRFX3ZhbHVlfjEyMw==\ndecoded=opaque-STATE_value~123\n"
}
```

---

### Feature 5: URL-Safe Base64 Codec (`op: base64url`)

**As a developer**, I want to convert raw bytes into URL-safe base64 text and convert such text back, so binary material (like a hashed challenge) is safe to put in a URL.

**Expected Behavior:** When the input supplies `bytes` (a list of byte values), the adapter emits `encoded=<url-safe base64, no [URL-safe alphabet requirements]>`. When the input supplies `encoded` (URL-safe base64 text), the adapter emits `decoded=<decoded string>`. The URL-safe alphabet is used and [URL-safe alphabet requirements] characters are omitted.

```json
{
  "input": { "op": "base64url", "bytes": [72, 101, 108, 108, 111] },
  "expected_output": "encoded=SGVsbG8\n"
}
```

---

### Feature 6: PKCE Code Verifier Generation (`op: code_verifier`)

**As a developer**, I want to turn a sequence of random bytes into a code verifier string, so the PKCE secret draws only from an unreserved character set.

**Expected Behavior:** The input field `bytes` provides the random byte values the generator consumes. Each requested byte maps to exactly one character of a fixed unreserved character set, producing a string whose length equals the number of bytes the generator requests. The mapping is deterministic, so fixed bytes always yield the same string, emitted as `verifier=<string>`.

```json
{
  "input": { "op": "code_verifier", "bytes": [1, 5, 10, 15, 100] },
  "expected_output": "verifier=15AFa15AFa15AFa15AFa15AFa15AFa15AFa15AFa15A\n"
}
```

---

### Feature 7: PKCE Code Challenge Derivation (`op: code_challenge`)

**As a developer**, I want to derive the code challenge from a code verifier, so the authorization request can carry the hashed public form of the secret.

**Expected Behavior:** The input field `verifier` is the code verifier. The adapter hashes it with SHA-256 and encodes the digest as URL-safe base64 without [URL-safe alphabet requirements], emitting `code_challenge=<...>` followed by `code_challenge_method=S256`. A fixed verifier always produces the same challenge.

```json
{
  "input": { "op": "code_challenge", "verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk" },
  "expected_output": "code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM\ncode_challenge_method=S256\n"
}
```

---

### Feature 8: Identity Token Decoding (`op: decode_token`)

**As a developer**, I want to decode an identity token without verifying its signature, so I can read its header, its full claim set, and the end-user profile it carries.

**Expected Behavior:** The input field `id_token` is a token of three dot-separated base64url segments. The adapter emits three lines: `header=<json>` (the decoded header), `claims=<json>` (all decoded claims, plus a `__raw` copy of the original token string), and `user=<json>` (the subset of claims that are *not* well-known protocol/registered claim names — i.e. the end-user profile fields).

```json
{
  "input": { "op": "decode_token", "id_token": "<header>.<payload>.<signature>" },
  "expected_output": "header={\"alg\":\"RS256\",\"typ\":\"JWT\"}\nclaims={\"__raw\":\"<token>\",\"iss\":\"https://tenant.example.com/\",\"aud\":\"CLIENTID123\",\"nonce\":\"n0nce-AbC\",\"sub\":\"auth0|0123456789\",\"name\":\"Jane Doe\",\"email\":\"jane@example.com\",\"email_verified\":true,\"exp\":2000000000,\"iat\":1500000000}\nuser={\"sub\":\"auth0|0123456789\",\"name\":\"Jane Doe\",\"email\":\"jane@example.com\",\"email_verified\":true}\n"
}
```

(See `rcb_tests/test_cases/feature8_token_decode.json` for the concrete token and exact bytes.)

---

### Feature 9: Identity Token Verification (`op: verify_token`)

**As a developer**, I want to validate a decoded identity token against expectations, so I reject impersonation, replay, and stale tokens.

**Expected Behavior:** The input supplies the `id_token` plus the expected `iss`, `aud`, and `nonce` (and an optional clock-skew `leeway`). The token is checked for: matching issuer, matching audience, the required signing algorithm, matching nonce, and the time constraints expiry / issued-at / not-before (each with a small skew allowance). On success the adapter emits `valid=true` followed by `claims=<json>`. On the first failing check it emits exactly one neutral category line, one of: `error=invalid_issuer`, `error=invalid_audience`, `error=invalid_algorithm`, `error=invalid_nonce`, `error=expired`, `error=future_issued`, `error=not_yet_valid`.

```json
{
  "input": { "op": "verify_token", "id_token": "<valid token>", "iss": "https://tenant.example.com/", "aud": "CLIENTID123", "nonce": "n0nce-AbC" },
  "expected_output": "valid=true\nclaims={ ... }\n"
}
```

```json
{
  "input": { "op": "verify_token", "id_token": "<token with wrong issuer expectation>", "iss": "https://evil.example.com/", "aud": "CLIENTID123", "nonce": "n0nce-AbC" },
  "expected_output": "error=invalid_issuer\n"
}
```

(See `rcb_tests/test_cases/feature9_token_verify.json` for every category and the concrete tokens.)

---

### Feature 10: Token Cache Keying (`op: cache_key`)

**As a developer**, I want a token cache that is keyed by both the API audience and the scope of a request, so a cached token is only reused for the exact audience+scope it was issued for.

**Expected Behavior:** The input supplies an `entry` to store (carrying at least its `audience`, `scope`, and `access_token`) and a list of `lookups`, each with an `audience` and `scope`. The entry is stored, then each lookup is resolved: a lookup whose audience and scope both match the stored entry returns that entry's access token; any other combination misses. Results are emitted in order as `lookup0=<...>`, `lookup1=<...>`, …, where the value is the matched access token or `miss`.

```json
{
  "input": { "op": "cache_key", "entry": { "audience": "https://api.example.com/", "scope": "openid profile", "access_token": "AT-1", "id_token": "id1", "expires_in": 3600, "exp": 2000000000 }, "lookups": [ { "audience": "https://api.example.com/", "scope": "openid profile" }, { "audience": "https://api.example.com/", "scope": "openid profile email" }, { "audience": "default", "scope": "openid profile" } ] },
  "expected_output": "lookup0=AT-1\nlookup1=miss\nlookup2=miss\n"
}
```

---

## Test Data Layout

- `rcb_tests/test_cases/featureN_*.json` — the authoritative, complete case list for each feature, of the form `{ "description", "cases": [ { "input", "expected_output" } ] }`.
- `rcb_tests/public_test_cases/featureN_*.json` — a strict subset mirror of the illustrative cases shown above.
- `expected_output` is the exact raw stdout the adapter must produce for the given `input`.


---
**Implementation notes:**
- follow the same derivation steps as the token challenge section
- unhide flagged keys for verification
