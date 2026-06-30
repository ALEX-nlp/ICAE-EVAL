## Product Requirement Document

# Fluent Guard-Clause Validation Library - Input Validation with Expressive Failures

## Project Goal

Build a guard-clause validation library that lets developers reject invalid arguments at the top of a method with a single fluent expression, so they can enforce pre-conditions without hand-writing repetitive `if (...) throw new ...` blocks. Each guard either lets the value pass through unchanged (so it can be assigned or chained) or throws a precise, well-described exception that names the offending parameter.

---

## Background & Problem

Without such a library, developers write the same defensive boilerplate everywhere: check for null, check a string is non-empty, check a number is in range, check a collection is not empty — each as a manual `if` followed by a hand-typed exception and message. This is verbose, easy to get subtly wrong (wrong exception type, missing parameter name, inconsistent messages), and clutters the real logic.

With this library, a single readable chain expresses the intent ("reject this if it is empty / too long / out of range / not a defined enum member / …") and produces a standard, consistently-worded exception while returning the validated value for continued use.

---

## Program Interface (stdin / stdout contract)

The program under test reads exactly **one JSON object** from stdin describing a single guard invocation, performs it against the real library, and writes the result to stdout.

**Input object fields:**

- `op` (string, required) — selects which guard to run (the vocabulary is defined per feature below).
- `param` (string, optional, default `"value"`) — the parameter name reported in failures.
- `value` — the data to validate; its JSON shape depends on the guard (string, integer, boolean, array, or an encoded timestamp / URI as described in the relevant feature).
- Additional operation-specific fields (e.g. a threshold, a target string, a comparison-mode name) described per feature.

**Output on pass-through (guard does not reject):** exactly two lines

```
[a specific list of enum keys — ask the system for the exact status codes]
[a specific list of enum keys — ask the system for the exact status codes]<rendered value>
```

where `<rendered value>` is the validated value rendered deterministically:
- text → the text verbatim;
- integer → its decimal digits;
- boolean → `[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]` or `[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]`;
- a collection → `[e1, e2, ...]` (elements separated by a comma and a space; a null element renders as `[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]`);
- a timestamp → `DateTime(Kind=Utc)`, `DateTime(Kind=Local)`, or `DateTime(Kind=Unspecified)`;
- an enumeration member → its member name;
- a URI → its absolute form for absolute URIs (scheme, host, normalized path — note an authority-only URL gains a trailing `/`), or the original string for relative URIs;
- a null reference → `[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]`.

**Output on rejection (guard rejects the value):** three-plus lines

```
[a specific list of enum keys — ask the system for the exact status codes]
error=<error category>
param=<parameter name, or empty when none applies>
message=<domain message describing why the value was rejected>
```

`error` is a neutral category naming the kind of failure: `argument_null` (a required reference was null), `argument_out_of_range` (a value fell outside an allowed range), `argument` (any other invalid argument), or `generic` (a fully custom failure). `message=` carries only the human-readable domain text explaining the rejection; it does not repeat the parameter name. Range rejections add a final line `actual=<value>` echoing the offending value.

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

### Feature 1: Null Rejection

**As a developer**, I want to reject a null reference up front, so I can fail fast with a clear null-argument error instead of a later, harder-to-trace failure.

**Expected Behavior / Usage:**

When `value` is null, the guard rejects it with a null-argument failure whose message is the standard "value cannot be null" text; the parameter name is reported separately in the `param=` field. When `value` is non-null it passes through and is rendered back unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature1_null_rejection.json`

```json
{
    "description": "Reject a null reference: when the supplied value is null the guard raises a null-argument error naming the parameter; a non-null value passes through unchanged.",
    "cases": [
        {"input": {"op": "reject_null", "param": "value", "value": null}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value cannot be null.\n"},
        {"input": {"op": "reject_null", "param": "value", "value": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]hello\n"}
    ]
}
```

---

### Feature 2: String Guards

**As a developer**, I want to validate the content, length, equality, and fragments of a string, so I can reject malformed text inputs with a descriptive message.

**Expected Behavior / Usage:**

*2.1 Blank checks — reject empty or white-space-only text*

Reject a string that is empty, and (separately) reject a string consisting only of white space. Any string with visible content passes through.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_string_blank.json`

```json
{
    "description": "Reject blank text: an empty string or a string made up only of white space is rejected; any string with visible content passes through.",
    "cases": [
        {"input": {"op": "string_reject_empty", "value": ""}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not be empty.\n"},
        {"input": {"op": "string_reject_whitespace", "value": "   "}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not be white space only.\n"}
    ]
}
```

*2.2 Length constraints — reject by character count*

Reject a string longer than a limit, shorter than a limit, with length exactly equal to a number, or with length not equal to a number (the field `limit` or `length` carries the count). Otherwise the string passes through.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_string_length.json`

```json
{
    "description": "Constrain text length: reject strings longer than, shorter than, exactly equal to, or not equal to a given character count; otherwise pass through.",
    "cases": [
        {"input": {"op": "string_reject_longer_than", "value": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values], "limit": 3}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not be longer than 3 characters.\n"},
        {"input": {"op": "string_reject_shorter_than", "value": "hi", "limit": 3}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not be shorter than 3 characters.\n"},
        {"input": {"op": "string_reject_length_equals", "value": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values], "length": 5}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String length should not be equal to 5.\n"},
        {"input": {"op": "string_require_length_equals", "value": "hi", "length": 5}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String length should be equal to 5.\n"}
    ]
}
```

*2.3 Equality — reject or require equality with optional comparison mode*

Reject equality to another string (case-sensitive), reject equality ignoring case, require equality (throwing when not equal), and require equality ignoring case. An optional `comparison` field names the comparison mode and is echoed in the message; when omitted, a default ordinal comparison applies. The compared string is supplied in `other`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_string_equality.json`

```json
{
    "description": "Compare text for equality: reject equality (case sensitive or ignoring case), require equality, and apply an explicit comparison mode whose name appears in the error.",
    "cases": [
        {"input": {"op": "string_reject_equals", "value": "abc", "other": "abc"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not be equal to 'abc'.\n"},
        {"input": {"op": "string_reject_equals_ignore_case", "value": "ABC", "other": "abc"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not be equal to 'abc' (case insensitive).\n"},
        {"input": {"op": "string_require_equals", "value": "abc", "other": "xyz", "comparison": "Ordinal"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should be equal to 'xyz' (comparison type: 'Ordinal').\n"},
        {"input": {"op": "string_require_equals_ignore_case", "value": "abc", "other": "xyz"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should be equal to 'xyz' (comparison type: 'OrdinalIgnoreCase').\n"}
    ]
}
```

*2.4 Fragments — reject or require substring, prefix, or suffix*

Reject or require that the string contains a substring (with optional `comparison` mode echoed in the message), starts with a given `prefix`, or ends with a given `suffix`. The "require" variants throw when the fragment is absent.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_string_substring.json`

```json
{
    "description": "Match text fragments: reject or require a substring (optionally under a named comparison mode), and reject or require a given prefix or suffix.",
    "cases": [
        {"input": {"op": "string_reject_contains", "value": "hello world", "substring": "world"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not contain 'world' (comparison type: 'Ordinal').\n"},
        {"input": {"op": "string_reject_contains", "value": "hello world", "substring": "WORLD", "comparison": "OrdinalIgnoreCase"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not contain 'WORLD' (comparison type: 'OrdinalIgnoreCase').\n"},
        {"input": {"op": "string_require_contains", "value": "hello world", "substring": "xyz"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should contain 'xyz' (comparison type: 'Ordinal').\n"},
        {"input": {"op": "string_reject_starts_with", "value": "hello world", "prefix": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not start with 'hello'.\n"},
        {"input": {"op": "string_require_starts_with", "value": "hello world", "prefix": "bye"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should start with 'bye'.\n"},
        {"input": {"op": "string_reject_ends_with", "value": "filename.txt", "suffix": ".txt"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should not end with '.txt'.\n"},
        {"input": {"op": "string_require_ends_with", "value": "filename.txt", "suffix": ".md"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=String should end with '.md'.\n"}
    ]
}
```

---

### Feature 3: Numeric Guards

**As a developer**, I want to validate that a number satisfies ordering, equality, sign, and range constraints, so I can reject out-of-bounds values with a message that reports the offending value.

**Expected Behavior / Usage:**

*3.1 Ordering — reject greater-than / less-than a threshold*

Reject a value greater than, or less than, the threshold in field `n`. These are range failures: the error category is out-of-range and a final `actual=<value>` line echoes the offending value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_number_ordering.json`

```json
{
    "description": "Order comparisons: reject a value greater than, or less than, a threshold; range errors echo the offending actual value.",
    "cases": [
        {"input": {"op": "number_reject_greater_than", "value": 5, "n": 4}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]_out_of_range\nparam=value\nmessage=Value should not be greater than 4.\nactual=5\n"},
        {"input": {"op": "number_reject_less_than", "value": 3, "n": 4}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]_out_of_range\nparam=value\nmessage=Value should not be less than 4.\nactual=3\n"}
    ]
}
```

*3.2 Equality — reject or require equality with a target*

Reject a value equal to the target in `n`, or require equality (rejecting when not equal). These are plain argument failures (no `actual=` line).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_number_equality.json`

```json
{
    "description": "Numeric equality: reject a value equal to a target, or require a value equal to a target; otherwise pass through.",
    "cases": [
        {"input": {"op": "number_reject_equals", "value": 4, "n": 4}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should not be equal to 4.\n"},
        {"input": {"op": "number_require_equals", "value": 5, "n": 4}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should be equal to 4.\n"}
    ]
}
```

*3.3 Sign — reject positive / reject negative*

Reject a strictly positive value, or reject a strictly negative value. These are range failures phrased relative to zero (greater-than [a predefined set of valid JSON-like outputs — ask the schema author for allowed values] / less-than [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]) and include the `actual=` line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_number_sign.json`

```json
{
    "description": "Sign checks: reject a positive value or reject a negative value; the complementary sign (including zero where applicable) passes through.",
    "cases": [
        {"input": {"op": "number_reject_positive", "value": 5}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]_out_of_range\nparam=value\nmessage=Value should not be greater than [a predefined set of valid JSON-like outputs — ask the schema author for allowed values].\nactual=5\n"},
        {"input": {"op": "number_reject_negative", "value": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]_out_of_range\nparam=value\nmessage=Value should not be less than [a predefined set of valid JSON-like outputs — ask the schema author for allowed values].\nactual=[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]\n"}
    ]
}
```

*3.4 Range — reject outside an inclusive interval*

Reject a value outside the inclusive interval `[min, max]`. This is a range failure with the `actual=` line; the message states the interval bounds.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_number_range.json`

```json
{
    "description": "Inclusive range: reject a value outside an inclusive [min, max] interval; the range error echoes the actual value.",
    "cases": [
        {"input": {"op": "number_reject_out_of_range", "value": 5, "min": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values], "max": 4}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]_out_of_range\nparam=value\nmessage=Value should be between [a predefined set of valid JSON-like outputs — ask the schema author for allowed values] and 4.\nactual=5\n"}
    ]
}
```

---

### Feature 4: Boolean Guards

**As a developer**, I want to reject a boolean that is true (or that is false), so I can assert a flag's required state in one line.

**Expected Behavior / Usage:**

Reject a `true` value, or reject a `false` value. The message for rejecting true is "should not be true"; the message for rejecting false states the value "should be true". The opposite boolean passes through.

**Test Cases:** `rcb_tests/public_test_cases/feature4_boolean.json`

```json
{
    "description": "Boolean checks: reject a true value, or reject a false value; the opposite boolean passes through.",
    "cases": [
        {"input": {"op": "bool_reject_true", "value": true}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should not be true.\n"},
        {"input": {"op": "bool_reject_false", "value": false}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should be true.\n"}
    ]
}
```

---

### Feature 5: Custom Condition Guards

**As a developer**, I want to reject a value based on an arbitrary boolean condition I evaluate myself, so I can express domain-specific rules while still getting a consistent, labeled error.

**Expected Behavior / Usage:**

The caller supplies a pre-evaluated boolean in `condition` plus a human-readable `condition_label`. The guard rejects when the condition is true (or, in the complementary guard, when it is false) and embeds the label in the message: "should not meet condition (condition: '<label>')" or "should meet condition (condition: '<label>')". The `value` is an opaque carrier returned unchanged when the condition does not trigger rejection.

**Test Cases:** `rcb_tests/public_test_cases/feature5_condition.json`

```json
{
    "description": "Custom condition: evaluate a caller-supplied boolean and reject when it is true (or, in the complementary guard, when it is false); the error embeds a human-readable label for the condition.",
    "cases": [
        {"input": {"op": "condition_reject_true", "value": "payload", "condition": true, "condition_label": "count > [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should not meet condition (condition: 'count > [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]').\n"},
        {"input": {"op": "condition_reject_false", "value": "payload", "condition": false, "condition_label": "count > [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should meet condition (condition: 'count > [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]').\n"}
    ]
}
```

---

### Feature 6: Collection Guards

**As a developer**, I want to validate the emptiness, size, and contents of a collection, so I can reject malformed collections with a clear message.

**Expected Behavior / Usage:**

*6.1 Emptiness — reject empty / reject non-empty*

Reject an empty collection, or reject a non-empty collection. The complementary shape passes through and the collection is rendered back. The `value` is a JSON array.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_collection_emptiness.json`

```json
{
    "description": "Collection emptiness: reject an empty collection, or reject a non-empty collection; the complementary shape passes through and the collection is returned unchanged.",
    "cases": [
        {"input": {"op": "collection_reject_empty", "value": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Collection should not be empty.\n"},
        {"input": {"op": "collection_require_empty", "value": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Collection should be empty.\n"}
    ]
}
```

*6.2 Size — reject by element count*

Reject a collection whose element count equals, does not equal, is greater than, or is less than the number in `count`. Otherwise the collection passes through.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_collection_count.json`

```json
{
    "description": "Collection size: reject a collection whose element count equals, does not equal, is greater than, or is less than a given number; otherwise pass through.",
    "cases": [
        {"input": {"op": "collection_reject_count_equals", "value": [1, 2, 3], "count": 3}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Collection count should not be equal to 3.\n"},
        {"input": {"op": "collection_require_count_equals", "value": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values], "count": 3}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Collection count should be equal to 3.\n"},
        {"input": {"op": "collection_reject_count_greater_than", "value": [1, 2, 3], "count": 2}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Collection count should not be greater than 2.\n"},
        {"input": {"op": "collection_reject_count_less_than", "value": [1], "count": 2}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Collection count should not be less than 2.\n"}
    ]
}
```

*6.3 Null elements — reject any null member*

Reject a collection that contains at least one null element; a collection free of nulls passes through.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_collection_null_elements.json`

```json
{
    "description": "Null elements: reject a collection that contains any null element; a collection free of nulls passes through.",
    "cases": [
        {"input": {"op": "collection_reject_null_elements", "value": [1, null, 3]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Collection should not have null elements.\n"}
    ]
}
```

---

### Feature 7: Timestamp Kind Guards

**As a developer**, I want to validate the "kind" of a timestamp (whether it is UTC, local, or unspecified), so I can reject timestamps that are not in the expected time basis.

**Expected Behavior / Usage:**

The `value` field encodes a timestamp by its kind: the string `"utc"`, `"local"`, or `"unspecified"` denotes a fixed timestamp tagged with that kind. On pass-through the timestamp renders as `DateTime(Kind=<kind>)`.

*7.1 UTC — reject UTC / require UTC*

Reject a timestamp whose kind is UTC, or require a UTC timestamp (rejecting any non-UTC kind, with message "should be Utc").

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_datetime_utc.json`

```json
{
    "description": "UTC kind: reject a timestamp whose kind is UTC, or require a timestamp whose kind is UTC (rejecting non-UTC); the value is returned unchanged when it passes.",
    "cases": [
        {"input": {"op": "datetime_reject_utc", "value": "utc"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should not be Utc.\n"},
        {"input": {"op": "datetime_require_utc", "value": "local"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should be Utc.\n"}
    ]
}
```

*7.2 Specific kind — reject matching / require a named kind*

Reject a timestamp whose kind matches the `kind` field, or require a timestamp of the named kind (rejecting any other). The kind name (`Utc`, `Local`, or `Unspecified`) appears in the message.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_datetime_kind.json`

```json
{
    "description": "Specific kind: reject a timestamp matching a named kind, or require a timestamp of a named kind (rejecting any other); the kind name appears in the error.",
    "cases": [
        {"input": {"op": "datetime_reject_kind", "value": "local", "kind": "Local"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should not be Local.\n"},
        {"input": {"op": "datetime_require_kind", "value": "local", "kind": "Utc"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should be Utc.\n"}
    ]
}
```

---

### Feature 8: Default-Value Guards

**As a developer**, I want to reject a value that equals its type's default (or require it to be the default), so I can catch uninitialized values.

**Expected Behavior / Usage:**

For an integer, the default is `[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]`. Reject a value equal to the default ("should not be default"), or require it to be the default, rejecting any non-default value ("should be default"). Otherwise the value passes through.

**Test Cases:** `rcb_tests/public_test_cases/feature8_default.json`

```json
{
    "description": "Default value: reject a value equal to its type's default, or require it to be the default (rejecting non-default); otherwise pass through.",
    "cases": [
        {"input": {"op": "value_reject_default", "value": [a predefined set of valid JSON-like outputs — ask the schema author for allowed values]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should not be default.\n"},
        {"input": {"op": "value_require_default", "value": 5}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Value should be default.\n"}
    ]
}
```

---

### Feature 9: Enumeration Membership Guard

**As a developer**, I want to reject an enumeration value that is not a defined member, so I can guard against invalid casts from raw integers.

**Expected Behavior / Usage:**

The guard operates on an enumeration with two defined members: one named `First` (numeric value `[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]`) and one named `Second` (numeric value `1`). The `value` field is the raw integer cast into this enumeration. If the integer is not a defined member, the guard reports an out-of-range failure ("should be defined in enum") with the `actual=` line echoing the integer. A defined member passes through and renders as its member name.

**Test Cases:** `rcb_tests/public_test_cases/feature9_enum.json`

```json
{
    "description": "Enum membership: reject an enumeration value that is not a defined member; the range error echoes the offending numeric value. A defined member passes through and its name is returned.",
    "cases": [
        {"input": {"op": "enum_reject_undefined", "value": 5}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]_out_of_range\nparam=value\nmessage=Value should be defined in enum.\nactual=5\n"}
    ]
}
```

---

### Feature 1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]: URI Guards

**As a developer**, I want to validate a URI's scheme, kind (absolute vs relative), and port, so I can reject URLs that do not meet my requirements.

**Expected Behavior / Usage:**

The `value` field is a URL string. By default it is parsed as an absolute URI; when the field `relative` is `true`, it is parsed as a relative URI.

*1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values].1 HTTP/HTTPS scheme — reject or require http / https*

Reject (or require) the `http` scheme, and reject (or require) the `https` scheme. The "require" variants throw when the scheme differs, with message "scheme should be http/https".

**Test Cases:** `rcb_tests/public_test_cases/feature1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]_1_uri_http_scheme.json`

```json
{
    "description": "HTTP/HTTPS scheme: reject (or require) the http scheme, and reject (or require) the https scheme; the absolute URI is returned unchanged when it passes.",
    "cases": [
        {"input": {"op": "uri_reject_http", "value": "http://example.com"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri scheme should not be http.\n"},
        {"input": {"op": "uri_require_http", "value": "https://example.com"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri scheme should be http.\n"},
        {"input": {"op": "uri_reject_https", "value": "https://example.com"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri scheme should not be https.\n"},
        {"input": {"op": "uri_require_https", "value": "http://example.com"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri scheme should be https.\n"}
    ]
}
```

*1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values].2 Named scheme — reject or require an arbitrary scheme*

Reject a URI whose scheme equals the `scheme` field, or require that exact scheme (rejecting any other). The scheme name appears in the message.

**Test Cases:** `rcb_tests/public_test_cases/feature1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]_2_uri_scheme.json`

```json
{
    "description": "Named scheme: reject a URI whose scheme equals a given scheme name, or require that exact scheme (rejecting any other); the scheme name appears in the error.",
    "cases": [
        {"input": {"op": "uri_reject_scheme", "value": "ftp://example.com", "scheme": "ftp"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri scheme should not be ftp.\n"},
        {"input": {"op": "uri_require_scheme", "value": "http://example.com", "scheme": "https"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri scheme should be https.\n"}
    ]
}
```

*1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values].3 Kind — reject or require absolute / relative*

Reject an absolute URI ("should be relative"), require an absolute URI by rejecting relative ones ("should be absolute"), reject a relative URI ("should be absolute"), and require a relative URI by rejecting absolute ones ("should be relative").

**Test Cases:** `rcb_tests/public_test_cases/feature1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]_3_uri_kind.json`

```json
{
    "description": "Absolute vs relative: reject an absolute URI, require an absolute URI (rejecting relative), reject a relative URI, and require a relative URI (rejecting absolute).",
    "cases": [
        {"input": {"op": "uri_reject_absolute", "value": "https://example.com"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri should be relative.\n"},
        {"input": {"op": "uri_require_absolute", "value": "/path/resource", "relative": true}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri should be absolute.\n"},
        {"input": {"op": "uri_reject_relative", "value": "/path/resource", "relative": true}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri should be absolute.\n"},
        {"input": {"op": "uri_require_relative", "value": "https://example.com"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri should be relative.\n"}
    ]
}
```

*1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values].4 Port — reject or require a port number*

Reject a URI served on the port in `port`, or require that exact port (rejecting any other). The port number appears in the message.

**Test Cases:** `rcb_tests/public_test_cases/feature1[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]_4_uri_port.json`

```json
{
    "description": "URI port: reject a URI served on a given port number, or require that exact port (rejecting any other); the port number appears in the error.",
    "cases": [
        {"input": {"op": "uri_reject_port", "value": "http://example.com:8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]", "port": 8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri port should not be 8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values].\n"},
        {"input": {"op": "uri_require_port", "value": "http://example.com:8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]", "port": 8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=value\nmessage=Uri port should be 8[a predefined set of valid JSON-like outputs — ask the schema author for allowed values].\n"}
    ]
}
```

---

### Feature 11: Exception Customization

**As a developer**, I want control over the exception that a failed guard produces, so I can either rely on standard messages or substitute my own message or exception type.

**Expected Behavior / Usage:**

Three low-level error signals back every guard: a null-argument signal, a general argument signal, and an out-of-range signal. Each is invoked with a parameter name in `param`.

*11.1 Default messages — the three signals without customization*

Without customization: the null-argument signal produces the standard "value cannot be null" message; the general argument signal produces the standard "value does not fall within the expected range" message; the out-of-range signal produces the standard "out of the range of valid values" message followed by an `actual=<actual_value>` line (the actual value is supplied in `actual_value`). Each reports the parameter name in the `param=` field.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_default_messages.json`

```json
{
    "description": "Default error messages: the three low-level error signals (null-argument, argument, and out-of-range) produce their standard messages, with the parameter name reported in its own field and, for out-of-range, the offending value reported on its own line.",
    "cases": [
        {"input": {"op": "signal_null_error", "param": "paramName"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=paramName\nmessage=Value cannot be null.\n"},
        {"input": {"op": "signal_argument_error", "param": "paramName"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=paramName\nmessage=Value does not fall within the expected range.\n"},
        {"input": {"op": "signal_range_error", "param": "paramName", "actual_value": "[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]"}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]_out_of_range\nparam=paramName\nmessage=Specified argument was out of the range of valid values.\nactual=[a predefined set of valid JSON-like outputs — ask the schema author for allowed values]\n"}
    ]
}
```

*11.2 Customized exceptions — override the message or the exception itself*

A signal may carry a `customize` object. With `mode` = `"message"`, the supplied `text` replaces the default message (the parameter name is still reported in `param=`). With `mode` = `"thrower"`, a caller-supplied factory builds an entirely different failure carrying the `text` verbatim as its message, reported under the `generic` category with an empty `param=`. With `mode` = `"thrower_param"`, the factory receives the parameter name and builds a failure whose message is `param: <name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_custom_exceptions.json`

```json
{
    "description": "Customized errors: an error signal may carry a custom message that replaces the default text, or a caller-supplied factory that produces an entirely different exception type (optionally receiving the parameter name).",
    "cases": [
        {"input": {"op": "signal_argument_error", "param": "paramName", "customize": {"mode": "message", "text": "custom message"}}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=paramName\nmessage=custom message\n"},
        {"input": {"op": "signal_argument_error", "param": "paramName", "customize": {"mode": "thrower", "text": "totally custom"}}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=\nmessage=totally custom\n"},
        {"input": {"op": "signal_argument_error", "param": "paramName", "customize": {"mode": "thrower_param"}}, "expected_output": "[a specific list of enum keys — ask the system for the exact status codes]\n[a specific list of enum keys — ask the system for the exact status codes]\nparam=\nmessage=param: paramName\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a JSON command from stdin and prints the result to stdout, matching the per-leaf-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_null_rejection.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_null_rejection@[a predefined set of valid JSON-like outputs — ask the schema author for allowed values][a predefined set of valid JSON-like outputs — ask the schema author for allowed values][a predefined set of valid JSON-like outputs — ask the schema author for allowed values].txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same rule structure as the absolute-vs-relative resolution logic
- yield the `${max_length}` constraint message
