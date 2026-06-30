## Product Requirement Document

# Temporal Value JSON Codec — Serializing and Parsing Date & Time Values To and From a Stable Wire Format

## Project Goal

Build a reusable codec that converts a small family of date and time values to and from JSON, so applications can persist and exchange temporal data using one well-defined, predictable wire format instead of each component inventing its own ad-hoc string handling.

---

## Background & Problem

Applications constantly need to move temporal values — a calendar date, a wall-clock time, a combined date-time, an elapsed duration, a year-month, a recurring month-day, a bare year, or a date-based period — across process boundaries as JSON. Each such value is a distinct concept: some have sub-second precision, some have no year, some have no day, some represent an amount of time rather than a point on the calendar.

Without a shared codec, every application hand-rolls its own formatting and parsing for each kind of value. This leads to inconsistent representations (is a date `[2013,8,21]` or `"2013-08-21"`?), silent precision loss, brittle parsing, and runtime errors that leak host-language internals to callers.

This codec provides one contract. It serializes each value into a documented wire form, supports a flag that selects between a compact numeric representation and an ISO-8601 textual representation where both make sense, parses every documented wire form back into the corresponding value, and reports any failure as a stable, language-neutral error.

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
   - **Open/Closed Principle (OCP):** The core engine must be open for extension (new temporal kinds) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

Every request is a single JSON object read from stdin. It carries an `op` field that is either `serialize` or `deserialize`, a `type` field naming the kind of temporal value, and a `value` field. For `serialize`, an optional boolean `as_timestamp` (default `true`) selects the numeric wire form over the textual one for the kinds that support both. The result is written to stdout. Supported `type` names are: `date`, `time`, `datetime`, `duration`, `period`, `year`, `year_month`, `month_day`.

### Feature 1: Calendar Date

**As a developer**, I want to serialize and parse a calendar date (year, month, day, with no time and no zone), so I can exchange plain dates without ambiguity.

**Expected Behavior / Usage:**

For `serialize`, `value` is the canonical ISO-8601 date the caller wants encoded. When `as_timestamp` is true the output is a compact numeric array of exactly three integers — year, month, day. When `as_timestamp` is false the output is the ISO-8601 extended date as a quoted JSON string. For `deserialize`, `value` may be the three-element numeric array, the ISO-8601 date string, or — leniently — a single integer interpreted as the number of days since the epoch (day 0 being 1970-01-01); the parsed date is reported in canonical ISO-8601 date form.

**Test Cases:** `rcb_tests/public_test_cases/feature1_date.json`

```json
{
    "description": "Round-trip a calendar date (year, month, day with no time-of-day and no zone) through the JSON codec. Serialization has two wire forms selected by a flag: a compact numeric array of the three date components, or an ISO-8601 extended date string. Deserialization accepts either of those wire forms and, leniently, a single integer interpreted as a count of days since the epoch; in every case the parsed value is reported in its canonical ISO-8601 date form so the conversion is observable.",
    "cases": [
        {
            "input": {"op": "serialize", "type": "date", "as_timestamp": true, "value": "1986-01-17"},
            "expected_output": "[1986,1,17]\n"
        },
        {
            "input": {"op": "deserialize", "type": "date", "value": [1986, 1, 17]},
            "expected_output": "1986-01-17\n"
        }
    ]
}
```

---

### Feature 2: Wall-Clock Time

**As a developer**, I want to serialize and parse a time-of-day (hour, minute, optional second and sub-second, with no date and no zone), so I can exchange times with nanosecond precision when needed.

**Expected Behavior / Usage:**

For `serialize`, `value` is the canonical ISO-8601 time. When `as_timestamp` is true the output is a numeric array listing the meaningful components — always hour and minute, plus second and then nanosecond when those carry information. When `as_timestamp` is false the output is the ISO-8601 local time as a quoted string, always normalized to include the seconds field even if the input omitted it. For `deserialize`, `value` may be the numeric array or the ISO-8601 time string; the parsed time is reported in canonical ISO-8601 time form.

**Test Cases:** `rcb_tests/public_test_cases/feature2_time.json`

```json
{
    "description": "Round-trip a wall-clock time-of-day (hour, minute, optional second and sub-second, no date and no zone) through the JSON codec. The numeric-array wire form lists the present components: hour and minute, plus second and nanosecond when they carry information. The string wire form is an ISO-8601 local time and is always normalized to include seconds even when the input omitted them. Deserialization accepts either wire form and reports the parsed value in canonical ISO-8601 time form.",
    "cases": [
        {
            "input": {"op": "serialize", "type": "time", "as_timestamp": true, "value": "22:31:05.000829837"},
            "expected_output": "[22,31,5,829837]\n"
        },
        {
            "input": {"op": "deserialize", "type": "time", "value": [9, 22, 57]},
            "expected_output": "09:22:57\n"
        }
    ]
}
```

---

### Feature 3: Combined Date-Time

**As a developer**, I want to serialize and parse a combined date-and-time without zone offset, so I can exchange local timestamps.

**Expected Behavior / Usage:**

For `serialize`, `value` is the canonical ISO-8601 local date-time. When `as_timestamp` is true the output is a numeric array that concatenates the date components (year, month, day) with the time components (hour, minute, and second/nanosecond when present). When `as_timestamp` is false the output is the ISO-8601 local date-time as a quoted string. For `deserialize`, `value` may be the numeric array or the ISO-8601 string; the parsed value is reported in canonical ISO-8601 date-time form.

**Test Cases:** `rcb_tests/public_test_cases/feature3_datetime.json`

```json
{
    "description": "Round-trip a combined date-and-time without zone offset through the JSON codec. The numeric-array wire form concatenates the date components (year, month, day) with the time components (hour, minute, and second/nanosecond when present). The string wire form is an ISO-8601 local date-time. Deserialization accepts either wire form and reports the parsed value in canonical ISO-8601 date-time form.",
    "cases": [
        {
            "input": {"op": "serialize", "type": "datetime", "as_timestamp": true, "value": "2013-08-21T09:22:57"},
            "expected_output": "[2013,8,21,9,22,57]\n"
        },
        {
            "input": {"op": "deserialize", "type": "datetime", "value": [2013, 8, 21, 9, 22, 57]},
            "expected_output": "2013-08-21T09:22:57\n"
        }
    ]
}
```

---

### Feature 4: Duration (Elapsed Time)

**As a developer**, I want to serialize and parse a time-based amount of elapsed time, so I can exchange durations with sub-second precision.

**Expected Behavior / Usage:**

For `serialize`, `value` is the canonical ISO-8601 duration. When `as_timestamp` is true the output is a decimal number of seconds whose fractional part carries sub-second precision down to nanoseconds; a whole-second duration is rendered with nine fractional digits. When `as_timestamp` is false the output is the ISO-8601 duration as a quoted string. For `deserialize`, `value` may be a number (interpreted as seconds, with any fractional part as sub-second precision) or the ISO-8601 duration string; the parsed duration is reported in canonical ISO-8601 duration form.

**Test Cases:** `rcb_tests/public_test_cases/feature4_duration.json`

```json
{
    "description": "Round-trip a time-based amount of elapsed time (a duration) through the JSON codec. The numeric wire form is a decimal count of seconds, where the fractional part carries sub-second precision down to nanoseconds and is always rendered with nine fractional digits when whole. The string wire form is the ISO-8601 duration notation. Deserialization accepts a number (interpreted as seconds) or the ISO-8601 string and reports the parsed value in canonical ISO-8601 duration form.",
    "cases": [
        {
            "input": {"op": "serialize", "type": "duration", "as_timestamp": true, "value": "PT1M"},
            "expected_output": "60.000000000\n"
        },
        {
            "input": {"op": "deserialize", "type": "duration", "value": 13498.000008374},
            "expected_output": "[a specific sub-precision duration value — ask the PM for the exact string]\n"
        }
    ]
}
```

---

### Feature 5: Period (Years/Months/Days Amount)

**As a developer**, I want to serialize and parse a date-based amount of time expressed in years, months and days, so I can exchange calendar offsets.

**Expected Behavior / Usage:**

A period has a single wire form regardless of `as_timestamp`: an ISO-8601 period string. For `serialize`, `value` is the canonical period and the output is that period as a quoted string. For `deserialize`, `value` is the period string; the parsed period is reported in canonical ISO-8601 period form, in which components that are zero may be omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_period.json`

```json
{
    "description": "Round-trip a date-based amount of time expressed in years, months and days (a period) through the JSON codec. A period has a single wire form regardless of the timestamp flag: an ISO-8601 period string. Serialization emits that string; deserialization parses it back and reports the canonical ISO-8601 period form, in which components that are zero may be omitted.",
    "cases": [
        {
            "input": {"op": "serialize", "type": "period", "value": "P1Y6M15D"},
            "expected_output": "\"P1Y6M15D\"\n"
        },
        {
            "input": {"op": "deserialize", "type": "period", "value": "P1Y6M15D"},
            "expected_output": "P1Y6M15D\n"
        }
    ]
}
```

---

### Feature 6: Calendar Year

**As a developer**, I want to serialize and parse a standalone calendar year, so I can exchange bare years compactly.

**Expected Behavior / Usage:**

A year is represented on the wire as a bare integer. For `serialize`, `value` is the year and the output is that integer. For `deserialize`, `value` may be an integer or a numeric string; the parsed year is reported as the canonical year number.

**Test Cases:** `rcb_tests/public_test_cases/feature6_year.json`

```json
{
    "description": "Round-trip a standalone calendar year through the JSON codec. A year is represented on the wire as a bare integer. Serialization emits that integer; deserialization accepts either an integer or a numeric string and reports the parsed value as the canonical year number.",
    "cases": [
        {
            "input": {"op": "serialize", "type": "year", "value": "1986"},
            "expected_output": "1986\n"
        },
        {
            "input": {"op": "deserialize", "type": "year", "value": 2013},
            "expected_output": "2013\n"
        }
    ]
}
```

---

### Feature 7: Year-Month

**As a developer**, I want to serialize and parse a specific month of a specific year (with no day), so I can exchange billing/reporting periods.

**Expected Behavior / Usage:**

For `serialize`, `value` is the canonical ISO-8601 year-month. When `as_timestamp` is true the output is a numeric array of exactly two integers — year and month. When `as_timestamp` is false the output is the ISO-8601 year-month as a quoted string. For `deserialize`, `value` may be the two-element numeric array or the ISO-8601 year-month string; the parsed value is reported in canonical ISO-8601 year-month form.

**Test Cases:** `rcb_tests/public_test_cases/feature7_year_month.json`

```json
{
    "description": "Round-trip a year-and-month value (a specific month of a specific year, with no day) through the JSON codec. The numeric-array wire form lists the year and the month number. The string wire form is an ISO-8601 year-month. Deserialization accepts either wire form and reports the parsed value in canonical ISO-8601 year-month form.",
    "cases": [
        {
            "input": {"op": "serialize", "type": "year_month", "as_timestamp": true, "value": "2013-08"},
            "expected_output": "[2013,8]\n"
        },
        {
            "input": {"op": "deserialize", "type": "year_month", "value": [2013, 8]},
            "expected_output": "2013-08\n"
        }
    ]
}
```

---

### Feature 8: Month-Day (Recurring)

**As a developer**, I want to serialize and parse a recurring month-and-day with no year (e.g. an anniversary), so I can exchange yearly recurrences.

**Expected Behavior / Usage:**

A month-day has a single wire form regardless of `as_timestamp`: an ISO-8601 month-day string that begins with a double dash. For `serialize`, `value` is the canonical month-day and the output is that string quoted. For `deserialize`, `value` is the month-day string; the parsed value is reported in canonical ISO-8601 month-day form.

**Test Cases:** `rcb_tests/public_test_cases/feature8_month_day.json`

```json
{
    "description": "Round-trip a recurring month-and-day value (a calendar position with no year, e.g. an anniversary) through the JSON codec. A month-day has a single wire form regardless of the timestamp flag: an ISO-8601 month-day string beginning with a double dash. Serialization emits that string; deserialization parses it back and reports the canonical ISO-8601 month-day form.",
    "cases": [
        {
            "input": {"op": "serialize", "type": "month_day", "value": "--01-17"},
            "expected_output": "\"--01-17\"\n"
        },
        {
            "input": {"op": "deserialize", "type": "month_day", "value": "--08-21"},
            "expected_output": "--08-21\n"
        }
    ]
}
```

---

### Feature 9: Language-Neutral Error Reporting

**As a developer**, I want failures reported as a stable, language-neutral contract, so callers can react programmatically without depending on host-runtime internals.

**Expected Behavior / Usage:**

Errors are emitted as plain `key=value` lines and never leak host-language type names, stack traces, or runtime-generated message text. When a `value` cannot be parsed into the requested `type`, the output is `[a specific error prefix — check the constant mapping]` followed by a `type=<requested type>` line. When the `type` name is not one of the supported temporal kinds, the output is `error=unknown_type` followed by a `type=<offending name>` line. When `op` is neither `serialize` nor `deserialize`, the output is `error=unknown_op` followed by an `op=<offending operation>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature9_errors.json`

```json
{
    "description": "Report failures as a stable, language-neutral error contract instead of leaking runtime details. When a value cannot be parsed into the requested temporal type, the codec reports an invalid-value error naming the requested type. When the requested operation is neither serialization nor deserialization, it reports an unknown-operation error echoing the offending operation. Each error is emitted as plain key=value lines.",
    "cases": [
        {
            "input": {"op": "deserialize", "type": "date", "value": "notadate"},
            "expected_output": "[a specific error prefix — check the constant mapping]\ntype=date\n"
        },
        {
            "input": {"op": "frobnicate", "type": "date", "value": "x"},
            "expected_output": "error=unknown_op\nop=frobnicate\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the codec for the eight temporal kinds described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result (or normalized error) to stdout, matching the per-feature contracts above. The request's `op` selects direction (`serialize` / `deserialize`), `type` selects the temporal kind, `value` carries the data, and the optional `as_timestamp` boolean (default `true`) selects the numeric wire form over the textual one where both exist. For serialization, the numeric form lists temporal components (and, for durations, a decimal seconds count); the textual form is the quoted ISO-8601 string. For deserialization, the canonical ISO-8601 form (or canonical number, for a year) of the parsed value is printed.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- handle all known date-time period formats consistent with other parse modes
