## Product Requirement Document

# Time-Based One-Time-Password Engine — TOTP Code Generation, Verification & Provisioning

## Project Goal

Build a reusable two-factor authentication engine that turns a single shared secret into time-based one-time-password (TOTP) codes, verifies submitted codes within a configurable tolerance, enforces single-use, exports the secret as a standard provisioning URI for authenticator apps, and manages a set of single-use recovery codes — so developers can add second-factor login to an application without hand-rolling the cryptography or the wire formats.

---

## Background & Problem

Adding a second authentication factor means implementing the TOTP standard correctly: deriving a time-step counter from the current time, computing an HMAC over that counter with the user's secret, truncating it to a short numeric code, and checking submitted codes against a small window of neighbouring time-steps to absorb clock drift — while making sure a code cannot be replayed. On top of that, the secret must be handed to an authenticator app in the exact `otpauth://` URI shape those apps expect, and a fallback set of recovery codes must be tracked so a user who loses their device can still get in.

Without a dedicated engine, every project re-implements this fiddly, security-sensitive logic and the precise output formats, which is repetitive and error-prone. With this engine, developers get one well-defined contract: feed in a secret and the moment in time, get back a code; submit a code with a tolerance window, get back accept/reject (with replay refused); ask for the provisioning URI or the grouped secret, and manage recovery codes — all as deterministic, inspectable outputs.

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

### Feature 1: Generate A Time-Based Code For A Moment

**As a developer**, I want to turn a shared secret and a point in time into a short numeric code, so the user's authenticator app and my server agree on the same code at the same moment.

**Expected Behavior / Usage:**

The input supplies a Base32-encoded shared secret, the hash algorithm (`sha1`, `sha256`, `sha512`), the number of output digits, and the time-step length in seconds, together with a Unix timestamp (seconds since the epoch, in UTC) and an optional integer step `offset`. The engine derives the time-step counter by integer-dividing the timestamp by the step length, computes the HMAC of that counter (encoded as an 8-byte big-endian value) under the raw secret, applies the standard dynamic-truncation rule to extract a 31-bit integer, reduces it modulo ten-to-the-`digits`, and renders the result as a decimal string left-zero-padded to exactly `digits` characters. The `offset` shifts the counter by that many whole time-steps before generating (negative = earlier step, positive = later step), which is how a verifier inspects neighbouring steps; it defaults to 0. Any two timestamps inside the same time-step yield the same code. The output is the code as `code=<digits>` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_generate_code.json`

```json
{
    "description": "Generate a time-based one-time-password (TOTP) code for an explicit moment in time. The engine is given a Base32-encoded shared secret, the number of output digits, the time-step length in seconds, and the hash algorithm. From a Unix timestamp (seconds since the epoch, UTC) it derives the current time-step counter, computes the HMAC of that counter under the secret, applies the standard dynamic-truncation rule, reduces the result modulo ten-to-the-digits, and renders it as a fixed-width zero-padded decimal string. An optional integer step offset shifts the counter by that many whole time-steps (negative for earlier steps, positive for later), which is how a verifier inspects neighbouring windows. Codes are stable across any timestamp that falls inside the same time-step.",
    "cases": [
        {
            "input": {"action": "generate_code", "secret": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3", "algorithm": "sha1", "digits": 6, "seconds": 30, "timestamp": 1577910600, "offset": 0},
            "expected_output": "code=716347\n"
        },
        {
            "input": {"action": "generate_code", "secret": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3", "algorithm": "sha1", "digits": 6, "seconds": 30, "timestamp": 1577910600, "offset": -1},
            "expected_output": "code=779186\n"
        }
    ]
}
```

---

### Feature 2: Verify A Submitted Code

**As a developer**, I want to check a code a user typed in, tolerating a little clock drift but refusing reused codes, so legitimate logins succeed while replay attempts fail.

**Expected Behavior / Usage:**

*2.1 Backward Tolerance Window — accept the current step and a bounded number of preceding steps*

The input supplies the same TOTP parameters plus a non-negative `window`, and a list of `checks`, each with a submitted `code` and the Unix timestamp `at` which the check occurs. A code is accepted when it equals the code of the time-step containing `at`, or the code of any of the `window` time-steps immediately before it; the window only looks backward, never forward. A `window` of 0 accepts only the exact current step's code. A positive `window` keeps a code generated for one step acceptable for that many later steps, but rejects it once `at` advances beyond the window, or precedes the step that produced the code. Each check is emitted on its own line as `code=<submitted> at=<timestamp> valid=<true|false>` followed by a newline, in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_validate_window.json`

```json
{
    "description": "Validate a candidate code against the shared secret at a given moment, tolerating a backward verification window. The engine accepts the same TOTP parameters plus a non-negative window size. For each check it is given the submitted code and the Unix timestamp at which the check happens. A code is accepted if it equals the code of the current time-step or of any of the preceding `window` time-steps (the window only looks backward, never forward), and rejected otherwise. With a window of zero, only the exact current time-step's code is accepted. With a positive window, a code generated for one step is still accepted for that many later steps but rejected once the moment advances beyond the window or precedes the step that produced it. Each check is reported on its own line echoing the submitted code, the timestamp, and whether it was accepted.",
    "cases": [
        {
            "input": {"action": "validate_code", "secret": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3", "algorithm": "sha1", "digits": 6, "seconds": 30, "window": 1, "checks": [{"code": "716347", "at": 1577910600}]},
            "expected_output": "code=716347 at=1577910600 valid=true\n"
        },
        {
            "input": {"action": "validate_code", "secret": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3", "algorithm": "sha1", "digits": 6, "seconds": 30, "window": 1, "checks": [{"code": "716347", "at": 1577910660}]},
            "expected_output": "code=716347 at=1577910660 valid=false\n"
        }
    ]
}
```

*2.2 Single-Use Replay Protection — a code is accepted at most once*

When several checks are processed against the same engine in one session, the engine remembers any code it just accepted (for the lifetime of the current step plus its window). Submitting the identical code again at the same moment is rejected even though it would otherwise still be time-valid. The first submission of a valid code yields `valid=true`; an immediate re-submission of the same code yields `valid=false`. Output follows the same per-check line format as 2.1.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_validate_single_use.json`

```json
{
    "description": "A code may only be accepted once: replay must be rejected. Within a single validation session the engine remembers every code it has just accepted for the duration of the current step (plus its window), so submitting the very same code a second time at the same moment is refused even though the code is otherwise still time-valid. The checks in a case are processed in order against the same engine instance so the remembered state carries across them. The first submission of a valid code is accepted; an immediate re-submission of the identical code is rejected.",
    "cases": [
        {
            "input": {"action": "validate_code", "secret": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3", "algorithm": "sha1", "digits": 6, "seconds": 30, "window": 0, "checks": [{"code": "716347", "at": 1577910600}, {"code": "716347", "at": 1577910600}]},
            "expected_output": "code=716347 at=1577910600 valid=true\ncode=716347 at=1577910600 valid=false\n"
        }
    ]
}
```

---

### Feature 3: Export A Provisioning URI

**As a developer**, I want to hand the secret to an authenticator app in the exact URI shape it expects, so the user can set up their second factor by scanning or pasting a single string.

**Expected Behavior / Usage:**

The input supplies the Base32 secret, a `label` of the form `issuer:account`, the hash algorithm and the digit count. The engine emits a URI with scheme `otpauth` and type `totp` whose path segment is the percent-encoded label, followed by a query string carrying, in this order: `issuer` (the part of the label before the first colon), `label` (the full label), `secret` (verbatim), `algorithm` (upper-cased), and `digits`. Query values are encoded per RFC 3986, so `:` becomes `%3A` and `@` becomes `%40`. The output is the URI followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_provisioning_uri.json`

```json
{
    "description": "Serialize the shared secret into a standard otpauth provisioning URI that authenticator apps can import. The engine is given the Base32 secret, a label of the form `issuer:account`, the hash algorithm and the digit count. It emits a URI of scheme `otpauth`, type `totp`, whose path segment is the percent-encoded label, followed by a query string carrying the issuer (the portion of the label before the first colon), the full label, the secret verbatim, the upper-cased algorithm name, and the digit count. Query values are encoded per RFC 3986 (so `:` becomes `%3A` and `@` becomes `%40`), and the query parameter order is issuer, label, secret, algorithm, digits.",
    "cases": [
        {
            "input": {"action": "uri", "secret": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3", "label": "quz:test@foo.com", "algorithm": "sha256", "digits": 14},
            "expected_output": "[a pre-generated OTPAUTH URI string — requires checking the secret key configuration]\n"
        }
    ]
}
```

---

### Feature 4: Present The Shared Secret As Text

**As a developer**, I want both the raw secret and a human-readable grouped form, so I can store the secret and also show it to users who type it in manually.

**Expected Behavior / Usage:**

*4.1 Raw Secret — the secret verbatim*

The string form of the secret is exactly the Base32 secret the engine holds, unchanged, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_secret_raw.json`

```json
{
    "description": "Expose the shared secret as its plain string form. The engine's string representation of the secret is exactly the Base32 secret it holds, with no separators, prefixes, or transformation.",
    "cases": [
        {
            "input": {"action": "secret_raw", "secret": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3"},
            "expected_output": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3\n"
        }
    ]
}
```

*4.2 Grouped Secret — four-character chunks for manual entry*

The secret is split into chunks of four characters joined by a single space, with no trailing space after the last chunk, followed by a newline. Characters are otherwise unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_secret_grouped.json`

```json
{
    "description": "Render the shared secret as a human-friendly grouped string for manual entry. The secret is split into chunks of four characters separated by a single space, with no trailing space after the final chunk. The characters are otherwise unchanged.",
    "cases": [
        {
            "input": {"action": "secret_grouped", "secret": "KS72XBTN5PEBGX2IWBMVW44LXHPAQ7L3"},
            "expected_output": "KS72 XBTN 5PEB GX2I WBMV W44L XHPA Q7L3\n"
        }
    ]
}
```

---

### Feature 5: Manage Recovery Codes

**As a developer**, I want to issue fallback recovery codes and spend them one at a time, so a user who loses their authenticator can still log in, and each code only works once.

**Expected Behavior / Usage:**

*5.1 Generate A Batch — a fixed number of fresh, unused codes of a fixed length*

Given a requested `amount` and per-code `length`, the engine produces exactly `amount` codes, each exactly `length` characters long, all initially unused. The concrete code values are random and are NOT part of the contract; the deterministic, observable facts are the batch size, the (uniform) code length, and that every code starts unused. The output reports `count=<amount>`, `length=<length>` (the uniform length, or -1 if codes differ in length), and `unused=<count of unused codes>`, each on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_generate_recovery.json`

```json
{
    "description": "Generate a fresh batch of single-use recovery codes. Given a requested amount and a per-code character length, the engine produces exactly that many codes, each exactly that many characters long, and all initially unused. The code values themselves are random (not part of the contract); the observable, deterministic facts are the batch size, the uniform code length, and that every code starts unused. The output reports the total count, the uniform code length, and the number of unused codes.",
    "cases": [
        {
            "input": {"action": "generate_recovery", "amount": 10, "length": 8},
            "expected_output": "count=10\nlength=8\nunused=10\n"
        }
    ]
}
```

*5.2 Consume Codes — spend a code at most once and report what remains*

The engine holds a list of recovery entries, each with a `code` value and a `used_at` marker (`null` when still available). For each value in `consume`, the engine marks the first matching still-unused entry as used and reports `success=true`; if no matching unused entry exists (the value is unknown, or its only match is already used) it reports `success=false` and changes nothing. After all consumption attempts it reports `unused=<count of entries still unused>` and `contains_unused=<true|false>` (whether any unused entry remains). An absent (`null`) or empty set has zero unused entries. Output is one `consume=<value> success=<bool>` line per attempt (in order), then the `unused` line, then the `contains_unused` line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_recovery_codes.json`

```json
{
    "description": "Consume recovery codes from a stored set and report what remains. The engine holds a list of recovery entries, each with a code value and a used marker (null when still available). Consuming a code marks the first matching still-unused entry as used and reports success; consuming a code that does not exist, or one whose only matching entry is already used, reports failure and changes nothing. After processing all consumption attempts, the engine reports how many entries remain unused and whether any unused entry still exists. An empty or absent set has no unused entries.",
    "cases": [
        {
            "input": {"action": "consume_recovery", "recovery_codes": [{"code": "AAA", "used_at": null}, {"code": "BBB", "used_at": null}, {"code": "CCC", "used_at": null}], "consume": ["AAA", "AAA", "ZZZ"]},
            "expected_output": "[a deterministic consume result set based on an admin-provided recovery code list]\nconsume=AAA success=false\nconsume=ZZZ success=false\n[a deterministic consume result set based on an admin-provided recovery code list]\n[a deterministic consume result set based on an admin-provided recovery code list]\n"
        },
        {
            "input": {"action": "consume_recovery", "recovery_codes": null, "consume": []},
            "expected_output": "unused=0\ncontains_unused=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the TOTP code generation, verification (with backward tolerance window and single-use replay protection), provisioning-URI export, secret text formatting, and recovery-code management described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command from stdin, selects behavior by the `action` field (`generate_code`, `validate_code`, `uri`, `secret_raw`, `secret_grouped`, `generate_recovery`, `consume_recovery`), invokes the appropriate core logic, and prints the raw result to stdout, matching the per-feature contracts above. Timestamps are Unix seconds in UTC; codes are zero-padded to the requested digit count; the verification window looks only backward.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- keep using standard URI encoding rules like in REST spec versions
