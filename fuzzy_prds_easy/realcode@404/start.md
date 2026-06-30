## Product Requirement Document

# Spreadsheet Document Serialization Engine — Product Requirements

## Project Goal

Build a deterministic spreadsheet-document core that turns an in-memory description of a worksheet — its cells, rows, columns, values, declared types, formulas, merged regions, page-layout settings, view panes, filters and named ranges — into the exact Office Open XML (OOXML) fragments that a spreadsheet file is assembled from. It also provides the small pure conversions those fragments depend on: translating between numeric grid coordinates and textual cell references, expanding ranges, inferring and coercing value types, and converting calendar dates and clock times to their spreadsheet serial numbers. The goal is to let developers produce valid spreadsheet documents programmatically without having to memorize the OOXML schema or hand-assemble brittle XML.

---

## Background & Problem

Without such an engine, developers who need to emit spreadsheet files are forced to assemble OOXML by hand: concatenating element strings, remembering that columns are labelled with a bijective base-26 alphabet, that rows are one-based, that dates are stored as serial day counts from an epoch that predates 1900, that booleans serialize as `1`/`0`, that formulas drop their leading `=`, and that dozens of layout records (margins, print options, protection flags, panes, filters) each have their own attribute spelling and default-omission rules. This is repetitive, error-prone, and produces files that silently fail to open.

With this engine, the developer hands over structured values and receives the precise, schema-valid fragments. Every operation is **pure and deterministic**: identical input always yields byte-for-byte identical output, with no dependence on the clock, locale, filesystem, or random state. Invalid input is rejected through a single neutral error channel rather than producing a malformed document.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial domain with many distinct serializable record types and several pure conversion utilities. It MUST NOT be a single "god file". Output a clear, multi-file directory tree that separates the conversion utilities, the value/typing model, and the individual serializable records, plus a separate execution adapter. Do not over-engineer the pure helpers, but do not collapse the record types into one monolith either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core domain and rendering results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core serialization, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** Adding a new serializable record type must not require modifying existing ones.
   - **Liskov Substitution Principle (LSP):** Records that share a serialization protocol must be substitutable through it.
   - **Interface Segregation Principle (ISP):** Keep the per-record interfaces small and cohesive.
   - **Dependency Inversion Principle (DIP):** High-level routing depends on a serialization abstraction, not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core must be elegant and idiomatic to the target language, hiding XML-assembly details.
   - **Resilience:** Invalid values (negative margins, non-boolean flags, unrecognized enumerated names, missing required attributes, out-of-range coordinates) must be handled gracefully and modelled as errors rather than producing malformed output.

### Execution Contract (wire protocol)

All behaviour is exercised through a single command-line entry point that behaves as a request/response filter:

- It reads **exactly one JSON object** from standard input and writes a single result string to standard output, with **no trailing newline** and nothing else (no logs, prompts, or metadata).
- Every request object has a string field `op` selecting the operation; the remaining fields are that operation's arguments, described per feature below.
- Results that contain several items are returned as lines joined by a single newline (`\n`), in the same order as the corresponding inputs.
- If a request is malformed or an operation cannot be carried out (invalid value, missing required attribute, out-of-range reference), the entry point prints the neutral token `[page margins defaults — left/right 0.75, top/bottom 1.0]` (for value/validation problems) or `error=invalid_request` (for structurally unusable requests) instead of a result. No host-language exception name, stack trace, or runtime-generated message text is ever exposed.

Because JSON cannot natively express every value a spreadsheet cell can hold, individual values are passed as small **tagged objects** `{"kind": ...}`:

| kind | meaning | extra field |
|------|---------|-------------|
| `string`   | text value | `v` (the text) |
| `integer`  | whole number | `v` |
| `float`    | floating-point number | `v` |
| `bool`     | boolean | `v` (true/false) |
| `nil`      | absence of a value | — |
| `array`    | an empty list value | — |
| `date`     | a calendar date, ISO `YYYY-MM-DD` | `v` |
| `time`     | an instant, ISO date-time | `v` |
| `richtext` | a styled-text value | — |

---

## Core Features

### Feature 1: Column and Row Labels

**As a developer**, I want to translate zero-based grid ordinals into the human-facing labels a spreadsheet uses, so I can address cells without hand-rolling the base-26 column alphabet.

**Expected Behavior / Usage:**

*1.1 Column Label — convert a column ordinal to its column letters*

A zero-based column ordinal maps to a column label under a bijective base-26 scheme: ordinal 0 is the first single letter, single-letter labels run out after 26 values and then grow to two letters, then three, and so on (so the value just past the last single letter is `AA`). The request lists column ordinals; the response emits one label per line in order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_column_label.json`

```json
{
  "description": "Convert a zero-based column ordinal into its spreadsheet column label using the bijective base-26 scheme (the first column is a single letter, and after the final single-letter label the labels grow to two letters, then three, and so on). Given a list of column ordinals, emit one label per line in the same order.",
  "cases": [
    {
      "input": {"op": "column_label", "indices": [0, 25, 1, 26, 702, 727, 728, 2048]},
      "expected_output": "A\nZ\nB\nAA\nAAA\nAAZ\nABA\nBZU"
    }
  ]
}
```

*1.2 Row Label — convert a row ordinal to its one-based label*

A zero-based row ordinal maps to a one-based row label by adding one. The request lists row ordinals; the response emits one label per line in order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_row_label.json`

```json
{
  "description": "Render a standalone one-based row label from a zero-based row ordinal. Row labels are simply the ordinal plus one. Given a list of row ordinals, emit one label per line in the same order.",
  "cases": [
    {
      "input": {"op": "row_label", "indices": [0, 99, 1, 25, 9998]},
      "expected_output": "1\n100\n2\n26\n9999"
    }
  ]
}
```

---

### Feature 2: Cell Name Parsing and Construction

**As a developer**, I want to convert between textual cell names and numeric index pairs in both directions, so I can move freely between user-facing references and grid math.

**Expected Behavior / Usage:**

*2.1 Parse Cell Name — name to index pair*

A textual cell name is a column label followed by a one-based row number. Parsing yields a pair of zero-based indices, column ordinal first then row ordinal. The request lists names; the response emits one comma-separated pair per line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_parse_cell_name.json`

```json
{
  "description": "Parse a textual cell name composed of a column label followed by a one-based row number into a pair of zero-based indices (column ordinal and row ordinal). Given a list of cell names, emit one comma-separated index pair per line, column first then row.",
  "cases": [
    {
      "input": {"op": "parse_cell_name", "names": ["A3", "Z3", "B3", "AA3", "AAA3", "AAZ3", "ABA3", "BZU3"]},
      "expected_output": "0,2\n25,2\n1,2\n26,2\n702,2\n727,2\n728,2\n2048,2"
    }
  ]
}
```

*2.2 Build Cell Reference — index pair to name*

A zero-based column ordinal and zero-based row ordinal compose into a full cell reference (column label plus one-based row number). The request lists index pairs; the response emits one reference per line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_cell_reference.json`

```json
{
  "description": "Compose a full cell reference (column label plus one-based row number) from a zero-based column ordinal and a zero-based row ordinal. Each input pair is rendered as one reference, emitted one per line in order.",
  "cases": [
    {
      "input": {"op": "cell_reference", "coords": [[0, 0], [25, 25], [1, 9], [26, 99]]},
      "expected_output": "A1\nZ26\nB10\nAA100"
    }
  ]
}
```

---

### Feature 3: Range Operations

**As a developer**, I want to expand, bound, and merge rectangular cell ranges, so I can reason about regions of a sheet as first-class values.

**Expected Behavior / Usage:**

*3.1 Expand Range — enumerate every cell in a rectangle*

A range is a start cell and an end cell separated by a colon. Expanding it produces the full grid of individual references it covers, ordered row by row and, within each row, left to right. Each requested range is rendered as lines of comma-separated references; successive ranges are separated by a line containing two equals signs.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_expand_range.json`

```json
{
  "description": "Expand a rectangular reference range (a start cell and an end cell separated by a colon) into the full grid of individual cell references it covers, ordered row by row and, within each row, left to right. Each requested range is rendered as lines of comma-separated references, and successive ranges are separated by a line containing two equals signs.",
  "cases": [
    {
      "input": {"op": "expand_range", "ranges": ["A1:C1", "A1:C2", "Z5:AB6"]},
      "expected_output": "A1,B1,C1\n==\nA1,B1,C1\nA2,B2,C2\n==\nZ5,AA5,AB5\nZ6,AA6,AB6"
    }
  ]
}
```

*3.2 Bounding Range — span a set of cells*

Given a collection of cells, the bounding range is the rectangle from the top-left to the bottom-right cell, independent of the order the cells are supplied. A relative result joins the two corner references with a colon. An absolute result additionally pins both row and column with anchor markers and prefixes the originating sheet name; the sheet name is single-quoted, embedded single quotes are doubled, and characters reserved in XML are entity-escaped. Cells are laid out left to right in a single row; a `pick` list selects cells by position, or the whole row is used when `pick` is omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_bounding_range.json`

```json
{
  "description": "Compute the bounding reference range that spans a collection of cells, independent of the order in which the cells are supplied. A relative result is just the top-left and bottom-right references joined by a colon. An absolute result additionally pins both row and column with anchor markers and prefixes the originating sheet name, with the sheet name quoted and any embedded quote characters doubled; reserved XML characters in the sheet name are entity-escaped. Cells are laid out left to right in a single row; the 'pick' list selects cells by position, or the whole row is used when 'pick' is omitted.",
  "cases": [
    {
      "input": {"op": "bounding_range", "sheet_name": "Sheet1", "num_cells": 2, "pick": [1, 0], "absolute": false},
      "expected_output": "A1:B1"
    },
    {
      "input": {"op": "bounding_range", "sheet_name": "Sheet <'>\" 1", "num_cells": 2, "pick": [1, 0], "absolute": true},
      "expected_output": "'Sheet &lt;''&gt;&quot; 1'!$A$1:$B$1"
    },
    {
      "input": {"op": "bounding_range", "sheet_name": "Sheet1", "num_cells": 3, "absolute": false},
      "expected_output": "A1:C1"
    }
  ]
}
```

*3.3 Merged Range — combine two endpoints into one region*

Merging one cell with a target (given either as a textual reference or as another cell in the same row) yields the range running from the top-left to the bottom-right of the two endpoints, independent of which endpoint initiates the merge. Cells are placed left to right in a single row and referenced by position; one merged range string is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_merged_range.json`

```json
{
  "description": "Compute the merged reference range produced by merging one cell with a target, where the target is given either as a textual cell reference or as another cell in the same row. The resulting range runs from the top-left to the bottom-right of the two endpoints and is independent of which endpoint initiates the merge. Cells are placed left to right in a single row and referenced by position; one merged range string is emitted.",
  "cases": [
    {"input": {"op": "merge", "num_cells": 3, "src": 0, "target_ref": "A2"}, "expected_output": "A1:A2"},
    {"input": {"op": "merge", "num_cells": 3, "src": 0, "target_index": 2}, "expected_output": "A1:C1"},
    {"input": {"op": "merge", "num_cells": 3, "src": 2, "target_index": 0}, "expected_output": "A1:C1"}
  ]
}
```

---

### Feature 4: Value Type Handling

**As a developer**, I want values to be classified and coerced into spreadsheet storage types, so cells store the right kind of data whether or not I declare a type explicitly.

**Expected Behavior / Usage:**

*4.1 Type Inference — classify an untyped value*

When no explicit type is declared, the storage type is inferred. Calendar dates, clock times, and booleans are recognized from their native kinds. Remaining values are classified by textual shape: a bare optionally-signed run of digits is `integer`; a decimal or scientific-notation number whose magnitude is within the representable floating range is `float`; a combined date-and-time string without a zone offset is the temporal literal `iso_8601`; a styled-text value is `richtext`; everything else — including out-of-range scientific notation and offset-bearing date-time strings — is `string`. One inferred type name is emitted per value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_type_inference.json`

```json
{
  "description": "Infer the storage data type of a value when no explicit type is declared. Calendar dates, clock times, and boolean values are recognized from their native object kinds. Remaining values are classified by textual shape: a bare optionally-signed run of digits is an integer; a decimal or scientific-notation number whose magnitude is within the representable floating range is a float; a date-time string in the extended combined-calendar-and-time notation without a zone offset is treated as a temporal literal; a styled-text object is rich text; everything else, including out-of-range scientific notation and offset-bearing date-time strings, is a string. Each input value is tagged with its source kind, and one inferred type name is emitted per value.",
  "cases": [
    {
      "input": {"op": "infer_type", "values": [
        {"kind": "float", "v": 1.0},
        {"kind": "string", "v": "1e1"},
        {"kind": "string", "v": "1e308"},
        {"kind": "string", "v": "1e309"},
        {"kind": "string", "v": "1e-1"},
        {"kind": "integer", "v": 1},
        {"kind": "date", "v": "2024-01-15"},
        {"kind": "time", "v": "2024-01-15T10:00:00Z"},
        {"kind": "array"},
        {"kind": "string", "v": "d"},
        {"kind": "nil"},
        {"kind": "integer", "v": -1},
        {"kind": "bool", "v": true},
        {"kind": "bool", "v": false},
        {"kind": "richtext"},
        {"kind": "string", "v": "2008-08-30T01:45:36.123+09:00"},
        {"kind": "string", "v": "2008-08-30T01:45:36.123"}
      ]},
      "expected_output": "float\nfloat\nfloat\nstring\nfloat\ninteger\ndate\ntime\nstring\nstring\nstring\ninteger\nboolean\nboolean\nrichtext\nstring\niso_8601"
    }
  ]
}
```

*4.2 Value Casting — coerce a value into a declared type*

Coercing a value into a declared storage type produces the stored value: casting to text yields the string form; casting to integer or float yields the numeric form; casting a boolean yields `1` for true and `0` for false; a null value stays null regardless of declared type (rendered as an empty line); and casting to the zone-offset date-time literal type leaves the supplied text unchanged. One stored value is emitted per item.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_value_casting.json`

```json
{
  "description": "Coerce a value into a declared storage type and report the resulting stored value. Casting to the textual type yields the value's string form; casting to the integer or float type yields its numeric form; casting a boolean yields one for true and zero for false; a null value stays null regardless of declared type; and casting to the zone-offset date-time literal type leaves the supplied text unchanged. Each item pairs a target type with a tagged source value, and one stored value is emitted per item (a null value renders as an empty line).",
  "cases": [
    {
      "input": {"op": "cast", "items": [
        {"type": "string", "value": {"kind": "float", "v": 1.0}},
        {"type": "integer", "value": {"kind": "float", "v": 1.0}},
        {"type": "float", "value": {"kind": "string", "v": "1.0"}},
        {"type": "string", "value": {"kind": "nil"}},
        {"type": "boolean", "value": {"kind": "bool", "v": true}},
        {"type": "boolean", "value": {"kind": "bool", "v": false}},
        {"type": "iso_8601", "value": {"kind": "string", "v": "2012-10-10T12:24"}}
      ]},
      "expected_output": "1.0\n1\n1.0\n\n1\n0\n2012-10-10T12:24"
    }
  ]
}
```

---

### Feature 5: Date and Time Serial Numbers

**As a developer**, I want calendar dates and clock instants converted to the numeric serials a spreadsheet stores, so temporal cells round-trip correctly under either epoch convention.

**Expected Behavior / Usage:**

*5.1 Date Serial — date to day count*

A calendar date converts to a serial number: the count of days from the workbook epoch. Two epoch conventions are exercised: the default convention whose day-zero predates the start of 1900, and the alternate convention anchored at the start of 1904. Each case selects a convention and lists dates; one serial number is emitted per date.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_date_serial.json`

```json
{
  "description": "Convert a calendar date to its spreadsheet serial number, the count of days from the workbook's epoch. Two epoch conventions are exercised: the default convention whose day-zero predates the start of 1900, and the alternate convention anchored at the start of 1904. Each case selects an epoch convention and lists dates; one serial number is emitted per date.",
  "cases": [
    {
      "input": {"op": "serialize_date", "date1904": false, "dates": ["1893-08-05", "1900-01-01", "1910-02-03", "2006-02-01", "9999-12-31"]},
      "expected_output": "-2338.0\n2.0\n3687.0\n38749.0\n2958465.0"
    },
    {
      "input": {"op": "serialize_date", "date1904": true, "dates": ["1893-08-05", "1904-01-01", "1910-02-03", "2006-02-01", "9999-12-31"]},
      "expected_output": "-3800.0\n0.0\n2225.0\n37287.0\n2957003.0"
    }
  ]
}
```

*5.2 Time Serial — instant to fractional day count*

An instant converts to a fractional serial number whose integer part is days from the workbook epoch and whose fractional part is the elapsed fraction of the day. The same two epoch conventions apply; instants are supplied in the zero-offset zone. One serial number is emitted per instant.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_time_serial.json`

```json
{
  "description": "Convert an instant in time to its fractional spreadsheet serial number, where the integer part is days from the workbook epoch and the fractional part is the elapsed fraction of the day. Two epoch conventions are exercised: the default convention whose day-zero predates the start of 1900, and the alternate convention anchored at the start of 1904. Times are supplied in the zero-offset zone. Each case selects an epoch convention and lists instants; one serial number is emitted per instant.",
  "cases": [
    {
      "input": {"op": "serialize_time", "date1904": false, "times": ["1893-08-05T00:00:01Z", "1899-12-28T18:00:00Z", "1910-02-03T10:05:54Z", "1900-01-01T12:00:00Z", "9999-12-31T23:59:59Z"]},
      "expected_output": "-2337.999988425926\n-1.25\n3687.420763888889\n2.5\n2958465.999988426"
    },
    {
      "input": {"op": "serialize_time", "date1904": true, "times": ["1893-08-05T00:00:01Z", "1910-02-03T10:05:54Z", "1904-01-01T12:00:00Z", "9999-12-31T23:59:59Z"]},
      "expected_output": "-3799.999988425926\n2225.420763888889\n0.5\n2957003.999988426"
    }
  ]
}
```

---

### Feature 6: Cell Serialization

**As a developer**, I want a single cell rendered to its exact XML fragment, so the value, type marker, style and formula handling all follow the storage schema.

**Expected Behavior / Usage:**

The opening element always carries the cell reference (column label plus one-based row) and a style index. A null-valued cell becomes a self-closing element with no body. A numeric cell carries a numeric type marker and a value body. A formula cell — a string beginning with `=`, when formula escaping is disabled — is written with a string type marker and a formula body holding the expression without its leading `=`. An array-formula cell (wrapped in braces with a leading `=`) is written with a formula body marked as an array over its own reference. When formula escaping is enabled, or for an explicitly textual value, the content is emitted verbatim as an inline string. The input describes one cell plus its row and column position; the output is the exact XML string.

**Test Cases:** `rcb_tests/public_test_cases/feature6_cell_serialization.json`

```json
{
  "description": "Serialize a single grid cell to its XML fragment. The opening element always carries the cell reference (column label plus one-based row) and a style index. A null-valued cell is written as a self-closing element with no body. A numeric cell carries a numeric type marker and a value body. A formula cell (a string beginning with an equals sign, when formula escaping is disabled) is written with a string type marker and a formula body holding the expression without its leading equals sign. An array-formula cell (wrapped in braces with a leading equals sign) is written with a formula body marked as an array over its own reference. When formula escaping is enabled, or for an explicitly textual value, the content is emitted verbatim as an inline string. Inputs describe one cell plus its row and column position; the emitted fragment is the exact XML string.",
  "cases": [
    {
      "input": {"op": "serialize_cell", "value": {"kind": "float", "v": 1.0}, "type": "float", "style": 1, "r_index": 1, "c_index": 1},
      "expected_output": "<c r=\"B2\" s=\"1\" t=\"n\"><v>1.0</v></c>"
    },
    {
      "input": {"op": "serialize_cell", "value": {"kind": "nil"}, "style": 1, "r_index": 1, "c_index": 1},
      "expected_output": "<c r=\"B2\" s=\"1\" />"
    },
    {
      "input": {"op": "serialize_cell", "value": {"kind": "string", "v": "=IF(2+2=4,4,5)"}, "escape_formulas": false, "r_index": 0, "c_index": 0},
      "expected_output": "<c r=\"A1\" s=\"0\" t=\"str\">[escape_formulas=false string value starting with = — e.g., an IF formula]</c>"
    },
    {
      "input": {"op": "serialize_cell", "value": {"kind": "string", "v": "=IF(2+2=4,4,5)"}, "escape_formulas": true, "r_index": 0, "c_index": 0},
      "expected_output": "<c r=\"A1\" s=\"0\" t=\"inlineStr\"><is><t>=IF(2+2=4,4,5)</t></is></c>"
    },
    {
      "input": {"op": "serialize_cell", "value": {"kind": "string", "v": "{=SUM(C2:C11*D2:D11)}"}, "escape_formulas": false, "r_index": 0, "c_index": 0},
      "expected_output": "<c r=\"A1\" s=\"0\" t=\"str\"><f t=\"array\" ref=\"A1\">SUM(C2:C11*D2:D11)</f></c>"
    }
  ]
}
```

---

### Feature 7: Row Serialization

**As a developer**, I want a worksheet row rendered to its exact XML fragment, so row-level attributes and the row's cells are emitted together correctly.

**Expected Behavior / Usage:**

The row element always carries its one-based row position. Optional row-level attributes are emitted only when set: a hidden flag, an outline nesting level, a collapsed flag, a custom-format flag together with a row style index, and — when a height is supplied — a custom-height flag together with the height value. Any cells belonging to the row are serialized in order inside the element. The input describes the row's values, optional attributes, and its row position; the output is the exact XML string.

**Test Cases:** `rcb_tests/public_test_cases/feature7_row_serialization.json`

```json
{
  "description": "Serialize a worksheet row to its XML fragment. The row element always carries its one-based row position. Optional row-level attributes are emitted when set: a hidden flag, an outline nesting level, a collapsed flag, a custom-format flag together with a row style index, and, when a height is supplied, a custom-height flag together with the height value. Any cells belonging to the row are serialized in order inside the row element. Inputs describe the row's values, optional attributes, and its row position; the emitted fragment is the exact XML string.",
  "cases": [
    {
      "input": {"op": "serialize_row", "values": [], "r_index": 0},
      "expected_output": "<row r=\"1\" ></row>"
    },
    {
      "input": {"op": "serialize_row", "values": [], "height": 20, "s": 1, "outline_level": 2, "collapsed": true, "hidden": true, "r_index": 0},
      "expected_output": "<row hidden=\"1\" outlineLevel=\"2\" collapsed=\"1\" customFormat=\"1\" s=\"1\" customHeight=\"1\" ht=\"20\" r=\"1\" ></row>"
    },
    {
      "input": {"op": "serialize_row", "values": [{"kind": "integer", "v": 1}], "height": 20, "r_index": 0},
      "expected_output": "<row customHeight=\"1\" ht=\"20\" r=\"1\" ><c r=\"A1\" s=\"0\" t=\"n\"><v>1</v></c></row>"
    }
  ]
}
```

---

### Feature 8: Column Serialization

**As a developer**, I want a column-information record rendered to its exact XML fragment, so column spans and widths are emitted with the right flags and clamping.

**Expected Behavior / Usage:**

The element carries the first and last affected column indices. When a width is assigned, the record also records the width together with a best-fit flag and a custom-width flag; any width exceeding the maximum permitted column width is clamped down to that maximum. The input describes the column span and an optional width; the output is the exact XML string.

**Test Cases:** `rcb_tests/public_test_cases/feature8_column_serialization.json`

```json
{
  "description": "Serialize a column-information record to its XML fragment. The element carries the first and last affected column indices. When a width is assigned, the record also records the width together with a best-fit flag and a custom-width flag; any width exceeding the maximum permitted column width is clamped down to that maximum. Inputs describe the column span and an optional width; the emitted fragment is the exact XML string.",
  "cases": [
    {
      "input": {"op": "serialize_column", "min": 1, "max": 1, "width": 100},
      "expected_output": "<col width=\"100\" min=\"1\" max=\"1\" bestFit=\"1\" customWidth=\"1\" />"
    },
    {
      "input": {"op": "serialize_column", "min": 1, "max": 1, "width": 31337},
      "expected_output": "<col width=\"255\" min=\"1\" max=\"1\" bestFit=\"1\" customWidth=\"1\" />"
    },
    {
      "input": {"op": "serialize_column", "min": 1, "max": 1, "width": 3},
      "expected_output": "<col width=\"3\" min=\"1\" max=\"1\" bestFit=\"1\" customWidth=\"1\" />"
    }
  ]
}
```

---

### Feature 9: Page Margins

**As a developer**, I want printable page margins rendered to their exact XML fragment with validation, so layout settings are valid and out-of-range values are rejected.

**Expected Behavior / Usage:**

Margins are given in inches for the left, right, top, bottom, header and footer edges. Margins not supplied keep their defaults (three-quarters of an inch for left/right, one inch for top/bottom, half an inch for header/footer). Every margin must be a non-negative number; a negative margin is rejected and reported as `[page margins defaults — left/right 0.75, top/bottom 1.0]`. The emitted fragment lists all six margins.

**Test Cases:** `rcb_tests/public_test_cases/feature9_page_margins.json`

```json
{
  "description": "Serialize the printable page-margin settings to their XML fragment. Margins are given in inches for the left, right, top, bottom, header and footer edges. Any margins not supplied keep their defaults (three-quarters of an inch for left/right, one inch for top/bottom, half an inch for header/footer). Every margin must be a non-negative number; supplying a negative margin is rejected and reported as a normalized error. The emitted fragment lists all six margins.",
  "cases": [
    {
      "input": {"op": "page_margins", "props": {"left": 1.1, "right": 1.2, "top": 1.3, "bottom": 1.4, "header": 0.8, "footer": 0.9}},
      "expected_output": "<pageMargins left=\"1.1\" right=\"1.2\" top=\"1.3\" bottom=\"1.4\" header=\"0.8\" footer=\"0.9\" />"
    },
    {
      "input": {"op": "page_margins", "props": {}},
      "expected_output": "<pageMargins left=\"0.75\" right=\"0.75\" top=\"1.0\" bottom=\"1.0\" header=\"0.5\" footer=\"0.5\" />"
    },
    {
      "input": {"op": "page_margins", "props": {"left": -1.2}},
      "expected_output": "[page margins defaults — left/right 0.75, top/bottom 1.0]"
    }
  ]
}
```

---

### Feature 10: Print Options

**As a developer**, I want the worksheet print options rendered to their exact XML fragment with validation, so each boolean toggle is emitted correctly and bad values are rejected.

**Expected Behavior / Usage:**

Four independent boolean flags control whether grid lines are printed, whether row/column headings are printed, and whether the printed content is centered horizontally and vertically. Each flag defaults to off. A flag accepts only a boolean-ish value; a non-boolean value (such as an arbitrary integer) is rejected and reported as `[page margins defaults — left/right 0.75, top/bottom 1.0]`. The emitted fragment carries all four flags rendered as `1` or `0`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_print_options.json`

```json
{
  "description": "Serialize the worksheet print options to their XML fragment. Four independent boolean flags control whether grid lines are printed, whether row/column headings are printed, and whether the printed content is centered horizontally and vertically. Each flag defaults to off. A flag only accepts a boolean-ish value; a non-boolean value (such as an arbitrary integer) is rejected and reported as a normalized error. The emitted fragment carries all four flags rendered as 1 or 0.",
  "cases": [
    {
      "input": {"op": "print_options", "props": {"grid_lines": true, "headings": true, "horizontal_centered": true, "vertical_centered": true}},
      "expected_output": "<printOptions gridLines=\"1\" headings=\"1\" horizontalCentered=\"1\" verticalCentered=\"1\" />"
    },
    {
      "input": {"op": "print_options", "props": {"grid_lines": true, "headings": true}},
      "expected_output": "<printOptions gridLines=\"1\" headings=\"1\" horizontalCentered=\"0\" verticalCentered=\"0\" />"
    },
    {
      "input": {"op": "print_options", "props": {"grid_lines": 99}},
      "expected_output": "[page margins defaults — left/right 0.75, top/bottom 1.0]"
    }
  ]
}
```

---

### Feature 11: Sheet Protection

**As a developer**, I want per-sheet protection settings rendered to their exact XML fragment with password hashing, so protected sheets enforce the right permissions without storing a clear-text password.

**Expected Behavior / Usage:**

A set of independent boolean toggles governs what a viewer may do on a protected sheet: whether the sheet itself is protected; whether objects and scenarios are locked; whether formatting of cells, columns and rows is allowed; whether columns and rows may be inserted or deleted; whether hyperlinks may be inserted; whether locked and unlocked cells may be selected; and whether sorting, auto-filtering and pivot tables are permitted. Most permissions default to enabled, while sheet protection, object/scenario locking, and cell-selection toggles default to off. An optional clear-text password is accepted and stored only as a short hash digest, never echoed back verbatim. Each toggle accepts only a boolean-ish value; a non-boolean value is rejected and reported as `[page margins defaults — left/right 0.75, top/bottom 1.0]`. The emitted fragment lists every toggle as `1` or `0`, with the password hash appended when present.

**Test Cases:** `rcb_tests/public_test_cases/feature11_sheet_protection.json`

```json
{
  "description": "Serialize the per-sheet protection settings to their XML fragment. A set of independent boolean toggles governs what a viewer may do on a protected sheet: whether the sheet itself is protected, whether objects and scenarios are locked, whether formatting of cells, columns and rows is allowed, whether columns and rows may be inserted or deleted, whether hyperlinks may be inserted, whether locked and unlocked cells may be selected, and whether sorting, auto-filtering and pivot tables are permitted. Most permissions default to enabled while sheet protection and object/scenario locking and cell selection default to their off state. An optional clear-text password is accepted and stored only as a short hash digest, never echoed back verbatim. Each toggle accepts only a boolean-ish value; a non-boolean value is rejected and reported as a normalized error. The emitted fragment lists every toggle as 1 or 0, with the password hash appended when present.",
  "cases": [
    {
      "input": {"op": "sheet_protection", "props": {}},
      "expected_output": "<sheetProtection sheet=\"1\" objects=\"0\" scenarios=\"0\" formatCells=\"1\" formatColumns=\"1\" formatRows=\"1\" insertColumns=\"1\" insertRows=\"1\" insertHyperlinks=\"1\" deleteColumns=\"1\" deleteRows=\"1\" selectLockedCells=\"0\" sort=\"1\" autoFilter=\"1\" pivotTables=\"1\" selectUnlockedCells=\"0\" />"
    },
    {
      "input": {"op": "sheet_protection", "props": {"objects": true, "scenarios": true, "select_locked_cells": true}, "password": "fish"},
      "expected_output": "<sheetProtection sheet=\"1\" objects=\"1\" scenarios=\"1\" formatCells=\"1\" formatColumns=\"1\" formatRows=\"1\" insertColumns=\"1\" insertRows=\"1\" insertHyperlinks=\"1\" deleteColumns=\"1\" deleteRows=\"1\" selectLockedCells=\"1\" sort=\"1\" autoFilter=\"1\" pivotTables=\"1\" selectUnlockedCells=\"0\" password=\"CA3F\" />"
    },
    {
      "input": {"op": "sheet_protection", "props": {"sheet": "A"}},
      "expected_output": "[page margins defaults — left/right 0.75, top/bottom 1.0]"
    }
  ]
}
```

---

### Feature 12: Frozen and Split Pane Views

**As a developer**, I want pane regions and their selections rendered to their exact XML fragments, so frozen/split views and the active selection within each region are emitted correctly.

**Expected Behavior / Usage:**

*12.1 Pane — a frozen or split view region*

A pane records which region is active, the split state (frozen, split, or frozen-and-split), the horizontal and vertical split positions, and the top-left visible cell of the bottom-right region. Region and split-state names are accepted in a snake-case spelling and rendered in the wire fragment in their camel-case spelling. Split positions are non-negative integers defaulting to zero. When the state is frozen and no top-left cell is supplied, the top-left cell is derived from the split positions. An unrecognized region or split-state name is rejected and reported as `[page margins defaults — left/right 0.75, top/bottom 1.0]`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_1_pane.json`

```json
{
  "description": "Serialize a worksheet pane (a frozen or split view region) to its XML fragment. The pane records which region is active, the split state (frozen, split, or frozen-and-split), the horizontal and vertical split positions, and the top-left visible cell of the bottom-right region. Region and split-state names are accepted in a snake-case spelling and rendered in the wire fragment in their camel-case spelling. The split positions are non-negative integers and default to zero. When the state is frozen and no top-left cell is supplied, the top-left cell is derived from the split positions. An unrecognized region or split-state name is rejected and reported as a normalized error.",
  "cases": [
    {
      "input": {"op": "pane", "props": {"active_pane": "bottom_left", "state": "frozen", "x_split": 2, "y_split": 2, "top_left_cell": "A2"}},
      "expected_output": "<pane activePane=\"bottomLeft\" state=\"frozen\" topLeftCell=\"A2\" xSplit=\"2\" ySplit=\"2\" />"
    },
    {
      "input": {"op": "pane", "props": {"state": "frozen", "y_split": 2}},
      "expected_output": "<pane state=\"frozen\" topLeftCell=\"A3\" xSplit=\"0\" ySplit=\"2\" />"
    },
    {
      "input": {"op": "pane", "props": {"state": "foo"}},
      "expected_output": "[page margins defaults — left/right 0.75, top/bottom 1.0]"
    }
  ]
}
```

*12.2 Selection — the active selection within a pane region*

A selection records the active cell, an optional active-cell index within a non-contiguous reference list, the pane region the selection belongs to, and the sequence of selected references. The pane region name is accepted in snake-case and rendered in camel-case. The active cell and reference sequence must be textual; the active-cell index must be a non-negative integer; an unrecognized pane region is rejected and reported as `[page margins defaults — left/right 0.75, top/bottom 1.0]`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_2_selection.json`

```json
{
  "description": "Serialize a pane selection to its XML fragment. A selection records the active cell, an optional active-cell index within a non-contiguous reference list, the pane region the selection belongs to, and the sequence of selected references. The pane region name is accepted in a snake-case spelling and rendered in its camel-case spelling. The active cell and reference sequence must be textual; the active-cell index must be a non-negative integer; an unrecognized pane region is rejected and reported as a normalized error.",
  "cases": [
    {
      "input": {"op": "selection", "props": {"active_cell": "B2", "pane": "bottom_right", "sqref": "B2"}},
      "expected_output": "<selection activeCell=\"B2\" pane=\"bottomRight\" sqref=\"B2\" />"
    },
    {
      "input": {"op": "selection", "props": {"active_cell": "I10", "active_cell_id": 1, "pane": "top_right", "sqref": "I10"}},
      "expected_output": "<selection activeCell=\"I10\" activeCellId=\"1\" pane=\"topRight\" sqref=\"I10\" />"
    },
    {
      "input": {"op": "selection", "props": {"pane": "foo"}},
      "expected_output": "[page margins defaults — left/right 0.75, top/bottom 1.0]"
    }
  ]
}
```

---

### Feature 13: Conditional Format Thresholds

**As a developer**, I want a conditional-format threshold value rendered to its exact XML fragment, so gradient scales, data bars and icon sets interpolate against well-formed threshold points.

**Expected Behavior / Usage:**

The threshold object describes one interpolation point. It carries a type (one of: minimum, maximum, a literal number, a percentage, a percentile, or a formula), a value, and a greater-than-or-equal flag that defaults to enabled and controls whether icon-set thresholds use the inclusive comparison. The type is restricted to the recognized set; an unrecognized type is rejected and reported as `[page margins defaults — left/right 0.75, top/bottom 1.0]`. The value accepts anything renderable as text. The emitted fragment carries the type, the flag (as `1`/`0`), and the value.

**Test Cases:** `rcb_tests/public_test_cases/feature13_cfvo.json`

```json
{
  "description": "Serialize a conditional-format threshold value object to its XML fragment. The object describes one interpolation point used by gradient color scales, data bars and icon sets. It carries a type (one of: minimum, maximum, a literal number, a percentage, a percentile, or a formula), a value, and a greater-than-or-equal flag that defaults to enabled and controls whether icon-set thresholds use the inclusive comparison. The type is restricted to the recognized set; an unrecognized type is rejected and reported as a normalized error. The value accepts anything renderable as text.",
  "cases": [
    {
      "input": {"op": "cfvo", "props": {"type": "min", "val": "0"}},
      "expected_output": "<cfvo type=\"min\" gte=\"1\" val=\"0\" />"
    },
    {
      "input": {"op": "cfvo", "props": {"type": "percentile", "val": "90", "gte": false}},
      "expected_output": "<cfvo type=\"percentile\" gte=\"0\" val=\"90\" />"
    },
    {
      "input": {"op": "cfvo", "props": {"type": "invalid_type"}},
      "expected_output": "[page margins defaults — left/right 0.75, top/bottom 1.0]"
    }
  ]
}
```

---

### Feature 14: Auto Filter

**As a developer**, I want an auto-filter's stored reference and its per-column value filters rendered correctly, so a spreadsheet can re-apply the filter and show only matching rows.

**Expected Behavior / Usage:**

*14.1 Filter Range Defined Name — the reference a spreadsheet stores*

Given a worksheet name and a rectangular range over that sheet (start cell and end cell separated by a colon, covering populated cells), the result is the absolute reference of that range — anchored on both row and column and prefixed with the quoted sheet name. The input supplies the sheet name, the seed rows of data, and the range; one reference string is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature14_1_auto_filter_range.json`

```json
{
  "description": "Compute the workbook-level defined-name formula for an auto-filter range. Given a worksheet name and a rectangular range over that sheet (start cell and end cell separated by a colon), the result is the absolute reference of that range, anchored on both row and column, prefixed with the quoted sheet name. This is the reference a spreadsheet stores so it can re-apply the filter. Inputs supply the sheet name, the seed rows of data, and the range; one reference string is emitted.",
  "cases": [
    {
      "input": {"op": "auto_filter_range", "sheet_name": "Sheet1", "rows": [[0, 0, 0], [1, 2, 3], [2, 4, 6]], "range": "A1:C3", "columns": [{"col_id": 0, "filter_type": "filters", "filter_items": [1]}]},
      "expected_output": "'Sheet1'!$A$1:$C$3"
    },
    {
      "input": {"op": "auto_filter_range", "sheet_name": "Data", "rows": [[0, 0, 0], [1, 1, 1]], "range": "A1:C2"},
      "expected_output": "'Data'!$A$1:$C$2"
    }
  ]
}
```

*14.2 Filter Column — a discrete-value filter on one column*

A filter column targets one zero-based column position within the filtered range and holds a discrete-value filter: a list of literal values, so only rows whose cell in that column matches one of the listed values remain visible. Two boolean flags control whether the drop-down button is shown and whether it is hidden. The emitted fragment carries the column position and any non-default flags, and nests one filter entry per listed value. The column position must be an integer and the filter kind must be a recognized kind; an invalid position or filter kind is rejected and reported as `[page margins defaults — left/right 0.75, top/bottom 1.0]`.

**Test Cases:** `rcb_tests/public_test_cases/feature14_2_filter_column.json`

```json
{
  "description": "Serialize an auto-filter column to its XML fragment. A filter column targets one zero-based column position within the filtered range and holds a discrete-value filter: a list of literal values; only rows whose cell in that column matches one of the listed values remain visible. Two boolean flags control whether the filter drop-down button is shown and whether it is hidden. The emitted fragment carries the column position and any non-default flags, and nests one filter entry per listed value. The column position must be an integer and the filter kind must be a recognized kind; an invalid position or filter kind is rejected and reported as a normalized error.",
  "cases": [
    {
      "input": {"op": "filter_column", "col_id": 0, "filter_type": "filters", "filter_items": [200]},
      "expected_output": "<filterColumn colId=\"0\" ><filters ><filter val='200' /></filters></filterColumn>"
    },
    {
      "input": {"op": "filter_column", "col_id": 0, "filter_type": "filters", "filter_items": [700, 100, 5], "hidden_button": true},
      "expected_output": "<filterColumn colId=\"0\" hiddenButton=\"1\" ><filters ><filter val='700' /><filter val='100' /><filter val='5' /></filters></filterColumn>"
    },
    {
      "input": {"op": "filter_column", "col_id": 0, "filter_type": "bogus_filter"},
      "expected_output": "[page margins defaults — left/right 0.75, top/bottom 1.0]"
    }
  ]
}
```

---

### Feature 15: Workbook Defined Names

**As a developer**, I want a workbook-level defined name rendered to its exact XML fragment with validation, so named formulas and ranges are serialized correctly and a missing name is rejected.

**Expected Behavior / Usage:**

A defined name binds a label to a formula or range reference. Serialization requires a name; attempting to serialize without one is rejected and reported as `[page margins defaults — left/right 0.75, top/bottom 1.0]`. An optional hidden flag is emitted when enabled. The name is written verbatim (never case-folded) and the formula reference becomes the element's text body. The input supplies the formula and the name plus optional flags.

**Test Cases:** `rcb_tests/public_test_cases/feature15_defined_name.json`

```json
{
  "description": "Serialize a workbook-level defined name to its XML fragment. A defined name binds a label to a formula or range reference. Serialization requires a name; attempting to serialize without one is rejected and reported as a normalized error. An optional hidden flag is emitted when enabled. The name is written verbatim (never case-folded) and the formula reference becomes the element's text body. Inputs supply the formula and the name plus optional flags.",
  "cases": [
    {
      "input": {"op": "defined_name", "formula": "Sheet1!A1:A1", "props": {}},
      "expected_output": "[page margins defaults — left/right 0.75, top/bottom 1.0]"
    },
    {
      "input": {"op": "defined_name", "formula": "Sheet1!A1:A1", "props": {"name": "_xlnm.Print_Titles", "hidden": true}},
      "expected_output": "<definedName name=\"_xlnm.Print_Titles\" hidden=\"1\" >Sheet1!A1:A1</definedName>"
    },
    {
      "input": {"op": "defined_name", "formula": "Sheet1!A1:A1", "props": {"name": "_xlnm._FilterDatabase"}},
      "expected_output": "<definedName name=\"_xlnm._FilterDatabase\" >Sheet1!A1:A1</definedName>"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the coordinate/range utilities, the value typing-and-casting model, the date/time serial conversions, and the individual serializable records (cell, row, column, page margins, print options, sheet protection, pane, selection, conditional-format threshold, auto-filter range and filter column, defined name). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint — separate logical units, no monolith — without over-engineering the pure helpers.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout with no trailing newline, strictly matching the per-leaf-feature contracts above. It is the only component aware of JSON and stdout, and it is responsible for normalizing any core error into the neutral `error=<category>` token. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_column_label.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_column_label@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check print options for gridLines default
- LOC number value serializes like this
