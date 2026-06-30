## Product Requirement Document

# Web Application Support Toolkit — Deterministic Core (Configuration, Async Chaining, Payload Marshalling & Parameter Conversion)

## Project Goal

Build a reusable support library for an annotation-driven web application framework that allows developers to resolve a project's package layout from configuration, run asynchronous tasks in a guaranteed order, serialise response payloads into well-defined wire formats, and convert raw request parameters into typed values — without each application having to reinvent this plumbing.

---

## Background & Problem

A framework that wires controllers, components and domain objects together by convention needs a small set of pure, deterministic building blocks underneath its request lifecycle: a way to learn where each kind of component lives from a single configuration descriptor, a way to chain asynchronous steps so they run strictly one after another, a way to turn handler return values (and error outcomes) into a response body in the negotiated content type, a way to remember the runtime type of the value a handler produced, and a way to coerce textual request parameters into the types a handler method declares.

Without these shared pieces, every application hand-rolls package scanning rules, ad-hoc sequencing of callbacks, bespoke JSON/text serialisation, and brittle string parsing — leading to inconsistent behaviour, duplicated boilerplate, and subtle ordering or formatting bugs. This library provides one well-defined, side-effect-free contract for each of these concerns so the rest of the framework can depend on stable, observable behaviour.

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

### Feature 1: Component Package Layout Resolution

**As a developer**, I want to derive where each kind of component lives from a single configuration descriptor, so I can configure a whole application with one base package while still being able to override individual locations.

**Expected Behavior / Usage:**

The input is a configuration descriptor (a key/value object). It may carry a single base package value. When it does, the locations of four component roles are derived by appending a fixed conventional suffix to that base: the controller role gets the `.controllers` suffix, the component/verticle role gets `.verticles`, the fixture role gets `.fixtures`, and the domain role gets `.domains`. The descriptor may also carry explicit locations for any of these roles; an explicit value always takes precedence over the convention-derived one. The controller and fixture roles are multi-valued (a list of locations), while the component/verticle and domain roles are single values. The output lists the resolved location of each of the four roles, one per line, as `controller_packages=...`, `verticle_package=...`, `fixture_packages=...`, `domain_package=...` (list-valued roles join their entries with commas).

**Test Cases:** `rcb_tests/public_test_cases/feature1_config_layout.json`

```json
{
    "description": "Resolve the component package layout of an annotation-driven web application from a JSON configuration descriptor. The descriptor may provide a single base package; in that case the locations of the controller, verticle/component, fixture and domain packages are each derived by appending a fixed conventional suffix to that base. The descriptor may instead (or additionally) provide explicit package locations for any of these roles, and any explicitly provided value overrides the convention-derived one. Controller and fixture locations are multi-valued lists; the verticle/component and domain locations are single values. The output reports each resolved location.",
    "cases": [
        {
            "input": {"op": "config", "config": {"src-package": "com.example.app"}},
            "expected_output": "controller_packages=com.example.app.controllers\nverticle_package=com.example.app.verticles\nfixture_packages=com.example.app.fixtures\ndomain_package=com.example.app.domains\n"
        },
        {
            "input": {"op": "config", "config": {"src-package": "com.example.app", "controller-packages": ["my.controllers"], "verticle-package": "my.verticles", "fixture-packages": ["my.fixtures"], "domain-package": "my.domain"}},
            "expected_output": "controller_packages=my.controllers\nverticle_package=my.verticles\nfixture_packages=my.fixtures\ndomain_package=my.domain\n"
        }
    ]
}
```

---

### Feature 2: Sequential Asynchronous Task Chaining

**As a developer**, I want to run an ordered list of asynchronous one-shot tasks strictly in sequence, so each step completes before the next begins regardless of how long any individual step takes.

**Expected Behavior / Usage:**

The input gives the number of tasks to schedule. Each task, when it runs, appends its zero-based position followed by a semicolon to a shared accumulator and then signals its own completion; the next task is only started once the previous one has completed. Because the chain is strictly sequential, the accumulator always ends up listing positions in ascending order. An empty task list is considered finished immediately with an empty accumulator. The output reports the final accumulator as `order=...`, the number of scheduled tasks as `length=...`, and whether the chain finished successfully as `completed=yes` (or `completed=no`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_async_chaining.json`

```json
{
    "description": "Run an ordered list of asynchronous one-shot tasks strictly in sequence, where each task signals its own completion before the next is allowed to begin. The input gives the number of tasks to schedule; each task appends its zero-based position followed by a semicolon to a shared accumulator and then completes. Because the chain is sequential, the accumulator always lists the positions in ascending order regardless of how long any individual task takes. The output reports the accumulated order string, the number of tasks, and whether the chain finished successfully. An empty task list completes immediately with an empty order string.",
    "cases": [
        {
            "input": {"op": "chain", "count": 10},
            "expected_output": "order=0;1;2;3;4;5;6;7;8;9;\nlength=10\ncompleted=yes\n"
        },
        {
            "input": {"op": "chain", "count": 0},
            "expected_output": "order=\nlength=0\ncompleted=yes\n"
        }
    ]
}
```

---

### Feature 3: Response Payload Type Tracking

**As a developer**, I want a response payload holder to remember the runtime type of the value a handler produced, so downstream content negotiation can react to that type.

**Expected Behavior / Usage:**

A freshly created payload holder is empty and reports a sentinel empty type token (`Void`). Once a value is placed into the holder, it reports the concrete type of that value instead. The output prints the reported type right after creation and, when a value is supplied, again after the value has been set — so the transition from empty to typed is observable. A supplied object value carrying name and breed attributes is treated as a domain entity (reported type `Dog`); a supplied scalar value is treated as text (reported type `String`). Each reported type is printed on its own line as `type=...`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_payload_type.json`

```json
{
    "description": "Track the runtime type carried by a response payload holder. A freshly created holder is empty and reports a sentinel empty type. Once a value is placed into the holder, it reports the concrete type of that value instead. The output prints the reported type immediately after creation and, when a value is supplied, again after the value has been set, so the transition from empty to typed is observable. A supplied object value with name and breed attributes is treated as a domain entity; a supplied scalar value is treated as a text value.",
    "cases": [
        {
            "input": {"op": "payload", "value": {"name": "Snoopy", "breed": "Beagle"}},
            "expected_output": "type=Void\ntype=Dog\n"
        },
        {
            "input": {"op": "payload", "value": "hello"},
            "expected_output": "type=Void\ntype=String\n"
        }
    ]
}
```

---

### Feature 4: JSON Payload Marshalling

**As a developer**, I want to serialise a handler's return value into a JSON body under the JSON content type, so successful responses are emitted in a uniform machine-readable format.

**Expected Behavior / Usage:**

The input names the kind of payload and its data. A domain entity is serialised field by field, exposing all of its bean-style properties — including a not-yet-assigned numeric property (rendered as `null`) and a boolean property — as JSON members. A structured object value is serialised as a JSON object and a structured array value as a JSON array, each reproduced faithfully. The output reports the negotiated media type as `media_type=application/json` followed by the serialised body as `body=<json>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_json_marshalling.json`

```json
{
    "description": "Serialise a response payload to a JSON representation under the JSON content type. A domain entity is serialised field by field, exposing all of its bean-style properties (including null and boolean-valued ones) as JSON members. A structured object value is serialised as a JSON object and a structured array value as a JSON array, each reproduced faithfully. The output reports the negotiated media type and the serialised body.",
    "cases": [
        {
            "input": {"op": "marshal_json", "kind": "domain", "name": "Snoopy", "breed": "Beagle"},
            "expected_output": "media_type=application/json\nbody={\"age\":null,\"name\":\"Snoopy\",\"breed\":\"Beagle\",\"puppy\":false}\n"
        },
        {
            "input": {"op": "marshal_json", "kind": "json_object", "data": {"Bill": "Cocker"}},
            "expected_output": "media_type=application/json\nbody={\"Bill\":\"Cocker\"}\n"
        }
    ]
}
```

---

### Feature 5: JSON Error & Status Marshalling

**As a developer**, I want error outcomes rendered into a JSON error body, so clients receive a consistent, code-carrying error shape instead of leaking internal failure details.

**Expected Behavior / Usage:**

For an explicit HTTP status outcome, the body wraps an `error` object carrying the numeric status `code` and the associated `message`. For an unexpected internal failure rendered without detail disclosure, the body wraps an `error` object carrying the internal-server-error code (500) and a generic `Internal Server Error` message that does not expose any implementation detail of the underlying failure. The output reports `media_type=application/json`, the status code as `status=<code>` when an explicit status was requested, and the serialised error body as `body=<json>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_json_status_marshalling.json`

```json
{
    "description": "Render an error response body in the JSON format. For an explicit HTTP status outcome the body wraps an error object carrying the numeric status code and the associated status message. For an unexpected internal failure rendered without detail disclosure, the body wraps an error object carrying the internal-server-error code and a generic message that does not leak any implementation detail of the failure. The output reports the media type, the status code when applicable, and the serialised error body.",
    "cases": [
        {
            "input": {"op": "marshal_status", "code": 406, "message": "Not acceptable"},
            "expected_output": "media_type=application/json\nstatus=406\nbody={\"error\":{\"code\":406,\"message\":\"Not acceptable\"}}\n"
        },
        {
            "input": {"op": "marshal_status", "mode": "unexpected"},
            "expected_output": "media_type=application/json\nbody={\"error\":{\"code\":500,\"message\":\"Internal Server Error\"}}\n"
        }
    ]
}
```

---

### Feature 6: Textual Request Parameter Conversion

**As a developer**, I want raw textual request parameters coerced into the typed values a handler declares, so handlers receive ready-to-use typed arguments and malformed input fails predictably.

**Expected Behavior / Usage:**

The input supplies a raw textual value and a declared target type token. Supported target types are: `string` (passed through unchanged), `integer` (32-bit), `long` (64-bit), `float` (floating point), and `boolean` (any value other than the literal text `true` resolves to `false`). When the textual value cannot be parsed as the requested numeric type, the conversion is rejected and reported as a neutral numeric-format error category — it must NOT leak any runtime-specific failure detail. When the declared target type is one the converter does not support, it yields no value. The output reports the requested target type as `target=<token>` and then either the converted value as `value=<result>` or the neutral error category as `error=number_format` (an unsupported target type yields `value=null`).

**Test Cases:** `rcb_tests/public_test_cases/feature6_param_conversion.json`

```json
{
    "description": "Convert a raw textual request parameter into a typed value according to a declared target type. Supported target types include text (passed through unchanged), 32-bit and 64-bit integers, floating point, and boolean (any value other than the literal true text resolves to false). When the textual value cannot be parsed as the requested numeric type, the conversion is rejected and reported as a neutral numeric-format error category rather than leaking any runtime-specific failure detail. When the declared target type is one the converter does not support, it yields no value. The output reports the requested target type and either the converted value or the neutral error category.",
    "cases": [
        {
            "input": {"op": "convert", "type": "integer", "value": "42"},
            "expected_output": "target=integer\nvalue=42\n"
        },
        {
            "input": {"op": "convert", "type": "integer", "value": "notanumber"},
            "expected_output": "target=integer\nerror=number_format\n"
        }
    ]
}
```

---

### Feature 7: Plain-Text Payload Marshalling

**As a developer**, I want to serialise text payloads and status outcomes under the plain-text content type, so simple textual responses avoid unnecessary structure.

**Expected Behavior / Usage:**

A text value is emitted verbatim as the body. An explicit HTTP status outcome is rendered as a single line combining the numeric status code and the status message, separated by ` : ` (space, colon, space). A non-text payload cannot be represented in this format, so the attempt is rejected and reported as a neutral unmarshallable-text error category — it must NOT leak any runtime-specific failure detail. The output reports `media_type=text/plain`, a `status=<code>` line for the explicit-status case, and then either the body as `body=<text>` or the neutral error category as `error=unmarshallable_text`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_plaintext_marshalling.json`

```json
{
    "description": "Serialise a response payload under the plain-text content type. A text value is emitted verbatim as the body. An explicit HTTP status outcome is rendered as a single line combining the numeric status code and the status message. A non-text payload cannot be represented in this format, so the attempt is rejected and reported as a neutral unmarshallable-text error category rather than leaking any runtime-specific failure detail. The output reports the media type and either the body, the status line, or the neutral error category.",
    "cases": [
        {
            "input": {"op": "marshal_text", "value": "hello world"},
            "expected_output": "media_type=text/plain\nbody=hello world\n"
        },
        {
            "input": {"op": "marshal_text", "value": 42},
            "expected_output": "error=unmarshallable_text\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (configuration layout resolution, sequential async task chaining, payload type tracking, JSON and plain-text payload/error marshalling, and textual parameter conversion). Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects behaviour via the request's `op` field (`config`, `chain`, `payload`, `marshal_json`, `marshal_status`, `marshal_text`, `convert`), invokes the appropriate core logic, and prints the resulting value-rich report to stdout, matching the per-feature contracts above. Native errors thrown by the core MUST be translated, in the adapter layer only, into the neutral `error=<category>` lines specified above (never leaking host-language exception identity).

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the output convention of the async chaining module for sequential outputs
