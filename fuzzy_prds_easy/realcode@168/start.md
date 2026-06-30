## Product Requirement Document

# Media Transmission Direction Token Utility — Canonical Direction Names and Codes

## Project Goal

Build a small, dependency-light utility that converts media transmission-direction values between their human-readable token form and their compact numeric-code form, so that components describing a media stream's flow (whether it sends, receives, both, or neither) can agree on one canonical, validated representation instead of each one inventing its own spelling or numbering.

---

## Background & Problem

When two endpoints negotiate a media session, every media stream carries a *direction* describing how it flows: it may only send, only receive, do both, or be temporarily inactive. This direction is exchanged in two different shapes depending on the layer: a textual token (a readable name) at the configuration/API boundary, and a small integer code at the low-level/protocol boundary. A fifth state exists for a direction that has not yet been determined.

Without a shared utility, each layer re-implements its own ad-hoc mapping between names and codes, which leads to subtle bugs: an unrecognized or mis-cased name silently behaves like a valid one, or an out-of-range code is rendered as a misleading direction. This utility centralizes the mapping in one place. It recognizes a fixed set of canonical names, folds anything unrecognized into a neutral "undetermined" token, maps the well-known numeric codes to their token, and emits a distinct catch-all token for any code outside the known set.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain.

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

### Feature 1: Normalize A Direction Token By Name

**As a developer**, I want to hand the utility a direction name and get back the canonical token for that direction, so that any unrecognized or mis-spelled name is folded into a single well-defined "undetermined" value instead of leaking through as if it were valid.

**Expected Behavior / Usage:**

The input is a request with an action of `normalize` and a `direction` field holding a name string. The utility recognizes exactly four canonical names — `SendOnly` (sends only), `RecvOnly` (receives only), `SendRecv` (sends and receives), and `Inactive` (neither) — and returns that same name unchanged. Matching is exact and case-sensitive: any value that is not one of those four canonical names (different casing such as `sendrecv`, an unrelated word such as `Bidirectional`, the empty string, or even the literal word `[a failure sentinel — consult the default handler prefix list in the spec]`) is normalized to the single neutral token `[a failure sentinel — consult the default handler prefix list in the spec]`, which represents an undetermined direction. The result is the resolved token followed by a trailing newline. If the `direction` field is missing or is not a string, the utility instead emits a neutral error line `error=missing_field` followed by a line `field=direction`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_normalize_direction.json`

```json
{
    "description": "Normalize a media transmission-direction token. The input supplies a direction name; the utility recognizes a fixed set of canonical names and echoes the recognized name back unchanged. Any name that is not one of the recognized canonical tokens (wrong casing, empty, or an unrelated word) is normalized to the neutral sentinel token reserved for unrecognized directions. Matching is exact and case-sensitive.",
    "cases": [
        {"input": {"action": "normalize", "direction": "SendRecv"}, "expected_output": "SendRecv\n"},
        {"input": {"action": "normalize", "direction": "sendrecv"}, "expected_output": "[a failure sentinel — consult the default handler prefix list in the spec]\n"}
    ]
}
```

---

### Feature 2: Format A Numeric Direction Code Into Its Token

**As a developer**, I want to convert a compact numeric direction code into its canonical token, so that low-level code values can be rendered in their readable form and any out-of-range value is reported distinctly rather than masquerading as a valid direction.

**Expected Behavior / Usage:**

The input is a request with an action of `format` and an integer `code` field. The utility maps the well-known codes to their canonical token as follows: `0` → `[a failure sentinel — consult the default handler prefix list in the spec]`, `1` → `SendOnly`, `2` → `RecvOnly`, `3` → `SendRecv`, `4` → `Inactive`. Any integer outside this contiguous range (for example a large value or a negative value) maps to the distinct catch-all token `[the reserved magic token for invalid code ranges]`, which is reserved for codes the utility does not know about and is deliberately different from the `[a failure sentinel — consult the default handler prefix list in the spec]` token used for code `0`. The result is the resolved token followed by a trailing newline. If the `code` field is missing or is not an integer, the utility instead emits a neutral error line `error=missing_field` followed by a line `field=code`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_format_direction_code.json`

```json
{
    "description": "Format a numeric media-direction code into its canonical token. The input supplies an integer direction code; the utility maps each well-known code to its canonical direction token. The well-known codes are a small contiguous set; any integer outside that set (too large or negative) maps to a distinct catch-all token reserved for unrecognized codes.",
    "cases": [
        {"input": {"action": "format", "code": 1}, "expected_output": "SendOnly\n"},
        {"input": {"action": "format", "code": 9}, "expected_output": "[the reserved magic token for invalid code ranges]\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the two mappings described above (name → canonical token, and numeric code → canonical token). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core mapping logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resolved token (or a neutral error line) to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `normalize` resolves a `direction` name into its canonical token; `format` resolves an integer `code` into its canonical token. Recognized direction tokens are `SendOnly`, `RecvOnly`, `SendRecv`, `Inactive`, and the undetermined `[a failure sentinel — consult the default handler prefix list in the spec]`; the catch-all token for an out-of-range code is `[the reserved magic token for invalid code ranges]`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same error format sequence as defined in the `validation_errors` module
- mimic the fallback behavior of the 'action_dispatch' module for unknown action keys
