## Product Requirement Document

# In-App Notification Dispatch Service - Decoupled Publish/Subscribe Notification Coordination

## Project Goal

Build a notification dispatch service that lets application code request transient in-app notifications (and dismiss them) without being coupled to the UI surface that actually renders them. Callers ask the service to "show" or "clear" notifications; the service re-publishes each request as an event that a separate display surface subscribes to. This keeps business code free of any reference to the rendering layer while still giving it a rich, intention-revealing API.

---

## Background & Problem

Without this service, any piece of application code that wants to surface a message (a success confirmation, a validation warning, an error banner) must hold a direct reference to the visual container that draws notifications, and must know how that container stores and lays out items. This couples unrelated layers together, makes the notification container hard to relocate or replace, and forces every call site to repeat low-level wiring.

With this service, application code depends only on a small dispatch interface. It calls intent-named operations ("show an informational message", "show an error", "show a custom component", "clear all", "clear the warnings") and the service raises a corresponding event. A single display surface subscribes once to those events and owns all rendering, layout, timing, and dismissal. Producers and the renderer never reference each other directly.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
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

The service is a publish/subscribe hub. Each public operation, when invoked, raises exactly one event to whoever has subscribed; the subscriber receives the operation's arguments unchanged. The execution adapter subscribes to every event, invokes the requested operation, and renders what the subscriber observed as a line-based `key=value` contract on stdout (one field per line, no trailing summary). A severity level is one of `Info`, `Success`, `Warning`, `Error`.

### Feature 1: Request a notification at a severity level

**As a developer**, I want to request a notification at a chosen severity with an optional heading and click handler, so I can surface messages of differing importance without touching the rendering surface.

**Expected Behavior / Usage:**

A show request carries: a severity `level`; a message body supplied either as plain text (`message_kind` = `text`) or as a deferred render callback (`message_kind` = `fragment`); an optional `heading` (defaulting to an empty string when omitted); and an optional click handler (`on_click` = `true` attaches one, otherwise none). The service raises a single show event whose payload is exactly `(level, message, heading, click handler)`. The adapter reports `event=show`, then `level=<severity>`, then `heading=<heading slot value>` (empty when none was supplied), then `message=present` when a message body was attached (it always is), then `on_click=present` or `on_click=absent`. Convenience entry points that fix the severity (informational, success, warning, error) and the general level-parameterized entry point are observationally equivalent: each routes its severity into the same show event. The two message-supply forms (plain text vs. deferred render callback) are also observationally equivalent — a message body is always attached regardless of form.

**Test Cases:** `rcb_tests/public_test_cases/feature1_show_notification.json`

```json
{
    "description": "A notification dispatch service raises a show event whenever a notification is requested at a given severity level. The request carries a message body supplied either as plain text or as a deferred render callback, an optional heading (empty when none is given), and an optional click handler. The emitted output reports the routed severity level, the heading slot value, whether a message body is attached, and whether a click handler is attached. The message body is attached in every case regardless of how it was supplied, and the two message-supply forms behave identically.",
    "cases": [
        {"input": {"action": "show", "level": "Info", "message": "Sync complete", "message_kind": "text", "heading": "Account updated"}, "expected_output": "event=show\nlevel=Info\nheading=Account updated\nmessage=present\non_click=absent"},
        {"input": {"action": "show", "level": "Warning", "message": "Low disk space", "message_kind": "fragment", "on_click": true}, "expected_output": "event=show\nlevel=Warning\nheading=\nmessage=present\non_click=present"}
    ]
}
```

---

### Feature 2: Request a custom component notification

**As a developer**, I want to request a notification whose body is a custom view component (with optional parameters and display settings), so I can show rich, interactive notifications rather than just text.

**Expected Behavior / Usage:**

A custom-component request targets a view component type and may carry a key/value parameter bag (`with_parameters`) and/or display settings (`with_settings`, which bundles an integer `timeout` and a boolean `show_progress_bar`). The service raises a single show-component event whose payload is `(component type, parameter bag, settings)`. The adapter reports `event=show_component`, then `component=present` when a component reference was attached, then `parameters=present|absent`, then `settings=present|absent`, and — only when settings were attached — two further lines `[an integer value]<integer>` and `[a boolean value]<true|false>`. Two attachment rules MUST hold: (a) when neither a parameter bag nor settings are supplied, an empty parameter bag is still attached (`parameters=present`); (b) when only settings are supplied, no parameter bag is attached (`parameters=absent`). A request whose target is not a valid component type MUST be rejected: the core raises a domain error, the adapter normalizes it to the single line `error=invalid_component_type`, and no event is raised.

**Test Cases:** `rcb_tests/public_test_cases/feature2_show_component.json`

```json
{
    "description": "The dispatch service can request a custom component notification instead of a plain message. The request optionally carries a key/value parameter bag and optional display settings (a timeout and a progress-bar flag). The emitted output reports whether the component reference, the parameter bag, and the settings were attached, plus the settings values when present. Two behavioural rules hold: when neither a parameter bag nor settings are supplied, an empty parameter bag is still attached; when only settings are supplied, no parameter bag is attached. A request whose target is not a valid component type is rejected with a normalized error and raises no event.",
    "cases": [
        {"input": {"action": "show_component", "component": "valid"}, "expected_output": "event=show_component\ncomponent=present\nparameters=present\nsettings=absent"},
        {"input": {"action": "show_component", "component": "valid", "with_settings": true, "timeout": 2, "show_progress_bar": true}, "expected_output": "event=show_component\ncomponent=present\nparameters=absent\nsettings=present\n[an integer value]2\n[a boolean value]true"},
        {"input": {"action": "show_component", "component": "invalid"}, "expected_output": "error=invalid_component_type"}
    ]
}
```

---

### Feature 3: Dismiss active notifications

**As a developer**, I want to dismiss notifications — selectively by severity, all at once, or just the custom-component ones — so I can clear stale messages in response to navigation or state changes.

**Expected Behavior / Usage:**

*3.1 Dismiss by severity level — raise a level-scoped clear event carrying the requested severity.*

A clear-by-level request carries a severity `level`. The service raises a single clear-by-level event whose payload is that severity. The adapter reports `event=clear_level` then `level=<severity>`. Convenience entry points that fix the severity and the general level-parameterized entry point are observationally equivalent: each routes its severity into the same clear-by-level event.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_clear_by_level.json`

```json
{
    "description": "The dispatch service raises a clear-by-level event when asked to remove all notifications of a given severity. The emitted output reports the clear event and the severity level that was requested, so the level routed through the event can be verified.",
    "cases": [
        {"input": {"action": "clear_level", "level": "Warning"}, "expected_output": "event=clear_level\nlevel=Warning"},
        {"input": {"action": "clear_level", "level": "Error"}, "expected_output": "event=clear_level\nlevel=Error"}
    ]
}
```

*3.2 Dismiss all — raise an unscoped clear event that removes every active notification.*

A clear-all request takes no payload. The service raises a single clear-all event. The adapter reports `event=[specific level names (Info, Success, Warning, Error)]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_[specific level names (Info, Success, Warning, Error)].json`

```json
{
    "description": "The dispatch service raises a clear-all event when asked to remove every active notification regardless of severity. The emitted output reports that the clear-all event fired.",
    "cases": [
        {"input": {"action": "[specific level names (Info, Success, Warning, Error)]"}, "expected_output": "event=[specific level names (Info, Success, Warning, Error)]"}
    ]
}
```

*3.3 Dismiss custom-component notifications — raise a dedicated clear event for component-bodied notifications only.*

A clear-custom request takes no payload and is distinct from level-scoped and clear-all dismissal. The service raises a single clear-custom event. The adapter reports `event=[specific level names (Info, Success, Warning, Error)]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_[specific level names (Info, Success, Warning, Error)].json`

```json
{
    "description": "The dispatch service raises a dedicated clear-custom event when asked to remove all custom component notifications, separately from level-based and clear-all removal. The emitted output reports that the clear-custom event fired.",
    "cases": [
        {"input": {"action": "[specific level names (Info, Success, Warning, Error)]"}, "expected_output": "event=[specific level names (Info, Success, Warning, Error)]"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same field ordering convention used for the error events
- emit the default parameter bag marker as specified in the component defaults
