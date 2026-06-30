## Product Requirement Document

# OAuth 2 Authorization Web Helper — Request URL Building, Redirect Parsing & Encoding Utilities

## Project Goal

Build a small, dependency-free helper library that prepares and interprets the browser-side pieces of an OAuth 2 authorization flow, so application developers can construct a correct provider authorization URL, read back the parameters a provider returns on redirect, resolve per-platform configuration overrides, and produce the Base64/Base64URL encodings these flows rely on — all as pure, deterministic functions that are easy to test in isolation.

---

## Background & Problem

An OAuth 2 client running in a browser context has to do several fiddly, easy-to-get-wrong string operations: assemble an authorization request URL with exactly the right query parameters in a stable order, percent-encode it, merge a base configuration with platform-specific overrides, and later pull the authorization `code`, `state`, or `access_token` back out of the URL the provider redirects to. It also needs Base64 and URL-safe Base64 encoding for PKCE-style values.

Without a shared helper, each application re-implements this by hand, leading to subtly malformed URLs, inconsistent override precedence, and brittle redirect parsing. This library provides one well-defined, deterministic contract for each of those operations so the surrounding application can stay simple and correct.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Platform-Overridable Option Resolution

**As a developer**, I want to resolve a configuration value where a platform-specific section may override the shared base value, so I can keep one base configuration and selectively override individual settings per platform.

**Expected Behavior / Usage:**

The input is a request naming a single option `key` plus an `options` object. The `options` object holds base values directly and may also hold a nested override section. Resolution rule: if the override section contains the requested key, the override section's value is used; otherwise the base value is used. The override wins even when its value is an empty string or the boolean `false`/`true` — presence of the key in the override section is what matters, not truthiness. If the key is absent from the override section, the base value is returned unchanged. When the resolved value is itself a map of extra parameters, the override section's map fully replaces the base map (it is not merged), so keys present only in the base map are not part of the result. A scalar result is emitted as a plain `value=<resolved value>` line (an empty string yields `value=` with nothing after it); a map result is emitted as `value=<object>` where the object is rendered as JSON with its keys sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_option_resolution.json`

```json
{
    "description": "Resolve a single configuration option value where a platform-specific override section may supersede the base value. Each request names the option key to resolve. When the override section contains that key, its value wins; when the override section does not contain the key, the base value is used. A scalar result is emitted as a plain value line, while a map result is emitted as a key-sorted object.",
    "cases": [
        {
            "input": {
                "action": "resolve_option",
                "key": "appId",
                "options": {
                    "appId": "appId",
                    "accessTokenEndpoint": "https://www.googleapis.com/oauth2/v4/token",
                    "scope": "email profile",
                    "pkceDisabled": false,
                    "web": {"accessTokenEndpoint": "", "appId": "webAppId", "pkceDisabled": true}
                }
            },
            "expected_output": "value=webAppId\n"
        },
        {
            "input": {
                "action": "resolve_option",
                "key": "additionalParameters",
                "options": {
                    "additionalParameters": {"willbeoverwritten": "foobar"},
                    "web": {"additionalParameters": {"resource": "resource_id", "emptyParam": null, " ": "test", "nonce": "fixednonce"}}
                }
            },
            "expected_output": "value={\" \":\"test\",\"emptyParam\":null,\"nonce\":\"fixednonce\",\"resource\":\"resource_id\"}\n"
        }
    ]
}
```

---

### Feature 2: Authorization Request URL Construction

**As a developer**, I want to build the provider authorization URL from a resolved set of options, so the browser can be sent to the provider with all required query parameters in a correct, stable order.

**Expected Behavior / Usage:**

The input is a request carrying a `webOptions` object of already-resolved authorization settings. The output is `url=<built url>`. The URL is the authorization base endpoint, then `?`, then a query string assembled in this fixed order: `client_id` (the application identifier), `response_type` (e.g. `code` or `token`), then — only when the corresponding option is present — `redirect_uri`, then `scope`; then `state` (always present); then every entry of an optional extra-parameters map, appended in iteration order as `&key=value`; then — only when a PKCE challenge is present — `code_challenge` followed by `code_challenge_method`. The fully assembled URL is percent-encoded, so a space inside a value (such as a multi-word scope) appears as `%20`. Optional segments that are absent contribute nothing to the URL. The ordering is deterministic so the same options always produce a byte-identical URL.

**Test Cases:** `rcb_tests/public_test_cases/feature2_authorization_url.json`

```json
{
    "description": "Build the provider authorization request URL from a fully resolved set of authorization options. The URL begins with the authorization base endpoint followed by a query string that always carries the client identifier, the response type and the state. Optional segments are appended only when present: a redirect target, a requested scope, any number of extra key/value parameters in the order supplied, and a PKCE challenge together with its challenge method. The whole URL is percent-encoded so spaces inside values appear as escape sequences. Parameter order is fixed and deterministic.",
    "cases": [
        {
            "input": {
                "action": "build_authorization_url",
                "webOptions": {
                    "authorizationBaseUrl": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                    "appId": "webAppId",
                    "responseType": "code",
                    "redirectUrl": "https://oauth2.byteowls.com/authorize",
                    "scope": "files.readwrite offline_access",
                    "state": "STATE123",
                    "additionalParameters": {"resource": "resource_id", "nonce": "NONCE1"},
                    "pkceCodeChallenge": "CHAL",
                    "pkceCodeChallengeMethod": "S256"
                }
            },
            "expected_output": "url=https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=webAppId&response_type=code&redirect_uri=https://oauth2.byteowls.com/authorize&scope=files.readwrite%20offline_access&state=STATE123&resource=resource_id&nonce=NONCE1&code_challenge=CHAL&code_challenge_method=S256\n"
        },
        {
            "input": {
                "action": "build_authorization_url",
                "webOptions": {
                    "authorizationBaseUrl": "https://accounts.google.com/o/oauth2/auth",
                    "appId": "webAppId",
                    "responseType": "token",
                    "state": "STATE123"
                }
            },
            "expected_output": "url=https://accounts.google.com/o/oauth2/auth?client_id=webAppId&response_type=token&state=STATE123\n"
        }
    ]
}
```

---

### Feature 3: Redirect URL Parameter Extraction

**As a developer**, I want to read the parameters a provider returns on its redirect URL, so I can recover the `code`, `state`, and `access_token` values after authorization.

**Expected Behavior / Usage:**

The input is a request carrying a `url` string (which may also be `null`). The parameter section is located by taking everything after the fragment marker `#` if one is present; otherwise everything after the first query marker `?`. That section is split on `&` into pairs, and each pair is split on the first `=` into a key and a value; values are percent-decoded. Any pair whose key is empty is discarded. No parameter set is produced — the output is `params=undefined` — when the input is `null`, empty, whitespace only, contains no `#`/`?` marker, or has an empty parameter section (for example a trailing `?` with nothing after it, or a section consisting solely of an empty-key pair). Otherwise the result is `params=<object>`, where the object lists the surviving key/value pairs rendered as JSON with keys sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_url_param_extraction.json`

```json
{
    "description": "Extract the parameters carried by a redirect URL. The parameter section is taken from the fragment portion when a hash marker is present, otherwise from the query portion after a question mark. Each parameter is split on the first equals sign; values are percent-decoded. Pairs whose key is empty are discarded. When the input has no usable parameter section, no parameter set is produced. A produced parameter set is rendered as a key-sorted object.",
    "cases": [
        {"input": {"action": "extract_url_params", "url": "https://app.example.com?=test"}, "expected_output": "params=undefined\n"},
        {"input": {"action": "extract_url_params", "url": "https://app.example.com?state=STATEXYZ&access_token=testtoken"}, "expected_output": "params={\"access_token\":\"testtoken\",\"state\":\"STATEXYZ\"}\n"}
    ]
}
```

---

### Feature 4: Standard Base64 Encoding

**As a developer**, I want to encode an ASCII string into standard Base64, so I can produce the encoded values these flows depend on.

**Expected Behavior / Usage:**

The input is a request carrying a `text` string. The bytes of the string are grouped into triplets and each triplet maps to four characters from the standard Base64 alphabet (`A`–`Z`, `a`–`z`, `0`–`9`, `+`, `/`). When the final group has only one or two leftover bytes, the result is padded with `==` or `=` respectively so the total length is a multiple of four. The output is `base64=<encoded value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_base64_encode.json`

```json
{
    "description": "Encode an ASCII text string into standard Base64. The text is taken byte by byte and grouped into triplets; each triplet maps to four Base64 characters drawn from the standard alphabet. When the final group has one or two leftover bytes, the output is padded with the appropriate number of equals signs so the result length is a multiple of four.",
    "cases": [
        {"input": {"action": "base64_encode", "text": "tester"}, "expected_output": "base64=dGVzdGVy\n"},
        {"input": {"action": "base64_encode", "text": "testerposfieppw2874929"}, "expected_output": "base64=dGVzdGVycG9zZmllcHB3Mjg3NDkyOQ==\n"}
    ]
}
```

---

### Feature 5: URL-Safe Base64 Conversion

**As a developer**, I want to convert a standard Base64 string into its URL-safe form, so the encoded value can be embedded directly in a URL without escaping.

**Expected Behavior / Usage:**

The input is a request carrying a `base64` string in standard Base64 form. The conversion replaces every `+` with `-`, every `/` with `_`, and removes all trailing `=` padding characters. The output is `base64url=<converted value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_base64url.json`

```json
{
    "description": "Convert a standard Base64 string into its URL-safe variant. Every plus sign becomes a minus sign, every forward slash becomes an underscore, and all trailing padding equals signs are removed, leaving a token that can be carried safely inside a URL.",
    "cases": [
        {"input": {"action": "base64url", "base64": "YmFz+TY0IG/uY29kZXI="}, "expected_output": "base64url=YmFz-TY0IG_uY29kZXI\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (option override resolution, authorization URL construction, redirect parameter extraction, Base64 and URL-safe Base64 encoding). Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting line to stdout, matching the per-feature contracts above. The request's `action` field selects behavior: `resolve_option` resolves one option key against an `options` object; `build_authorization_url` builds a URL from a `webOptions` object; `extract_url_params` parses a redirect `url`; `base64_encode` encodes a `text` string to standard Base64; `base64url` converts a standard `base64` string to the URL-safe form. Object-valued results (resolved maps, extracted parameter sets) are rendered as JSON with keys sorted so output is deterministic.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the kernel module documentation for 'webOverrides'
- verify the alias mapping in the core identity provider
