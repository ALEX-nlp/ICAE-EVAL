## Product Requirement Document

# Pure-Dart Identity & Authentication Client — Email/Password Auth, Provider Discovery & Local Session Store

## Project Goal

Build a small, dependency-light client library that lets an application authenticate users against a remote identity backend over a plain HTTP/JSON REST protocol — registering accounts, signing in, discovering which sign-in methods an email already uses, and caching the signed-in session locally — so developers can add user authentication to a desktop/server program without embedding a heavyweight platform SDK.

---

## Background & Problem

An application that needs user accounts must talk to an identity backend: it sends a request (credentials, an email to inspect, a token to act on) and receives a JSON response that is either a success payload or a structured error. Without a dedicated client, every application re-implements the same request building, response parsing, error decoding, and local caching of the current session — inconsistently and error-prone.

This library provides one well-defined contract over that REST protocol. It builds the requests, parses the responses into typed result objects, and — crucially — translates the backend's raw error codes into a stable, vocabulary of normalized domain error categories so callers never have to special-case transport details. It also offers a tiny local key-value store so the current session can be persisted between runs.

The backend is an external dependency reached over HTTP. For deterministic, offline testing the backend's canned responses are supplied alongside each request (see the Execution Adapter contract below), keyed by a neutral endpoint role. Given the request parameters and those canned responses, every feature below produces a fully determined output.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., transport, request building, response parsing, error mapping, local persistence), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON command parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain, and for translating the HTTP transport (including the simulated backend responses) and any native exceptions into the stdout contract.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate transport, request building, response parsing, error normalization, and local persistence into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions; the HTTP transport in particular must be injectable so it can be replaced with a test double.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., a dedicated authentication-exception type carrying a normalized error code, and a dedicated storage-exception type) rather than relying on generic faults.

---

## Core Features

### Feature 1: Discover Sign-In Methods For An Email

**As a developer**, I want to ask the backend which sign-in methods are already registered for an email, so I can route a user to the right flow (or detect an invalid identifier) before asking for a password.

**Expected Behavior / Usage:**

The input is a request with action `fetch_providers`, the `email` to inspect, and a `responses` map holding the backend's canned reply for the provider-lookup endpoint under the role key `lookup`. Each role entry has an HTTP `status` and a JSON `body`. On success (`status` 200) the body carries an `allProviders` array of provider identifier strings; the client returns that list and the adapter prints a single line `providers=<comma-joined provider ids>` (an empty list prints `providers=` with nothing after the equals sign). On failure the body carries an `error` object whose `message` is the backend error code; the client raises a normalized authentication error and the adapter prints `error=<normalized-code>`. Normalization lower-cases the backend code and replaces underscores with hyphens, so a backend code of `INVALID_IDENTIFIER` becomes `[specific normalized error string for invalid user identifier]`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_provider_lookup.json`

```json
{
    "description": "Look up which sign-in methods are registered for a given email address by querying the identity backend. The request carries the email to look up and the canned backend response for the lookup endpoint. On a successful lookup the backend returns the list of provider identifiers associated with the address, and the client surfaces that list. When the backend rejects the lookup with an [specific normalized error string for invalid user identifier] failure (for example when the supplied identifier is empty or malformed), the client raises a normalized domain error whose category is reported instead of the provider list.",
    "cases": [
        {
            "input": {
                "action": "fetch_providers",
                "email": "user@example.com",
                "responses": {
                    "lookup": {
                        "status": 200,
                        "body": {"allProviders": ["password"], "registered": true}
                    }
                }
            },
            "expected_output": "providers=password\n"
        },
        {
            "input": {
                "action": "fetch_providers",
                "email": "",
                "responses": {
                    "lookup": {
                        "status": 400,
                        "body": {"error": {"code": 400, "message": "INVALID_IDENTIFIER"}}
                    }
                }
            },
            "expected_output": "error=[specific normalized error string for invalid user identifier]\n"
        }
    ]
}
```

---

### Feature 2: Register A New Account With Email & Password

**As a developer**, I want to create a new account from an email and password and immediately get back the authenticated identity, so I can sign the user in as part of registration.

**Expected Behavior / Usage:**

The input is a request with action `sign_up`, the `email` and `password` to register, and a `responses` map with two roles. The `register` role is the account-creation reply: on success its body returns an identity token (`idToken`), a `refreshToken`, the account's unique identifier (`localId`), and the `email`. The client then fetches the full profile via the `account` role: on success its body returns a `users` array whose first element holds `localId`, `email`, `createdAt` and `lastLoginAt` (epoch-millisecond timestamps expressed as strings), and a `providerUserInfo` array listing the linked sign-in providers. The client merges both payloads into a user object and the adapter prints seven lines, in this exact order: `email=<email>`, `uid=<localId>`, `is_new_user=<true|false>` (registration yields `true`), `provider_id=<the sign-in provider used>`, `is_anonymous=<true|false>` (true only when the account has no linked providers), `provider_count=<number of linked providers>`, and `creation_time_ms=<createdAt as an integer>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_account_registration.json`

```json
{
    "description": "Register a new account with an email and password and expose the resulting authenticated identity. The request supplies the chosen credentials together with two canned backend responses: one for the account-creation endpoint (which returns an identity token, refresh token and the new account's unique identifier) and one for the account-info endpoint (which returns the stored profile, including the unique identifier, email, creation and last-login timestamps in epoch milliseconds, and the list of linked sign-in providers). The client merges these into a user object and reports the email, unique identifier, whether the account is newly created, the sign-in provider used, whether the account is anonymous, how many linked providers it has, and the account creation time in epoch milliseconds.",
    "cases": [
        {
            "input": {
                "action": "sign_up",
                "email": "new.user@example.com",
                "password": "secret-pass",
                "responses": {
                    "register": {
                        "status": 200,
                        "body": {"idToken": "tok-abc", "email": "new.user@example.com", "refreshToken": "refresh-xyz", "localId": "[specific local ID format example extracted from the 'register' body]"}
                    },
                    "account": {
                        "status": 200,
                        "body": {"users": [{"localId": "[specific local ID format example extracted from the 'register' body]", "email": "new.user@example.com", "createdAt": "[specific epoch millisecond timestamp value used as a test case]", "lastLoginAt": "1600000005000", "providerUserInfo": [{"providerId": "password", "email": "new.user@example.com", "federatedId": "new.user@example.com"}]}]}
                    }
                }
            },
            "expected_output": "email=new.user@example.com\nuid=[specific local ID format example extracted from the 'register' body]\nis_new_user=true\nprovider_id=password\nis_anonymous=false\nprovider_count=1\ncreation_time_ms=[specific epoch millisecond timestamp value used as a test case]\n"
        }
    ]
}
```

---

### Feature 3: Normalize A Failed Email/Password Sign-In

**As a developer**, I want a failed sign-in to surface a stable, normalized error category rather than a transport-specific fault, so my caller can branch on a predictable code.

**Expected Behavior / Usage:**

The input is a request with action `sign_in`, the `email` and `password`, and a `responses` map whose `credential` role is the backend reply for the credential-verification endpoint. When that reply is a failure carrying an `error.message` of `EMAIL_NOT_FOUND` (no account matches the email), the client raises a normalized authentication error and the adapter prints a single line `error=email-not-found`. The normalization is the same transformation used everywhere: the backend code is lower-cased and its underscores become hyphens.

**Test Cases:** `rcb_tests/public_test_cases/feature3_signin_error.json`

```json
{
    "description": "Attempt to sign in with an email and password where the backend reports that no account corresponds to the supplied email. The request carries the credentials and a canned backend response for the credential-verification endpoint that signals an email-not-found failure. The client translates this backend failure into a normalized domain error and reports its category rather than completing the sign-in.",
    "cases": [
        {
            "input": {
                "action": "sign_in",
                "email": "ghost@example.com",
                "password": "secret-pass",
                "responses": {
                    "credential": {
                        "status": 400,
                        "body": {"error": {"code": 400, "message": "EMAIL_NOT_FOUND"}}
                    }
                }
            },
            "expected_output": "error=email-not-found\n"
        }
    ]
}
```

---

### Feature 4: Normalize A Failed Account Deletion

**As a developer**, I want deleting an account that the backend says is already gone to produce a stable normalized error, so I can handle the race cleanly.

**Expected Behavior / Usage:**

The input is a request with action `delete_account`, the `email` and `password` (used to first establish a signed-in user via the `register` and `account` roles, exactly as in Feature 2), plus a `remove` role giving the backend reply for the account-removal endpoint. When the removal reply is a failure carrying an `error.message` of `USER_NOT_FOUND`, the client raises a normalized authentication error and the adapter prints a single line `error=user-not-found`. (Had removal succeeded, the adapter would instead report that deletion completed and the current session was cleared.)

**Test Cases:** `rcb_tests/public_test_cases/feature4_account_deletion_error.json`

```json
{
    "description": "Create an account and then attempt to delete it, where the backend reports that the account no longer exists at deletion time. The request supplies credentials and canned backend responses for account creation and account-info retrieval (so a signed-in user is established), plus a canned response for the account-removal endpoint that signals a user-not-found failure. The client translates the deletion failure into a normalized domain error and reports its category.",
    "cases": [
        {
            "input": {
                "action": "delete_account",
                "email": "temp@example.com",
                "password": "secret-pass",
                "responses": {
                    "register": {
                        "status": 200,
                        "body": {"idToken": "tok-del", "email": "temp@example.com", "refreshToken": "refresh-del", "localId": "uid-del"}
                    },
                    "account": {
                        "status": 200,
                        "body": {"users": [{"localId": "uid-del", "email": "temp@example.com", "createdAt": "[specific epoch millisecond timestamp value used as a test case]", "lastLoginAt": "1600000005000", "providerUserInfo": [{"providerId": "password"}]}]}
                    },
                    "remove": {
                        "status": 400,
                        "body": {"error": {"code": 400, "message": "USER_NOT_FOUND"}}
                    }
                }
            },
            "expected_output": "error=user-not-found\n"
        }
    ]
}
```

---

### Feature 5: Local Session Persistence Store

**As a developer**, I want a small named key-value store backed by local storage, so I can persist the current session between runs and read it back.

**Expected Behavior / Usage:**

The input is a request with action `store`, a box `name`, an ordered list of `puts` (each a `key` plus a `value` that is either a string or `null`), and a `get` key to read back. Putting a key with a string value persists it. Putting a key with a `null` value removes the key (a `null` is never persisted). After applying all puts in order, the client reads the `get` key: if present, the adapter prints `value=<stored value>`; if the key is absent, or the named box was never written to at all, the read fails and the adapter prints `error=not_found`. The box is uniquely identified by its name; distinct names are independent stores.

**Test Cases:** `rcb_tests/public_test_cases/feature5_local_persistence.json`

```json
{
    "description": "A named local key-value store used to persist small pieces of session data. The request names a box, supplies an ordered list of put operations (each a key with either a string value or a null value), and finally names a key to read back. Storing a key with a string value makes it retrievable, and reading it back returns that value. Reading from a box that was never written to fails. Every failed read is reported as a normalized not-found error.",
    "cases": [
        {
            "input": {
                "action": "store",
                "name": "session-box",
                "puts": [{"key": "token", "value": "abc123"}],
                "get": "token"
            },
            "expected_output": "value=abc123\n"
        },
        {
            "input": {
                "action": "store",
                "name": "absent-box",
                "puts": [],
                "get": "token"
            },
            "expected_output": "error=not_found\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — an injectable HTTP transport, request builders, response parsers producing typed user/identity objects, an error-normalization layer mapping backend error codes to neutral hyphenated categories, and a named local key-value persistence store. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON command parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result (or normalized error) to stdout, matching the per-feature contracts above. The request's `action` selects behavior. For the network-backed actions (`fetch_providers`, `sign_in`, `sign_up`, `delete_account`) the request also carries a `responses` map that supplies the backend's canned reply for each endpoint role it will call — `lookup` (provider discovery), `credential` (credential verification), `register` (account creation), `account` (profile retrieval), and `remove` (account removal) — each with an HTTP `status` and JSON `body`; the adapter MUST inject these as the HTTP transport so no real network is touched. A reply whose `status` is an error and whose `body` contains an `error.message` is decoded into a normalized authentication error (`error=<lower-cased, hyphenated code>`). All native exceptions MUST be normalized to neutral `error=<category>` lines in the adapter layer; no host-language runtime type names may appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- retrive the string value matching the 'get' key from the 'puts' list following the same logic as the retrieval module
