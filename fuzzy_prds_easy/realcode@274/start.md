## Product Requirement Document

# JSON Value Translator - Parse, Serialize, and Inspect JSON-Compatible Data

## Project Goal

Build a JSON value translation library that allows developers to parse JSON text into typed application values, serialize typed values back to JSON text, and inspect conversion results without writing repetitive parsing, escaping, formatting, or object-mapping code.

---

## Background & Problem

Without this library, developers are forced to manually tokenize JSON text, decode string escapes, distinguish numeric and scalar value categories, handle malformed input, and format generated JSON with correct escaping and whitespace. This leads to repetitive code, inconsistent edge-case handling, and fragile data interchange behavior.

With this library, developers can rely on a compact core that converts between JSON wire text and generic typed values, reports normalized parse or serialization failures, supports configurable numeric and whitespace output, and maps reflective objects to generic property values when needed.

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

### Feature 1: Parse Structured JSON Documents

**As a developer**, I want to parse complete JSON objects and arrays into typed, inspectable values, so I can consume structured interchange data without manually walking JSON syntax.

**Expected Behavior / Usage:**

The adapter input is a JSON string containing the document to parse. On success, stdout must contain `ok=true`, the top-level value category, and a deterministic rendered value tree. Objects are rendered as `object{key=value|...}`, arrays as `array[value|...]`, strings as `string:<escaped text>`, booleans as `boolean:true/false`, null as `null`, and numbers with signed or unsigned integer or number categories. Nested arrays and objects must preserve their structure and member names.

**Test Cases:** `rcb_tests/public_test_cases/feature1_parse_structured_json.json`

```json
{
    "description": "Parses complete JSON objects and arrays into typed, inspectable values while preserving nested structure and member names.",
    "cases": [
        {
            "input": "{\"foo\":\"bar\"}",
            "expected_output": "ok=true\ntype=object\nvalue=object{foo=string:bar}\n"
        },
        {
            "input": "{}",
            "expected_output": "ok=true\ntype=object\nvalue=object{}\n"
        }
    ]
}
```

---

### Feature 2: Decode JSON Strings and Escapes

**As a developer**, I want escaped JSON string content decoded into character values, so I can work with URLs, control characters, and Unicode text as normal application strings.

**Expected Behavior / Usage:**

The adapter input is a JSON string containing a JSON value with escaped string content. Escaped slashes must become literal slashes, standard control escapes must become their character values and then be rendered with neutral backslash escapes in stdout, and Unicode escape sequences must become the corresponding Unicode character rendered as `[a character for representing Unicode escapes]XXXX` when outside printable ASCII.

**Test Cases:** `rcb_tests/public_test_cases/feature2_parse_strings_and_escapes.json`

```json
{
    "description": "Parses JSON string escapes, escaped slashes, and Unicode escape sequences into their character values.",
    "cases": [
        {
            "input": "{\"artist\":\"Queensr\[a character for representing Unicode escapes]00ffche\"}",
            "expected_output": "ok=true\ntype=object\nvalue=object{artist=string:Queensr\[a character for representing Unicode escapes]00ffche}\n"
        },
        {
            "input": "[\"http:\\/\\/www.last.fm\\/venue\\/8926427\"]",
            "expected_output": "ok=true\ntype=array\nvalue=array[string:http://www.last.fm/venue/8926427]\n"
        }
    ]
}
```

---

### Feature 3: Parse Scalar and Numeric Values

**As a developer**, I want top-level JSON scalars and numeric forms parsed with their value categories exposed, so I can distinguish strings, booleans, nulls, arrays, objects, integers, and floating-point numbers.

**Expected Behavior / Usage:**

The adapter input is a JSON string containing a scalar, array, or object. Successful output must identify the top-level category and render the parsed value. Unsigned integer inputs remain unsigned when appropriate, negative integers are signed, decimals and exponent forms are numbers, booleans remain booleans, and `null` renders as a null value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_parse_numbers_and_scalars.json`

```json
{
    "description": "Parses top-level JSON scalar values and numeric forms with the resulting value category exposed in output.",
    "cases": [
        {
            "input": "1",
            "expected_output": "ok=true\ntype=unsigned_integer\nvalue=unsigned_integer:1\n"
        },
        {
            "input": "12345678901234567890",
            "expected_output": "ok=true\ntype=unsigned_integer\nvalue=unsigned_integer:12345678901234567890\n"
        },
        {
            "input": "2.004",
            "expected_output": "ok=true\ntype=number\nvalue=number:2.004\n"
        }
    ]
}
```

---

### Feature 4: Reject Invalid JSON

**As a developer**, I want malformed or unsupported JSON input rejected with a neutral error contract, so callers can handle parse failure without depending on runtime-specific diagnostics.

**Expected Behavior / Usage:**

The adapter input is a JSON string containing the candidate JSON text. If the text is incomplete, empty, misspelled, or uses unsupported non-finite numeric tokens in normal parsing mode, stdout must be exactly a failure status and normalized parse-error category: `ok=false` followed by `error=parse_error`. No language-specific exception names, stack traces, or parser internals may appear in stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature4_reject_invalid_json.json`

```json
{
    "description": "Rejects malformed or unsupported JSON input and reports a normalized parse error instead of returning partial data.",
    "cases": [
        {
            "input": "{\"foo\":\"bar\"",
            "expected_output": "ok=false\nerror=parse_error\n"
        },
        {
            "input": "Infinum",
            "expected_output": "ok=false\nerror=parse_error\n"
        }
    ]
}
```

---

### Feature 5: Serialize Common Typed Values

**As a developer**, I want typed in-memory values serialized to JSON text, so I can emit valid JSON for nulls, strings, lists, maps, integers, booleans, and escaped characters.

**Expected Behavior / Usage:**

The adapter input is a typed value descriptor such as `{"kind":"string","value":"..."}`, `{"kind":"list","value":[...]}`, or `{"kind":"map","value":{...}}`. Successful stdout must contain `ok=true` and `json=<serialized text>`. Strings must be quoted and escaped, non-ASCII characters are emitted as `[a character for representing Unicode escapes]XXXX`, control characters are escaped, lists and maps use JSON array and object syntax, and integer and boolean values retain their literal JSON forms.

**Test Cases:** `rcb_tests/public_test_cases/feature5_serialize_values.json`

```json
{
    "description": "Serializes typed in-memory values to JSON text, including nulls, strings, lists, integers, booleans, and escaped characters.",
    "cases": [
        {
            "input": {
                "kind": "null"
            },
            "expected_output": "ok=true\njson=null\n"
        },
        {
            "input": {
                "kind": "map",
                "value": {
                    "value": {
                        "kind": "null"
                    }
                }
            },
            "expected_output": "ok=true\njson={ \"value\" : null }\n"
        },
        {
            "input": {
                "kind": "string",
                "value": ""
            },
            "expected_output": "ok=true\njson=\"\"\n"
        },
        {
            "input": {
                "kind": "string",
                "value": "simpleString"
            },
            "expected_output": "ok=true\njson=\"simpleString\"\n"
        }
    ]
}
```

---

### Feature 6: Serialize Finite Floating-Point Values and Reject Non-Finite Values

**As a developer**, I want floating-point serialization to distinguish valid finite values from unsupported non-finite values, so generated JSON is predictable in normal mode.

**Expected Behavior / Usage:**

The adapter input is a typed numeric descriptor. Finite double and float values must serialize as JSON number text, preserving expected decimal or exponent notation. When special-number output has not been enabled, non-finite values must not produce JSON; stdout must contain `ok=false` and the neutral category `error=non_finite_number`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_serialize_double_handling.json`

```json
{
    "description": "Serializes finite floating-point values, applies requested output precision, and normalizes errors for non-finite values when special-number output is disabled.",
    "cases": [
        {
            "input": {
                "kind": "double",
                "value": "0.0"
            },
            "expected_output": "ok=true\njson=0.0\n"
        },
        {
            "input": {
                "kind": "double",
                "value": "-1.0"
            },
            "expected_output": "ok=true\njson=-1.0\n"
        },
        {
            "input": {
                "kind": "double",
                "value": "1.5e-20"
            },
            "expected_output": "ok=true\njson=1.5e-20\n"
        }
    ]
}
```

---

### Feature 7: Configure Floating-Point Precision

**As a developer**, I want to choose significant precision for floating-point serialization, so output can be rounded consistently for a caller's data interchange requirements.

**Expected Behavior / Usage:**

The adapter input contains a numeric value and a list of requested precision settings. Stdout must contain one line per precision in input order, formatted as `precision=<n> json=<serialized number>`. The same numeric value is serialized independently for each precision, with rounding applied by the selected precision.

**Test Cases:** `rcb_tests/public_test_cases/feature7_serialize_double_precision.json`

```json
{
    "description": "Serializes a floating-point value with caller-selected significant precision settings.",
    "cases": [
        {
            "input": {
                "value": "0.12345678",
                "precisions": [
                    1,
                    2,
                    4,
                    14
                ]
            },
            "expected_output": "precision=1 json=0.1\nprecision=2 json=0.12\nprecision=4 json=0.1235\nprecision=14 json=0.12345678\n"
        }
    ]
}
```

---

### Feature 8: Configure JSON Whitespace Layout

**As a developer**, I want the same data serialized with selectable whitespace layouts, so I can choose compact wire output or more readable formatted output without changing values.

**Expected Behavior / Usage:**

The adapter input is a JSON string containing a structured value. The system parses the value once and serializes it in four modes: compact, minimum, medium, and full. Stdout must contain a `mode=<name>` header, the exact JSON text for that mode, and `--end--` after each mode. Whitespace and line breaks must match the requested layout while preserving all object members, array elements, strings, and numbers.

**Test Cases:** `rcb_tests/public_test_cases/feature8_serialize_indentation_modes.json`

```json
{
    "description": "Serializes the same structured value using compact, minimum, medium, and full whitespace layouts without changing the data.",
    "cases": [
        {
            "input": " { \"foo\" : 0, \"foo1\" : 1, \"foo2\" : [ { \"bar\" : 1, \"foo\" : 0, \"foobar\" : 0 }, { \"bar\" : 1, \"foo\" : 1, \"foobar\" : 1 } ], \"foo3\" : [ 1, 2, 3, 4, 5, 6 ], \"foobaz\" : [ \"one\", \"two\", \"three\", \"four\" ] }",
            "expected_output": "mode=compact\n{\"foo\":0,\"foo1\":1,\"foo2\":[{\"bar\":1,\"foo\":0,\"foobar\":0},{\"bar\":1,\"foo\":1,\"foobar\":1}],\"foo3\":[1,2,3,4,5,6],\"foobaz\":[\"one\",\"two\",\"three\",\"four\"]}\n--end--\nmode=minimum\n{ \"foo\" : 0, \"foo1\" : 1, \"foo2\" : [\n  { \"bar\" : 1, \"foo\" : 0, \"foobar\" : 0 },\n  { \"bar\" : 1, \"foo\" : 1, \"foobar\" : 1 }\n ], \"foo3\" : [\n  1,\n  2,\n  3,\n  4,\n  5,\n  6\n ], \"foobaz\" : [\n  \"one\",\n  \"two\",\n  \"three\",\n  \"four\"\n ] }\n--end--\nmode=medium\n{\n \"foo\" : 0, \"foo1\" : 1, \"foo2\" : [\n  {\n   \"bar\" : 1, \"foo\" : 0, \"foobar\" : 0\n  },\n  {\n   \"bar\" : 1, \"foo\" : 1, \"foobar\" : 1\n  }\n ], \"foo3\" : [\n  1,\n  2,\n  3,\n  4,\n  5,\n  6\n ], \"foobaz\" : [\n  \"one\",\n  \"two\",\n  \"three\",\n  \"four\"\n ]\n}\n--end--\nmode=full\n{\n \"foo\" : 0,\n \"foo1\" : 1,\n \"foo2\" : [\n  {\n   \"bar\" : 1,\n   \"foo\" : 0,\n   \"foobar\" : 0\n  },\n  {\n   \"bar\" : 1,\n   \"foo\" : 1,\n   \"foobar\" : 1\n  }\n ],\n \"foo3\" : [\n  1,\n  2,\n  3,\n  4,\n  5,\n  6\n ],\n \"foobaz\" : [\n  \"one\",\n  \"two\",\n  \"three\",\n  \"four\"\n ]\n}\n--end--\n"
        }
    ]
}
```

---

### Feature 9: Serialize Explicitly Allowed Special Numbers

**As a developer**, I want non-finite numeric values serialized only when explicitly allowed, so applications that opt into these tokens can exchange them intentionally.

**Expected Behavior / Usage:**

The adapter input is a typed special-number descriptor. In the opt-in special-number serialization path, positive infinity, negative infinity, and not-a-number values must serialize as the exact tokens `Infinity`, `-Infinity`, and `NaN`. Stdout must contain `ok=true` and the emitted token as the JSON payload.

**Test Cases:** `rcb_tests/public_test_cases/feature9_serialize_special_numbers.json`

```json
{
    "description": "When explicitly allowed, serializes non-finite numeric values using JSON-compatible special-number tokens.",
    "cases": [
        {
            "input": {
                "kind": "special",
                "value": "Infinity"
            },
            "expected_output": "ok=true\njson=Infinity\n"
        },
        {
            "input": {
                "kind": "special",
                "value": "-Infinity"
            },
            "expected_output": "ok=true\njson=-Infinity\n"
        },
        {
            "input": {
                "kind": "special",
                "value": "NaN"
            },
            "expected_output": "ok=true\njson=NaN\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_parse_structured_json.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_parse_structured_json@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- handles the four modes specified in the serialization flags
