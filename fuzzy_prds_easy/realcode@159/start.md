## Product Requirement Document

# OpenID Connect Implicit-Flow Client Toolkit - Product Requirements

## Project Goal

Build a client-side toolkit that lets web developers add OpenID Connect / OAuth2 implicit-flow login to a single-page application without hand-writing the security-critical plumbing. The toolkit builds the correct authorization and logout request URLs, parses the redirect callback, decodes and validates the returned identity token end-to-end, and exposes the verdict to the application — so developers integrate standards-compliant sign-in by configuring values rather than implementing token cryptography themselves.

---

## Background & Problem

Without this toolkit, a developer adding OpenID Connect sign-in to a browser app must, by hand: assemble the authorization request query string (correctly percent-encoding every parameter and preserving any provider-specific query already on the endpoint), parse the URL fragment the provider redirects back with, base64url-decode the three segments of the returned JSON Web Token, and then run the full battery of token checks the specification demands — signature verification against the provider's published keys, nonce replay protection, audience and issuer matching, issued-at and expiry windows, and the access-token hash binding. Each of these is easy to get subtly wrong, and a single mistake (skipping the nonce check, mis-ordering audience comparison, accepting an expired token) is a real security hole.

With this toolkit, the developer supplies a small configuration object (client id, scopes, response type, endpoints, allowed clock offset) and calls a handful of high-level operations. The toolkit produces the request URLs, parses the callback, and returns a single structured verdict describing whether the response is valid and, if not, exactly which check failed — turning a security-sensitive implementation task into a configuration task.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (URL building, fragment parsing, token decoding, signature/claims validation, configuration resolution, an orchestrating validation pipeline). It MUST NOT be a single "god file". Output a clear directory tree separating these responsibilities into cohesive units (e.g. a config layer, a token-decoding helper, a low-level claim-validator, a high-level validation pipeline, and the request/URL service), with the test adapter kept apart from the domain.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box contract for the execution adapter**, NOT the internal data model. The core logic must be free of any stdin/stdout or JSON-command coupling. The adapter alone translates a JSON command into idiomatic calls on the core API and renders the neutral stdout lines.

3. **Adherence to SOLID Design Principles (scaled to project size):**
   - **SRP:** Keep parsing, URL formatting, claim validation, pipeline orchestration, and output rendering in distinct units.
   - **OCP:** The validation pipeline must be extensible with new checks without rewriting existing ones.
   - **LSP:** Any value-source or storage abstraction must be substitutable by a test double.
   - **ISP:** Keep collaborator interfaces (logging, storage, key retrieval) small and focused.
   - **DIP:** The pipeline depends on abstractions (a key source, a clock, a logger) rather than concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public API should be ergonomic in the target language and hide cryptographic detail behind clear operations.
   - **Resilience:** Malformed tokens, absent claims, and mismatched values must yield a defined, categorized verdict — never an uncaught fault. Every failure mode is modeled as an explicit outcome code.

---

## Core Features

### Feature 1: Loose Value Equality for Claim Comparison

**As a developer**, I want a single equality primitive that can compare claim values whether they arrive as a plain string, a list of strings, an object, or as a missing value, so I can compare token claims uniformly without scattering type checks through my code.

**Expected Behavior / Usage:**

The operation compares two values and answers whether they are "equal" under claim-comparison rules. Two strings are equal only when identical character-for-character (case sensitive). Two lists are equal only when they have the same length and identical elements in the same order. Two objects are equal when their case-insensitive serialized forms match. A plain string compared against a one-element list is equal exactly when the string equals that single element (in either argument order). Any missing operand (null or undefined) forces "not equal", and two empty strings are deliberately treated as "not equal". Output is one line, `equal=true` or `[a specific hardcoded false value for empty strings]`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_value_equality.json`

```json
{
    "op": "value_equality",
    "description": "Loose structural equality between two credential-claim values that may each be a string, a string array, an object, or a null/undefined absence. Two strings are equal only when byte-for-byte identical (case sensitive). Two arrays are equal only when they have the same length and identical ordered elements. Two objects are equal when their case-insensitive serialized forms match. A string compared against a single-element array is equal when the string equals that one element. Any null or undefined operand makes the result not-equal, and two empty strings are treated as not-equal. Output is a single line 'equal=true' or '[a specific hardcoded false value for empty strings]'.",
    "cases": [
        {"input": {"left": null, "right": "somestring"}, "expected_output": "[a specific hardcoded false value for empty strings]\n"},
        {"input": {"left": "somestring", "right": "somestring"}, "expected_output": "equal=true\n"},
        {"input": {"left": "somestring", "right": "Somestring"}, "expected_output": "[a specific hardcoded false value for empty strings]\n"},
        {"input": {"left": ["somestring1", "somestring2"], "right": ["somestring1", "somestring2"]}, "expected_output": "equal=true\n"},
        {"input": {"left": ["somestring1"], "right": "somestring1"}, "expected_output": "equal=true\n"}
    ]
}
```

---

### Feature 2: Audience Claim Validation

**As a developer**, I want to confirm that the audience named inside a decoded identity token is the audience I expect (my client identifier), so I can reject tokens that were minted for some other application.

**Expected Behavior / Usage:**

Given the audience embedded in a decoded token and the expected client identifier, the operation answers whether they match. When the token audience is a single string it must equal the expected value exactly. When the token audience is a list it must equal the expected list element-for-element, in order. Output is one line, `match=true` or `match=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_audience_validation.json`

```json
{
    "op": "audience_validation",
    "description": "Verify that the audience embedded in a decoded identity token matches the expected client identifier. When the token audience is a single string, it must exactly equal the expected value. When the token audience is an array of strings, it must equal the expected array element-for-element in order. Output is a single line 'match=true' or 'match=false'.",
    "cases": [
        {"input": {"token_aud": "banana", "expected_aud": "banana"}, "expected_output": "match=true\n"},
        {"input": {"token_aud": "banana", "expected_aud": "bananammmm"}, "expected_output": "match=false\n"},
        {"input": {"token_aud": ["banana", "apple", "https://nice.dom"], "expected_aud": ["banana", "apple", "https://nice.dom"]}, "expected_output": "match=true\n"},
        {"input": {"token_aud": ["banana", "apple", "https://nice.dom"], "expected_aud": ["ooo", "apple", "https://nice.dom"]}, "expected_output": "match=false\n"}
    ]
}
```

---

### Feature 3: Token Reading

**As a developer**, I want to read the time-validity and the raw contents out of a token, so I can inspect and validate it without owning any base64 or JWT-parsing code.

**Expected Behavior / Usage:**

*3.1 Token Expiration Instant — derive the absolute expiry time from a claim set*

Given a token's claim set, compute its expiration instant. When the claims include an `exp` field (seconds since the Unix epoch, UTC), the output is `has_exp=true` followed by `exp_utc=<ISO-8601 UTC timestamp>` for that instant. When no `exp` claim is present there is no fixed expiry to report, and the output is the single line `has_exp=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_token_expiration.json`

```json
{
    "op": "token_expiration",
    "description": "Compute the absolute expiration instant of an identity token from its claim set. When the claims contain an 'exp' field (seconds since the Unix epoch, UTC), the output reports 'has_exp=true' followed by 'exp_utc=<ISO-8601 UTC timestamp>' derived from that value. When no 'exp' claim is present, no fixed instant exists; the output reports only 'has_exp=false'.",
    "cases": [
        {"input": {"claims": {}}, "expected_output": "has_exp=false\n"},
        {"input": {"claims": {"exp": 123}}, "expected_output": "has_exp=true\nexp_utc=1970-01-01T00:02:03.000Z\n"}
    ]
}
```

*3.2 Token Segment Decode — extract a chosen segment, raw or decoded*

A compact token is three base64url segments separated by dots: header, payload, signature. This operation extracts the requested segment by name. With `encoded` true the raw segment text is returned verbatim. With `encoded` false the segment is base64url-decoded and parsed as JSON into a structured object, applying UTF-8 / percent-decoding so non-ASCII text round-trips correctly. Any input that is null, empty, contains no dot, or does not split into exactly three parts is invalid and yields the empty object. Output is one line `value=<rendering>`, where a raw string is printed as-is and an object is printed as compact JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_jwt_segment_decode.json`

```json
{
    "op": "jwt_segment_decode",
    "description": "Extract one of the three dot-separated segments (header, payload, or signature) from a compact three-part token string. With 'encoded' true the raw segment text is returned verbatim. With 'encoded' false the segment is base64url-decoded and parsed as JSON, yielding the structured object (UTF-8 / percent-decoding is applied so non-ASCII text is preserved). A token that is null, empty, contains no dot, or does not have exactly three parts is invalid and yields the empty object. Output is a single line 'value=<rendering>' where strings render as-is and objects render as compact JSON.",
    "cases": [
        {"input": {"segment": "header", "token": "abc.def.ghi", "encoded": true}, "expected_output": "value=abc\n"},
        {"input": {"segment": "payload", "token": "abc.eyAidGV4dCIgOiAiSGVsbG8gV29ybGQgMTIzISJ9.ghi", "encoded": false}, "expected_output": "value={\"text\":\"Hello World 123!\"}\n"},
        {"input": {"segment": "payload", "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiSm9obiBEw7PDqyJ9.wMn-1oLWnxKJolMGb7YKnlwjqusWf4xnnjABgFaDkI4", "encoded": false}, "expected_output": "value={\"name\":\"John Dóë\"}\n"},
        {"input": {"segment": "payload", "token": "testStringWithoutDots", "encoded": true}, "expected_output": "[the specific literal string indicating invalid token format]\n"}
    ]
}
```

---

### Feature 4: Request URL Building

**As a developer**, I want the toolkit to assemble my sign-in and sign-out request URLs from configuration, so the query parameters are always present, ordered, and percent-encoded correctly.

**Expected Behavior / Usage:**

*4.1 Authorization Request URL — build the sign-in redirect URL*

From a base authorization endpoint plus configuration, build the authorization request URL. Any query already present on the endpoint is preserved, then `client_id`, `redirect_uri`, `response_type`, `scope`, `nonce`, and `state` are appended in that fixed order, followed by any extra custom request parameters in the order supplied. Every key and value is percent-encoded per `application/x-www-form-urlencoded` rules (so spaces become `%20`, reserved punctuation like `;,/?:@&=+$` and `#` are escaped, and the unreserved set `-_.!~*()` is left intact). Output is one line `url=<full url>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_authorize_url.json`

```json
{
    "op": "authorize_url",
    "description": "Build an authorization request URL from a base authorization endpoint and the client configuration. The endpoint's own pre-existing query (if any) is preserved, then the parameters client_id, redirect_uri, response_type, scope, nonce, and state are appended in that fixed order, followed by any extra custom request parameters in the order supplied. All keys and values are percent-encoded per application/x-www-form-urlencoded rules. Output is a single line 'url=<full url>'.",
    "cases": [
        {"input": {"config": {"client_id": "188968487735-b1hh7k87nkkh6vv84548sinju2kpr7gn.apps.googleusercontent.com", "response_type": "id_token token", "scope": "openid email profile"}, "redirect_url": "https://localhost:44386", "nonce": "nonce", "state": "state", "authorization_endpoint": "http://example"}, "expected_output": "url=http://example?client_id=188968487735-b1hh7k87nkkh6vv84548sinju2kpr7gn.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Flocalhost%3A44386&response_type=id_token%20token&scope=openid%20email%20profile&nonce=nonce&state=state\n"},
        {"input": {"config": {"client_id": "myid", "response_type": "id_token token", "scope": "openid email profile"}, "redirect_url": "https://localhost:44386", "nonce": "nonce", "state": "state", "authorization_endpoint": "https://login.microsoftonline.com/fabrikamb2c.onmicrosoft.com/oauth2/v2.0/authorize?p=b2c_1_sign_in"}, "expected_output": "url=https://login.microsoftonline.com/fabrikamb2c.onmicrosoft.com/oauth2/v2.0/authorize?p=b2c_1_sign_in&client_id=myid&redirect_uri=https%3A%2F%2Flocalhost%3A44386&response_type=id_token%20token&scope=openid%20email%20profile&nonce=nonce&state=state\n"},
        {"input": {"config": {"client_id": "188968487735-b1hh7k87nkkh6vv84548sinju2kpr7gn.apps.googleusercontent.com", "response_type": "id_token token", "scope": "openid email profile"}, "redirect_url": "https://localhost:44386", "nonce": "nonce", "state": "state", "authorization_endpoint": "http://example", "custom_request_params": {"t4": "ABC abc 123", "t3": "#", "t2": "-_.!~*()", "t1": ";,/?:@&=+$"}}, "expected_output": "url=http://example?client_id=188968487735-b1hh7k87nkkh6vv84548sinju2kpr7gn.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Flocalhost%3A44386&response_type=id_token%20token&scope=openid%20email%20profile&nonce=nonce&state=state&t4=ABC%20abc%20123&t3=%23&t2=-_.!~*()&t1=%3B%2C%2F%3F%3A%40%26%3D%2B%24\n"}
    ]
}
```

*4.2 End-Session Request URL — build the sign-out redirect URL*

From a base end-session endpoint, the identity-token hint, and the configured post-logout redirect URI, build the logout URL. Any query already on the endpoint is preserved, then `id_token_hint` and `post_logout_redirect_uri` are appended in that fixed order, percent-encoded by the same rules. Output is one line `url=<full url>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_end_session_url.json`

```json
{
    "op": "end_session_url",
    "description": "Build an end-session (logout) URL from a base end-session endpoint, the identity-token hint, and the configured post-logout redirect URI. The endpoint's pre-existing query (if any) is preserved, then id_token_hint and post_logout_redirect_uri are appended in that fixed order, percent-encoded per application/x-www-form-urlencoded rules. Output is a single line 'url=<full url>'.",
    "cases": [
        {"input": {"config": {"post_logout_redirect_uri": "https://localhost:44386/Unauthorized"}, "end_session_endpoint": "http://example", "id_token_hint": "mytoken"}, "expected_output": "url=http://example?id_token_hint=mytoken&post_logout_redirect_uri=https%3A%2F%2Flocalhost%3A44386%2FUnauthorized\n"},
        {"input": {"config": {"post_logout_redirect_uri": "https://localhost:44386/Unauthorized"}, "end_session_endpoint": "https://login.microsoftonline.com/fabrikamb2c.onmicrosoft.com/oauth2/v2.0/logout?p=b2c_1_sign_in", "id_token_hint": "UzI1NiIsImtpZCI6Il"}, "expected_output": "url=https://login.microsoftonline.com/fabrikamb2c.onmicrosoft.com/oauth2/v2.0/logout?p=b2c_1_sign_in&id_token_hint=UzI1NiIsImtpZCI6Il&post_logout_redirect_uri=https%3A%2F%2Flocalhost%3A44386%2FUnauthorized\n"}
    ]
}
```

---

### Feature 5: Callback Fragment Parsing

**As a developer**, I want to turn the raw `key=value&...` fragment the identity provider redirects back with into a key/value map, so I can read the returned access token, state, and token type reliably even when values themselves contain `=` characters.

**Expected Behavior / Usage:**

The fragment is split on `&` between pairs and on the **first** `=` within each pair, so any further `=` characters stay inside the value. This means a base64 token ending in `==`, or a `state` value that itself contains `=`, is preserved intact rather than truncated. Output prints one `key=value` line per parsed entry, in the order the keys appear in the fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature5_callback_fragment_parse.json`

```json
{
    "op": "callback_fragment_parse",
    "description": "Parse a redirect callback fragment of the form 'key1=value1&key2=value2&...' into its key/value map. Splitting is performed on '&' between pairs and on the first '=' within each pair, so any further '=' characters are kept inside the value (e.g. a base64 token ending in '==' or a state value that itself contains '='). Output prints one 'key=value' line per parsed entry in encounter order.",
    "cases": [
        {"input": {"fragment": "access_token=ACCESS-TOKEN&token_type=bearer&state=testState"}, "expected_output": "access_token=ACCESS-TOKEN\ntoken_type=bearer\nstate=testState\n"},
        {"input": {"fragment": "access_token=ACCESS-TOKEN==&token_type=bearer&state=test=State"}, "expected_output": "access_token=ACCESS-TOKEN==\ntoken_type=bearer\nstate=test=State\n"}
    ]
}
```

---

### Feature 6: Authorization Response Validation Pipeline

**As a developer**, I want to hand the toolkit a complete authorization response — the access token plus the signed identity token — and the trusted signing keys, and get back a single verdict that tells me whether the response is valid and, if not, precisely which security check failed, so my application can trust the result without re-implementing the checks.

**Expected Behavior / Usage:**

The pipeline runs an ordered chain of checks and reports the **first** stage that fails (short-circuiting), or success if all pass. The order is:

1. The returned `state` must equal the locally stored state.
2. The identity-token signature must verify against the issuer's signing key.
3. The token `nonce` must equal the locally stored nonce.
4. The required claims `iss`, `sub`, `aud`, `exp`, `iat` must all be present.
5. The issue time must be within the configured allowed offset of the current time.
6. The `iss` claim must match the configured issuer.
7. The `aud` claim must match the configured client id.
8. The token must not be expired.
9. Only when the response type requests both an access token and an identity token, the token's access-token hash must match the supplied access token and an access token must be present.

When every stage passes the verdict is the success outcome `Ok` and the response is valid. The outcome codes, one per failing stage in pipeline order, are: `StatesDoNotMatch`, `SignatureFailed`, `IncorrectNonce`, `RequiredPropertyMissing`, `MaxOffsetExpired`, `IssDoesNotMatchIssuer`, `IncorrectAud`, `TokenExpired`, `IncorrectAtHash`, and `Ok`. The verdict also carries the echoed access token (only when the response type requests one), whether an identity token was carried through, and the decoded subject.

Inputs describe a scenario declaratively — the stored state and nonce, the claims to put in the token, whether to sign with the correct key, how long ago it was issued, whether it is already expired, and whether to bind a correct access-token hash — and the executing adapter mints a real signed token from that description. Output is five lines: `result=<outcome code>`, `valid=<true|false>`, `access_token=<echoed token or empty>`, `id_token=<present|empty>`, `decoded_sub=<subject claim or empty>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_response_validation.json`

```json
{
    "op": "response_validation",
    "description": "Validate a full authorization response (an access token plus a signed identity token) against the client configuration and the issuer signing keys, running the ordered chain of identity-token checks and reporting the first failing stage. The pipeline, in order, is: (1) the returned state must equal the locally stored state; (2) the identity-token signature must verify against the issuer key; (3) the token nonce must equal the locally stored nonce; (4) the required claims iss/sub/aud/exp/iat must all be present; (5) the issue time must be within the allowed offset of now; (6) the issuer must match the configured issuer; (7) the audience must match the configured client id; (8) the token must not be expired; (9) only when the response type requests both an access token and an identity token, the token's access-token hash must match the supplied access token and an access token must be present. When every stage passes the result is the success code and the response is valid. Inputs describe the scenario declaratively (which stored values, which token claims, whether to sign with the correct key, etc.); the adapter mints a real signed token accordingly. Output is five lines: 'result=<stage outcome code>', 'valid=<true|false>', 'access_token=<echoed access token or empty>', 'id_token=<present|empty>', and 'decoded_sub=<subject claim or empty>'. The outcome codes are: StatesDoNotMatch, SignatureFailed, IncorrectNonce, RequiredPropertyMissing, MaxOffsetExpired, IssDoesNotMatchIssuer, IncorrectAud, TokenExpired, IncorrectAtHash, Ok.",
    "cases": [
        {"input": {"client_id": "singleapp", "response_type": "id_token token", "max_iat_offset_seconds": 10, "issuer": "https://localhost:44363", "local_state": "st", "local_nonce": "nn", "response_state": "WRONG", "access_token": "AT", "id_token_present": false}, "expected_output": "result=StatesDoNotMatch\nvalid=false\naccess_token=\nid_token=\ndecoded_sub=\n"},
        {"input": {"client_id": "singleapp", "response_type": "id_token token", "max_iat_offset_seconds": 10, "issuer": "https://localhost:44363", "local_state": "st", "local_nonce": "nn", "response_state": "st", "access_token": "AT", "id_token_present": true, "include_at_hash": true, "signature": "wrong", "id_token_claims": {"iss": "https://localhost:44363", "sub": "s", "aud": "singleapp", "nonce": "nn"}}, "expected_output": "result=SignatureFailed\nvalid=false\naccess_token=AT\nid_token=present\ndecoded_sub=s\n"},
        {"input": {"client_id": "singleapp", "response_type": "id_token token", "max_iat_offset_seconds": 10, "issuer": "https://localhost:44363", "local_state": "st", "local_nonce": "nn", "response_state": "st", "access_token": "AT", "id_token_present": true, "include_at_hash": true, "signature": "correct", "id_token_claims": {"iss": "https://localhost:44363", "sub": "s", "aud": "OTHER", "nonce": "nn"}}, "expected_output": "result=IncorrectAud\nvalid=false\naccess_token=AT\nid_token=present\ndecoded_sub=s\n"},
        {"input": {"client_id": "singleapp", "response_type": "id_token token", "max_iat_offset_seconds": 10, "issuer": "https://localhost:44363", "local_state": "st", "local_nonce": "nn", "response_state": "st", "access_token": "AT", "id_token_present": true, "include_at_hash": true, "signature": "correct", "id_token_claims": {"iss": "https://localhost:44363", "sub": "s", "aud": "singleapp", "nonce": "nn"}}, "expected_output": "result=Ok\nvalid=true\naccess_token=AT\nid_token=present\ndecoded_sub=s\n"}
    ]
}
```

---

### Feature 7: Platform-Aware Feature Gating

**As a developer**, I want browser-only capabilities (silent token renewal and session-state checking) to be automatically disabled when my app renders outside a live browser, so the same configuration is safe to run during server-side rendering without me adding environment guards.

**Expected Behavior / Usage:**

Given the requested feature flags and the host platform, resolve the effective settings. On an interactive browser platform the requested flags are honored unchanged. On a non-interactive (server-side) platform both silent renewal and session checking are forced off regardless of what was requested, because they depend on a live browser. Output is two lines: `silent_renew=<true|false>` and `start_checksession=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_platform_feature_gating.json`

```json
{
    "op": "platform_feature_gating",
    "description": "Resolve whether the silent-renew and session-check features are enabled, given the requested configuration flags and the host platform. On an interactive browser platform the requested flags are honored as-is. On a non-interactive (server-side rendering) platform both features are forced off regardless of what was requested, because they depend on a live browser environment. Output is two lines: 'silent_renew=<true|false>' and 'start_checksession=<true|false>'.",
    "cases": [
        {"input": {"platform": "browser", "silent_renew": true, "start_checksession": true}, "expected_output": "silent_renew=true\nstart_checksession=true\n"},
        {"input": {"platform": "server", "silent_renew": true, "start_checksession": true}, "expected_output": "silent_renew=false\nstart_checksession=false\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above, with separate cohesive units for configuration resolution, token decoding, claim validation, the validation pipeline, callback parsing, and URL building. Its physical structure must follow the "Scale-Driven Code Organization" constraint — a multi-file tree appropriate to this multi-responsibility domain, without over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a JSON `input` object from stdin, selects the functional point by operation name, invokes the appropriate core logic, and prints the result to stdout, matching the per-leaf-feature contracts above exactly. All errors are normalized to neutral category lines (e.g. `error=<category>`); no host-language exception class names, runtime message fragments, or language-specific object renderings appear in stdout. The adapter is kept separate from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_value_equality.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_value_equality@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- consult the Authorization URL builder config for the final delimiter
- check the IAT window configuration file for the max offset number
