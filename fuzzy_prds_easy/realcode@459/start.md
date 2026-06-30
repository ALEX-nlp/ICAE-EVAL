## Product Requirement Document

# HTML Test-Report Generator — Render Test Results Into Browsable HTML Pages

## Project Goal

Build a reusable component that turns a project's structured test-run results into a small set of browsable HTML pages — a top-level summary index plus one detail page per test class — so developers and CI systems can review what passed and failed without parsing raw machine-readable result files by hand.

---

## Background & Problem

After a test run, results are typically available only as structured per-class records: each test class has a name, a set of roll-up counts (how many tests ran, and how many ended in [a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format], [a specific string literal for remaining tests — ask the PM for the exact output format], or were [a specific string literal for skipped tests — ask the PM for the exact output format]), and a list of individual test cases (each with a name, a duration, and a result). These records are accurate but not pleasant to read directly.

Without this component, every project hand-rolls its own way of turning those records into a human-readable view, leading to inconsistent layouts and ad-hoc, hard-to-style markup. This component defines one well-specified contract for rendering those records into HTML: a summary page that lists every class with its counts and a link to its detail page, and a per-class page that lists every individual test case with its outcome. Both pages share a common document skeleton (a doctype, a linked stylesheet, and a body) and a simple health-classification convention that lets a stylesheet visually distinguish healthy from unhealthy rows. The rendered markup is pretty-printed with two-space indentation and CRLF line endings.

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

### Feature 1: Summary Index Page

**As a developer**, I want a single index page that lists every test class with its roll-up counts and a link to its detail page, so I can see the overall health of a test run at a glance and drill into any class.

**Expected Behavior / Usage:**

The input is a request with an action of `summary`, an `output_dir` string, and a `classes` array. Each entry in `classes` has a `name` and a `summary` object holding four count fields as strings: `tests`, `[a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format]`, `[a specific string literal for remaining tests — ask the PM for the exact output format]`, and `[a specific string literal for skipped tests — ask the PM for the exact output format]`. The output is one HTML document, pretty-printed with two-space indentation and CRLF (`\r\n`) line endings, beginning with a `<!DOCTYPE html>` line. The document has a `<head>` containing a single `<link rel="stylesheet">` whose `href` is the `output_dir` joined with `css/style.css` (using `/` as the separator), and a `<body>` containing an `<h1>Test Summary</h1>` heading followed by a `<table>`.

The table opens with a header row of five `<th>` cells: `Class`, `Tests`, `Errors`, `Failures`, `Skipped`. Then comes one row per class, in the exact order supplied. Each class row contains a first `<td>` wrapping an `<a>` whose text is the class name and whose `href` is `./classes/<name>.html`, followed by four `<td>` cells showing the tests, [a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format], [a specific string literal for remaining tests — ask the PM for the exact output format], and [a specific string literal for skipped tests — ask the PM for the exact output format] counts. Each count is parsed as an integer; any value that is not a valid integer (including an empty string) is rendered as `0`.

Each class row carries a health style class chosen as follows: if [a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format], [a specific string literal for remaining tests — ask the PM for the exact output format], and [a specific string literal for skipped tests — ask the PM for the exact output format] are all zero, the row gets `class="success"`; if there is at least one failure, the row gets `class="failure"` (this takes precedence); otherwise — no [a specific string literal for remaining tests — ask the PM for the exact output format], but at least one error and/or skip — the row carries no `class` attribute at all. When the `classes` array is empty, the table contains only the header row.

**Test Cases:** `rcb_tests/public_test_cases/feature1_summary_index.json`

```json
{
    "description": "Render the top-level test summary index page from a list of test classes. Each class supplies its name and a summary of counts (total tests, [a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format], [a specific string literal for remaining tests — ask the PM for the exact output format], [a specific string literal for skipped tests — ask the PM for the exact output format]). The page is an HTML document with a doctype, a head linking a stylesheet whose href is the configured output directory joined with css/style.css, and a body containing an 'Test Summary' heading and a table. The table has a header row (Class, Tests, Errors, Failures, Skipped) followed by one row per class, in the given order. Each class row links to that class's detail page under ./classes/<name>.html and shows the four counts. Count fields that are not parseable integers are rendered as 0. A row is marked with a 'success' style class when [a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format], [a specific string literal for remaining tests — ask the PM for the exact output format] and [a specific string literal for skipped tests — ask the PM for the exact output format] are all zero; it is marked 'failure' when there is at least one failure; otherwise (no [a specific string literal for remaining tests — ask the PM for the exact output format] but some [a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format] and/or [a specific string literal for skipped tests — ask the PM for the exact output format]) the row carries no style class. Lines are CRLF-terminated.",
    "cases": [
        {
            "input": {
                "action": "summary",
                "output_dir": "report-out",
                "classes": [
                    {"name": "OrderProcessorTest", "summary": {"tests": "2", "[a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format]": "0", "[a specific string literal for remaining tests — ask the PM for the exact output format]": "0", "[a specific string literal for skipped tests — ask the PM for the exact output format]": "0"}},
                    {"name": "InventoryServiceTest", "summary": {"tests": "3", "[a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format]": "0", "[a specific string literal for remaining tests — ask the PM for the exact output format]": "0", "[a specific string literal for skipped tests — ask the PM for the exact output format]": "0"}}
                ]
            },
            "expected_output": "<!DOCTYPE html>\r\n<html>\r\n  <head>\r\n    <link rel=\"stylesheet\" href=\"report-out/css/style.css\" />\r\n  </head>\r\n  <body>\r\n    <h1>Test Summary</h1>\r\n    <table>\r\n      <tr>\r\n        <th>Class</th>\r\n        <th>Tests</th>\r\n        <th>Errors</th>\r\n        <th>Failures</th>\r\n        <th>Skipped</th>\r\n      </tr>\r\n      <tr class=\"success\">\r\n        <td>\r\n          <a href=\"./classes/OrderProcessorTest.html\">OrderProcessorTest</a>\r\n        </td>\r\n        <td>2</td>\r\n        <td>0</td>\r\n        <td>0</td>\r\n        <td>0</td>\r\n      </tr>\r\n      <tr class=\"success\">\r\n        <td>\r\n          <a href=\"./classes/InventoryServiceTest.html\">InventoryServiceTest</a>\r\n        </td>\r\n        <td>3</td>\r\n        <td>0</td>\r\n        <td>0</td>\r\n        <td>0</td>\r\n      </tr>\r\n    </table>\r\n  </body>\r\n</html>\r\n"
        },
        {
            "input": {
                "action": "summary",
                "output_dir": "report-out",
                "classes": [
                    {"name": "PaymentTest", "summary": {"tests": "5", "[a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format]": "0", "[a specific string literal for remaining tests — ask the PM for the exact output format]": "2", "[a specific string literal for skipped tests — ask the PM for the exact output format]": "1"}},
                    {"name": "NetworkTest", "summary": {"tests": "4", "[a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format]": "1", "[a specific string literal for remaining tests — ask the PM for the exact output format]": "0", "[a specific string literal for skipped tests — ask the PM for the exact output format]": "0"}},
                    {"name": "FlakyTest", "summary": {"tests": "4", "[a specific string literal for render [a specific string literal for remaining tests — ask the PM for the exact output format] — ask the PM for the exact error message format]": "0", "[a specific string literal for remaining tests — ask the PM for the exact output format]": "0", "[a specific string literal for skipped tests — ask the PM for the exact output format]": "2"}}
                ]
            },
            "expected_output": "<!DOCTYPE html>\r\n<html>\r\n  <head>\r\n    <link rel=\"stylesheet\" href=\"report-out/css/style.css\" />\r\n  </head>\r\n  <body>\r\n    <h1>Test Summary</h1>\r\n    <table>\r\n      <tr>\r\n        <th>Class</th>\r\n        <th>Tests</th>\r\n        <th>Errors</th>\r\n        <th>Failures</th>\r\n        <th>Skipped</th>\r\n      </tr>\r\n      <tr class=\"failure\">\r\n        <td>\r\n          <a href=\"./classes/PaymentTest.html\">PaymentTest</a>\r\n        </td>\r\n        <td>5</td>\r\n        <td>0</td>\r\n        <td>2</td>\r\n        <td>1</td>\r\n      </tr>\r\n      <tr>\r\n        <td>\r\n          <a href=\"./classes/NetworkTest.html\">NetworkTest</a>\r\n        </td>\r\n        <td>4</td>\r\n        <td>1</td>\r\n        <td>0</td>\r\n        <td>0</td>\r\n      </tr>\r\n      <tr>\r\n        <td>\r\n          <a href=\"./classes/FlakyTest.html\">FlakyTest</a>\r\n        </td>\r\n        <td>4</td>\r\n        <td>0</td>\r\n        <td>0</td>\r\n        <td>2</td>\r\n      </tr>\r\n    </table>\r\n  </body>\r\n</html>\r\n"
        }
    ]
}
```

---

### Feature 2: Per-Class Detail Page

**As a developer**, I want a detail page for one test class that lists every individual test case with its duration and outcome, so I can investigate exactly which tests in a class behaved how.

**Expected Behavior / Usage:**

The input is a request with an action of `class`, an `output_dir` string, a `homepage` string, and a `class` object. The `class` object has a `name` and a `testcases` array, where each test case has a `name`, a `duration`, and a `result` (the result is free text such as `Passed` or `Failed`). The output is one HTML document, pretty-printed with two-space indentation and CRLF (`\r\n`) line endings, beginning with a `<!DOCTYPE html>` line. As with the summary page, the `<head>` contains a single `<link rel="stylesheet">` whose `href` is the `output_dir` joined with `css/style.css`.

The `<body>` contains an `<h1>` reading `Class <name>`, then an `<a>` whose text is `Home` and whose `href` is the supplied `homepage` string, then a `<table>`. The table opens with a header row of three `<th>` cells: `Test`, `Duration`, `Result`. Then comes one row per test case, in the exact order supplied; each row has three `<td>` cells holding the test name, the duration, and the result text verbatim. Each row carries a health style class: a result of exactly `Passed` yields `class="success"`, and any other result value yields `class="failure"`. When the `testcases` array is empty, the table contains only the header row.

**Test Cases:** `rcb_tests/public_test_cases/feature2_class_detail.json`

```json
{
    "description": "Render a per-class detail page from a single test class and its list of test cases. The page is an HTML document with a doctype, a head linking a stylesheet whose href is the configured output directory joined with css/style.css, and a body that contains a heading reading 'Class <name>', a 'Home' link pointing at the supplied homepage path, and a results table. The table has a header row (Test, Duration, Result) followed by one row per test case, in the given order, showing the test name, its duration and its result text verbatim. A row is marked with a 'success' style class when the result text is exactly 'Passed'; any other result text marks the row 'failure'. Lines are CRLF-terminated.",
    "cases": [
        {
            "input": {
                "action": "class",
                "output_dir": "report-out",
                "homepage": "../index.html",
                "class": {
                    "name": "OrderProcessorTest",
                    "testcases": [
                        {"name": "accepts a valid order", "duration": "0.012", "result": "Passed"},
                        {"name": "rejects an empty cart", "duration": "0.004", "result": "Passed"}
                    ]
                }
            },
            "expected_output": "<!DOCTYPE html>\r\n<html>\r\n  <head>\r\n    <link rel=\"stylesheet\" href=\"report-out/css/style.css\" />\r\n  </head>\r\n  <body>\r\n    <h1>Class OrderProcessorTest</h1>\r\n    <a href=\"../index.html\">Home</a>\r\n    <table>\r\n      <tr>\r\n        <th>Test</th>\r\n        <th>Duration</th>\r\n        <th>Result</th>\r\n      </tr>\r\n      <tr class=\"success\">\r\n        <td>accepts a valid order</td>\r\n        <td>0.012</td>\r\n        <td>Passed</td>\r\n      </tr>\r\n      <tr class=\"success\">\r\n        <td>rejects an empty cart</td>\r\n        <td>0.004</td>\r\n        <td>Passed</td>\r\n      </tr>\r\n    </table>\r\n  </body>\r\n</html>\r\n"
        },
        {
            "input": {
                "action": "class",
                "output_dir": "report-out",
                "homepage": "../index.html",
                "class": {
                    "name": "PaymentTest",
                    "testcases": [
                        {"name": "charges the card", "duration": "0.030", "result": "Passed"},
                        {"name": "declines on insufficient funds", "duration": "0.015", "result": "Failed"},
                        {"name": "[a specific string literal for skipped tests — ask the PM for the exact output format] offline path", "duration": "0", "result": "Skipped"}
                    ]
                }
            },
            "expected_output": "<!DOCTYPE html>\r\n<html>\r\n  <head>\r\n    <link rel=\"stylesheet\" href=\"report-out/css/style.css\" />\r\n  </head>\r\n  <body>\r\n    <h1>Class PaymentTest</h1>\r\n    <a href=\"../index.html\">Home</a>\r\n    <table>\r\n      <tr>\r\n        <th>Test</th>\r\n        <th>Duration</th>\r\n        <th>Result</th>\r\n      </tr>\r\n      <tr class=\"success\">\r\n        <td>charges the card</td>\r\n        <td>0.030</td>\r\n        <td>Passed</td>\r\n      </tr>\r\n      <tr class=\"failure\">\r\n        <td>declines on insufficient funds</td>\r\n        <td>0.015</td>\r\n        <td>Failed</td>\r\n      </tr>\r\n      <tr class=\"failure\">\r\n        <td>[a specific string literal for skipped tests — ask the PM for the exact output format] offline path</td>\r\n        <td>0</td>\r\n        <td>Skipped</td>\r\n      </tr>\r\n    </table>\r\n  </body>\r\n</html>\r\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core rendering logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing, modelling the test-result records (a class name, its roll-up counts, and its per-test-case outcomes) as plain domain objects and producing the report markup from them.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the rendered HTML document to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `summary` renders the index page from `output_dir` plus a `classes` array; `class` renders a single class's detail page from `output_dir`, a `homepage` link target, and a `class` object. Output markup is pretty-printed with two-space indentation and CRLF line endings, begins with `<!DOCTYPE html>`, and omits any XML declaration.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same class naming pattern as the layout module
