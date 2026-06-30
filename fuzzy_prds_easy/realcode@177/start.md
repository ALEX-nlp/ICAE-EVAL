## Product Requirement Document

# HTTP Test Double Toolkit - Mock Request and Response Contracts for Handler Tests

## Project Goal

Build an HTTP test-double library that allows developers to exercise request handlers, response logic, and content negotiation behavior without starting a network server or manually constructing protocol objects.

---

## Background & Problem

Without this library/tool, developers are forced to create ad hoc request and response doubles by hand for each handler test. This leads to repetitive setup, incomplete protocol behavior, fragile assertions, and tests that fail to capture important HTTP-visible state such as status codes, headers, body data, redirects, and accepted formats.

With this library/tool, developers can create configurable in-memory request and response objects that behave like the HTTP objects used by common server frameworks, while still exposing deterministic inspection points for assertions.

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

### Feature 1: Mock Request Objects

**As a developer**, I want to create in-memory HTTP request objects with configurable protocol state, so I can test handler code without a live HTTP client.

**Expected Behavior / Usage:**

*1.1 Request State Defaults and Options — Request construction produces default visible request state and copies supplied request metadata into the resulting object.*

A newly created request has method `GET`, empty URL-derived fields, empty containers for route parameters, cookies, headers, body, query, and files, and absent optional session or signed-cookie state. When the input supplies method, URL, base URL, original URL, route parameters, session, cookies, signed cookies, headers, body, files, and additional custom request metadata, the created request exposes those values. If a path is supplied without a URL, that path becomes the observable URL.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_request_defaults_and_options.json`

```json
{
    "description": "A request object exposes default HTTP request state and copies supplied route, URL, header, body, query, file, cookie, and custom metadata into observable fields.",
    "cases": [
        {
            "input": {
                "scenario": "request_state"
            },
            "expected_output": "method=GET\nurl=\noriginal_url=\nbase_url=\npath=\nparams={}\nsession=absent\ncookies={}\nsigned_cookies=absent\nheaders={}\nbody={}\nquery={}\nfiles={}\n"
        }
    ]
}
```

*1.2 Request Header Lookup — Header lookup is case-insensitive and handles referrer spelling variants.*

A request created with headers allows callers to read header values using any casing. The common `referer` and `referrer` spellings are interchangeable. Missing headers render as an absent value rather than throwing.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_request_header_lookup.json`

```json
{
    "description": "Request header lookup is case-insensitive and treats the common referrer spelling variants as equivalent; missing headers produce an absent value.",
    "cases": [
        {
            "input": {
                "scenario": "request_header_lookup",
                "options": {
                    "headers": {
                        "KEY1": "value1",
                        "Key2": "value2"
                    }
                },
                "names": [
                    "KEY1",
                    "key2",
                    "missing"
                ]
            },
            "expected_output": "lookup_KEY1=value1\nalias_KEY1=value1\nlookup_key2=value2\nalias_key2=value2\nlookup_missing=absent\nalias_missing=absent\n"
        }
    ]
}
```

*1.3 Request Content Negotiation — Request headers are used to select compatible media types and preferences.*

Given body metadata and accept-family headers, request negotiation returns the first compatible body type, response media type, encoding, charset, or language from the candidate list. If no candidate matches, the output is `false`; if a body type cannot be matched against the request body headers, the output is also `false`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_request_content_negotiation.json`

```json
{
    "description": "Request content negotiation reports the first acceptable media type, encoding, charset, or language from a candidate list and returns false when none match.",
    "cases": [
        {
            "input": {
                "scenario": "request_negotiation",
                "options": {
                    "headers": {
                        "content-type": "text/html",
                        "transfer-encoding": "chunked",
                        "accept": "text/html",
                        "Accept-Encoding": "gzip",
                        "Accept-Charset": "utf-8",
                        "Accept-Language": "en-GB"
                    }
                },
                "checks": [
                    {
                        "kind": "body_type",
                        "values": [
                            "json",
                            "html",
                            "text"
                        ]
                    },
                    {
                        "kind": "body_type",
                        "values": [
                            "json"
                        ]
                    },
                    {
                        "kind": "accept",
                        "values": [
                            "json",
                            "html"
                        ]
                    },
                    {
                        "kind": "encoding",
                        "values": [
                            "compress",
                            "gzip"
                        ]
                    },
                    {
                        "kind": "charset",
                        "values": [
                            "iso-8859-15",
                            "utf-8"
                        ]
                    },
                    {
                        "kind": "language",
                        "values": [
                            "de-DE",
                            "en-GB"
                        ]
                    }
                ]
            },
            "expected_output": "match_0=html\nmatch_1=false\nmatch_2=html\n[a specific encoding preference (requires runtime header inspection)]\nmatch_4=utf-8\nmatch_5=en-GB\n"
        }
    ]
}
```

*1.4 Request Range Parsing — Byte range headers are parsed into protocol-visible range results.*

When no range header is present, range parsing reports an absent result. Unsatisfiable ranges and malformed ranges return distinct negative sentinel values. Valid byte ranges produce a `range_type` and an ordered list of inclusive start and end offsets; when combining is requested, adjacent or overlapping ranges are collapsed.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_request_range_parsing.json`

```json
{
    "description": "A request range parser returns an absent result for absent ranges, negative sentinel values for invalid or unsatisfiable ranges, and inclusive byte ranges for valid headers with optional combining.",
    "cases": [
        {
            "input": {
                "scenario": "request_range",
                "options": {
                    "headers": {}
                },
                "size": 10
            },
            "expected_output": "range=absent\n"
        },
        {
            "input": {
                "scenario": "request_range",
                "options": {
                    "headers": {
                        "range": "bytes=90-100"
                    }
                },
                "size": 10
            },
            "expected_output": "range=-1\n"
        }
    ]
}
```

*1.5 Request Parameter Resolution — Named input values are resolved from route, body, then query containers.*

Parameter lookup checks route parameters first, body fields second, and query fields third. Falsy stored values such as `0` are returned as real values rather than treated as absent. If a name is not present and a fallback is supplied, the fallback is returned; without a fallback, the value is absent.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_request_parameter_resolution.json`

```json
{
    "description": "Request parameter lookup checks route parameters before body fields before query fields, preserves falsy values, and returns a caller-provided fallback when absent.",
    "cases": [
        {
            "input": {
                "scenario": "request_parameter_lookup",
                "options": {
                    "params": {
                        "key": "from-route"
                    },
                    "body": {
                        "key": "from-body"
                    },
                    "query": {
                        "key": "from-query"
                    }
                },
                "name": "key",
                "defaultValue": "fallback"
            },
            "expected_output": "value=from-route\n"
        },
        {
            "input": {
                "scenario": "request_parameter_lookup",
                "options": {
                    "body": {
                        "key": 0
                    },
                    "query": {
                        "key": "from-query"
                    }
                },
                "name": "key",
                "defaultValue": "fallback"
            },
            "expected_output": "value=0\n"
        }
    ]
}
```

*1.6 Request Body Stream and Host Information — Request helpers emit body payloads and derive host names from HTTP headers.*

A request can emit a supplied body payload as stream data followed by an end signal. String, structured data, numeric, buffer, and empty payloads must produce deterministic body bytes. Host information is derived from the host header by removing the port for the hostname and returning subdomains in nearest-to-farthest order; an explicitly supplied hostname overrides the host header.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_request_stream_and_host_helpers.json`

```json
{
    "description": "A mock request can emit supplied body payloads as stream data and derives hostname and subdomain information from the host header unless an explicit hostname is provided.",
    "cases": [
        {
            "input": {
                "scenario": "request_body_stream",
                "payload": {
                    "kind": "value",
                    "value": "test data"
                }
            },
            "expected_output": "data=test data\nended=true\n"
        },
        {
            "input": {
                "scenario": "request_body_stream",
                "payload": {
                    "kind": "value",
                    "value": {
                        "key": "value"
                    }
                }
            },
            "expected_output": "data={\"key\":\"value\"}\nended=true\n"
        }
    ]
}
```

---

### Feature 2: Mock Response Objects

**As a developer**, I want to create in-memory HTTP response objects that record protocol-visible output, so I can assert status, headers, body, cookies, redirects, rendering, and negotiation results.

**Expected Behavior / Usage:**

*2.1 Response Initial State and Cookies — Response construction and cookie helpers expose deterministic status, local state, and cookie records.*

A newly created response starts with status code `200`, no cookies, and any supplied local variables. Storing a cookie records its value and optional metadata. Expiring a cookie records an empty value with an expiration timestamp equivalent to the earliest positive epoch millisecond and path `/`, while preserving caller-supplied options other than overridden expiration and path.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_response_initial_state_and_cookies.json`

```json
{
    "description": "A response object starts with success status, empty cookies, and supplied local variables; cookie operations store values with options and clearing a cookie writes an expired empty cookie.",
    "cases": [
        {
            "input": {
                "scenario": "response_initial_state",
                "options": {
                    "locals": {
                        "a": "b"
                    }
                }
            },
            "expected_output": "status=200\ncookies={}\nlocals={\"a\":\"b\"}\n"
        },
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "store_cookie",
                        "name": "name",
                        "value": "value"
                    }
                ]
            },
            "expected_output": "status=200\nstatus_message=OK\nheaders={}\ncookies={\"name\":{\"options\":absent,\"value\":\"value\"}}\ndata=\nbuffer=\nencoding=absent\nended=false\nheaders_sent=false\nwritable_finished=false\ndata_length_valid=true\n"
        }
    ]
}
```

*2.2 Response Status and Body Serialization — Body sending operations update HTTP-visible status, headers, data, and completion state.*

Setting a status changes only the response status code. Sending a status code sets the status, `text/plain` content type, body text for the code, and completion state. Sending body data records strings directly, extracts body and status fields from structured values, and serializes JSON or JSONP values according to the requested operation. JSON operations set an application JSON content type, while JSONP operations set a JavaScript content type. Deprecated argument orders that include a status code are still reflected in the final status and data.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_response_status_and_body_serialization.json`

```json
{
    "description": "Response status and body operations update status code, content type, serialized data, encoding, completion flags, and emitted body data for text, status messages, JSON values, and JSONP values.",
    "cases": [
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "set_status_code",
                        "code": 404
                    }
                ]
            },
            "expected_output": "status=404\nstatus_message=OK\nheaders={}\ncookies={}\ndata=\nbuffer=\nencoding=absent\nended=false\nheaders_sent=false\nwritable_finished=false\ndata_length_valid=true\n"
        },
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "send_status_message",
                        "code": 404
                    }
                ]
            },
            "expected_output": "status=404\nstatus_message=OK\nheaders={\"content-type\":\"text/plain\"}\ncookies={}\ndata=Not Found\nbuffer=\nencoding=absent\nended=true\nheaders_sent=true\nwritable_finished=true\ndata_length_valid=true\n"
        },
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "send_body",
                        "args": [
                            {
                                "kind": "value",
                                "value": "payload"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "status=200\nstatus_message=OK\nheaders={}\ncookies={}\ndata=payload\nbuffer=\nencoding=absent\nended=true\nheaders_sent=true\nwritable_finished=true\ndata_length_valid=true\n"
        }
    ]
}
```

*2.3 Response Header Management — Headers can be set, read, appended, varied, removed, and resolved case-insensitively.*

Content type helpers resolve common shorthand types into media types. Headers can be set one at a time or in bulk, non-string scalar values are converted to strings, and reading is case-insensitive. Appending a repeated header accumulates values, while assigning the same header later replaces the accumulated value. Vary header updates avoid duplicate values regardless of case. Location setting writes the `Location` header. Removing a header deletes it regardless of name casing.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_response_header_management.json`

```json
{
    "description": "Response header management supports MIME type resolution, direct and bulk setting, appending repeated values, Vary de-duplication, case-insensitive reads, names listing, presence checks, removal, and location headers.",
    "cases": [
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "set_body_type",
                        "value": "html"
                    },
                    {
                        "type": "set_body_type",
                        "value": "txt"
                    }
                ],
                "readHeaders": [
                    "Content-Type"
                ]
            },
            "expected_output": "status=200\nstatus_message=OK\nheaders={\"content-type\":\"text/plain\"}\ncookies={}\ndata=\nbuffer=\nencoding=absent\nended=false\nheaders_sent=false\nwritable_finished=false\ndata_length_valid=true\nread_Content-Type=text/plain\n"
        },
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "assign_header",
                        "name": "name1",
                        "value": "value1"
                    },
                    {
                        "type": "assign_header_alias",
                        "name": "name2",
                        "value": "value2"
                    },
                    {
                        "type": "assign_header",
                        "values": {
                            "name3": "value3",
                            "num": 1,
                            "bool": false
                        }
                    }
                ],
                "readHeaders": [
                    "name1",
                    "name2",
                    "name3",
                    "num",
                    "bool"
                ]
            },
            "expected_output": "status=200\nstatus_message=OK\nheaders={\"bool\":\"false\",\"name1\":\"value1\",\"name2\":\"value2\",\"name3\":\"value3\",\"num\":\"1\"}\ncookies={}\ndata=\nbuffer=\nencoding=absent\nended=false\nheaders_sent=false\nwritable_finished=false\ndata_length_valid=true\nread_name1=value1\nread_name2=value2\nread_name3=value3\nread_num=1\nread_bool=false\n"
        },
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "add_header_value",
                        "name": "Link",
                        "value": "<http://localhost/>"
                    },
                    {
                        "type": "add_header_value",
                        "name": "Link",
                        "value": "<http://localhost:80/>"
                    }
                ],
                "readHeaders": [
                    "Link"
                ]
            },
            "expected_output": "status=200\nstatus_message=OK\nheaders={\"link\":[\"<http://localhost/>\",\"<http://localhost:80/>\"]}\ncookies={}\ndata=\nbuffer=\nencoding=absent\nended=false\nheaders_sent=false\nwritable_finished=false\ndata_length_valid=true\nread_Link=[\"<http://localhost/>\",\"<http://localhost:80/>\"]\n"
        }
    ]
}
```

*2.4 Response Write, End, and Status Line — Low-level response output accumulates body bytes and status-line metadata.*

Writing string chunks appends them to the response data and records any encoding. Writing buffer chunks accumulates binary chunks and exposes their concatenated buffer after the response is finished. Finishing the response sets ended, headers-sent, and writable-finished state. Writing a status line updates status code, optional status message, and headers before the body has been sent. Once body bytes have been sent, later status-line writes do not replace already visible headers.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_response_write_end_and_head.json`

```json
{
    "description": "Low-level response writing concatenates string and buffer payloads, tracks encoding and finish state, writes status line and headers before body transmission, and preserves already-sent headers from later status writes.",
    "cases": [
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "write_body_part",
                        "payload": {
                            "kind": "value",
                            "value": "payload1"
                        },
                        "encoding": "utf8"
                    },
                    {
                        "type": "write_body_part",
                        "payload": {
                            "kind": "value",
                            "value": "payload2"
                        }
                    }
                ]
            },
            "expected_output": "status=200\nstatus_message=OK\nheaders={}\ncookies={}\ndata=payload1payload2\nbuffer=\nencoding=utf8\nended=false\nheaders_sent=true\nwritable_finished=false\ndata_length_valid=true\n"
        },
        {
            "input": {
                "scenario": "response_state_after_operations",
                "actions": [
                    {
                        "type": "write_body_part",
                        "payload": {
                            "kind": "buffer",
                            "value": "payload1"
                        }
                    },
                    {
                        "type": "finish_body",
                        "payload": {
                            "kind": "buffer",
                            "value": "payload2"
                        }
                    }
                ]
            },
            "expected_output": "status=200\nstatus_message=OK\nheaders={}\ncookies={}\ndata=\nbuffer=payload1payload2\nencoding=absent\nended=true\nheaders_sent=true\nwritable_finished=true\ndata_length_valid=true\n"
        }
    ]
}
```

*2.5 Response Redirect, Render, and Format Selection — Higher-level helpers record navigation, rendering, and negotiated handler outcomes.*

Redirecting without an explicit status uses `302` and records the redirect URL; redirecting with an explicit status records that status and URL. Rendering records the view name and optional data. Rendering without a callback emits render, end, and finish events; rendering with a callback returns a null error and empty rendered body without emitting those events. Format selection calls the handler whose key best matches the request accept header, calls a default handler when provided and no match is found, sends a `406` response with `Not Acceptable` when no acceptable option exists, and reports a normalized `request_unavailable` error when no request is attached.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_response_redirect_render_and_format.json`

```json
{
    "description": "Higher-level response helpers capture redirect targets, rendered view names and data, callback rendering results, accepted response-format handlers, and 406 not-acceptable fallbacks.",
    "cases": [
        {
            "input": {
                "scenario": "response_navigation_or_rendering",
                "actions": [
                    {
                        "type": "redirect_to",
                        "args": [
                            "/path/to/redirect"
                        ]
                    }
                ]
            },
            "expected_output": "status=302\nredirect_url=/path/to/redirect\nrender_view=\nrender_data={}\nevents=[\"end\",\"finish\"]\n"
        },
        {
            "input": {
                "scenario": "response_navigation_or_rendering",
                "actions": [
                    {
                        "type": "redirect_to",
                        "args": [
                            301,
                            "/path/to/redirect"
                        ]
                    }
                ]
            },
            "expected_output": "status=301\nredirect_url=/path/to/redirect\nrender_view=\nrender_data={}\nevents=[\"end\",\"finish\"]\n"
        },
        {
            "input": {
                "scenario": "response_navigation_or_rendering",
                "actions": [
                    {
                        "type": "render_view",
                        "view": "view"
                    }
                ]
            },
            "expected_output": "status=200\nredirect_url=\nrender_view=view\nrender_data={}\nevents=[\"render\",\"end\",\"finish\"]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- See how aliases are handled in the header mapping logic
- Check the JSON serialization escape rules applied to unicode strings
