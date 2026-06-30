## Product Requirement Document

# DOM Assertion Contract Adapter - Black-Box Assertions for Rendered HTML

## Project Goal

Build a DOM assertion helper and execution adapter that allows developers to verify rendered HTML structure, text, form values, attributes, classes, disabled state, and focus state without writing repetitive low-level DOM inspection code.

---

## Background & Problem

Without this library/tool, developers are forced to manually query the DOM, count matches, normalize text, inspect attributes and values, and construct diagnostic messages for every UI assertion. This leads to repetitive code, brittle whitespace comparisons, inconsistent failure output, and harder-to-maintain tests.

With this library/tool, a caller supplies a small JSON command to the execution adapter and receives deterministic stdout describing the observable assertion result or a normalized error.

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

### Feature 1: Whitespace Normalization

**As a developer**, I want to normalize text copied from a document into stable comparison text, so I can compare user-visible text without brittle formatting differences.

**Expected Behavior / Usage:**

The adapter input uses `operation: "normalize_whitespace"` with a `text` string. The output is JSON with `value`, where tabs, carriage returns, newlines, and repeated spaces are treated as ordinary whitespace, collapsed into one space, and trimmed at the beginning and end. Non-whitespace characters remain in their original order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_normalize_whitespace.json`

```json
{
    "description": "Normalize whitespace in text",
    "cases": [
        {
            "input": {
                "operation": "normalize_whitespace",
                "text": "[a string transformation logic example]"
            },
            "expected_output": "{\n  \"value\": \"[a string transformation logic example]\"\n}\n"
        },
        {
            "input": {
                "operation": "normalize_whitespace",
                "text": "a     b\tc"
            },
            "expected_output": "{\n  \"value\": \"[a string transformation logic example]\"\n}\n"
        }
    ]
}
```

---

### Feature 2: DOM Target Description

**As a developer**, I want to render DOM targets as compact, human-readable selector descriptions, so I can show precise assertion evidence for elements and collections.

**Expected Behavior / Usage:**

The adapter input uses `operation: "describe_node"`, an optional `document` HTML string, and a `node` descriptor. A selector-string target is returned unchanged. A single element is described by lowercase tag name followed by id, classes, and non-class/id attributes. A collection is described by joining up to the first five element descriptions; empty collections and truncated collections must be reported explicitly.

**Test Cases:** `rcb_tests/public_test_cases/feature2_node_description.json`

```json
{
    "description": "Describe DOM targets as compact selectors",
    "cases": [
        {
            "input": {
                "operation": "describe_node",
                "document": "",
                "node": {
                    "kind": "all",
                    "value": "h1"
                }
            },
            "expected_output": "{\n  \"value\": \"[default formatting for empty lists]\"\n}\n"
        },
        {
            "input": {
                "operation": "describe_node",
                "document": "<h1></h1><h1></h1><h1 class=\"foo\"></h1><h1></h1><h1></h1><h1></h1>",
                "node": {
                    "kind": "all",
                    "value": "h1"
                }
            },
            "expected_output": "{\n  \"value\": \"h1, h1, h1.foo, h1, h1... (+1 more)\"\n}\n"
        }
    ]
}
```

---

### Feature 3: Element Presence

**As a developer**, I want to assert that a selector resolves to existing elements, so I can report both success and failure with observable DOM evidence.

**Expected Behavior / Usage:**

The adapter input uses `operation: "presence"`, a `document`, a selector `target`, and optionally `arguments.count`. Without a count, the assertion is satisfied when at least one element matches. With a count, it is satisfied only when the match count is exact. The output is JSON containing one assertion object with `satisfied`, `actual`, `expected`, and `message` fields.

**Test Cases:** `rcb_tests/public_test_cases/feature3_presence.json`

```json
{
    "description": "Assert that selected elements exist with optional counts",
    "cases": [
        {
            "input": {
                "operation": "presence",
                "document": "<h1 class=\"baz\">foo</h1>bar",
                "target": {
                    "kind": "selector",
                    "value": "h1"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"Element h1 exists\",\n      \"expected\": \"Element h1 exists\",\n      \"message\": \"Element h1 exists\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "presence",
                "document": "<h1 class=\"baz\">foo</h1>bar",
                "target": {
                    "kind": "selector",
                    "value": "h2"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"Element h2 does not exist\",\n      \"expected\": \"Element h2 exists\",\n      \"message\": \"Element h2 exists\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 4: Element Absence

**As a developer**, I want to assert that a selector resolves to no elements, so I can verify UI states where content should not be present.

**Expected Behavior / Usage:**

The adapter input uses `operation: "absence"`, a `document`, a selector `target`, and optionally a selector `root` that scopes the query. The assertion is satisfied only when the selector has zero matches in the chosen root. The output reports the expected absence and the actual existence count when any matching elements are found.

**Test Cases:** `rcb_tests/public_test_cases/feature4_absence.json`

```json
{
    "description": "Assert that selected elements do not exist",
    "cases": [
        {
            "input": {
                "operation": "absence",
                "document": "<h1 class=\"baz\">foo</h1>bar",
                "target": {
                    "kind": "selector",
                    "value": "h2"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"Element h2 does not exist\",\n      \"expected\": \"Element h2 does not exist\",\n      \"message\": \"Element h2 does not exist\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "absence",
                "document": "<h1 class=\"baz\">foo</h1>bar",
                "target": {
                    "kind": "selector",
                    "value": "h1"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"Element h1 exists once\",\n      \"expected\": \"Element h1 does not exist\",\n      \"message\": \"Element h1 does not exist\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 5: Attribute Presence and Value Matching

**As a developer**, I want to assert that an element has an attribute and optionally a matching value, so I can validate rendered HTML attributes with diagnostic evidence.

**Expected Behavior / Usage:**

The adapter input uses `operation: "attribute_matches"` for exact or pattern value checks, or `operation: "attribute_present"` for presence-only checks. Inputs include a selector `target`, an attribute `arguments.name`, and optionally `arguments.expected`, which may be a string or `{ "kind": "regex", "pattern": "..." }`. The output reports whether the selected element has the attribute and whether its value matches the expected condition.

**Test Cases:** `rcb_tests/public_test_cases/feature5_attribute_matching.json`

```json
{
    "description": "Assert attribute presence and values",
    "cases": [
        {
            "input": {
                "operation": "attribute_matches",
                "document": "<input type=\"password\">",
                "target": {
                    "kind": "selector",
                    "value": "input"
                },
                "arguments": {
                    "name": "type",
                    "expected": "password"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"Element input has attribute \\\"type\\\" with value \\\"password\\\"\",\n      \"expected\": \"Element input has attribute \\\"type\\\" with value \\\"password\\\"\",\n      \"message\": \"Element input has attribute \\\"type\\\" with value \\\"password\\\"\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "attribute_matches",
                "document": "<input type=\"password\">",
                "target": {
                    "kind": "selector",
                    "value": "input"
                },
                "arguments": {
                    "name": "type",
                    "expected": "text"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"Element input has attribute \\\"type\\\" with value \\\"password\\\"\",\n      \"expected\": \"Element input has attribute \\\"type\\\" with value \\\"text\\\"\",\n      \"message\": \"Element input has attribute \\\"type\\\" with value \\\"text\\\"\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 6: Attribute Absence

**As a developer**, I want to assert that an element does not carry a named attribute, so I can verify that rendered markup omits unwanted flags or values.

**Expected Behavior / Usage:**

The adapter input uses `operation: "attribute_absent"` with a selector `target` and `arguments.name`. The assertion is satisfied when the selected element lacks that attribute. If the attribute exists, the output reports the actual attribute value, including the empty string used by present boolean attributes.

**Test Cases:** `rcb_tests/public_test_cases/feature6_attribute_absence.json`

```json
{
    "description": "Assert attribute absence",
    "cases": [
        {
            "input": {
                "operation": "attribute_absent",
                "document": "<input type=\"password\" required>",
                "target": {
                    "kind": "selector",
                    "value": "input"
                },
                "arguments": {
                    "name": "disabled"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"Element input does not have attribute \\\"disabled\\\"\",\n      \"expected\": \"Element input does not have attribute \\\"disabled\\\"\",\n      \"message\": \"Element input does not have attribute \\\"disabled\\\"\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "attribute_absent",
                "document": "<input type=\"password\" required>",
                "target": {
                    "kind": "selector",
                    "value": "input"
                },
                "arguments": {
                    "name": "type"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"Element input has attribute \\\"type\\\" with value \\\"password\\\"\",\n      \"expected\": \"Element input does not have attribute \\\"type\\\"\",\n      \"message\": \"Element input does not have attribute \\\"type\\\"\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 7: CSS Class Membership

**As a developer**, I want to assert that an element contains or omits a CSS class, so I can validate style-related DOM state with clear diagnostics.

**Expected Behavior / Usage:**

The adapter input uses `operation: "class_contains"` to require a class or `operation: "class_absent"` to forbid a class. Inputs include a selector `target` and `arguments.name`. The output includes the full actual class list, the expected class condition, and a generated message naming the element and class condition.

**Test Cases:** `rcb_tests/public_test_cases/feature7_class_matching.json`

```json
{
    "description": "Assert CSS class membership and absence",
    "cases": [
        {
            "input": {
                "operation": "class_contains",
                "document": "<input type=\"password\" class=\"secret-password-input foo\">",
                "target": {
                    "kind": "selector",
                    "value": "input[type=\"password\"]"
                },
                "arguments": {
                    "name": "secret-password-input"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"secret-password-input foo\",\n      \"expected\": \"secret-password-input\",\n      \"message\": \"Element input[type=\\\"password\\\"] has CSS class \\\"secret-password-input\\\"\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "class_contains",
                "document": "<input type=\"password\" class=\"secret-password-input foo\">",
                "target": {
                    "kind": "selector",
                    "value": "input[type=\"password\"]"
                },
                "arguments": {
                    "name": "username-input"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"secret-password-input foo\",\n      \"expected\": \"username-input\",\n      \"message\": \"Element input[type=\\\"password\\\"] has CSS class \\\"username-input\\\"\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 8: Complete Text Equality

**As a developer**, I want to assert that an element’s complete text equals an expected string after whitespace normalization, so I can compare rendered content without depending on indentation or inline markup layout.

**Expected Behavior / Usage:**

The adapter input uses `operation: "text_equals"` with a selector `target` and `arguments.expected`. Text is read from the selected element including child text, then whitespace is collapsed before comparison. The output includes normalized actual text, normalized expected text, and a message describing the equality requirement.

**Test Cases:** `rcb_tests/public_test_cases/feature8_text_equality.json`

```json
{
    "description": "Assert complete text content after whitespace normalization",
    "cases": [
        {
            "input": {
                "operation": "text_equals",
                "document": "<h2 id=\"title\">\n\tWelcome to <b>QUnit</b>\n</h2>\n",
                "target": {
                    "kind": "selector",
                    "value": "#title"
                },
                "arguments": {
                    "expected": "Welcome to QUnit"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"Welcome to QUnit\",\n      \"expected\": \"Welcome to QUnit\",\n      \"message\": \"Element #title has text \\\"Welcome to QUnit\\\"\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "text_equals",
                "document": "<h2 id=\"title\">\n\tWelcome to <b>QUnit</b>\n</h2>\n",
                "target": {
                    "kind": "selector",
                    "value": "#title"
                },
                "arguments": {
                    "expected": "Welcome to Mocha"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"Welcome to QUnit\",\n      \"expected\": \"Welcome to Mocha\",\n      \"message\": \"Element #title has text \\\"Welcome to Mocha\\\"\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 9: Text Pattern Matching

**As a developer**, I want to assert that an element’s text matches a regular expression, so I can validate variable rendered text without hard-coding every character.

**Expected Behavior / Usage:**

The adapter input uses `operation: "text_matches"` with a selector `target` and `arguments.expected` as `{ "kind": "regex", "pattern": "..." }`. The assertion is satisfied when the selected element text matches the pattern. The output preserves the actual text and renders the expected pattern as a string in assertion evidence.

**Test Cases:** `rcb_tests/public_test_cases/feature9_text_pattern.json`

```json
{
    "description": "Assert text content with patterns",
    "cases": [
        {
            "input": {
                "operation": "text_matches",
                "document": "<h1 class=\"baz\">foo</h1>bar",
                "target": {
                    "kind": "selector",
                    "value": "h1"
                },
                "arguments": {
                    "expected": {
                        "kind": "regex",
                        "pattern": "fo+"
                    }
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"foo\",\n      \"expected\": \"/fo+/\",\n      \"message\": \"Element h1 has text matching /fo+/\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "text_matches",
                "document": "<h1 class=\"baz\">foo</h1>bar",
                "target": {
                    "kind": "selector",
                    "value": "h1"
                },
                "arguments": {
                    "expected": {
                        "kind": "regex",
                        "pattern": "oo"
                    }
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"foo\",\n      \"expected\": \"/oo/\",\n      \"message\": \"Element h1 has text matching /oo/\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 10: Text Containment and Exclusion

**As a developer**, I want to assert that element text includes or excludes a substring, so I can check partial content presence and absence in rendered UI text.

**Expected Behavior / Usage:**

The adapter input uses `operation: "text_contains"` for required substrings and `operation: "text_excludes"` for forbidden substrings. Inputs include a selector `target` and `arguments.expected` containing the substring. The output reports the observed text or a generated inclusion/exclusion diagnostic depending on the assertion kind.

**Test Cases:** `rcb_tests/public_test_cases/feature10_text_containment.json`

```json
{
    "description": "Assert text containment and exclusion",
    "cases": [
        {
            "input": {
                "operation": "text_contains",
                "document": "<h1 class=\"baz\">foo</h1>bar",
                "target": {
                    "kind": "selector",
                    "value": "h1"
                },
                "arguments": {
                    "expected": "foo"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"foo\",\n      \"expected\": \"foo\",\n      \"message\": \"Element h1 has text containing \\\"foo\\\"\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "text_contains",
                "document": "<h1 class=\"baz\">foo</h1>bar",
                "target": {
                    "kind": "selector",
                    "value": "h1"
                },
                "arguments": {
                    "expected": "oo"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"foo\",\n      \"expected\": \"oo\",\n      \"message\": \"Element h1 has text containing \\\"oo\\\"\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 11: Form Control Value Assertions

**As a developer**, I want to assert exact, pattern, non-empty, and empty values for form controls, so I can validate user-editable field state through its value property.

**Expected Behavior / Usage:**

The adapter input uses `operation: "value_equals"`, `"value_matches"`, `"value_present"`, or `"value_empty"`. Inputs include a selector `target`, optional initial `values` assignments for controls, and an expected string or pattern when needed. The output reports whether the control value satisfies the condition and includes actual and expected value evidence when the original assertion produces it.

**Test Cases:** `rcb_tests/public_test_cases/feature11_value_matching.json`

```json
{
    "description": "Assert form control values",
    "cases": [
        {
            "input": {
                "operation": "value_equals",
                "document": "<input class=\"input username\">",
                "values": [
                    {
                        "selector": "input.username",
                        "value": "HSimpson"
                    }
                ],
                "target": {
                    "kind": "selector",
                    "value": "input.username"
                },
                "arguments": {
                    "expected": "HSimpson"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"HSimpson\",\n      \"expected\": \"HSimpson\",\n      \"message\": \"Element input.username has value \\\"HSimpson\\\"\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "value_equals",
                "document": "<input class=\"input username\">",
                "values": [
                    {
                        "selector": "input.username",
                        "value": "HSimpson"
                    }
                ],
                "target": {
                    "kind": "selector",
                    "value": "input.username"
                },
                "arguments": {
                    "expected": "Bart"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"HSimpson\",\n      \"expected\": \"Bart\",\n      \"message\": \"Element input.username has value \\\"Bart\\\"\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 12: Disabled State Assertions

**As a developer**, I want to assert that a selected control is disabled, so I can distinguish disabled controls, enabled controls, and elements that cannot be disabled.

**Expected Behavior / Usage:**

The adapter input uses `operation: "disabled_state"` with a selector `target`. The assertion is satisfied only when the selected element exposes a disabled state that is true. Enabled controls fail with a not-disabled diagnostic, and elements that do not support disabled state fail with a non-support diagnostic.

**Test Cases:** `rcb_tests/public_test_cases/feature12_disabled_state.json`

```json
{
    "description": "Assert disabled state of selected controls",
    "cases": [
        {
            "input": {
                "operation": "disabled_state",
                "document": "<input disabled>",
                "target": {
                    "kind": "selector",
                    "value": "input"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"Element input is disabled\",\n      \"expected\": \"Element input is disabled\",\n      \"message\": \"Element input is disabled\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "disabled_state",
                "document": "<input>",
                "target": {
                    "kind": "selector",
                    "value": "input"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"Element input is not disabled\",\n      \"expected\": \"Element input is disabled\",\n      \"message\": \"Element input is disabled\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 13: Focus State Assertions

**As a developer**, I want to assert whether a selected element is or is not the active element, so I can validate keyboard-focus behavior in rendered DOM.

**Expected Behavior / Usage:**

The adapter input uses `operation: "focused_state"` or `operation: "not_focused_state"` with a selector `target` and optional `focus` selector that sets the active element before assertion. Focus assertions include actual and expected focus descriptions. Not-focus assertions report satisfaction and message. Missing targets produce a normal existence assertion.

**Test Cases:** `rcb_tests/public_test_cases/feature13_focus_state.json`

```json
{
    "description": "Assert current focus and not-focus state",
    "cases": [
        {
            "input": {
                "operation": "focused_state",
                "document": "foo<input type=\"email\">bar",
                "focus": "input",
                "target": {
                    "kind": "selector",
                    "value": "input"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": true,\n      \"actual\": \"input[type=\\\"email\\\"]\",\n      \"expected\": \"input\",\n      \"message\": \"Element input is focused\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "focused_state",
                "document": "foo<input type=\"email\">bar",
                "focus": "body",
                "target": {
                    "kind": "selector",
                    "value": "input"
                }
            },
            "expected_output": "{\n  \"assertions\": [\n    {\n      \"satisfied\": false,\n      \"actual\": \"body\",\n      \"expected\": \"input\",\n      \"message\": \"Element input is focused\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 14: Unsupported Target Error Normalization

**As a developer**, I want to return language-neutral errors for assertion targets that cannot be interpreted, so I can avoid leaking runtime-specific exception classes or messages in black-box output.

**Expected Behavior / Usage:**

When an assertion operation receives a target that is not a selector string, an element, or a supported null/missing element case, the adapter catches the implementation error and renders a neutral JSON error. The output uses `error: "unexpected_target"` plus `target_type` and `target_value` fields instead of host-language exception names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature14_unexpected_target_errors.json`

```json
{
    "description": "Normalize errors for unsupported assertion targets",
    "cases": [
        {
            "input": {
                "operation": "presence",
                "document": "<h1></h1>",
                "target": {
                    "kind": "number",
                    "value": 5
                }
            },
            "expected_output": "{\n  \"error\": \"unexpected_target\",\n  \"target_type\": \"number\",\n  \"target_value\": \"5\"\n}\n"
        },
        {
            "input": {
                "operation": "text_contains",
                "document": "<h1>foo</h1>",
                "target": {
                    "kind": "boolean",
                    "value": true
                },
                "arguments": {
                    "expected": "foo"
                }
            },
            "expected_output": "{\n  \"error\": \"unexpected_target\",\n  \"target_type\": \"boolean\",\n  \"target_value\": \"true\"\n}\n"
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
- use the same node description structure as used for 'all' kind selectors
- refer to the active DOM element selection logic in the test suite examples
