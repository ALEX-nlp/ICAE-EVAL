## Product Requirement Document

# Plain-Text Time-Tracking Engine - Product Requirements Document

## Project Goal

Build a time-tracking engine centred on a human-friendly plain-text file format. The engine lets developers represent days of work as plain text — a date, an optional target, a free-text summary, and a list of time entries — and then parse, validate, evaluate, query, and re-serialise that text programmatically. The goal is to let people record their time in a file they can read and edit by hand, while still getting machine-accurate totals, period breakdowns, and sanity checks.

---

## Background & Problem

Without this engine, developers who want to track time in plain text are forced to invent an ad-hoc format and hand-roll fragile parsing for it: stitching together regular expressions for dates, clock times, durations, and ranges; reconciling 12-hour and 24-hour notations; handling activities that cross midnight; summing signed durations; and second-guessing whether a typo silently corrupted a total. This leads to repetitive, error-prone boilerplate and totals nobody fully trusts.

With this engine, the text format is precisely defined and the parsing, evaluation, querying, and validation are provided as a clean library. Developers describe their days in a readable file and ask the engine for structured records, exact totals, calendar-period boundaries, filtered views, and warnings about likely mistakes.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial domain (value types, a text parser, a serialiser, an evaluation service, calendar periods, and a warning checker). It MUST NOT be a single "god file". Output a clear, multi-file directory tree that separates the value model (date, time, duration, range, tags, summary, record), the text parser and serialiser, and the higher-level services (evaluation, querying, calendar periods, warnings). Do not over-engineer, but reflect a production-grade repository structure.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box testing contract** for an execution adapter, NOT the internal data model. The core domain logic MUST remain completely decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating each JSON command into idiomatic calls on the core domain and rendering the result lines.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, validation, evaluation, period math, warning checks, and output formatting in distinct units.
   - **Open/Closed Principle (OCP):** New warning checks or new calendar-period kinds should be addable without modifying the evaluation core.
   - **Liskov Substitution Principle (LSP):** The three entry kinds (duration, range, open range) must be uniformly substitutable wherever an entry is consumed.
   - **Interface Segregation Principle (ISP):** Keep the value-type contracts small and cohesive.
   - **Dependency Inversion Principle (DIP):** High-level services depend on abstractions of the value model, not on I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core must be elegant and idiomatic to the target language.
   - **Resilience:** Every parsing and construction operation that can fail MUST model failure explicitly (e.g. a specific error type or a result value) rather than silently producing wrong data. The neutral error categories named in the contracts below (such as `malformed_duration`, `unrepresentable_date`, `illegal_range`, `impossible_operation`) are the externally observable error vocabulary.

---

## Core Features

### Feature 1: Duration Values

**As a developer**, I want to convert between signed time spans and their compact textual form, so I can store and read durations like `2h30m` and `-3h18m` reliably.

**Expected Behavior / Usage:**

A duration is a signed quantity measured in whole minutes. It can be rendered to text or parsed from text.

*1.1 Format a duration — Render a minute amount to compact text*

Given a signed amount of minutes, produce two renderings: a `plain` form and a `signed` form. The compact form omits any zero part and omits leading zeros: 150 minutes is `2h30m`, 900 minutes is `15h`, 1 minute is `1m`. Zero is `0m`. Negative amounts are prefixed with `-`. The `signed` form is identical to plain except that strictly positive values gain a leading `+`; zero is never signed.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_format_duration.json`

```json
{
    "description": "Render a signed minute amount into the canonical compact duration string, both without and with an explicit leading plus sign.",
    "cases": [
        {"input": {"action": "format_duration", "minutes": 0}, "expected_output": "plain=0m\nsigned=0m\n"},
        {"input": {"action": "format_duration", "minutes": 150}, "expected_output": "plain=2h30m\n[a specific signed string format constant — check snake_case format constants in api/v2]\n"},
        {"input": {"action": "format_duration", "minutes": -198}, "expected_output": "plain=-3h18m\nsigned=-3h18m\n"}
    ]
}
```

*1.2 Parse a duration — Read compact text into minutes*

Parse a duration string into its signed total number of minutes. A valid duration has an optional sign (`+`/`-`), an optional hour part (`<int>h`) and an optional minute part (`<int>m`); at least one of the two parts must be present. Leading zeros are allowed. When an hour part is present the minute part must be 0–59 (`1h60m` is rejected as `unrepresentable_duration`); when there is no hour part the minute part may exceed 59 (`120m` → 120). Empty input, embedded spaces, or non-numeric text are rejected as `malformed_duration`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_parse_duration.json`

```json
{
    "description": "Parse a duration string into a signed total number of minutes; reject malformed text and minute parts that exceed 59 when an hour part is present.",
    "cases": [
        {"input": {"action": "parse_duration", "text": "2h6m"}, "expected_output": "minutes=126\n"},
        {"input": {"action": "parse_duration", "text": "-2h5m"}, "expected_output": "minutes=-125\n"},
        {"input": {"action": "parse_duration", "text": "1h60m"}, "expected_output": "error=unrepresentable_duration\n"}
    ]
}
```

---

### Feature 2: Wall-Clock Time Values

**As a developer**, I want to parse and manipulate times of day, including activities that cross midnight, so I can model real working hours without ambiguity.

**Expected Behavior / Usage:**

A time is a point within a day (hour and minute). It also carries a *day-shift*: it can be associated with the previous day (prefix `<`), the current day, or the next day (suffix `>`). It records whether it was written using a 24-hour clock or a 12-hour (`am`/`pm`) clock.

*2.1 Parse a time — Read a clock value into its components*

Parse a time string into `hour` (0–23), `minute` (0–59), `day_shift` (`-1` yesterday, `0` today, `1` tomorrow) and `clock` (`24h` or `12h`). 24-hour and 12-hour notations are both accepted, as are the `<`/`>` shift markers. The special value `24:00` means midnight of the next day (`hour=0`, `day_shift=1`), and `<24:00` means midnight of the current day. Malformed strings (e.g. shift markers on both sides, missing minutes, too many leading zeros) yield `malformed_time`; syntactically valid but out-of-range values (e.g. `25:12`, `3:60`, `0:00am`) yield `invalid_time`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_parse_time.json`

```json
{
    "description": "Parse a wall-clock time string into its hour, minute, day-shift (yesterday/today/tomorrow) and clock convention (24-hour vs 12-hour), including the 24:00 boundary; reject malformed and out-of-range values.",
    "cases": [
        {"input": {"action": "parse_time", "text": "9:42"}, "expected_output": "hour=9\nminute=42\nday_shift=0\nclock=24h\n"},
        {"input": {"action": "parse_time", "text": "1:45pm"}, "expected_output": "hour=13\nminute=45\nday_shift=0\nclock=12h\n"},
        {"input": {"action": "parse_time", "text": "<3:43"}, "expected_output": "hour=3\nminute=43\nday_shift=-1\nclock=24h\n"},
        {"input": {"action": "parse_time", "text": "24:00"}, "expected_output": "hour=0\nminute=0\nday_shift=1\nclock=24h\n"}
    ]
}
```

*2.2 Add a duration to a time — Shift a clock value by minutes*

Add a signed amount of minutes to a time. The result may roll into the previous or next day and is rendered in canonical text (with `<`/`>` shift markers as needed). Adding minutes that would move the result more than one day away from the original (in either direction) is rejected as `impossible_operation`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_add_duration_to_time.json`

```json
{
    "description": "Add a signed minute amount to a wall-clock time, allowing the result to shift to the adjacent day; reject shifts of more than one day in either direction.",
    "cases": [
        {"input": {"action": "add_duration_to_time", "time": "11:30", "minutes": 30}, "expected_output": "result=12:00\n"},
        {"input": {"action": "add_duration_to_time", "time": "<23:45", "minutes": 735}, "expected_output": "result=12:00\n"},
        {"input": {"action": "add_duration_to_time", "time": "23:59>", "minutes": 1}, "expected_output": "error=impossible_operation\n"}
    ]
}
```

*2.3 Minutes from midnight — Project a time onto a single timeline*

Return the number of minutes from midnight of the record's day to the given time. Times shifted to the previous day are negative; times shifted to the next day exceed a full day (1440). This makes shifted times directly comparable on one continuous axis.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_time_midnight_offset.json`

```json
{
    "description": "Compute the number of minutes from midnight to a wall-clock time; times shifted to the previous day are negative, times shifted to the next day exceed a full day.",
    "cases": [
        {"input": {"action": "time_midnight_offset", "text": "0:01"}, "expected_output": "minutes=1\n"},
        {"input": {"action": "time_midnight_offset", "text": "<18:35"}, "expected_output": "minutes=-325\n"},
        {"input": {"action": "time_midnight_offset", "text": "5:35>"}, "expected_output": "minutes=1775\n"}
    ]
}
```

---

### Feature 3: Calendar Date Values

**As a developer**, I want to parse calendar dates and derive calendar facts from them, so I can group and label records by day, week, quarter, and year.

**Expected Behavior / Usage:**

A date is a day in the Gregorian calendar (year, month, day). It remembers whether it was written with dashes or slashes.

*3.1 Parse a date — Read a calendar date and remember its separator style*

Parse a date string in either `YYYY-MM-DD` (dashed) or `YYYY/MM/DD` (slashed) form. Both parts must use the same separator consistently, month and day must be two digits, and the year four digits. The result reports `year`, `month`, `day`, and `format` (`dashes` or `slashes`). Strings that do not match the shape yield `malformed_date`; well-formed strings whose values are not a real calendar day yield `unrepresentable_date`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_parse_date.json`

```json
{
    "description": "Parse a calendar date string in either dashed (YYYY-MM-DD) or slashed (YYYY/MM/DD) form, preserving which separator style was used; reject malformed strings and calendar-invalid dates.",
    "cases": [
        {"input": {"action": "parse_date", "text": "1856-10-22"}, "expected_output": "year=1856\nmonth=10\nday=22\nformat=dashes\n"},
        {"input": {"action": "parse_date", "text": "1856/10/22"}, "expected_output": "year=1856\nmonth=10\nday=22\nformat=slashes\n"},
        {"input": {"action": "parse_date", "text": "01.01.2000"}, "expected_output": "error=malformed_date\n"}
    ]
}
```

*3.2 Date attributes — Derive weekday, quarter, and ISO week*

Given a date by numeric year/month/day, derive its `weekday` (Monday = 1 … Sunday = 7), its `quarter` (1–4), and its ISO week as `week_number` together with the `week_year` that the week number belongs to (which may differ from the calendar year near year boundaries, e.g. 1 Jan 2021 belongs to week 53 of 2020). Calendar-invalid year/month/day combinations yield `unrepresentable_date`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_date_attributes.json`

```json
{
    "description": "Given a calendar date by its numeric year/month/day, derive its weekday (Monday=1..Sunday=7), its quarter (1-4), and its ISO week number together with the year that week number belongs to; reject calendar-invalid dates.",
    "cases": [
        {"input": {"action": "date_attributes", "year": 2005, "month": 4, "day": 15}, "expected_output": "weekday=5\nquarter=2\nweek_year=2005\nweek_number=15\n"},
        {"input": {"action": "date_attributes", "year": 2021, "month": 1, "day": 1}, "expected_output": "weekday=5\nquarter=1\nweek_year=2020\nweek_number=53\n"},
        {"input": {"action": "date_attributes", "year": 2005, "month": 13, "day": 15}, "expected_output": "error=unrepresentable_date\n"}
    ]
}
```

*3.3 Shift a date by days — Add or subtract calendar days*

Add a (possibly negative) number of days to a date, rolling correctly across month and year boundaries and accounting for leap years. The result is rendered as a dashed `YYYY-MM-DD` date.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_add_days.json`

```json
{
    "description": "Add (or subtract) a number of days to a calendar date, rolling correctly across month and year boundaries and accounting for leap years.",
    "cases": [
        {"input": {"action": "add_days", "year": 2005, "month": 12, "day": 31, "days": 1}, "expected_output": "date=2006-01-01\n"},
        {"input": {"action": "add_days", "year": 2020, "month": 2, "day": 28, "days": 1}, "expected_output": "date=2020-02-29\n"},
        {"input": {"action": "add_days", "year": 2005, "month": 12, "day": 31, "days": -1}, "expected_output": "date=2005-12-30\n"}
    ]
}
```

---

### Feature 4: Time Ranges

**As a developer**, I want to build a span between two clock times and get its length, so I can record "I worked from X to Y" and know how long it was.

**Expected Behavior / Usage:**

A range is built from a start time and an end time. It is rendered with a space-padded dash (`11:25 - 17:10`) and its duration is the number of minutes between the two endpoints projected onto the continuous midnight axis — so ranges that cross midnight via shifted times (e.g. `<23:30 - 8:10`) are measured correctly. The two endpoints may be equal (a zero-length range). A range whose end is chronologically before its start is rejected as `illegal_range`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_range_duration.json`

```json
{
    "description": "Build a time range from a start and end wall-clock time and compute its serialised form and its duration in minutes; ranges may span the adjacent day via shifted times; reject ranges whose end precedes their start.",
    "cases": [
        {"input": {"action": "range_duration", "start": "11:25", "end": "17:10"}, "expected_output": "value=11:25 - 17:10\nminutes=345\n"},
        {"input": {"action": "range_duration", "start": "<23:30", "end": "8:10"}, "expected_output": "value=<23:30 - 8:10\nminutes=520\n"},
        {"input": {"action": "range_duration", "start": "15:00", "end": "14:00"}, "expected_output": "error=illegal_range\n"}
    ]
}
```

---

### Feature 5: Tags

**As a developer**, I want to attach hashtags to my notes and query them, so I can categorise and later retrieve related work.

**Expected Behavior / Usage:**

Tags are hashtags embedded anywhere in summary text. A tag is a `#` followed by one or more letters, digits, or underscores; it ends at the first character outside that set.

*5.1 Extract tags — Collect all hashtags from text*

Given one or more lines of free text, return all tags, lowercased, de-duplicated, and sorted, each prefixed with `#` and joined by commas. Non-tag punctuation terminates a tag (e.g. `#GREAT-ish` yields `#great`).

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_extract_tags.json`

```json
{
    "description": "Extract all hashtags from one or more lines of free text, returning them lowercased, de-duplicated and sorted; a tag is a '#' followed by letters, digits or underscores and ends at the first other character.",
    "cases": [
        {"input": {"action": "extract_tags", "lines": ["Hello #world, I feel #great #TODAY"]}, "expected_output": "tags=#great,#today,#world\n"},
        {"input": {"action": "extract_tags", "lines": ["Hello #world, I feel", "#GREAT-ish today #123_test!"]}, "expected_output": "tags=#123_test,#great,#world\n"}
    ]
}
```

*5.2 Match a tag — Exact and prefix (fuzzy) matching*

Test whether the set of extracted tags contains a query. A plain query matches only a whole tag (case-insensitively, with or without a leading `#`). A query ending in `...` is a fuzzy match that succeeds for any tag starting with the given prefix. The output echoes the extracted `tags`, the `query`, and a boolean `matches`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_match_tag.json`

```json
{
    "description": "Test whether a set of extracted tags contains a query tag. An exact query matches a whole tag; a query ending in '...' matches any tag that starts with the given prefix (fuzzy match).",
    "cases": [
        {"input": {"action": "match_tag", "lines": ["Hello #world, I feel #GREAT-ish today #123_test!"], "query": "#123_..."}, "expected_output": "tags=#123_test,#great,#world\nquery=#123_...\nmatches=true\n"},
        {"input": {"action": "match_tag", "lines": ["Hello #world, I feel #GREAT-ish today #123_test!"], "query": "worl"}, "expected_output": "tags=#123_test,#great,#world\nquery=worl\nmatches=false\n"},
        {"input": {"action": "match_tag", "lines": ["Hello #world, I feel #GREAT-ish today #123_test!"], "query": "WoRl..."}, "expected_output": "tags=#123_test,#great,#world\nquery=WoRl...\nmatches=true\n"}
    ]
}
```

---

### Feature 6: Summary Validation

**As a developer**, I want the engine to reject summary text that would be ambiguous in the file format, so my files stay round-trippable.

**Expected Behavior / Usage:**

Summaries are made of lines. There are two flavours with different rules, because of where they sit in the file.

*6.1 Record summary — Lines under the date*

A record-level summary sits directly under the date line. Every line must be non-empty and must not begin with any blank character (a space, a tab, or any Unicode space separator). A valid summary reports `valid=true` and its `line_count`. Any violation yields `malformed_summary`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_validate_record_summary.json`

```json
{
    "description": "Validate a record-level summary (the text under the date). Every line must be non-empty and must not begin with any blank character (space, tab, or other Unicode space separators).",
    "cases": [
        {"input": {"action": "validate_record_summary", "lines": ["First line"]}, "expected_output": "valid=true\nline_count=1\n"},
        {"input": {"action": "validate_record_summary", "lines": ["First line", "Second line"]}, "expected_output": "valid=true\nline_count=2\n"},
        {"input": {"action": "validate_record_summary", "lines": [" Hello"]}, "expected_output": "error=malformed_summary\n"}
    ]
}
```

*6.2 Entry summary — Lines behind an entry*

An entry-level summary follows an entry. Here the *first* line may be empty or blank (it sits right after the entry value), but every *subsequent* line must be non-empty and non-blank. A valid summary reports `valid=true` and its `line_count`; a blank continuation line yields `malformed_summary`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_validate_entry_summary.json`

```json
{
    "description": "Validate an entry-level summary (the text behind an entry). The first line may be empty or blank, but every subsequent line must be non-empty and non-blank.",
    "cases": [
        {"input": {"action": "validate_entry_summary", "lines": ["", "Foo"]}, "expected_output": "valid=true\nline_count=2\n"},
        {"input": {"action": "validate_entry_summary", "lines": ["Foo", ""]}, "expected_output": "error=malformed_summary\n"}
    ]
}
```

---

### Feature 7: Document Parsing

**As a developer**, I want to parse a whole plain-text document into structured records, so I can work with my time data programmatically.

**Expected Behavior / Usage:**

A document is a sequence of records separated by blank lines. Each record is a contiguous block: a headline (a date, optionally followed by a should-total target wrapped as `(…!)`), an optional record summary, then any number of indented entries. An entry is a duration, a time range, or an open range (`… - ?`), optionally followed by an entry summary. Indentation must be uniform within a record (2–4 spaces or one tab). Both Unix and Windows line endings are accepted.

*7.1 Parse a document — Produce structured records*

Parse the text and report, for the whole document, the number of `records`; then for each record its `date`, its `should_total` in minutes (0 if absent), its `summary` (lines joined with `|`, empty if absent), and its `entries` count; then for each entry its `type` (`duration` / `range` / `open_range`), its serialised `value`, its `minutes` (an open range contributes 0), and its `summary` (lines joined with `|`).

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_parse_document.json`

```json
{
    "description": "Parse a plain-text document into structured records. Each record exposes its date, optional should-total (in minutes), optional record summary, and its ordered entries; each entry exposes its kind (duration / range / open_range), serialised value, duration in minutes, and summary (lines joined by '|').",
    "cases": [
        {"input": {"action": "parse_document", "text": "2000-01-01"}, "expected_output": "records=1\nrecord[0].date=2000-01-01\nrecord[0].should_total=0\nrecord[0].summary=\nrecord[0].entries=0\n"},
        {"input": {"action": "parse_document", "text": "1970-08-29 (8h15m!)\nRecord summary\n    1h Work\n    8:00 - 9:30\n    11:00 - ?\n        Open range"}, "expected_output": "records=1\nrecord[0].date=1970-08-29\nrecord[0].should_total=495\nrecord[0].summary=Record summary\nrecord[0].entries=3\nrecord[0].entry[0].type=duration\nrecord[0].entry[0].value=1h\nrecord[0].entry[0].minutes=60\nrecord[0].entry[0].summary=Work\nrecord[0].entry[1].type=range\nrecord[0].entry[1].value=8:00 - 9:30\nrecord[0].entry[1].minutes=90\nrecord[0].entry[1].summary=\nrecord[0].entry[2].type=open_range\nrecord[0].entry[2].value=11:00 - ?\nrecord[0].entry[2].minutes=0\nrecord[0].entry[2].summary=|Open range\n"},
        {"input": {"action": "parse_document", "text": "1999-05-31\n\n1999-06-03\n  1h"}, "expected_output": "records=2\nrecord[0].date=1999-05-31\nrecord[0].should_total=0\nrecord[0].summary=\nrecord[0].entries=0\nrecord[1].date=1999-06-03\nrecord[1].should_total=0\nrecord[1].summary=\nrecord[1].entries=1\nrecord[1].entry[0].type=duration\nrecord[1].entry[0].value=1h\nrecord[1].entry[0].minutes=60\nrecord[1].entry[0].summary=\n"}
    ]
}
```

*7.2 Parse errors — Report structural problems precisely*

When the text violates the format, report the number of `errors` and, for each error, a neutral `code`, the 1-based `line`, the cursor `position` within the line (excluding leading indentation), and the `length` of the offending span. Error codes are neutral categories such as `invalid_date`, `malformed_should_total`, `illegal_indentation`, `malformed_entry`, `illegal_range`, `duplicate_open_range`, `malformed_summary`, and `unrecognised_text_in_headline`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_parse_errors.json`

```json
{
    "description": "Report the structural errors found while parsing a document. Each error carries a neutral category, the 1-based line number, the cursor position within the line (excluding indentation), and the number of erroneous characters.",
    "cases": [
        {"input": {"action": "parse_errors", "text": "Hello 123"}, "expected_output": "errors=1\nerror[0].code=invalid_date\nerror[0].line=1\nerror[0].position=0\nerror[0].length=5\n"},
        {"input": {"action": "parse_errors", "text": "2020-01-01 (asdf!)"}, "expected_output": "errors=1\nerror[0].code=malformed_should_total\nerror[0].line=1\nerror[0].position=12\nerror[0].length=4\n"},
        {"input": {"action": "parse_errors", "text": "2020-01-01\n\t8:00- ?\n\t09:00 - ?"}, "expected_output": "errors=1\nerror[0].code=duplicate_open_range\nerror[0].line=3\nerror[0].position=1\nerror[0].length=9\n"}
    ]
}
```

---

### Feature 8: Canonical Serialisation

**As a developer**, I want to render parsed records back to canonical text, so that reformatting is deterministic and round-trips cleanly.

**Expected Behavior / Usage:**

Serialise records to the canonical text representation: four-space indentation, a single space on each side of a range dash, a should-total rendered as `(…!)` on the headline only when non-zero, and entry-summary continuation lines indented by two levels (eight spaces). Re-serialising already-canonical text reproduces it exactly; a record with only a date renders as just that date line followed by a newline. (Canonical output does not attempt to preserve the original whitespace styling of the input.)

**Test Cases:** `rcb_tests/public_test_cases/feature8_serialise_roundtrip.json`

```json
{
    "description": "Parse a document and re-serialise it into the canonical text representation. The canonical form uses 4-space indentation, a single space around range dashes, and places continuation summary lines at double indentation.",
    "cases": [
        {"input": {"action": "serialise_roundtrip", "text": "1999-05-31 (8h30m!)\nSummary that consists of multiple\nlines and contains a #tag as well.\n    5h30m This and that\n    -2h Something else\n    <18:00 - 4:00 Foo\n        Bar\n    19:00 - 20:00\n    20:01 - 0:15>\n    1:00am - 3:12pm\n    7:00 - ?\n"}, "expected_output": "1999-05-31 (8h30m!)\nSummary that consists of multiple\nlines and contains a #tag as well.\n    5h30m This and that\n    -2h Something else\n    <18:00 - 4:00 Foo\n        Bar\n    19:00 - 20:00\n    20:01 - 0:15>\n    1:00am - 3:12pm\n    7:00 - ?\n"},
        {"input": {"action": "serialise_roundtrip", "text": "2020-01-15"}, "expected_output": "2020-01-15\n"}
    ]
}
```

---

### Feature 9: Time Evaluation

**As a developer**, I want the engine to total my tracked time and compare it to my targets, so I can see how much I worked and whether I hit my goal.

**Expected Behavior / Usage:**

Totals are computed over the entries of one or more records. Positive durations add and negative durations subtract; overlapping ranges are each counted in full (never offset against each other).

*9.1 Total — Sum the tracked time*

Sum every entry across all records and report the number of `records` and the `total_minutes`. Open ranges are not counted (they have no end yet).

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_total.json`

```json
{
    "description": "Compute the total tracked time (in minutes) across all records in a document by summing every entry; durations and ranges contribute, open ranges contribute zero.",
    "cases": [
        {"input": {"action": "total", "text": "2020-01-01\n    3h\n    1h33m\n    13:49 - 17:12\n    1:02 - ?"}, "expected_output": "records=1\ntotal_minutes=476\n"},
        {"input": {"action": "total", "text": "2020-01-01"}, "expected_output": "records=1\ntotal_minutes=0\n"}
    ]
}
```

*9.2 Should-total difference — Compare actual against target*

Sum the should-total targets of all records, sum the actual tracked time, and report `should_total`, `actual`, and their `diff` (actual minus should), all in minutes. A negative diff means the target was not met.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_should_total_diff.json`

```json
{
    "description": "Compute the aggregate should-total of all records, the actual total, and the difference (actual minus should), all in minutes.",
    "cases": [
        {"input": {"action": "should_total_diff", "text": "2020-01-01 (8h!)\n    6h\n\n2020-01-02 (8h!)\n    9h"}, "expected_output": "should_total=960\nactual=900\ndiff=-60\n"}
    ]
}
```

*9.3 Hypothetical total — Total as if open ranges closed now*

Compute the total as if every open range were closed at a given reference timestamp (ISO 8601), and report whether an open range was actually counted via `ongoing`. An open range only contributes if its record is dated on the reference day or the day before (so its end can be reached); otherwise it contributes nothing and `ongoing` stays `false`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_hypothetical_total.json`

```json
{
    "description": "Compute the total tracked time as if every open range were closed at a given reference timestamp, and report whether an open range was actually counted (i.e. the record is ongoing). Open ranges only count if their record is the reference day or the day before.",
    "cases": [
        {"input": {"action": "hypothetical_total", "until": "2020-01-01T05:06:59-0000", "text": "2020-01-01\n    2h14m\n    <23:00 - 4:00\n    5:07 - ?"}, "expected_output": "total_minutes=434\nongoing=false\n"},
        {"input": {"action": "hypothetical_total", "until": "2020-01-01T10:48:13-0000", "text": "2020-01-01\n    2h14m\n    <23:00 - 4:00\n    5:07 - ?"}, "expected_output": "total_minutes=775\nongoing=true\n"}
    ]
}
```

---

### Feature 10: Querying

**As a developer**, I want to filter and sort my records, so I can focus on a date range, a project tag, or a chronological view.

**Expected Behavior / Usage:**

Queries operate on the records parsed from a document.

*10.1 Filter — Keep records that satisfy every clause*

Filter records by any combination of: on/after a date, on/before a date, and containing all of a set of tags. A tag clause matches if the tags appear in the record summary (keeping the whole record) or, failing that, narrows the record to only the entries whose own summary (combined with the record summary) carries the tags. Report the count of `matched` records, their `dates` (comma-separated, in original order), and the `total_minutes` of the matched (possibly tag-reduced) records.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_filter.json`

```json
{
    "description": "Filter records in a document. A record is kept only if it satisfies all of the supplied clauses: on/after a date, on/before a date, and containing all of a set of tags (tags may match the record summary or be narrowed to matching entries). The result reports the count, the matching dates, and the total minutes of the matching (possibly tag-reduced) records.",
    "cases": [
        {"input": {"action": "filter", "after": "2000-01-01", "text": "1999-12-31\n    5h #bar\n\n2000-01-01\n#foo\n    6h #bar\n\n2000-01-03\n#foo\n    4h #bar"}, "expected_output": "matched=2\ndates=2000-01-01,2000-01-03\ntotal_minutes=600\n"},
        {"input": {"action": "filter", "tags": ["bar"], "text": "1999-12-31\n    5h #bar\n\n2000-01-01\n#foo\n    15m\n    6h #bar\n\n2000-01-02\n#foo\n    7h"}, "expected_output": "matched=2\ndates=1999-12-31,2000-01-01\ntotal_minutes=660\n"}
    ]
}
```

*10.2 Sort — Order records by date*

Order the records by date, either oldest-first (`ascending: true`) or newest-first (`ascending: false`), and return the resulting `dates` (comma-separated).

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_sort.json`

```json
{
    "description": "Sort the records of a document by date, either oldest-first (ascending) or newest-first (descending), returning the resulting date order.",
    "cases": [
        {"input": {"action": "sort", "ascending": true, "text": "2000-01-02\n    1h\n\n1999-12-31\n    1h\n\n2000-01-01\n    1h"}, "expected_output": "dates=1999-12-31,2000-01-01,2000-01-02\n"},
        {"input": {"action": "sort", "ascending": false, "text": "2000-01-02\n    1h\n\n1999-12-31\n    1h\n\n2000-01-01\n    1h"}, "expected_output": "dates=2000-01-02,2000-01-01,1999-12-31\n"}
    ]
}
```

---

### Feature 11: Calendar Periods

**As a developer**, I want to compute the boundaries of calendar periods, so I can group records into weeks, months, quarters, and years and step backwards through them.

**Expected Behavior / Usage:**

Each period exposes its inclusive first day (`since`) and last day (`until`), plus the same for the immediately preceding period (`previous_since`, `previous_until`).

*11.1 Week — The Monday-to-Sunday week of a date*

Given a date, compute the week (Monday through Sunday) that contains it, and the week before it. Weeks may straddle month and year boundaries.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_period_week.json`

```json
{
    "description": "Given a date, compute the Monday-to-Sunday calendar week that contains it, plus the preceding week, expressed as inclusive start/end dates. Weeks may straddle month and year boundaries.",
    "cases": [
        {"input": {"action": "period_week", "date": "1987-05-19"}, "expected_output": "since=1987-05-18\nuntil=1987-05-24\nprevious_since=1987-05-11\nprevious_until=1987-05-17\n"},
        {"input": {"action": "period_week", "date": "2009-01-02"}, "expected_output": "since=2008-12-29\nuntil=2009-01-04\nprevious_since=2008-12-22\nprevious_until=2008-12-28\n"}
    ]
}
```

*11.2 Month — A calendar month written as YYYY-MM*

Given a month string `YYYY-MM`, compute its inclusive first and last day, and the same for the preceding month, accounting for varying month lengths and leap years. Malformed month strings yield `invalid_month_period`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_period_month.json`

```json
{
    "description": "Given a calendar month written as YYYY-MM, compute its inclusive first/last day and those of the preceding month, accounting for varying month lengths and leap years; reject malformed month strings.",
    "cases": [
        {"input": {"action": "period_month", "value": "2018-02"}, "expected_output": "since=2018-02-01\nuntil=2018-02-28\nprevious_since=2018-01-01\nprevious_until=2018-01-31\n"},
        {"input": {"action": "period_month", "value": "2016-02"}, "expected_output": "since=2016-02-01\nuntil=2016-02-29\nprevious_since=2016-01-01\nprevious_until=2016-01-31\n"}
    ]
}
```

*11.3 Quarter — The three-month quarter of a date*

Given a date, compute the calendar quarter (three months) that contains it, and the quarter before it, as inclusive start/end dates.

**Test Cases:** `rcb_tests/public_test_cases/feature11_3_period_quarter.json`

```json
{
    "description": "Given a date, compute the calendar quarter (three months) that contains it, plus the preceding quarter, expressed as inclusive start/end dates.",
    "cases": [
        {"input": {"action": "period_quarter", "date": "2005-05-19"}, "expected_output": "since=2005-04-01\nuntil=2005-06-30\nprevious_since=2005-01-01\nprevious_until=2005-03-31\n"},
        {"input": {"action": "period_quarter", "date": "1999-01-19"}, "expected_output": "since=1999-01-01\nuntil=1999-03-31\nprevious_since=1998-10-01\nprevious_until=1998-12-31\n"}
    ]
}
```

*11.4 Year — A calendar year written as YYYY*

Given a year string `YYYY`, compute its inclusive first and last day, and the same for the preceding year. Out-of-range or non-four-digit year strings yield `invalid_year_period`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_4_period_year.json`

```json
{
    "description": "Given a calendar year written as YYYY, compute its inclusive first/last day and those of the preceding year; reject malformed or out-of-range year strings.",
    "cases": [
        {"input": {"action": "period_year", "value": "2008"}, "expected_output": "since=2008-01-01\nuntil=2008-12-31\nprevious_since=2007-01-01\nprevious_until=2007-12-31\n"}
    ]
}
```

---

### Feature 12: Sanity Warnings

**As a developer**, I want the engine to flag likely mistakes in my records, so I can catch typos before they corrupt my reports.

**Expected Behavior / Usage:**

Given the records and a reference timestamp (ISO 8601, "now"), scan for likely mistakes and report the number of `warnings` and, for each, a neutral `kind` and the `date` of the offending record. The checks are: an unclosed open range that can no longer be closed (`unclosed_open_range`) — an open range in the past that is not on the reference day, nor on the day before when there is no record yet on the reference day; an entry dated in the future beyond a short grace period (`future_entry`); two time ranges within one record that overlap (`overlapping_ranges`); and a record whose total tracked time exceeds 24 hours (`exceeds_24h`). A record with no detected problems produces no warnings.

**Test Cases:** `rcb_tests/public_test_cases/feature12_warnings.json`

```json
{
    "description": "Scan records against a reference timestamp for likely mistakes and report each warning's neutral kind and the date of the offending record. Checks cover unclosed open ranges in the past, entries dated in the future, overlapping time ranges within a record, and records whose total exceeds 24 hours.",
    "cases": [
        {"input": {"action": "warnings", "now": "2000-03-05T12:00:00-0000", "text": "2000-03-03\n    8:00 - ?\n\n2000-03-05"}, "expected_output": "warnings=1\nwarning[0].kind=unclosed_open_range\nwarning[0].date=2000-03-03\n"},
        {"input": {"action": "warnings", "now": "2000-03-05T12:00:00-0000", "text": "2000-03-05\n    8:00 - 9:00\n    8:30 - 9:30"}, "expected_output": "warnings=1\nwarning[0].kind=overlapping_ranges\nwarning[0].date=2000-03-05\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing all features above — the value model (date, time, duration, range, tags, summaries, records and entries), the text parser and canonical serialiser, and the services (evaluation, querying, calendar periods, warnings). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core system. It reads a single JSON command object from stdin (the `action` field selects the operation; remaining fields are its arguments), invokes the appropriate core logic, and prints the result to stdout as newline-terminated `key=value` lines, strictly matching the per-leaf-feature contracts above. All failures are rendered as a single neutral `error=<category>` line; no host-language runtime artefacts ever appear in stdout. This adapter MUST be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_format_duration.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_format_duration@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same padding logic as the timestamp module
