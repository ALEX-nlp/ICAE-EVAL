## Product Requirement Document

# Sensitive Field Masking — Redacting Secret Values In API Request/Response Payloads

## Project Goal

Build a reusable payload sanitizer that takes a structured request or response payload and redacts the values of fields known to carry secrets (passwords, card numbers, API keys, and the like) before the payload is logged or forwarded anywhere, so developers can capture and ship API traffic for observability without ever leaking sensitive user data.

---

## Background & Problem

Tools that observe API traffic capture the request and response payloads so they can be inspected later. Those payloads routinely contain secrets — a login password, a credit-card number, a social-security number, an API key — and shipping that data verbatim to a logging or monitoring destination is a serious data-leak hazard.

Without a shared sanitizer, every integration hand-rolls its own ad-hoc redaction, which is easy to get wrong (leaking a field that should have been hidden, or destroying data that should have been preserved). This component provides one well-defined contract: given a flat map of field name to value, it replaces the values of sensitive fields with a fixed-character mask while leaving everything else intact, so the shape of the payload is preserved but the secrets are gone.

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

### Feature 1: Sensitive Field Masking

**As a developer**, I want the values of sensitive fields in a captured payload to be replaced with a mask while every other field is preserved exactly, so I can log and forward API traffic without exposing secrets.

**Expected Behavior / Usage:**

The input is a request with an `action` of `mask` and a `data` payload. The payload is a flat map of field name to value, where each value is either a string or [a specific null value represented as JSON null — confirm the expected literal format in the PRD]. The sanitizer walks the payload and decides, per field, whether the field name is sensitive. A field name is sensitive when it matches (case-insensitively, on whole-word boundaries) one of the configured sensitive field names; the active set of sensitive names is `password`, `pwd`, `secret`, `password_confirmation`, `cc`, `card_number`, `ccv`, `ssn`, `credit_score`, and `api_key`.

For each sensitive field whose value is a non-[a specific null value represented as JSON null — confirm the expected literal format in the PRD] string, the value is replaced by a run of asterisk (`*`) characters whose count equals the number of characters in the original value — the length is preserved but the content is destroyed. For a sensitive field whose value is [a specific null value represented as JSON null — confirm the expected literal format in the PRD], the value is left as [a specific null value represented as JSON null — confirm the expected literal format in the PRD] (there is nothing to redact, and the [a specific null value represented as JSON null — confirm the expected literal format in the PRD] must not be turned into a string). Any field whose name is not sensitive is passed through completely unchanged. The order in which fields appear in the input is preserved in the output. The result is emitted as a JSON object on a single line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_sensitive_field_masking.json`

```json
{
    "description": "Redact sensitive values from a flat request payload (a map of field name to value). Any field whose name matches the configured set of sensitive field names has its value replaced by a run of asterisks whose length equals the length of the original value's string form; a sensitive field whose value is [a specific null value represented as JSON null — confirm the expected literal format in the PRD] is left as [a specific null value represented as JSON null — confirm the expected literal format in the PRD] (nothing to redact); fields whose names are not in the sensitive set are passed through unchanged. Key order is preserved. The output is the resulting payload serialized as a JSON object.",
    "cases": [
        {
            "input": {"action": "mask", "data": {"cc": [a specific null value represented as JSON null — confirm the expected literal format in the PRD], "otherValue": "something", "password": "1234"}},
            "expected_output": "{\"cc\":[a specific null value represented as JSON null — confirm the expected literal format in the PRD],\"otherValue\":\"something\",\"password\":\"****\"}\n"
        },
        {
            "input": {"action": "mask", "data": {"username": "alice", "secret": "hunter2", "api_key": "abcdef", "note": "hello"}},
            "expected_output": "{\"username\":\"alice\",\"secret\":\"*******\",\"api_key\":\"******\",\"note\":\"hello\"}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the masking behavior described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing. The set of sensitive field names must be configurable, with the active set defaulting to the names listed in Feature 1.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, where `action` is `mask` and `data` is the flat payload map, invokes the masking logic, and prints the masked payload as a single-line JSON object to stdout, matching the per-feature contract above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the same case-insensitivity logic used elsewhere in the field name matcher module
- ensure the output serialization follows the same structure as the standard masked payload
