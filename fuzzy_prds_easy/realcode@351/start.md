## Product Requirement Document

# Web Account Authentication Framework - Request/Response Contract

## Project Goal
Build a web account authentication framework that allows developers to add sign-in, sign-out, registration, password recovery, confirmation, unlocking, remembered sessions, timeouts, and sign-in tracking to web applications without hand-writing repetitive and security-sensitive account-flow plumbing.

---

## Background & Problem
Without this library/tool, developers are forced to manually wire account storage, credential verification, HTTP redirects, validation messages, mail-based token flows, cookie-based remembered sessions, and multi-scope session policy. This leads to repetitive code, inconsistent framework behavior, security mistakes, and brittle maintenance across applications.

With this library/tool, developers can configure account flows declaratively while the framework performs the underlying web requests, persistence updates, mail delivery, cookies, redirects, and session state transitions in a consistent way.

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

### Feature 1: Session Sign-In

**As a developer**, I want to rely on framework-managed session sign-in, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives a sign-in request containing an account category, stored identifier, submitted identifier, and submitted password. It must exercise the web sign-in flow and print the HTTP status, final path, authenticated account scopes, and visible message. Identifier case and whitespace normalization are configurable inputs; when normalization is disabled, mismatching submitted identifiers must remain unauthenticated and expose the invalid-credentials message.

**Test Cases:** `rcb_tests/public_test_cases/feature1_session_sign_in.json`

```json
{
    "description": "Session sign-in authenticates the correct account scope, applies configured identifier normalization, and reports HTTP/session signals.",
    "cases": [
        {
            "input": {
                "scenario": "sign_in",
                "account": "user",
                "stored_email": "Foo@Bar.com",
                "submitted_email": "foo@bar.com"
            },
            "expected_output": "status=200\npath=/\nauthenticated_user=true\nauthenticated_admin=false\nmessage=[specific counter pattern description]\n"
        }
    ]
}
```

---

### Feature 2: Protected Route Access

**As a developer**, I want to rely on framework-managed protected route access, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives a request to access a protected administrator area with no session, a regular-account session, or an administrator-account session. It must print the response status, current path, redirect target, authentication state for both scopes, and the protected-page marker when access is allowed.

**Test Cases:** `rcb_tests/public_test_cases/feature2_protected_routes.json`

```json
{
    "description": "Protected routes allow only the required authenticated scope and expose redirect or success signals.",
    "cases": [
        {
            "input": {
                "scenario": "admin_area",
                "signed_in_as": "[specific counter pattern description]"
            },
            "expected_output": "status=302\npath=null\nredirect_to=/admin_area/sign_in\nauthenticated_user=false\nauthenticated_admin=false\nbody_marker=[specific counter pattern description]\n"
        }
    ]
}
```

---

### Feature 3: Scoped Sign-Out

**As a developer**, I want to rely on framework-managed scoped sign-out, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives a sign-out request after both account scopes are signed in plus a boolean cross-scope sign-out policy. It must invoke the web sign-out route and print the response status, redirect target, and which account scopes remain authenticated.

**Test Cases:** `rcb_tests/public_test_cases/feature3_sign_out_scope_policy.json`

```json
{
    "description": "Signing out one account scope respects the configured cross-scope sign-out policy.",
    "cases": [
        {
            "input": {
                "scenario": "sign_out_scopes",
                "sign_out": "user",
                "sign_out_all_account_scopes": false
            },
            "expected_output": "status=302\nredirect_to=/\nauthenticated_user=false\nauthenticated_admin=true\n"
        }
    ]
}
```

---

### Feature 4: Account Registration

**As a developer**, I want to rely on framework-managed account registration, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives registration form fields for either an active account category or a confirmation-required account category. It must submit the registration form and print the HTTP status, resulting path, authentication state, visible message, persisted email, and confirmation state where applicable. Invalid registration data must return validation-visible output and must not create an account.

**Test Cases:** `rcb_tests/public_test_cases/feature4_registration.json`

```json
{
    "description": "Registration creates accounts, authenticates active accounts, and blocks inactive accounts pending confirmation.",
    "cases": [
        {
            "input": {
                "scenario": "registration",
                "account": "admin",
                "email": "new_user@test.com",
                "password": "new_user123",
                "password_confirmation": "new_user123"
            },
            "expected_output": "status=200\npath=/admin_area/home\nauthenticated_user=false\nauthenticated_admin=true\nmessage=Welcome! You have signed up successfully.\ncreated_email=new_user@test.com\n"
        }
    ]
}
```

---

### Feature 5: Account Updates

**As a developer**, I want to rely on framework-managed account updates, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives an authenticated account-update request with proposed email and/or password fields plus the current password. It must submit the account edit flow and print the HTTP status, resulting path, authentication state, visible message, persisted email, and password-validity signal when a new password was submitted. A wrong current password must leave persisted account data unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature5_account_update.json`

```json
{
    "description": "Authenticated account updates require the current password and preserve or replace credentials according to submitted fields.",
    "cases": [
        {
            "input": {
                "scenario": "account_update",
                "new_email": "user.new@example.com",
                "current_password": "12345678"
            },
            "expected_output": "status=200\npath=/\nauthenticated_user=true\nauthenticated_admin=false\nmessage=Your account has been updated successfully.\nstored_email=user.new@example.com\n"
        }
    ]
}
```

---

### Feature 6: Password Reset Requests

**As a developer**, I want to rely on framework-managed password reset requests, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives a password-reset request containing a stored account email and a submitted email. It must exercise the forgot-password web flow and print the HTTP status, resulting path, visible message, number of instruction emails sent, email recipient/sender, and whether the mail body contains a reset link. Configurable case and whitespace normalization determine whether the submitted email matches the stored account.

**Test Cases:** `rcb_tests/public_test_cases/feature6_password_reset_request.json`

```json
{
    "description": "Password reset requests normalize configured identifiers, return framework responses, and send reset instructions only for matched accounts.",
    "cases": [
        {
            "input": {
                "scenario": "password_reset_request",
                "stored_email": "Foo@Bar.com",
                "submitted_email": "foo@bar.com"
            },
            "expected_output": "status=200\npath=/users/sign_in\nmessage=You will receive an email with instructions on how to reset your password in a few minutes.\nmail_count=1\nmail_to=foo@bar.com\nmail_from=please-change-me@config-initializers-devise.com\nbody_has_reset_path=true\n"
        }
    ]
}
```

---

### Feature 7: Password Reset Token Consumption

**As a developer**, I want to rely on framework-managed password reset token consumption, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives a password-reset token category and new password fields. It must exercise the reset form and print the HTTP status, resulting path, authentication state, visible message, and whether the stored password changed. Invalid tokens or mismatched confirmation fields must leave the password unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature7_password_reset_change.json`

```json
{
    "description": "Password reset token consumption changes the password only for a valid token and valid matching password fields.",
    "cases": [
        {
            "input": {
                "scenario": "password_reset_change",
                "token": "valid",
                "password": "987654321",
                "password_confirmation": "987654321"
            },
            "expected_output": "status=200\npath=/\nauthenticated_user=true\nauthenticated_admin=false\nmessage=Your password has been changed successfully. You are now signed in.\npassword_changed=true\n"
        }
    ]
}
```

---

### Feature 8: Email Confirmation

**As a developer**, I want to rely on framework-managed email confirmation, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives either a confirmation-instruction request or a confirmation-token consumption request, optionally using JSON format and token-age constraints. It must print HTTP status/path or JSON error signals, email delivery count for instruction requests, visible message, and whether the account became confirmed.

**Test Cases:** `rcb_tests/public_test_cases/feature8_email_confirmation.json`

```json
{
    "description": "Email confirmation requests and token consumption expose HTML/JSON framework outcomes and account confirmation state.",
    "cases": [
        {
            "input": {
                "scenario": "confirmation",
                "mode": "request"
            },
            "expected_output": "status=200\npath=/users/sign_in\nmessage=You will receive an email with instructions for how to confirm your email address in a few minutes\nmail_count=1\njson_has_errors=false\n"
        }
    ]
}
```

---

### Feature 9: Account Unlocking

**As a developer**, I want to rely on framework-managed account unlocking, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives either an unlock-instruction request or an unlock-token consumption request, optionally using JSON format. It must print HTTP status/path or JSON error signals, email delivery count for instruction requests, visible message, and whether the account remains locked.

**Test Cases:** `rcb_tests/public_test_cases/feature9_account_unlock.json`

```json
{
    "description": "Locked-account unlock requests and token consumption expose mail delivery, HTTP status, JSON errors, and lock state.",
    "cases": [
        {
            "input": {
                "scenario": "unlock",
                "mode": "request",
                "locked": true
            },
            "expected_output": "status=200\npath=/users/sign_in\nmessage=You will receive an email with instructions for how to unlock your account in a few minutes\nmail_count=1\njson_has_errors=false\n"
        }
    ]
}
```

---

### Feature 10: Remembered Sessions

**As a developer**, I want to rely on framework-managed remembered sessions, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives either a sign-in request with a remember-me flag or a future request carrying a remembered-session token. It must print HTTP/authentication state and whether a remember cookie was created or consumed. Invalid remembered tokens must redirect to sign-in and remain unauthenticated.

**Test Cases:** `rcb_tests/public_test_cases/feature10_remembered_sessions.json`

```json
{
    "description": "Remember-me sessions create cookies when requested and authenticate future requests only with a valid remembered token.",
    "cases": [
        {
            "input": {
                "scenario": "remember_session",
                "mode": "sign_in",
                "remember": false
            },
            "expected_output": "status=200\nauthenticated_user=true\nauthenticated_admin=false\nremember_cookie_present=false\n"
        }
    ]
}
```

---

### Feature 11: Session Timeout

**As a developer**, I want to rely on framework-managed session timeout, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives an active or expired session setup and a cross-scope timeout policy. It must access a protected route and print HTTP status, redirect target, authenticated scopes, and visible message. Expired sessions must sign out the configured scopes while non-expired sessions remain authenticated.

**Test Cases:** `rcb_tests/public_test_cases/feature11_session_timeout.json`

```json
{
    "description": "Expired sessions are signed out according to scope policy while active sessions remain authenticated.",
    "cases": [
        {
            "input": {
                "scenario": "timeout",
                "expired": false
            },
            "expected_output": "status=200\nredirect_to=null\nauthenticated_user=true\nauthenticated_admin=false\nmessage=[specific counter pattern description]\n"
        }
    ]
}
```

---

### Feature 12: Sign-In Tracking

**As a developer**, I want to rely on framework-managed sign-in tracking, so I can deliver account flows with consistent HTTP, persistence, mail, cookie, and session behavior.

**Expected Behavior / Usage:**

The adapter receives a tracking mode for successful sign-ins. It must print sign-in counters, timestamp ordering, IP metadata, or skipped-tracking status depending on the requested mode. Tracking can be suppressed by an explicit skip signal.

**Test Cases:** `rcb_tests/public_test_cases/feature12_sign_in_tracking.json`

```json
{
    "description": "Successful sign-ins update tracking counters and IP metadata unless tracking is explicitly skipped.",
    "cases": [
        {
            "input": {
                "scenario": "tracking",
                "mode": "count"
            },
            "expected_output": "sign_in_count=2\n[timestamp ordering convention reference]\n"
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
- matching normalization config
- instructions for email address
