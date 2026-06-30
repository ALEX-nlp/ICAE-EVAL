## Product Requirement Document

# Human Verification Challenge Widget - Browser Integration Contract

## Project Goal

Build a browser UI component for embedding a third-party human verification challenge that allows developers to render, configure, and control the challenge from an application without manually wiring script injection, readiness polling, lifecycle callbacks, and imperative challenge APIs.

---

## Background & Problem

Without this library, developers are forced to manually add the challenge provider script, wait for the provider API to become available, create the challenge container, pass provider configuration, forward verification callbacks, and guard imperative operations against invalid states. This leads to repetitive integration code, fragile readiness timing, duplicated scripts, and inconsistent error handling.

With this library, developers get a single widget abstraction that creates the container, injects the provider script when requested, waits for readiness, renders with the right configuration, exposes lifecycle events, and provides safe controls for reset, manual execution, and response retrieval.

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

### Feature 1: Challenge Container Rendering

**As a developer**, I want to render a challenge host container with predictable external attributes, so I can target it with application styling and accessibility hooks.

**Expected Behavior / Usage:**

The widget accepts a presentation configuration with an optional container identifier and optional CSS class. Rendering creates one host container. If a container identifier is supplied, the container exposes that identifier. If a CSS class is supplied, the container uses it; otherwise it uses the default class `g-recaptcha`. The output reports only externally visible DOM attributes: `id=<value>` and `class=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_container_rendering.json`

```json
{
  "description": "Rendering the verification widget produces a host container whose external identifier and styling class reflect the provided presentation configuration, or the documented default class when no custom class is provided.",
  "cases": [
    {
      "input": {"scenario":"container","configuration":{"container_id":"some-id"}},
      "expected_output": "id=some-id\nclass=g-recaptcha\n"
    },
    {
      "input": {"scenario":"container","configuration":{}},
      "expected_output": "id=\nclass=g-recaptcha\n"
    }
  ]
}
```

---

### Feature 2: Custom Child Renderer Slot

**As a developer**, I want to replace the default rendered content while receiving the widget slot and controls, so I can compose the challenge inside custom layouts.

**Expected Behavior / Usage:**

When the caller supplies a child renderer, the widget invokes it and provides a challenge slot plus controls named by behavior: `render`, `reset`, `execute`, and `read_response`. The child renderer can return the supplied challenge slot for placement. The output reports whether the child renderer was called, which controls were provided, and whether the slot was present.

**Test Cases:** `rcb_tests/public_test_cases/feature2_child_renderer.json`

```json
{
  "description": "When a caller supplies a custom child renderer, the renderer is invoked with the widget slot plus the imperative controls that can render, reset, execute, and read a response.",
  "cases": [
    {
      "input": {"scenario":"render_child_slot","configuration":{}},
      "expected_output": "child_renderer_called=yes\nprovided_controls=challenge_slot,execute,read_response,render,reset\nrecaptcha_slot=present\n"
    }
  ]
}
```

---

### Feature 3: Provider Render Configuration

**As a developer**, I want widget options to be forwarded to the external challenge service accurately, so I can control challenge appearance, language, tab order, and invisible-mode behavior.

**Expected Behavior / Usage:**

When the provider service is ready and automatic rendering is enabled, the widget calls the provider render operation once. The render call includes the host container, site key, visual theme, challenge size, tab order, and verification/expiration/error callbacks. For visible challenges, badge position and isolation are omitted and the language value is forwarded. For invisible challenges, badge position and isolation are forwarded, and the language field is omitted from the provider render configuration. The output reports the provider-observable render count, container attributes, configuration fields, and callback categories.

**Test Cases:** `rcb_tests/public_test_cases/feature3_challenge_render_configuration.json`

```json
{
  "description": "When the external challenge service is ready and automatic rendering is enabled, the widget forwards the configured site key, theme, size, tab order, language, badge, isolation flag, and event callbacks to the service using the correct visible-versus-invisible rules.",
  "cases": [
    {
      "input": {"scenario":"render_config","configuration":{"site_key":"my-key","visual_theme":"dark","challenge_size":"normal","tab_order":2}},
      "expected_output": "render_calls=1\ncontainer_id=\ncontainer_class=g-recaptcha\nsitekey=my-key\ntheme=dark\nsize=normal\nbadge=undefined\ntabindex=2\nlanguage=\nisolated=undefined\ncallbacks=verify,expire,error\n"
    },
    {
      "input": {"scenario":"render_config","configuration":{"site_key":"my-key","badge_position":"[distinct badge position sentinel string from locale config]","challenge_size":"invisible","tab_order":3,"auto_render":true,"isolated":true}},
      "expected_output": "render_calls=1\ncontainer_id=\ncontainer_class=g-recaptcha\nsitekey=my-key\ntheme=light\nsize=invisible\nbadge=[distinct badge position sentinel string from locale config]\ntabindex=3\nlanguage=undefined\nisolated=true\ncallbacks=verify,expire,error\n"
    }
  ]
}
```

---

### Feature 4: Readiness and Automatic Rendering

**As a developer**, I want rendering to wait until the provider API is available, so I do not need to coordinate script loading manually.

**Expected Behavior / Usage:**

If the provider service is absent at mount time, the widget polls for readiness and renders once the service becomes available. If the service never becomes available during the observed interval, no render call occurs. The output reports the number of provider render calls after the simulated time window.

**Test Cases:** `rcb_tests/public_test_cases/feature4_readiness_and_explicit_rendering.json`

```json
{
  "description": "Rendering is deferred until the external challenge service becomes ready; explicit mode suppresses automatic rendering until the caller asks for it, and an unavailable service does not render by itself.",
  "cases": [
    {
      "input": {"scenario":"delayed_service","available_after_ms":500,"tick_ms":500,"configuration":{}},
      "expected_output": "render_calls=1\n"
    },
    {
      "input": {"scenario":"unavailable_service","tick_ms":1000,"configuration":{}},
      "expected_output": "render_calls=0\n"
    }
  ]
}
```

---

### Feature 5: Provider Script Injection

**As a developer**, I want the widget to manage the provider script safely, so pages avoid duplicated script tags while still supporting language-specific loading.

**Expected Behavior / Usage:**

By default, the widget injects the provider API script with `async` and `defer` enabled and the source `[standard async script injection URL]`. If a language is configured, the source includes an `hl` query parameter. If script injection is disabled, no script is added. If a script whose URL identifies an existing challenge provider script is already present, the widget does not inject a duplicate. Multiple widget instances share a single injected script. The output reports script count, async/defer flags, script source, and whether a language query parameter is present.

**Test Cases:** `rcb_tests/public_test_cases/feature5_script_injection.json`

```json
{
  "description": "The widget can add the external challenge API script with async and defer attributes, optionally include a language parameter, avoid injection when disabled, avoid duplicate injection for known existing challenge script URLs, and share one script across multiple widget instances.",
  "cases": [
    {
      "input": {"scenario":"script_injection","configuration":{}},
      "expected_output": "script_count=1\nscript_async=true\nscript_defer=true\nscript_src=[standard async script injection URL]\ncontains_language_param=false\n"
    },
    {
      "input": {"scenario":"script_injection","configuration":{"language":"en"}},
      "expected_output": "script_count=1\nscript_async=true\nscript_defer=true\nscript_src=[standard async script injection URL]&hl=en\ncontains_language_param=true\n"
    }
  ]
}
```

---

### Feature 6: Lifecycle and Challenge Callbacks

**As a developer**, I want the widget to forward provider lifecycle and challenge events, so application code can react to load, render, verification, expiration, and error events.

**Expected Behavior / Usage:**

The widget calls the load callback when the provider reports readiness and calls the render callback after the challenge is rendered. The provider render configuration includes callbacks for verification, expiration, and error. Triggering the verification callback forwards the response token to the caller; triggering expiration or error invokes the corresponding caller callback. The output reports per-callback call counts and the verified response token when present.

**Test Cases:** `rcb_tests/public_test_cases/feature6_callbacks.json`

```json
{
  "description": "The widget reports lifecycle and challenge events by invoking caller-provided callbacks for service load, successful render, verification with the response token, expiration, and service errors.",
  "cases": [
    {
      "input": {"scenario":"callback","configuration":{}},
      "expected_output": "on_load_calls=1\non_render_calls=1\non_verify_calls=0\nverified_response=undefined\non_expire_calls=0\non_error_calls=0\n"
    },
    {
      "input": {"scenario":"callback","trigger":"verify","response":"response","configuration":{}},
      "expected_output": "on_load_calls=1\non_render_calls=1\non_verify_calls=1\nverified_response=response\non_expire_calls=0\non_error_calls=0\n"
    }
  ]
}
```

---

### Feature 7: Imperative Challenge Controls

**As a developer**, I want to reset, execute, and read a rendered challenge through controls, so I can integrate visible and invisible challenge flows into custom user actions.

**Expected Behavior / Usage:**

After rendering, `reset` calls the provider reset operation with the rendered challenge id. In invisible mode, `execute` calls the provider execute operation with the rendered challenge id. Reading the response calls the provider response operation with the rendered challenge id and returns the provider token. The output reports the rendered id, provider call counts, ids passed to provider operations, and any returned response token.

**Test Cases:** `rcb_tests/public_test_cases/feature7_imperative_controls.json`

```json
{
  "description": "After a challenge has rendered, callers can reset it by rendered instance id, manually execute it in invisible mode by rendered instance id, and read the response token by rendered instance id.",
  "cases": [
    {
      "input": {"scenario":"control","control":"reset","render_id":"reset-test-id","configuration":{}},
      "expected_output": "rendered_id=reset-test-id\nreset_calls=1\nreset_id=reset-test-id\nexecute_calls=0\nexecute_id=undefined\nget_response_calls=0\nget_response_id=undefined\nresponse=undefined\n"
    },
    {
      "input": {"scenario":"control","control":"get_response","render_id":"get-response-test-id","response":"stubbed-response","configuration":{"challenge_size":"invisible"}},
      "expected_output": "rendered_id=get-response-test-id\nreset_calls=0\nreset_id=undefined\nexecute_calls=0\nexecute_id=undefined\nget_response_calls=1\nget_response_id=get-response-test-id\nresponse=stubbed-response\n"
    }
  ]
}
```

---

### Feature 8: Invalid Control Operation Errors

**As a developer**, I want invalid control operations to fail with stable categories, so application code and tests can distinguish state errors without depending on runtime-specific exception rendering.

**Expected Behavior / Usage:**

Attempting to render an already-rendered challenge returns `error=already_rendered`. Attempting to render before readiness returns `error=not_ready`. Attempting to reset, execute, or read a response before rendering returns `error=not_rendered`. Attempting manual execution for a visible challenge returns `error=manual_execution_requires_invisible`. Unmounting before rendering succeeds and returns `error=none`. The output includes the normalized error category and the requested operation.

**Test Cases:** `rcb_tests/public_test_cases/feature8_control_errors.json`

```json
{
  "description": "Invalid imperative operations are reported with language-neutral error categories: rendering twice, rendering before readiness, resetting or reading before rendering, executing a visible challenge, and executing before rendering all fail predictably; unmounting before rendering succeeds.",
  "cases": [
    {
      "input": {"scenario":"error","operation":"render_twice","configuration":{"auto_render":false}},
      "expected_output": "error=already_rendered\noperation=render_twice\n"
    },
    {
      "input": {"scenario":"error","operation":"execute_visible","configuration":{"challenge_size":"normal"}},
      "expected_output": "error=manual_execution_requires_invisible\noperation=execute_visible\n"
    }
  ]
}
```

---

### Feature 9: Re-rendering on Challenge Configuration Changes

**As a developer**, I want rendered challenges to refresh when challenge-defining configuration changes, so the provider always receives current site, display, language, and isolation options.

**Expected Behavior / Usage:**

After a challenge has already rendered, changing a challenge-defining configuration value causes the widget to create a fresh provider render. Challenge-defining fields include site key, visual theme, challenge size, badge position, tab order, language, and isolation. The output reports two render calls and the configuration of the latest provider render.

**Test Cases:** `rcb_tests/public_test_cases/feature9_configuration_updates.json`

```json
{
  "description": "After a challenge has already rendered, changing any challenge-defining configuration value causes a fresh service render using the updated value.",
  "cases": [
    {
      "input": {"scenario":"rerender_on_change","configuration":{},"next_configuration":{"site_key":"new-sitekey"}},
      "expected_output": "render_calls=2\ncontainer_id=\ncontainer_class=g-recaptcha\nsitekey=new-sitekey\ntheme=light\nsize=normal\nbadge=undefined\ntabindex=0\nlanguage=\nisolated=undefined\ncallbacks=verify,expire,error\n"
    },
    {
      "input": {"scenario":"rerender_on_change","configuration":{},"next_configuration":{"challenge_size":"invisible"}},
      "expected_output": "render_calls=2\ncontainer_id=\ncontainer_class=g-recaptcha\nsitekey=some-key\ntheme=light\nsize=invisible\nbadge=[distinct badge position sentinel string from locale config]\ntabindex=0\nlanguage=undefined\nisolated=false\ncallbacks=verify,expire,error\n"
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
- use the container attribute syntax defined in the feature 3 state spec
- adhere to the core system boolean flags for async script handling
