## Product Requirement Document

# Multi-Source File Transfer Task Model — Construction, Serialization & Chunked Download Planning

## Project Goal

Build a reusable library that models background file-transfer *tasks* (downloads and uploads, including multi-file uploads and parallel multi-source downloads) as immutable, fully serializable value objects, so application developers can describe, persist, transmit and resume transfers across process and platform boundaries without hand-writing fragile serialization or duplicating validation logic.

---

## Background & Problem

Background transfers are typically created in one runtime, handed to a platform layer to execute, and reported back asynchronously — possibly after the originating process has been restarted. Without a shared model, developers re-implement task construction, URL assembly, validation, JSON (de)serialization, progress accounting and parallel-chunk planning in every layer, and the encodings drift apart until a task serialized on one side can no longer be understood on the other.

With this library, a transfer is a single validated value object with one canonical wire form. The same object describes a simple download, a multi-part upload, a multi-file upload, or a parallel download split across mirrors; it round-trips losslessly through its wire form; and it carries the helper logic needed to plan a chunked download and to roll up the progress and status of the resulting child pieces into the parent transfer.

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

### Feature 1: Transfer Progress Display Fields

**As a developer**, I want a progress update to expose ready-to-render display fields, so I can show transfer speed and remaining time without re-deriving formatting everywhere.

**Expected Behavior / Usage:**

A progress update is created from a progress fraction and, optionally, an expected total byte size, a network speed expressed in megabytes per second, and a remaining time expressed in whole seconds. Three boolean flags report whether each optional quantity is available (a value is unavailable when omitted, in which case it defaults to a negative sentinel). The network-speed string renders as a whole number of megabytes per second when the speed is at least one, as a whole number of kilobytes per second when the speed is between zero and one, and as a fixed placeholder when unavailable. The remaining-time string renders as zero-padded minutes and seconds, switches to hours, zero-padded minutes and seconds once an hour or more remains, and renders a fixed placeholder when unavailable. The output lists the three flags followed by the two formatted strings, one field per line.

**Test Cases:** `rcb_tests/public_test_cases/feature01_progress_display.json`

```json
{
    "description": "A transfer progress update exposes derived display fields: three boolean flags indicating whether an expected total size, a network speed, and a remaining time are available, plus a human-readable network-speed string and a human-readable remaining-time string. The input supplies a progress fraction and optionally an expected total byte size, a network speed in MB per second, and a remaining time in whole seconds; when any of those three is omitted it is treated as not-available. The speed string renders as MB per second when at least one, as kB per second when below one, and a placeholder when not available; the time string renders as MM:SS, or H:MM:SS once an hour or more remains, and a placeholder when not available.",
    "cases": [
        {
            "input": {
                "action": "progress_display",
                "progress": 0.1
            },
            "expected_output": "hasExpectedFileSize=false\nhasNetworkSpeed=false\nhasTimeRemaining=false\nnetworkSpeed=-- MB/s\ntimeRemaining=--:--\n"
        },
        {
            "input": {
                "action": "progress_display",
                "progress": 0.1,
                "expectedFileSize": 123,
                "networkSpeed": 0.2,
                "timeRemaining": 30
            },
            "expected_output": "hasExpectedFileSize=true\nhasNetworkSpeed=true\nhasTimeRemaining=true\nnetworkSpeed=[a specific numeric string representing network speed]\ntimeRemaining=00:30\n"
        }
    ]
}
```

---

### Feature 2: Task Construction & Validation

**As a developer**, I want task construction to assemble derived fields and reject invalid inputs up front, so malformed transfers fail fast instead of producing wrong behavior later.

**Expected Behavior / Usage:**

*2.1 Copy Without Overrides — produce an identical copy of a populated task*

Copying a fully-populated download task while supplying no overrides yields a new task whose every field equals the original — identifier, target url, filename, request headers and method, request body, base location, directory, group, update mode, wifi requirement, pause permission, retry count and remaining retries, metadata, and creation time. The output is the canonical serialized form of the copy. (In the serialized form, the base location and update mode are encoded as small integer codes, and the task kind is carried as a discriminator string.)

**Test Cases:** `rcb_tests/public_test_cases/feature02_copy_with.json`

```json
{
    "description": "Copying a fully-populated download task without supplying any overrides yields a task whose every field equals the original, including identifier, target location, request headers and method, request body, group, update mode, retry settings (including remaining retries), wifi requirement, pause permission, metadata and creation time. The output is the canonical serialized form of the copy.",
    "cases": [
        {
            "input": {
                "action": "build_task",
                "taskType": "DownloadTask",
                "copyWith": true,
                "taskId": "uniqueId",
                "url": "https://avmaps-dot-bbflightserver-hrd.appspot.com/public/test_post_data",
                "filename": "google.html",
                "headers": {
                    "Auth": "Test"
                },
                "httpRequestMethod": "PATCH",
                "post": "TestPost",
                "directory": "directory",
                "baseDirectory": 1,
                "group": "someGroup",
                "updates": 3,
                "requiresWiFi": true,
                "retries": 5,
                "metaData": "someMetaData",
                "creationTime": 1000
            },
            "expected_output": "{\"url\":\"https://avmaps-dot-bbflightserver-hrd.appspot.com/public/test_post_data\",\"headers\":{\"Auth\":\"Test\"},\"httpRequestMethod\":\"PATCH\",\"post\":\"TestPost\",\"retries\":5,\"retriesRemaining\":5,\"creationTime\":1000,\"taskId\":\"uniqueId\",\"filename\":\"google.html\",\"directory\":\"directory\",\"baseDirectory\":1,\"group\":\"someGroup\",\"updates\":3,\"requiresWiFi\":true,\"allowPause\":false,\"metaData\":\"someMetaData\",\"taskType\":\"DownloadTask\"}\n"
        }
    ]
}
```

*2.2 URL Query Parameter Composition — append optional query parameters to a base url*

When building a request, an optional map of query parameters is appended to the base url. With no parameters the url is unchanged; otherwise the parameters are appended in iteration order as `name=value` pairs joined by ampersands. The leading separator is a question mark when the base url contains no query string yet, or an ampersand when it already does. Values are appended verbatim (no additional encoding). The resulting url appears in the serialized task.

**Test Cases:** `rcb_tests/public_test_cases/feature03_url_query.json`

```json
{
    "description": "When building a download request, optional query parameters are appended to the base url. If no parameters are supplied the url is left unchanged; otherwise each name/value pair is appended in order. The separator is a question mark when the base url has none yet, or an ampersand when the url already contains a query string. The resulting url is reflected in the serialized task.",
    "cases": [
        {
            "input": {
                "action": "build_task",
                "taskId": "q",
                "filename": "f",
                "creationTime": 1000,
                "url": "url with space",
                "urlQueryParameters": {}
            },
            "expected_output": "{\"url\":\"url with space\",\"headers\":{},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":0,\"retriesRemaining\":0,\"creationTime\":1000,\"taskId\":\"q\",\"filename\":\"f\",\"directory\":\"\",\"baseDirectory\":0,\"group\":\"default\",\"updates\":1,\"requiresWiFi\":false,\"allowPause\":false,\"metaData\":\"\",\"taskType\":\"DownloadTask\"}\n"
        },
        {
            "input": {
                "action": "build_task",
                "taskId": "q",
                "filename": "f",
                "creationTime": 1000,
                "url": "url",
                "urlQueryParameters": {
                    "param1": "1",
                    "param2": "with space"
                }
            },
            "expected_output": "{\"url\":\"url?param1=1&param2=with space\",\"headers\":{},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":0,\"retriesRemaining\":0,\"creationTime\":1000,\"taskId\":\"q\",\"filename\":\"f\",\"directory\":\"\",\"baseDirectory\":0,\"group\":\"default\",\"updates\":1,\"requiresWiFi\":false,\"allowPause\":false,\"metaData\":\"\",\"taskType\":\"DownloadTask\"}\n"
        }
    ]
}
```

*2.3 Filename Validation — reject path separators in a filename*

A target filename must be a plain name. A plain filename is accepted and appears in the serialized task. A filename containing a path separator is rejected at construction time, surfaced as a neutral error category line, because directory information must be supplied separately from the filename.

**Test Cases:** `rcb_tests/public_test_cases/feature04_filename_validation.json`

```json
{
    "description": "A download target filename is accepted as-is when it is a plain name, and is reflected in the serialized task. A filename that contains a path separator is rejected at construction time with a neutral error category, because the directory must be specified separately from the filename.",
    "cases": [
        {
            "input": {
                "action": "build_task",
                "taskId": "t",
                "creationTime": 1000,
                "url": "https://google.com",
                "filename": "google.html"
            },
            "expected_output": "{\"url\":\"https://google.com\",\"headers\":{},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":0,\"retriesRemaining\":0,\"creationTime\":1000,\"taskId\":\"t\",\"filename\":\"google.html\",\"directory\":\"\",\"baseDirectory\":0,\"group\":\"default\",\"updates\":1,\"requiresWiFi\":false,\"allowPause\":false,\"metaData\":\"\",\"taskType\":\"DownloadTask\"}\n"
        },
        {
            "input": {
                "action": "build_task",
                "taskId": "t",
                "creationTime": 1000,
                "url": "https://google.com",
                "filename": "somedir/google.html"
            },
            "expected_output": "error=filename_has_path_separator\n"
        }
    ]
}
```

*2.4 Directory Validation — require a relative directory*

A target directory defaults to empty when omitted and is accepted as-is when relative, both appearing in the serialized task. A directory expressed as an absolute path (beginning with a path separator) is rejected at construction time as a neutral error category line, because the directory must be relative to a separately chosen base location.

**Test Cases:** `rcb_tests/public_test_cases/feature05_directory_validation.json`

```json
{
    "description": "A download target directory defaults to empty when omitted, and is accepted as-is when it is a relative path, both reflected in the serialized task. A directory given as an absolute path (one that begins with a path separator) is rejected at construction time with a neutral error category, because the directory must be relative to a chosen base directory.",
    "cases": [
        {
            "input": {
                "action": "build_task",
                "taskId": "t",
                "filename": "f",
                "creationTime": 1000,
                "url": "https://google.com"
            },
            "expected_output": "{\"url\":\"https://google.com\",\"headers\":{},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":0,\"retriesRemaining\":0,\"creationTime\":1000,\"taskId\":\"t\",\"filename\":\"f\",\"directory\":\"\",\"baseDirectory\":0,\"group\":\"default\",\"updates\":1,\"requiresWiFi\":false,\"allowPause\":false,\"metaData\":\"\",\"taskType\":\"DownloadTask\"}\n"
        },
        {
            "input": {
                "action": "build_task",
                "taskId": "t",
                "filename": "f",
                "creationTime": 1000,
                "url": "https://google.com",
                "directory": "testDir"
            },
            "expected_output": "{\"url\":\"https://google.com\",\"headers\":{},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":0,\"retriesRemaining\":0,\"creationTime\":1000,\"taskId\":\"t\",\"filename\":\"f\",\"directory\":\"testDir\",\"baseDirectory\":0,\"group\":\"default\",\"updates\":1,\"requiresWiFi\":false,\"allowPause\":false,\"metaData\":\"\",\"taskType\":\"DownloadTask\"}\n"
        }
    ]
}
```

---

### Feature 3: Lossless Serialization Round-Trips

**As a developer**, I want every transfer object and update to round-trip through one canonical wire form, so a value encoded in one runtime can be reconstructed identically in another.

**Expected Behavior / Usage:**

Each object below is reconstructed from a wire map and re-serialized to its canonical wire form. Reconstruction is tolerant of numeric fields arriving either as integers or as floating-point numbers, tolerant of extra fields some producers include, and (for updates) tolerant of the embedded task fields being either nested under a `task` key or flattened alongside the update's own fields; the re-serialized output is identical in every case. In the canonical form, enumerated values (base location, update mode, status, exception kind) are encoded as their codes/type strings, and the task kind is carried as a discriminator string.

*3.1 Download Task*

Round-trips a download task, including its target url, headers, request method, retry counters, timing, location and grouping fields.

**Test Cases:** `rcb_tests/public_test_cases/feature06_download_task_json.json`

```json
{
    "description": "A download task is reconstructed from its serialized wire map and re-serialized to a canonical form. The canonical form is stable regardless of whether numeric fields arrive as integers or as floating-point numbers, and tolerant of extra fields that some producers include. The output is the canonical serialized download task.",
    "cases": [
        {
            "input": {
                "action": "roundtrip",
                "kind": "DownloadTask",
                "json": {
                    "url": "url?a=b",
                    "headers": {
                        "c": "d"
                    },
                    "httpRequestMethod": "GET",
                    "post": null,
                    "retries": 5,
                    "retriesRemaining": 5,
                    "creationTime": 1000,
                    "taskId": "taskId",
                    "filename": "filename",
                    "directory": "dir",
                    "baseDirectory": 1,
                    "group": "group",
                    "updates": 3,
                    "requiresWiFi": true,
                    "allowPause": true,
                    "metaData": "metaData",
                    "taskType": "DownloadTask"
                }
            },
            "expected_output": "{\"url\":\"url?a=b\",\"headers\":{\"c\":\"d\"},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":5,\"retriesRemaining\":5,\"creationTime\":1000,\"taskId\":\"taskId\",\"filename\":\"filename\",\"directory\":\"dir\",\"baseDirectory\":1,\"group\":\"group\",\"updates\":3,\"requiresWiFi\":true,\"allowPause\":true,\"metaData\":\"metaData\",\"taskType\":\"DownloadTask\"}\n"
        },
        {
            "input": {
                "action": "roundtrip",
                "kind": "DownloadTask",
                "json": {
                    "allowPause": false,
                    "baseDirectory": 1,
                    "chunks": 1,
                    "creationTime": 1694879914883,
                    "directory": "",
                    "fields": {},
                    "fileField": "",
                    "filename": "com.bbflight.background_downloader.1186323287",
                    "group": "chunk",
                    "headers": {
                        "Range": "bytes=0-29836749"
                    },
                    "httpRequestMethod": "GET",
                    "metaData": "{\"parentTaskId\":\"3069222547\",\"from\":0,\"to\":29836749}",
                    "mimeType": "",
                    "requiresWiFi": false,
                    "retries": 0,
                    "retriesRemaining": 0,
                    "taskId": "1702658487",
                    "taskType": "DownloadTask",
                    "updates": 2,
                    "url": "https://storage.googleapis.com/approachcharts/test/57MB-test.ZIP",
                    "urls": []
                }
            },
            "expected_output": "{\"url\":\"https://storage.googleapis.com/approachcharts/test/57MB-test.ZIP\",\"headers\":{\"Range\":\"bytes=0-29836749\"},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":0,\"retriesRemaining\":0,\"creationTime\":1694879914883,\"taskId\":\"1702658487\",\"filename\":\"com.bbflight.background_downloader.1186323287\",\"directory\":\"\",\"baseDirectory\":1,\"group\":\"chunk\",\"updates\":2,\"requiresWiFi\":false,\"allowPause\":false,\"metaData\":\"{\\\"parentTaskId\\\":\\\"3069222547\\\",\\\"from\\\":0,\\\"to\\\":29836749}\",\"taskType\":\"DownloadTask\"}\n"
        }
    ]
}
```

*3.2 Upload Task*

Round-trips an upload task, additionally preserving the multi-part file field name, the mime type, and the extra form fields.

**Test Cases:** `rcb_tests/public_test_cases/feature07_upload_task_json.json`

```json
{
    "description": "An upload task is reconstructed from its serialized wire map and re-serialized to a canonical form, including upload-specific fields such as the file field name, the mime type and the extra form fields. The canonical form is stable regardless of whether numeric fields arrive as integers or floating-point numbers. The output is the canonical serialized upload task.",
    "cases": [
        {
            "input": {
                "action": "roundtrip",
                "kind": "UploadTask",
                "json": {
                    "url": "url?a=b",
                    "headers": {
                        "c": "d"
                    },
                    "httpRequestMethod": "PUT",
                    "post": null,
                    "retries": 5,
                    "retriesRemaining": 5,
                    "creationTime": 1000,
                    "taskId": "taskId",
                    "filename": "filename",
                    "directory": "dir",
                    "baseDirectory": 1,
                    "group": "group",
                    "updates": 3,
                    "requiresWiFi": true,
                    "allowPause": false,
                    "metaData": "metaData",
                    "taskType": "UploadTask",
                    "fileField": "fileField",
                    "mimeType": "application/octet-stream",
                    "fields": {
                        "e": "f"
                    }
                }
            },
            "expected_output": "{\"url\":\"url?a=b\",\"headers\":{\"c\":\"d\"},\"httpRequestMethod\":\"PUT\",\"post\":null,\"retries\":5,\"retriesRemaining\":5,\"creationTime\":1000,\"taskId\":\"taskId\",\"filename\":\"filename\",\"directory\":\"dir\",\"baseDirectory\":1,\"group\":\"group\",\"updates\":3,\"requiresWiFi\":true,\"allowPause\":false,\"metaData\":\"metaData\",\"taskType\":\"UploadTask\",\"fileField\":\"fileField\",\"mimeType\":\"application/octet-stream\",\"fields\":{\"e\":\"f\"}}\n"
        }
    ]
}
```

*3.3 Status Update*

Round-trips a status update: the associated task, a status code, an optional failure exception (a domain exception type name plus a description), and an optional response body.

**Test Cases:** `rcb_tests/public_test_cases/feature10_status_update_json.json`

```json
{
    "description": "A status update carries its task, a status code, an optional failure exception (with a domain exception type name and description), and an optional response body. It is reconstructed from its wire map (whether the task fields are nested or flattened, and whether numbers are integers or floating-point) and re-serialized to a canonical form. The output is the canonical serialized status update.",
    "cases": [
        {
            "input": {
                "action": "roundtrip",
                "kind": "TaskStatusUpdate",
                "json": {
                    "task": {
                        "url": "url?a=b",
                        "headers": {
                            "c": "d"
                        },
                        "httpRequestMethod": "GET",
                        "post": null,
                        "retries": 5,
                        "retriesRemaining": 5,
                        "creationTime": 1000,
                        "taskId": "taskId",
                        "filename": "filename",
                        "directory": "dir",
                        "baseDirectory": 1,
                        "group": "group",
                        "updates": 3,
                        "requiresWiFi": true,
                        "allowPause": true,
                        "metaData": "metaData",
                        "taskType": "DownloadTask"
                    },
                    "taskStatus": 4,
                    "exception": {
                        "type": "TaskConnectionException",
                        "description": "test"
                    },
                    "responseBody": null
                }
            },
            "expected_output": "{\"task\":{\"url\":\"url?a=b\",\"headers\":{\"c\":\"d\"},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":5,\"retriesRemaining\":5,\"creationTime\":1000,\"taskId\":\"taskId\",\"filename\":\"filename\",\"directory\":\"dir\",\"baseDirectory\":1,\"group\":\"group\",\"updates\":3,\"requiresWiFi\":true,\"allowPause\":true,\"metaData\":\"metaData\",\"taskType\":\"DownloadTask\"},\"taskStatus\":4,\"exception\":{\"type\":\"TaskConnectionException\",\"description\":\"test\"},\"responseBody\":null}\n"
        }
    ]
}
```

*3.4 Progress Update*

Round-trips a progress update: the associated task, a progress fraction, an expected total byte size, a network speed and a remaining time, with unset speed and time encoded as their negative sentinels.

**Test Cases:** `rcb_tests/public_test_cases/feature11_progress_update_json.json`

```json
{
    "description": "A progress update carries its task, a progress fraction, an expected total byte size, a network speed and a remaining time. It is reconstructed from its wire map (task fields nested or flattened, numbers integer or floating-point) and re-serialized to a canonical form in which unset speed and time appear as their not-available sentinels. The output is the canonical serialized progress update.",
    "cases": [
        {
            "input": {
                "action": "roundtrip",
                "kind": "TaskProgressUpdate",
                "json": {
                    "task": {
                        "url": "url?a=b",
                        "headers": {
                            "c": "d"
                        },
                        "httpRequestMethod": "GET",
                        "post": null,
                        "retries": 5,
                        "retriesRemaining": 5,
                        "creationTime": 1000,
                        "taskId": "taskId",
                        "filename": "filename",
                        "directory": "dir",
                        "baseDirectory": 1,
                        "group": "group",
                        "updates": 3,
                        "requiresWiFi": true,
                        "allowPause": true,
                        "metaData": "metaData",
                        "taskType": "DownloadTask"
                    },
                    "progress": 1.0,
                    "expectedFileSize": 123,
                    "networkSpeed": [the specific magic numeric sentinel values],
                    "timeRemaining": [the specific magic numeric sentinel values]
                }
            },
            "expected_output": "{\"task\":{\"url\":\"url?a=b\",\"headers\":{\"c\":\"d\"},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":5,\"retriesRemaining\":5,\"creationTime\":1000,\"taskId\":\"taskId\",\"filename\":\"filename\",\"directory\":\"dir\",\"baseDirectory\":1,\"group\":\"group\",\"updates\":3,\"requiresWiFi\":true,\"allowPause\":true,\"metaData\":\"metaData\",\"taskType\":\"DownloadTask\"},\"progress\":1.0,\"expectedFileSize\":123,\"networkSpeed\":[the specific magic numeric sentinel values],\"timeRemaining\":[the specific magic numeric sentinel values]}\n"
        }
    ]
}
```

*3.5 Task Record*

Round-trips a tracked record that merges a task with its status, progress fraction, expected total byte size and optional exception into a single flat map.

**Test Cases:** `rcb_tests/public_test_cases/feature12_task_record_json.json`

```json
{
    "description": "A task record merges a task with its tracked status, progress fraction, expected total byte size and optional failure exception into a single flat serialized map. It is reconstructed from its wire map (numbers integer or floating-point) and re-serialized to a canonical form. The output is the canonical serialized task record.",
    "cases": [
        {
            "input": {
                "action": "roundtrip",
                "kind": "TaskRecord",
                "json": {
                    "url": "url?a=b",
                    "headers": {
                        "c": "d"
                    },
                    "httpRequestMethod": "GET",
                    "post": null,
                    "retries": 5,
                    "retriesRemaining": 5,
                    "creationTime": 1000,
                    "taskId": "taskId",
                    "filename": "filename",
                    "directory": "dir",
                    "baseDirectory": 1,
                    "group": "group",
                    "updates": 3,
                    "requiresWiFi": true,
                    "allowPause": true,
                    "metaData": "metaData",
                    "taskType": "DownloadTask",
                    "status": 4,
                    "progress": 1.0,
                    "expectedFileSize": 123,
                    "exception": {
                        "type": "TaskUrlException",
                        "description": "test"
                    }
                }
            },
            "expected_output": "{\"url\":\"url?a=b\",\"headers\":{\"c\":\"d\"},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":5,\"retriesRemaining\":5,\"creationTime\":1000,\"taskId\":\"taskId\",\"filename\":\"filename\",\"directory\":\"dir\",\"baseDirectory\":1,\"group\":\"group\",\"updates\":3,\"requiresWiFi\":true,\"allowPause\":true,\"metaData\":\"metaData\",\"taskType\":\"DownloadTask\",\"status\":4,\"progress\":1.0,\"expectedFileSize\":123,\"exception\":{\"type\":\"TaskUrlException\",\"description\":\"test\"}}\n"
        }
    ]
}
```

*3.6 Resume Data*

Round-trips resume data pairing a task with an opaque resume payload, a required start byte and an optional entity tag; a missing entity tag is preserved as a null.

**Test Cases:** `rcb_tests/public_test_cases/feature13_resume_data_json.json`

```json
{
    "description": "Resume data pairs a task with an opaque resume payload, a required start byte and an optional entity tag. It is reconstructed from its wire map and re-serialized to a canonical form; a missing entity tag is preserved as a null. The output is the canonical serialized resume data.",
    "cases": [
        {
            "input": {
                "action": "roundtrip",
                "kind": "ResumeData",
                "json": {
                    "task": {
                        "url": "url?a=b",
                        "headers": {
                            "c": "d"
                        },
                        "httpRequestMethod": "GET",
                        "post": null,
                        "retries": 5,
                        "retriesRemaining": 5,
                        "creationTime": 1000,
                        "taskId": "taskId",
                        "filename": "filename",
                        "directory": "dir",
                        "baseDirectory": 1,
                        "group": "group",
                        "updates": 3,
                        "requiresWiFi": true,
                        "allowPause": true,
                        "metaData": "metaData",
                        "taskType": "DownloadTask"
                    },
                    "data": "data",
                    "requiredStartByte": 123,
                    "eTag": "tag"
                }
            },
            "expected_output": "{\"task\":{\"url\":\"url?a=b\",\"headers\":{\"c\":\"d\"},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":5,\"retriesRemaining\":5,\"creationTime\":1000,\"taskId\":\"taskId\",\"filename\":\"filename\",\"directory\":\"dir\",\"baseDirectory\":1,\"group\":\"group\",\"updates\":3,\"requiresWiFi\":true,\"allowPause\":true,\"metaData\":\"metaData\",\"taskType\":\"DownloadTask\"},\"data\":\"data\",\"requiredStartByte\":123,\"eTag\":\"tag\"}\n"
        }
    ]
}
```

---

### Feature 4: Multi-File Upload Construction

**As a developer**, I want to declare several files to upload in one task and have per-file metadata derived automatically, so I do not have to spell out field names and mime types for every file.

**Expected Behavior / Usage:**

A multi-file upload is built from a list whose entries are each one of: a bare filename; a pair of (field name, filename); or a triple of (field name, filename, mime type). For a bare filename the field name is the filename without its extension and the mime type is inferred from the extension; for a pair the mime type is inferred; for a triple the mime type is taken verbatim. When a mime type cannot be inferred, a generic binary type is used. The output reports the per-file field names, filenames and mime types as three ordered lists, then the same three as compact JSON-encoded strings (the form embedded in the serialized task), then the task kind discriminator.

**Test Cases:** `rcb_tests/public_test_cases/feature08_multi_upload_construction.json`

```json
{
    "description": "A multi-file upload task is built from a list describing each file. Each entry is either a bare filename, a pair of (field name, filename), or a triple of (field name, filename, mime type). For a bare filename the field name is the filename without its extension and the mime type is inferred from the extension (defaulting to a generic binary type when unknown); for a pair the mime type is inferred; for a triple the mime type is taken verbatim. The output reports the per-file field names, filenames and mime types as ordered lists, the same three as compact JSON-encoded strings, and the task type.",
    "cases": [
        {
            "input": {
                "action": "build_task",
                "taskType": "MultiUploadTask",
                "taskId": "task1",
                "url": "https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP",
                "files": [
                    "f1.txt",
                    "f2.txt"
                ]
            },
            "expected_output": "fileFields=[\"f1\",\"f2\"]\nfilenames=[\"f1.txt\",\"f2.txt\"]\nmimeTypes=[\"text/plain\",\"text/plain\"]\nfileField=[\"f1\",\"f2\"]\nfilename=[\"f1.txt\",\"f2.txt\"]\nmimeType=[\"text/plain\",\"text/plain\"]\ntaskType=MultiUploadTask\n"
        },
        {
            "input": {
                "action": "build_task",
                "taskType": "MultiUploadTask",
                "taskId": "task2",
                "url": "https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP",
                "files": [
                    [
                        "file1",
                        "f1.txt"
                    ],
                    [
                        "file2",
                        "f2.txt"
                    ]
                ]
            },
            "expected_output": "fileFields=[\"file1\",\"file2\"]\nfilenames=[\"f1.txt\",\"f2.txt\"]\nmimeTypes=[\"text/plain\",\"text/plain\"]\nfileField=[\"file1\",\"file2\"]\nfilename=[\"f1.txt\",\"f2.txt\"]\nmimeType=[\"text/plain\",\"text/plain\"]\ntaskType=MultiUploadTask\n"
        }
    ]
}
```

---

### Feature 5: Parallel Multi-Source Download Construction

**As a developer**, I want to describe a download that may be fetched from one or several mirror urls in a chosen number of chunks, so the same file can be pulled in parallel.

**Expected Behavior / Usage:**

A parallel download is built from either a single url or a list of urls that all serve the same file, plus a chunk count per url. Optional query parameters are applied to every url. The serialized task exposes the full ordered list of resolved urls and the chunk count, and its primary url is the first resolved url. The output is the canonical serialized task.

**Test Cases:** `rcb_tests/public_test_cases/feature09_parallel_construction.json`

```json
{
    "description": "A parallel download task is built from a single url or a list of urls, each providing the same file, plus a chunk count. Optional query parameters are applied to every url. The serialized task exposes the full list of resolved urls and the chunk count, and its primary url is the first resolved url. The output is the canonical serialized parallel download task.",
    "cases": [
        {
            "input": {
                "action": "build_task",
                "taskType": "ParallelDownloadTask",
                "taskId": "p1",
                "filename": "f",
                "creationTime": 1000,
                "url": "https://storage.googleapis.com/approachcharts/test/57MB-test.ZIP"
            },
            "expected_output": "{\"url\":\"https://storage.googleapis.com/approachcharts/test/57MB-test.ZIP\",\"headers\":{},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":0,\"retriesRemaining\":0,\"creationTime\":1000,\"taskId\":\"p1\",\"filename\":\"f\",\"directory\":\"\",\"baseDirectory\":0,\"group\":\"default\",\"updates\":1,\"requiresWiFi\":false,\"allowPause\":false,\"metaData\":\"\",\"taskType\":\"ParallelDownloadTask\",\"urls\":[\"https://storage.googleapis.com/approachcharts/test/57MB-test.ZIP\"],\"chunks\":1}\n"
        },
        {
            "input": {
                "action": "build_task",
                "taskType": "ParallelDownloadTask",
                "taskId": "p2",
                "filename": "f",
                "creationTime": 1000,
                "url": [
                    "https://storage.googleapis.com/approachcharts/test/57MB-test.ZIP",
                    "https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP"
                ],
                "urlQueryParameters": {
                    "a": "b"
                },
                "chunks": 5
            },
            "expected_output": "{\"url\":\"https://storage.googleapis.com/approachcharts/test/57MB-test.ZIP?a=b\",\"headers\":{},\"httpRequestMethod\":\"GET\",\"post\":null,\"retries\":0,\"retriesRemaining\":0,\"creationTime\":1000,\"taskId\":\"p2\",\"filename\":\"f\",\"directory\":\"\",\"baseDirectory\":0,\"group\":\"default\",\"updates\":1,\"requiresWiFi\":false,\"allowPause\":false,\"metaData\":\"\",\"taskType\":\"ParallelDownloadTask\",\"urls\":[\"https://storage.googleapis.com/approachcharts/test/57MB-test.ZIP?a=b\",\"https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP?a=b\"],\"chunks\":5}\n"
        }
    ]
}
```

---

### Feature 6: Ranged Chunk Splitting

**As a developer**, I want a download split into contiguous byte ranges across its sources, so each range can be fetched independently and stitched back together.

**Expected Behavior / Usage:**

Given a parallel download across one or more urls and a chunk count per url, and given the server-reported response headers, the content is divided into contiguous byte ranges. The total number of pieces equals the number of urls times the chunks per url. The piece size is the content length divided by the piece count, rounded up; each piece records its source url (cycling through the urls in order), its inclusive start and end byte offsets (the final piece ending at the last byte of the content), the chunk group it belongs to, and metadata linking it to its parent transfer together with its byte range. If the content length is absent or non-positive, or the headers do not advertise byte-range support, the split is rejected with a neutral error category line. The output lists the piece count, then one line per piece.

**Test Cases:** `rcb_tests/public_test_cases/feature14_chunk_split.json`

```json
{
    "description": "Given a ranged download split across one or more urls and a number of chunks per url, the file is divided into contiguous byte ranges. The total number of pieces is the number of urls times the chunks per url. Each piece records its source url, its inclusive start and end byte offsets (the last piece ending at the final byte of the content), the chunk group it belongs to, and metadata linking it to its parent transfer with its byte range. If the content length is missing or non-positive, or the server does not advertise range support, the split is rejected with a neutral error category. The output lists the piece count followed by one line per piece.",
    "cases": [
        {
            "input": {
                "action": "chunk_split",
                "taskId": "P",
                "url": "https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP",
                "chunks": 1,
                "headers": {
                    "content-length": "100",
                    "accept-ranges": "bytes"
                }
            },
            "expected_output": "count=1\nurl=https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP fromByte=0 toByte=99 group=chunk metaData={\"parentTaskId\":\"P\",\"from\":0,\"to\":99}\n"
        },
        {
            "input": {
                "action": "chunk_split",
                "taskId": "P",
                "url": "https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP",
                "chunks": 3,
                "headers": {
                    "content-length": "100",
                    "accept-ranges": "bytes"
                }
            },
            "expected_output": "count=3\nurl=https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP fromByte=0 toByte=33 group=chunk metaData={\"parentTaskId\":\"P\",\"from\":0,\"to\":33}\nurl=https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP fromByte=34 toByte=67 group=chunk metaData={\"parentTaskId\":\"P\",\"from\":34,\"to\":67}\nurl=https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP fromByte=68 toByte=99 group=chunk metaData={\"parentTaskId\":\"P\",\"from\":68,\"to\":99}\n"
        }
    ]
}
```

---

### Feature 7: Parent Progress & Status Aggregation From Chunks

**As a developer**, I want a parent transfer's overall progress and status derived from its child pieces, so callers see one coherent figure for a download that is internally split.

**Expected Behavior / Usage:**

After a download is split into pieces, the parent's overall progress is the average of the child progress fractions (initially zero). The parent's overall status resolves to *failed* if any child has failed; otherwise to *not-found* if any child reports not-found; otherwise to *complete* only once every child has completed; otherwise it is undetermined. A per-child progress event updates that child's fraction and yields the recomputed parent average. A per-child status event updates that child's status and yields the newly-derived parent status **only when it differs** from the previously reported parent status, yielding nothing otherwise. The driver applies a sequence of events one at a time; the output records the value derived after each event (an undetermined or unchanged result is rendered as a neutral placeholder).

**Test Cases:** `rcb_tests/public_test_cases/feature15_chunk_aggregation.json`

```json
{
    "description": "A parent transfer derives its overall progress and overall status from its child chunks. Overall progress is the average of the child progress fractions. Overall status resolves to failed if any child failed, to not-found if any child reports not-found (and none failed), to complete only once every child has completed, and is otherwise undetermined. A per-chunk status event reports the newly-derived parent status only when it changes from the previously reported one. Events drive the chunks one at a time and the output records the derived value after each event.",
    "cases": [
        {
            "input": {
                "action": "chunk_aggregate",
                "taskId": "PA",
                "url": "https://storage.googleapis.com/approachcharts/test/5MB-test.ZIP",
                "chunks": 3,
                "contentLength": 6207471,
                "events": [
                    {
                        "type": "parentProgress"
                    },
                    {
                        "type": "progress",
                        "chunk": 0,
                        "value": 0.5
                    },
                    {
                        "type": "parentStatus"
                    },
                    {
                        "type": "status",
                        "chunk": 0,
                        "value": "complete"
                    },
                    {
                        "type": "status",
                        "chunk": 2,
                        "value": "complete"
                    },
                    {
                        "type": "status",
                        "chunk": 1,
                        "value": "complete"
                    },
                    {
                        "type": "status",
                        "chunk": 0,
                        "value": "failed"
                    },
                    {
                        "type": "status",
                        "chunk": 1,
                        "value": "failed"
                    },
                    {
                        "type": "status",
                        "chunk": 2,
                        "value": "failed"
                    },
                    {
                        "type": "parentStatus"
                    },
                    {
                        "type": "status",
                        "chunk": 0,
                        "value": "notFound"
                    },
                    {
                        "type": "status",
                        "chunk": 1,
                        "value": "notFound"
                    },
                    {
                        "type": "status",
                        "chunk": 2,
                        "value": "notFound"
                    },
                    {
                        "type": "parentStatus"
                    }
                ]
            },
            "expected_output": "parent_progress=0.0\nparent_progress=0.16666666666666666\nparent_status=none\nstatus_change=none\nstatus_change=none\nstatus_change=complete\nstatus_change=failed\nstatus_change=none\nstatus_change=none\nparent_status=failed\nstatus_change=none\nstatus_change=none\nstatus_change=notFound\nparent_status=notFound\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above (task value objects and their construction/validation, the canonical serialization, the chunk-splitting planner, and the parent aggregation logic). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core business logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin (or one per case as driven by the harness), selects behavior via an `action` field, invokes the appropriate core logic, and prints the result (or a neutral error line) to stdout, matching the per-feature contracts above. All native exceptions raised by the core MUST be normalized in this adapter layer into neutral `error=<category>` lines; the core must never embed standard-output formatting.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use defaults consistent with the baseTask initialization pattern
- canonical output following the Web3ContractResponse sequence
