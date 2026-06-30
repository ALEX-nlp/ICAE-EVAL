## Product Requirement Document

# Data Parsing and Utility Contracts - Deterministic Text Interfaces

## Project Goal

Build a compact utility library that allows developers to parse structured text, compose computation results, manipulate positional records, control deterministic time, validate primitive values, and render sensitive values without repeatedly writing fragile boilerplate for each project.

---

## Background & Problem

Without this library/tool, developers are forced to hand-code small parsers, ad hoc result aggregation, tuple conversion, fake clocks, validation predicates, and value masking in every codebase. This leads to repetitive code, inconsistent edge-case behavior, and tests that are hard to make deterministic.

With this library/tool, these behaviors are exposed as reusable contracts with deterministic input/output behavior that can be verified through a single execution adapter.

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

### Feature 1: CSV Record Parsing

**As a developer**, I want to parse CSV text into records, so I can consume delimited data without hand-written field splitting.

**Expected Behavior / Usage:**

The input is one complete CSV text string. The output reports `header=none` or a header list, then `records=` followed by the parsed rows. Quoted fields preserve embedded commas and escaped quote sequences as field content. If parsing stops before the whole input is consumed, stdout reports `error=unconsumed_input` and a normalized diagnostic message.

**Test Cases:** `rcb_tests/public_test_cases/feature1_csv_records.json`

```json
{
    "description": "Parse CSV text into an optional header and ordered records while preserving quoted field content.",
    "cases": [
        {
            "input": "field0,field1",
            "expected_output": "header=none\nrecords=[[\"field0\", \"field1\"]]\n"
        },
        {
            "input": "\"fie,ld\"",
            "expected_output": "header=none\nrecords=[[\"fie,ld\"]]\n"
        }
    ]
}
```

---

### Feature 2: JSON Value Parsing

**As a developer**, I want to parse JSON values, so I can convert wire-format JSON text into normalized values.

**Expected Behavior / Usage:**

The input is one complete JSON value. The output is a normalized textual representation of the parsed value followed by a newline. Null, booleans, numbers, strings, arrays, and objects are supported; object keys are rendered deterministically. Escapes in strings are decoded before output rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature2_json_values.json`

```json
{
    "description": "Parse a complete JSON value and render its normalized value form.",
    "cases": [
        {
            "input": "null",
            "expected_output": "null\n"
        },
        {
            "input": "[1, 2, 3]",
            "expected_output": "[1, 2, 3]\n"
        }
    ]
}
```

---

### Feature 3: Arithmetic Expression Evaluation

**As a developer**, I want to evaluate arithmetic expressions, so I can calculate numeric results from expression text.

**Expected Behavior / Usage:**

The input is one arithmetic expression string. The output is `[the evaluated arithmetic result]` for a successful evaluation. Whitespace may separate tokens. Parentheses override precedence; exponentiation binds tighter than multiplication and division, which bind tighter than addition and subtraction. Invalid input that cannot start a valid expression is reported as `error=no_parse` with the original input.

**Test Cases:** `rcb_tests/public_test_cases/feature3_arithmetic_expressions.json`

```json
{
    "description": "Evaluate arithmetic expressions with parentheses, whitespace, exponentiation, multiplication, division, addition, and subtraction precedence.",
    "cases": [
        {
            "input": "1 + 2 * 3",
            "expected_output": "value=7\n"
        },
        {
            "input": "(1 + 2) * 3 - 4 / 5",
            "expected_output": "value=8.2\n"
        }
    ]
}
```

---

### Feature 4.1: Require All Results to Succeed

**As a developer**, I want to collect values from result sequences, so I can fail fast when any step fails.

**Expected Behavior / Usage:**

The input is a comma-separated sequence of `success:<integer>` and `failure:<reason>` items. The output is `status=success` with the ordered values if every item succeeds, or `status=failure` with the first failure reason encountered.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_all_results.json`

```json
{
    "description": "Collect success values from an ordered result sequence only when every item succeeds; otherwise return the first failure reason.",
    "cases": [
        {
            "input": "success:1,success:2,success:3",
            "expected_output": "status=success\nvalues=[1, 2, 3]\n"
        }
    ]
}
```

---

### Feature 4.2: Keep Only Successful Results

**As a developer**, I want to extract successful values from result sequences, so I can ignore failed items when partial success is acceptable.

**Expected Behavior / Usage:**

The input is a comma-separated sequence of success and failure items. The output is `values=` containing the ordered integer values from successful items only; failure reasons are omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_any_successes.json`

```json
{
    "description": "Extract all success values from an ordered result sequence and drop failures.",
    "cases": [
        {
            "input": "success:1,failure:bad,success:3",
            "expected_output": "values=[1, 3]\n"
        }
    ]
}
```

---

### Feature 4.3: Partition Results

**As a developer**, I want to separate successes from failures, so I can inspect both outcomes independently.

**Expected Behavior / Usage:**

The input is a comma-separated sequence of success and failure items. The output has `successes=` with all successful integer values in encounter order and `failures=` with all failure reasons in encounter order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_result_partition.json`

```json
{
    "description": "Separate an ordered result sequence into success values and failure reasons while preserving each group order.",
    "cases": [
        {
            "input": "success:1,failure:bad,success:3,failure:also bad",
            "expected_output": "successes=[1, 3]\nfailures=[bad, also bad]\n"
        }
    ]
}
```

---

### Feature 5.1: Tuple Append

**As a developer**, I want to append fixed-size tuples, so I can combine ordered heterogeneous groups without losing position order.

**Expected Behavior / Usage:**

The input is two comma-separated integer groups separated by `|`: the left group has five positions and the right group has three positions. The output reports the combined ordered values and the resulting size.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_tuple_append.json`

```json
{
    "description": "Append a five-item tuple and a three-item tuple into one ordered eight-item tuple.",
    "cases": [
        {
            "input": "1,2,3,4,5|6,7,8",
            "expected_output": "values=[1, 2, 3, 4, 5, 6, 7, 8]\nsize=8\n"
        }
    ]
}
```

---

### Feature 5.2: List-to-Tuple Conversion

**As a developer**, I want to convert lists into fixed-position tuples, so I can work with positional records of known sizes.

**Expected Behavior / Usage:**

The input is a comma-separated integer list. The output shows selected fixed-size tuple projections. Available list positions fill the tuple from left to right; missing trailing positions are rendered as `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_tuple_from_list.json`

```json
{
    "description": "Convert an ordered list into fixed-size tuples, preserving available positions and padding missing trailing positions with null.",
    "cases": [
        {
            "input": "1,2,3,4",
            "expected_output": "tuple2=[1, 2]\ntuple5=[1, 2, 3, 4, null]\ntuple6=[1, 2, 3, 4, null, null]\n"
        }
    ]
}
```

---

### Feature 5.3: Nullable Tuple Narrowing

**As a developer**, I want to require all tuple positions to be non-null, so I can safely use a complete positional record.

**Expected Behavior / Usage:**

The input is a comma-separated four-position tuple where each position is either an integer or `null`. The output is `all_non_null=<values>` when every position has a value, otherwise `all_non_null=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_tuple_nullability.json`

```json
{
    "description": "Convert a nullable four-item tuple into a non-null tuple only when all positions have values.",
    "cases": [
        {
            "input": "1,2,3,4",
            "expected_output": "all_non_null=[1, 2, 3, 4]\n"
        }
    ]
}
```

---

### Feature 6.1: Manually Advanced Clock

**As a developer**, I want to control test time manually, so I can make time-dependent behavior deterministic.

**Expected Behavior / Usage:**

The input is a semicolon-separated command string with `start=<instant>`, `defaultTick=<seconds>`, and `[the base tick duration defined by the system team]<operations>`. Operations are `read`, `tick`, or `tick:<seconds>`. Reads do not advance time; ticks advance by the configured or explicit amount. The output lists the instants returned by read operations.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_fixed_time.json`

```json
{
    "description": "Read and manually advance a controllable clock; reading the clock by itself does not advance time.",
    "cases": [
        {
            "input": "start=1970-01-01T00:00:01Z;defaultTick=10;[the base tick duration defined by the system team]read,read,tick:1,read,read",
            "expected_output": "instants=[1970-01-01T00:00:01Z, 1970-01-01T00:00:01Z, 1970-01-01T00:00:02Z, 1970-01-01T00:00:02Z]\n"
        }
    ]
}
```

---

### Feature 6.2: Auto-Advancing Clock

**As a developer**, I want to read a deterministic clock that advances itself, so repeated reads simulate time progression.

**Expected Behavior / Usage:**

The input uses the same command shape as the manually advanced clock. Each read returns the current instant and then advances by the configured tick. Explicit ticks may also be interleaved. The output lists the instants returned by reads.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_auto_ticking_time.json`

```json
{
    "description": "Read and manually advance an auto-advancing clock; each read returns the current time and then advances by the configured tick.",
    "cases": [
        {
            "input": "start=1970-01-01T00:00:01Z;defaultTick=2;[the base tick duration defined by the system team]read,read,read",
            "expected_output": "instants=[1970-01-01T00:00:01Z, 1970-01-01T00:00:03Z, 1970-01-01T00:00:05Z]\n"
        }
    ]
}
```

---

### Feature 7.1: String Validation Rules

**As a developer**, I want to apply reusable string validation rules, so I can enforce length and pattern constraints consistently.

**Expected Behavior / Usage:**

The input is `rule=<name>;value=<text>`. The output reports whether the value satisfies the named rule, echoes the rule name, and reports the input length. Supported tested rules include minimum length, maximum length, exact length, bounded length, non-empty pattern, and composed logical rules.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_string_validation.json`

```json
{
    "description": "Evaluate named string validation rules and report the boolean result together with rule identity and input length.",
    "cases": [
        {
            "input": "rule=min10;value=123456789",
            "expected_output": "valid=false\nrule=min10\nlength=9\n"
        },
        {
            "input": "rule=max10;value=12345678901",
            "expected_output": "valid=false\nrule=max10\nlength=11\n"
        }
    ]
}
```

---

### Feature 7.2: Number Validation Rules

**As a developer**, I want to apply reusable numeric validation rules, so I can enforce numeric bounds consistently.

**Expected Behavior / Usage:**

The input is `rule=<name>;[the evaluated arithmetic result]`. The output reports whether the value satisfies the named rule, echoes the rule name, and reports the numeric input. Supported tested rules include exact value, maximum, minimum, and inclusive range checks.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_number_validation.json`

```json
{
    "description": "Evaluate named numeric validation rules and report the boolean result together with rule identity and numeric input.",
    "cases": [
        {
            "input": "rule=max10;value=10",
            "expected_output": "valid=true\nrule=max10\nvalue=10\n"
        }
    ]
}
```

---

### Feature 7.3: Masked Value Rendering

**As a developer**, I want to render sensitive string-backed values safely, so displayed output can hide or partially reveal content.

**Expected Behavior / Usage:**

The input is `mask=<policy>;value=<text>`. The output reports the displayed string and its displayed length. Tested policies include no masking, complete replacement with a fixed character, and revealing configured prefix/suffix regions while masking the middle.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_masked_values.json`

```json
{
    "description": "Render string-backed values using the selected masking policy and report the displayed string length.",
    "cases": [
        {
            "input": "mask=none;value=hellohello",
            "expected_output": "display=hellohello\nlength=10\n"
        },
        {
            "input": "mask=hidden;value=hellohello",
            "expected_output": "display=tttttttttt\nlength=10\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_csv_records.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_csv_records@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Wait, the format string needs adjustment if the environment variable 'CASE_MODE' is set to 'verbose'
- Run the result in invert mode
