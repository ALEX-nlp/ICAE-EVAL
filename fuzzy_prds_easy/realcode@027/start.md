## Product Requirement Document

# OpenID Connect Authentication Adapter - Redirect and Callback Contract

## Project Goal

Build an OpenID Connect authentication integration that allows developers to initiate sign-in, handle sign-out, process callback responses, expose authenticated profile data, and select token verification material without hand-writing repetitive protocol and web-framework glue.

---

## Background & Problem

Without this library/tool, developers are forced to manually compose authorization URLs, preserve state and nonce values, validate callback parameters, map provider claims into application-facing identity fields, and translate protocol failures into framework redirects. This leads to duplicated security-sensitive code, inconsistent error behavior, and fragile integrations across applications.

With this library/tool, applications receive a consistent web authentication flow: sign-in requests become provider redirects, sign-out requests either route to provider logout or continue to the application, callbacks are validated before the application sees them, and provider data is exposed through stable output fields.

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

### Feature 1: Provider Endpoint Defaults

**As a developer**, I want to initialize a provider client with secure defaults, so I can begin a standard OpenID Connect flow without specifying every endpoint manually.

**Expected Behavior / Usage:**

The input selects the client-defaults flow. The output MUST list the default transport scheme, port, authorization endpoint, token endpoint, user-info endpoint, and key-discovery endpoint, one `key=value` line per field.

**Test Cases:** `rcb_tests/public_test_cases/feature1_provider_endpoint_defaults.json`

```json
{
    "description": "Reports the default network endpoints and transport settings used when no provider overrides are supplied.",
    "cases": [
        {
            "input": {
                "flow": "client_defaults"
            },
            "expected_output": "scheme=https\nport=443\nauthorization_endpoint=/authorize\ntoken_endpoint=/token\nuserinfo_endpoint=/userinfo\njwks_uri=/jwk\n"
        }
    ]
}
```

---

### Feature 2: Authorization Redirect Construction

**As a developer**, I want to build a provider authorization redirect from request and option data, so I can send users to the identity provider with the correct protocol parameters.

**Expected Behavior / Usage:**

The input selects the authorization-request flow and may include issuer/client settings, response type, response mode, and incoming request parameters such as login hints or locales. The output MUST include `status=302`, the provider authorization URL without query string, protocol fields that are present in the redirect, a state signal, and a nonce signal. Generated random state values are normalized to `generated_32_hex`; generated nonces are reported by length so the contract remains deterministic while still proving nonce generation occurred.

**Test Cases:** `rcb_tests/public_test_cases/feature2_authorization_redirect.json`

```json
{
    "description": "Builds an authorization redirect for sign-in, preserving protocol parameters and externally visible redirect metadata.",
    "cases": [
        {
            "input": {
                "flow": "authorization_request",
                "options": {
                    "issuer": "example.com",
                    "client": {
                        "host": "example.com"
                    }
                }
            },
            "expected_output": "status=302\nauthorization_url=https://example.com/authorize\nclient_id=1234\nresponse_type=code\nscope=openid\nstate=generated_32_hex\nnonce_length=32\n"
        },
        {
            "input": {
                "flow": "authorization_request",
                "options": {
                    "issuer": "example.com",
                    "client": {
                        "host": "example.com"
                    }
                },
                "request_params": {
                    "login_hint": "john.doe@example.com",
                    "ui_locales": "en",
                    "claims_locales": "es"
                }
            },
            "expected_output": "status=302\nauthorization_url=https://example.com/authorize\nclient_id=1234\nresponse_type=code\nscope=openid\nlogin_hint=john.doe@example.com\nui_locales=en\nclaims_locales=es\nstate=generated_32_hex\nnonce_length=32\n"
        },
        {
            "input": {
                "flow": "authorization_request",
                "options": {
                    "issuer": "example.com",
                    "response_mode": "form_post",
                    "response_type": "id_token",
                    "client": {
                        "host": "example.com"
                    }
                }
            },
            "expected_output": "status=302\nauthorization_url=https://example.com/authorize\nclient_id=1234\nresponse_type=id_token\nresponse_mode=form_post\nscope=openid\nstate=generated_32_hex\nnonce_length=32\n"
        }
    ]
}
```

---

### Feature 3: Logout Routing

**As a developer**, I want to handle logout paths consistently, so I can either redirect to provider logout or continue to the application when logout is unavailable.

**Expected Behavior / Usage:**

The input selects the logout-request flow and includes the requested path plus optional discovery metadata. If a valid provider end-session endpoint is discovered for the logout path, the output MUST include `status=302` and `logout_url=<endpoint>`, plus `post_logout_redirect_uri=<uri>` when configured. If no provider logout endpoint is available, the output MUST include `status=200` and `route=application`, proving the request was forwarded instead of redirected.

**Test Cases:** `rcb_tests/public_test_cases/feature3_logout_routing.json`

```json
{
    "description": "Handles sign-out paths by redirecting to a discovered end-session endpoint when one exists, otherwise forwarding the request to the downstream application.",
    "cases": [
        {
            "input": {
                "flow": "logout_request",
                "path": "/auth/openid_connect/logout",
                "options": {
                    "discovery": true,
                    "client": {
                        "host": "example.com"
                    }
                },
                "discovery": {
                    "issuer": "https://example.com/",
                    "authorization_endpoint": "https://example.com/authorization",
                    "token_endpoint": "https://example.com/token",
                    "userinfo_endpoint": "https://example.com/userinfo",
                    "jwks_uri": "https://example.com/jwks",
                    "end_session_endpoint": "https://example.com/logout",
                    "jwks_json": "{\"keys\": [{\n    \"kty\": \"RSA\",\n    \"n\": \"0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw\",\n    \"e\": \"AQAB\",\n    \"alg\": \"RS256\",\n    \"kid\": \"1e9gdk7\"\n  }]\n}\n"
                }
            },
            "expected_output": "status=302\nlogout_url=https://example.com/logout\n"
        },
        {
            "input": {
                "flow": "logout_request",
                "path": "/auth/openid_connect/logout",
                "options": {
                    "discovery": true,
                    "post_logout_redirect_uri": "https://mysite.com",
                    "client": {
                        "host": "example.com"
                    }
                },
                "discovery": {
                    "issuer": "https://example.com/",
                    "authorization_endpoint": "https://example.com/authorization",
                    "token_endpoint": "https://example.com/token",
                    "userinfo_endpoint": "https://example.com/userinfo",
                    "jwks_uri": "https://example.com/jwks",
                    "end_session_endpoint": "https://example.com/logout",
                    "jwks_json": "{\"keys\": [{\n    \"kty\": \"RSA\",\n    \"n\": \"0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw\",\n    \"e\": \"AQAB\",\n    \"alg\": \"RS256\",\n    \"kid\": \"1e9gdk7\"\n  }]\n}\n"
                }
            },
            "expected_output": "status=302\nlogout_url=https://example.com/logout\npost_logout_redirect_uri=https://mysite.com\n"
        },
        {
            "input": {
                "flow": "logout_request",
                "path": "/auth/openid_connect/logout",
                "options": {
                    "issuer": "example.com",
                    "client": {
                        "host": "example.com"
                    }
                }
            },
            "expected_output": "status=200\nroute=application\n"
        }
    ]
}
```

---

### Feature 4: Callback Validation Failures

**As a developer**, I want to validate callback inputs before accepting a login, so I can reject invalid or incomplete provider responses with stable failure output.

**Expected Behavior / Usage:**

The input selects the callback-request flow and supplies request parameters plus stored session values. Invalid state, provider-supplied errors, and missing response fields MUST produce a framework-observable failure redirect. The output MUST include `status=302`, the failure URL, and a language-neutral `error=` category; invalid state also includes `detail=invalid_state`. No host-language exception class names or runtime-generated messages may appear in stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature4_callback_validation.json`

```json
{
    "description": "Validates sign-in callback parameters and renders framework-observable failure redirects with normalized error categories for invalid or incomplete callbacks.",
    "cases": [
        {
            "input": {
                "flow": "callback_request",
                "request_params": {
                    "code": "abc",
                    "state": "wrong-state"
                },
                "session": {
                    "omniauth.state": "expected-state",
                    "omniauth.nonce": "expected-nonce"
                }
            },
            "expected_output": "status=302\nfailure_url=/auth/failure?message=invalid_credentials&strategy=openid_connect\nerror=invalid_callback\ndetail=invalid_state\n"
        },
        {
            "input": {
                "flow": "callback_request",
                "request_params": {
                    "state": "expected-state"
                },
                "session": {
                    "omniauth.state": "expected-state",
                    "omniauth.nonce": "expected-nonce"
                },
                "options": {
                    "response_type": "code"
                }
            },
            "expected_output": "status=302\nfailure_url=/auth/failure?message=missing_code&strategy=openid_connect\nerror=missing_authorization_code\n"
        },
        {
            "input": {
                "flow": "callback_request",
                "request_params": {
                    "state": "expected-state"
                },
                "session": {
                    "omniauth.state": "expected-state",
                    "omniauth.nonce": "expected-nonce"
                },
                "options": {
                    "response_type": "id_token"
                }
            },
            "expected_output": "status=302\nfailure_url=/auth/failure?message=missing_id_token&strategy=openid_connect\nerror=missing_identity_token\n"
        }
    ]
}
```

---

### Feature 5: Identity Token Callback Success

**As a developer**, I want to accept a valid identity-token callback, so I can pass an authenticated identity to the downstream application.

**Expected Behavior / Usage:**

The input selects the callback-request flow for an identity-token response, supplies matching state and session data, and provides decoded token claims. When validation succeeds, the output MUST include `status=200` plus the provider identifier and user-facing identity fields `uid`, `name`, and `email`, proving the callback reached the application layer with authenticated identity data.

**Test Cases:** `rcb_tests/public_test_cases/feature5_identity_token_callback.json`

```json
{
    "description": "Accepts an identity-token callback when state and nonce are valid, verifies the decoded token, and exposes the authenticated identity to the downstream application.",
    "cases": [
        {
            "input": {
                "flow": "callback_request",
                "request_params": {
                    "id_token": "compact-token",
                    "state": "expected-state"
                },
                "session": {
                    "omniauth.state": "expected-state",
                    "omniauth.nonce": "expected-nonce"
                },
                "options": {
                    "issuer": "example.com",
                    "response_type": "id_token"
                },
                "decoded_id_token": {
                    "sub": "sub",
                    "name": "name",
                    "email": "email"
                }
            },
            "expected_output": "status=200\nprovider=openid_connect\nuid=sub\nname=name\nemail=email\n"
        }
    ]
}
```

---

### Feature 6: Profile and Credential Mapping

**As a developer**, I want to map provider data into stable application-facing fields, so I can consume identity and token values without depending on provider-specific claim names.

**Expected Behavior / Usage:**

The input selects either profile-claims or credential-values flow. Profile-claims input contains provider claim data and the output MUST expose the selected subject, display-name fields, contact fields, website URL, image URL, and raw subject signal. Credential-values input contains issued token data and the output MUST expose identity token, access token, refresh token, expiry, and scope as direct stdout fields.

**Test Cases:** `rcb_tests/public_test_cases/feature6_profile_and_credentials.json`

```json
{
    "description": "Maps provider claims and issued token values into externally visible account profile and credential fields.",
    "cases": [
        {
            "input": {
                "flow": "profile_claims",
                "claims": {
                    "sub": "subject-123",
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "preferred_username": "jane",
                    "given_name": "Jane",
                    "family_name": "Doe",
                    "gender": "female",
                    "picture": "https://cdn.example.com/jane.png",
                    "phone_number": "+1-555-0100",
                    "website": "https://jane.example.com"
                }
            },
            "expected_output": "[lookup profile claim field mappings configuration]\n[lookup profile claim field mappings configuration]\n[lookup profile claim field mappings configuration]\n[lookup profile claim field mappings configuration]\n[lookup profile claim field mappings configuration]\n[lookup profile claim field mappings configuration]\ngender=female\nimage=https://cdn.example.com/jane.png\nphone=+1-555-0100\nwebsite=https://jane.example.com\nraw_sub=subject-123\n"
        },
        {
            "input": {
                "flow": "credential_values",
                "token": {
                    "id_token": "id-token-value",
                    "access_token": "access-token-value",
                    "refresh_token": "refresh-token-value",
                    "expires_in": 3600,
                    "scope": "openidconnect"
                }
            },
            "expected_output": "[check credential value template for current flow]\n[check credential value template for current flow]\nrefresh_token=refresh-token-value\nexpires_in=3600\nscope=openidconnect\n"
        }
    ]
}
```

---

### Feature 7: Verification Key Selection

**As a developer**, I want to select verification material from signing configuration, so I can verify identity tokens with the correct key source.

**Expected Behavior / Usage:**

The input selects the verification-key flow and supplies signing configuration. For asymmetric signing, JSON Web Key Set input MUST output `key_kind=jwk_set`, single JSON Web Key input MUST output `key_kind=jwk`, and certificate input MUST output `key_kind=x509_rsa_public_key`. For HMAC signing, client secret input MUST output `key_kind=shared_secret`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_verification_key_selection.json`

```json
{
    "description": "Selects the token verification material based on signing configuration, distinguishing JWK sets, single JWKs, X.509 public keys, and shared secrets.",
    "cases": [
        {
            "input": {
                "flow": "verification_key",
                "options": {
                    "signing": {
                        "algorithm": "RS256",
                        "jwk_json": "{\"keys\": [{\n    \"kty\": \"RSA\",\n    \"n\": \"0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw\",\n    \"e\": \"AQAB\",\n    \"alg\": \"RS256\",\n    \"kid\": \"1e9gdk7\"\n  }]\n}\n"
                    }
                }
            },
            "expected_output": "key_kind=jwk_set\n"
        },
        {
            "input": {
                "flow": "verification_key",
                "options": {
                    "signing": {
                        "algorithm": "RS256",
                        "certificate_pem": "-----BEGIN CERTIFICATE-----\nMIIDJDCCAgwCCQC57Ob2JfXb+DANBgkqhkiG9w0BAQUFADBUMQswCQYDVQQGEwJK\nUDEOMAwGA1UECBMFVG9reW8xITAfBgNVBAoTGEludGVybmV0IFdpZGdpdHMgUHR5\nIEx0ZDESMBAGA1UEAxMJbG9jYWxob3N0MB4XDTE0MDgwMTA4NTAxM1oXDTE1MDgw\nMTA4NTAxM1owVDELMAkGA1UEBhMCSlAxDjAMBgNVBAgTBVRva3lvMSEwHwYDVQQK\nExhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQxEjAQBgNVBAMTCWxvY2FsaG9zdDCC\nASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAN+7czSGHN2087T+oX2kBCY/\nXN6UOS/mdU2Gn//omZlyxsQXIqvgBLNWeCVt4QdlFUbgPLggfXUelECV/RUOCIIi\nF2Th4t3x1LviN2XkUiva0DZBnOycqEaJdkyreEuGL1CLVZgZjKmSzNqLl0Yci3D0\nzgVsXFZSadQebietm4CCmfJYREt9NJxXcrLxVDgat/Xm/KJBsohs3f+cbBT8EXer\n7+2oZjZoVUgw1hu0alaOvAfE4mxsVwjn3g2mjDqRJLbbuWqgDobjMHah+d4zwJvN\nePK8E0hfaz/XBLsJ4e6bQA3M3bANEgSvsicup/qb/0th4gUdc/kj4aJGj0RP7oEC\nAwEAATANBgkqhkiG9w0BAQUFAAOCAQEADuVec/8u2qJiq6K2W/gSLGYCBZq64OrA\ns7L2+S82m9/3gAb62wGcDNZjIGFDQubXmO6RhHv7JUT5YZqv9/kRGTJcHDUrwwoN\nIE99CIPizp7VfnrZ6GsYeszSsw3m+mKTETm+6ELmaSDbYAsrCg4IpGwUF0L88ATv\nCJ8QzW4X7b9dYVc7UAYyCie2N65GXfesBbRlSwFLuVqIzZfMdNpNijTIUwUqGSME\nb8IjLYzvekP53CO4wEBRrAVIPNXgftorxIE30OLWua2Qw3y6Pn+Qp5fLe47025S7\nLcec18/FbHG0Vbq0qO9cKQw80XyK31N6z556wr2GN2WyixkzVRddXA==\n-----END CERTIFICATE-----\n"
                    }
                }
            },
            "expected_output": "key_kind=x509_rsa_public_key\n"
        },
        {
            "input": {
                "flow": "verification_key",
                "options": {
                    "client": {
                        "secret": "secret"
                    },
                    "signing": {
                        "algorithm": "HS256"
                    }
                }
            },
            "expected_output": "key_kind=shared_secret\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_provider_endpoint_defaults.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_provider_endpoint_defaults@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- uses the routing logic defined in the application semantic layer
- follows the error classification schema in the callback failure handler module
