## Product Requirement Document

# CVE Data Normalization Utilities — CPE/CWE Parsing and Vendor Indexing

## Project Goal

Build a small set of pure data-normalization utilities for a vulnerability-tracking system, so developers can turn raw vulnerability feed documents into clean, deduplicated, query-friendly structures (vendor/product mappings, flat lookup tokens, distinct weakness identifiers, and index buckets) without re-implementing the same parsing and de-duplication logic in every consumer.

---

## Background & Problem

Vulnerability feeds describe affected software using standardized component identifiers and attach weakness classifications and other metadata. The raw documents are deeply nested, contain duplicates, and embed the interesting fields inside variable-depth structures. Consumers (search pages, change detectors, subscription filters) all need the same derived shapes: which vendors and products are affected, a flat list of tokens to index or match against, the unique set of weakness identifiers, and a stable alphabet for grouping vendors in a directory view.

Without a shared utility layer, every consumer re-writes the same extraction, de-duplication, and flattening code, producing subtle inconsistencies (different handling of duplicates, different token formats). This library centralizes that logic behind a few well-defined, side-effect-free functions whose inputs and outputs are fully specified below.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic function calls to the core domain.

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

### Feature 1: Extract Vendor/Product Mapping From A Configuration Document

**As a developer**, I want to derive which vendors and products are affected by a vulnerability from its raw configuration document, so I can store and query the affected software without re-parsing nested feed data everywhere.

**Expected Behavior / Usage:**

The input is a request whose `conf` field holds a vulnerability configuration document (an arbitrary nested object). Embedded anywhere within it, at any nesting depth, are zero or more standardized component identifier strings under the key `cpe23Uri`. Each such identifier follows the colon-delimited CPE 2.3 format `cpe:2.3:<part>:<vendor>:<product>:<version>:...`; the vendor is the 4th colon-separated field and the product is the 5th (zero-based indices 3 and 4). The utility gathers every `cpe23Uri` value found in the document, reads the `(vendor, product)` pair from each, removes duplicate pairs, and produces a mapping from each vendor to the list of its distinct products. A document containing no identifiers (including an empty object) yields an empty mapping. The rendered output is canonical JSON: object keys (vendors) are sorted, and each vendor's product array is sorted; an empty mapping renders as `{}`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_convert_cpes.json`

```json
{
    "description": "Extract the vulnerable software identifiers from a vulnerability configuration document. The document embeds one or more standardized component URIs (the CPE 2.3 colon-delimited format) at arbitrary nesting depths under a fixed key. From each URI the vendor and product tokens (the 4th and 5th colon-separated fields) are read, duplicate vendor/product pairs are collapsed, and the result is a mapping from each vendor to the list of its distinct products. An empty document yields an empty mapping.",
    "cases": [
        {
            "input": {"action": "convert_cpes", "conf": {}},
            "expected_output": "{}\n"
        },
        {
            "input": {
                "action": "convert_cpes",
                "conf": {
                    "configurations": {
                        "CVE_data_version": "4.0",
                        "nodes": [
                            {
                                "operator": "OR",
                                "cpe_match": [
                                    {"vulnerable": true, "cpe23Uri": "cpe:2.3:a:foo:bar:2020:-:*:*:*:*:*:*"},
                                    {"vulnerable": true, "cpe23Uri": "cpe:2.3:a:foo:baz:2000:-:*:*:*:*:*:*"},
                                    {"vulnerable": true, "cpe23Uri": "cpe:2.3:a:bar:baz:2000:-:*:*:*:*:*:*"}
                                ]
                            }
                        ]
                    }
                }
            },
            "expected_output": "{\"bar\": [\"baz\"], \"foo\": [\"bar\", \"baz\"]}\n"
        }
    ]
}
```

---

### Feature 2: Flatten A Vendor/Product Mapping Into Lookup Tokens

**As a developer**, I want to turn a nested vendor→products mapping into a single flat list of tokens, so I can store affected software as an indexable, matchable token list for subscriptions and search.

**Expected Behavior / Usage:**

The input is a request whose `vendors` field holds a mapping from vendor name to a list of product names. The utility produces a single flat ordered list of string tokens. For each vendor, in the order the vendors appear in the mapping, it first appends the bare vendor token; then, for each of that vendor's products in the given order, it appends a combined token formed by joining the vendor and product with the fixed [a specific token joining strategy] string `$PRODUCT$` (i.e. `<vendor>$PRODUCT$<product>`). An empty mapping yields an empty list. The rendered output is the resulting list as canonical JSON, preserving order; an empty list renders as `[]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_flatten_vendors.json`

```json
{
    "description": "Flatten a mapping of vendors to their products into a single ordered token list. For each vendor, first emit the vendor token, then emit one combined token per product formed by joining the vendor and product with a fixed [a specific token joining strategy] string. Vendors are processed in the order they appear in the mapping, and each vendor's products are processed in the given order. An empty mapping yields an empty list.",
    "cases": [
        {
            "input": {"action": "flatten_vendors", "vendors": {"foo": ["bar"]}},
            "expected_output": "[\"foo\", \"foo$PRODUCT$bar\"]\n"
        },
        {
            "input": {"action": "flatten_vendors", "vendors": {"foo": ["bar", "baz"], "bar": ["baz"]}},
            "expected_output": "[\"foo\", \"foo$PRODUCT$bar\", \"foo$PRODUCT$baz\", \"bar\", \"bar$PRODUCT$baz\"]\n"
        }
    ]
}
```

---

### Feature 3: Deduplicate Weakness Identifiers From Problem Entries

**As a developer**, I want the distinct set of weakness identifiers attached to a vulnerability, so I can classify it without storing duplicate classifications.

**Expected Behavior / Usage:**

The input is a request whose `problems` field holds a list of problem-entry objects. Each entry carries a `value` field holding a weakness identifier string (such as `CWE-732`), possibly alongside other fields (e.g. a language tag) that are ignored. The utility returns the set of distinct `value` strings, collapsing any duplicates. An empty input list yields an empty result. The rendered output is the distinct identifiers as a canonical JSON array, sorted ascending; an empty result renders as `[]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_get_cwes.json`

```json
{
    "description": "Collect the distinct weakness identifiers from a list of problem entries. Each entry is an object carrying a value field holding the identifier string (alongside other ignored fields such as a language tag). The result is the set of unique identifier values, with duplicates collapsed. An empty input list yields an empty result.",
    "cases": [
        {
            "input": {
                "action": "get_cwes",
                "problems": [
                    {"lang": "en", "value": "CWE-732"},
                    {"lang": "en", "value": "CWE-732"},
                    {"lang": "en", "value": "CWE-532"}
                ]
            },
            "expected_output": "[\"CWE-532\", \"CWE-732\"]\n"
        },
        {
            "input": {"action": "get_cwes", "problems": []},
            "expected_output": "[]\n"
        }
    ]
}
```

---

### Feature 4: Enumerate Vendor Index Letters

**As a developer**, I want the fixed alphabet of buckets used to group vendors in a directory listing, so the navigation index is consistent everywhere it is rendered.

**Expected Behavior / Usage:**

The input is a request with no parameters. The utility returns a fixed ordered sequence of single-character bucket labels: the 26 lowercase Latin letters `a`–`z` in order, then the at-sign `@`, then the ten decimal digits `0`–`9` in ascending order. The rendered output is these characters concatenated into one string on a single line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_vendors_letters.json`

```json
{
    "description": "Produce the fixed sequence of index letters used to bucket vendors alphabetically. The sequence is the 26 lowercase Latin letters in order, followed by an at-sign, followed by the ten decimal digits in ascending order. The output is these characters concatenated into a single string. The request carries no parameters.",
    "cases": [
        {
            "input": {"action": "get_vendors_letters"},
            "expected_output": "abcdefghijklmnopqrstuvwxyz@0123456789\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the four utilities described above as pure, side-effect-free functions over plain data structures. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `convert_cpes` (uses `conf`), `flatten_vendors` (uses `vendors`), `get_cwes` (uses `problems`), and `get_vendors_letters` (no parameters). Structured results are rendered as canonical JSON: mappings have sorted keys and sorted value arrays; deduplicated identifier lists are sorted ascending; the flattened token list preserves order. Any unexpected failure must be rendered as a neutral `error=<category>` line rather than leaking a host-language traceback.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the standard error line format defined in the core modules
- adhere to the insertion order policy established in the configuration loader
