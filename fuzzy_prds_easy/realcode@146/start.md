## Product Requirement Document

# Value Validation Engine - A Declarative Input Assertion Library

## Project Goal

Build a value-validation engine that lets developers declaratively assert facts about untrusted input — its type, range, length, format, and structure — and obtain a uniform, machine-readable outcome for each assertion, without hand-writing repetitive conditional checks and ad-hoc error reporting throughout an application.

---

## Background & Problem

Without a validation engine, developers scatter manual `if` checks throughout their code to confirm that a value is an integer, falls within a range, matches a pattern, or is one of a set of allowed choices. This leads to repetitive, error-prone boilerplate, inconsistent error messages, and validation rules that drift apart over time.

With this engine, a developer states the expectation once as a named rule, and the engine reports either success or a structured violation carrying a stable numeric code and a human-readable message. Rules can also be composed: tolerated when the value is null, applied across every element of a collection, sequenced into an ordered chain, or batched so that all field-level failures are reported together.

---

## Input / Output Contract

The execution adapter reads ONE JSON request object from stdin and writes the normalized outcome to stdout. The request always carries a `mode` (default `check`).

- **`check`** mode names a single rule via `check`, supplies the subject in `value`, and any rule parameters in `args` (an array). Optional flags `null_or` and `all` wrap the rule (see Feature 9).
- **`chain`** mode supplies a `value` and an ordered list of `steps`, each `{check, args}`, applied left to right until one fails.
- **`lazy`** mode supplies a list of `assertions`, each `{value, property_path, steps}`; every assertion is evaluated and all failures are aggregated.

Output is a language-neutral, line-oriented contract:

- A satisfied rule prints `valid\n`.
- A violated rule prints three lines: `invalid`, then `code=<integer>` (a stable violation code), then `message=<text>` (a human-readable explanation that quotes the offending value).
- Referencing a rule that does not exist inside a chain prints `error=unknown_assertion` followed by a `message=` line.
- An aggregated (lazy) run that has failures prints a report beginning with `The following <n> assertions failed:` and one numbered `<i>) <property_path>: <message>` line per failure; a fully satisfied lazy run prints `valid\n`.

The stable violation codes referenced by the embedded cases are intrinsic to this contract and must be reproduced exactly.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-rule domain with distinct responsibilities (request parsing, rule resolution, rule evaluation, outcome rendering). It MUST NOT be a single "god file"; output a clear directory tree separating the core rule engine from the I/O adapter.
2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON cases below are a black-box contract for the execution adapter, NOT the internal data model. The core engine must be decoupled from stdin/stdout and JSON parsing; the adapter alone translates JSON requests into idiomatic calls into the core and renders the outcome.
3. **Adherence to SOLID Design Principles:** Separate parsing, routing, rule evaluation, and output formatting into distinct units; keep the engine open for new rules without modification of existing ones.
4. **Robustness & Interface Design:** The core interface must be idiomatic and elegant. Violations must be modeled as a proper error/exception type that carries a code and message; the adapter is responsible for normalizing any thrown failure into the neutral stdout contract above — never by leaking host-language runtime identities into stdout.

---

## Core Features

### Feature 1: Primitive Type Rules

**As a developer**, I want to assert that a value has a specific primitive type, so I can reject malformed input before it reaches business logic.

**Expected Behavior / Usage:**

*1.1 Float*

Accepts values that are real floating-point numbers and rejects every other type, including integers and numeric strings.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_float.json`

```json
{
    "description": "Accepts values that are real floating-point numbers and rejects every other type, including integers and numeric strings.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "float",
                "value": 0.1
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "float",
                "value": 1
            },
            "expected_output": "invalid\ncode=9\nmessage=Value \"1\" is not a float.\n"
        }
    ]
}
```

*1.2 Integer*

Accepts native integer values and rejects floats, numeric strings, booleans and null.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_integer.json`

```json
{
    "description": "Accepts native integer values and rejects floats, numeric strings, booleans and null.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "integer",
                "value": 5
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "integer",
                "value": "5"
            },
            "expected_output": "invalid\ncode=10\nmessage=Value \"5\" is not an integer.\n"
        }
    ]
}
```

*1.3 Integer-like*

Accepts integers and strings that represent an integer without loss, and rejects fractional values, non-numeric strings, booleans and null.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_integerish.json`

```json
{
    "description": "Accepts integers and strings that represent an integer without loss, and rejects fractional values, non-numeric strings, booleans and null.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "integerish",
                "value": "10"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "integerish",
                "value": 5.5
            },
            "expected_output": "invalid\ncode=12\nmessage=Value \"5.5\" is not an integer or a number castable to integer.\n"
        }
    ]
}
```

*1.4 Boolean*

Accepts only genuine boolean values and rejects integers, strings and null.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_boolean.json`

```json
{
    "description": "Accepts only genuine boolean values and rejects integers, strings and null.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "boolean",
                "value": true
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "boolean",
                "value": 1
            },
            "expected_output": "invalid\ncode=13\nmessage=Value \"1\" is not a boolean.\n"
        }
    ]
}
```

*1.5 Scalar*

Accepts scalar values (string, number, boolean) and rejects compound values such as arrays.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_scalar.json`

```json
{
    "description": "Accepts scalar values (string, number, boolean) and rejects compound values such as arrays.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "scalar",
                "value": "x"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "scalar",
                "value": []
            },
            "expected_output": "invalid\ncode=209\nmessage=Value \"<ARRAY>\" is not a scalar.\n"
        }
    ]
}
```

*1.6 String*

Accepts string values (including the empty string) and rejects numbers, booleans, arrays and null. The error message reports the actual type that was supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_string.json`

```json
{
    "description": "Accepts string values (including the empty string) and rejects numbers, booleans, arrays and null. The error message reports the actual type that was supplied.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "string",
                "value": "hello"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "string",
                "value": 5
            },
            "expected_output": "invalid\ncode=16\nmessage=Value \"5\" expected to be string, type integer given.\n"
        }
    ]
}
```

*1.7 Numeric*

Accepts numbers and numeric strings and rejects non-numeric strings and null.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_numeric.json`

```json
{
    "description": "Accepts numbers and numeric strings and rejects non-numeric strings and null.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "numeric",
                "value": "123"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "numeric",
                "value": "abc"
            },
            "expected_output": "invalid\ncode=23\nmessage=Value \"abc\" is not numeric.\n"
        }
    ]
}
```

*1.8 Digit*

Accepts values whose textual form consists only of decimal digits and rejects values containing signs, separators or letters.

**Test Cases:** `rcb_tests/public_test_cases/feature1_8_digit.json`

```json
{
    "description": "Accepts values whose textual form consists only of decimal digits and rejects values containing signs, separators or letters.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "digit",
                "value": "123"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "digit",
                "value": "12.3"
            },
            "expected_output": "invalid\ncode=11\nmessage=Value \"12.3\" is not a digit.\n"
        }
    ]
}
```

---

### Feature 2: Emptiness and Null Rules

**As a developer**, I want to assert whether a value is present, absent, or blank, so I can enforce required and optional fields.

**Expected Behavior / Usage:**

*2.1 Not Empty*

Requires a value that is not considered empty; rejects empty string, zero, null, empty array and false.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_not_empty.json`

```json
{
    "description": "Requires a value that is not considered empty; rejects empty string, zero, null, empty array and false.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "not_empty",
                "value": "hello"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "not_empty",
                "value": ""
            },
            "expected_output": "invalid\ncode=14\nmessage=Value \"\" is empty, but non empty value was expected.\n"
        }
    ]
}
```

*2.2 Empty*

Requires a value that is considered empty; accepts empty string, zero, null and empty array, and rejects any non-empty value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_empty.json`

```json
{
    "description": "Requires a value that is considered empty; accepts empty string, zero, null and empty array, and rejects any non-empty value.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "empty",
                "value": ""
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "empty",
                "value": "x"
            },
            "expected_output": "invalid\ncode=205\nmessage=Value \"x\" is not empty, but empty value was expected.\n"
        }
    ]
}
```

*2.3 Null*

Requires the value to be null and rejects any non-null value, including empty string and zero.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_null.json`

```json
{
    "description": "Requires the value to be null and rejects any non-null value, including empty string and zero.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "null",
                "value": null
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "null",
                "value": ""
            },
            "expected_output": "invalid\ncode=25\nmessage=Value \"\" is not null, but null value was expected.\n"
        }
    ]
}
```

*2.4 Not Null*

Requires the value to be anything other than null; empty string and zero are accepted.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_not_null.json`

```json
{
    "description": "Requires the value to be anything other than null; empty string and zero are accepted.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "not_null",
                "value": "x"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "not_null",
                "value": null
            },
            "expected_output": "invalid\ncode=15\nmessage=Value \"<NULL>\" is null, but non null value was expected.\n"
        }
    ]
}
```

*2.5 Not Blank*

Requires a non-blank value: rejects the empty string and strings consisting solely of whitespace.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_not_blank.json`

```json
{
    "description": "Requires a non-blank value: rejects the empty string and strings consisting solely of whitespace.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "not_blank",
                "value": "x"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "not_blank",
                "value": "   "
            },
            "expected_output": "invalid\ncode=27\nmessage=Value \"   \" is blank, but was expected to contain a value.\n"
        }
    ]
}
```

---

### Feature 3: Numeric Comparison Rules

**As a developer**, I want to assert that a number falls within expected bounds, so I can validate ranges and thresholds.

**Expected Behavior / Usage:**

*3.1 Minimum (inclusive)*

Requires a number greater than or equal to a given lower bound; the bound itself is accepted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_min.json`

```json
{
    "description": "Requires a number greater than or equal to a given lower bound; the bound itself is accepted.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "min",
                "value": 10,
                "args": [
                    5
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "min",
                "value": 1,
                "args": [
                    5
                ]
            },
            "expected_output": "invalid\ncode=35\nmessage=Number \"1\" was expected to be at least \"5\".\n"
        }
    ]
}
```

*3.2 Maximum (inclusive)*

Requires a number less than or equal to a given upper bound; the bound itself is accepted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_max.json`

```json
{
    "description": "Requires a number less than or equal to a given upper bound; the bound itself is accepted.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "max",
                "value": 1,
                "args": [
                    5
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "max",
                "value": 10,
                "args": [
                    5
                ]
            },
            "expected_output": "invalid\ncode=36\nmessage=Number \"10\" was expected to be at most \"5\".\n"
        }
    ]
}
```

*3.3 Range (inclusive)*

Requires a number within an inclusive lower and upper bound; values outside the range are rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_range.json`

```json
{
    "description": "Requires a number within an inclusive lower and upper bound; values outside the range are rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "range",
                "value": 5,
                "args": [
                    1,
                    10
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "range",
                "value": 0,
                "args": [
                    1,
                    10
                ]
            },
            "expected_output": "invalid\ncode=30\nmessage=Number \"0\" was expected to be at least \"1\" and at most \"10\".\n"
        }
    ]
}
```

*3.4 Less Than (strict)*

Requires a number strictly less than a given limit; equality with the limit is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_less_than.json`

```json
{
    "description": "Requires a number strictly less than a given limit; equality with the limit is rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "less_than",
                "value": 4,
                "args": [
                    5
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "less_than",
                "value": 5,
                "args": [
                    5
                ]
            },
            "expected_output": "invalid\ncode=210\nmessage=Provided \"5\" is not less than \"5\".\n"
        }
    ]
}
```

*3.5 Less Than Or Equal*

Requires a number less than or equal to a given limit; values above the limit are rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_less_or_equal.json`

```json
{
    "description": "Requires a number less than or equal to a given limit; values above the limit are rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "less_or_equal",
                "value": 5,
                "args": [
                    5
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "less_or_equal",
                "value": 6,
                "args": [
                    5
                ]
            },
            "expected_output": "invalid\ncode=211\nmessage=Provided \"6\" is not less or equal than \"5\".\n"
        }
    ]
}
```

*3.6 Greater Than (strict)*

Requires a number strictly greater than a given limit; equality with the limit is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_greater_than.json`

```json
{
    "description": "Requires a number strictly greater than a given limit; equality with the limit is rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "greater_than",
                "value": 6,
                "args": [
                    5
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "greater_than",
                "value": 5,
                "args": [
                    5
                ]
            },
            "expected_output": "invalid\ncode=212\nmessage=Provided \"5\" is not greater than \"5\".\n"
        }
    ]
}
```

*3.7 Greater Than Or Equal*

Requires a number greater than or equal to a given limit; values below the limit are rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature3_7_greater_or_equal.json`

```json
{
    "description": "Requires a number greater than or equal to a given limit; values below the limit are rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "greater_or_equal",
                "value": 5,
                "args": [
                    5
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "greater_or_equal",
                "value": 4,
                "args": [
                    5
                ]
            },
            "expected_output": "invalid\ncode=213\nmessage=Provided \"4\" is not greater or equal than \"5\".\n"
        }
    ]
}
```

---

### Feature 4: String Content and Length Rules

**As a developer**, I want to assert the size and content of strings, so I can enforce formatting constraints.

**Expected Behavior / Usage:**

*4.1 Exact Length*

Requires a string whose character count equals an exact length.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_length.json`

```json
{
    "description": "Requires a string whose character count equals an exact length.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "length",
                "value": "hello",
                "args": [
                    5
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "length",
                "value": "hi",
                "args": [
                    5
                ]
            },
            "expected_output": "invalid\ncode=37\nmessage=Value \"hi\" has to be 5 exactly characters long, but length is 2.\n"
        }
    ]
}
```

*4.2 Minimum Length*

Requires a string whose character count is at least a given minimum.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_min_length.json`

```json
{
    "description": "Requires a string whose character count is at least a given minimum.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "min_length",
                "value": "hello",
                "args": [
                    3
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "min_length",
                "value": "hi",
                "args": [
                    3
                ]
            },
            "expected_output": "invalid\ncode=18\nmessage=Value \"hi\" is too short, it should have more than 3 characters, but only has 2 characters.\n"
        }
    ]
}
```

*4.3 Maximum Length*

Requires a string whose character count does not exceed a given maximum.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_max_length.json`

```json
{
    "description": "Requires a string whose character count does not exceed a given maximum.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "max_length",
                "value": "hi",
                "args": [
                    3
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "max_length",
                "value": "hello",
                "args": [
                    3
                ]
            },
            "expected_output": "invalid\ncode=19\nmessage=Value \"hello\" is too long, it should have no more than 3 characters, but has 5 characters.\n"
        }
    ]
}
```

*4.4 Length Between*

Requires a string whose character count is within an inclusive minimum and maximum.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_between_length.json`

```json
{
    "description": "Requires a string whose character count is within an inclusive minimum and maximum.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "between_length",
                "value": "hello",
                "args": [
                    3,
                    10
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "between_length",
                "value": "hi",
                "args": [
                    3,
                    10
                ]
            },
            "expected_output": "invalid\ncode=18\nmessage=Value \"hi\" is too short, it should have at least 3 characters, but only has 2 characters.\n"
        }
    ]
}
```

*4.5 Starts With*

Requires a string that begins with a given prefix.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_starts_with.json`

```json
{
    "description": "Requires a string that begins with a given prefix.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "starts_with",
                "value": "hello",
                "args": [
                    "he"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "starts_with",
                "value": "hello",
                "args": [
                    "lo"
                ]
            },
            "expected_output": "invalid\ncode=20\nmessage=Value \"hello\" does not start with \"lo\".\n"
        }
    ]
}
```

*4.6 Ends With*

Requires a string that ends with a given suffix.

**Test Cases:** `rcb_tests/public_test_cases/feature4_6_ends_with.json`

```json
{
    "description": "Requires a string that ends with a given suffix.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "ends_with",
                "value": "hello",
                "args": [
                    "lo"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "ends_with",
                "value": "hello",
                "args": [
                    "he"
                ]
            },
            "expected_output": "invalid\ncode=39\nmessage=Value \"hello\" does not end with \"he\".\n"
        }
    ]
}
```

*4.7 Contains*

Requires a string that contains a given substring anywhere within it.

**Test Cases:** `rcb_tests/public_test_cases/feature4_7_contains.json`

```json
{
    "description": "Requires a string that contains a given substring anywhere within it.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "contains",
                "value": "hello",
                "args": [
                    "ell"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "contains",
                "value": "hello",
                "args": [
                    "xyz"
                ]
            },
            "expected_output": "invalid\ncode=21\nmessage=Value \"hello\" does not contain \"xyz\".\n"
        }
    ]
}
```

*4.8 Regular Expression*

Requires a string that matches a given regular expression. A non-string value is also rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature4_8_regex.json`

```json
{
    "description": "Requires a string that matches a given regular expression. A non-string value is also rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "regex",
                "value": "abc",
                "args": [
                    "/^[a-z]+$/"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "regex",
                "value": "123",
                "args": [
                    "/^[a-z]+$/"
                ]
            },
            "expected_output": "invalid\ncode=17\nmessage=Value \"123\" does not match expression.\n"
        }
    ]
}
```

*4.9 Alphanumeric*

Requires a string that starts with a letter and then contains only letters and digits.

**Test Cases:** `rcb_tests/public_test_cases/feature4_9_alnum.json`

```json
{
    "description": "Requires a string that starts with a letter and then contains only letters and digits.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "alnum",
                "value": "abc123"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "alnum",
                "value": "123abc"
            },
            "expected_output": "invalid\ncode=31\nmessage=Value \"123abc\" is not alphanumeric, starting with letters and containing only letters and numbers.\n"
        }
    ]
}
```

---

### Feature 5: Equality and Identity Rules

**As a developer**, I want to assert equality or identity against a reference value, so I can validate exact or loose matches.

**Expected Behavior / Usage:**

*5.1 Loosely Equal*

Requires the value to be loosely equal (type-coercing comparison) to a reference value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_equal.json`

```json
{
    "description": "Requires the value to be loosely equal (type-coercing comparison) to a reference value.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "equal",
                "value": "10",
                "args": [
                    10
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "equal",
                "value": 10,
                "args": [
                    5
                ]
            },
            "expected_output": "invalid\ncode=33\nmessage=Value \"10\" does not equal expected value \"5\".\n"
        }
    ]
}
```

*5.2 Loosely Not Equal*

Requires the value to be loosely unequal to a reference value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_not_equal.json`

```json
{
    "description": "Requires the value to be loosely unequal to a reference value.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "not_equal",
                "value": 10,
                "args": [
                    5
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "not_equal",
                "value": 10,
                "args": [
                    10
                ]
            },
            "expected_output": "invalid\ncode=42\nmessage=Value \"10\" is equal to expected value \"10\".\n"
        }
    ]
}
```

*5.3 Strictly Identical*

Requires the value to be strictly identical (same type and value) to a reference value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_same.json`

```json
{
    "description": "Requires the value to be strictly identical (same type and value) to a reference value.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "same",
                "value": 10,
                "args": [
                    10
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "same",
                "value": 10,
                "args": [
                    "10"
                ]
            },
            "expected_output": "invalid\ncode=34\nmessage=Value \"10\" is not the same as expected value \"10\".\n"
        }
    ]
}
```

*5.4 Strictly Not Identical*

Requires the value to differ in type or value from a reference value (strict comparison).

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_not_same.json`

```json
{
    "description": "Requires the value to differ in type or value from a reference value (strict comparison).",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "not_same",
                "value": 10,
                "args": [
                    "10"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "not_same",
                "value": 10,
                "args": [
                    10
                ]
            },
            "expected_output": "invalid\ncode=43\nmessage=Value \"10\" is the same as expected value \"10\".\n"
        }
    ]
}
```

---

### Feature 6: Array, Choice and Key Rules

**As a developer**, I want to assert structural properties of arrays and membership in allowed sets, so I can validate collections and option fields.

**Expected Behavior / Usage:**

*6.1 Is Array*

Requires the value to be an array; non-array values are rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_is_array.json`

```json
{
    "description": "Requires the value to be an array; non-array values are rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "is_array",
                "value": [
                    1,
                    2
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "is_array",
                "value": "x"
            },
            "expected_output": "invalid\ncode=24\nmessage=Value \"x\" is not an array.\n"
        }
    ]
}
```

*6.2 In Choices*

Requires the value to be one of an allowed set of choices.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_in_choices.json`

```json
{
    "description": "Requires the value to be one of an allowed set of choices.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "in_choices",
                "value": "b",
                "args": [
                    [
                        "a",
                        "b",
                        "c"
                    ]
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "in_choices",
                "value": "z",
                "args": [
                    [
                        "a",
                        "b",
                        "c"
                    ]
                ]
            },
            "expected_output": "invalid\ncode=22\nmessage=Value \"z\" is not an element of the valid values: a, b, c\n"
        }
    ]
}
```

*6.3 Not In Choices*

Requires the value to be absent from a forbidden set of choices.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_not_in_choices.json`

```json
{
    "description": "Requires the value to be absent from a forbidden set of choices.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "not_in_choices",
                "value": "z",
                "args": [
                    [
                        "a",
                        "b",
                        "c"
                    ]
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "not_in_choices",
                "value": "b",
                "args": [
                    [
                        "a",
                        "b",
                        "c"
                    ]
                ]
            },
            "expected_output": "invalid\ncode=47\nmessage=Value \"b\" is in given \"<ARRAY>\".\n"
        }
    ]
}
```

*6.4 Key Exists*

Requires an array that contains a given key.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_key_exists.json`

```json
{
    "description": "Requires an array that contains a given key.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "key_exists",
                "value": {
                    "a": 1
                },
                "args": [
                    "a"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "key_exists",
                "value": {
                    "a": 1
                },
                "args": [
                    "b"
                ]
            },
            "expected_output": "invalid\ncode=26\nmessage=Array does not contain an element with key \"b\"\n"
        }
    ]
}
```

*6.5 Key Does Not Exist*

Requires an array that does not contain a given key.

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_key_not_exists.json`

```json
{
    "description": "Requires an array that does not contain a given key.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "key_not_exists",
                "value": {
                    "a": 1
                },
                "args": [
                    "b"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "key_not_exists",
                "value": {
                    "a": 1
                },
                "args": [
                    "a"
                ]
            },
            "expected_output": "invalid\ncode=216\nmessage=Array contains an element with key \"a\"\n"
        }
    ]
}
```

*6.6 Key Present And Not Empty*

Requires an array that contains a given key whose associated value is not empty.

**Test Cases:** `rcb_tests/public_test_cases/feature6_6_not_empty_key.json`

```json
{
    "description": "Requires an array that contains a given key whose associated value is not empty.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "not_empty_key",
                "value": {
                    "a": 1
                },
                "args": [
                    "a"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "not_empty_key",
                "value": {
                    "a": ""
                },
                "args": [
                    "a"
                ]
            },
            "expected_output": "invalid\ncode=14\nmessage=Value \"\" is empty, but non empty value was expected.\n"
        }
    ]
}
```

*6.7 Required Keys Not Empty*

Given an array and a list of required keys, requires every listed key to be present in the array with a non-empty value.

**Test Cases:** `rcb_tests/public_test_cases/feature6_7_choices_not_empty.json`

```json
{
    "description": "Given an array and a list of required keys, requires every listed key to be present in the array with a non-empty value.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "choices_not_empty",
                "value": {
                    "a": 1,
                    "b": 2
                },
                "args": [
                    [
                        "a",
                        "b"
                    ]
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "choices_not_empty",
                "value": {
                    "a": 1,
                    "b": ""
                },
                "args": [
                    [
                        "a",
                        "b"
                    ]
                ]
            },
            "expected_output": "invalid\ncode=14\nmessage=Value \"\" is empty, but non empty value was expected.\n"
        }
    ]
}
```

*6.8 Element Count*

Requires an array whose element count equals an exact number.

**Test Cases:** `rcb_tests/public_test_cases/feature6_8_count.json`

```json
{
    "description": "Requires an array whose element count equals an exact number.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "count",
                "value": [
                    1,
                    2,
                    3
                ],
                "args": [
                    3
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "count",
                "value": [
                    1,
                    2
                ],
                "args": [
                    3
                ]
            },
            "expected_output": "invalid\ncode=41\nmessage=List does not contain exactly \"3\" elements.\n"
        }
    ]
}
```

---

### Feature 7: Boolean Truth Rules

**As a developer**, I want to assert that a flag is exactly true or false, so I can validate strict boolean inputs.

**Expected Behavior / Usage:**

*7.1 Is True*

Requires the value to be exactly boolean true; anything else, including a truthy integer, is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_is_true.json`

```json
{
    "description": "Requires the value to be exactly boolean true; anything else, including a truthy integer, is rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "is_true",
                "value": true
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "is_true",
                "value": false
            },
            "expected_output": "invalid\ncode=32\nmessage=Value \"<FALSE>\" is not TRUE.\n"
        }
    ]
}
```

*7.2 Is False*

Requires the value to be exactly boolean false; anything else is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_is_false.json`

```json
{
    "description": "Requires the value to be exactly boolean false; anything else is rejected.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "is_false",
                "value": false
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "is_false",
                "value": true
            },
            "expected_output": "invalid\ncode=38\nmessage=Value \"<TRUE>\" is not FALSE.\n"
        }
    ]
}
```

---

### Feature 8: Format Validators

**As a developer**, I want to assert that a string conforms to a well-known format, so I can validate emails, URLs, identifiers and dates.

**Expected Behavior / Usage:**

*8.1 Email*

Requires a syntactically valid email address.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_email.json`

```json
{
    "description": "Requires a syntactically valid email address.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "email",
                "value": "foo@example.com"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "email",
                "value": "not-an-email"
            },
            "expected_output": "invalid\ncode=201\nmessage=Value \"not-an-email\" was expected to be a valid e-mail address.\n"
        }
    ]
}
```

*8.2 URL*

Requires a syntactically valid URL.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_url.json`

```json
{
    "description": "Requires a syntactically valid URL.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "url",
                "value": "http://example.com"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "url",
                "value": "notaurl"
            },
            "expected_output": "invalid\ncode=203\nmessage=Value \"notaurl\" was expected to be a valid URL starting with http or https\n"
        }
    ]
}
```

*8.3 UUID*

Requires a string in valid UUID format.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_uuid.json`

```json
{
    "description": "Requires a string in valid UUID format.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "uuid",
                "value": "ff6f8cb0-c57d-11e1-9b21-0800200c9a66"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "uuid",
                "value": "not-a-uuid"
            },
            "expected_output": "invalid\ncode=40\nmessage=Value \"not-a-uuid\" is not a valid UUID.\n"
        }
    ]
}
```

*8.4 JSON String*

Requires a string that is parseable as JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature8_4_json_string.json`

```json
{
    "description": "Requires a string that is parseable as JSON.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "json_string",
                "value": "{\"a\":1}"
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "json_string",
                "value": "{invalid"
            },
            "expected_output": "invalid\ncode=206\nmessage=Value \"{invalid\" is not a valid JSON string.\n"
        }
    ]
}
```

*8.5 Date*

Requires a string that represents a real calendar date in a given format.

**Test Cases:** `rcb_tests/public_test_cases/feature8_5_date.json`

```json
{
    "description": "Requires a string that represents a real calendar date in a given format.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "date",
                "value": "2021-01-01",
                "args": [
                    "Y-m-d"
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "date",
                "value": "2021-13-99",
                "args": [
                    "Y-m-d"
                ]
            },
            "expected_output": "invalid\ncode=214\nmessage=Date \"2021-13-99\" is invalid or does not match format \"Y-m-d\".\n"
        }
    ]
}
```

---

### Feature 9: Composition Modes

**As a developer**, I want to combine and aggregate rules, so I can express null-tolerance, collection-wide checks, ordered chains, and batched multi-field validation.

**Expected Behavior / Usage:**

*9.1 Null-Tolerant Wrapper*

A null-tolerant wrapper around any rule: a null value always passes, otherwise the underlying rule is applied.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_null_or.json`

```json
{
    "description": "A null-tolerant wrapper around any rule: a null value always passes, otherwise the underlying rule is applied.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "max",
                "value": null,
                "args": [
                    5
                ],
                "null_or": true
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "max",
                "value": 10,
                "args": [
                    5
                ],
                "null_or": true
            },
            "expected_output": "invalid\ncode=36\nmessage=Number \"10\" was expected to be at most \"5\".\n"
        }
    ]
}
```

*9.2 Apply To All Elements*

Applies a rule to every element of a collection; passes only when all elements satisfy the rule, and fails as soon as one element violates it.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_all.json`

```json
{
    "description": "Applies a rule to every element of a collection; passes only when all elements satisfy the rule, and fails as soon as one element violates it.",
    "cases": [
        {
            "input": {
                "mode": "check",
                "check": "integer",
                "value": [
                    1,
                    2,
                    3
                ],
                "all": true
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "check",
                "check": "integer",
                "value": [
                    1,
                    "x",
                    3
                ],
                "all": true
            },
            "expected_output": "invalid\ncode=10\nmessage=Value \"x\" is not an integer.\n"
        }
    ]
}
```

*9.3 Ordered Rule Chain*

Applies an ordered sequence of rules to a single value, stopping at the first violation. Referencing a rule that does not exist yields a normalized unknown-assertion error.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_chain.json`

```json
{
    "description": "Applies an ordered sequence of rules to a single value, stopping at the first violation. Referencing a rule that does not exist yields a normalized unknown-assertion error.",
    "cases": [
        {
            "input": {
                "mode": "chain",
                "value": 10,
                "steps": [
                    {
                        "check": "integer"
                    },
                    {
                        "check": "min",
                        "args": [
                            5
                        ]
                    }
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "chain",
                "value": 3,
                "steps": [
                    {
                        "check": "integer"
                    },
                    {
                        "check": "min",
                        "args": [
                            5
                        ]
                    }
                ]
            },
            "expected_output": "invalid\ncode=35\nmessage=Number \"3\" was expected to be at least \"5\".\n"
        }
    ]
}
```

*9.4 Aggregated Multi-Field Validation*

Collects validation outcomes across several labelled fields and reports every failure together in an aggregated report, rather than stopping at the first error. When all fields pass, the success result is produced.

**Test Cases:** `rcb_tests/public_test_cases/feature9_4_lazy.json`

```json
{
    "description": "Collects validation outcomes across several labelled fields and reports every failure together in an aggregated report, rather than stopping at the first error. When all fields pass, the success result is produced.",
    "cases": [
        {
            "input": {
                "mode": "lazy",
                "assertions": [
                    {
                        "value": "hello",
                        "property_path": "name",
                        "steps": [
                            {
                                "check": "string"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "valid\n"
        },
        {
            "input": {
                "mode": "lazy",
                "assertions": [
                    {
                        "value": 10,
                        "property_path": "name",
                        "steps": [
                            {
                                "check": "string"
                            }
                        ]
                    },
                    {
                        "value": "",
                        "property_path": "bio",
                        "steps": [
                            {
                                "check": "not_blank"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "The following 2 assertions failed:\n1) name: Value \"10\" expected to be string, type integer given.\n2) bio: Value \"\" is blank, but was expected to contain a value.\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the rules and composition modes described above, with the core rule engine decoupled from all I/O.
2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON request from stdin, invokes the core engine, and prints the outcome to stdout, strictly matching the per-leaf contracts above.
3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` that reads every `*.json` case file from a case directory (default `public_test_cases`, switchable with `--cases-dir <subdir>`) and writes one file per case to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03d}.txt` containing only the raw program stdout.



---
**Implementation notes:**
- match the length requirement as specified in the contract
- validate a substring match per the regex field spec
