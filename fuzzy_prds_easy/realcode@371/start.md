## Product Requirement Document

# Secret-Injection CLI Toolkit — Parsing, Validation, Formatting & Output-Masking Primitives

## Project Goal

Build a toolkit of small, composable primitives that a secrets-management command-line tool relies on to safely move secret values between configuration files, environment variables, and process output. The toolkit lets developers parse user-supplied flags, validate names, render timestamps, expand secret references inside templates, detect text encodings, and redact secrets from streamed output — each behavior being a precise, testable contract — without every command re-implementing this fiddly, error-prone plumbing.

---

## Background & Problem

A secrets-management CLI constantly converts between human-typed strings and strict machine formats: a file-permission flag like `0440`, an environment-variable name that must obey POSIX or portable-charset rules, a timestamp shown to the user, a configuration file peppered with `${...}` secret references, a file whose encoding must be guessed from its byte-order mark, and a log stream from which actual secret values must be redacted before display.

Without a shared toolkit, each command hand-rolls this logic, producing inconsistent parsing, weak validation, leaked secrets, and subtle formatting bugs. This toolkit provides one well-defined contract per primitive so that behavior is predictable and reusable. Each feature below is an independent, self-contained functional point; the execution adapter exposes each one through a single JSON request read from stdin, dispatched by an `action` field, and renders the result (or a neutral error) to stdout.

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

### Feature 1: Octal File-Permission Parsing

**As a developer**, I want to turn a textual octal permission string (as typed on the command line) into a concrete file permission, so I can apply the requested mode to files I write.

**Expected Behavior / Usage:**

The input carries a `mode` string. The value is interpreted as a base-8 (octal) number; a leading zero is optional, so `440` and `0440` mean the same thing. The string must contain at least three characters — anything shorter is rejected. On success the parsed permission is reported on two lines: `octal=` followed by the canonical four-digit octal form (with a leading zero), and `perm=` followed by the ten-character symbolic representation (a leading file-type position — `-` for a regular permission set — followed by the owner/group/other `rwx` triples). On failure a neutral error is reported as `error=invalid_filemode` followed by a line echoing the offending `mode` value. Each emitted line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_filemode.json`

```json
{
    "description": "Parse a textual octal file-permission string (as a command-line flag would supply) into a concrete permission set. A valid input is interpreted as a base-8 number and must contain at least three digits; a leading zero is optional. On success the parsed value is reported both as its canonical 4-digit octal form and as its symbolic rwx permission string. Inputs shorter than three characters are rejected as invalid.",
    "cases": [
        {"input": {"action": "parse_filemode", "mode": "0660"}, "expected_output": "octal=0660\nperm=-rw-rw----\n"},
        {"input": {"action": "parse_filemode", "mode": ""}, "expected_output": "error=invalid_filemode\nmode=\n"}
    ]
}
```

---

### Feature 2: POSIX Trailing-Newline Normalization

**As a developer**, I want a chunk of output text to always end with exactly one newline, so secret values written to a stream are POSIX-compliant and play nicely with shell pipelines.

**Expected Behavior / Usage:**

The input carries a `data` string. If the data is non-empty and already ends with a newline byte, it is returned unchanged. Otherwise a single newline byte is appended. Empty input therefore produces a lone newline. The raw resulting bytes are emitted verbatim (no extra wrapping, labels, or trailing additions beyond the one normalized newline).

**Test Cases:** `rcb_tests/public_test_cases/feature2_posix_newline.json`

```json
{
    "description": "Ensure a chunk of output text is terminated by exactly one trailing newline so it is POSIX-compliant. If the input already ends with a newline it is returned unchanged; otherwise a single newline byte is appended. Empty input yields just a newline. The raw resulting bytes are emitted verbatim.",
    "cases": [
        {"input": {"action": "add_newline", "data": "no_newline_secret"}, "expected_output": "no_newline_secret\n"},
        {"input": {"action": "add_newline", "data": "trailing_newline_secret\n"}, "expected_output": "trailing_newline_secret\n"}
    ]
}
```

---

### Feature 3: Environment-Variable Name Validation

**As a developer**, I want to validate names before using them as environment variables, so I can reject malformed names early under whichever ruleset applies.

**Expected Behavior / Usage:**

*3.1 Portable-Charset Validation — validate against the portable character set (IEEE Std 1003.1)*

The input carries a `name` string. The name is valid only when it is non-empty and every character lies within the allowed portable character ranges, which explicitly exclude the NUL character and the `=` character (and exclude control characters outside the permitted low range, and characters at or above the high boundary). A valid name reports `valid=true`. An invalid name reports `valid=false` followed by a neutral category line `error=invalid_envar_name`. Each emitted line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_envar_charset.json`

```json
{
    "description": "Validate whether a string is an acceptable environment-variable name under the portable character set (IEEE Std 1003.1): every character must fall within the allowed portable ranges, and the NUL and '=' characters are forbidden. An empty string is invalid. A valid name reports success; an invalid name reports failure together with a neutral error category.",
    "cases": [
        {"input": {"action": "validate_envar_name", "name": "foo"}, "expected_output": "valid=true\n"},
        {"input": {"action": "validate_envar_name", "name": "a=b"}, "expected_output": "valid=false\nerror=invalid_envar_name\n"}
    ]
}
```

*3.2 POSIX-Shell Name Validation — validate against the stricter POSIX shell rule*

The input carries a `name` string. Under the stricter POSIX rule the name must be non-empty, may contain only ASCII letters, digits, and underscores, and must not begin with a digit; letters of any case are allowed. A conforming name reports `posix_valid=true`; otherwise `posix_valid=false`. The emitted line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_envar_posix.json`

```json
{
    "description": "Validate whether a string is a POSIX-shell-compliant environment-variable name: it may contain only ASCII letters, digits, and underscores, must be non-empty, and must not begin with a digit. Letters of any case are allowed. Names that are empty, start with a digit, or contain any other character are rejected.",
    "cases": [
        {"input": {"action": "validate_posix_name", "name": "abc"}, "expected_output": "posix_valid=true\n"},
        {"input": {"action": "validate_posix_name", "name": "0abc"}, "expected_output": "posix_valid=false\n"}
    ]
}
```

---

### Feature 4: Timestamp Formatting

**As a developer**, I want to render an instant as a stable machine-readable timestamp, so timestamps shown to users are unambiguous about their time zone.

**Expected Behavior / Usage:**

The input carries the calendar components `year`, `month`, `day`, `hour`, `minute`, `second` (and optional `nanosecond`), a named time zone in `location`, and a `timestamps` flag. With `timestamps` enabled, the instant is rendered in the standard internet date-time format: the date as `YYYY-MM-DD`, the literal `T`, the time as `HH:MM:SS`, and the zone's UTC offset. A zero-offset zone (for example `UTC`) is shown with a trailing `Z`; a zone with a positive offset is shown with an explicit `+HH:MM` suffix. The rendered timestamp is emitted on its own line ending with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_timestamp.json`

```json
{
    "description": "Format a calendar instant as a machine-readable timestamp. Given the date/time components and a named time zone, with timestamp mode enabled, the instant is rendered in the standard internet date-time format (date, time, and the UTC offset of the zone). A zone with no offset is shown with a 'Z' suffix; a positive-offset zone is shown with the explicit '+hh:mm' offset.",
    "cases": [
        {"input": {"action": "format_time", "timestamps": true, "year": 2018, "month": 1, "day": 1, "hour": 1, "minute": 1, "second": 1, "location": "UTC"}, "expected_output": "2018-01-01T01:01:01Z\n"},
        {"input": {"action": "format_time", "timestamps": true, "year": 2018, "month": 1, "day": 1, "hour": 1, "minute": 1, "second": 1, "location": "Europe/Amsterdam"}, "expected_output": "2018-01-01T01:01:01+01:00\n"}
    ]
}
```

---

### Feature 5: Secret-Reference Template Injection

**As a developer**, I want to expand `${...}` references inside a template by substituting supplied values, so configuration files can carry secret placeholders that are filled in at runtime.

**Expected Behavior / Usage:**

The input carries a `template` string and a `replacements` map of key→value. A placeholder begins at the start delimiter `${` and ends at the next end delimiter `}`; the text between them, trimmed of surrounding spaces, is the lookup key. Each placeholder is replaced by the value supplied for its key, while all text outside placeholders is copied through verbatim. Parsing proceeds left-to-right: once a placeholder is opened, the first `}` closes it, so a second `${` appearing before that `}` becomes literal text that is part of the current key (e.g. the template `${${}}` yields a placeholder whose key is `${` followed by the literal text `}`). A template containing no placeholders is returned unchanged, and an empty template yields empty output. On success the fully expanded text is emitted verbatim. If a referenced key has no value in the map, a neutral error `error=key_not_found` is emitted followed by a `key=` line naming the missing key. If a placeholder is opened but never closed, a neutral error `error=tag_not_closed` is emitted followed by a `delimiter=` line naming the missing closing delimiter. Error lines each end with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_template_inject.json`

```json
{
    "description": "Inject named values into a template string. Placeholders are written between the start delimiter '${' and the end delimiter '}', and the trimmed text between them is the lookup key; each placeholder is replaced by the value supplied for that key, while text outside placeholders is copied verbatim. Parsing is left-to-right and treats a second '${' before the matching '}' as part of the current key. A template with no placeholders is returned unchanged. If a referenced key has no supplied value, a neutral key-not-found error naming the missing key is reported; if a placeholder is opened but never closed, a neutral tag-not-closed error naming the missing delimiter is reported.",
    "cases": [
        {"input": {"action": "inject_template", "template": "${danny/example-repo/hello}", "replacements": {"danny/example-repo/hello": "hello world"}}, "expected_output": "hello world"},
        {"input": {"action": "inject_template", "template": "${ danny/example-repo/hello }${ danny/example-repo/hello2}", "replacements": {"danny/example-repo/hello": "hello world"}}, "expected_output": "error=key_not_found\nkey=danny/example-repo/hello2\n"},
        {"input": {"action": "inject_template", "template": "${ foobar", "replacements": {}}, "expected_output": "error=tag_not_closed\ndelimiter=}\n"}
    ]
}
```

---

### Feature 6: Streaming Output Secret-Masking

**As a developer**, I want secret values redacted from a stream of output as it is written, so secrets never leak into logs or the terminal even when split across multiple writes.

**Expected Behavior / Usage:**

The writer is configured with `masks` (a list of secret strings to redact) and a `mask_string` (the replacement text). The input supplies `writes`, an ordered list of chunks that are written to the stream one after another. Every occurrence of any secret in the concatenated stream is replaced by the replacement string. Matching works across chunk boundaries, and overlapping/enclosing secrets are handled (a longer secret that contains a shorter one is still fully matched). Consecutive masked bytes collapse into a single replacement (a secret immediately followed by another secret, with a separator between, yields two replacements with that separator preserved). Bytes that form only a partial match of a secret at the very end of the stream — never completed — are emitted unmasked. The fully processed output is emitted verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature6_masking.json`

```json
{
    "description": "Mask sensitive substrings as they stream through an output writer. The writer is configured with a list of secret byte sequences and a replacement string; any occurrence of a secret in the streamed bytes (even spanning multiple writes, even when one secret encloses another) is replaced by the replacement string, and consecutive masked bytes collapse into a single replacement. Bytes that only partially match a secret at the end of the stream are emitted unmasked. Input is supplied as an ordered list of write chunks; the fully processed output is emitted verbatim.",
    "cases": [
        {"input": {"action": "mask", "masks": ["foo", "bar"], "mask_string": "<redacted by SecretHub>", "writes": ["test foo test"]}, "expected_output": "test <redacted by SecretHub> test"},
        {"input": {"action": "mask", "masks": ["foo", "bar"], "mask_string": "<redacted by SecretHub>", "writes": ["fo", "o bar f", "o"]}, "expected_output": "<redacted by SecretHub> <redacted by SecretHub> fo"}
    ]
}
```

---

### Feature 7: Text Encoding Identification

**As a developer**, I want to identify a text encoding either from a file's leading bytes or from a named encoding string, so I can correctly read and write secret files in the right encoding.

**Expected Behavior / Usage:**

*7.1 Detection by Byte-Order Mark — guess the encoding from leading bytes*

The input carries `hex`, the leading bytes of the content as a hex string. The leading bytes are compared against the known byte-order-mark signatures of the Unicode transformation formats. Longer signatures take precedence over shorter ones that share a prefix (so a four-byte UTF-32 mark is recognized as UTF-32 rather than the two-byte UTF-16 mark it begins with). When a known mark is found, the corresponding encoding label is reported as `encoding=<label>` (one of `utf-8`, `utf-16le`, `utf-16be`, `utf-32le`, `utf-32be`); when no known mark is present, the result is `encoding=none`. The emitted line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_encoding_detect.json`

```json
{
    "description": "Detect the character encoding of a byte stream from its leading byte-order mark (BOM). The leading bytes are checked against the known BOM signatures for the Unicode transformation formats, with the longer (UTF-32) signatures taking precedence over the shorter (UTF-16) ones that share a prefix. If a known BOM is found, the corresponding encoding is reported; otherwise the result is 'none'. Input bytes are given as a hex string.",
    "cases": [
        {"input": {"action": "detect_encoding", "hex": "EFBBBF0102"}, "expected_output": "encoding=utf-8\n"},
        {"input": {"action": "detect_encoding", "hex": "010203"}, "expected_output": "encoding=none\n"}
    ]
}
```

*7.2 Lookup by Name — resolve a named encoding (case-insensitive)*

The input carries a `name` string. The name is resolved case-insensitively to a supported encoding. The Unicode transformation formats are recognized, including the BOM-using `utf-16`/`utf-32` forms and the explicit little-endian/big-endian variants, as well as common single-byte code pages. A recognized name reports its canonical label as `encoding=<label>` (e.g. `utf-8`, `utf-16`, `utf-16le`, `utf-16be`, `utf-32`, `utf-32le`, `utf-32be`, `windows-1252`); an unrecognized name reports `error=unsupported_encoding` followed by a `name=` line echoing the requested input. Lines end with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_encoding_lookup.json`

```json
{
    "description": "Resolve a character-encoding name (case-insensitive) to a supported encoding. The Unicode transformation formats are recognized, including the UTF-32 variants and explicit little-endian/big-endian forms. A recognized name reports its canonical encoding label; an unrecognized name reports a neutral unsupported-encoding error naming the requested input.",
    "cases": [
        {"input": {"action": "lookup_encoding", "name": "utf-8"}, "expected_output": "encoding=utf-8\n"},
        {"input": {"action": "lookup_encoding", "name": "unknown"}, "expected_output": "error=unsupported_encoding\nname=unknown\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above, with each primitive (permission parsing, name validation, timestamp formatting, template injection, output masking, encoding identification) in its own cohesive logical unit. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin, selects behavior by the request's `action` field (`parse_filemode`, `add_newline`, `validate_envar_name`, `validate_posix_name`, `format_time`, `inject_template`, `detect_encoding`, `lookup_encoding`, `mask`), invokes the appropriate core logic, and prints the raw result (or a neutral `error=<category>` contract) to stdout, matching the per-feature contracts above. Native errors must be translated into the neutral contract in this adapter layer; no host-language runtime traces may appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata), so it can be byte-compared directly against `expected_output`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other.


---
**Implementation notes:**
- follow the same octal formatting style as the file descriptor handling module
