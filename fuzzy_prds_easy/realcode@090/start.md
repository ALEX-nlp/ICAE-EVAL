## Product Requirement Document

# Delimited-Text Conversion Library — Configurable CSV Encoding, Decoding, and Streaming

## Project Goal

Build a reusable delimited-text (CSV) conversion library that lets developers turn in-memory rows of values into CSV text and parse CSV text back into rows, with full control over delimiters, quoting, escaping, value typing, header handling, and incremental (streaming) processing, so applications can interoperate with spreadsheets and data feeds without hand-rolling a brittle parser for every edge case.

---

## Background & Problem

CSV looks trivial but is full of corner cases: fields that contain the delimiter, embedded line breaks, quote characters that must be escaped, byte-order marks, spreadsheet "delimiter hint" preambles, ambiguous delimiters that must be guessed, blank lines, and data that arrives in arbitrary network chunks rather than one complete string. Without a shared library, developers reimplement these rules inconsistently, producing parsers that corrupt data the moment a value contains a comma or a newline.

This library provides one well-defined contract for both directions. On the encoding side it joins rows with a configurable field delimiter and line delimiter, quotes fields only when necessary (or [a specific quote mode string], or only textual values), and escapes embedded quotes. On the decoding side it splits text into rows and fields, honors quoted regions, strips a leading byte-order mark, can infer the delimiter, can read a `sep=` hint, can skip blank lines, can coerce values to numbers and booleans, and can treat the first row as a header. Both directions also work incrementally: rows can be fed or produced one chunk at a time, with the parser correctly stitching together tokens that straddle chunk boundaries.

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

## Adapter Output Contract

The execution adapter reads one JSON command object from stdin and prints a plain-text result to stdout. Every command carries an `op` field selecting the behavior; an optional `config` object carries conversion settings (`fieldDelimiter`, `lineDelimiter`, `quoteCharacter`, `escapeCharacter`, `quoteMode` of `necessary`/`[a specific quote mode string]`/`[a specific quote mode string]`, `addBom`, `autoDetect`, `skipEmptyLines`, `parseHeaders`, `dynamicTyping`). Defaults are: comma field delimiter, carriage-return-plus-line-feed line delimiter, double-quote quote and escape character, `necessary` quoting, no byte-order mark, delimiter auto-detection on, blank-line skipping on, headers off, value typing off.

Encoding operations print the resulting CSV text verbatim (the wire format itself, including any byte-order mark, quotes, and line delimiters). Decoding operations print a structured rendering: a first line `rows=<n>`, then one line per row `row[<i>]: <field> | <field> | ...`; each field is rendered as `<tag>=<json>` where `<tag>` is the neutral value-type category (`str`, `int`, `double`, or `bool`) and `<json>` is the JSON encoding of the value (so textual fields appear quoted and control characters stay unambiguous). Header-aware decoding renders each field as `<json-header>: <tag>=<json>`. Batch operations print `batches=<n>` then one line per batch `batch[<i>] rows=<k>: [ <row> ] [ <row> ] ...`. Errors are reported as neutral category lines of the form `error=<category>`.

---

## Core Features

### Feature 1: Encode Rows Into CSV Text

**As a developer**, I want to turn a list of rows of values into a single CSV string with correct delimiting, quoting, and escaping, so I can serialize tabular data safely.

**Expected Behavior / Usage:**

*1.1 Field and row joining — flat serialization of values*

Given rows of values, fields within a row are joined by the field delimiter and consecutive rows are separated by the line delimiter. No line delimiter is appended after the final row. The output is the raw CSV text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_encode_join.json`

```json
{
    "description": "Encode a list of rows into a single CSV text. Fields within a row are joined by the field delimiter and consecutive rows are separated by the line delimiter; no trailing line delimiter is appended after the final row.",
    "cases": [
        {"input": {"op": "encode", "rows": [["A", "b", "c"]]}, "expected_output": "A,b,c"},
        {"input": {"op": "encode", "rows": [["A", "b", "c"], ["d", "E", "f"]]}, "expected_output": "A,b,c\r\nd,E,f"}
    ]
}
```

*1.2 Necessary quoting and quote escaping — quote only fields that require it*

Under the default quoting policy a field is wrapped in the quote character only when it contains the field delimiter, a line break, or the quote character itself. An embedded quote character is escaped by doubling it (prefixing it with the escape character, which defaults to the quote character).

**Test Cases:** `rcb_tests/public_test_cases/feature2_encode_quoting.json`

```json
{
    "description": "Encode rows where some fields require quoting. Under the default quoting policy a field is wrapped in the quote character only when it contains the field delimiter, a line break, or the quote character itself. An embedded quote character is escaped by doubling it (prefixing it with the escape character, which defaults to the quote character).",
    "cases": [
        {"input": {"op": "encode", "rows": [["A", "B,B", "C"]]}, "expected_output": "A,\"B,B\",C"},
        {"input": {"op": "encode", "rows": [["A", "B\"B", "C"]]}, "expected_output": "A,\"B\"\"B\",C"}
    ]
}
```

*1.3 Quote-mode policies — [a specific quote mode string]-quote and quote-textual-only*

Beyond the default, two explicit policies exist. The `[a specific quote mode string]` policy quotes only fields whose runtime value is textual, leaving numeric and boolean values unquoted. The `[a specific quote mode string]` policy quotes every field regardless of its type or content.

**Test Cases:** `rcb_tests/public_test_cases/feature3_encode_quote_modes.json`

```json
{
    "description": "Encode rows under explicit quoting policies other than the default. The '[a specific quote mode string]' policy quotes only fields whose runtime value is textual, leaving numeric and boolean values unquoted. The '[a specific quote mode string]' policy quotes every field regardless of its type or content.",
    "cases": [
        {"input": {"op": "encode", "config": {"quoteMode": "[a specific quote mode string]"}, "rows": [[1, "1", true, "true"]]}, "expected_output": "1,\"1\",true,\"true\""},
        {"input": {"op": "encode", "config": {"quoteMode": "[a specific quote mode string]"}, "rows": [[1, "A"]]}, "expected_output": "\"1\",\"A\""}
    ]
}
```

*1.4 Custom escape character — escape embedded quotes with a different character*

When a custom escape character different from the quote character is configured, an embedded quote character inside a quoted field is preceded by the escape character instead of being doubled.

**Test Cases:** `rcb_tests/public_test_cases/feature4_encode_escape_char.json`

```json
{
    "description": "Encode using a custom escape character that differs from the quote character. When a quoted field contains the quote character, the configured escape character is placed before it instead of doubling the quote.",
    "cases": [
        {"input": {"op": "encode", "config": {"escapeCharacter": "\\"}, "rows": [["A\"B"]]}, "expected_output": "\"A\\\"B\""}
    ]
}
```

---

### Feature 2: Spreadsheet-Compatible Encoding Preset

**As a developer**, I want a one-shot preset that produces output a common spreadsheet program opens cleanly, so I do not have to remember the exact delimiter and byte-order-mark combination.

**Expected Behavior / Usage:**

The spreadsheet preset encodes with a semicolon field delimiter and prepends a UTF-8 byte-order mark to the output. The default necessary-quoting policy still applies, so a field containing the semicolon delimiter is quoted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_excel_encode.json`

```json
{
    "description": "Encode using the spreadsheet-compatible preset: a semicolon field delimiter and a UTF-8 byte order mark prepended to the output. Fields that contain the semicolon delimiter are still quoted under the default necessary-quoting policy.",
    "cases": [
        {"input": {"op": "encode", "preset": "excel", "rows": [["Header1", "Header2"], ["Value1", "Value;2"]]}, "expected_output": "\ufeffHeader1;Header2\r\nValue1;\"Value;2\""}
    ]
}
```

---

### Feature 3: Decode CSV Text Into Rows

**As a developer**, I want to parse CSV text into rows of fields with correct handling of quoting, delimiters, byte-order marks, and blank lines, so I can read tabular data reliably.

**Expected Behavior / Usage:**

*3.1 Basic field and row parsing — split on delimiters and line breaks*

Fields are separated by the delimiter and rows by line breaks. Empty fields between consecutive delimiters are preserved as empty [a specific quote mode string], and a single trailing line break does not create an extra empty row.

**Test Cases:** `rcb_tests/public_test_cases/feature6_decode_basic.json`

```json
{
    "description": "Decode CSV text into a list of rows of string fields. Fields are separated by the delimiter and rows by line breaks. Empty fields between consecutive delimiters are preserved as empty [a specific quote mode string], and a single trailing line break does not create an extra empty row. Each decoded field is reported with a neutral type tag (here [a specific quote mode string] textual) and its value.",
    "cases": [
        {"input": {"op": "decode", "input": "A,b,c"}, "expected_output": "rows=1\nrow[0]: str=\"A\" | str=\"b\" | str=\"c\"\n"},
        {"input": {"op": "decode", "input": "a,b,,,c,d"}, "expected_output": "rows=1\nrow[0]: str=\"a\" | str=\"b\" | str=\"\" | str=\"\" | str=\"c\" | str=\"d\"\n"}
    ]
}
```

*3.2 Quoted-field parsing — honor quoted regions and escapes*

A field wrapped in the quote character may itself contain the delimiter, line breaks, or escaped quote characters (a doubled quote decodes to a single quote). Surrounding whitespace inside a quoted field is preserved, whitespace in an unquoted field is kept verbatim, a stray quote in the middle of an otherwise unquoted field is treated literally, and runs of escaped quotes around a delimiter decode correctly.

**Test Cases:** `rcb_tests/public_test_cases/feature7_decode_quoted.json`

```json
{
    "description": "Decode CSV text containing quoted fields. A field wrapped in the quote character may itself contain the delimiter, line breaks, or escaped quote characters (a doubled quote decodes to a single quote). Surrounding whitespace inside a quoted field is preserved, whitespace in an unquoted field is kept verbatim, a stray quote in the middle of an otherwise unquoted field is treated literally, and runs of escaped quotes around a delimiter decode correctly.",
    "cases": [
        {"input": {"op": "decode", "input": "A,\"B,B\",C"}, "expected_output": "rows=1\nrow[0]: str=\"A\" | str=\"B,B\" | str=\"C\"\n"},
        {"input": {"op": "decode", "input": "A,\"B\"\"B\",C"}, "expected_output": "rows=1\nrow[0]: str=\"A\" | str=\"B\\\"B\" | str=\"C\"\n"}
    ]
}
```

*3.3 Delimiter auto-detection — infer the separator from content*

When the delimiter is not supplied, it is inferred from the content. The detector considers common candidates (comma, semicolon, tab, pipe) and picks the one that best and most consistently separates fields across the leading lines.

**Test Cases:** `rcb_tests/public_test_cases/feature8_decode_autodetect.json`

```json
{
    "description": "Decode CSV text without being told the delimiter, letting it be inferred from the content. The detector considers common candidates (comma, semicolon, tab, pipe) and picks the one that best and most consistently separates fields across the leading lines.",
    "cases": [
        {"input": {"op": "decode", "input": "A;B;C"}, "expected_output": "rows=1\nrow[0]: str=\"A\" | str=\"B\" | str=\"C\"\n"},
        {"input": {"op": "decode", "input": "A\tB\tC"}, "expected_output": "rows=1\nrow[0]: str=\"A\" | str=\"B\" | str=\"C\"\n"}
    ]
}
```

*3.4 Byte-order-mark stripping — drop a leading BOM*

A UTF-8 byte-order mark at the start of the input is consumed and never becomes part of the first field, whether the delimiter is supplied explicitly or inferred automatically.

**Test Cases:** `rcb_tests/public_test_cases/feature9_decode_bom.json`

```json
{
    "description": "Decode CSV text that begins with a UTF-8 byte order mark. The byte order mark is consumed and never becomes part of the first field, whether the delimiter is supplied explicitly or inferred automatically.",
    "cases": [
        {"input": {"op": "decode", "input": "\ufeffA,B,C"}, "expected_output": "rows=1\nrow[0]: str=\"A\" | str=\"B\" | str=\"C\"\n"}
    ]
}
```

*3.5 Delimiter hint line — read a `sep=` preamble*

When the input opens with a hint line of the form `sep=<char>`, that delimiter is used for the rest of the document and the hint line itself is not emitted as data; subsequent content is split on the hinted delimiter rather than any auto-detected one.

**Test Cases:** `rcb_tests/public_test_cases/feature10_decode_sep_hint.json`

```json
{
    "description": "Decode CSV text that opens with a spreadsheet-style delimiter hint line of the form sep=<char>. When present, the hint sets the delimiter for the rest of the document and the hint line itself is not emitted as data; subsequent content is then split on that delimiter rather than any auto-detected one.",
    "cases": [
        {"input": {"op": "decode", "input": "sep=;\r\nA;B;C"}, "expected_output": "rows=1\nrow[0]: str=\"A\" | str=\"B\" | str=\"C\"\n"},
        {"input": {"op": "decode", "input": "sep=;\r\nA,B,C"}, "expected_output": "rows=1\nrow[0]: str=\"A,B,C\"\n"}
    ]
}
```

*3.6 Blank-line handling — skip or keep empty rows*

With empty-line skipping enabled (the default), rows that consist solely of empty fields are dropped. With skipping disabled, every physical line — including blank ones — becomes a row.

**Test Cases:** `rcb_tests/public_test_cases/feature11_decode_skip_empty.json`

```json
{
    "description": "Decode CSV text that contains blank lines, controlling whether they are kept. With empty-line skipping enabled (the default), rows that consist solely of empty fields are dropped. With skipping disabled, every physical line — including blank ones — becomes a row.",
    "cases": [
        {"input": {"op": "decode", "config": {"skipEmptyLines": true}, "input": "A,B\n\nC,D\n\n"}, "expected_output": "rows=2\nrow[0]: str=\"A\" | str=\"B\"\nrow[1]: str=\"C\" | str=\"D\"\n"},
        {"input": {"op": "decode", "config": {"skipEmptyLines": false}, "input": "A,B\n\nC,D\n\n"}, "expected_output": "rows=4\nrow[0]: str=\"A\" | str=\"B\"\nrow[1]: str=\"\"\nrow[2]: str=\"C\" | str=\"D\"\nrow[3]: str=\"\"\n"}
    ]
}
```

---

### Feature 4: Automatic Value Typing

**As a developer**, I want decoded fields optionally coerced to numbers and booleans, so I get typed data instead of raw [a specific quote mode string].

**Expected Behavior / Usage:**

When value typing is enabled, each field is examined and converted to an integer, floating-point number, or boolean when its full text matches that form; otherwise it stays textual. Boolean recognition is exact and case-sensitive, and even quoted fields are subject to typing. The reported neutral type tag reflects the inferred type of each field.

**Test Cases:** `rcb_tests/public_test_cases/feature12_dynamic_typing.json`

```json
{
    "description": "Decode CSV text with automatic value typing enabled. Each field is examined and converted to an integer, floating-point number, or boolean when its full text matches that form; otherwise it stays textual. Boolean recognition is exact and case-sensitive, and even quoted fields are subject to typing. The reported neutral type tag reflects the inferred type of each field.",
    "cases": [
        {"input": {"op": "decode", "config": {"dynamicTyping": true}, "input": "123,-456"}, "expected_output": "rows=1\nrow[0]: int=123 | int=-456\n"},
        {"input": {"op": "decode", "config": {"dynamicTyping": true}, "input": "123,true,hello,1.5"}, "expected_output": "rows=1\nrow[0]: int=123 | bool=true | str=\"hello\" | double=1.5\n"}
    ]
}
```

---

### Feature 5: Header-Aware Decoding

**As a developer**, I want the first row treated as a header so subsequent rows are addressable by column name, so I can read fields without tracking positional indices.

**Expected Behavior / Usage:**

When header parsing is enabled, the first line is consumed as the header row and each following row is exposed as a mapping from header name to the corresponding field value, in column order, while remaining addressable by position.

**Test Cases:** `rcb_tests/public_test_cases/feature13_headers.json`

```json
{
    "description": "Decode CSV text while treating the first line as a header row, exposing each subsequent row by header name as well as by position. The result reports each data row as a mapping from header name to the corresponding typed field value, in column order.",
    "cases": [
        {"input": {"op": "decode_headers", "input": "id,name\n1,Alice\n2,Bob"}, "expected_output": "rows=2\nrow[0]: \"id\": str=\"1\" | \"name\": str=\"Alice\"\nrow[1]: \"id\": str=\"2\" | \"name\": str=\"Bob\"\n"}
    ]
}
```

---

### Feature 6: Configurable Multi-Character Delimiter

**As a developer**, I want to use a delimiter longer than one character, so I can parse formats that separate fields with multi-character markers.

**Expected Behavior / Usage:**

When an explicit multi-character delimiter is configured, the whole delimiter sequence separates fields, and single characters that merely begin the delimiter sequence are treated as ordinary content.

**Test Cases:** `rcb_tests/public_test_cases/feature14_multi_char_delim.json`

```json
{
    "description": "Decode CSV text using an explicitly configured multi-character delimiter. The whole delimiter sequence separates fields, and single characters that merely begin the delimiter sequence are treated as ordinary content.",
    "cases": [
        {"input": {"op": "decode", "config": {"autoDetect": false, "fieldDelimiter": "::"}, "input": "a::b::c"}, "expected_output": "rows=1\nrow[0]: str=\"a\" | str=\"b\" | str=\"c\"\n"}
    ]
}
```

---

### Feature 7: Streaming Chunked Decoding

**As a developer**, I want to decode CSV that arrives in arbitrary chunks, with tokens correctly reassembled across chunk edges, so I can parse large or networked inputs without buffering everything first.

**Expected Behavior / Usage:**

The chunked decoder is fed an ordered list of string chunks and emits the same rows it would produce from the concatenated text. Partial tokens at a chunk boundary are buffered until completed.

*7.1 Arbitrary chunk boundaries — split rows and quoted fields*

Row and field boundaries, including quoted fields that contain a line break, may be split anywhere across chunk edges; the decoder reconstructs each completed row in order.

**Test Cases:** `rcb_tests/public_test_cases/feature15_chunked_decode.json`

```json
{
    "description": "Decode CSV text delivered as a sequence of arbitrary chunks, where row and field boundaries may be split across chunk edges. The decoder buffers partial content and reconstructs exactly the same rows it would produce from the concatenated text, emitting each completed row in order.",
    "cases": [
        {"input": {"op": "decode_chunks", "config": {"autoDetect": false, "fieldDelimiter": ","}, "chunks": ["A,B,C\nd", ",e,f"]}, "expected_output": "rows=2\nrow[0]: str=\"A\" | str=\"B\" | str=\"C\"\nrow[1]: str=\"d\" | str=\"e\" | str=\"f\"\n"},
        {"input": {"op": "decode_chunks", "config": {"autoDetect": false, "fieldDelimiter": ","}, "chunks": ["A,\"B\n", "B\",C"]}, "expected_output": "rows=1\nrow[0]: str=\"A\" | str=\"B\\nB\" | str=\"C\"\n"}
    ]
}
```

*7.2 Split line terminator — a carriage-return/line-feed pair split across chunks*

A carriage-return/line-feed line terminator whose carriage return ends one chunk and whose line feed begins the next must be recognized as a single line terminator, not two, so no spurious empty row appears regardless of the blank-line-skipping setting.

**Test Cases:** `rcb_tests/public_test_cases/feature16_split_crlf.json`

```json
{
    "description": "Decode chunked CSV text where a carriage-return/line-feed pair that ends a line is split so the carriage return ends one chunk and the line feed begins the next. The pair must be recognized as a single line terminator rather than producing a spurious empty row, regardless of the empty-line-skipping setting.",
    "cases": [
        {"input": {"op": "decode_chunks", "config": {"autoDetect": false, "fieldDelimiter": ","}, "chunks": ["a\r", "\nb"]}, "expected_output": "rows=2\nrow[0]: str=\"a\"\nrow[1]: str=\"b\"\n"}
    ]
}
```

*7.3 Split escaped quote at every position — exhaustive boundary robustness*

When a quoted field containing an escaped quote sequence is split into two chunks at every possible position, every split must reconstruct the identical row — including the case where the escaped quote surrounds a delimiter that therefore becomes part of the field value. The result lists the decoded row for each split index.

**Test Cases:** `rcb_tests/public_test_cases/feature17_split_escape.json`

```json
{
    "description": "Decode chunked CSV text containing an escaped quote sequence inside a quoted field, verifying correctness for every possible split point. The input is fed as two chunks for each split position from start to end, and every split must reconstruct the identical row, including the case where the escaped quote surrounds a delimiter that is therefore part of the field value.",
    "cases": [
        {"input": {"op": "decode_split_scan", "config": {"autoDetect": false, "fieldDelimiter": ","}, "input": "a,\"b\"\"c\",d"}, "expected_output": "[a method for handling byte-level splits]10\nsplit[0]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[1]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[2]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[3]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[4]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[5]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[6]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[7]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[8]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[9]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\nsplit[10]: [ str=\"a\" | str=\"b\\\"c\" | str=\"d\" ]\n"}
    ]
}
```

*7.4 Split multi-character delimiter — partial delimiter across chunks*

A multi-character delimiter split across a chunk boundary, including a split immediately after a closing quote, must be buffered and rejoined so fields separate correctly.

**Test Cases:** `rcb_tests/public_test_cases/feature18_split_multi_char.json`

```json
{
    "description": "Decode chunked CSV text using a multi-character delimiter that is split across a chunk boundary, including the case where the split occurs immediately after a closing quote. The partial delimiter at a chunk edge must be buffered and rejoined so the fields separate correctly.",
    "cases": [
        {"input": {"op": "decode_chunks", "config": {"autoDetect": false, "fieldDelimiter": "::"}, "chunks": ["a:", ":b"]}, "expected_output": "rows=1\nrow[0]: str=\"a\" | str=\"b\"\n"},
        {"input": {"op": "decode_chunks", "config": {"autoDetect": false, "fieldDelimiter": "::"}, "chunks": ["\"a\":", ":b"]}, "expected_output": "rows=1\nrow[0]: str=\"a\" | str=\"b\"\n"}
    ]
}
```

*7.5 Maximal fragmentation with detection — one character at a time*

When the input is streamed one character at a time, delimiter detection and the `sep=` hint must still work: the decoder buffers until it can determine the delimiter, then yields the same rows as a single-shot decode.

**Test Cases:** `rcb_tests/public_test_cases/feature19_small_chunk_detect.json`

```json
{
    "description": "Decode CSV text streamed one character at a time, forcing delimiter detection and the spreadsheet delimiter hint to work under maximal fragmentation. Even when no chunk individually contains enough context, the decoder buffers until it can determine the delimiter and then yields the same rows as a single-shot decode.",
    "cases": [
        {"input": {"op": "decode_chunks", "chunks": ["s", "e", "p", "=", ";", "\r", "\n", "a", ";", "b", ";", "c"]}, "expected_output": "rows=1\nrow[0]: str=\"a\" | str=\"b\" | str=\"c\"\n"},
        {"input": {"op": "decode_chunks", "chunks": ["a", ",", "b", ",", "c", "\n", "1", ",", "2", ",", "3"]}, "expected_output": "rows=2\nrow[0]: str=\"a\" | str=\"b\" | str=\"c\"\nrow[1]: str=\"1\" | str=\"2\" | str=\"3\"\n"}
    ]
}
```

---

### Feature 8: Streaming Encoding

**As a developer**, I want to encode rows one at a time through a streaming pipeline, so I can produce CSV incrementally without holding all rows in memory.

**Expected Behavior / Usage:**

Rows are fed one at a time and each produces an output fragment; the concatenation of all fragments equals the full CSV text. The first row contributes no leading line delimiter and each later row is prefixed by the line delimiter.

**Test Cases:** `rcb_tests/public_test_cases/feature20_streaming_encode.json`

```json
{
    "description": "Encode rows fed one at a time through a streaming pipeline, where each row produces an output fragment and the concatenation of all fragments equals the full CSV text. The first row contributes no leading line delimiter and each later row is prefixed by the line delimiter.",
    "cases": [
        {"input": {"op": "encode_stream", "rows": [["A", "B"], ["C", "D"]]}, "expected_output": "A,B\r\nC,D"}
    ]
}
```

---

### Feature 9: Batch-Oriented Codec Adapter

**As a developer**, I want a codec adapter that delivers decoded rows in batches aligned to input chunks, with an optional cap on batch size, so I can integrate with pipelines that consume groups of rows.

**Expected Behavior / Usage:**

*9.1 Chunk-aligned batching — one batch per input chunk*

Rows decoded from a single input chunk are forwarded together as one batch, so the number and contents of the batches reflect how the input was chunked. Rows that straddle chunk edges are reconstructed correctly before being grouped. When the delimiter must be auto-detected, the rows from the buffered prefix are emitted as a single batch once detection completes.

**Test Cases:** `rcb_tests/public_test_cases/feature21_codec_batching.json`

```json
{
    "description": "Decode chunked CSV text through the batch-oriented codec adapter, where rows decoded from one input chunk are forwarded together as a single batch so natural chunk boundaries are preserved. Rows that straddle chunk edges (split fields, split line terminators, split escaped quotes, single-character feeding) are reconstructed correctly, and the number and contents of the emitted batches reflect how the input was chunked.",
    "cases": [
        {"input": {"op": "decode_batches", "config": {"autoDetect": true}, "chunks": ["a,b\r\n1,2\r\n3,4\r\n"]}, "expected_output": "batches=1\nbatch[0] rows=3: [ str=\"a\" | str=\"b\" ] [ str=\"1\" | str=\"2\" ] [ str=\"3\" | str=\"4\" ]\n"},
        {"input": {"op": "decode_batches", "config": {"autoDetect": false}, "chunks": ["a,b\r\n", "c,d\r\n"]}, "expected_output": "batches=2\nbatch[0] rows=1: [ str=\"a\" | str=\"b\" ]\nbatch[1] rows=1: [ str=\"c\" | str=\"d\" ]\n"}
    ]
}
```

*9.2 Row-count cap per batch — bound batch size*

When a maximum number of rows per batch is configured, a single chunk that decodes to more rows than the cap is split into multiple batches of at most that size; the cap composes with chunk boundaries and with split line terminators, and a cap larger than the available rows yields one batch.

**Test Cases:** `rcb_tests/public_test_cases/feature22_codec_max_rows.json`

```json
{
    "description": "Decode chunked CSV text through the batch-oriented codec adapter with a cap on the number of rows per emitted batch. A single chunk that decodes to more rows than the cap is split into multiple batches of at most that size, the cap composes with chunk boundaries and with split line terminators, and a cap larger than the available rows yields one batch.",
    "cases": [
        {"input": {"op": "decode_batches", "config": {"autoDetect": false}, "maxRowsPerBatch": 1, "chunks": ["a,b\r\nc,d\r\ne,f\r\n"]}, "expected_output": "batches=3\nbatch[0] rows=1: [ str=\"a\" | str=\"b\" ]\nbatch[1] rows=1: [ str=\"c\" | str=\"d\" ]\nbatch[2] rows=1: [ str=\"e\" | str=\"f\" ]\n"},
        {"input": {"op": "decode_batches", "config": {"autoDetect": false}, "maxRowsPerBatch": 3, "chunks": ["0,row0\r\n1,row1\r\n2,row2\r\n3,row3\r\n4,row4\r\n5,row5\r\n6,row6\r\n7,row7\r\n8,row8\r\n9,row9\r\n"]}, "expected_output": "batches=4\nbatch[0] rows=3: [ str=\"0\" | str=\"row0\" ] [ str=\"1\" | str=\"row1\" ] [ str=\"2\" | str=\"row2\" ]\nbatch[1] rows=3: [ str=\"3\" | str=\"row3\" ] [ str=\"4\" | str=\"row4\" ] [ str=\"5\" | str=\"row5\" ]\nbatch[2] rows=3: [ str=\"6\" | str=\"row6\" ] [ str=\"7\" | str=\"row7\" ] [ str=\"8\" | str=\"row8\" ]\nbatch[3] rows=1: [ str=\"9\" | str=\"row9\" ]\n"}
    ]
}
```

---

### Feature 10: Decoder Configuration Validation

**As a developer**, I want invalid decoder settings rejected up front with a clear category, so misconfiguration fails fast instead of corrupting output.

**Expected Behavior / Usage:**

The quote character and the escape character must each be exactly one character. Supplying a multi-character value is rejected with a neutral configuration-error category that identifies which option was invalid (`[an error returned when a multi-character escape character is invalid]` or `error=invalid_escape_character`), while a valid single-character configuration is accepted (`valid=true`).

**Test Cases:** `rcb_tests/public_test_cases/feature23_decoder_validation.json`

```json
{
    "description": "Validate decoder configuration up front. The quote character and the escape character must each be exactly one character; supplying a multi-character value is rejected with a neutral configuration-error category identifying which option was invalid, while a valid single-character configuration is accepted.",
    "cases": [
        {"input": {"op": "validate_decoder", "config": {"quoteCharacter": "xx"}}, "expected_output": "[an error returned when a multi-character escape character is invalid]\n"},
        {"input": {"op": "validate_decoder", "config": {"quoteCharacter": "\"", "escapeCharacter": "\\"}}, "expected_output": "valid=true\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the encoding, decoding, typing, header, streaming, and batching features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core conversion logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command from stdin and prints the result (or a neutral error line) to stdout, matching the per-feature contracts above. The command's `op` selects behavior: `encode` and `encode_stream` serialize rows; `decode`, `decode_headers`, `decode_chunks`, `decode_split_scan`, and `decode_batches` parse text or chunk lists; `validate_decoder` checks configuration. Field values in decoded output are rendered with the neutral type tag and JSON-encoded value defined in the Adapter Output Contract. Native exceptions raised by the core must be translated by the adapter into neutral `error=<category>` lines without leaking host-language runtime details.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- conforms to the row drop policy established in legacy macros
- overrides the standard trim logic unless explicitly disabled
