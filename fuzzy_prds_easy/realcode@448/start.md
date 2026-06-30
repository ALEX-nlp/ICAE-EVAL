## Product Requirement Document

/testbed/start.md
# Interactive Data Table and License Utilities - Black-Box Behavior Contract

## Project Goal

Build a reusable interactive data-table toolkit with companion license-token utilities that allows developers to render, sort, filter, paginate, select, customize, and validate tabular experiences without hand-writing repetitive table state management or token encoding logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually implement row rendering, column interactions, filtering rules, pagination callbacks, selection state, visual customization hooks, and license-token encoding. This leads to duplicated UI logic, inconsistent behavior across tables, fragile edge-case handling, and error-prone credential checks.

With this library/tool, developers can provide ordinary data, configuration, and token inputs while the system produces observable table behavior and license results through stable contracts.

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

### Feature 1: Base64 Encoding

**As a developer**, I want to convert clear text into Base64 text, so I can transport or store text safely in an ASCII-compatible form.

**Expected Behavior / Usage:**

The adapter accepts an object containing `text`. It prints one line named `encoded` whose value is the Base64 representation of the original string. Unicode characters must be encoded through UTF-8 before Base64 conversion.

**Test Cases:** `rcb_tests/public_test_cases/feature1_base64_encode.json`

```json
{
    "description": "Encode clear text into the standard Base64 alphabet while preserving Unicode characters.",
    "cases": [
        {
            "input": {
                "text": "✓ à la mode"
            },
            "expected_output": "encoded=4pyTIMOgIGxhIG1vZGU=\n"
        }
    ]
}
```

---

### Feature 2: Base64 Decoding

**As a developer**, I want to recover clear text from Base64 text, so I can round-trip encoded data back into its original form.

**Expected Behavior / Usage:**

The adapter accepts an object containing `encoded_text`. It prints one line named `decoded` containing the decoded Unicode string.

**Test Cases:** `rcb_tests/public_test_cases/feature2_base64_decode.json`

```json
{
    "description": "Decode Base64 text back to its original Unicode string.",
    "cases": [
        {
            "input": {
                "encoded_text": "4pyTIMOgIGxhIG1vZGU="
            },
            "expected_output": "decoded=✓ à la mode\n"
        }
    ]
}
```

---

### Feature 3: MD5 Digest Generation

**As a developer**, I want to derive a stable MD5 digest from text, so I can compare or sign strings with a deterministic lowercase hexadecimal fingerprint.

**Expected Behavior / Usage:**

The adapter accepts an object containing `text`. It prints one line named `hash` containing the lowercase 32-character MD5 digest of that text.

**Test Cases:** `rcb_tests/public_test_cases/feature3_md5_hashing.json`

```json
{
    "description": "Hash arbitrary input text into a lowercase 32-character MD5 digest.",
    "cases": [
        {
            "input": {
                "text": "Je suis a la mode"
            },
            "expected_output": "[output a standardized 32-character lowercase hexadecimal digest]8a59b141a26e95b5020e04ed5d4877dd\n"
        }
    ]
}
```

---

### Feature 4: Signed License Token Generation

**As a developer**, I want to generate a signed token from an order identifier and expiry instant, so I can create a portable credential that can later be verified without additional state.

**Expected Behavior / Usage:**

The adapter accepts an object containing `order_number` and `expiry_timestamp`. It prints one line named `license` containing a token built from the encoded license payload prefixed by its digest.

**Test Cases:** `rcb_tests/public_test_cases/feature4_license_generation.json`

```json
{
    "description": "Create a signed license token from an order number and an expiry timestamp.",
    "cases": [
        {
            "input": {
                "order_number": "MUI-123",
                "expiry_timestamp": 1591723879062
            },
            "expected_output": "license=e34253b37166e7a4a85189b91b653e63T1JERVI6TVVJLTEyMyxFWFBJUlk9MTU5MTcyMzg3OTA2MixLRVlWRVJTSU9OPTE=\n"
        }
    ]
}
```

---

### Feature 5: License Verification

**As a developer**, I want to check a signed token against encoded release information, so I can distinguish valid, missing, invalid, expired, and release-information failures.

**Expected Behavior / Usage:**

The adapter accepts `release_info` and `license`. It prints `status=<Status>` for ordinary verification results. If release information cannot be decoded as a release timestamp, it prints the normalized line `error=release_info_invalid` rather than a host-language exception.

**Test Cases:** `rcb_tests/public_test_cases/feature5_license_verification.json`

```json
{
    "description": "Verify a signed license token against encoded release information and report a normalized status or release-information error.",
    "cases": [
        {
            "input": {
                "release_info": "X19SRUxFQVNFX0lORk9fXw==",
                "license": "e34253b37166e7a4a85189b91b653e63T1JERVI6TVVJLTEyMyxFWFBJUlk9MTU5MTcyMzg3OTA2MixLRVlWRVJTSU9OPTE="
            },
            "expected_output": "error=release_info_invalid\n"
        }
    ]
}
```

---

### Feature 6: Initial Row Rendering Order

**As a developer**, I want to render table rows in the supplied order, so I can preserve the caller’s data sequence when no table operation changes it.

**Expected Behavior / Usage:**

The adapter accepts row objects and column descriptors. It renders the table and prints the visible values in the first column as `visible_values`, separated by `|`, preserving input order.

**Test Cases:** `rcb_tests/public_test_cases/feature6_grid_initial_order.json`

```json
{
    "description": "Render rows in their supplied order when no sorting or filtering is applied.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "id": 10
                    },
                    {
                        "id": 0
                    },
                    {
                        "id": 5
                    }
                ],
                "columns": [
                    {
                        "field": "id"
                    }
                ]
            },
            "expected_output": "visible_values=10|0|5\n"
        }
    ]
}
```

---

### Feature 7.1: Client-Side Header Sorting

**As a developer**, I want to sort visible rows by activating a column header, so I can let users reorder data without server involvement.

**Expected Behavior / Usage:**

The adapter accepts a target column and a header click count. It renders the table, clicks the column header, and prints the visible first-column values before and after each click. Text columns sort ascending then descending; boolean columns follow the table’s built-in ordering.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_client_sorting.json`

```json
{
    "description": "Sort visible rows when a sortable column header is clicked, cycling through ascending and descending order.",
    "cases": [
        {
            "input": {
                "column": "brand",
                "click_count": 2
            },
            "expected_output": "initial=Nike|Adidas|Puma\nafter_1_click=Adidas|Nike|Puma\nafter_2_click=Puma|Nike|Adidas\n"
        }
    ]
}
```

---

### Feature 7.2: Server-Side Sorting Order Preservation

**As a developer**, I want to render server-provided row order without local resorting, so I can delegate ordering decisions to a remote data source.

**Expected Behavior / Usage:**

The adapter accepts an initial row list and an updated row list. In server-side sorting mode it prints first-column values before and after the update exactly in the order provided by the caller.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_server_sorting.json`

```json
{
    "description": "In server-side sorting mode, render rows exactly in the order supplied by the data source after updates.",
    "cases": [
        {
            "input": {
                "initial_rows": [
                    {
                        "id": 10
                    },
                    {
                        "id": 0
                    },
                    {
                        "id": 5
                    }
                ],
                "updated_rows": [
                    {
                        "id": 5
                    },
                    {
                        "id": 0
                    },
                    {
                        "id": 10
                    }
                ]
            },
            "expected_output": "initial_values=10|0|5\nupdated_values=5|0|10\n"
        }
    ]
}
```

---

### Feature 8.1: String Filtering

**As a developer**, I want to filter text columns with string conditions, so I can show only rows whose text matches the user’s condition.

**Expected Behavior / Usage:**

The adapter accepts a condition, a value, and optionally rows and a column. It prints `visible_values` for rows that remain after filtering. Matching is case-insensitive for equality-style comparisons, and punctuation used in the value is treated as literal text rather than as a pattern language.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_string_filtering.json`

```json
{
    "description": "Filter text columns with case-insensitive string conditions and treat pattern characters as literal input.",
    "cases": [
        {
            "input": {
                "condition": "contains",
                "value": "a"
            },
            "expected_output": "visible_values=Adidas|Puma\n"
        }
    ]
}
```

---

### Feature 8.2: Number Filtering

**As a developer**, I want to filter numeric values by comparison, so I can show numeric rows that satisfy equality or inequality conditions.

**Expected Behavior / Usage:**

The adapter accepts numeric rows, a comparison condition, and a comparison value. It prints formatted visible values for rows satisfying the comparison.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_number_filtering.json`

```json
{
    "description": "Filter numeric column values using equality and inequality comparisons.",
    "cases": [
        {
            "input": {
                "condition": ">=",
                "value": 1974,
                "rows": [
                    {
                        "year": 1984
                    },
                    {
                        "year": 1954
                    },
                    {
                        "year": 1974
                    }
                ]
            },
            "expected_output": "visible_values=1,984|1,974\n"
        }
    ]
}
```

---

### Feature 8.3: Date Filtering

**As a developer**, I want to filter date values by exact and relative date conditions, so I can show rows before, after, on, or not on a selected date.

**Expected Behavior / Usage:**

The adapter accepts date rows expressed as year, month index, and day, plus a date condition and comparison value. It prints formatted visible date values for rows that satisfy the condition.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_date_filtering.json`

```json
{
    "description": "Filter date values using exact-date and relative-date comparisons while displaying the surviving formatted dates.",
    "cases": [
        {
            "input": {
                "condition": "before",
                "value": "2001-01-01",
                "rows": [
                    {
                        "year": 2000,
                        "month_index": 11,
                        "day": 1
                    },
                    {
                        "year": 2001,
                        "month_index": 0,
                        "day": 1
                    },
                    {
                        "year": 2002,
                        "month_index": 0,
                        "day": 1
                    }
                ]
            },
            "expected_output": "visible_values=12/1/2000\n"
        }
    ]
}
```

---

### Feature 9.1: Paginated Visible Rows

**As a developer**, I want to render only the row slice for the requested page, so I can display large datasets one page at a time.

**Expected Behavior / Usage:**

The adapter accepts rows, a zero-based page number, and a page size. It prints first-column values for only the rows visible on that page.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_pagination_visible_page.json`

```json
{
    "description": "Render only the row slice for the requested page and page size.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "id": 0,
                        "brand": "Nike"
                    },
                    {
                        "id": 1,
                        "brand": "Adidas"
                    },
                    {
                        "id": 2,
                        "brand": "Puma"
                    }
                ],
                "page": 1,
                "page_size": 1
            },
            "expected_output": "visible_values=Adidas\n"
        }
    ]
}
```

---

### Feature 9.2: Pagination Control Events

**As a developer**, I want to report target page numbers when pagination controls are activated, so I can let controlled clients update page state explicitly.

**Expected Behavior / Usage:**

The adapter accepts rows and a current page. It activates next-page and previous-page controls, then prints the callback count and target page numbers reported by the table.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_pagination_events.json`

```json
{
    "description": "When pagination controls are activated in controlled mode, report the target page numbers through callbacks without changing the supplied page.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "id": 0,
                        "brand": "Nike"
                    },
                    {
                        "id": 1,
                        "brand": "Adidas"
                    },
                    {
                        "id": 2,
                        "brand": "Puma"
                    }
                ],
                "current_page": 1
            },
            "expected_output": "callback_count=2\nnext_page=2\nprevious_page=0\n"
        }
    ]
}
```

---

### Feature 10.1: Single Row Selection

**As a developer**, I want to select one row at a time from row clicks, so I can keep selection state unambiguous in single-selection tables.

**Expected Behavior / Usage:**

The adapter accepts rows and a sequence of clicked row indexes. It prints whether row 0 and row 1 are selected after each click. A modifier key does not turn single-selection mode into multi-selection.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_single_row_selection.json`

```json
{
    "description": "In single-selection mode, a row click selects that row and replaces the previous selection even when a modifier key is held.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "id": 0,
                        "brand": "Nike"
                    },
                    {
                        "id": 1,
                        "brand": "Adidas"
                    }
                ],
                "clicks": [
                    0,
                    1
                ]
            },
            "expected_output": "after_first_click=row0:yes|row1:no\nafter_second_click=row0:no|row1:yes\n"
        }
    ]
}
```

---

### Feature 10.2: Checkbox Selectability

**As a developer**, I want to disable checkboxes for rows that are not selectable, so I can prevent users from selecting rows disallowed by a row predicate.

**Expected Behavior / Usage:**

The adapter accepts rows and the only selectable row id. It prints whether each row checkbox is disabled.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_checkbox_selectability.json`

```json
{
    "description": "Disable a row selection checkbox when the row is not selectable according to the supplied row predicate.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "id": 0,
                        "brand": "Nike"
                    },
                    {
                        "id": 1,
                        "brand": "Adidas"
                    }
                ],
                "selectable_id": 0
            },
            "expected_output": "row0_checkbox_disabled=no\nrow1_checkbox_disabled=yes\n"
        }
    ]
}
```

---

### Feature 11: Custom Row Identity and Row Classes

**As a developer**, I want to identify rows with caller-supplied identity data and style rows from row values, so I can render datasets that do not use a built-in `id` field while exposing data-driven row styling.

**Expected Behavior / Usage:**

The adapter accepts rows, an age threshold, and a class name. It prints visible row identity values and whether each rendered row has the requested class.

**Test Cases:** `rcb_tests/public_test_cases/feature11_custom_row_identity.json`

```json
{
    "description": "Use a caller-provided row identity field for rendering and apply row classes derived from row data.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "clientId": "c1",
                        "first": "Mike",
                        "age": 11
                    },
                    {
                        "clientId": "c2",
                        "first": "Jack",
                        "age": 11
                    },
                    {
                        "clientId": "c3",
                        "first": "Mike",
                        "age": 20
                    }
                ],
                "age_threshold": 20,
                "class_name": "under-age"
            },
            "expected_output": "visible_values=c1|c2|c3\nrow0_under_age=yes\nrow1_under_age=yes\nrow2_under_age=no\n"
        }
    ]
}
```

---

### Feature 12: Cell and Header Class Application

**As a developer**, I want to attach caller-provided class names to body cells and headers, so I can support data-table customization through rendered class markers.

**Expected Behavior / Usage:**

The adapter accepts rows plus a body-cell class and a header class. It renders a one-column table and prints whether the first body cell and first header contain those class markers.

**Test Cases:** `rcb_tests/public_test_cases/feature12_cell_header_classes.json`

```json
{
    "description": "Attach caller-provided CSS class names to rendered body cells and column headers.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "id": 0,
                        "brand": "Nike"
                    }
                ],
                "cell_class": "cell-marker",
                "header_class": "header-marker"
            },
            "expected_output": "cell0_has_marker=yes\nheader0_has_marker=yes\n"
        }
    ]
}
```

---

### Feature 13: Toolbar Column Visibility

**As a developer**, I want to hide a column through the table toolbar, so I can let users control which columns are visible at runtime.

**Expected Behavior / Usage:**

The adapter accepts rows and a column to hide. It opens the column selector, toggles that column, and prints header text before and after the change.

**Test Cases:** `rcb_tests/public_test_cases/feature13_toolbar_column_visibility.json`

```json
{
    "description": "Use the toolbar column selector to hide a selected column and update visible header text.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "id": 0,
                        "brand": "Nike"
                    },
                    {
                        "id": 1,
                        "brand": "Adidas"
                    }
                ],
                "column_to_hide": "id"
            },
            "expected_output": "initial_headers=id|brand\nafter_hiding_id=brand\n"
        }
    ]
}
```

---

### Feature 14: Density-Based Sizing

**As a developer**, I want to scale rendered row and cell heights from a base row height, so I can allow compact or comfortable table density without changing the data model.

**Expected Behavior / Usage:**

The adapter accepts rows, a base row height, and a density setting. It prints the rendered maximum height style for a row and a cell after density scaling.

**Test Cases:** `rcb_tests/public_test_cases/feature14_density_sizing.json`

```json
{
    "description": "Apply density settings by scaling row and cell maximum heights from the supplied base row height.",
    "cases": [
        {
            "input": {
                "rows": [
                    {
                        "id": 0,
                        "brand": "Nike"
                    },
                    {
                        "id": 1,
                        "brand": "Adidas"
                    }
                ],
                "row_height": 30,
                "density": "compact"
            },
            "expected_output": "row_max_height=21px\ncell_max_height=21px\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- follow the proprietary signature encoding pattern defined in the security module
- implement the same window calculation logic used in the pagination controller
