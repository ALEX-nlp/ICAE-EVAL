## Product Requirement Document

# Authenticating Reverse Gateway — Identity Authorization, Session Cookies & Request Routing

## Project Goal

Build the deterministic core of an authenticating reverse gateway that sits in front of upstream web applications. The gateway authorizes who may pass (by email/domain rules and by static credentials), encodes and verifies tamper-resistant session cookies, routes incoming requests, and challenges unauthenticated visitors with a sign-in page. The aim is to let application teams put a single uniform access-control layer in front of any backend without re-implementing identity checks, cookie signing, and request routing in every service.

---

## Background & Problem

Teams that want to protect an internal web application typically bolt authentication onto each service by hand. That leads to inconsistent rules for who is allowed in, ad-hoc and often insecure cookie handling, and duplicated request-routing logic. It is easy to get the security-sensitive parts wrong: a session cookie that is not signed can be forged; an email allow-list that is case-sensitive silently rejects legitimate users; a misconfigured gateway can start up and fail in confusing ways.

This project provides the reusable, well-specified core of such a gateway: a set of authorization rules, a signed/encrypted session-cookie format, configuration validation that reports *every* problem at once, and an HTTP front door that serves a few fixed unauthenticated endpoints and a sign-in challenge. Each piece is specified as a pure input-to-output contract so it can be tested in isolation, independent of any live identity provider or network.

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

### Feature 1: Email / Domain Authorization

**As a developer**, I want to decide whether a login identity is permitted based on configured domains and an explicit allow-list, so I can control exactly who gets through the gateway.

**Expected Behavior / Usage:**

Authorization is configured by two inputs: a set of permitted domains and an allow-list file of exact addresses (one per line). An address is authorized when its host part (the portion after the at-sign) matches one of the configured domains, OR when the full address is present in the allow-list. A single wildcard domain (`*`) authorizes every non-empty address. All comparisons are case-insensitive: both configured domains and allow-list entries, as well as the queried address, are folded to lower case before comparing. An empty address is never authorized. When both the domain set and the allow-list are empty, nothing is authorized. For a batch of queried addresses, the verdict (`allowed` or `denied`) is reported for each address on its own line, in the order queried.

**Test Cases:** `rcb_tests/public_test_cases/feature1_email_authorization.json`

```json
{
    "description": "Decide whether a login identity is authorized, given a set of permitted address suffixes (domains) and an allow-list file of exact addresses. An address is authorized when its host part matches one of the configured domains, or when the whole address appears in the allow-list. When the configured domain set contains the wildcard everything is authorized. Matching is case-insensitive on both sides. An empty address is never authorized; when both the domain set and the allow-list are empty nothing is authorized. For each queried address the verdict is reported on its own line.",
    "cases": [
        {
            "input": {"action": "validate_email", "domains": ["example.com"], "allowlist": [], "queries": ["foo.bar@example.com", "baz.quux@example.com"]},
            "expected_output": "foo.bar@example.com=allowed\nbaz.quux@example.com=allowed\n"
        },
        {
            "input": {"action": "validate_email", "domains": ["example0.com", "example1.com"], "allowlist": ["xyzzy@example.com", "plugh@example.com"], "queries": ["foo.bar@example0.com", "baz.quux@example1.com", "xyzzy@example.com", "plugh@example.com", "xyzzy.plugh@example.com"]},
            "expected_output": "foo.bar@example0.com=allowed\nbaz.quux@example1.com=allowed\nxyzzy@example.com=allowed\nplugh@example.com=allowed\nxyzzy.plugh@example.com=denied\n"
        }
    ]
}
```

---

### Feature 2: Static Credential Verification

**As a developer**, I want to verify a username and password against a static credential store, so users without an external identity can still authenticate.

**Expected Behavior / Usage:**

The credential store is a list of entries, each pairing a username with a stored secret of the form `{SHA}` immediately followed by the Base64 encoding of the SHA-1 digest of the password. A username/password pair is accepted only when the username exists in the store and the Base64-encoded SHA-1 digest of the supplied password exactly equals the stored digest. Entries whose stored secret does not use the supported hashing marker are never accepted. The output reports the username that was checked and a boolean verdict.

**Test Cases:** `rcb_tests/public_test_cases/feature2_basic_credential.json`

```json
{
    "description": "Verify a username/password pair against a credential store whose entries each pair a username with a salted hash marker followed by the Base64 of the SHA-1 digest of the password. A pair is accepted only when the username exists in the store and the SHA-1 digest of the supplied password, Base64-encoded, equals the stored digest. The checked username and the boolean verdict are reported.",
    "cases": [
        {
            "input": {"action": "check_credential", "entries": ["testuser:{SHA}PaVBVZkYqAjCQCu6UBL2xgsnZhw="], "user": "testuser", "password": "asdf"},
            "expected_output": "user=testuser\nauthenticated=true\n"
        }
    ]
}
```

---

### Feature 3: Session State Serialization

**As a developer**, I want to encode the authenticated session into a compact string for storage in a cookie and decode it back, so the gateway can carry identity and tokens between requests without server-side state.

**Expected Behavior / Usage:**

*3.1 Encrypted round-trip — encode and decode a full session under a symmetric key*

A session carries an identity address, an access token, a refresh token, and an absolute expiry instant. With a cipher available (keyed by a secret), the session encodes to a single string of four delimiter-separated fields. The identity and the expiry instant are stored in the clear; the access and refresh tokens are encrypted. Decoding with the same secret recovers every field exactly, and the local part of the identity address (before the at-sign) is exposed as the derived username. Decoding with a *different* secret still recovers the clear fields (identity, derived username, expiry) but the encrypted tokens do not recover to their original values. The output reports the field count, the recovered identity and username, the recovered expiry as an absolute number, and for each token either its recovered value or a not-recovered marker.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_session_encrypted_roundtrip.json`

```json
{
    "description": "Serialize a session (identity address, access token, refresh token, and an absolute expiry instant) into a single delimited string using a symmetric cipher keyed by a secret, then deserialize it back. The serialized form has four delimiter-separated fields; the access and refresh tokens are encrypted while the identity and expiry are stored in the clear. When the same secret is used to decode, every field round-trips exactly. When a different secret is used to decode, the clear fields (identity, derived user, expiry) still round-trip but the encrypted tokens do not recover to their originals. The reported output gives the field count, the recovered identity and user, the recovered expiry as an absolute number, and either the recovered token value or a not-recovered marker for each token.",
    "cases": [
        {
            "input": {"action": "session_encrypted_roundtrip", "secret": "0123456789abcdefghijklmnopqrstuv", "email": "user@domain.com", "access_token": "token1234", "refresh_token": "refresh4321", "expires_unix": 4102444800},
            "expected_output": "[standard webhook payload format]\n[standard webhook payload format]\n[standard webhook payload format]\n[standard webhook payload format]\n[standard webhook payload format]\n[standard webhook payload format]\n"
        },
        {
            "input": {"action": "session_encrypted_roundtrip", "secret": "0123456789abcdefghijklmnopqrstuv", "decode_secret": "0000000000abcdefghijklmnopqrstuv", "email": "user@domain.com", "access_token": "token1234", "refresh_token": "refresh4321", "expires_unix": 4102444800},
            "expected_output": "[standard webhook payload format]\n[standard webhook payload format]\n[standard webhook payload format]\n[standard webhook payload format]\naccess_token=<not-recovered>\nrefresh_token=<not-recovered>\n"
        }
    ]
}
```

*3.2 Identity-only encoding without a cipher*

When no cipher is available, only the session identity is persisted (the tokens are dropped). The identity is the address when one is present, otherwise the bare username. Decoding the result yields the same identity; when the identity is an email-style address, the local part is also exposed as the derived username. The output reports the persisted identity string and the recovered address and username.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_session_identity.json`

```json
{
    "description": "Serialize a session WITHOUT a cipher. With no encryption key available, only the session identity is persisted: the address is preferred when present, otherwise the bare username is used. Deserializing the result yields the same identity, and when the identity is an email-style address the local part (before the at-sign) is also exposed as the username. The reported output shows the persisted identity string plus the recovered address and username.",
    "cases": [
        {
            "input": {"action": "session_identity", "email": "user@domain.com", "user": "just-user"},
            "expected_output": "identity=user@domain.com\n[standard webhook payload format]\n[standard webhook payload format]\n"
        },
        {
            "input": {"action": "session_identity", "email": "", "user": "just-user"},
            "expected_output": "identity=just-user\nemail=\nuser=just-user\n"
        }
    ]
}
```

*3.3 Expiry check*

Given a session's expiry instant, report whether it is expired relative to the current moment. An expiry in the past means expired; an expiry in the future means not expired; a session with no expiry instant at all is never expired. The output reports whether an expiry was set and the resulting verdict.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_session_expiry.json`

```json
{
    "description": "Report whether a session is expired relative to the current moment, given its expiry instant. A session with an expiry instant in the past is expired; one with an expiry in the future is not. A session that carries no expiry instant at all is never considered expired. The output reports whether an expiry was set and the resulting expired verdict.",
    "cases": [
        {
            "input": {"action": "session_expiry", "expires_unix": 1000000000},
            "expected_output": "has_expiry=true\nexpired=true\n"
        },
        {
            "input": {"action": "session_expiry"},
            "expected_output": "has_expiry=false\nexpired=false\n"
        }
    ]
}
```

---

### Feature 4: Reversible Value Encryption

**As a developer**, I want to encrypt an opaque value and later recover it with the same key, so sensitive tokens are never stored in the clear inside a cookie.

**Expected Behavior / Usage:**

Given a secret key and an arbitrary string value, encrypting then decrypting with the same key recovers the original value exactly. The ciphertext must differ from the plaintext (the value is never stored verbatim). The output reports the decrypted value and whether the ciphertext differed from the plaintext.

**Test Cases:** `rcb_tests/public_test_cases/feature4_value_encryption.json`

```json
{
    "description": "Encrypt an opaque string value with a symmetric cipher keyed by a secret, then decrypt it with the same secret. The decrypted result must equal the original value, and the ciphertext must differ from the plaintext (the value is not stored in the clear). The output reports the decrypted value and whether the ciphertext differed from the plaintext.",
    "cases": [
        {
            "input": {"action": "encrypt_roundtrip", "secret": "0123456789abcdefghijklmnopqrstuv", "value": "my access token"},
            "expected_output": "[typical encryption artifact output]\n[typical encryption artifact output]\n"
        }
    ]
}
```

---

### Feature 5: HTTP Front Door

**As a developer**, I want the gateway's front door to serve a few fixed unauthenticated endpoints and to challenge unauthenticated visitors, so protected resources are never exposed by accident.

**Expected Behavior / Usage:**

*5.1 Crawler-exclusion endpoint*

A request to the well-known robots path is served without any authentication and returns a success status with a body that disallows all crawling. The output reports the HTTP status code and the response body.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_robots.json`

```json
{
    "description": "A fixed unauthenticated endpoint serves a crawler-exclusion document without requiring any authentication. A request to the well-known robots path returns a success status and a body that disallows all crawling. The output reports the HTTP status code and the response body.",
    "cases": [
        {
            "input": {"action": "http_request", "path": "/robots.txt", "extract": "body"},
            "expected_output": "status=200\nbody=User-agent: *\nDisallow: /\n"
        }
    ]
}
```

*5.2 Sign-in challenge with redirect target*

When an unauthenticated visitor requests a protected path, the gateway responds with a forbidden status and renders a sign-in challenge page that embeds, as a hidden post-sign-in redirect target, the exact path that was originally requested. When the request directly targets the dedicated sign-in path, the response status is success and the embedded redirect target collapses to the site root. The output reports the HTTP status code and the redirect target extracted from the rendered page.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_signin_challenge.json`

```json
{
    "description": "When an unauthenticated visitor reaches a protected resource, the gateway answers with a sign-in challenge page instead of proxying. For a request to an arbitrary protected path the response status is forbidden and the rendered challenge embeds, as its post-sign-in redirect target, the exact path that was originally requested. For a request that directly targets the dedicated sign-in path, the response status is success and the embedded redirect target collapses to the site root. The output reports the HTTP status code and the embedded redirect target extracted from the rendered page.",
    "cases": [
        {
            "input": {"action": "http_request", "path": "/some/random/endpoint", "extract": "redirect"},
            "expected_output": "status=403\nredirect=/some/random/endpoint\n"
        },
        {
            "input": {"action": "http_request", "path": "/oauth2/sign_in", "extract": "redirect"},
            "expected_output": "status=200\nredirect=/\n"
        }
    ]
}
```

---

### Feature 6: Configuration Validation

**As a developer**, I want the gateway configuration validated up front with all problems reported at once, so misconfiguration fails fast and clearly instead of at runtime.

**Expected Behavior / Usage:**

Validation collects every problem rather than stopping at the first. The required settings are: at least one upstream target, a cookie secret, a client id, and a client secret; each missing one is reported as its own problem keyed by the setting name. Each upstream target is parsed into a structured URL (scheme, host, path) and a missing path is normalized to the root path. An optional redirect URL is parsed into a structured URL. Optional skip-authentication patterns are compiled as regular expressions, and each invalid pattern is a separate problem. When token pass-through or a non-zero cookie-refresh interval is enabled, the cookie secret length must be one of the accepted symmetric-key sizes (16, 24, or 32). The cookie-refresh interval must be strictly less than the cookie-expiry interval. If group restriction is requested (a non-empty group list, an admin address, or a credentials-file path), then the group list, the admin address, and an existing credentials file must all be present. On success the output reports `valid=true` followed by the parsed redirect (when supplied), one line per resolved upstream, and one line per compiled pattern. On failure the output reports `[common validation error cases]` followed by one neutral error category line per problem, in the order the problems were found. Error categories are language-neutral (for example `missing_setting`, `invalid_url`, `invalid_regex`, `invalid_cookie_secret_length`, `refresh_not_less_than_expire`, `invalid_credentials_file`) and never leak runtime-specific details.

**Test Cases:** `rcb_tests/public_test_cases/feature6_config_validation.json`

```json
{
    "description": "Validate a gateway configuration and report the outcome. Validation aggregates every problem found rather than stopping at the first. Required settings (at least one upstream target, a cookie secret, a client id, and a client secret) must be present. Upstream targets are parsed into structured URLs and a missing path is normalized to the root path. An optional redirect URL is parsed into a structured URL. Optional skip-authentication patterns are compiled as regular expressions; an invalid pattern is a validation error. When token pass-through or cookie refresh is enabled the cookie secret length must be one of the accepted cipher key sizes. The cookie refresh interval must be strictly less than the cookie expiry interval. If group restriction is requested, the administrator address and the service-account credentials file must be present and the file must exist. On success the output reports valid plus the parsed redirect, upstreams, and compiled patterns; on failure it reports invalid plus one neutral error category per problem.",
    "cases": [
        {
            "input": {"action": "validate_config", "config": {"email_domains": ["*"]}},
            "expected_output": "[common validation error cases]\n[common validation error cases]\n[common validation error cases]\n[common validation error cases]\n[common validation error cases]\n"
        },
        {
            "input": {"action": "validate_config", "config": {"upstreams": ["http://127.0.0.1:8080/"], "cookie_secret": "foobar", "client_id": "bazquux", "client_secret": "xyzzyplugh", "email_domains": ["*"], "redirect_url": "https://myhost.com/oauth2/callback"}},
            "expected_output": "valid=true\nredirect=https|myhost.com|/oauth2/callback\nupstream=http|127.0.0.1:8080|/\n"
        },
        {
            "input": {"action": "validate_config", "config": {"upstreams": ["http://127.0.0.1:8080/"], "cookie_secret": "foobar", "client_id": "bazquux", "client_secret": "xyzzyplugh", "email_domains": ["*"], "skip_auth_regex": ["(foobaz", "barquux)"]}},
            "expected_output": "[common validation error cases]\nerror=invalid_regex\nerror=invalid_regex\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above (identity authorization, static credential verification, session-state serialization, reversible value encryption, the HTTP front door, and configuration validation). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting contract to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `validate_email`, `check_credential`, `session_encrypted_roundtrip`, `session_identity`, `session_expiry`, `encrypt_roundtrip`, `http_request` (driven by `path`, optional `method`, and an `extract` of `body` or `redirect`), and `validate_config`. The adapter is the only place that normalizes native errors into the neutral `error=<category>` lines; the core domain may raise idiomatic errors but their runtime identity must never appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the URL construction pattern used in inbound OAuth2 endpoints
- match the regex invalidation logic found in step 4 of the validation flow
