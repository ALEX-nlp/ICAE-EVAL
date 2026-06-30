## Product Requirement Document

# Git Hosting API Request Adapter - Black-Box Routing and Response Contracts

## Project Goal

Build a Git hosting API client core and execution adapter that allows developers to construct authenticated resource requests, process returned data, and inspect transport behavior without hand-coding endpoint URLs, pagination loops, and payload packaging.

---

## Background & Problem

Without this library/tool, developers are forced to manually concatenate API routes, split request data between query strings and bodies, follow pagination links, normalize returned key shapes, and handle unsupported streaming transports by hand. This leads to repetitive code, route mistakes, inconsistent payloads, and brittle test adapters.

With this library/tool, developers describe the desired resource operation and receive deterministic request construction and response handling through a small execution adapter that prints observable stdout contracts.

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

### Feature 1: Read Response Handling

**As a developer**, I want to receive resource data through a request adapter, so I can consume returned objects or arrays consistently.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `read requests`. It must invoke the core read path using a mocked transport, then print line-oriented stdout containing the rendered response data, the number of transport calls, the requested URL, the query payload, and the status. When the input asks for camel-case keys, returned object keys are converted before rendering; otherwise keys remain unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature1_read_response_handling.json`

```json
{
    "description": "Reads a resource response and renders returned data, key naming, request count, requested URL, query payload, and status without performing a real network call.",
    "cases": [
        {
            "input": {
                "feature": "read requests"
            },
            "expected_output": "response={\"prop1\":5,\"prop2\":\"test property\"}\nrequests=1\nurl=test\nquery={}\nstatus=200\n"
        },
        {
            "input": {
                "feature": "read requests",
                "mock_body": [
                    {
                        "id": 3,
                        "gravatar_enable": true
                    },
                    {
                        "id": 4,
                        "gravatar_enable": false
                    }
                ],
                "key_style": "camelCase"
            },
            "expected_output": "count=2\nfirst={\"gravatarEnable\":true,\"id\":3}\nlast={\"gravatarEnable\":false,\"id\":4}\nrequests=1\nlast_url=test\n"
        }
    ]
}
```

---

### Feature 2: Paginated Read Handling

**As a developer**, I want to follow paginated list responses, so I can retrieve complete list data without manual page loops.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `read requests` and `page_links` enabled. By default it must follow every link-based next-page hop until the server reports no further page, accumulating all records. A page limit caps how many pages are fetched, so the accumulated item count and request count shrink accordingly. Requesting a single explicit starting page disables link following and returns only that page. Stdout must include total accumulated item count, first and last records, request count, final fetched URL, and, when offset-style expanded pagination is requested, normalized pagination metadata (total, current, next, previous, per-page, total-pages).

**Test Cases:** `rcb_tests/public_test_cases/feature2_paginated_read_handling.json`

```json
{
    "description": "Reads array responses with link-based pagination and renders item count, boundary records, request count, final URL, and optional pagination metadata.",
    "cases": [
        {
            "input": {
                "feature": "read requests",
                "page_links": true
            },
            "expected_output": "count=20\nfirst={\"prop1\":1,\"prop2\":\"test property 1\"}\nlast={\"prop1\":20,\"prop2\":\"test property 20\"}\nrequests=10\nlast_url=test[standard pagination query parameters]10[standard pagination query parameters]2\n"
        },
        {
            "input": {
                "feature": "read requests",
                "page_links": true,
                "limit_pages": 3
            },
            "expected_output": "count=6\nfirst={\"prop1\":1,\"prop2\":\"test property 1\"}\nlast={\"prop1\":6,\"prop2\":\"test property 6\"}\nrequests=3\nlast_url=test[standard pagination query parameters]3[standard pagination query parameters]2\n"
        }
    ]
}
```

---

### Feature 3: Write Request Packaging

**As a developer**, I want to send create, replace, and delete operations, so I can place payload data in the correct transport field.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `write requests`. It must route create operations to POST, replace operations to PUT, and delete operations to DELETE. Stdout must show the HTTP method, endpoint URL, query or body payload after reserved transport options are separated, impersonation value when present, and returned body. Multipart form input is rendered as a neutral form marker.

**Test Cases:** `rcb_tests/public_test_cases/feature3_write_request_packaging.json`

```json
{
    "description": "Sends mutating requests and renders the HTTP verb, endpoint, separated query or body payload, impersonation value, and returned body.",
    "cases": [
        {
            "input": {
                "feature": "write requests",
                "verb": "create",
                "payload": {
                    "sudo": "yes"
                }
            },
            "expected_output": "http_method=POST\nurl=test\nquery=\nbody={}\nsudo=yes\nresult={\"accepted\":true}\n"
        },
        {
            "input": {
                "feature": "write requests",
                "verb": "create",
                "payload": {
                    "isForm": true,
                    "test": 3
                }
            },
            "expected_output": "http_method=POST\nurl=test\nquery=\nbody=\"[multipart_form]\"\nsudo=\nresult={\"accepted\":true}\n"
        }
    ]
}
```

---

### Feature 4: Stream Request Availability

**As a developer**, I want to request streaming content, so I can handle transports that may or may not support streaming.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `stream requests`. When the mocked transport supports streaming, stdout must include the stream operation name, endpoint URL, and query payload. When streaming is unavailable, stdout must print a language-neutral unsupported-stream error category and the operation name.

**Test Cases:** `rcb_tests/public_test_cases/feature4_stream_request_availability.json`

```json
{
    "description": "Requests streaming content and renders either the stream endpoint with query payload or a neutral unsupported-stream error.",
    "cases": [
        {
            "input": {
                "feature": "stream requests",
                "available": false
            },
            "expected_output": "[the specific unsupported stream error message]\n[the default operation type string]\n"
        },
        {
            "input": {
                "feature": "stream requests",
                "available": true
            },
            "expected_output": "[the default operation type string]\nurl=test\nquery={\"ref\":\"main\"}\n"
        }
    ]
}
```

---

### Feature 5: Project and Group Route Construction

**As a developer**, I want to build project and group management API calls, so I can target the correct resource routes and payloads.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `api route` for project or group catalog operations. It must translate list, create, edit, archive, fork, event, delete, directory-link, and search requests into the correct HTTP method, route URL, payload location, optional impersonation value, and response status without performing a real network call.

**Test Cases:** `rcb_tests/public_test_cases/feature5_project_and_group_routes.json`

```json
{
    "description": "Builds project and group management requests and renders the HTTP verb, route URL, payload placement, impersonation value, and response status.",
    "cases": [
        {
            "input": {
                "feature": "api route",
                "area": "project catalog",
                "request": "list projects"
            },
            "expected_output": "http_method=GET\nurl=projects\nquery={}\nbody=\nsudo=\nresponse_status=200\n"
        },
        {
            "input": {
                "feature": "api route",
                "area": "project catalog",
                "request": "archive project",
                "project": 12
            },
            "expected_output": "http_method=POST\nurl=projects/12/archive\nquery=\nbody={}\nsudo=\nresponse_status=200\n"
        }
    ]
}
```

---

### Feature 6: Branch and Commit Route Construction

**As a developer**, I want to build repository branch and commit API calls, so I can target version-sensitive and action-specific repository routes.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `api route` for branch references or commit records. It must translate branch listing, creation, protection, deletion, display, unprotection, commit listing, cherry-pick, comments, creation, diff, status, references, and related review lookups into line-oriented stdout containing HTTP method, route URL, payload placement, impersonation value, and response status. Branch creation must reflect the requested API version in its body field names.

**Test Cases:** `rcb_tests/public_test_cases/feature6_branch_and_commit_routes.json`

```json
{
    "description": "Builds branch and commit repository requests and renders the HTTP verb, route URL, payload placement, impersonation value, and response status.",
    "cases": [
        {
            "input": {
                "feature": "api route",
                "area": "branch refs",
                "request": "list branches",
                "project": 1
            },
            "expected_output": "http_method=GET\nurl=projects/1/repository/branches\nquery={}\nbody=\nsudo=\nresponse_status=200\n"
        },
        {
            "input": {
                "feature": "api route",
                "area": "branch refs",
                "request": "create branch",
                "project": 1,
                "branch": "name",
                "ref": "ref"
            },
            "expected_output": "http_method=POST\nurl=projects/1/repository/branches\nquery=\nbody={\"branch\":\"name\",\"ref\":\"ref\"}\nsudo=\nresponse_status=200\n"
        }
    ]
}
```

---

### Feature 7: Issue Route Construction

**As a developer**, I want to build issue tracking API calls, so I can target issue lists, details, time tracking, and subscriptions reliably.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `api route` for issue tracking. It must translate global, project, and group issue listing plus create, edit, delete, participant, time tracking, reset, show, subscribe, unsubscribe, and time-stat requests into stdout containing HTTP method, route URL, payload placement, impersonation value, and response status.

**Test Cases:** `rcb_tests/public_test_cases/feature7_issue_routes.json`

```json
{
    "description": "Builds issue tracking requests and renders the HTTP verb, route URL, payload placement, impersonation value, and response status.",
    "cases": [
        {
            "input": {
                "feature": "api route",
                "area": "issue tracking",
                "request": "add spent time",
                "project": 2,
                "issue": 3,
                "duration": "10m"
            },
            "expected_output": "http_method=POST\nurl=projects/2/issues/3/add_spent_time\nquery=\nbody={\"duration\":\"10m\"}\nsudo=\nresponse_status=200\n"
        },
        {
            "input": {
                "feature": "api route",
                "area": "issue tracking",
                "request": "add time estimate",
                "project": 2,
                "issue": 3,
                "duration": "10m"
            },
            "expected_output": "http_method=POST\nurl=projects/2/issues/3/time_estimate\nquery=\nbody={\"duration\":\"10m\"}\nsudo=\nresponse_status=200\n"
        }
    ]
}
```

---

### Feature 8: Merge Review Route Construction

**As a developer**, I want to build merge review API calls, so I can target approval, listing, time tracking, and review-detail routes reliably.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `api route` for merge review operations. It must translate review acceptance, time tracking, global/project/group lists, approvals, approval state, approver updates, cancel-on-success, changes, closing issues, commits, and edit requests into stdout containing HTTP method, route URL, payload placement, impersonation value, and response status.

**Test Cases:** `rcb_tests/public_test_cases/feature8_merge_review_routes.json`

```json
{
    "description": "Builds merge review requests and renders the HTTP verb, route URL, payload placement, impersonation value, and response status.",
    "cases": [
        {
            "input": {
                "feature": "api route",
                "area": "merge review",
                "request": "accept review",
                "project": 2,
                "review": 3
            },
            "expected_output": "http_method=PUT\nurl=projects/2/merge_requests/3/merge\nquery=\nbody={}\nsudo=\nresponse_status=200\n"
        },
        {
            "input": {
                "feature": "api route",
                "area": "merge review",
                "request": "add spent time",
                "project": 2,
                "review": 3,
                "duration": "10m"
            },
            "expected_output": "http_method=POST\nurl=projects/2/merge_requests/3/add_spent_time\nquery=\nbody={\"duration\":\"10m\"}\nsudo=\nresponse_status=200\n"
        }
    ]
}
```

---

### Feature 9: Repository File and Pipeline Route Construction

**As a developer**, I want to build repository file and pipeline API calls, so I can target file content and pipeline creation endpoints reliably.

**Expected Behavior / Usage:**

The adapter accepts JSON input with `feature` set to `api route` for repository files or pipeline runs. It must translate file create, edit, delete, metadata, blame, raw content, and pipeline creation requests into stdout containing HTTP method, route URL, payload placement, impersonation value, and response status.

**Test Cases:** `rcb_tests/public_test_cases/feature9_repository_file_and_pipeline_routes.json`

```json
{
    "description": "Builds repository file and pipeline creation requests and renders the HTTP verb, route URL, payload placement, impersonation value, and response status.",
    "cases": [
        {
            "input": {
                "feature": "api route",
                "area": "repository files",
                "request": "create file",
                "project": 1,
                "file_path": "path",
                "branch": "master",
                "content": "content",
                "message": "message"
            },
            "expected_output": "http_method=POST\nurl=projects/1/repository/files/path\nquery=\nbody={\"branch\":\"master\",\"commitMessage\":\"message\",\"content\":\"content\"}\nsudo=\nresponse_status=200\n"
        },
        {
            "input": {
                "feature": "api route",
                "area": "repository files",
                "request": "edit file",
                "project": 1,
                "file_path": "path",
                "branch": "master",
                "content": "content",
                "message": "message"
            },
            "expected_output": "http_method=PUT\nurl=projects/1/repository/files/path\nquery=\nbody={\"branch\":\"master\",\"commitMessage\":\"message\",\"content\":\"content\"}\nsudo=\nresponse_status=200\n"
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
- follow the neutral marker convention for forms
- quote the form body marker correctly
