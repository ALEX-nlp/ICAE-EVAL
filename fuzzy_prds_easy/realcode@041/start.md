## Product Requirement Document

# Token Session Authentication Service - HTTP Login, Logout, and Token Lifecycle Behavior

## Project Goal

Build a token-based session authentication service that allows developers to protect HTTP resources, issue revocable bearer-style session tokens, and enforce token lifecycle policies without storing plaintext credentials or hand-writing token cleanup, expiry, and logout logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually create tokens during login, persist lookup metadata, parse authorization headers, reject malformed or expired credentials, revoke one or many sessions, and coordinate expiry refresh rules across protected endpoints. This leads to repetitive security-sensitive code, inconsistent HTTP responses, stale tokens accumulating in storage, and fragile session limit handling.

With this library/tool, developers get a consistent HTTP authentication flow: credential-based login returns a token contract, protected resources validate tokens through the framework request path, logout endpoints remove the correct persisted sessions, and configurable expiry, prefix, and active-session policies remain observable through stable input/output behavior.

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

### Feature 1: Login Token Issuance

**As a developer**, I want valid credential exchanges to issue persisted session tokens with predictable HTTP response fields, so I can authenticate later requests and inspect token lifecycle metadata.

**Expected Behavior / Usage:**

The input describes a login operation, optional frozen time for deterministic expiry output, an optional repeat count, and optional settings such as session lifetime, response profile inclusion, expiry display format, and issued token prefix. A successful login must go through the `/api/login/` HTTP route and print the route, HTTP status, routed URL, expiry representation, token presence, token prefix signal, token length, persisted token count, and whether stored lookup keys are present. Repeated logins create independent persisted tokens. If no custom account profile output is enabled, the response contains token and expiry signals only; if profile output is enabled, the authenticated account identifier is included as a nested user signal. If sessions do not expire, `expiry` is printed as `null` while the field remains present.

**Test Cases:** `rcb_tests/public_test_cases/feature1_login_issuance.json`

```json
{
    "description": "Login issues session tokens and returns configured response fields.",
    "cases": [
        {
            "description": "A valid credential exchange creates one persisted session token and returns a successful HTTP response with an expiry timestamp.",
            "input": {
                "operation": "login",
                "frozen_time": "2020-01-01T00:00:00"
            },
            "expected_output": "route=/api/login/\nlogin.status=200\nlogin.url=/api/login/\nlogin.expiry=\"2020-01-01T10:00:00Z\"\nlogin.token_present=true\nlogin.token_prefix=\nlogin.token_length=64\ntoken_count=1\nstored_token_keys_present=true\n"
        },
        {
            "description": "Repeated valid credential exchanges create independent persisted session tokens.",
            "input": {
                "operation": "login",
                "repeat": 5,
                "frozen_time": "2020-01-01T00:00:00"
            },
            "expected_output": "route=/api/login/\nlogin.status=200\nlogin.url=/api/login/\nlogin.expiry=\"2020-01-01T10:00:00Z\"\nlogin.token_present=true\nlogin.token_prefix=\nlogin.token_length=64\ntoken_count=5\nstored_token_keys_present=true\n"
        }
    ]
}
```

---

### Feature 2: Logout Revocation Scope

**As a developer**, I want logout requests to revoke exactly the intended persisted sessions, so I can support both current-session logout and all-sessions logout without affecting unrelated accounts.

**Expected Behavior / Usage:**

The input describes a logout operation, a scope, and how many existing tokens should be created before the request. A single-session logout must use the `/api/logout/` route and return HTTP 204 while deleting only the presented token. An all-sessions logout must use the `/api/logoutall/` route and return HTTP 204 while deleting all persisted tokens for the authenticated account. Other accounts' tokens must remain outside the revocation scope.

**Test Cases:** `rcb_tests/public_test_cases/feature2_logout_scope.json`

```json
{
    "description": "Logout endpoints revoke the intended set of persisted session tokens.",
    "cases": [
        {
            "description": "A single-session logout revokes only the presented session token and leaves other sessions for the same account intact.",
            "input": {
                "operation": "logout",
                "scope": "single",
                "tokens_for_user": 2
            },
            "expected_output": "route=/api/logout/\nlogout.status=204\nlogout.url=/api/logout/\nlogout.body=null\nbefore.total_tokens=2\nafter.total_tokens=1\n"
        },
        {
            "description": "An all-sessions logout revokes every session token belonging to the authenticated account.",
            "input": {
                "operation": "logout",
                "scope": "all_for_user",
                "tokens_for_user": 10
            },
            "expected_output": "route=/api/logoutall/\nlogout.status=204\nlogout.url=/api/logoutall/\nlogout.body=null\nbefore.total_tokens=10\nafter.total_tokens=0\n"
        }
    ]
}
```

---

### Feature 3: Protected Resource Authentication

**As a developer**, I want protected HTTP resources to accept valid session tokens according to configured authorization schemes, so I can rely on the framework authentication layer instead of bypassing it.

**Expected Behavior / Usage:**

The input describes an authenticated request operation, optional authorization scheme settings, and one or more header schemes to try. A valid token presented to `/api/` must return HTTP 200 from the routed protected resource with the authenticated body text. If a custom authorization scheme is configured, the default scheme is ignored and the framework returns an unauthenticated HTTP 401 response; the configured scheme must then authenticate the same token successfully. The output includes HTTP status, routed URL, and either protected resource body or authentication detail so direct non-framework stubs cannot satisfy the contract.

**Test Cases:** `rcb_tests/public_test_cases/feature3_protected_resource_authentication.json`

```json
{
    "description": "Protected resource requests accept valid session tokens and configured authorization schemes.",
    "cases": [
        {
            "description": "A request to a protected resource with a valid session token succeeds through the HTTP authentication layer.",
            "input": {
                "operation": "authenticated_request"
            },
            "expected_output": "request1.status=200\nrequest1.url=/api/\nrequest1.body=User is authenticated.\n"
        },
        {
            "description": "When a custom authorization scheme is configured, the default scheme is rejected and the configured scheme is accepted for the same token.",
            "input": {
                "operation": "authenticated_request",
                "settings": {
                    "authorization_scheme": "Baerer"
                },
                "header_prefixes": [
                    "Token",
                    "Baerer"
                ]
            },
            "expected_output": "request1.status=401\nrequest1.url=/api/\nrequest1.detail=Authentication credentials were not provided.\nrequest2.status=200\nrequest2.url=/api/\nrequest2.body=User is authenticated.\n"
        }
    ]
}
```

---

### Feature 4: Authorization Header Validation

**As a developer**, I want authorization headers to be parsed consistently before token lookup, so malformed headers fail deterministically and empty headers can be delegated to other authentication mechanisms.

**Expected Behavior / Usage:**

The input describes a raw authorization header. An empty header produces `auth_result=none`, meaning the token authenticator did not attempt credential validation. A header that contains only the scheme fails with the normalized error `missing_credentials`. A header with spaces inside the credential portion fails with the normalized error `credentials_contain_spaces`. These errors are rendered as language-neutral categories rather than runtime exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature4_authorization_header_validation.json`

```json
{
    "description": "Authorization headers are parsed consistently before token lookup.",
    "cases": [
        {
            "description": "An empty authorization header is ignored by the token authenticator instead of producing a failed token lookup.",
            "input": {
                "operation": "header_parse",
                "authorization": ""
            },
            "expected_output": "auth_result=none\n"
        },
        {
            "description": "A header that contains only the authorization scheme is rejected as missing credentials.",
            "input": {
                "operation": "header_parse",
                "authorization": "Token"
            },
            "expected_output": "error=missing_credentials\n"
        },
        {
            "description": "A header whose credential portion contains spaces is rejected as malformed credentials.",
            "input": {
                "operation": "header_parse",
                "authorization": "Token wordone wordtwo"
            },
            "expected_output": "error=credentials_contain_spaces\n"
        }
    ]
}
```

---

### Feature 5: Invalid and Expired Token Rejection

**As a developer**, I want invalid or expired tokens to be rejected through protected HTTP endpoints, so stale or tampered credentials cannot authenticate requests.

**Expected Behavior / Usage:**

The input describes a protected request using a token variant such as already expired, shorter than the lookup key length, or modified after issuance. Each invalid token request must go through `/api/`, return HTTP 401, include the routed URL, and expose the domain authentication detail `Invalid token.`. Expired-token cleanup and expiration notifications are part of the broader hidden contract for this feature; visible cases focus on the externally observable HTTP rejection signals.

**Test Cases:** `rcb_tests/public_test_cases/feature5_invalid_and_expired_tokens.json`

```json
{
    "description": "Invalid or expired tokens are rejected and expired token cleanup is observable.",
    "cases": [
        {
            "description": "A request with an already expired token is rejected by the protected HTTP endpoint.",
            "input": {
                "operation": "invalid_token",
                "token_kind": "expired"
            },
            "expected_output": "route=/api/\nrequest.status=401\nrequest.url=/api/\nrequest.detail=Invalid token.\n"
        },
        {
            "description": "A request with a token shorter than the lookup key length is rejected by the protected HTTP endpoint.",
            "input": {
                "operation": "invalid_token",
                "token_kind": "too_short"
            },
            "expected_output": "route=/api/\nrequest.status=401\nrequest.url=/api/\nrequest.detail=Invalid token.\n"
        },
        {
            "description": "A request with a modified token value that cannot match the stored digest is rejected by the protected HTTP endpoint.",
            "input": {
                "operation": "invalid_token",
                "token_kind": "odd_length_existing_plus_one"
            },
            "expected_output": "route=/api/\nrequest.status=401\nrequest.url=/api/\nrequest.detail=Invalid token.\n"
        }
    ]
}
```

---

### Feature 6: Session Expiry Refresh Rules

**As a developer**, I want session expiry timestamps to refresh only under configured rules, so active sessions can be extended without uncontrolled lifetime growth or unnecessary storage writes.

**Expected Behavior / Usage:**

The input describes an original issuance time, refresh settings, and a sequence of protected-resource checks at offsets from issuance. With automatic refresh enabled, a successful authenticated request extends stored expiry by the configured lifetime; later checks can remain valid beyond the original expiry, and the token is rejected after the renewed expiry has passed. With automatic refresh disabled, successful authentication does not change the stored expiry. The output records each framework response status and URL, protected body or invalid-token detail, current stored expiry after each check, and the original expiry.

**Test Cases:** `rcb_tests/public_test_cases/feature6_session_expiry_refresh.json`

```json
{
    "description": "Session expiry times are renewed only under the configured refresh rules.",
    "cases": [
        {
            "description": "With automatic refresh enabled, a successful authenticated request extends the stored expiry and the token remains usable beyond its original expiry until the renewed expiry is passed.",
            "input": {
                "operation": "expiry_refresh",
                "settings": {
                    "auto_extend_sessions": true
                },
                "original_time": "2018-07-25T00:00:00",
                "checks": [
                    {
                        "at": {
                            "hours": 5
                        }
                    },
                    {
                        "at": {
                            "hours": 11
                        }
                    },
                    {
                        "at": {
                            "hours": 21,
                            "seconds": 1
                        }
                    }
                ]
            },
            "expected_output": "check1.status=200\ncheck1.url=/api/\ncheck1.body=User is authenticated.\ncheck1.stored_expiry=2018-07-25T15:00:00\ncheck2.status=200\ncheck2.url=/api/\ncheck2.body=User is authenticated.\ncheck2.stored_expiry=2018-07-25T21:00:00\ncheck3.status=401\ncheck3.url=/api/\ncheck3.detail=Invalid token.\ncheck3.stored_expiry=null\noriginal_expiry=2018-07-25T10:00:00\n"
        },
        {
            "description": "With automatic refresh disabled, a successful authenticated request does not change the stored expiry timestamp.",
            "input": {
                "operation": "expiry_refresh",
                "settings": {
                    "auto_extend_sessions": false
                },
                "original_time": "2018-07-25T00:00:00",
                "checks": [
                    {
                        "at": {
                            "hours": 1
                        }
                    }
                ]
            },
            "expected_output": "check1.status=200\ncheck1.url=/api/\ncheck1.body=User is authenticated.\ncheck1.stored_expiry=2018-07-25T10:00:00\noriginal_expiry=2018-07-25T10:00:00\n"
        }
    ]
}
```

---

### Feature 7: Active Session Limit Per Account

**As a developer**, I want login to enforce a configurable maximum number of active sessions per account, so compromised or excessive session proliferation can be prevented while expired sessions do not block legitimate logins.

**Expected Behavior / Usage:**

The input describes a login operation under a configured active-session limit, pre-existing active session count, pre-existing expired session count, number of login attempts, and optional frozen time. If active sessions already meet the limit, login through `/api/login/` returns HTTP 403 with the domain error message and does not create a new token. Expired sessions do not count toward the active-session limit; a login can fill the remaining slot and a subsequent login is rejected. Output includes per-attempt HTTP status and URL plus active and total token counts after the attempts.

**Test Cases:** `rcb_tests/public_test_cases/feature7_session_limit_per_account.json`

```json
{
    "description": "Login enforces a maximum number of active sessions per account.",
    "cases": [
        {
            "description": "When an account already has the configured maximum number of active sessions, a new login is rejected with a forbidden HTTP response.",
            "input": {
                "operation": "token_limit",
                "settings": {
                    "session_limit_per_account": 10
                },
                "valid_existing": 10,
                "login_attempts": 1,
                "frozen_time": "2020-01-01T00:00:00"
            },
            "expected_output": "login1.status=403\nlogin1.url=/api/login/\nlogin1.error=Maximum amount of tokens allowed per user exceeded.\nvalid_tokens_after=10\ntotal_tokens_after=10\n"
        },
        {
            "description": "Expired sessions do not count toward the active-session limit; after the last available slot is filled, the next login is rejected.",
            "input": {
                "operation": "token_limit",
                "settings": {
                    "session_limit_per_account": 10
                },
                "valid_existing": 9,
                "expired_existing": 1,
                "login_attempts": 2,
                "frozen_time": "2020-01-01T00:00:00"
            },
            "expected_output": "login1.status=200\nlogin1.url=/api/login/\nlogin1.expiry=\"2020-01-01T10:00:00Z\"\nlogin1.token_present=true\nlogin1.token_prefix=\nlogin1.token_length=64\nlogin2.status=403\nlogin2.url=/api/login/\nlogin2.error=Maximum amount of tokens allowed per user exceeded.\nvalid_tokens_after=10\ntotal_tokens_after=11\n"
        }
    ]
}
```

---

### Feature 8: Token Storage Lookup Metadata

**As a developer**, I want persisted token lookup metadata to match the submitted token prefix used during authentication, so token lookup can be efficient while the full token remains secret.

**Expected Behavior / Usage:**

The input describes a token metadata verification operation. After a valid token is created and used for authentication, the output must report successful authentication, the fixed lookup key length, and whether the stored lookup key matches the leading characters of the submitted token.

**Test Cases:** `rcb_tests/public_test_cases/feature8_token_storage_metadata.json`

```json
{
    "description": "Stored token lookup metadata matches the submitted token prefix used for authentication.",
    "cases": [
        {
            "description": "After authenticating with a valid token, the persisted lookup key has the configured key length and matches the leading characters of the submitted token.",
            "input": {
                "operation": "token_key"
            },
            "expected_output": "auth_result=authenticated\ntoken_key_length=15\ntoken_key_matches_submitted_prefix=true\n"
        }
    ]
}
```

---

### Feature 9: Issued Token Prefix Validation

**As a developer**, I want issued-token prefix configuration to be validated before use, so invalid prefixes cannot create tokens with unsupported lookup metadata.

**Expected Behavior / Usage:**

The input describes a prefix validation operation and a proposed issued-token prefix. A prefix longer than the supported maximum is rejected with the normalized error `token_prefix_too_long`; output includes the maximum supported prefix length and the provided prefix length. The adapter must not expose host-language exception names or runtime-specific message suffixes.

**Test Cases:** `rcb_tests/public_test_cases/feature9_token_prefix_validation.json`

```json
{
    "description": "Issued-token prefix configuration is validated before use.",
    "cases": [
        {
            "description": "A configured issued-token prefix longer than the allowed maximum is rejected with a normalized configuration error.",
            "input": {
                "operation": "prefix_validation",
                "prefix": "aaaaaaaaaaa"
            },
            "expected_output": "error=token_prefix_too_long\nmax_prefix_length=10\nprefix_length=11\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the token_key length constant
