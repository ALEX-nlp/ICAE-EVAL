## Product Requirement Document

# Browser Entropy Collection Toolkit - Standardized Input/Output Specification

## Project Goal

Build a client-side entropy toolkit that turns the many small, quirky readings a browser exposes (numeric strings, missing values, fluctuating screen geometry) into clean, deterministic, fingerprint-ready data. It gives developers a single dependable layer for numeric coercion, stable hashing, fault-isolated signal collection, and screen-frame measurement, so that an identifying signature can be derived from a device without hand-writing defensive parsing and error handling at every call site.

---

## Background & Problem

Without this toolkit, developers who want to derive a stable device signature must individually paper over the browser's inconsistencies: some properties arrive as numeric strings instead of numbers, some are absent entirely, the "available screen area" silently collapses to zero in fullscreen, and any single signal that throws can abort the whole collection. They also need a fast, dependency-free hash that produces the exact same digest across runs and platforms. Doing all of this by hand leads to repetitive, error-prone boilerplate and signatures that drift between environments.

With this toolkit, each concern is handled once and uniformly: numbers are parsed and rounded predictably, a fixed-width hash digest is produced deterministically, signal collection isolates failures per-signal while preserving order, and screen-frame measurement is smoothed over time so a transient zero reading does not destroy a previously observed good value.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (numeric data utilities, a hashing algorithm, a fault-isolating collection engine, and stateful screen-frame measurement). It MUST NOT be a single "god file"; output a clear directory tree separating these concerns from the execution adapter. Do not over-engineer the individual leaf utilities.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter only**, NOT the internal data model. The core logic MUST be completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic core calls and rendering results back to the line-oriented stdout contract.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Keep numeric parsing, hashing, collection/fault-isolation, screen-frame state, and output formatting in distinct logical units.
   - **OCP:** The collection engine must accept an arbitrary set of named signal producers without being modified to add new signals.
   - **LSP:** Any signal producer must be substitutable for any other; the engine treats them uniformly.
   - **ISP:** Keep the signal-producer contract minimal (a callable that returns a value or throws).
   - **DIP:** The collection engine depends on the abstract notion of a "named signal producer", not on any concrete browser reading.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Public functions must read naturally in the target language and hide internal complexity.
   - **Resilience:** Edge cases (absent values, numeric strings, all-zero geometry, a throwing producer) must be handled gracefully. A failure in one signal must never abort the collection of others; it must be captured and reported as an error outcome.

---

## Core Features

### Feature 1: Numeric Coercion & Rounding

**As a developer**, I want to convert loosely-typed browser readings into well-defined integers, floats, and rounded values, so I can compute stable signals without scattering defensive parsing throughout my code.

**Expected Behavior / Usage:**

*1.1 Integer Coercion — parse a value into an integer*

Accept either a number or a string. Read an optional leading sign followed by consecutive leading digits and stop at the first character that is not part of an integer; any fractional portion is **truncated toward zero**, not rounded (so `12.6` becomes `12` and `-1.5` becomes `-1`). If the input does not begin with a parseable number, emit the not-a-number sentinel `NaN`. Output is a single line `value=<result>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_to_int.json`

```json
{
    "description": "Parse a textual or numeric input into an integer by reading an optional leading sign and consecutive leading digits, stopping at the first character that is not part of an integer. A fractional part is truncated (not rounded). Input that does not begin with a parseable number yields the not-a-number sentinel.",
    "cases": [
        {"input": {"op": "to_int", "value": "12.6"}, "expected_output": "value=12"},
        {"input": {"op": "to_int", "value": "-1.5"}, "expected_output": "value=-1"},
        {"input": {"op": "to_int", "value": "foo"}, "expected_output": "value=NaN"}
    ]
}
```

*1.2 Float Coercion — parse a value into a floating-point number*

Accept either a number or a string and preserve the fractional part (so `"12.6"` becomes `12.6` and `"-1.5"` becomes `-1.5`). If the input does not begin with a parseable number, emit the not-a-number sentinel `NaN`. Output is a single line `value=<result>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_to_float.json`

```json
{
    "description": "Parse a textual or numeric input into a floating-point number, preserving the fractional part. Input that does not begin with a parseable number yields the not-a-number sentinel.",
    "cases": [
        {"input": {"op": "to_float", "value": "12.6"}, "expected_output": "value=12.6"},
        {"input": {"op": "to_float", "value": "-1.5"}, "expected_output": "value=-1.5"},
        {"input": {"op": "to_float", "value": "foo"}, "expected_output": "value=NaN"}
    ]
}
```

*1.3 Rounding to a Base — snap a number to the nearest multiple of a base*

Round a number to the nearest multiple of a given base. The base defaults to `1` when omitted. When the base magnitude is `>= 1` it rounds to that multiple (e.g. base `10` rounds to tens). When the base is a small fraction below `1` it effectively rounds to a fixed number of decimals and MUST avoid floating-point drift (e.g. `0.1234321` at base `0.0001` yields exactly `0.1234`, not `0.12340000000000001`). A negative base uses its magnitude. If either the value or the base is the not-a-number sentinel, the result is `NaN`. Output is a single line `value=<result>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_round.json`

```json
{
    "description": "Round a number to the nearest multiple of a given base (default base 1). The base may be a large integer (rounding to tens, etc.), a small fraction below 1 (rounding to a fixed number of decimals while avoiding floating-point drift), or negative (its magnitude is used). If either the value or the base is the not-a-number sentinel, the result is the not-a-number sentinel.",
    "cases": [
        {"input": {"op": "round", "value": 29847.23, "base": 10}, "expected_output": "value=29850"},
        {"input": {"op": "round", "value": 0.1234321, "base": 0.0001}, "expected_output": "value=0.1234"},
        {"input": {"op": "round", "value": 4.2, "base": -5}, "expected_output": "value=5"},
        {"input": {"op": "round", "value": "NaN", "base": 10}, "expected_output": "value=NaN"}
    ]
}
```

---

### Feature 2: Deterministic 128-bit Hash Digest

**As a developer**, I want to reduce an arbitrary string into a fixed-width, deterministic digest, so I can derive a compact, stable signature that is identical across runs and platforms.

**Expected Behavior / Usage:**

Implement the 128-bit x64 variant of the MurmurHash3 non-cryptographic hash over the UTF-16 code units of the input string. The output MUST be exactly 32 lowercase hexadecimal characters (zero-padded, no separators). The function is pure and deterministic: identical input always yields identical output. An empty string yields all zeros. The specific digests below are part of the contract and pin the exact algorithm behavior. Output is a single line `hash=<32 hex chars>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_murmur_hash.json`

```json
{
    "description": "Compute the 128-bit x64 MurmurHash3 of a UTF-16 string and render it as a fixed 32-character lowercase hexadecimal digest. The same input always produces the same digest; an empty string produces all zeros.",
    "cases": [
        {"input": {"op": "hash", "text": "Hello, world"}, "expected_output": "hash=[specific hash outputs for known inputs]"},
        {"input": {"op": "hash", "text": ""}, "expected_output": "hash=[specific hash outputs for known inputs]"}
    ]
}
```

---

### Feature 3: Fault-Isolating Signal Collection

**As a developer**, I want to run a set of named signal producers and gather their results into one map without letting any single failure abort the rest, so I can collect a device signature robustly even when some readings are unavailable or error out.

**Expected Behavior / Usage:**

The collection engine takes an ordered set of named producers, where each producer is a callable that either returns a value or throws. It invokes each producer independently and builds a result map. The input wire format models each producer as either `{"name": ..., "returns": <value>}` (a producer that returns the given value) or `{"name": ..., "throws": <message>, "as": "error"|"string"}` (a producer that throws — `"error"` throws a structured error object carrying the message, `"string"` throws a bare string). Each result is rendered as one line; collection order MUST follow the input order.

*3.1 Per-Signal Error Isolation — a throwing producer is captured, not propagated*

Every producer is invoked; a value outcome renders as `name=<name> outcome=value value=<json-encoded value>` and a thrown outcome renders as `name=<name> outcome=error message=<text>`. A failure in one producer MUST NOT prevent later producers from being collected, and producers before it keep their values. The error message in the output MUST be the language-neutral error text only — it MUST NOT leak any host-language exception class name, object representation, or runtime-appended suffix.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_collect_error_isolation.json`

```json
{
    "description": "Collect a set of named data sources into a components map. Each source is invoked independently: a source that returns a value is recorded as a value component, while a source that throws is caught and recorded as an error component whose normalized message carries the source's error text. One failing source never aborts the others, and the collection preserves the original source order.",
    "cases": [
        {
            "input": {"op": "collect", "sources": [
                {"name": "success1", "returns": "foo"},
                {"name": "throwsErrorObject", "throws": "bar", "as": "error"},
                {"name": "throwsErrorString", "throws": "baz", "as": "string"},
                {"name": "success2", "returns": "baq"}
            ]},
            "expected_output": "name=success1 outcome=value value=\"foo\"\nname=throwsErrorObject outcome=error message=bar\nname=throwsErrorString outcome=error message=baz\nname=success2 outcome=value value=\"baq\""
        }
    ]
}
```

*3.2 Exclusion Filter — skip named producers entirely*

The engine also accepts an exclusion set of names. Any excluded producer MUST be neither invoked nor present in the result; only the surviving producers, in their original order, are collected and rendered.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_collect_exclusion.json`

```json
{
    "description": "Collect named data sources while skipping any source listed in the exclusion set. Excluded sources are neither invoked nor present in the resulting components map; only the surviving sources, in their original order, are collected.",
    "cases": [
        {
            "input": {"op": "collect", "sources": [
                {"name": "toBe", "returns": true},
                {"name": "notToBe", "returns": false}
            ], "exclude": ["notToBe"]},
            "expected_output": "name=toBe outcome=value value=true"
        }
    ]
}
```

---

### Feature 4: Screen Frame Measurement

**As a developer**, I want to measure the gap between the full screen and the usable screen area, and keep a stable reading even when that gap momentarily collapses to zero, so I can use screen geometry as a reliable signal.

**Expected Behavior / Usage:**

*4.1 Frame Computation — derive the four-sided frame from screen geometry*

Given screen geometry (`width`, `height`, `availWidth`, `availHeight`, `availLeft`, `availTop`), compute the frame as a four-element list ordered **top, right, bottom, left**, where: top = `availTop`; right = `width - availWidth - availLeft`; bottom = `height - availHeight - availTop`; left = `availLeft`. When `availLeft`/`availTop` are unavailable ([a specific sentinel and arithmetic null handling strategy]), they are treated as `0` inside the width/height arithmetic but reported as the `[a specific sentinel and arithmetic null handling strategy]` sentinel in their own top/left positions. A frame whose sides are all zero is reported as all zeros. A **rounded** form is also produced that snaps each non-[a specific sentinel and arithmetic null handling strategy] side to the nearest multiple of 10. Output is two lines: `frame=<json list>` and `rounded=<json list>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_screen_frame.json`

```json
{
    "description": "Compute the screen 'frame' (the gap on each side between the full screen and the available screen area) as a four-element list ordered top, right, bottom, left. Top equals availTop; right equals width - availWidth - availLeft; bottom equals height - availHeight - availTop; left equals availLeft. When availLeft/availTop are unavailable they are treated as 0 for the width/height arithmetic but reported as the [a specific sentinel and arithmetic null handling strategy] sentinel in their own positions. A frame whose sides are all zero is reported as all zeros. The rounded form snaps each non-[a specific sentinel and arithmetic null handling strategy] side to the nearest multiple of 10.",
    "cases": [
        {
            "input": {"op": "screen_frame", "screen": {"width": 1440, "height": 900, "availWidth": 1367, "availHeight": 853, "availLeft": 49, "availTop": 11}},
            "expected_output": "frame=[11,24,36,49]\nrounded=[10,20,40,50]"
        },
        {
            "input": {"op": "screen_frame", "screen": {"width": 1280, "height": 1024, "availWidth": 1182, "availHeight": 1000, "availLeft": [a specific sentinel and arithmetic null handling strategy], "availTop": [a specific sentinel and arithmetic null handling strategy]}},
            "expected_output": "frame=[[a specific sentinel and arithmetic null handling strategy],98,24,[a specific sentinel and arithmetic null handling strategy]]\nrounded=[[a specific sentinel and arithmetic null handling strategy],100,20,[a specific sentinel and arithmetic null handling strategy]]"
        }
    ]
}
```

*4.2 Frame Watch & Backup — remember a good reading across transient zero collapses*

Because the frame momentarily collapses to all-zero in some conditions, a watch facility smooths the reading over time. The input is a sequence of steps: a `watch` step starts monitoring; a `tick` step re-samples the current geometry (each step may carry a new `set` of geometry); a `get` step reports the frame that would be exposed and appends one `frame=<json list>` line to the output. Behavior contract: while the live frame is all-zero and no non-zero frame has ever been observed, `get` reports all zeros. Once any non-zero frame is observed it is remembered; a later `get` that finds the live frame collapsed to all-zero returns the **remembered** non-zero frame instead of zeros. When the live frame is itself non-zero, `get` returns the live frame and updates the remembered value. Output is one `frame=...` line per `get` step, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_screen_frame_watch.json`

```json
{
    "description": "Watch the screen frame over time to mitigate the fact that the frame momentarily collapses to all-zero in some conditions. A 'watch' step starts monitoring; each 'tick' re-samples the current screen geometry; each 'get' reports the frame that would be exposed. Behavior: while the live frame is all-zero and no non-zero frame has ever been observed, get reports all zeros. Once any non-zero frame is observed it is remembered, and a later get that finds the live frame collapsed to all-zero returns the remembered non-zero frame instead. When the live frame is itself non-zero, get returns the live frame and updates the remembered value.",
    "cases": [
        {
            "input": {"op": "screen_frame_watch", "steps": [
                {"set": {"width": 640, "height": 480, "availWidth": 640, "availHeight": 480, "availLeft": 0, "availTop": 0}, "do": "watch"},
                {"do": "get"},
                {"set": {"width": 640, "height": 480, "availWidth": 600, "availHeight": 400, "availLeft": 10, "availTop": 30}, "do": "tick"},
                {"set": {"width": 640, "height": 480, "availWidth": 640, "availHeight": 480, "availLeft": 0, "availTop": 0}, "do": "tick"},
                {"do": "get"},
                {"set": {"width": 640, "height": 480, "availWidth": 600, "availHeight": 400, "availLeft": 30, "availTop": 10}, "do": "tick"},
                {"do": "get"},
                {"set": {"width": 640, "height": 480, "availWidth": 640, "availHeight": 480, "availLeft": 0, "availTop": 0}, "do": "tick"},
                {"do": "get"}
            ]},
            "expected_output": "frame=[0,0,0,0]\nframe=[30,30,50,10]\nframe=[10,10,70,30]\nframe=[10,10,70,30]"
        }
    ]
}
```

---

### Feature 5: Device Memory Normalization

**As a developer**, I want to read the advertised device memory and turn it into a clean number or a defined "unknown" sentinel, so I can use it as a signal regardless of whether the environment reports it as a number, a numeric string, or not at all.

**Expected Behavior / Usage:**

Read the advertised device memory (in gigabytes). A numeric or numeric-string reading is coerced to a number. A missing/undefined reading is reported as the `unknown` sentinel rather than a number. Output is a single line `device_memory=<number>` or `device_memory=unknown`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_device_memory.json`

```json
{
    "description": "Read the advertised device memory (in gigabytes) and normalize it to a number. Numeric and numeric-string inputs are coerced to a number; a missing/undefined reading is reported as the 'unknown' sentinel.",
    "cases": [
        {"input": {"op": "device_memory", "value": "4"}, "expected_output": "device_memory=4"},
        {"input": {"op": "device_memory", "value": [a specific sentinel and arithmetic null handling strategy]}, "expected_output": "device_memory=unknown"}
    ]
}
```

---

### Feature 6: Touch Point Normalization

**As a developer**, I want to read the maximum number of simultaneous touch points as an integer even when the environment reports it as a numeric string, so I get a consistent numeric signal across environments.

**Expected Behavior / Usage:**

Read the maximum number of simultaneous touch points and normalize it to an integer, coercing numeric-string readings (e.g. `"5"`) to their integer value. Output is a single line `max_touch_points=<integer>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_touch_points.json`

```json
{
    "description": "Read the maximum number of simultaneous touch points and normalize it to an integer, even when the underlying value is reported as a numeric string by some environments.",
    "cases": [
        {"input": {"op": "touch_points", "value": "5"}, "expected_output": "max_touch_points=5"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above, with numeric utilities, the hashing algorithm, the fault-isolating collection engine, and the stateful screen-frame measurement kept as separate logical units. The physical structure MUST follow the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command from stdin, dispatches on the `op` field, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature line contracts above. The adapter is responsible for normalizing any thrown native error into the language-neutral error contract (Feature 3.1); it MUST be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_to_int.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_to_int@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- behavior of frame state persistence
- normalization rules for error messages
