## Product Requirement Document

# Delegated Authorization Endpoint - Grant-Code Issuance Contract

## Project Goal

Build the server-side authorization endpoint of a delegated-authorization protocol (the "authorization request" leg of the standard authorization-code flow) that lets a third-party client obtain a short-lived grant code on a resource owner's behalf without ever handling the resource owner's credentials. The endpoint validates an incoming authorization request, decides whether it must answer with a direct error or by redirecting the user agent back to the client, and — on success and approval — issues a one-time grant code that the client can later redeem for tokens.

---

## Background & Problem

Without such an endpoint, every application that wants to act on a user's behalf would have to collect that user's password directly, store it, and replay it — a fragile and dangerous pattern. The delegated-authorization flow replaces that with a redirect-based handshake: the client sends the user agent to this endpoint with a set of request parameters; the endpoint authenticates the request against a registry of pre-registered clients, lets the resource owner approve or deny, and hands back a single-use grant code through a redirect. The subtlety is in *where* failures surface: some failures (the client cannot be identified, or no safe redirect target exists) must be reported as a direct error page because redirecting would be unsafe, while other failures (a bad [two output keys for rendering typed responses] type, a missing anti-forgery value, a denied request) must be reported by redirecting back to the already-validated target with the error encoded in the URL, so the client can react. Getting this split right, plus faithful reconstruction of the redirect target and correct issuance/binding of the grant code, is the whole contract.

With this endpoint, a client integration becomes: redirect to the endpoint, receive a code (or a structured error), and redeem the code. The reader of this document must be able to reproduce the exact observable behavior — HTTP status, redirect target, query parameters, and error codes — from the contract below alone.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (request parsing, client/redirect-URI resolution, [two output keys for rendering typed responses]-type and scope policy, the approve/deny decision, grant-code issuance and identity binding, and two distinct [two output keys for rendering typed responses] renderings — direct error vs. redirect). It MUST NOT be a single "god file"; output a clear multi-file tree (e.g. `src/`, plus the execution adapter and `rcb_tests/`) reflecting a production-grade repository. Do not over-engineer, but do separate these concerns.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract** for an execution adapter, NOT the internal data model. The core authorization logic must be decoupled from stdin/stdout and JSON parsing. A thin execution adapter reads one JSON request from stdin, drives the core endpoint, and renders the normalized stdout described under "Execution Contract". The adapter is the only place that translates between JSON/stdout and core method calls, and the only place that maps native runtime exceptions to neutral error lines.

3. **Adherence to SOLID Design Principles:** Separate parsing, client/redirect resolution, validation, grant-code issuance, and output formatting into distinct cohesive units; keep the core open for extension (new [two output keys for rendering typed responses] types, new scope policies) but closed for modification; depend on storage abstractions, not concrete I/O.

4. **Robustness & Interface Design:** The public interface of the core endpoint must be idiomatic for the target language and hide internal complexity. Edge cases (unknown client, fragment in redirect, multiple registered targets, denied request) must be modeled explicitly, not as generic faults.

---

## Execution Contract

This section defines the exact stdin → stdout contract that every case below obeys. The execution adapter reads **one** JSON object from stdin and writes the rendered result to stdout.

**Input object:**

- `config` *(optional object)* — endpoint configuration toggles. Recognized keys: `enforce_state` (bool — require an anti-forgery `state` value on grant-code requests), `require_exact_redirect_uri` (bool — require a supplied redirect target to match a registered one exactly, vs. prefix-match), `allow_implicit` (bool), `use_openid_connect` (bool — enable identity-connect features), `issuer` (string — identity-token issuer label). **Defaults when omitted:** state IS enforced, exact redirect-URI matching IS required, implicit is NOT allowed, identity-connect is OFF.
- `scope_util` *(optional object)* — a scope policy backed by storage: `supported_scopes` (array of accepted scope strings) and `default_scope` (a default scope string, or `false` for "no default — a scope must be supplied").
- `steps` *(array)* — an ordered list of requests against the endpoint. Each step:
  - `action` — `"authorize"` (default) for an authorization request, or `"token"` for a grant-code redemption at the token endpoint.
  - `is_authorized` *(bool, authorize only, default true)* — the resource owner's decision: `true` = approve, `false` = decline (or not-yet-approved).
  - `request` *(object)* — the request parameters (e.g. `client_id`, `redirect_uri`, `[two output keys for rendering typed responses]_type`, `state`, `scope`; for token redemption: `grant_type`, `code`, `client_secret`).
  - **Chaining:** any `request` value equal to the literal `"@AUTH_[four specific placeholder strings for sensitive data]@"` is replaced, at run time, by the real grant code issued in a preceding `authorize` step — letting a `token` step redeem the code that an earlier step produced.

**Output (stdout):** one block per step, blocks separated by one blank line, the stream ending with a trailing newline. Each block begins with `[two output keys for rendering typed responses]=<step_index>` then `status=<http_status>`, followed by exactly one of:

- **Redirect rendering** (emitted when the [two output keys for rendering typed responses] carries a redirect/`Location`): the line `type=redirect`; then the components of the redirect target, each present even when empty — `redirect.scheme=`, `redirect.user=`, `redirect.host=`, `redirect.port=`, `redirect.path=`, `redirect.fragment=`; then every query parameter of the redirect, **sorted by key**, as `query.<key>=<value>` (a multi-valued parameter is comma-joined); and, whenever a grant code is present in the redirect, the line `issued.identity_token=present` or `issued.identity_token=absent` reporting whether an identity assertion was bound to that code.
- **Body rendering** (emitted for a direct, non-redirect [two output keys for rendering typed responses]): the line `type=[two output keys for rendering typed responses]`; then every [two output keys for rendering typed responses] parameter, **sorted by key**, as `[two output keys for rendering typed responses].<key>=<value>` (null → empty string, boolean → `true`/`false`, array → comma-joined).

**Normalization (mandatory):** server-issued secrets are replaced by stable placeholders so output is deterministic and leaks no per-run value — a grant code renders as `[four specific placeholder strings for sensitive data]`, an access token as `[four specific placeholder strings for sensitive data]`, a refresh token as `[four specific placeholder strings for sensitive data]`, an identity token as `[four specific placeholder strings for sensitive data]`. The caller's `state` value and all protocol error codes / descriptions / reference URIs are domain wire-format and are preserved verbatim.

**Error normalization:** protocol-level rejections (e.g. `invalid_client`, `invalid_uri`, `invalid_request`, `redirect_uri_mismatch`, `invalid_scope`, `access_denied`) are part of the domain contract and appear as `[two output keys for rendering typed responses].error=…` / `query.error=…` fields, never as exceptions. If the core instead throws a native runtime exception, the adapter renders a single neutral category line in place of the block [two output keys for rendering typed responses]: `error=invalid_argument`, `error=invalid_configuration`, or `error=internal`. No host-language exception class name or runtime artifact ever appears in stdout.

---

## Fixture Preconditions — Registered Client Catalog

The endpoint resolves clients against a fixed pre-registered catalog. The cases below reference these registrations (client identifier → secret, registered redirect target(s)):

- **"Test Client ID"** — secret `TestSecret`; **no** registered redirect target (so a request must supply one).
- **"Test Client ID with Redirect Uri"** — secret `TestSecret2`; one registered target `http://brentertainment.com`.
- **"Test Client ID with Multiple Redirect Uris"** — secret `TestSecret3`; two registered targets `http://brentertainment.com` and `http://morehazards.com`.
- **"Test Client ID with Redirect Uri Parts"** — secret `TestSecret4`; one registered target `http://user:pass@brentertainment.com:2222/authorize/cb?auth_type=oauth&test=true`.

Any client identifier not in the catalog is treated as unregistered.

---

## Core Features

### Feature 1: Client Identification Precedes Everything

**As a developer**, I want the endpoint to identify and validate the requesting client before any other processing, so that a request from an unknown or unnamed client is rejected directly and never triggers a redirect.

**Expected Behavior / Usage:**

Before validating the redirect target or anything else, the endpoint must establish which registered client is making the request. If the request carries no client identifier, or carries one that is not in the catalog, the endpoint cannot trust any redirect target and therefore answers with a **direct** (non-redirect) error: a `4xx` client-error status and a stable error code. The two situations are distinguished only by the human-readable description ("no client supplied" vs. "supplied client is invalid"). The decision is independent of the resource owner's approval.

**Test Cases:** `rcb_tests/public_test_cases/feature1_client_identification.json`

```json
{
    "description": "An authorization request is rejected before any redirect can occur when the client cannot be identified. Submitting a request with no client identifier, or with an identifier that is not registered, yields a direct (non-redirect) error [two output keys for rendering typed responses] carrying an HTTP client-error status and a stable error code distinguishing the two situations by description.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": false, "request": {}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=400\ntype=[two output keys for rendering typed responses]\n[two output keys for rendering typed responses].error=invalid_client\n[two output keys for rendering typed responses].error_description=No client id supplied\n"
        },
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": false, "request": {"client_id": "Fake Client ID"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=400\ntype=[two output keys for rendering typed responses]\n[two output keys for rendering typed responses].error=invalid_client\n[two output keys for rendering typed responses].error_description=The client id supplied is invalid\n"
        }
    ]
}
```

---

### Feature 2: Redirect-Target Resolution & Validation

**As a developer**, I want the endpoint to determine a single safe redirect target — combining the request's supplied target with the client's registered target(s) under a configurable matching policy — so that the grant code can only ever be delivered to a pre-approved destination, and any failure to do so safely is reported directly.

**Expected Behavior / Usage:**

*2.1 No redirect target available — direct error*

When the named (registered) client has no stored redirect target and the request supplies none, the endpoint has nowhere safe to redirect and answers with a direct client-error [two output keys for rendering typed responses] carrying an invalid-URI error code.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_no_redirect_uri.json`

```json
{
    "description": "When a request names a registered client that has no stored redirect target and supplies none in the request, the endpoint cannot safely redirect and returns a direct error [two output keys for rendering typed responses] with a client-error status and an invalid-URI error code.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": false, "request": {"client_id": "Test Client ID"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=400\ntype=[two output keys for rendering typed responses]\n[two output keys for rendering typed responses].error=invalid_uri\n[two output keys for rendering typed responses].error_description=No redirect URI was supplied or stored\n"
        }
    ]
}
```

*2.2 Supplied target containing a fragment — direct error*

A supplied redirect target that contains a URL fragment component is rejected directly, because authorization parameters must be appended as query parameters and can never be attached to a fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_fragment_rejected.json`

```json
{
    "description": "A supplied redirect target that contains a URL fragment component is rejected with a direct error [two output keys for rendering typed responses] (client-error status, invalid-URI error code), because authorization parameters may not be appended to a fragment.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com#fragment", "[two output keys for rendering typed responses]_type": "code"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=400\ntype=[two output keys for rendering typed responses]\n[two output keys for rendering typed responses].error=invalid_uri\n[two output keys for rendering typed responses].error_description=The redirect URI must not contain a fragment\n"
        }
    ]
}
```

*2.3 Supplied target does not match the single registered target — direct mismatch*

When a client has exactly one registered redirect target and the request supplies a different one, the request is rejected directly with a mismatch error code and a reference link to the relevant specification section.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_mismatch.json`

```json
{
    "description": "When a client has exactly one registered redirect target and the request supplies a different one, the request is rejected with a direct error [two output keys for rendering typed responses] carrying a client-error status, a mismatch error code, and a reference link to the relevant specification section.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID with Redirect Uri", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "code"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=400\ntype=[two output keys for rendering typed responses]\n[two output keys for rendering typed responses].error=redirect_uri_mismatch\n[two output keys for rendering typed responses].error_description=The redirect URI provided is missing or does not match\n[two output keys for rendering typed responses].error_uri=http://tools.ietf.org/html/rfc6749#section-3.1.2\n"
        }
    ]
}
```

*2.4 Multiple registered targets but none chosen — direct error*

When a client registers more than one redirect target and the request omits the redirect parameter, the endpoint cannot pick one automatically and returns a direct error (invalid-URI code, spec reference) requiring the caller to specify which registered target to use.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_multiple_requires_selection.json`

```json
{
    "description": "When a client registers more than one redirect target and the request omits the redirect parameter, the endpoint cannot choose one automatically and returns a direct error [two output keys for rendering typed responses] (client-error status, invalid-URI error code, spec reference) requiring the caller to specify which registered target to use.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID with Multiple Redirect Uris", "[two output keys for rendering typed responses]_type": "code"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=400\ntype=[two output keys for rendering typed responses]\n[two output keys for rendering typed responses].error=invalid_uri\n[two output keys for rendering typed responses].error_description=A redirect URI must be supplied when multiple redirect URIs are registered\n[two output keys for rendering typed responses].error_uri=http://tools.ietf.org/html/rfc6749#section-3.1.2.3\n"
        }
    ]
}
```

*2.5 Exact-match policy rejects a query-string difference — direct mismatch*

Under a strict exact-match policy, a supplied target whose query string differs from the registered one (even when scheme/host/path match) is rejected directly as a mismatch with a spec reference.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_exact_match_required.json`

```json
{
    "description": "Under a strict exact-match policy, a supplied redirect target whose query string differs from the registered one (even if the scheme/host/path match) is rejected with a direct mismatch error [two output keys for rendering typed responses] and a spec reference.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID with Redirect Uri Parts", "[two output keys for rendering typed responses]_type": "code", "redirect_uri": "http://user:pass@brentertainment.com:2222/authorize/cb?auth_type=oauth&test=true&hereisa=querystring"}}], "config": {"require_exact_redirect_uri": true}}],
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=400\ntype=[two output keys for rendering typed responses]\n[two output keys for rendering typed responses].error=redirect_uri_mismatch\n[two output keys for rendering typed responses].error_description=The redirect URI provided is missing or does not match\n[two output keys for rendering typed responses].error_uri=http://tools.ietf.org/html/rfc6749#section-3.1.2\n"
        }
    ]
}
```

---

### Feature 3: Response-Type Validation (Reported via Redirect)

**As a developer**, I want a missing or unrecognized [two output keys for rendering typed responses]-type selector to be reported by redirecting back to the validated target with the error in the query string, so the client receives it programmatically rather than as a dead-end error page.

**Expected Behavior / Usage:**

Once the client and redirect target are valid, the endpoint inspects the [two output keys for rendering typed responses]-type selector. If it is omitted or names an unsupported type, the failure is **not** a direct error — instead the user agent is redirected (`302`) back to the now-validated target, with `error` and `error_description` encoded in the query string. Both the "omitted" and the "unrecognized value" cases produce the same error contract.

**Test Cases:** `rcb_tests/public_test_cases/feature3_[two output keys for rendering typed responses]_type.json`

```json
{
    "description": "Once the client and redirect target are valid, a request that omits the [two output keys for rendering typed responses]-type selector, or supplies an unrecognized one, is reported by REDIRECTING the user agent back to the validated redirect target with an error code and description encoded in the query string, rather than as a direct error [two output keys for rendering typed responses].",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": false, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.error=invalid_request\nquery.error_description=Invalid or missing [two output keys for rendering typed responses] type\n"
        },
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": false, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "invalid"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.error=invalid_request\nquery.error_description=Invalid or missing [two output keys for rendering typed responses] type\n"
        }
    ]
}
```

---

### Feature 4: Anti-Forgery State Enforcement

**As a developer**, I want the endpoint to optionally require an anti-forgery `state` value on grant-code requests, so I can enable CSRF protection by configuration and fall back to lenient behavior when disabled.

**Expected Behavior / Usage:**

*4.1 State required and missing — redirect error*

When configured to require state, a grant-code request that omits `state` is reported by redirecting back to the validated target with an `invalid_request` error and a description stating the state parameter is required.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_enforce_state.json`

```json
{
    "description": "When the endpoint is configured to require an anti-forgery state value, a request for a grant code that omits it is reported by redirecting back to the validated target with an error code and description in the query string.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "code"}}], "config": {"enforce_state": true}}],
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.error=invalid_request\nquery.error_description=The state parameter is required\n"
        }
    ]
}
```

*4.2 State not required — success without state*

When state is not required, the same request that omits `state` succeeds: a `302` redirect back to the target carries a freshly issued grant code (no error), and no identity assertion is bound to the code.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_no_enforce_state.json`

```json
{
    "description": "When state is NOT required, the same request that omits the state value succeeds: the user agent is redirected back to the target with a freshly issued grant code and no error, and no identity assertion is bound to the code.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "code"}}], "config": {"enforce_state": false}}],
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.code=[four specific placeholder strings for sensitive data]\nissued.identity_token=absent\n"
        }
    ]
}
```

---

### Feature 5: Scope Enforcement Under a Supported-Scope Policy

**As a developer**, I want the endpoint to enforce a configured scope policy, so that when the deployment defines a set of supported scopes with no default, a request must name a supported scope and is otherwise reported via redirect.

**Expected Behavior / Usage:**

Given a policy that lists supported scopes and declares no default scope, a grant-code request that omits the scope is redirected back with an `invalid_scope` error (and the echoed state); the same request that names a supported scope succeeds with a redirect carrying a freshly issued grant code (and the echoed state).

**Test Cases:** `rcb_tests/public_test_cases/feature5_scope_enforcement.json`

```json
{
    "description": "When the deployment defines a set of supported scopes and no default scope, a grant-code request that omits the scope parameter is redirected back with a scope error, while the same request that names a supported scope succeeds with a redirect carrying a freshly issued grant code.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "code", "state": "xyz"}}], "scope_util": {"default_scope": false, "supported_scopes": ["testscope"]}}],
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.error=invalid_scope\nquery.error_description=This application requires you specify a scope parameter\nquery.state=xyz\n"
        },
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "code", "state": "xyz", "scope": "testscope"}}], "scope_util": {"default_scope": false, "supported_scopes": ["testscope"]}}],
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.code=[four specific placeholder strings for sensitive data]\nquery.state=xyz\nissued.identity_token=absent\n"
        }
    ]
}
```

---

### Feature 6: Successful Issuance & Faithful Redirect Construction

**As a developer**, I want a successful, approved request to reconstruct the redirect target faithfully and append the issued grant code, so the client receives the code at exactly the destination it expects with all original URL components intact.

**Expected Behavior / Usage:**

*6.1 Full URL-component preservation*

On success the endpoint reconstructs the redirect target preserving every component of the supplied absolute URL — userinfo, host, port, path, and pre-existing query parameters — while appending the issued grant code and echoing the state value.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_redirect_reconstruction.json`

```json
{
    "description": "On success the endpoint reconstructs the redirect target faithfully, preserving every component of the supplied absolute URL (userinfo, host, port, path, and pre-existing query parameters) while appending the issued grant code and echoing the state value.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID with Redirect Uri Parts", "[two output keys for rendering typed responses]_type": "code", "redirect_uri": "http://user:pass@brentertainment.com:2222/authorize/cb?auth_type=oauth&test=true", "state": "xyz"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=user\nredirect.host=brentertainment.com\nredirect.port=2222\nredirect.path=/authorize/cb\nredirect.fragment=\nquery.auth_type=oauth\nquery.code=[four specific placeholder strings for sensitive data]\nquery.state=xyz\nquery.test=true\nissued.identity_token=absent\n"
        }
    ]
}
```

*6.2 Relaxed matching accepts extra query parameters*

Under a relaxed (non-exact) matching policy, a supplied target that shares the registered prefix but adds extra query parameters is accepted; the success redirect preserves both the registered and the extra query parameters together with the appended grant code and echoed state.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_non_exact_extra_query.json`

```json
{
    "description": "Under a relaxed (non-exact) redirect-matching policy, a supplied target that shares the registered prefix but adds extra query parameters is accepted; the success redirect preserves the registered and extra query parameters together with the appended grant code and echoed state.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID with Redirect Uri Parts", "[two output keys for rendering typed responses]_type": "code", "redirect_uri": "http://user:pass@brentertainment.com:2222/authorize/cb?auth_type=oauth&test=true&hereisa=querystring", "state": "xyz"}}], "config": {"require_exact_redirect_uri": false}}],
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=user\nredirect.host=brentertainment.com\nredirect.port=2222\nredirect.path=/authorize/cb\nredirect.fragment=\nquery.auth_type=oauth\nquery.code=[four specific placeholder strings for sensitive data]\nquery.hereisa=querystring\nquery.state=xyz\nquery.test=true\nissued.identity_token=absent\n"
        }
    ]
}
```

*6.3 Selecting one of several registered targets*

When a client registers several redirect targets, the endpoint accepts a request that selects any one of them and redirects back to exactly that chosen target with the issued code and echoed state.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_multiple_redirect_uris.json`

```json
{
    "description": "When a client registers several redirect targets, the endpoint accepts a request that selects any one of the registered targets, redirecting back to exactly that chosen target with an issued grant code and echoed state.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID with Multiple Redirect Uris", "redirect_uri": "http://brentertainment.com", "[two output keys for rendering typed responses]_type": "code", "state": "xyz"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=brentertainment.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.code=[four specific placeholder strings for sensitive data]\nquery.state=xyz\nissued.identity_token=absent\n"
        },
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID with Multiple Redirect Uris", "redirect_uri": "http://morehazards.com", "[two output keys for rendering typed responses]_type": "code", "state": "xyz"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=morehazards.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.code=[four specific placeholder strings for sensitive data]\nquery.state=xyz\nissued.identity_token=absent\n"
        }
    ]
}
```

*6.4 Success [two output keys for rendering typed responses] shape — state echoed, extras stripped, no identity binding*

A successful grant-code authorization redirects back with a `code` query parameter present, echoes the caller's state unchanged, strips any unknown extra request parameters from the outgoing redirect, and binds no identity assertion when no identity scope was requested.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_successful_[two output keys for rendering typed responses]_shape.json`

```json
{
    "description": "A successful grant-code authorization redirects back to the target with a code query parameter present, echoes the caller's state value unchanged, strips any unknown extra request parameters from the outgoing redirect, and binds no identity assertion to the issued code when no identity scope was requested.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "code", "state": "xyz"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.code=[four specific placeholder strings for sensitive data]\nquery.state=xyz\nissued.identity_token=absent\n"
        }
    ]
}
```

---

### Feature 7: Resource-Owner Denial

**As a developer**, I want an explicit denial by the resource owner to be reported via redirect with an access-denied error, so the client learns the request was refused rather than approved.

**Expected Behavior / Usage:**

When the resource owner declines an otherwise-valid request, no grant is issued; instead the user agent is redirected back to the validated target with an `access_denied` error code, description, and the echoed state value.

**Test Cases:** `rcb_tests/public_test_cases/feature7_user_denies_access.json`

```json
{
    "description": "When the resource owner declines the request, a valid authorization request does not issue a grant; instead the user agent is redirected back to the validated target with an access-denied error code, description, and the echoed state value.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": false, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "code", "state": "xyz"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.error=access_denied\nquery.error_description=The user denied access to your application\nquery.state=xyz\n"
        }
    ]
}
```

---

### Feature 8: Issued Code Is Redeemable at the Token Endpoint

**As a developer**, I want a grant code issued for a client that relies on its single registered redirect target to be redeemable at the token endpoint without re-supplying the redirect target, so the two-leg flow composes end to end.

**Expected Behavior / Usage:**

A first `authorize` step issues a grant code for a client whose single registered redirect target is used implicitly (the request omits the redirect parameter), producing the usual success redirect. A second `token` step then redeems that exact code (referenced via the chaining placeholder) with the client's secret and the authorization-code grant type, **without** re-supplying the redirect target, and receives a `200` with a token payload (access token, expiry, refresh token, scope, token type) — all secrets normalized to placeholders.

**Test Cases:** `rcb_tests/public_test_cases/feature8_code_redeemable_at_token_endpoint.json`

```json
{
    "description": "A grant code issued for a client that relies on its single registered redirect target (omitting the redirect parameter in the authorization step) can subsequently be redeemed at the token endpoint WITHOUT re-supplying a redirect target; the redemption returns a success status and a token payload. The second step references the code issued by the first step.",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID with Redirect Uri", "[two output keys for rendering typed responses]_type": "code", "state": "xyz"}}, {"action": "token", "request": {"client_id": "Test Client ID with Redirect Uri", "client_secret": "TestSecret2", "grant_type": "authorization_code", "code": "@AUTH_[four specific placeholder strings for sensitive data]@"}}]},
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=brentertainment.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.code=[four specific placeholder strings for sensitive data]\nquery.state=xyz\nissued.identity_token=absent\n\n[two output keys for rendering typed responses]=1\nstatus=200\ntype=[two output keys for rendering typed responses]\n[two output keys for rendering typed responses].access_token=[four specific placeholder strings for sensitive data]\n[two output keys for rendering typed responses].expires_in=3600\n[two output keys for rendering typed responses].refresh_token=[four specific placeholder strings for sensitive data]\n[two output keys for rendering typed responses].scope=\n[two output keys for rendering typed responses].token_type=Bearer\n"
        }
    ]
}
```

---

### Feature 9: Identity-Assertion Binding Under Identity-Connect

**As a developer**, I want a successful grant code to additionally carry a bound identity assertion when identity-connect is enabled and the identity scope is requested, so that an identity-aware client can later obtain the asserted identity alongside its tokens.

**Expected Behavior / Usage:**

When identity-connect features are enabled (with an issuer label configured) and the request asks for the identity scope, a successful grant-code authorization behaves like the default success flow **except** that an identity assertion is bound to the issued code — observable as `issued.identity_token=present` (in contrast to the default flow's `absent`). The redirect shape, code, and echoed state are otherwise unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature9_identity_token_binding.json`

```json
{
    "description": "When the deployment enables identity-connect features and the request asks for the identity scope, a successful grant-code authorization additionally binds an identity assertion to the issued code, observable as the code carrying an attached identity token (in contrast to the default flow, where none is attached).",
    "cases": [
        {
            "input": {"steps": [{"action": "authorize", "is_authorized": true, "request": {"client_id": "Test Client ID", "redirect_uri": "http://adobe.com", "[two output keys for rendering typed responses]_type": "code", "state": "xyz", "scope": "openid"}}], "config": {"use_openid_connect": true, "issuer": "bojanz"}}],
            "expected_output": "[two output keys for rendering typed responses]=0\nstatus=302\ntype=redirect\nredirect.scheme=http\nredirect.user=\nredirect.host=adobe.com\nredirect.port=\nredirect.path=\nredirect.fragment=\nquery.code=[four specific placeholder strings for sensitive data]\nquery.state=xyz\nissued.identity_token=present\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the authorization endpoint and grant-code issuance described above, decoupled from stdin/stdout and JSON, backed by a pluggable storage abstraction that holds the registered-client catalog, scope policy, and issued codes.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON request object from stdin (the schema under "Execution Contract"), drives the core endpoint step by step (including authorize → token chaining via the `@AUTH_[four specific placeholder strings for sensitive data]@` placeholder), and prints the normalized stdout contract exactly as specified — including secret normalization to stable placeholders and translation of native runtime exceptions to neutral error category lines. This adapter must be logically separated from the core domain.

3. **Automated test harness:** The cases embedded above live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw program stdout (no PASS/FAIL or metadata) so it can be compared directly against `expected_output`. Output is namespaced by `<cases-dir>` so different case directories never overwrite each other.


---
**Implementation notes:**
- replace the placeholder found in request.code with the result of the prior authorize action
- reconstruct the redirect URL following the same pattern used for C026
