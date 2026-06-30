## Product Requirement Document

# Mobile Data Flow Starter - Observable Contracts for Feed, Preferences, Errors, and Home State

## Project Goal

Build a mobile application starter that allows developers to connect a remote list feed, local launch preferences, domain operations, and a home screen state coordinator without hand-writing repetitive data mapping, error translation, preference fallback, loading, and navigation glue for every new app.

---

## Background & Problem

Without this library/tool, developers are forced to manually translate network payloads into domain rows, convert transport failures into user-safe categories, manage first-launch preference defaults, relay repository data through use-case boundaries, and keep screen state synchronized with loading, errors, and navigation. This leads to duplicated boilerplate, inconsistent user feedback, brittle startup behavior, and hard-to-test UI state transitions.

With this library/tool, developers can rely on clear contracts for each layer: request outputs become domain rows, failures become normalized domain signals, preferences provide safe defaults, domain operations relay repository results, and the home coordinator exposes observable state that an execution adapter can render as deterministic stdout.

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

### Feature 1: Model Feed Mapping

**As a developer**, I want remote feed rows to be converted into domain model rows, so I can consume a stable model list regardless of transport payload shape.

**Expected Behavior / Usage:**

The input describes whether the upstream feed succeeds and, on success, provides a payload array containing row identifiers. A successful feed must emit `[a specific string literal sequence representing the result key]`, the total row count, and one `item[index].id=<id>` line per row in the same order as the payload. If the upstream feed fails, the output must be a normalized upstream failure for the model feed operation and must not include runtime-specific exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature1_model_feed_mapping.json`

```json
{
    "description": "The model feed converts a successful upstream list into domain model rows and forwards upstream failures as a normalized error.",
    "cases": [
        {
            "input": {"upstream": "success", "payload": [{"id": 1}]},
            "expected_output": "[a specific string literal sequence representing the result key]\ncount=1\nitem[0].id=1\n"
        }
    ]
}
```

---

### Feature 2: Request Error Mapping

**As a developer**, I want transport and protocol failures to become domain-level error signals, so I can show consistent user feedback and diagnostics without leaking runtime exception details.

**Expected Behavior / Usage:**

The input describes a request failure kind. Connectivity failures and interrupted timeouts both map to `error=no_connectivity`. HTTP failures must preserve framework-observable protocol signals by printing `http_status`, `http_message`, and the parsed response `body_message` in addition to `error=api_error`. Unhandled request I/O failures are reported as `error=unhandled_request_error` with the supplied message. All outputs include `operation=request` and must avoid host-language exception class names.

**Test Cases:** `rcb_tests/public_test_cases/feature2_request_error_mapping.json`

```json
{
    "description": "Request failures are translated into domain-level error categories while successful framework details such as HTTP status and body message remain visible.",
    "cases": [
        {
            "input": {"failure": "http", "status": 500, "status_message": "message", "body": {"message": "message"}},
            "expected_output": "error=api_error\noperation=request\nhttp_status=500\nhttp_message=message\nbody_message=message\n"
        }
    ]
}
```

---

### Feature 3: Launch Preference Storage

**As a developer**, I want the app's first-launch preference to be read and updated safely, so startup behavior remains deterministic even when preference storage has recoverable read errors.

**Expected Behavior / Usage:**

The input either provides a stored first-launch flag, requests an update, or describes a read failure. Reading a stored value must output `first_time_launch=<value>`. A recoverable preference read I/O failure must fall back to `[the boolean value used to mark the first launch event in the system]`. Unexpected preference read failures must be normalized as an upstream failure for `operation=preference_read`. Updating the preference to a supplied boolean must persist that value so a subsequent read emits the same flag.

**Test Cases:** `rcb_tests/public_test_cases/feature3_launch_preference_storage.json`

```json
{
    "description": "Launch preference storage returns the saved first-launch flag, falls back to true on read I/O failure, propagates unexpected read failures, and persists updates.",
    "cases": [
        {
            "input": {"stored_value": false},
            "expected_output": "[the boolean value used to mark the first launch event in the system]\n"
        },
        {
            "input": {"failure": "io_on_read"},
            "expected_output": "[the boolean value used to mark the first launch event in the system]\n"
        }
    ]
}
```

---

### Feature 4: Domain Model Query

**As a developer**, I want a domain-level model query to relay repository results and failures, so application code can depend on a stable use-case boundary rather than a concrete data source.

**Expected Behavior / Usage:**

The input describes a repository result or repository failure. On success, the query must emit the repository's model list unchanged using the same `[a specific string literal sequence representing the result key]`, `count`, and `item[index].id` stdout format as the feed contract. On failure, it must emit a normalized upstream failure with `operation=model_query`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_domain_model_query.json`

```json
{
    "description": "The domain model query emits the repository's model list unchanged and forwards upstream failures as a normalized query error.",
    "cases": [
        {
            "input": {"repository": "success", "repository_result": [{"id": 1}]},
            "expected_output": "[a specific string literal sequence representing the result key]\ncount=1\nitem[0].id=1\n"
        }
    ]
}
```

---

### Feature 5: Launch Preference Operations

**As a developer**, I want domain-level launch preference operations for reading and writing the first-launch flag, so preference access is expressed through a stable application boundary.

**Expected Behavior / Usage:**

The input either provides a stored first-launch flag to read or an `update_to` flag to write. Reads must emit `first_time_launch=<value>`. Writes must call the underlying preference update exactly once with the requested value and render both `updated_value=<value>` and `write_count=1`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_launch_preference_operations.json`

```json
{
    "description": "Launch preference operations read the current first-launch flag and write a requested flag exactly once.",
    "cases": [
        {
            "input": {"update_to": true},
            "expected_output": "updated_value=true\nwrite_count=1\n"
        }
    ]
}
```

---

### Feature 6: Home State Coordinator

**As a developer**, I want the home state coordinator to combine feed data, launch preference state, loading, errors, and navigation, so the screen can render and react consistently from observable state.

**Expected Behavior / Usage:**

The input selects a home scenario and supplies feed status, feed rows, and first-launch preference state where applicable. A loaded home scenario must expose the `Home` screen title, a loading transition sequence, visible model identifiers in feed order, the first-launch flag, and no toast. A selected model navigation scenario must emit a route containing the selected model identifier. Hidden cases additionally verify that model loading failures render the generic error toast and that first-launch acknowledgement emits the first-launch toast, writes `false`, and updates the exposed flag to false.

**Test Cases:** `rcb_tests/public_test_cases/feature6_home_state_coordinator.json`

```json
{
    "description": "The home state coordinator exposes a Home screen title, loaded item identifiers, loading transitions, first-launch acknowledgement, generic error toast, and route navigation from a selected model.",
    "cases": [
        {
            "input": {"scenario": "show_loaded_home", "model_feed_status": "success", "model_feed": [{"id": 1}, {"id": 2}, {"id": 3}], "first_time_launch": false},
            "expected_output": "screen_title=Home\nloading_sequence=false,true,false\nvisible_model_ids=1,2,3\n[the boolean value used to mark the first launch event in the system]\n[the specific string assigned to the toast notification when the home screen loads normally]\n"
        },
        {
            "input": {"scenario": "navigate_from_model", "model_feed_status": "success", "model_feed": [{"id": 1}, {"id": 2}, {"id": 3}], "first_time_launch": false},
            "expected_output": "navigation_route=second/1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin or from the test harness case runner, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_model_feed_mapping.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_model_feed_mapping@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same formatting and separator rules as the navigation routing scheme used in C016
- adhere to the version incremented header pattern defined by the database output contract
