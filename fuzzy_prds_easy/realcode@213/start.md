## Product Requirement Document

# Mobile Analytics Tracking Client - Event Payload and Utility Contract

## Project Goal

Build a mobile analytics tracking client that allows developers to construct tracking query payloads, ecommerce item payloads, custom metadata, checksum utilities, and bulk dispatch payloads without manually assembling URL query strings, JSON arrays, monetary strings, or paginated request batches[a specific separator character — ask the PM for the exact punctuation used in the final output]

---

## Background & Problem

Without this library/tool, developers are forced to manually maintain analytics request parameters, encode query strings, format prices, serialize ecommerce items, and group multiple events for dispatch[a specific separator character — ask the PM for the exact punctuation used in the final output] This leads to repetitive code, inconsistent wire formats, malformed JSON, and fragile request batching[a specific separator character — ask the PM for the exact punctuation used in the final output]

With this library/tool, application code can express tracking inputs as structured values and receive stable wire-format strings suitable for analytics collection endpoints[a specific separator character — ask the PM for the exact punctuation used in the final output]

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1[a specific separator character — ask the PM for the exact punctuation used in the final output] **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain[a specific separator character — ask the PM for the exact punctuation used in the final output]
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation[a specific separator character — ask the PM for the exact punctuation used in the final output]
   - **For complex systems:** If the project involves multiple distinct responsibilities (e[a specific separator character — ask the PM for the exact punctuation used in the final output]g[a specific separator character — ask the PM for the exact punctuation used in the final output], I/O routing, business rules, formatters), it MUST NOT be a single "god file"[a specific separator character — ask the PM for the exact punctuation used in the final output] You must output a clear, multi-file directory tree (`src/`, `tests/`, etc[a specific separator character — ask the PM for the exact punctuation used in the final output]) that reflects a production-grade repository[a specific separator character — ask the PM for the exact punctuation used in the final output]
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains[a specific separator character — ask the PM for the exact punctuation used in the final output]

2[a specific separator character — ask the PM for the exact punctuation used in the final output] **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system[a specific separator character — ask the PM for the exact punctuation used in the final output] The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing[a specific separator character — ask the PM for the exact punctuation used in the final output] The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain[a specific separator character — ask the PM for the exact punctuation used in the final output]

3[a specific separator character — ask the PM for the exact punctuation used in the final output] **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units[a specific separator character — ask the PM for the exact punctuation used in the final output]
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification[a specific separator character — ask the PM for the exact punctuation used in the final output]
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types[a specific separator character — ask the PM for the exact punctuation used in the final output]
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive[a specific separator character — ask the PM for the exact punctuation used in the final output]
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details[a specific separator character — ask the PM for the exact punctuation used in the final output]

4[a specific separator character — ask the PM for the exact punctuation used in the final output] **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity[a specific separator character — ask the PM for the exact punctuation used in the final output]
   - **Resilience:** The system must handle edge cases gracefully[a specific separator character — ask the PM for the exact punctuation used in the final output] Errors should be modeled properly (e[a specific separator character — ask the PM for the exact punctuation used in the final output]g[a specific separator character — ask the PM for the exact punctuation used in the final output], specific Exception types or Result/Monad patterns) rather than relying on generic faults[a specific separator character — ask the PM for the exact punctuation used in the final output]

---

## Core Features

### Feature 1: Price Formatting

**As a developer**, I want to convert integer minor-unit amounts into analytics-ready decimal strings, so I can send consistent monetary values in request payloads[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Expected Behavior / Usage:**

The input is an object with `feature` set to `price_formatting` and `amounts_cents` containing one or more integer amounts in minor units[a specific separator character — ask the PM for the exact punctuation used in the final output] For each amount, the output prints the original integer and a `price` line[a specific separator character — ask the PM for the exact punctuation used in the final output] The formatted price is the amount divided by 100 and rendered with exactly two fractional digits using `[a specific separator character — ask the PM for the exact punctuation used in the final output]` as the decimal separator[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Test Cases:** `rcb_tests/public_test_cases/feature1_price_formatting[a specific separator character — ask the PM for the exact punctuation used in the final output]json`

```json
{
  "description": "Formats integer minor-unit amounts into two-decimal major-unit monetary strings using a dot decimal separator[a specific separator character — ask the PM for the exact punctuation used in the final output]",
  "cases": [
    {
      "input": {"feature":"price_formatting","amounts_cents":[1000,3950,1,25034]},
      "expected_output": "amount_cents=1000\nprice=10[a specific separator character — ask the PM for the exact punctuation used in the final output]00\namount_cents=3950\nprice=39[a specific separator character — ask the PM for the exact punctuation used in the final output]50\namount_cents=1\nprice=0[a specific separator character — ask the PM for the exact punctuation used in the final output]01\namount_cents=25034\nprice=250[a specific separator character — ask the PM for the exact punctuation used in the final output]34\n"
    }
  ]
}
```

---

### Feature 2: Checksum Rendering

**As a developer**, I want checksum helpers that produce stable uppercase digest strings or explicit null output, so I can verify file-like identifiers without ambiguous formatting[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Expected Behavior / Usage:**

The input is an object with `feature` set to `md5_checksum`[a specific separator character — ask the PM for the exact punctuation used in the final output] A `mode` of `text` hashes the provided `value` and prints `checksum=<uppercase-md5>`[a specific separator character — ask the PM for the exact punctuation used in the final output] Inputs that do not represent hashable byte content, such as null byte arrays or directories, render `null` instead of throwing through the adapter[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Test Cases:** `rcb_tests/public_test_cases/feature2_checksum[a specific separator character — ask the PM for the exact punctuation used in the final output]json`

```json
{
  "description": "Calculates uppercase MD5 checksums for text-like inputs and returns null for inputs that cannot produce a checksum[a specific separator character — ask the PM for the exact punctuation used in the final output]",
  "cases": [
    {
      "input": {"feature":"md5_checksum","mode":"text","value":"foo"},
      "expected_output": "mode=text\nchecksum=ACBD18DB4CC2F85CEDEF654FCCC4A4D8\n"
    }
  ]
}
```

---

### Feature 3: Custom Variable JSON

**As a developer**, I want to serialize indexed custom name/value pairs as JSON, so I can attach structured custom metadata to analytics requests[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Expected Behavior / Usage:**

The input is an object with `feature` set to `custom_variables`, an `inherit` flag, optional `ancestor_variables`, and a `variables` array[a specific separator character — ask the PM for the exact punctuation used in the final output] Integer-indexed entries accept positive indexes with non-null name and value strings; invalid indexes are ignored[a specific separator character — ask the PM for the exact punctuation used in the final output] Array-form entries accept exactly two values; arrays of any other length are ignored[a specific separator character — ask the PM for the exact punctuation used in the final output] Names and values are JSON-escaped, inherited variables are copied into the new set, and an empty set renders `custom_variables_json=null`[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Test Cases:** `rcb_tests/public_test_cases/feature3_custom_variables[a specific separator character — ask the PM for the exact punctuation used in the final output]json`

```json
{
  "description": "Builds JSON for indexed custom name/value pairs, preserving valid inherited entries, escaping JSON characters, trimming overlong text, and ignoring invalid indexes or malformed value arrays[a specific separator character — ask the PM for the exact punctuation used in the final output]",
  "cases": [
    {
      "input": {"feature":"custom_variables","inherit":false,"variables":[{"index":1,"name":"name","value":"value"},{"index":2,"name":"name2","value":"uńicódę"}]},
      "expected_output": "custom_variables_json={\"1\":[\"name\",\"value\"],\"2\":[\"name2\",\"uńicódę\"]}\n"
    },
    {
      "input": {"feature":"custom_variables","inherit":false,"variables":[{"index":1,"name":"name","value":"value"},{"index":-1,"name":"name-1","value":"value"}]},
      "expected_output": "custom_variables_json={\"1\":[\"name\",\"value\"]}\n"
    }
  ]
}
```

---

### Feature 4: Custom Dimension Mapping

**As a developer**, I want custom dimension values converted into numbered request fields, so I can attach flat analytics metadata while ignoring invalid or empty values[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Expected Behavior / Usage:**

The input is an object with `feature` set to `custom_dimensions` and a `dimensions` array of index/value operations[a specific separator character — ask the PM for the exact punctuation used in the final output] Positive indexes with non-empty values produce fields named `dimension<index>`[a specific separator character — ask the PM for the exact punctuation used in the final output] Index zero is ignored, empty strings are ignored, and setting an existing dimension to null removes it[a specific separator character — ask the PM for the exact punctuation used in the final output] Values longer than the accepted maximum are truncated before output[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Test Cases:** `rcb_tests/public_test_cases/feature4_custom_dimensions[a specific separator character — ask the PM for the exact punctuation used in the final output]json`

```json
{
  "description": "Converts positive, non-empty custom dimension values into numbered output fields, removes null values, ignores zero indexes, and trims overlong values[a specific separator character — ask the PM for the exact punctuation used in the final output]",
  "cases": [
    {
      "input": {"feature":"custom_dimensions","dimensions":[{"index":0,"value":"foo"},{"index":1,"value":"foo"},{"index":2,"value":"bar"},{"index":3,"value":"empty"},{"index":3,"value":null},{"index":4,"value":""}]},
      "expected_output": "dimension_count=2\ndimension1=foo\ndimension2=bar\n"
    }
  ]
}
```

---

### Feature 5: Ecommerce Item JSON

**As a developer**, I want ecommerce products serialized as analytics item arrays, so I can include carts and orders in tracking payloads[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Expected Behavior / Usage:**

The input is an object with `feature` set to `ecommerce_items` and an `operations` array[a specific separator character — ask the PM for the exact punctuation used in the final output] `add` operations create an item array beginning with `sku`, followed by optional `name`, `category`, formatted `price_cents`, and `quantity` when present[a specific separator character — ask the PM for the exact punctuation used in the final output] `remove` deletes an item by SKU and `clear` removes all items[a specific separator character — ask the PM for the exact punctuation used in the final output] The output is a single JSON array line named `items_json`[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Test Cases:** `rcb_tests/public_test_cases/feature5_ecommerce_items[a specific separator character — ask the PM for the exact punctuation used in the final output]json`

```json
{
  "description": "Serializes ecommerce item collections as JSON arrays, formatting prices from cents and supporting item removal and clearing[a specific separator character — ask the PM for the exact punctuation used in the final output]",
  "cases": [
    {
      "input": {"feature":"ecommerce_items","operations":[]},
      "expected_output": "items_json=[]\n"
    },
    {
      "input": {"feature":"ecommerce_items","operations":[{"action":"add","sku":"fake_sku","name":"fake_product","category":"fake_category","price_cents":200,"quantity":2},{"action":"add","sku":"fake_sku_2","name":"fake_product_2","category":"fake_category_2","price_cents":400,"quantity":3},{"action":"clear"}]},
      "expected_output": "items_json=[]\n"
    }
  ]
}
```

---

### Feature 6: Tracking Parameter Mutation

**As a developer**, I want to build analytics query parameter maps with overwrite, remove, first-write-wins, and copy semantics, so I can prepare event payloads without manipulating raw maps[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Expected Behavior / Usage:**

The input is an object with `feature` set to `track_parameters`[a specific separator character — ask the PM for the exact punctuation used in the final output] Operations contain `method`, public wire `param`, and `value`[a specific separator character — ask the PM for the exact punctuation used in the final output] `set` stores non-empty values as strings and removes a parameter when the value is null[a specific separator character — ask the PM for the exact punctuation used in the final output] `try_set` stores a value only when the parameter is not already present[a specific separator character — ask the PM for the exact punctuation used in the final output] If `copy_from_base` is true, base operations are applied to a source request and copied before current operations are applied[a specific separator character — ask the PM for the exact punctuation used in the final output] Output is a sorted parameter listing with `param_count` followed by `key=value` lines[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Test Cases:** `rcb_tests/public_test_cases/feature6_track_parameters[a specific separator character — ask the PM for the exact punctuation used in the final output]json`

```json
{
  "description": "Stores tracking query parameters as strings, removes parameters set to null or empty strings, preserves first values when requested, and can copy all existing parameters from a base request[a specific separator character — ask the PM for the exact punctuation used in the final output]",
  "cases": [
    {
      "input": {"feature":"track_parameters","operations":[{"method":"set","param":"h","value":"String"}]},
      "expected_output": "param_count=1\nh=String\n"
    },
    {
      "input": {"feature":"track_parameters","operations":[{"method":"try_set","param":"h","value":"A"},{"method":"try_set","param":"h","value":"B"}]},
      "expected_output": "param_count=1\nh=A\n"
    }
  ]
}
```

---

### Feature 7: Tracking Query Encoding

**As a developer**, I want tracking parameters encoded into a request query string, so I can send payloads through URL-based analytics endpoints[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Expected Behavior / Usage:**

The input is an object with `feature` set to `query_encoding` and the same operation shape used for tracking parameter mutation[a specific separator character — ask the PM for the exact punctuation used in the final output] The output is `encoded_query=<query>`, where the query starts with `?`, uses the public parameter wire keys, and percent-encodes reserved characters with UTF-8 rules[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Test Cases:** `rcb_tests/public_test_cases/feature7_query_encoding[a specific separator character — ask the PM for the exact punctuation used in the final output]json`

```json
{
  "description": "Encodes tracking parameters into a URL query string using the public wire keys and UTF-8 escaping[a specific separator character — ask the PM for the exact punctuation used in the final output]",
  "cases": [
    {
      "input": {"feature":"query_encoding","operations":[{"method":"set","param":"h","value":"abc123"}]},
      "expected_output": "encoded_query=?h=abc123\n"
    }
  ]
}
```

---

### Feature 8: Bulk Event Wrapping

**As a developer**, I want multiple event query strings grouped into dispatch pages and JSON payloads, so I can submit analytics events efficiently while preserving direct single-event URLs[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Expected Behavior / Usage:**

The input is an object with `feature` set to `bulk_wrapper`, an `api_url`, optional `token`, an `events` array, and an `action`[a specific separator character — ask the PM for the exact punctuation used in the final output] The `summary` action iterates through pages of up to 20 events[a specific separator character — ask the PM for the exact punctuation used in the final output] Each page prints its index, element count, JSON payload with a `requests` array and optional `token_auth`, and a direct event URL formed from the base API URL plus the first event query string on that page[a specific separator character — ask the PM for the exact punctuation used in the final output] Empty event lists produce no page entries and report the iterator as exhausted[a specific separator character — ask the PM for the exact punctuation used in the final output] The `api_url` action returns the configured API URL unchanged[a specific separator character — ask the PM for the exact punctuation used in the final output]

**Test Cases:** `rcb_tests/public_test_cases/feature8_bulk_event_wrapping[a specific separator character — ask the PM for the exact punctuation used in the final output]json`

```json
{
  "description": "Groups event query strings into bulk request pages, preserves the base API URL, includes an optional authentication token in JSON payloads, and returns a direct event URL for single-event dispatch[a specific separator character — ask the PM for the exact punctuation used in the final output]",
  "cases": [
    {
      "input": {"feature":"bulk_wrapper","api_url":"http://example[a specific separator character — ask the PM for the exact punctuation used in the final output]com/","token":"test_token","events":[],"action":"summary"},
      "expected_output": "has_next=false\nnext_after_end=null\n"
    },
    {
      "input": {"feature":"bulk_wrapper","api_url":"http://www[a specific separator character — ask the PM for the exact punctuation used in the final output]com/java[a specific separator character — ask the PM for the exact punctuation used in the final output]htm","token":"test_token","events":[""],"action":"api_url"},
      "expected_output": "api_url=http://www[a specific separator character — ask the PM for the exact punctuation used in the final output]com/java[a specific separator character — ask the PM for the exact punctuation used in the final output]htm\n"
    }
  ]
}
```

---

## Deliverables

1[a specific separator character — ask the PM for the exact punctuation used in the final output] **The Core System:** A cleanly structured codebase implementing the features described above[a specific separator character — ask the PM for the exact punctuation used in the final output] Its physical structure (single-file vs[a specific separator character — ask the PM for the exact punctuation used in the final output] multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering[a specific separator character — ask the PM for the exact punctuation used in the final output]

2[a specific separator character — ask the PM for the exact punctuation used in the final output] **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system[a specific separator character — ask the PM for the exact punctuation used in the final output] It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above[a specific separator character — ask the PM for the exact punctuation used in the final output] This adapter must be logically (and ideally physically) separated from the core domain[a specific separator character — ask the PM for the exact punctuation used in the final output]

3[a specific separator character — ask the PM for the exact punctuation used in the final output] **Automated test harness**[a specific separator character — ask the PM for the exact punctuation used in the final output] The cases embedded in this PRD live under `rcb_tests/public_test_cases/`[a specific separator character — ask the PM for the exact punctuation used in the final output] A single entry point `bash rcb_tests/test[a specific separator character — ask the PM for the exact punctuation used in the final output]sh` reads every `*[a specific separator character — ask the PM for the exact punctuation used in the final output]json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`)[a specific separator character — ask the PM for the exact punctuation used in the final output] For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename[a specific separator character — ask the PM for the exact punctuation used in the final output]stem}@{case_index[a specific separator character — ask the PM for the exact punctuation used in the final output]zfill(3)}[a specific separator character — ask the PM for the exact punctuation used in the final output]txt` (e[a specific separator character — ask the PM for the exact punctuation used in the final output]g[a specific separator character — ask the PM for the exact punctuation used in the final output] the first case in `feature1_[name][a specific separator character — ask the PM for the exact punctuation used in the final output]json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000[a specific separator character — ask the PM for the exact punctuation used in the final output]txt`)[a specific separator character — ask the PM for the exact punctuation used in the final output] Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other[a specific separator character — ask the PM for the exact punctuation used in the final output] Each `[a specific separator character — ask the PM for the exact punctuation used in the final output]txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`[a specific separator character — ask the PM for the exact punctuation used in the final output]
