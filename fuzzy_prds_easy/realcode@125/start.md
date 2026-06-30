## Product Requirement Document

# On-Device File Cache Toolkit — Cache Record Modeling, HTTP Fetch Metadata & Download Progress

## Project Goal

Build the data-modeling and metadata layer of a generic file cache that downloads remote files, stores them on a device, and remembers when each file expires, so application developers can reuse cached files instead of re-downloading them and can reason about freshness without writing their own persistence and HTTP-parsing boilerplate.

---

## Background & Problem

Applications that display or process remote files (images, documents, media) repeatedly fetch the same URLs over the network. Without a cache layer, every view costs bandwidth and latency, and developers hand-roll ad-hoc logic to track which file came from where, when it was last refreshed, and when it should be considered stale.

This toolkit provides the building blocks for such a cache: a record type that captures everything known about one cached file (its source URL, an optional lookup key, the on-disk relative path, an entity tag, a validity deadline, a stored byte length, and an internal id) together with the rules for persisting and copying that record; a metadata extractor that reads an HTTP response and decides the file extension, the entity tag, the byte length, and how long the response stays valid; and a progress calculator for streaming downloads. The features below define the externally observable input/output behavior of these pieces. They are pure data transformations: no real network or disk access is required to exercise them.

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

### Feature 1: Cache Record Modeling

**As a developer**, I want a record type that captures everything known about one cached file and supports persistence and immutable copies, so I can store, reload, and update cache entries reliably.

**Expected Behavior / Usage:**

A cache record describes one cached file. Its fields are: the source `url`, a lookup `key`, the on-disk `relativePath`, an entity tag `eTag`, a validity deadline (`validTill`), a stored byte `length`, and an internal numeric `id`. Every output renders these as `name=value` lines; absent values render as the literal `null`. Timestamps are exchanged as epoch milliseconds. The sub-features below define construction, deserialization, serialization, and copy semantics.

*1.1 Construct A Record (Key Defaulting) — Build a record from a URL with an optional explicit key*

A record is created from a source URL. If no key is supplied, the key defaults to the URL itself; if an explicit key is supplied, it is retained exactly. The URL is always kept verbatim. The output reports the resulting `url` and `key`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_construct.json`

```json
{
    "description": "Constructing a cache record from a source URL, optionally with an explicit key. When no key is supplied the record's key defaults to the URL; when an explicit key is supplied it is kept verbatim. The URL is always retained as given.",
    "cases": [
        {
            "input": {"action": "construct", "url": "baseflow.com/test.png"},
            "expected_output": "url=baseflow.com/test.png\nkey=baseflow.com/test.png\n"
        },
        {
            "input": {"action": "construct", "url": "baseflow.com/test.png", "key": "test key 1234"},
            "expected_output": "url=baseflow.com/test.png\nkey=test key 1234\n"
        }
    ]
}
```

*1.2 Deserialize A Record — Rebuild a record from a persisted flat key/value record*

A record is reconstructed from a stored flat map of columns: `_id` (numeric id), `url`, an optional `key`, `relativePath`, `eTag`, and `validTill` stored as epoch milliseconds. When the stored map omits the `key` column, the key falls back to the URL; when present it is used directly. A missing `length` column yields a null length. The output reports `id`, `url`, `key`, `relativePath`, `eTag`, `validTill_millis`, and `length`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_deserialize.json`

```json
{
    "description": "Reconstructing a cache record from a persisted flat key/value record loaded from storage. Recognised fields are the numeric id, the URL, an optional key, the relative file path, the entity tag, and the validity timestamp stored as epoch milliseconds. When the record omits the key field the key falls back to the URL; when present it is used directly. The validity timestamp is reported back as epoch milliseconds.",
    "cases": [
        {
            "input": {"action": "deserialize", "record": {"_id": 3, "url": "baseflow.com/test.png", "relativePath": "test.png", "eTag": "test1", "validTill": 1585301160000, "touched": 1585387560000}},
            "expected_output": "id=3\nurl=baseflow.com/test.png\nkey=baseflow.com/test.png\nrelativePath=test.png\neTag=test1\nvalidTill_millis=1585301160000\nlength=null\n"
        },
        {
            "input": {"action": "deserialize", "record": {"_id": 3, "url": "baseflow.com/test.png", "key": "testId1234", "relativePath": "test.png", "eTag": "test1", "validTill": 1585301160000, "touched": 1585387560000}},
            "expected_output": "id=3\nurl=baseflow.com/test.png\nkey=testId1234\nrelativePath=test.png\neTag=test1\nvalidTill_millis=1585301160000\nlength=null\n"
        }
    ]
}
```

*1.3 Serialize A Record — Flatten a record into a persistable key/value record*

A record is serialized into a flat map for persistence. The validity deadline is written as epoch milliseconds, defaulting to `0` when absent. A `touched` timestamp is stamped from the current clock at the moment of serialization (supplied via `now_millis`). The `id` entry is emitted only when the record has an id. The fields `url`, `key`, `relativePath`, `eTag`, and `length` are written through unchanged. The output reports `url`, `key`, `relativePath`, `eTag`, `validTill`, `touched`, `length`, and `id`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_serialize.json`

```json
{
    "description": "Serialising a cache record into a flat key/value record suitable for persistence. The validity timestamp is written as epoch milliseconds (or 0 when absent) and a 'touched' timestamp is stamped from the current clock at serialisation time. The id is only emitted when the record has one; the remaining identifying fields (url, key, relative path, entity tag, length) are written through unchanged.",
    "cases": [
        {
            "input": {"action": "serialize", "url": "baseflow.com/test.png", "key": "testKey1234", "relativePath": "test.png", "validTill_millis": 1585301160000, "eTag": "test1", "id": 3, "now_millis": 1585387560000},
            "expected_output": "url=baseflow.com/test.png\nkey=testKey1234\nrelativePath=test.png\neTag=test1\nvalidTill=1585301160000\ntouched=1585387560000\nlength=null\nid=3\n"
        }
    ]
}
```

*1.4 Copy A Record With Overrides — Derive a modified record while preserving the key*

A modified copy of a record is produced by overriding a single field while carrying over the rest. Any one of `url`, `id`, `relativePath`, `validTill` (as epoch milliseconds), `eTag`, or `length` may be replaced; fields not mentioned keep their original values. The `key` is always preserved from the original record and is never changed by a copy. The output reports all record fields. (The full case set in `rcb_tests/test_cases/` covers each overridable field individually; the examples below show overriding the id and the url.)

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_copy.json`

```json
{
    "description": "Producing a modified copy of a cache record by overriding a single field while leaving the others intact. Any one of url, id, relative path, validity timestamp, entity tag, or length may be replaced; fields not mentioned are carried over from the original. The key is always preserved from the original record and is never altered by a copy.",
    "cases": [
        {
            "input": {"action": "copy", "base": {"url": "www.test.com/image", "key": "test123", "relativePath": "test.png", "validTill_millis": 1585387560000, "eTag": "test1", "length": 200, "id": null}, "changes": {"id": 1}},
            "expected_output": "id=1\nurl=www.test.com/image\nkey=test123\nrelativePath=test.png\neTag=test1\nvalidTill_millis=1585387560000\nlength=200\n"
        },
        {
            "input": {"action": "copy", "base": {"url": "www.test.com/image", "key": "test123", "relativePath": "test.png", "validTill_millis": 1585387560000, "eTag": "test1", "length": 200, "id": 1}, "changes": {"url": "www.someotherurl.com"}},
            "expected_output": "id=1\nurl=www.someotherurl.com\nkey=test123\nrelativePath=test.png\neTag=test1\nvalidTill_millis=1585387560000\nlength=200\n"
        }
    ]
}
```

---

### Feature 2: HTTP Fetch Metadata Extraction

**As a developer**, I want to derive cache metadata from an HTTP response to a file request, so I know what extension to save the file under, how to revalidate it later, and how long it stays fresh.

**Expected Behavior / Usage:**

Given an HTTP response (described by a status code, an optional content length, a header map, and the reception time as `now_millis`), the extractor reports the `statusCode`, the `contentLength` (or `null`), the entity tag from the `etag` header (or `null` when absent), the file extension derived from the `content-type` header, and the validity deadline as epoch milliseconds. The validity deadline is the reception time plus a freshness window: a `cache-control: max-age=N` directive yields N seconds; when no cache directive is present the default window is one week (604800 seconds).

*2.1 Full Response Metadata — Extract status, length, entity tag, extension and validity together*

For a successful response carrying an `etag`, a recognized `content-type`, and a `max-age` cache directive, all five metadata fields are reported. The validity deadline equals the reception time plus the max-age seconds.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_response_metadata.json`

```json
{
    "description": "Extracting cache metadata from an HTTP response to a file request. The reported metadata is the HTTP status code, the content length, the entity tag (from the response's etag header, or null when absent), the file extension derived from the content type, and the validity timestamp. When the response carries a 'max-age' cache directive the content is valid for that many seconds from the moment the response is received; the validity timestamp is reported as epoch milliseconds relative to the supplied reception time.",
    "cases": [
        {
            "input": {"action": "http_response", "now_millis": 1585387560000, "status": 200, "content_length": 16, "headers": {"etag": "test", "content-type": "image/jpeg", "cache-control": "max-age=7200"}},
            "expected_output": "statusCode=200\ncontentLength=16\neTag=test\nfileExtension=.jpg\nvalidTill_millis=1585394760000\n"
        }
    ]
}
```

*2.2 File Extension From Content Type — Map media type to extension, falling back to the subtype*

The file extension is derived from the response `content-type`. A recognized media type maps to its conventional extension (for example `image/jpeg` to `.jpg`, `audio/mpeg` to `.mp3`). An unrecognized media type falls back to a dot followed by the content subtype (for example `unknown/cov` to `.cov`). Any parameters trailing the media type (such as a charset) are ignored when determining the extension. With no cache directive present, the validity deadline defaults to one week after the reception time.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_file_extension.json`

```json
{
    "description": "Deriving the on-disk file extension from an HTTP response's content type. A recognised media type maps to its conventional extension; an unrecognised media type falls back to a dot followed by the content subtype. Parameters after the media type (such as a charset) are ignored when determining the extension. With no cache directive present the content defaults to a one-week validity measured from the reception time.",
    "cases": [
        {
            "input": {"action": "http_response", "now_millis": 1585387560000, "status": 200, "content_length": 16, "headers": {"content-type": "unknown/cov"}},
            "expected_output": "statusCode=200\ncontentLength=16\neTag=null\nfileExtension=.cov\nvalidTill_millis=1585992360000\n"
        },
        {
            "input": {"action": "http_response", "now_millis": 1585387560000, "status": 200, "content_length": 16, "headers": {"content-type": "audio/mpeg;chartset=UTF-8"}},
            "expected_output": "statusCode=200\ncontentLength=16\neTag=null\nfileExtension=.mp3\nvalidTill_millis=1585992360000\n"
        }
    ]
}
```

---

### Feature 3: Download Progress Calculation

**As a developer**, I want to compute the fractional progress of a streaming download, so I can drive a progress indicator from the running byte count and the total expected size.

**Expected Behavior / Usage:**

Given the total expected size and the number of bytes downloaded so far, progress is the ratio `downloaded / total`, a value between 0 and 1. The output reports the raw `totalSize`, the raw `downloaded` count, and the computed `progress`. The progress value is rendered as a decimal fraction (for example `0.16666666666666666`, and `1.0` when the download is complete).

**Test Cases:** `rcb_tests/public_test_cases/feature3_progress.json`

```json
{
    "description": "Computing fractional download progress from the total expected size and the number of bytes downloaded so far. Progress is reported as the ratio of downloaded bytes to total size (a value between 0 and 1), alongside the raw downloaded count and total size.",
    "cases": [
        {
            "input": {"action": "progress", "total_size": 6, "downloaded": 1},
            "expected_output": "totalSize=6\ndownloaded=1\nprogress=0.16666666666666666\n"
        },
        {
            "input": {"action": "progress", "total_size": 6, "downloaded": 6},
            "expected_output": "totalSize=6\ndownloaded=6\nprogress=1.0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (cache record modeling, HTTP fetch metadata extraction, and download progress calculation). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting `name=value` report to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `construct`, `deserialize`, `serialize`, and `copy` exercise the cache record; `http_response` extracts response metadata; `progress` computes download progress. Timestamps are exchanged as epoch milliseconds; absent values render as the literal `null`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- handle zero total size per the EdgeCase handling pattern used in the LegacyModule
- exclude null ID lines following the spacing convention from the core serialization logic
