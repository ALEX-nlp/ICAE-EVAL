## Product Requirement Document

# OAuth2 / OpenID-Connect Authentication Strategy - Login Configuration, Token Validation & Profile Normalization

## Project Goal

Build an authentication-strategy library for the OAuth2 Authorization-Code flow with OpenID-Connect ID tokens, so developers can wire a hosted identity provider into a web application's login pipeline without hand-rolling endpoint derivation, login-request parameter assembly, ID-token validation, and user-profile normalization. The library is configured once with the provider host and client credentials and then exposes four cooperating capabilities: deriving protocol endpoints, building the per-login authorization query parameters, validating a returned ID token claim-by-claim, and turning a raw user record into a normalized profile object.

---

## Background & Problem

Without such a library, every application that integrates a hosted identity provider must repeat the same fragile boilerplate: stitch together the authorize / token / userinfo URLs from the provider host, decide which optional login hints to attach to each authorization request, and — most importantly — implement the full set of OpenID-Connect ID-token claim checks (issuer, subject, audience, authorized party, nonce, expiry, issued-at, authentication age). Getting any of those checks wrong silently weakens authentication. Profile shapes also differ between the provider's legacy and OpenID-Connect record formats, forcing callers to special-case identifier and provider extraction.

With this library, the host and credentials are supplied once; endpoints are derived automatically (and overridable), login parameters are assembled from a small declarative options object, ID tokens are validated against a precise contract that fails with a specific reason, and raw records are normalized into one consistent profile regardless of source format.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The domain has several distinct responsibilities (configuration/endpoint derivation, login-parameter assembly, ID-token decoding & validation, profile normalization). It MUST NOT be a single "god file"; lay out a clear multi-file tree separating these concerns. Do not over-engineer, but do not collapse independent concerns into one module.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, not the internal data model. The core validation and normalization logic must be completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core and rendering results as the line-oriented text shown here.

3. **Adherence to SOLID Design Principles:** Separate decoding, claim validation, parameter assembly, and profile mapping into distinct cohesive units; keep the core open for extension (e.g. new optional login parameters, new claim checks) but closed for modification; depend on abstractions rather than I/O details.

4. **Robustness & Interface Design:** The public interface must be idiomatic and elegant in the target language. Validation failures must be modeled as proper errors (specific error types or a Result-style value), not generic faults. The adapter translates every such failure into the neutral `error=<category>` contract below; the core may raise idiomatic errors but their language identity must never leak into stdout.

### Output contract (shared by all features)

The execution adapter reads ONE JSON request object from stdin (the `input` of a case) and writes raw stdout only. Output is a sequence of newline-terminated `key=value` lines (and, for some features, a bare `(none)` line). Optional/absent values are rendered as `(none)`. Validation failures are rendered as an `error=<category>` line optionally followed by neutral context lines (`expected=`, `actual=`, `[specific standard cryptographic algorithms]`). No status words (`PASS`/`FAIL`/`OK`) ever appear. Every request carries an `"op"` field selecting the capability.

---

## Core Features

### Feature 1: Strategy Configuration & Endpoint Derivation

**As a developer**, I want to configure the strategy once with a provider host and client credentials and have all protocol endpoints derived automatically (yet overridable), so I can avoid hand-assembling and mistyping URLs.

**Expected Behavior / Usage:**

The constructor requires four mandatory settings: a provider host, a client identifier, a client secret, and a callback path. From the host it derives five endpoints — an expected issuer (`https://<host>/`), an authorization URL (`.../authorize`), a token URL (`.../oauth/token`), a userinfo URL (`.../userinfo`), and an API base (`.../api`). An anti-forgery state flag defaults to enabled. Callers may override any derived endpoint and may set the state flag explicitly; explicit values always win over derived defaults. Constructing the strategy must not mutate the caller's own options object, and the strategy keeps its effective configuration on a separate internal object. For the `op=config` request the adapter prints the five effective endpoints and the effective state flag; for `op=immutability` it reports whether the strategy's config object is distinct from the caller's and whether the caller's object was left free of derived endpoint fields; for `op=custom_headers` it echoes each caller-supplied custom header value.

*1.1 Default endpoint derivation — minimal credentials derive all endpoints and enable state by default*

Given only the four mandatory settings, every endpoint is derived from the host and the state flag is enabled.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_default_endpoints.json`

```json
{
    "description": "Constructing a strategy with only the mandatory credentials (an identity-provider host, a client identifier, a client secret, and a callback path) derives the full set of protocol endpoint URLs from the host and enables the anti-forgery state parameter by default. The adapter reports each derived endpoint and the default state flag.",
    "cases": [
        {
            "input": {"op": "config", "config": {"domain": "login.example.com", "clientID": "sample-client", "clientSecret": "sample-secret", "callbackURL": "/callback"}},
            "expected_output": "expectedIssuer=https://login.example.com/\nauthorizationURL=https://login.example.com/authorize\ntokenURL=https://login.example.com/oauth/token\nuserInfoURL=https://login.example.com/userinfo\napiUrl=https://login.example.com/api\n[specific domain-based URL patterns]\n"
        }
    ]
}
```

*1.2 Explicit endpoint overrides — caller-provided endpoints are never clobbered by derived defaults*

When the caller passes explicit endpoint URLs, those exact values are kept.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_explicit_overrides.json`

```json
{
    "description": "When the caller supplies explicit endpoint URLs in addition to the host, the explicit values take precedence and are never clobbered by the host-derived defaults. The adapter reports the effective endpoints, which here are the caller-provided ones.",
    "cases": [
        {
            "input": {"op": "config", "config": {"domain": "login.example.com", "clientID": "sample-client", "clientSecret": "sample-secret", "callbackURL": "/callback", "expectedIssuer": "https://custom.example.org/", "authorizationURL": "https://custom.example.org/authorize", "tokenURL": "https://custom.example.org/oauth/token", "userInfoURL": "https://custom.example.org/userinfo", "apiUrl": "https://custom.example.org/api"}},
            "expected_output": "expectedIssuer=https://custom.example.org/\nauthorizationURL=https://custom.example.org/authorize\ntokenURL=https://custom.example.org/oauth/token\nuserInfoURL=https://custom.example.org/userinfo\napiUrl=https://custom.example.org/api\n[specific domain-based URL patterns]\n"
        }
    ]
}
```

*1.3 Explicit state flag — caller-supplied state value is preserved*

An explicitly supplied boolean state flag is preserved rather than reset to the default.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_state_flag.json`

```json
{
    "description": "The anti-forgery state flag is configurable. When the caller explicitly sets it, the supplied boolean value is preserved on the constructed strategy rather than being reset to the default.",
    "cases": [
        {"input": {"op": "config", "config": {"domain": "login.example.com", "clientID": "sample-client", "clientSecret": "sample-secret", "callbackURL": "/callback", "state": false}}, "expected_output": "expectedIssuer=https://login.example.com/\nauthorizationURL=https://login.example.com/authorize\ntokenURL=https://login.example.com/oauth/token\nuserInfoURL=https://login.example.com/userinfo\napiUrl=https://login.example.com/api\nstate=false\n"},
        {"input": {"op": "config", "config": {"domain": "login.example.com", "clientID": "sample-client", "clientSecret": "sample-secret", "callbackURL": "/callback", "state": true}}, "expected_output": "expectedIssuer=https://login.example.com/\nauthorizationURL=https://login.example.com/authorize\ntokenURL=https://login.example.com/oauth/token\nuserInfoURL=https://login.example.com/userinfo\napiUrl=https://login.example.com/api\n[specific domain-based URL patterns]\n"}
    ]
}
```

*1.4 Option immutability — the caller's options object is left untouched*

Construction copies configuration onto a separate object and does not add derived fields to the caller's object.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_option_immutability.json`

```json
{
    "description": "Constructing a strategy must not mutate the caller's original options object. The strategy stores its effective configuration on a separate internal object, and the caller's object never gains the host-derived endpoint fields.",
    "cases": [
        {"input": {"op": "immutability", "config": {"domain": "login.example.com", "clientID": "sample-client", "clientSecret": "sample-secret", "callbackURL": "/callback"}}, "expected_output": "strategy_options_is_separate=true\ncaller_has_derived_url=false\n"}
    ]
}
```

*1.5 Custom request headers — caller-supplied headers are preserved*

Custom headers passed by the caller survive onto the configured strategy.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_custom_headers.json`

```json
{
    "description": "Caller-supplied custom request headers are preserved on the constructed strategy. The adapter reports the value of each caller-provided header key.",
    "cases": [
        {"input": {"op": "custom_headers", "customHeaders": {"testCustomHeader": "Test Custom Header"}}, "expected_output": "header.testCustomHeader=Test Custom Header\n"}
    ]
}
```

---

### Feature 2: Login-Request Authorization Parameter Assembly

**As a developer**, I want to declare optional login hints in a small options object and have only the valid ones forwarded as authorization-request parameters, so I can steer the provider's login experience without manually filtering inputs.

**Expected Behavior / Usage:**

For an `op=auth_params` request the adapter asks the strategy to build the extra authorization-request parameters from a per-request options object. Each recognized hint is forwarded only when its value has the correct type, and the output lists the forwarded parameters as `key=value` lines in a fixed order (`connection`, `connection_scope`, `audience`, `prompt`, `login_hint`, `acr_values`, `max_age`, `nonce`); when nothing is forwarded a single `(none)` line is printed. Two parameters are special: `max_age` is forwarded only when a numeric maximum age is configured on the strategy itself (a per-request value is ignored), and `nonce` is forwarded only when a nonce was recorded on the strategy during an earlier login step (a per-request nonce is ignored). An absent options argument is treated identically to an empty object.

*2.1 Connection & connection scope — textual selectors, scope gated on connection*

A textual connection is forwarded; a textual connection scope is forwarded only alongside a connection; non-textual values are dropped.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_connection.json`

```json
{
    "description": "The login-request parameter builder maps a textual connection selector into the outgoing authorization parameters. A dependent connection-scope selector is only forwarded when a connection selector is also present. Non-textual values for either selector are ignored. The adapter prints each forwarded parameter as key=value in a fixed order, or a placeholder line when nothing is forwarded.",
    "cases": [
        {"input": {"op": "auth_params", "options": {"connection": "enterprise-ad"}}, "expected_output": "connection=enterprise-ad\n"},
        {"input": {"op": "auth_params", "options": {"connection": "enterprise-ad", "connection_scope": "read:files"}}, "expected_output": "connection=enterprise-ad\nconnection_scope=read:files\n"}
    ]
}
```

*2.2 Audience — textual API audience only*

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_audience.json`

```json
{
    "description": "The login-request parameter builder forwards a textual API audience identifier into the outgoing authorization parameters, and ignores a non-textual audience value.",
    "cases": [
        {"input": {"op": "auth_params", "options": {"audience": "https://api.example.com"}}, "expected_output": "audience=https://api.example.com\n"},
        {"input": {"op": "auth_params", "options": {"audience": 42}}, "expected_output": "(none)\n"}
    ]
}
```

*2.3 Prompt — textual prompt directive only*

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_prompt.json`

```json
{
    "description": "The login-request parameter builder forwards a textual prompt directive into the outgoing authorization parameters, and ignores a non-textual prompt value.",
    "cases": [
        {"input": {"op": "auth_params", "options": {"prompt": "login"}}, "expected_output": "prompt=login\n"},
        {"input": {"op": "auth_params", "options": {"prompt": 42}}, "expected_output": "(none)\n"}
    ]
}
```

*2.4 Login hint — textual login hint only*

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_login_hint.json`

```json
{
    "description": "The login-request parameter builder forwards a textual login-hint into the outgoing authorization parameters, and ignores a non-textual login-hint value.",
    "cases": [
        {"input": {"op": "auth_params", "options": {"login_hint": "test.user@example.com"}}, "expected_output": "login_hint=test.user@example.com\n"},
        {"input": {"op": "auth_params", "options": {"login_hint": 42}}, "expected_output": "(none)\n"}
    ]
}
```

*2.5 Authentication context class reference — textual selector only*

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_acr_values.json`

```json
{
    "description": "The login-request parameter builder forwards a textual authentication-context-class-reference selector into the outgoing authorization parameters, ignores a non-textual value, and forwards nothing when the selector is absent.",
    "cases": [
        {"input": {"op": "auth_params", "options": {"acr_values": "dummy:1"}}, "expected_output": "acr_values=dummy:1\n"},
        {"input": {"op": "auth_params", "options": {"acr_values": 1}}, "expected_output": "(none)\n"}
    ]
}
```

*2.6 Maximum authentication age — gated on a numeric strategy-level setting*

`max_age` is forwarded only when configured numerically on the strategy; a per-request value is ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_max_age.json`

```json
{
    "description": "The login-request parameter builder forwards a maximum-authentication-age parameter only when a numeric maximum age is configured on the strategy itself; the value supplied per-request is irrelevant. A non-numeric configured value, or an unconfigured value, forwards nothing for this parameter.",
    "cases": [
        {"input": {"op": "auth_params", "strategyMaxAge": 3600, "options": {}}, "expected_output": "max_age=3600\n"},
        {"input": {"op": "auth_params", "options": {"max_age": "60"}}, "expected_output": "(none)\n"}
    ]
}
```

*2.7 Nonce — gated on a nonce recorded during an earlier login step*

`nonce` is forwarded only when previously recorded on the strategy; a per-request nonce is ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature2_7_nonce.json`

```json
{
    "description": "The login-request parameter builder forwards a textual nonce into the outgoing authorization parameters only when a nonce was recorded on the strategy during an earlier login step. A per-request nonce value is never consulted, and nothing is forwarded when no nonce was recorded.",
    "cases": [
        {"input": {"op": "auth_params", "strategyAuthParams": {"nonce": "a1b2c3"}, "options": {}}, "expected_output": "nonce=a1b2c3\n"},
        {"input": {"op": "auth_params", "options": {"nonce": 1}}, "expected_output": "(none)\n"}
    ]
}
```

*2.8 Empty and absent options — nothing forwarded*

An empty options object and an absent options argument both forward nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature2_8_empty.json`

```json
{
    "description": "The login-request parameter builder forwards no parameters when given an empty options object, and treats an absent options argument identically to an empty one.",
    "cases": [
        {"input": {"op": "auth_params", "options": {}}, "expected_output": "(none)\n"},
        {"input": {"op": "auth_params"}, "expected_output": "(none)\n"}
    ]
}
```

---

### Feature 3: Callback Error Short-Circuit

**As a developer**, I want an authentication attempt to abort early and surface the provider's error code when the callback carries one, so a denied or failed login is reported faithfully instead of proceeding to a code exchange.

**Expected Behavior / Usage:**

For an `op=authenticate` request the adapter drives the strategy's authentication entry point with an inbound request whose query string contains a provider error code. The strategy must short-circuit and report a failure whose challenge equals that error code verbatim, without attempting any token exchange. The adapter prints the captured failure challenge.

**Test Cases:** `rcb_tests/public_test_cases/feature3_authenticate_error.json`

```json
{
    "description": "When an incoming callback request carries a provider error code in its query string, authentication is aborted and that error code is propagated unchanged as the failure challenge instead of attempting to exchange an authorization code. The adapter reports the captured failure challenge.",
    "cases": [
        {"input": {"op": "authenticate", "error": "domain_mismatch"}, "expected_output": "fail=domain_mismatch\n"}
    ]
}
```

---

### Feature 4: ID-Token Decoding

**As a developer**, I want to decode a compact ID token into its structured parts, so I can read its header and claims before or independently of full validation.

**Expected Behavior / Usage:**

A compact token is three dot-separated segments: a base64-encoded JSON header, a base64-encoded JSON payload, and a signature segment. For an `op=decode` request the adapter builds such a token from the supplied header and payload (or accepts a raw token string), decodes it, and reports the header algorithm, every decoded payload claim as `key=value` (claims emitted in sorted key order; array/object claim values rendered as compact JSON), the verbatim signature segment, and whether the original raw token string was retained unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_decode.json`

```json
{
    "description": "A compact token is the concatenation of three dot-separated segments: a base64-encoded JSON header, a base64-encoded JSON payload, and a signature segment. Decoding parses the header and payload back into structured claims, keeps the signature segment verbatim, and retains the original raw token string. The adapter reports the header algorithm, every decoded payload claim, the signature segment, and whether the raw token round-tripped.",
    "cases": [
        {"input": {"op": "decode", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|123", "aud": "sample-client", "exp": 9999999999, "iat": 1000000000}}, "expected_output": "[specific standard cryptographic algorithms]RS256\naud=sample-client\nexp=9999999999\niat=1000000000\niss=https://login.example.com/\nsub=user|123\nsignature=sig\nraw_matches=true\n"},
        {"input": {"op": "decode", "header": {"alg": "HS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|123", "name": "ÁÁutf8"}}, "expected_output": "[specific standard cryptographic algorithms]HS256\niss=https://login.example.com/\nname=ÁÁutf8\nsub=user|123\nsignature=sig\nraw_matches=true\n"}
    ]
}
```

---

### Feature 5: ID-Token Validation

**As a developer**, I want a returned ID token validated claim-by-claim against an expected set of options, so an invalid token is rejected with a specific, machine-readable reason rather than a vague failure.

**Expected Behavior / Usage:**

For an `op=verify` request the adapter builds a token from the supplied header and payload (or uses a supplied raw token, which may be null/absent) and runs validation against an options object (expected issuer, expected audience, optional expected nonce, optional maximum age). On success the adapter prints `verified`. On the first failed check it prints a neutral `error=<category>` line plus any relevant context fields. The checks, in order, are: a token must be present (`token_missing`); the signature algorithm must be one of the two approved algorithms, else `unsupported_algorithm` with the offending `alg`; the issuer claim must be a present string (`issuer_missing`) equal to the expected issuer, else `issuer_mismatch` with `expected`/`actual`; the subject must be a present string (`subject_missing`); the audience must be a present string or array of strings (`audience_invalid`) and must contain/equal the expected audience, else `audience_mismatch` with `expected`; the expiration must be a number (`exp_invalid`) and must not be in the past (`token_expired`); the issued-at must be a present number (`iat_invalid`); when an expected nonce is set, the nonce claim must be a present string (`nonce_missing`) equal to it, else `nonce_mismatch` with `expected`/`actual`; when the audience claim has multiple values, the authorized-party claim must be a present string (`azp_missing`) equal to the expected audience, else `azp_mismatch` with `expected`/`actual`; when a maximum age is set, the authentication-time claim must be a present number (`auth_time_invalid`) and the authentication must not be older than the maximum (`auth_time_expired`). All checks allow a small clock-skew leeway.

*5.1 Token presence — a missing token is rejected first*

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_token_presence.json`

```json
{
    "description": "Verification rejects a request that carries no token at all, reporting a neutral missing-token category before any claim inspection.",
    "cases": [
        {"input": {"op": "verify", "token": null, "options": {}}, "expected_output": "error=token_missing\n"}
    ]
}
```

*5.2 Issuer — present string equal to the expected issuer*

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_issuer.json`

```json
{
    "description": "Verification requires the issuer claim to be a present string and to equal the expected issuer. A missing issuer yields a neutral issuer-missing category; a present but non-matching issuer yields an issuer-mismatch category carrying the expected and actual issuer values as separate fields.",
    "cases": [
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"sub": "user|abc", "aud": "sample-client", "exp": 9999999999, "iat": 1000000000}, "options": {}}, "expected_output": "error=issuer_missing\n"},
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": "sample-client", "exp": 9999999999, "iat": 1000000000}, "options": {"iss": "https://other.example.com/"}}, "expected_output": "error=issuer_mismatch\nexpected=https://other.example.com/\nactual=https://login.example.com/\n"}
    ]
}
```

*5.3 Subject — present string required*

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_subject.json`

```json
{
    "description": "Verification requires the subject claim to be a present string. A missing subject yields a neutral subject-missing category.",
    "cases": [
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "aud": "sample-client", "exp": 9999999999, "iat": 1000000000}, "options": {"iss": "https://login.example.com/"}}, "expected_output": "error=subject_missing\n"}
    ]
}
```

*5.4 Signature algorithm — must be an approved algorithm*

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_algorithm.json`

```json
{
    "description": "Verification only accepts tokens signed with one of two approved signature algorithms. A token whose header declares any other algorithm is rejected with a neutral unsupported-algorithm category that carries the offending algorithm name as a separate field.",
    "cases": [
        {"input": {"op": "verify", "header": {"alg": "HS512"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": "sample-client"}, "options": {"iss": "https://login.example.com/"}}, "expected_output": "[specific standard cryptographic algorithms]\n[specific standard cryptographic algorithms]HS512\n"}
    ]
}
```

*5.5 Audience — present string/array containing the expected audience*

**Test Cases:** `rcb_tests/public_test_cases/feature5_5_audience.json`

```json
{
    "description": "Verification requires the audience claim to be a present string or array of strings, and the expected audience must be the audience (string form) or be contained in it (array form). A missing/invalid audience yields an audience-invalid category; an expected audience absent from the claim yields an audience-mismatch category carrying the expected audience as a separate field.",
    "cases": [
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "exp": 9999999999, "iat": 1000000000}, "options": {"iss": "https://login.example.com/"}}, "expected_output": "error=audience_invalid\n"},
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": ["sample-client", "other-client"], "exp": 9999999999, "iat": 1000000000, "azp": "sample-client"}, "options": {"iss": "https://login.example.com/", "aud": "expectedAudience"}}, "expected_output": "error=audience_mismatch\nexpected=expectedAudience\n"}
    ]
}
```

*5.6 Authorized party — required and matching when audience has multiple values*

**Test Cases:** `rcb_tests/public_test_cases/feature5_6_authorized_party.json`

```json
{
    "description": "When the audience claim contains multiple values, verification requires an authorized-party claim that is a present string equal to the expected audience. A missing authorized party yields an azp-missing category; a non-matching authorized party yields an azp-mismatch category carrying the expected and actual values as separate fields.",
    "cases": [
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": ["sample-client", "other-client"], "exp": 9999999999, "iat": 1000000000}, "options": {"iss": "https://login.example.com/", "aud": "sample-client"}}, "expected_output": "error=azp_missing\n"},
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": ["sample-client", "other-client"], "exp": 9999999999, "iat": 1000000000, "azp": "sample-client"}, "options": {"iss": "https://login.example.com/", "aud": "other-client"}}, "expected_output": "error=azp_mismatch\nexpected=other-client\nactual=sample-client\n"}
    ]
}
```

*5.7 Nonce — required and matching when an expected nonce is set*

**Test Cases:** `rcb_tests/public_test_cases/feature5_7_nonce.json`

```json
{
    "description": "When an expected nonce is supplied, verification requires the nonce claim to be a present string equal to it. A missing nonce yields a nonce-missing category; a non-matching nonce yields a nonce-mismatch category carrying the expected and actual nonce values as separate fields.",
    "cases": [
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": "sample-client", "exp": 9999999999, "iat": 1000000000}, "options": {"iss": "https://login.example.com/", "aud": "sample-client", "nonce": "a1b2c3"}}, "expected_output": "error=nonce_missing\n"},
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": "sample-client", "exp": 9999999999, "iat": 1000000000, "nonce": "notExpected"}, "options": {"iss": "https://login.example.com/", "aud": "sample-client", "nonce": "noncey"}}, "expected_output": "error=nonce_mismatch\nexpected=noncey\nactual=notExpected\n"}
    ]
}
```

*5.8 Expiration & issued-at — numeric, unexpired, present*

**Test Cases:** `rcb_tests/public_test_cases/feature5_8_expiration.json`

```json
{
    "description": "Verification requires the expiration claim to be a number and the token must not have expired (with a small clock-skew allowance), and requires the issued-at claim to be a present number. A non-numeric expiration yields an exp-invalid category; an expiration already in the past yields a token-expired category; a missing issued-at yields an iat-invalid category.",
    "cases": [
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": "sample-client", "exp": "not a number", "iat": 1000000000}, "options": {"iss": "https://login.example.com/", "aud": "sample-client"}}, "expected_output": "error=exp_invalid\n"},
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": "sample-client", "exp": 1000000000, "iat": 900000000}, "options": {"iss": "https://login.example.com/", "aud": "sample-client"}}, "expected_output": "error=token_expired\n"}
    ]
}
```

*5.9 Maximum authentication age — present numeric auth-time within the allowed window*

**Test Cases:** `rcb_tests/public_test_cases/feature5_9_max_age.json`

```json
{
    "description": "When a maximum authentication age is configured, verification requires an authentication-time claim that is a present number and that the elapsed time since authentication does not exceed the maximum (with a small clock-skew allowance). A missing authentication time yields an auth-time-invalid category; an authentication that is too old yields an auth-time-expired category.",
    "cases": [
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": "sample-client", "exp": 9999999999, "iat": 1000000000}, "options": {"iss": "https://login.example.com/", "aud": "sample-client", "maxAge": 123}}, "expected_output": "error=auth_time_invalid\n"},
        {"input": {"op": "verify", "header": {"alg": "RS256"}, "payload": {"iss": "https://login.example.com/", "sub": "user|abc", "aud": "sample-client", "exp": 9999999999, "iat": 1000000000, "auth_time": 1000000000}, "options": {"iss": "https://login.example.com/", "aud": "sample-client", "maxAge": 123}}, "expected_output": "error=auth_time_expired\n"}
    ]
}
```

---

### Feature 6: User-Profile Normalization

**As a developer**, I want a raw user record turned into a consistent normalized profile regardless of which record format the provider used, so downstream code reads one stable shape.

**Expected Behavior / Usage:**

For an `op=profile` request the adapter normalizes a raw user record. The identifier comes from the record's user-id field, or from its subject field when user-id is absent; the same value is exposed both as `id` and `user_id`. The display name comes from the record's name. The provider is taken from the first entry of an identities list when present; otherwise, when the identifier contains a provider-qualified prefix delimited by a vertical bar, it is derived from that prefix; otherwise there is no provider at all. Given/family names are mapped into a structured name. An email is normalized into a collection of value entries; a record without an email exposes no email collection. The adapter reports `id`, `user_id`, `displayName`, `provider`, `givenName`, `familyName`, and `emails`, rendering any absent field as `(none)`.

*6.1 Record with identities list — provider from first identity entry*

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_with_identities.json`

```json
{
    "description": "A raw user record that includes an identities list is normalized into a standard profile: the display name comes from the record's name, the identifier comes from the record's user id, the provider is taken from the first identity entry, the given/family names are mapped into a structured name, and a single email is wrapped into a list of value objects. The adapter reports each normalized field.",
    "cases": [
        {"input": {"op": "profile", "data": {"email": "user@example.com", "family_name": "Doe", "gender": "n/a", "given_name": "Jane", "identities": [{"provider": "samlp", "user_id": "u-1", "connection": "samlp", "isSocial": true}], "locale": "en", "name": "Jane Doe", "nickname": "jane", "picture": "https://img.example.com/p.png", "user_id": "samlp|u-1"}}, "expected_output": "id=samlp|u-1\nuser_id=samlp|u-1\ndisplayName=Jane Doe\nprovider=samlp\ngivenName=Jane\nfamilyName=Doe\nemails=user@example.com\n"}
    ]
}
```

*6.2 Record without identities — provider from the identifier prefix*

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_provider_from_id.json`

```json
{
    "description": "When a raw user record has no identities list but its identifier contains a provider-qualified prefix delimited by a vertical bar, the provider is derived from that prefix. All other standard fields are normalized as usual.",
    "cases": [
        {"input": {"op": "profile", "data": {"email": "user@example.com", "family_name": "Doe", "gender": "n/a", "given_name": "Jane", "locale": "en", "name": "Jane Doe", "nickname": "jane", "picture": "https://img.example.com/p.png", "user_id": "samlp|u-1"}}, "expected_output": "id=samlp|u-1\nuser_id=samlp|u-1\ndisplayName=Jane Doe\nprovider=samlp\ngivenName=Jane\nfamilyName=Doe\nemails=user@example.com\n"}
    ]
}
```

*6.3 OpenID-Connect record — identifier from the subject field*

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_oidc_sub.json`

```json
{
    "description": "An OpenID-Connect style raw record carries its identifier under a subject field rather than a user-id field. Normalization uses the subject as the identifier while still deriving the provider from the first identity entry and mapping all other standard fields.",
    "cases": [
        {"input": {"op": "profile", "data": {"email": "user@example.com", "family_name": "Doe", "gender": "n/a", "given_name": "Jane", "identities": [{"provider": "samlp", "user_id": "u-1", "connection": "samlp", "isSocial": true}], "locale": "en", "name": "Jane Doe", "nickname": "jane", "picture": "https://img.example.com/p.png", "sub": "samlp|u-1"}}, "expected_output": "id=samlp|u-1\nuser_id=samlp|u-1\ndisplayName=Jane Doe\nprovider=samlp\ngivenName=Jane\nfamilyName=Doe\nemails=user@example.com\n"}
    ]
}
```

*6.4 Record without any identifier — no provider*

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_no_id.json`

```json
{
    "description": "A raw record with neither an identities list nor any identifier produces a profile that exposes no provider field at all.",
    "cases": [
        {"input": {"op": "profile", "data": {"email": "user@example.com"}}, "expected_output": "id=(none)\nuser_id=(none)\ndisplayName=(none)\nprovider=(none)\ngivenName=(none)\nfamilyName=(none)\nemails=user@example.com\n"}
    ]
}
```

*6.5 Identifier without a provider prefix — id kept, no provider*

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_id_without_provider.json`

```json
{
    "description": "A raw record whose identifier contains no provider-qualifying delimiter yields a profile that exposes the identifier verbatim but exposes no provider field.",
    "cases": [
        {"input": {"op": "profile", "data": {"sub": "plain-subject-id"}}, "expected_output": "id=plain-subject-id\nuser_id=plain-subject-id\ndisplayName=(none)\nprovider=(none)\ngivenName=(none)\nfamilyName=(none)\nemails=(none)\n"}
    ]
}
```

*6.6 Record without an email — no email collection*

**Test Cases:** `rcb_tests/public_test_cases/feature6_6_no_email.json`

```json
{
    "description": "A raw record that carries no email produces a profile that exposes no email collection.",
    "cases": [
        {"input": {"op": "profile", "data": {"sub": "plain-subject-id"}}, "expected_output": "id=plain-subject-id\nuser_id=plain-subject-id\ndisplayName=(none)\nprovider=(none)\ngivenName=(none)\nfamilyName=(none)\nemails=(none)\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing strategy configuration & endpoint derivation, login-request parameter assembly, the callback error short-circuit, ID-token decoding, ID-token validation, and user-profile normalization, with these concerns kept in separate cohesive modules.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core. It reads ONE JSON command from stdin (the `input` of a case), invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature `key=value` / `error=<category>` contracts above. The adapter is the only component aware of stdin/stdout and JSON, and it is the only place that translates native validation errors into the neutral `error=<category>` lines. It must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing only the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- order the output parameters following the convention established by the connection_scope module
- validate the output claim sequence matching the structure used in the initialization module
