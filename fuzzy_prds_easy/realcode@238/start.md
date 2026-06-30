## Product Requirement Document

# Geographic Coordinate String Formatter - Render latitude/longitude pairs as stable decimal text

## Project Goal

Build a small library that converts a geographic coordinate (a latitude/longitude pair of floating-point numbers) into a single, human- and machine-readable text token of the form `<latitude>,<longitude>`. The conversion must produce stable, plain-decimal output that is safe to embed in URLs and query strings, regardless of how the host platform's default number formatter would otherwise render the values.

---

## Background & Problem

Many platforms' default floating-point-to-text conversion switches to scientific/exponent notation for very small magnitudes (for example a longitude such as `0.000009` may be emitted as `9E-06`), and may drop a zero component down to an empty or ambiguous token. When such text is concatenated into a coordinate parameter, the result is malformed and rejected by downstream services that expect plain decimal coordinates.

Without this library, developers must hand-roll culture-independent formatting logic and special-case every tiny or zero-valued component, which is repetitive and error-prone. With this library, a developer constructs a coordinate from two numbers and obtains a single, dependable `latitude,longitude` string with the rounding/notation problems already solved.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a focused micro-utility: a small, well-organized module (a coordinate value type plus its text-rendering rule) is appropriate. Do not inflate it into a multi-layer framework, but keep the rendering rule cleanly separated from any I/O.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section define a **black-box contract** for an execution adapter, NOT the internal data model. The core value type must expose an idiomatic constructor and string conversion and must not know anything about JSON, stdin, or stdout. A thin adapter is solely responsible for parsing a JSON coordinate, calling the core conversion, and printing the result.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, the coordinate value type, the text-formatting rule, and output rendering as distinct units.
   - **Open/Closed Principle (OCP):** The formatting rule should be extendable (e.g. an alternate address-based location representation) without modifying the coordinate type.
   - **Liskov Substitution Principle (LSP):** Any alternative "location string source" must be substitutable wherever a location string is expected.
   - **Interface Segregation Principle (ISP):** Expose a minimal abstraction that yields only the location string.
   - **Dependency Inversion Principle (DIP):** Output rendering must depend on the abstraction, not on a concrete I/O implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Constructing a coordinate and converting it to text must read naturally in the target language.
   - **Resilience:** Formatting must be independent of the host's locale/regional number settings (the decimal separator is always `.`), and must handle very small magnitudes and exact-zero components without losing or corrupting them.

---

## Core Features

### Feature 1: Coordinate pair to plain-decimal string

**As a developer**, I want to turn a latitude/longitude pair into a single `latitude,longitude` text token, so I can embed coordinates in requests without worrying about exponent notation or locale-specific separators.

**Expected Behavior / Usage:**

The input is an object with two numeric fields, `lat` (latitude) and `lng` (longitude). The output is a single line containing the latitude and the longitude, each formatted as a plain decimal number, joined by a single comma, with no surrounding whitespace, followed by a trailing newline. The decimal separator is always a period (`.`) regardless of host locale. Negative values keep their leading minus sign, and ordinary fractional values are rendered as-is (for example `-33.8688,151.2093`). Two behaviors require special care and are split into the leaf sub-features below: very small-magnitude components, and exact-zero components.

*1.1 Small-magnitude components without scientific notation — A component whose magnitude is very small must still be written in plain fixed-point form.*

A component such as `0.000009` or `0.0000009` must be rendered in full positional decimal form (`0.000009`, `0.0000009`) and must never be emitted in scientific/exponent form (e.g. never `9E-06`). The number of fractional digits expands as needed to express the value exactly without rounding it away. The output is the joined `latitude,longitude` token followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_small_magnitude.json`

```json
{
    "description": "Convert a latitude/longitude pair into a single comma-joined decimal string. A component with a very small magnitude must be rendered in plain fixed-point decimal notation, never in scientific/exponent form.",
    "cases": [
        {"input": {"lat": 57.231, "lng": 0.000009}, "expected_output": "57.231,0.000009\n"},
        {"input": {"lat": 57.231, "lng": 0.0000009}, "expected_output": "57.231,0.0000009\n"}
    ]
}
```

*1.2 Zero-valued components render as `0.0` — An exactly-zero component must produce a stable literal token.*

When a component is exactly `0`, it must be rendered as the literal token `0.0` rather than collapsing to an empty string. This applies to either component independently, so a coordinate where both components are zero renders as `0.0,0.0`. The output is the joined `latitude,longitude` token followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_zero_component.json`

```json
{
    "description": "Convert a latitude/longitude pair where a coordinate component is exactly zero. A zero component must render as the literal token \"0.0\" rather than collapsing to an empty string or a bare integer.",
    "cases": [
        {"input": {"lat": 52.123123, "lng": 0.0}, "expected_output": "52.123123,0.0\n"},
        {"input": {"lat": 0.0, "lng": 0.0}, "expected_output": "0.0,0.0\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured module implementing a coordinate value type and its plain-decimal string conversion rule, scaled appropriately for a micro-utility (a small, logically separated module — not a monolithic god-file, and not an over-engineered framework). The formatting rule must be locale-independent and decoupled from any I/O.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON coordinate object (`{"lat": <number>, "lng": <number>}`) from stdin, invokes the core conversion, and prints the resulting `latitude,longitude` token plus a trailing newline to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_small_magnitude.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_small_magnitude@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
