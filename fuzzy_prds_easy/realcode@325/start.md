## Product Requirement Document

# Test Code Linting Adapter - Black-Box Rules for Test Quality

## Project Goal

Build a linting library and execution adapter for JavaScript-style test source code that allows developers to detect unsafe, unclear, or non-portable test patterns without manually reviewing every test file.

---

## Background & Problem

Without this library, developers are forced to rely on convention and manual code review to catch skipped tests, focused tests, empty assertions, misplaced assertions, malformed titles, brittle snapshot usage, and unclear matcher forms. This leads to silent test gaps, accidental partial test runs, repetitive review comments, and inconsistent test style across a codebase.

With this library, developers provide source text and a set of enabled checks to a deterministic linting engine. The engine returns structured diagnostics and, when requested and supported, fixed source text for style-preserving rewrites.

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

### Feature 1: Disabled and Pending Test Detection

**As a developer**, I want to identify test declarations that are skipped, disabled, missing executable bodies, or explicitly pending, so I can prevent incomplete or intentionally suppressed tests from being committed.

**Expected Behavior / Usage:**

The adapter accepts source text plus a rules object enabling the disabled-test check. It reports each disabled suite, disabled case, missing test function, or pending marker as structured lines. Clean runnable tests produce `[a specific prefix string — ask the PM for the exact format requested]=0`. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature1_disabled_and_pending_tests.json`

```json
{
    "description": "Flags declarations and calls that intentionally disable tests or leave pending placeholders.",
    "cases": [
        {
            "input": {
                "source": "it.skip(\"skips\", () => {})",
                "rules": {
                    "no-disabled-tests": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-disabled-tests\nmessage0.text=Skipped test\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "describe.skip(\"suite\", () => {})",
                "rules": {
                    "no-disabled-tests": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-disabled-tests\nmessage0.text=Skipped test suite\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        }
    ]
}
```

---

### Feature 2: Focused Test Detection

**As a developer**, I want to identify focused suites and test cases, so I can ensure a committed test run does not execute only a narrow subset.

**Expected Behavior / Usage:**

The adapter accepts source text plus a rules object enabling the focused-test check. It reports focused aliases and `.only` chains with rule identity, message text, location, and severity. Non-focused declarations produce `[a specific prefix string — ask the PM for the exact format requested]=0`. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature2_focused_tests.json`

```json
{
    "description": "Flags focused test declarations so committed suites do not run only a selected subset.",
    "cases": [
        {
            "input": {
                "source": "fit(\"focused\", () => {})",
                "rules": {
                    "no-focused-tests": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-focused-tests\nmessage0.text=Unexpected focused test.\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "describe.only(\"suite\", () => {})",
                "rules": {
                    "no-focused-tests": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-focused-tests\nmessage0.text=Unexpected focused test.\nmessage0.line=1\nmessage0.column=10\nmessage0.severity=2\n"
        }
    ]
}
```

---

### Feature 3: Assertion Presence Checking

**As a developer**, I want to verify that each test body contains a recognized assertion, so I can catch empty tests that can pass without checking behavior.

**Expected Behavior / Usage:**

The adapter accepts source text plus a rules object that may include recognized assertion helper names. It treats configured helper calls and supported wildcard patterns as assertions. Tests with at least one recognized assertion produce `[a specific prefix string — ask the PM for the exact format requested]=0`; tests without one produce a structured diagnostic. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature3_assertion_presence.json`

```json
{
    "description": "Checks test bodies for recognized assertion calls, including configured assertion helper names and wildcard patterns.",
    "cases": [
        {
            "input": {
                "source": "it(\"passes\", () => expect(true).toBeDefined())",
                "rules": {
                    "expect-expect": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=0\n"
        },
        {
            "input": {
                "source": "it(\"fails\", () => {});",
                "rules": {
                    "expect-expect": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/expect-expect\nmessage0.text=Test has no assertions\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        }
    ]
}
```

---

### Feature 4: Assertion Placement Checking

**As a developer**, I want to detect assertion calls outside test bodies or inside conditional execution paths, so I can avoid assertions that are skipped by control flow or detached from a test case.

**Expected Behavior / Usage:**

The adapter accepts source text plus placement-related rule configuration. Standalone assertions outside valid test blocks are reported. Assertions guarded by conditions, switch branches, logical branches, or catch blocks are reported by the conditional-assertion check. Valid assertions directly in test bodies produce `[a specific prefix string — ask the PM for the exact format requested]=0`. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature4_expect_placement.json`

```json
{
    "description": "Flags assertions that appear outside valid test contexts or inside conditional control flow.",
    "cases": [
        {
            "input": {
                "source": "expect(true).toBe(false)",
                "rules": {
                    "no-standalone-expect": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-standalone-expect\nmessage0.text=Expect must be inside of a test block.\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "it(\"case\", () => expect(true).toBe(true))",
                "rules": {
                    "no-standalone-expect": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=0\n"
        }
    ]
}
```

---

### Feature 5: Assertion Shape and Promise Validation

**As a developer**, I want to validate assertion call shape and promise assertion handling, so I can ensure asynchronous checks are actually awaited or returned and assertion calls have useful operands.

**Expected Behavior / Usage:**

The adapter accepts source text plus rules for assertion arity and promise chains. It reports missing assertion operands, missing matcher calls, unreturned promise chains containing assertions, and discouraged promise-resolution matcher usage. Valid synchronous or properly returned asynchronous assertions produce `[a specific prefix string — ask the PM for the exact format requested]=0`. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature5_expect_argument_and_promise_validation.json`

```json
{
    "description": "Validates assertion call arity and promise chains so asynchronous assertions are returned or awaited correctly.",
    "cases": [
        {
            "input": {
                "source": "it(\"case\", () => { expect() })",
                "rules": {
                    "valid-expect": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=2\nmessage0.rule=jest/valid-expect\nmessage0.text=Expect must have a corresponding matcher call.\nmessage0.line=1\nmessage0.column=20\nmessage0.severity=2\nmessage1.rule=jest/valid-expect\nmessage1.text=Expect requires at least 1 argument.\nmessage1.line=1\nmessage1.column=26\nmessage1.severity=2\n"
        },
        {
            "input": {
                "source": "it(\"case\", () => { expect(1).toBe(1) })",
                "rules": {
                    "valid-expect": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=0\n"
        }
    ]
}
```

---

### Feature 6: Suite and Case Title Validation

**As a developer**, I want to validate suite and test titles, so I can keep test reports readable and enforce naming conventions.

**Expected Behavior / Usage:**

The adapter accepts source text plus title-related rules and options. It reports uppercase starts when lowercase titles are required, empty titles, accidental leading or trailing spaces, non-string titles, and configured disallowed words. Titles satisfying the active rules produce `[a specific prefix string — ask the PM for the exact format requested]=0`. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature6_title_validation.json`

```json
{
    "description": "Validates suite and case titles for string literals, non-empty text, accidental spacing, disallowed words, and casing.",
    "cases": [
        {
            "input": {
                "source": "describe(\"FOO\", () => {})",
                "rules": {
                    "lowercase-name": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/lowercase-name\nmessage0.text=`describe`s should begin with lowercase\nmessage0.line=1\nmessage0.column=10\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "describe(\"foo\", () => {})",
                "rules": {
                    "lowercase-name": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=0\n"
        }
    ]
}
```

---

### Feature 7: Matcher Style Normalization

**As a developer**, I want to replace unclear matcher forms with canonical matcher expressions, so I can make assertions easier to read and more consistent.

**Expected Behavior / Usage:**

The adapter accepts source text, style rules, and `fix: true`. It prints an `output=` line containing the fixed source when a fix is available, followed by structured diagnostics. Supported style fixes include alias matcher replacement, null and undefined matcher specialization, containment matcher conversion, and length matcher conversion. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature7_matcher_style_fixes.json`

```json
{
    "description": "Detects matcher expressions that should use clearer canonical matcher forms and provides fixed source when available.",
    "cases": [
        {
            "input": {
                "source": "expect(fn).toBeCalled()",
                "rules": {
                    "no-alias-methods": "error"
                },
                "fix": true
            },
            "expected_output": "output=expect(fn).toHaveBeenCalled()\n[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-alias-methods\nmessage0.text=Replace toBeCalled() with its canonical name of toHaveBeenCalled()\nmessage0.line=1\nmessage0.column=12\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "expect(value).toBe(null)",
                "rules": {
                    "prefer-to-be-null": "error"
                },
                "fix": true
            },
            "expected_output": "output=expect(value).toBeNull()\n[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/prefer-to-be-null\nmessage0.text=Use toBeNull() instead\nmessage0.line=1\nmessage0.column=15\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "expect(value).toBe(undefined)",
                "rules": {
                    "prefer-to-be-undefined": "error"
                },
                "fix": true
            },
            "expected_output": "output=expect(value).toBeUndefined()\n[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/prefer-to-be-undefined\nmessage0.text=Use toBeUndefined() instead\nmessage0.line=1\nmessage0.column=15\nmessage0.severity=2\n"
        }
    ]
}
```

---

### Feature 8: Hook Structure Validation

**As a developer**, I want to validate lifecycle hook declarations, so I can keep test setup predictable and avoid duplicated setup or teardown.

**Expected Behavior / Usage:**

The adapter accepts source text plus hook-structure rules. It reports duplicate hooks in the same suite, forbidden hook usage, and hooks that appear after test cases when ordering is enforced. Correctly ordered non-duplicated hooks produce `[a specific prefix string — ask the PM for the exact format requested]=0`. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature8_hooks_structure.json`

```json
{
    "description": "Checks test lifecycle hooks for duplicate declarations, forbidden hook usage, and ordering before tests.",
    "cases": [
        {
            "input": {
                "source": "describe(\"suite\", () => { beforeEach(() => {}); beforeEach(() => {}) })",
                "rules": {
                    "no-duplicate-hooks": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-duplicate-hooks\nmessage0.text=Duplicate beforeEach in describe block\nmessage0.line=1\nmessage0.column=49\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "beforeEach(() => {})",
                "rules": {
                    "no-hooks": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-hooks\nmessage0.text=Unexpected 'beforeEach' hook\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        }
    ]
}
```

---

### Feature 9: Test Module Boundary Restrictions

**As a developer**, I want to detect imports, mock imports, exports, and legacy globals that should not appear in test files, so I can keep tests isolated and aligned with the test runtime environment.

**Expected Behavior / Usage:**

The adapter accepts module source text plus boundary rules. It reports direct imports from the test runtime package, manual imports from mock directories, exports from files that also contain tests, and legacy global usage. Source without the restricted pattern produces `[a specific prefix string — ask the PM for the exact format requested]=0`. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature9_import_export_restrictions.json`

```json
{
    "description": "Flags test-file imports, mock imports, exports, and legacy global names that should not appear in tests.",
    "cases": [
        {
            "input": {
                "source": "import jest from \"jest\"",
                "rules": {
                    "no-jest-import": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-jest-import\nmessage0.text=Jest is automatically in scope. Do not import \"jest\", as Jest doesn't export anything.\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "import mock from \"__mocks__/thing\"",
                "rules": {
                    "no-mocks-import": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-mocks-import\nmessage0.text=Mocks should not be manually imported from a __mocks__ directory. Instead use jest.mock and import from the original module path.\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        }
    ]
}
```

---

### Feature 10: Test Function Pattern Modernization

**As a developer**, I want to detect discouraged test function shapes and convert supported shorthand forms, so I can keep tests explicit and compatible with modern test-runner behavior.

**Expected Behavior / Usage:**

The adapter accepts source text plus rules for callback-style tests, returned values, todo shorthand, prefixed names, and preferred case function naming. Diagnostics are emitted for callback parameters and return statements. With `fix: true`, supported shorthand and naming conversions print the fixed source before diagnostics. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature10_test_function_patterns.json`

```json
{
    "description": "Detects callback-style tests, returned values from tests, prefixed test names, and deprecated test APIs.",
    "cases": [
        {
            "input": {
                "source": "it(\"case\", done => { done() })",
                "rules": {
                    "no-test-callback": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-test-callback\nmessage0.text=Illegal usage of test callback\nmessage0.line=1\nmessage0.column=12\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "it(\"case\", () => { return value })",
                "rules": {
                    "no-test-return-statement": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-test-return-statement\nmessage0.text=Jest tests should not return a value.\nmessage0.line=1\nmessage0.column=20\nmessage0.severity=2\n"
        }
    ]
}
```

---

### Feature 11: Snapshot Processing and Snapshot Assertion Limits

**As a developer**, I want to process snapshot-file text and enforce snapshot assertion style and size limits, so I can lint generated snapshots and inline snapshots without mixing unrelated diagnostics.

**Expected Behavior / Usage:**

For snapshot processing, the adapter accepts `mode: snapshot` plus an action. Preprocessing returns source parts, and postprocessing filters diagnostics to snapshot-specific rules. For source linting, snapshot rules report external snapshot usage that should be inline and inline snapshots that exceed configured size limits. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature11_snapshot_handling.json`

```json
{
    "description": "Processes snapshot files and flags snapshot assertions that are too large or should be inline.",
    "cases": [
        {
            "input": {
                "mode": "snapshot",
                "action": "preprocess",
                "source": "exports[`a`] = `hello`;"
            },
            "expected_output": "part0=exports[`a`] = `hello`;\n"
        },
        {
            "input": {
                "mode": "snapshot",
                "action": "postprocess",
                "[a specific prefix string — ask the PM for the exact format requested]": [
                    [
                        {
                            "ruleId": "no-console"
                        },
                        {
                            "ruleId": "jest/no-large-snapshots"
                        }
                    ]
                ]
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/no-large-snapshots\n"
        }
    ]
}
```

---

### Feature 12: Suite Wrapper and Throw Assertion Validation

**As a developer**, I want to validate top-level suite structure, suite callback shape, and thrown-error assertions, so I can make test organization and exception assertions explicit.

**Expected Behavior / Usage:**

The adapter accepts source text plus structural and thrown-error rules. It reports tests not wrapped in a suite when required, invalid suite declarations such as missing callbacks or async callbacks, and thrown-error assertions that do not specify an expected message. Valid wrapped suites produce `[a specific prefix string — ask the PM for the exact format requested]=0`. Output is plain stdout made of newline-delimited fields: optional fixed source as `output=...`, total diagnostic count as `[a specific prefix string — ask the PM for the exact format requested]=<number>`, and per-diagnostic fields for rule identity, message text, line, column, and severity.

**Test Cases:** `rcb_tests/public_test_cases/feature12_describe_and_throw_contracts.json`

```json
{
    "description": "Validates suite wrappers, describe callback shape, and thrown-error assertions that require expected [a specific prefix string — ask the PM for the exact format requested].",
    "cases": [
        {
            "input": {
                "source": "it(\"case\", () => {})",
                "rules": {
                    "require-top-level-describe": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=1\nmessage0.rule=jest/require-top-level-describe\nmessage0.text=All test cases must be wrapped in a describe block.\nmessage0.line=1\nmessage0.column=1\nmessage0.severity=2\n"
        },
        {
            "input": {
                "source": "describe(\"suite\", () => { it(\"case\", () => {}) })",
                "rules": {
                    "require-top-level-describe": "error"
                }
            },
            "expected_output": "[a specific prefix string — ask the PM for the exact format requested]=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_disabled_and_pending_tests.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_disabled_and_pending_tests@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
