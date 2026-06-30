## Product Requirement Document

# HTTP Payload Toolkit — Form-Data Encoding, Multipart (De)serialization & Sized Streaming

## Project Goal

Build a small toolkit of HTTP payload helpers that lets developers serialize complex form data, build and parse `multipart/form-data` bodies, assemble user-agent strings, and stream an upload of known size from an iterator — without each application re-implementing these fiddly, error-prone wire-format details by hand.

---

## Background & Problem

Applications that talk to HTTP services repeatedly need the same low-level building blocks: turning a nested dictionary into a flat URL-encoded query, packing several fields (some of them file-like, with their own content types and headers) into a `multipart/form-data` body, taking such a body apart again into its constituent parts, composing a well-formed `User-Agent` string, and feeding a generator of byte chunks to an uploader that insists on knowing the content length up front.

Without a shared toolkit, developers hand-roll each of these and get the details subtly wrong: square-bracket nesting in query keys, exact boundary framing and CRLF placement in multipart bodies, case-insensitive boundary discovery when decoding, and reads that must return *exactly* the requested number of bytes while spanning chunk boundaries. This toolkit provides one well-defined, black-box contract for each of those concerns.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain has several independent concerns (encoding, multipart serialization, multipart parsing, streaming) and is naturally multi-module.

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
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults. Native errors must be surfaced to the contract as neutral `error=<category>` lines, never as host-language runtime traces.

---

## Core Features

### Feature 1: URL-Encoded Form Data With Nested Structures

**As a developer**, I want to serialize a deeply nested mapping or ordered list of pairs into a single URL-encoded query string, so I can submit structured form data that flat encoders cannot express.

**Expected Behavior / Usage:**

*1.1 Flatten and encode a nested structure — leaf*

The input request has an action of `formdata_urlencode` and a `query`. The `query` may be a JSON object (mapping), a JSON array of two-element `[key, value]` pairs, or any mix of the two nested to arbitrary depth. The toolkit flattens the structure: every nested key is appended to its parent key wrapped in square brackets (`parent[child]`, and so on for deeper levels), producing a flat list of leaf key/value pairs. That flat list is then `application/x-www-form-urlencoded`: pairs are joined with `&`, key and value separated by `=`, and reserved characters (including the `[` and `]` introduced by flattening) are percent-encoded. The output is the encoded string followed by a trailing newline. Insertion order of the original structure is preserved in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_nested_urlencode.json`

```json
{
    "description": "Serialize an arbitrarily nested mapping or ordered sequence of key/value pairs into a single flat application/x-www-form-urlencoded string. Nested levels are flattened by composing each parent key with the child key wrapped in square brackets, and the whole structure is percent-encoded. Mappings, lists of pairs, and a mix of the two are all accepted and produce equivalent flattened output.",
    "cases": [
        {
            "input": {
                "action": "formdata_urlencode",
                "query": {
                    "first_nested": {
                        "second_nested": {
                            "third_nested": {"fourth0": "fourth_value0", "fourth1": "fourth_value1"},
                            "third0": "third_value0"
                        },
                        "second0": "second_value0"
                    },
                    "outter": "outter_value"
                }
            },
            "expected_output": "first_nested%5Bsecond_nested%5D%5Bthird_nested%5D%5Bfourth0%5D=fourth_value0&first_nested%5Bsecond_nested%5D%5Bthird_nested%5D%5Bfourth1%5D=fourth_value1&first_nested%5Bsecond_nested%5D%5Bthird0%5D=third_value0&first_nested%5Bsecond0%5D=second_value0&outter=outter_value\n"
        }
    ]
}
```

*1.2 Reject malformed query entries — leaf*

If the `query` cannot be interpreted as a collection of two-element key/value pairs — for example a top-level entry that is a bare scalar, or a tuple/array carrying more or fewer than two elements — encoding is rejected. The toolkit emits a neutral validation error line `error=invalid_query` followed by a newline and produces no encoded output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_invalid_query.json`

```json
{
    "description": "Reject inputs that cannot be interpreted as a collection of key/value pairs. When a top-level entry is not a two-element pair (for example a bare scalar, or a tuple with the wrong number of elements) the encoder reports a neutral validation error instead of producing output.",
    "cases": [
        {"input": {"action": "formdata_urlencode", "query": ["fo"]}, "expected_output": "error=invalid_query\n"}
    ]
}
```

---

### Feature 2: User-Agent String Assembly

**As a developer**, I want to compose a single user-agent string from a primary product and a list of additional products, so I can advertise my client and its dependencies in one well-formed header value.

**Expected Behavior / Usage:**

*2.1 Build from a primary product and optional extras — leaf*

The input request has an action of `user_agent`, a `name`, a `version`, and an optional `extras` list of `[name, version]` pairs. Each product is rendered as `name/version`. The primary product comes first, followed by each extra in the order supplied, all joined by single spaces. The output is the assembled string followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_build.json`

```json
{
    "description": "Assemble a single user-agent string from a primary product name and version, optionally followed by additional product/version pairs. Each pair is rendered as name slash version, and the pieces are joined by single spaces in the order supplied.",
    "cases": [
        {"input": {"action": "user_agent", "name": "fake", "version": "1.0.0"}, "expected_output": "fake/1.0.0\n"},
        {"input": {"action": "user_agent", "name": "fake", "version": "1.0.0", "extras": [["another-fake", "2.0.1"], ["yet-another-fake", "17.1.0"]]}, "expected_output": "fake/1.0.0 another-fake/2.0.1 yet-another-fake/17.1.0\n"}
    ]
}
```

*2.2 Reject malformed extras — leaf*

Every entry in `extras` must be an exact two-element `[name, version]` pair. If any entry has more or fewer than two elements, assembly is rejected: the toolkit emits a neutral validation error line `error=invalid_extras` followed by a newline and produces no string.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_invalid_extras.json`

```json
{
    "description": "Reject extra product entries that are not exact name/version pairs. If any supplied extra entry has more or fewer than two elements, the builder reports a neutral validation error rather than assembling a string.",
    "cases": [
        {"input": {"action": "user_agent", "name": "my-package", "version": "0.0.1", "extras": [["extra", "1.0.0", "oops"]]}, "expected_output": "error=invalid_extras\n"}
    ]
}
```

---

### Feature 3: Multipart/Form-Data Serialization

**As a developer**, I want to pack several fields — including file-style fields with their own filename, content type, and headers — into a single `multipart/form-data` body with a chosen boundary, so I can submit mixed form uploads.

**Expected Behavior / Usage:**

The input request has an action of `multipart_encode`, a `boundary` string, and a `fields` list. A simple field is `{"name", "value"}`. A file-style field is `{"name", "filename", "content"}` and may additionally carry a `content_type` and a `headers` object of extra header name/value pairs. The toolkit produces, in order: a `--<boundary>` delimiter line, then for each field a `Content-Disposition: form-data; name="<name>"` header (with `; filename="<filename>"` appended for file-style fields), then any field-specific `Content-Type` header, then any extra headers, a blank line, the field content, and a closing `--<boundary>--` delimiter at the end. All structural newlines are CRLF (`\r\n`). Empty values are preserved as empty bodies.

The program prints a single `content_type=<media type>` line (the media type is `multipart/form-data; boundary=<boundary>`, exposing the boundary that frames the body) followed immediately by the encoded body. This makes the framing observable: the reported content type and the in-body delimiters must agree.

**Test Cases:** `rcb_tests/public_test_cases/feature3_multipart_encode.json`

```json
{
    "description": "Serialize a set of form fields into a multipart/form-data body using a caller-supplied boundary. The output reports the resulting content type (which embeds the boundary) followed by the encoded body. Each field becomes a boundary-delimited part with a Content-Disposition header; file-style fields may carry a filename, an explicit content type, and arbitrary extra headers; empty values are preserved.",
    "cases": [
        {
            "input": {"action": "multipart_encode", "boundary": "this-is-a-boundary", "fields": [{"name": "field", "value": "value"}, {"name": "other_field", "value": "other_value"}]},
            "expected_output": "content_type=multipart/form-data; boundary=this-is-a-boundary\n--this-is-a-boundary\r\nContent-Disposition: form-data; name=\"field\"\r\n\r\nvalue\r\n--this-is-a-boundary\r\nContent-Disposition: form-data; name=\"other_field\"\r\n\r\nother_value\r\n--this-is-a-boundary--\r\n"
        },
        {
            "input": {"action": "multipart_encode", "boundary": "this-is-a-boundary", "fields": [{"name": "test", "filename": "filename", "content": "filecontent", "content_type": "application/json"}]},
            "expected_output": "content_type=multipart/form-data; boundary=this-is-a-boundary\n--this-is-a-boundary\r\nContent-Disposition: form-data; name=\"test\"; filename=\"filename\"\r\nContent-Type: application/json\r\n\r\nfilecontent\r\n--this-is-a-boundary--\r\n"
        }
    ]
}
```

---

### Feature 4: Multipart/Form-Data Parsing

**As a developer**, I want to take a `multipart/form-data` (or related multipart) body apart into its constituent parts, so I can read each part's headers and content.

**Expected Behavior / Usage:**

*4.1 Decode a multipart body into ordered parts — leaf*

The input request has an action of `multipart_decode`, a `content_type`, and a `content` string. The boundary is read from the `boundary=` parameter of the content type, and the top-level type is checked case-insensitively (so `Multipart/Related` is accepted). The body is split on its boundary delimiters into parts, in order. For each part, everything up to the first blank-line separator is parsed as headers (preserving order); a part with no headers yields an empty header set. Everything after the separator is the part's content, preserved verbatim including any internal CRLFs, with the surrounding boundary framing and the separator removed. The program prints a `parts=<count>` line, then for each part its headers as `part<i>.header.<name>=<value>` lines followed by a `part<i>.content=<content>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_decode.json`

```json
{
    "description": "Parse a multipart body into an ordered tuple of parts. The boundary is taken from the content-type parameters (case-insensitively). Each part exposes its headers (preserving order) and its raw content with the leading/trailing boundary framing and the header/body separator removed; a part with no headers yields an empty header set. Content that spans multiple lines is preserved verbatim.",
    "cases": [
        {
            "input": {"action": "multipart_decode", "content_type": "multipart/related; boundary=\"samp1\"", "content": "\r\n--samp1\r\nHeader-1: Header-Value-1\r\nHeader-2: Header-Value-2\r\n\r\nBody 1, Line 1\r\nBody 1, Line 2\r\n--samp1\r\n\r\nBody 2, Line 1\r\n--samp1--\r\n"},
            "expected_output": "parts=2\npart0.header.Header-1=Header-Value-1\npart0.header.Header-2=Header-Value-2\npart0.content=Body 1, Line 1\r\nBody 1, Line 2\npart1.content=Body 2, Line 1\n"
        }
    ]
}
```

*4.2 Reject a non-multipart content type — leaf*

If the declared `content_type`'s top-level media type is not `multipart`, parsing fails. The toolkit emits a neutral error reporting the offending media type: `error=not_multipart` followed by a `mimetype=<media type>` line, each terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_non_multipart.json`

```json
{
    "description": "Reject content whose top-level media type is not multipart. When the declared content type does not denote a multipart payload, parsing fails with a neutral error that reports the offending media type.",
    "cases": [
        {"input": {"action": "multipart_decode", "content_type": "image/jpeg", "content": "\u00ff\u00d8\u00ff stuff"}, "expected_output": "error=not_multipart\nmimetype=image/jpeg\n"}
    ]
}
```

*4.3 Parse a single body segment — leaf*

The input request has an action of `bodypart_parse` and a `content` string representing one multipart segment. The segment must contain a blank-line (`\r\n\r\n`) separator between its optional headers and its content. When present, the headers are exposed and the content after the separator is returned as text; the program prints a `headers=<count>` line, any `header.<name>=<value>` lines, then a `content=<content>` line. A segment that lacks the separator is rejected with a neutral error line `error=missing_part_separator` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_bodypart.json`

```json
{
    "description": "Parse a single multipart body segment. The segment must contain a blank-line separator between its headers and its content; the content after the separator is returned as text and any headers before it are exposed. A segment that lacks the separator is rejected with a neutral error.",
    "cases": [
        {"input": {"action": "bodypart_parse", "content": "\r\n\r\nNo headers\r\nTwo lines"}, "expected_output": "headers=0\ncontent=No headers\r\nTwo lines\n"},
        {"input": {"action": "bodypart_parse", "content": "no CRLF CRLF here!\r\n"}, "expected_output": "error=missing_part_separator\n"}
    ]
}
```

---

### Feature 5: Sized Streaming Reads Over An Iterable

**As a developer**, I want to wrap an iterator of byte chunks with a known total size in a reader that satisfies exact sized reads, so I can stream an upload of a declared length without buffering it all in memory.

**Expected Behavior / Usage:**

The input request has an action of `stream_read`, a `size` (the declared total byte count), a `chunks` list of strings (the source produces these byte chunks in order), and a `reads` list describing a sequence of read calls. A read entry of `null` requests all remaining source bytes joined together; an integer entry requests exactly that many bytes. A sized read returns exactly the requested number of bytes, drawing across chunk boundaries as needed, until the source is exhausted; once exhausted, every read (sized or not) returns an empty result. The program prints one line per read of the form `read=<byte count returned>|<bytes returned>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_stream_read.json`

```json
{
    "description": "Stream a sequence of byte chunks of a known total size through a reader that satisfies sized reads. A read with no size returns all remaining source bytes joined together; a sized read returns exactly the requested number of bytes (drawing across chunk boundaries as needed) until the source is exhausted, after which every read returns an empty result. Each output line reports the byte count returned by one read followed by the bytes themselves.",
    "cases": [
        {"input": {"action": "stream_read", "size": 17, "chunks": ["here", "are", "some", "chunks"], "reads": [null]}, "expected_output": "read=17|herearesomechunks\n"},
        {"input": {"action": "stream_read", "size": 17, "chunks": ["here", "are", "some", "chunks"], "reads": [8192, 8192, 8192, 8192, null, 8192]}, "expected_output": "read=17|herearesomechunks\n[minimal read output format for insufficient chunks]\n[minimal read output format for insufficient chunks]\n[minimal read output format for insufficient chunks]\n[minimal read output format for insufficient chunks]\n[minimal read output format for insufficient chunks]\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above, organized into cohesive modules (form-data encoding, multipart serialization, multipart parsing, user-agent assembly, sized streaming). The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects behavior by the request's `action` field (`formdata_urlencode`, `user_agent`, `multipart_encode`, `multipart_decode`, `bodypart_parse`, `stream_read`), invokes the appropriate core logic, and prints the result (or a neutral `error=<category>` contract) to stdout, matching the per-feature contracts above. Native errors must be translated into the neutral error lines specified per feature; host-language exception identities must never appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same space separator convention as electronic commerce API rules
- align header key naming with the network fetch utility module
