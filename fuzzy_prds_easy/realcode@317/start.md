## Product Requirement Document

# Fluent Test Expectation Toolkit - Black-Box Assertion and Scenario Behavior

## Project Goal

Build a developer testing utility that allows developers to express readable expectations, structural comparisons, and scenario setup/action flows without repetitive assertion boilerplate.

---

## Background & Problem

Without this library/tool, developers are forced to manually write low-level comparisons, membership checks, range checks, exception checks, and setup/teardown state passing in every test. This leads to repetitive code, inconsistent error reporting, brittle value rendering, and maintenance issues when nested structures fail.

With this library/tool, developers can describe expected behavior at a high level while receiving deterministic, inspectable outputs for both simple checks and nested scenario flows.

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

### Feature 1: Equality Checks

**As a developer**, I want to compare two supplied values for equality or inequality, so I can express exact value expectations in fluent tests.

**Expected Behavior / Usage:**

The input is an object with `actual`, `expected`, and an optional `negated` flag. The adapter compares the two JSON-compatible values, including nested objects. On a match, stdout identifies the feature, states `result=matched`, echoes whether the comparison was negated, and renders both compared values as canonical JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature1_equality.json`

```json
{
    "description": "Equality and inequality assertions",
    "cases": [
        {
            "input": {
                "actual": 4,
                "expected": 4
            },
            "expected_output": "feature=feature1_equality\nresult=matched\nnegated=false\nactual=4\nexpected=4\n"
        },
        {
            "input": {
                "actual": 4,
                "expected": 8,
                "negated": true
            },
            "expected_output": "feature=feature1_equality\nresult=matched\nnegated=true\nactual=4\nexpected=8\n"
        }
    ]
}
```

---

### Feature 2: Numeric Range Membership

**As a developer**, I want to verify that a number falls inside or outside a half-open range, so I can state boundary-sensitive numeric expectations clearly.

**Expected Behavior / Usage:**

The input is an object with `value`, `lower`, `upper`, and an optional `negated` flag. The range includes the lower bound and excludes the upper bound. On a match, stdout identifies the feature, states `result=matched`, echoes the negation flag, the checked value, the lower bound, and the exclusive upper bound.

**Test Cases:** `rcb_tests/public_test_cases/feature2_range_membership.json`

```json
{
    "description": "Exclusive upper-bound numeric range membership",
    "cases": [
        {
            "input": {
                "value": 1,
                "lower": 0,
                "upper": 2
            },
            "expected_output": "feature=feature2_range_membership\nresult=matched\nnegated=false\nvalue=1\nlower=0\nupper_exclusive=2\n"
        },
        {
            "input": {
                "value": 4,
                "lower": 0,
                "upper": 2,
                "negated": true
            },
            "expected_output": "feature=feature2_range_membership\nresult=matched\nnegated=true\nvalue=4\nlower=0\nupper_exclusive=2\n"
        }
    ]
}
```

---

### Feature 3: Truthiness, Falsiness, and Null Checks

**As a developer**, I want to classify a supplied value as truthy, falsy, or null, so I can write readable expectations for boolean-like and absence conditions.

**Expected Behavior / Usage:**

The input is an object with `value`, an `expectation` of `truthy`, `falsy`, or `null`, and an optional `negated` flag. On a match, stdout identifies the feature, states `result=matched`, and echoes the expectation, negation flag, and value in canonical JSON form.

**Test Cases:** `rcb_tests/public_test_cases/feature3_truth_null.json`

```json
{
    "description": "Truthiness, falsiness, and null checks",
    "cases": [
        {
            "input": {
                "value": true,
                "expectation": "truthy"
            },
            "expected_output": "feature=feature3_truth_null\nresult=matched\nexpectation=truthy\nnegated=false\nvalue=true\n"
        },
        {
            "input": {
                "value": false,
                "expectation": "truthy",
                "negated": true
            },
            "expected_output": "feature=feature3_truth_null\nresult=matched\nexpectation=truthy\nnegated=true\nvalue=false\n"
        },
        {
            "input": {
                "value": false,
                "expectation": "falsy"
            },
            "expected_output": "feature=feature3_truth_null\nresult=matched\nexpectation=falsy\nnegated=false\nvalue=false\n"
        }
    ]
}
```

---

### Feature 4: Type and Callable Category Checks

**As a developer**, I want to verify that a value belongs to a broad category or is callable, so I can state interface expectations without exposing implementation structure.

**Expected Behavior / Usage:**

The input is an object with `value`, `category`, and an optional `negated` flag. Supported categories in the contract are `integer`, `iterable`, `list`, and `callable`; the sentinel value `callable_sample` represents a callable input for adapter execution. On a match, stdout identifies the feature, states `result=matched`, and echoes the category, negation flag, and value token.

**Test Cases:** `rcb_tests/public_test_cases/feature4_type_callable.json`

```json
{
    "description": "Type category and callable checks",
    "cases": [
        {
            "input": {
                "value": 1,
                "category": "integer"
            },
            "expected_output": "feature=feature4_type_callable\nresult=matched\ncategory=integer\nnegated=false\nvalue=1\n"
        },
        {
            "input": {
                "value": [],
                "category": "iterable"
            },
            "expected_output": "feature=feature4_type_callable\nresult=matched\ncategory=iterable\nnegated=false\nvalue=[]\n"
        },
        {
            "input": {
                "value": {},
                "category": "list",
                "negated": true
            },
            "expected_output": "feature=feature4_type_callable\nresult=matched\ncategory=list\nnegated=true\nvalue={}\n"
        }
    ]
}
```

---

### Feature 5: Collection Size Checks

**As a developer**, I want to verify emptiness or exact length of a collection, so I can make collection cardinality expectations explicit.

**Expected Behavior / Usage:**

The input is an object with `value`, `mode`, an optional `length`, and an optional `negated` flag. `mode=empty` checks whether the collection is empty; `mode=length` checks exact length. On a match, stdout identifies the feature, states `result=matched`, and echoes the mode, negation flag, collection value, and length when applicable.

**Test Cases:** `rcb_tests/public_test_cases/feature5_collection_size.json`

```json
{
    "description": "Collection emptiness and length checks",
    "cases": [
        {
            "input": {
                "value": [],
                "mode": "empty"
            },
            "expected_output": "feature=feature5_collection_size\nresult=matched\nmode=empty\nnegated=false\nvalue=[]\n"
        },
        {
            "input": {
                "value": [
                    1,
                    2,
                    3
                ],
                "mode": "empty",
                "negated": true
            },
            "expected_output": "feature=feature5_collection_size\nresult=matched\nmode=empty\nnegated=true\nvalue=[1,2,3]\n"
        }
    ]
}
```

---

### Feature 6: Numeric Ordering Checks

**As a developer**, I want to compare two numbers using ordering relations, so I can express less-than and greater-than expectations precisely.

**Expected Behavior / Usage:**

The input is an object with `actual`, `relation`, `expected`, and an optional `negated` flag. Supported relations are `greater`, `greater_or_equal`, `lower`, and `lower_or_equal`. On a match, stdout identifies the feature, states `result=matched`, and echoes the relation, negation flag, actual value, and expected comparator value.

**Test Cases:** `rcb_tests/public_test_cases/feature6_ordering.json`

```json
{
    "description": "Numeric ordering comparisons",
    "cases": [
        {
            "input": {
                "actual": 5,
                "relation": "greater",
                "expected": 4
            },
            "expected_output": "feature=feature6_ordering\nresult=matched\nrelation=greater\nnegated=false\nactual=5\nexpected=4\n"
        },
        {
            "input": {
                "actual": 1,
                "relation": "greater",
                "expected": 2,
                "negated": true
            },
            "expected_output": "feature=feature6_ordering\nresult=matched\nrelation=greater\nnegated=true\nactual=1\nexpected=2\n"
        },
        {
            "input": {
                "actual": 4,
                "relation": "greater_or_equal",
                "expected": 4
            },
            "expected_output": "feature=feature6_ordering\nresult=matched\nrelation=greater_or_equal\nnegated=false\nactual=4\nexpected=4\n"
        }
    ]
}
```

---

### Feature 7: Record and Mapping Member Lookup

**As a developer**, I want to verify that a record property or mapping key exists and may hold a specific value, so I can test object-like and dictionary-like data access consistently.

**Expected Behavior / Usage:**

The input is an object selecting `target_kind` as `record` or `mapping`, providing the corresponding target data, a `member` name, an optional `expected_value`, and an optional `negated` flag. On a match, stdout identifies the feature, states `result=matched`, and echoes the target kind, member name, negation flag, and expected value when supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature7_member_lookup.json`

```json
{
    "description": "Record property and mapping key lookup",
    "cases": [
        {
            "input": {
                "target_kind": "record",
                "record": {
                    "name": "John Doe"
                },
                "member": "name"
            },
            "expected_output": "feature=feature7_member_lookup\nresult=matched\ntarget_kind=record\nmember=name\nnegated=false\n"
        },
        {
            "input": {
                "target_kind": "record",
                "record": {
                    "name": "John Doe"
                },
                "member": "age",
                "negated": true
            },
            "expected_output": "feature=feature7_member_lookup\nresult=matched\ntarget_kind=record\nmember=age\nnegated=true\n"
        }
    ]
}
```

---

### Feature 8: Normalized Text Similarity

**As a developer**, I want to compare text while ignoring whitespace and case differences, so I can avoid brittle failures caused only by formatting.

**Expected Behavior / Usage:**

The input is an object with `actual`, `expected`, and an optional `negated` flag. The comparison removes whitespace and ignores case. On a match, stdout identifies the feature, states `result=matched`, and echoes the negation flag plus both text values as JSON strings.

**Test Cases:** `rcb_tests/public_test_cases/feature8_text_similarity.json`

```json
{
    "description": "Whitespace-insensitive case-insensitive text similarity",
    "cases": [
        {
            "input": {
                "actual": "   \n  aa \n  ",
                "expected": "AA"
            },
            "expected_output": "feature=feature8_text_similarity\nresult=matched\nnegated=false\nactual=\"   \\n  aa \\n  \"\nexpected=\"AA\"\n"
        },
        {
            "input": {
                "actual": "   \n  bb \n  ",
                "expected": "aa",
                "negated": true
            },
            "expected_output": "feature=feature8_text_similarity\nresult=matched\nnegated=true\nactual=\"   \\n  bb \\n  \"\nexpected=\"aa\"\n"
        }
    ]
}
```

---

### Feature 9: Regular Expression Matching

**As a developer**, I want to verify that text matches or does not match a supplied regular expression, so I can state pattern-based text expectations.

**Expected Behavior / Usage:**

The input is an object with `actual`, `pattern`, and an optional `negated` flag. On a match, stdout identifies the feature, states `result=matched`, and echoes the negation flag, input text, and pattern string.

**Test Cases:** `rcb_tests/public_test_cases/feature9_pattern_match.json`

```json
{
    "description": "Regular-expression matching",
    "cases": [
        {
            "input": {
                "actual": "some string",
                "pattern": "\\w{4} \\w{6}"
            },
            "expected_output": "feature=feature9_pattern_match\nresult=matched\nnegated=false\nactual=\"some string\"\npattern=\\w{4} \\w{6}\n"
        },
        {
            "input": {
                "actual": "some string",
                "pattern": "^\\d*$",
                "negated": true
            },
            "expected_output": "feature=feature9_pattern_match\nresult=matched\nnegated=true\nactual=\"some string\"\npattern=^\\d*$\n"
        }
    ]
}
```

---

### Feature 10: Containment Checks

**As a developer**, I want to verify that strings and collections contain a supplied member, so I can write membership expectations across common container shapes.

**Expected Behavior / Usage:**

The input is an object with `container`, `member`, and an optional `negated` flag. Containers may be strings, mappings, arrays, set tokens, or tuple tokens. On a match, stdout identifies the feature, states `result=matched`, and echoes the negation flag, container, and member in canonical JSON form.

**Test Cases:** `rcb_tests/public_test_cases/feature10_containment.json`

```json
{
    "description": "Membership containment checks",
    "cases": [
        {
            "input": {
                "container": "some string",
                "member": "tri"
            },
            "expected_output": "feature=feature10_containment\nresult=matched\nnegated=false\ncontainer=\"some string\"\nmember=\"tri\"\n"
        },
        {
            "input": {
                "container": "some string",
                "member": "foo",
                "negated": true
            },
            "expected_output": "feature=feature10_containment\nresult=matched\nnegated=true\ncontainer=\"some string\"\nmember=\"foo\"\n"
        },
        {
            "input": {
                "container": {
                    "name": "foobar"
                },
                "member": "name"
            },
            "expected_output": "feature=feature10_containment\nresult=matched\nnegated=false\ncontainer={\"name\":\"foobar\"}\nmember=\"name\"\n"
        }
    ]
}
```

---

### Feature 11: Callable Error Expectations

**As a developer**, I want to verify that invoking a callable produces a specified domain-level error signal, so I can test expected exceptional control flow.

**Expected Behavior / Usage:**

The input is an object with `call_behavior` and `expected_error`. The adapter invokes a representative callable that either emits the requested signal or returns normally. On a match, stdout identifies the feature, states `result=matched`, echoes the expected neutral error category, and reports the observed signal without leaking host-language exception class names.

**Test Cases:** `rcb_tests/public_test_cases/feature11_exception_expectation.json`

```json
{
    "description": "Callable error expectation",
    "cases": [
        {
            "input": {
                "call_behavior": "system_exit",
                "expected_error": "system_exit"
            },
            "expected_output": "feature=feature11_exception_expectation\nresult=matched\nexpected_error=system_exit\nobserved_signal=system_exit\n"
        }
    ]
}
```

---

### Feature 12: Stable Value Representation

**As a developer**, I want to render values with deterministic ordering for mappings, so I can produce readable comparison output that is stable across insertion order.

**Expected Behavior / Usage:**

The input is an object with `value`. Lists render in order, mappings render with keys sorted, and nested mappings inside arrays are also sorted. Stdout identifies the feature and prints a single `representation` line containing the deterministic human-readable value representation.

**Test Cases:** `rcb_tests/public_test_cases/feature12_stable_representation.json`

```json
{
    "description": "Stable human-readable value representation",
    "cases": [
        {
            "input": {
                "value": [
                    "one",
                    "yeah"
                ]
            },
            "expected_output": "feature=feature12_stable_representation\n[a specific Python list representation example]\n"
        },
        {
            "input": {
                "value": {
                    "b": "d",
                    "a": "c"
                }
            },
            "expected_output": "feature=feature12_stable_representation\nrepresentation={'a': 'c', 'b': 'd'}\n"
        }
    ]
}
```

---

### Feature 13: Deep Structural Comparison

**As a developer**, I want to compare nested structures and report the first observable mismatch, so I can diagnose differences in dictionaries, arrays, tuples, and nested combinations.

**Expected Behavior / Usage:**

The input is an object with `actual` and `expected`. If the structures match deeply, stdout identifies the feature, states `result=matched`, and echoes both values. If they differ, stdout identifies the feature, emits `error=deep_mismatch`, prints a neutral summary of the first mismatch path or length/key problem, and echoes both original values as canonical JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature13_deep_comparison.json`

```json
{
    "description": "Deep structural comparison",
    "cases": [
        {
            "input": {
                "actual": {
                    "one": "yeah"
                },
                "expected": {
                    "one": "yeah"
                }
            },
            "expected_output": "feature=feature13_deep_comparison\nresult=matched\nactual={\"one\":\"yeah\"}\nexpected={\"one\":\"yeah\"}\n"
        },
        {
            "input": {
                "actual": {
                    "one": "yeah"
                },
                "expected": {
                    "one": "oops"
                }
            },
            "expected_output": "feature=feature13_deep_comparison\nerror=deep_mismatch\nsummary=X['one'] is 'yeah' whereas Y['one'] is 'oops'\nactual={\"one\":\"yeah\"}\nexpected={\"one\":\"oops\"}\n"
        },
        {
            "input": {
                "actual": [
                    "one",
                    "yeahs"
                ],
                "expected": [
                    "one",
                    "yeah"
                ]
            },
            "expected_output": "feature=feature13_deep_comparison\nerror=deep_mismatch\nsummary=X[1] is 'yeahs' whereas Y[1] is 'yeah'\nactual=[\"one\",\"yeahs\"]\nexpected=[\"one\",\"yeah\"]\n"
        }
    ]
}
```

---

### Feature 14: Scenario Context Lifecycle

**As a developer**, I want to run a scenario with setup data, teardown cleanup, and meaningful missing-variable errors, so I can share state across arranged test steps safely.

**Expected Behavior / Usage:**

The input is an object with `scenario`. Supported scenarios cover setup data visibility, teardown cleanup after execution, and missing context attribute diagnostics. Successful lifecycle scenarios print `result=matched` with observable state lines; missing attributes print `error=context_attribute_missing`, the missing attribute name, and the available names.

**Test Cases:** `rcb_tests/public_test_cases/feature14_context_lifecycle.json`

```json
{
    "description": "Scenario context lifecycle",
    "cases": [
        {
            "input": {
                "scenario": "setup_visible"
            },
            "expected_output": "feature=feature14_context_lifecycle\nresult=matched\ncontext_has_name=true\nname=John Resig\nfunction_name=check\n"
        },
        {
            "input": {
                "scenario": "teardown_runs"
            },
            "expected_output": "feature=feature14_context_lifecycle\nresult=matched\nmodified_after_run=false\n"
        }
    ]
}
```

---

### Feature 15: Context Actions and Dependencies

**As a developer**, I want to attach actions to a scenario context with provided variables and dependency checks, so I can compose reusable test actions with explicit data contracts.

**Expected Behavior / Usage:**

The input is an object with `scenario`. Supported scenarios cover dynamic provider names and dependency failure when a required provided variable has not been produced. Successful provider execution prints `result=matched` with provided values; dependency failure prints `error=action_dependency_missing`, the missing dependency, and the action name.

**Test Cases:** `rcb_tests/public_test_cases/feature15_context_actions.json`

```json
{
    "description": "Context action providers and dependencies",
    "cases": [
        {
            "input": {
                "scenario": "dynamic_provider"
            },
            "expected_output": "feature=feature15_context_actions\nresult=matched\n[dynamic variable assignments defined in the provider module]\n[dynamic variable assignments defined in the provider module]\n[dynamic variable assignments defined in the provider module]\n"
        },
        {
            "input": {
                "scenario": "dependency_missing"
            },
            "expected_output": "feature=feature15_context_actions\nerror=action_dependency_missing\ndependency=missing_value\naction=action_needing_value\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_equality.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_equality@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the escaping rules used in the text similarity validator
- reference the missing dependency mapping from the dependency resolver config
