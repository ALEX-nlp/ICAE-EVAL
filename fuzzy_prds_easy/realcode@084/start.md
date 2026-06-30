## Product Requirement Document

# Request Option String Parsing - Header and Route-Mapping Decoders

## Project Goal

Build a small option-parsing library that turns raw, user-supplied configuration strings (the kind typed on a command line or written in a config file) into clean, structured maps. It focuses on two recurring shapes: HTTP header definitions and source-to-destination route mappings. The library hides the fiddly details of separator handling, whitespace trimming, escaping, and input validation so the rest of an application can work with ready-to-use key/value maps.

---

## Background & Problem

Tools that accept repeatable options frequently receive values such as `Header-Name: value` or `/source/path=https://target`. Without a dedicated decoder, every call site must re-implement the same brittle logic: find the right separator, decide what counts as the key versus the value, trim stray spaces, deal with separator characters that legitimately appear inside a value, and detect malformed input. This leads to duplicated, error-prone string code and inconsistent behavior across the application.

With this library, callers hand over the raw strings and receive a validated map. Header lines are split on their first colon with values trimmed; route mappings are split on a single unescaped equals sign with escaped equals signs preserved as literal characters; and clearly malformed mappings are rejected with a descriptive error instead of producing silent garbage.

---

## Protocol

Each operation is invoked by sending one JSON object on standard input. The object always has an `op` field naming the operation, plus the operation's argument field. The program prints a plain-text result to standard output.

For operations that yield a map, the first output line is `count=N` (the number of entries), followed by one line per entry formatted as `key => value`, emitted in the same order the inputs were supplied.

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

### Feature 1: Header Line Decoding

**As a developer**, I want to turn raw header definition lines into a name/value map, so I can apply caller-specified headers without writing colon-splitting code everywhere.

**Expected Behavior / Usage:**

The `parse_headers` operation takes a `headers` array of raw strings. For each string, the first colon separates the header name (everything before it) from the header value (everything after it). The value has its surrounding whitespace trimmed. Header names are treated case-insensitively when forming the map, but the original spelling of each name is preserved in the output. The result is printed as a `count=N` line followed by one `name => value` line per entry, in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_parse_headers.json`

```json
{
    "description": "Parse a list of raw HTTP header definition lines into a header-name to header-value map. Each line uses a colon to separate the name from the value; the value is taken from everything after the first colon, with surrounding whitespace trimmed. Header names are matched case-insensitively. The output reports the number of resulting entries followed by one 'name => value' line per entry in input order.",
    "cases": [
        {
            "input": {"op": "parse_headers", "headers": ["X-XSS-Protection: 1; mode=block", "x-frame-options:SAMEORIGIN"]},
            "expected_output": "count=2\nX-XSS-Protection => 1; mode=block\nx-frame-options => SAMEORIGIN\n"
        }
    ]
}
```

---

### Feature 2: Route Mapping Decoding

**As a developer**, I want to turn raw route-mapping strings into a source-to-destination map, so I can configure path forwarding from a single flat string while still allowing equals signs inside the values.

**Expected Behavior / Usage:**

*2.1 Valid mapping parsing — decode a well-formed mapping into one source/destination entry*

The `parse_route_map` operation takes a `mappings` array of raw strings. Each string is first trimmed of surrounding whitespace. It must contain exactly one *unescaped* `=` separator: the text before the separator is the source pattern and the text after it is the destination prefix. An equals sign that is meant literally (on either side) is escaped by preceding it with a backslash; the scanner does not treat such an escaped equals as the separator, and every escaped equals is converted back to a plain equals in the final result. Source patterns are compared case-sensitively. The result is printed as a `count=N` line followed by one `source => destination` line per entry, in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_route_map_valid.json`

```json
{
    "description": "Parse a list of raw route-mapping strings into a source-pattern to destination-prefix map. Each string contains exactly one unescaped '=' separator; the part before it is the source pattern and the part after is the destination prefix. A literal equals sign inside either side is escaped by preceding it with a backslash, and each escaped equals is unescaped to a plain equals in the result. The output reports the number of resulting entries followed by one 'source => destination' line per entry in input order.",
    "cases": [
        {
            "input": {"op": "parse_route_map", "mappings": ["/api/{**all}=http://localhost:5000"]},
            "expected_output": "count=1\n/api/{**all} => http://localhost:5000\n"
        },
        {
            "input": {"op": "parse_route_map", "mappings": ["/myPath\\=example=https://example.com"]},
            "expected_output": "count=1\n/myPath=example => https://example.com\n"
        }
    ]
}
```

*2.2 Invalid mapping rejection — report a descriptive error for a malformed mapping*

Using the same `parse_route_map` operation, a mapping string is rejected when, after trimming, it does not contain exactly one unescaped `=` separator that has a non-empty source on the left and a non-empty destination on the right. This includes: a string with no separator at all, a string whose left or right side is empty, a string that is only whitespace, and a string that contains more than one unescaped separator. When any supplied mapping is invalid the operation aborts and reports the failure: the first output line is `error=<ErrorTypeName>` and the second is `message=<the error message>` describing the required format.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_route_map_invalid.json`

```json
{
    "description": "Reject malformed route-mapping strings. Before parsing, each string is trimmed of surrounding whitespace. A string is invalid when, after trimming, it does not contain exactly one unescaped '=' separator with a non-empty source on the left and a non-empty destination on the right: this covers strings with no separator, an empty side, only whitespace, or more than one unescaped separator. Parsing an invalid mapping aborts with an error; the output reports the error type name and its message.",
    "cases": [
        {
            "input": {"op": "parse_route_map", "mappings": [""]},
            "expected_output": "error=ArgumentException\nmessage=The format of the key-value pair is invalid. It must contain exactly one '=' separator. Make sure non-separator '=' characters are escaped ('\\=').\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command from stdin and prints the result to stdout, matching the per-leaf-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same expansion logic as the whitespace handler in section 3.4
- apply the same collapsing strategy used for the whitespace module
