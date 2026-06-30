## Product Requirement Document

# Tile-Server Admin Metrics & Formatting Library — Size Formatting, API URL Building, and Request-Metrics Parsing

## Project Goal

Build a small, reusable support library for the administrative dashboard of a map-tile server that converts raw numeric and textual inputs into clean, presentation-ready values: human-readable file sizes, fully-qualified API endpoint URLs, and structured request-performance metrics parsed from a metrics exposition text. The goal is to let a dashboard render correct sizes, reach the right backend endpoints, and chart per-endpoint latency without each screen re-implementing the same parsing and formatting rules.

---

## Background & Problem

A tile-server dashboard repeatedly needs three boring-but-error-prone transformations: turning a byte count into something like `1.5 KB`, turning a relative API path into an absolute URL that respects an optionally configured backend base address, and turning a Prometheus-style metrics dump into per-endpoint sums, counts, and latency histograms that can be grouped into logical categories (tiles, sprites, fonts, styles).

Without a shared library, each of these is hand-rolled per screen, producing inconsistent size labels, broken URLs when query/hash fragments leak into the base, and subtly wrong histogram aggregation (for example, double-counting the redundant `+Inf` bucket, or failing to add same-boundary buckets across endpoints). This library centralizes the rules into a handful of pure functions with a single, well-defined input/output contract per behavior.

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

### Feature 1: Human-Readable File Size Formatting

**As a developer**, I want to turn a raw byte count into a compact size label, so the dashboard can show sizes that humans can read at a glance.

**Expected Behavior / Usage:**

The input supplies a byte count. The output is a single formatted line. Units are decimal ([use the program's configured base unit (Bytes, KB, etc.) based on input magnitude]): `Bytes`, `KB`, `MB`, `GB`, `TB`. Special and boundary rules: a count of `0` returns `0 Bytes`; a count of exactly `1` returns `1 Byte` (singular); any input that is not a usable non-negative number — absent, null, not-a-number, or negative — returns `Unknown size`. Otherwise the count is floored to an integer before scaling; the scaled value is rendered with up to two decimal places and trailing zeros stripped (so `1000` → `1 KB`, `1500` → `1.5 KB`, `1234` → `1.23 KB`), followed by a space and the unit. Any value large enough to land at or beyond the unit list (i.e. would need a unit larger than `TB`) returns `File too large`. A single trailing newline terminates the output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_file_size.json`

```json
{
    "description": "Convert a raw byte count into a compact, human-readable size string using decimal ([use the program's configured base unit (Bytes, KB, etc.) based on input magnitude]) units. Zero yields a special label; exactly one byte uses the singular unit; any value that is not a usable non-negative number (absent, null, not-a-number, or negative) yields an unknown-size label; fractional inputs are floored before scaling; the scaled value is shown with up to two decimal places (trailing zeros stripped) followed by the unit; values at or beyond the largest supported unit yield a too-large label.",
    "cases": [
        {"input": {"action": "format_file_size", "bytes": 0}, "expected_output": "0 Bytes\n"},
        {"input": {"action": "format_file_size", "bytes": 1500}, "expected_output": "1.5 KB\n"},
        {"input": {"action": "format_file_size", "bytes": null}, "expected_output": "Unknown size\n"}
    ]
}
```

---

### Feature 2: API Endpoint URL Construction

**As a developer**, I want to resolve the backend base address and join it with a request path, so the dashboard always calls a correct absolute URL regardless of how it is deployed.

**Expected Behavior / Usage:**

*2.1 Base Address Resolution — derive the API root*

The base address is resolved from configuration when present, otherwise from the current document location. The input may carry an explicit configured `base`; when it is a non-empty string it is returned verbatim. When `base` is empty (not configured), the result is the current location's `origin` concatenated with its `pathname` (so query/hash fragments cannot corrupt the API root). The output is the resolved base address followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_base_url.json`

```json
{
    "description": "Resolve the base address used to reach the server API. When an explicit base address is configured, that value is returned verbatim. When no base is configured (empty), the base is derived from the current document location by concatenating its origin with its path component, so query/hash fragments do not corrupt the API root.",
    "cases": [
        {"input": {"action": "get_base_url", "base": "https://api.example.com"}, "expected_output": "https://api.example.com\n"},
        {"input": {"action": "get_base_url", "base": "", "location": {"origin": "http://localhost", "pathname": "/"}}, "expected_output": "http://localhost/\n"}
    ]
}
```

*2.2 Path Joining — build a complete endpoint URL*

Given a resolved base address and a request path, produce the full URL by joining them with exactly one slash: a leading slash is added to the path when missing, and a single trailing slash on the base is removed first. Characters in the path that look special (such as `@` in a retina sprite name, or an underscore-prefixed reserved segment) are preserved unchanged. The output is the complete URL followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_build_url.json`

```json
{
    "description": "Build a complete endpoint URL from the resolved base address and a request path. Exactly one slash joins the two: a leading slash is added to the path if missing, and a trailing slash on the base is removed. Special characters in the path (such as @ or reserved-looking segments) are preserved unchanged.",
    "cases": [
        {"input": {"action": "build_url", "base": "https://api.example.com", "path": "/catalog"}, "expected_output": "https://api.example.com/catalog\n"},
        {"input": {"action": "build_url", "base": "https://api.example.com", "path": "catalog"}, "expected_output": "https://api.example.com/catalog\n"}
    ]
}
```

---

### Feature 3: Request-Duration Sum & Count Parsing

**As a developer**, I want to extract per-endpoint duration totals and request counts from a metrics exposition text, so the dashboard can compute average latencies.

**Expected Behavior / Usage:**

The input is a metrics exposition text (newline-separated lines). The parser recognizes only the request-duration histogram metric family whose base name is `martin_http_requests_duration_seconds`, specifically its `_sum` and `_count` series. For each recognized line it reads the `endpoint="..."` label and the trailing numeric value, accumulating the value per endpoint into a `sum` map and a `count` map respectively (repeated endpoints add together). Comment lines, blank lines, and unrelated metric families are ignored. An endpoint that appears in only one series produces a value only in that series. The output lists, in first-seen order, each `sum <endpoint> <value>` line followed by each `count <endpoint> <value>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_parse_metrics.json`

```json
{
    "description": "Parse a server metrics exposition text and extract, per endpoint label, the total accumulated request-duration (sum) and the total request count, keyed by endpoint. Only the duration sum and count series for the request-duration metric family are recognized; comment lines and unrelated metric families are ignored. Endpoints that appear only in one series produce a value only in that series.",
    "cases": [
        {
            "input": {"action": "parse_metrics", "text": "# HELP martin_http_requests_duration_seconds HTTP request duration in seconds for all requests\n# TYPE martin_http_requests_duration_seconds histogram\nmartin_http_requests_duration_seconds_sum{endpoint=\"/sprite/{source_ids}.json\",method=\"GET\",status=\"200\"} 12.5\nmartin_http_requests_duration_seconds_count{endpoint=\"/sprite/{source_ids}.json\",method=\"GET\",status=\"200\"} 50\nmartin_http_requests_duration_seconds_sum{endpoint=\"/font/{fontstack}/{start}-{end}\",method=\"GET\",status=\"200\"} 3.2\nmartin_http_requests_duration_seconds_count{endpoint=\"/font/{fontstack}/{start}-{end}\",method=\"GET\",status=\"200\"} 8\nmartin_http_requests_duration_seconds_sum{endpoint=\"/style/{style_id}\",method=\"GET\",status=\"200\"} 7.0\nmartin_http_requests_duration_seconds_count{endpoint=\"/style/{style_id}\",method=\"GET\",status=\"200\"} 14"},
            "expected_output": "sum /sprite/{source_ids}.json 12.5\nsum /font/{fontstack}/{start}-{end} 3.2\nsum /style/{style_id} 7\ncount /sprite/{source_ids}.json 50\ncount /font/{fontstack}/{start}-{end} 8\ncount /style/{style_id} 14\n"
        },
        {
            "input": {"action": "parse_metrics", "text": "other_metric{foo=\"bar\"} 123\nmartin_http_requests_duration_seconds_sum{endpoint=\"/catalog\",method=\"GET\",status=\"200\"} 1.1\nmartin_http_requests_duration_seconds_count{endpoint=\"/catalog\",method=\"GET\",status=\"200\"} 2"},
            "expected_output": "sum /catalog 1.1\ncount /catalog 2\n"
        }
    ]
}
```

---

### Feature 4: Endpoint-Group Metric Aggregation

**As a developer**, I want to roll up per-endpoint sums and counts into named logical groups, so the dashboard can show one latency figure per category instead of per raw endpoint pattern.

**Expected Behavior / Usage:**

The input supplies a `sum` map, a `count` map, and a `groups` definition mapping each group name to a list of endpoint patterns. For each group, the total sum and total count are the arithmetic totals over its member endpoints, where an endpoint absent from the maps contributes zero. The reported average request duration is in milliseconds, computed as `(total sum / total count) * 1000`, or `0` when the group has no requests. Each group is reported, in the order given, as `<group> [standard prefix string for averages]<averageRequestDurationMs> count=<requestCount>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_aggregate_groups.json`

```json
{
    "description": "Aggregate per-endpoint duration sums and request counts into named logical groups. Each group lists one or more endpoint patterns; the group total sum and total count are the arithmetic totals over its member endpoints (absent endpoints contribute zero). The average request duration is reported in milliseconds as (total sum / total count) * 1000, or 0 when the group has no requests. Groups are reported in the order given.",
    "cases": [
        {
            "input": {"action": "aggregate_groups", "sum": {"/font/{fontstack}/{start}-{end}": 5, "/sprite/{source_ids}.json": 10, "/sprite/{source_ids}.png": 20, "/style/{style_id}": 8}, "count": {"/font/{fontstack}/{start}-{end}": 1, "/sprite/{source_ids}.json": 2, "/sprite/{source_ids}.png": 4, "/style/{style_id}": 8}, "groups": {"fonts": ["/font/{fontstack}/{start}-{end}"], "missing": ["/not_present"], "sprites": ["/sprite/{source_ids}.json", "/sprite/{source_ids}.png"], "styles": ["/style/{style_id}"]}},
            "expected_output": "fonts [standard prefix string for averages]5000 count=1\nmissing [standard prefix string for averages]0 count=0\nsprites [standard prefix string for averages]5000 count=6\nstyles [standard prefix string for averages]1000 count=8\n"
        },
        {
            "input": {"action": "aggregate_groups", "sum": {}, "count": {}, "groups": {"group1": ["/foo"], "group2": ["/bar"]}},
            "expected_output": "group1 [standard prefix string for averages]0 count=0\ngroup2 [standard prefix string for averages]0 count=0\n"
        }
    ]
}
```

---

### Feature 5: Latency Histogram Bucket Parsing

**As a developer**, I want to extract per-endpoint latency histogram buckets from the metrics text, so the dashboard can chart the latency distribution.

**Expected Behavior / Usage:**

The parser scans the metrics exposition text for the `_bucket` series of the request-duration metric family. Each recognized bucket line carries an `endpoint="..."` label, an `le="..."` upper-bound label, and a trailing cumulative count. For each endpoint a list of `{le, count}` buckets is collected. The synthetic `le="+Inf"` bucket is dropped because it is redundant with the total request count. The collected buckets for each endpoint are sorted ascending by upper-bound. Bucket lines without an endpoint label, comment lines, and unrelated metric families are ignored. The output prints, per endpoint, the endpoint on its own line followed by one `<le> <count>` line per retained bucket in ascending order.

**Test Cases:** `rcb_tests/public_test_cases/feature5_parse_histogram.json`

```json
{
    "description": "Parse a server metrics exposition text and extract per-endpoint latency histogram buckets. Each bucket carries an upper-bound (le) and a cumulative count. The synthetic +Inf bucket is dropped (it is redundant with the total count). Buckets are returned sorted ascending by upper-bound for each endpoint. Lines without an endpoint label, comment lines, and unrelated metric families are ignored.",
    "cases": [
        {
            "input": {"action": "parse_histogram", "text": "# HELP martin_http_requests_duration_seconds HTTP request duration in seconds for all requests\n# TYPE martin_http_requests_duration_seconds histogram\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.005\"} 1\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.01\"} 2\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.025\"} 4\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.05\"} 5\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.1\"} 5\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.25\"} 10\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.5\"} 15\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"1\"} 15\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"2.5\"} 20\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"5\"} 20\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"10\"} 20\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"+Inf\"} 20\nmartin_http_requests_duration_seconds_sum{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\"} 20\nmartin_http_requests_duration_seconds_count{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\"} 20"},
            "expected_output": "/{source_ids}/{z}/{x}/{y}\n0.005 1\n0.01 2\n0.025 4\n0.05 5\n0.1 5\n0.25 10\n0.5 15\n1 15\n2.5 20\n5 20\n10 20\n"
        },
        {
            "input": {"action": "parse_histogram", "text": "other_metric{foo=\"bar\"} 123\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/test\",method=\"GET\",status=\"200\",le=\"0.1\"} 50\nmartin_http_requests_duration_seconds_sum{endpoint=\"/test\",method=\"GET\",status=\"200\"} 1.0\nmartin_http_requests_duration_seconds_count{endpoint=\"/test\",method=\"GET\",status=\"200\"} 50\nunrelated_bucket{le=\"0.1\"} 999"},
            "expected_output": "/test\n0.1 50\n"
        }
    ]
}
```

---

### Feature 6: Combined Single-Pass Metrics Parsing

**As a developer**, I want one call that returns sums, counts, and histograms together, so the dashboard can load all request-performance views from a single metrics fetch.

**Expected Behavior / Usage:**

The input is a metrics exposition text. The output is the composition of the sum/count extraction (Feature 3) and the histogram extraction (Feature 5) over the same text: per-endpoint duration `sum`, per-endpoint request `count`, and per-endpoint latency histogram buckets (with the `+Inf` bucket dropped and buckets sorted ascending by upper-bound). The output prints each `sum <endpoint> <value>` line, then each `count <endpoint> <value>` line, then for each endpoint a `histogram <endpoint>` header line followed by its `<le> <count>` bucket lines in ascending order.

**Test Cases:** `rcb_tests/public_test_cases/feature6_parse_complete.json`

```json
{
    "description": "Parse a server metrics exposition text in a single pass and return all three views together: per-endpoint duration sum, per-endpoint request count, and per-endpoint latency histogram buckets (with the +Inf bucket dropped and buckets sorted ascending by upper-bound). This is the composition of the sum/count extraction and the histogram extraction over the same input.",
    "cases": [
        {
            "input": {"action": "parse_complete", "text": "# HELP martin_http_requests_duration_seconds HTTP request duration in seconds for all requests\n# TYPE martin_http_requests_duration_seconds histogram\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.005\"} 23004\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.01\"} 23045\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.025\"} 23228\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.05\"} 23410\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.1\"} 23637\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.25\"} 23722\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"0.5\"} 23735\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"1\"} 23746\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"2.5\"} 23747\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"5\"} 23747\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"10\"} 23747\nmartin_http_requests_duration_seconds_bucket{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\",le=\"+Inf\"} 23747\nmartin_http_requests_duration_seconds_sum{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\"} 61.49839745299979\nmartin_http_requests_duration_seconds_count{endpoint=\"/{source_ids}/{z}/{x}/{y}\",method=\"GET\",status=\"200\"} 23747"},
            "expected_output": "sum /{source_ids}/{z}/{x}/{y} 61.49839745299979\ncount /{source_ids}/{z}/{x}/{y} 23747\nhistogram /{source_ids}/{z}/{x}/{y}\n0.005 23004\n0.01 23045\n0.025 23228\n0.05 23410\n0.1 23637\n0.25 23722\n0.5 23735\n1 23746\n2.5 23747\n5 23747\n10 23747\n"
        }
    ]
}
```

---

### Feature 7: Histogram Group Aggregation

**As a developer**, I want to merge per-endpoint histogram buckets into named groups, so the dashboard can chart latency for a whole category of endpoints at once.

**Expected Behavior / Usage:**

The input supplies a `histograms` map (endpoint to a list of `{le, count}` buckets) and a `groups` definition mapping each group name to a list of endpoint patterns. For each group, buckets that share the same upper-bound (`le`) across the group's member endpoints have their counts added together, while buckets with distinct upper-bounds are kept as separate entries. The merged buckets are sorted ascending by upper-bound. A group whose member endpoints have no histogram data still appears in the result with an empty bucket list. The output prints, for each group in the order given, the group name on its own line followed by one `<le> <count>` line per merged bucket in ascending order (a group with no buckets is just its name line).

**Test Cases:** `rcb_tests/public_test_cases/feature7_aggregate_histogram.json`

```json
{
    "description": "Combine per-endpoint histogram buckets into named logical groups. For each group, buckets that share the same upper-bound (le) across member endpoints have their counts added together; buckets with distinct upper-bounds are kept separately. The combined buckets are sorted ascending by upper-bound. A group whose endpoints have no histogram data still appears in the result with an empty bucket list. Groups are reported in the order given.",
    "cases": [
        {
            "input": {"action": "aggregate_histogram", "histograms": {"/sprite/{source_ids}.json": [{"count": 100, "le": 0.005}, {"count": 150, "le": 0.01}, {"count": 180, "le": 0.025}], "/sprite/{source_ids}.png": [{"count": 50, "le": 0.005}, {"count": 80, "le": 0.01}, {"count": 120, "le": 0.025}]}, "groups": {"sprites": ["/sprite/{source_ids}.json", "/sprite/{source_ids}.png"], "tiles": ["/{source_ids}/{z}/{x}/{y}"]}},
            "expected_output": "sprites\n0.005 150\n0.01 230\n0.025 300\ntiles\n"
        },
        {
            "input": {"action": "aggregate_histogram", "histograms": {"/sprite/{source_ids}.json": [{"count": 100, "le": 0.005}, {"count": 150, "le": 0.025}], "/sprite/{source_ids}.png": [{"count": 50, "le": 0.01}, {"count": 80, "le": 0.05}]}, "groups": {"sprites": ["/sprite/{source_ids}.json", "/sprite/{source_ids}.png"]}},
            "expected_output": "sprites\n0.005 100\n0.01 50\n0.025 150\n0.05 80\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (size formatting, URL construction, and metrics parsing/aggregation). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, dispatches on the request's `action` field, invokes the appropriate core logic, and prints the result to stdout, matching the per-feature contracts above. Actions: `format_file_size` (a `bytes` value; omit it to represent an absent value, use the string `"NaN"` to represent not-a-number); `get_base_url` and `build_url` (a configured `base`, an optional `location` with `origin`/`pathname`, and for `build_url` a `path`); `parse_metrics`, `parse_histogram`, and `parse_complete` (a metrics exposition `text`); `aggregate_groups` (a `sum` map, a `count` map, and a `groups` definition); and `aggregate_histogram` (a `histograms` map and a `groups` definition). Numeric values are rendered using the platform's default number-to-string conversion.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- handle line comments and whitespace
- format histogram header block
