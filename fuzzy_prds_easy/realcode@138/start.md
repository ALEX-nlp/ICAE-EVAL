## Product Requirement Document

# Cross-Platform Error Reporting Bridge - Platform-aware event and scope synchronization

## Project Goal

Build a cross-platform error reporting bridge that allows developers to initialize browser and native reporting together, forward events to native capture, and keep native scope data synchronized without hand-writing platform-specific bridge logic.

---

## Background & Problem

Without this library/tool, developers are forced to separately configure web reporting, mobile native reporting, event transport, native availability checks, crash triggering, and scope synchronization. This leads to repetitive configuration code, mismatched session behavior between platforms, malformed native event payloads, and scope data that is missing from native crash reports.

With this library/tool, a single client setup can choose the correct platform behavior, forward events through the native bridge as structured envelopes, and mirror user, tag, extra, context, and severity data consistently.

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

### Feature 1: Client Initialization

**As a developer**, I want to initialize an error-reporting client with platform-aware session and native bridge settings, so I can get consistent web and mobile behavior from one configuration entry point.

**Expected Behavior / Usage:**

The input describes the runtime platform and client options. On a web platform, browser session tracking follows the auto-session option and native bridge settings are disabled. On mobile platforms, browser session tracking is off, native bridge startup is enabled, the native-enable reminder is enabled, and native auto-session tracking follows the auto-session option.

**Test Cases:** `rcb_tests/public_test_cases/feature1_client_initialization.json`

```json
{
  "description": "Initializes the cross-platform client with platform-specific browser-session and native-bridge settings.",
  "cases": [
    {
      "input": {"scenario":"initialize_client","platform":"web","options":{"dsn":""}},
      "expected_output": "[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n"
    },
    {
      "input": {"scenario":"initialize_client","platform":"ios","options":{"dsn":""}},
      "expected_output": "[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n"
    },
    {
      "input": {"scenario":"initialize_client","platform":"android","options":{"dsn":""}},
      "expected_output": "[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n"
    },
    {
      "input": {"scenario":"initialize_client","platform":"web","options":{"dsn":"","enableAutoSessionTracking":false}},
      "expected_output": "[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n"
    },
    {
      "input": {"scenario":"initialize_client","platform":"android","options":{"dsn":"","enableAutoSessionTracking":false}},
      "expected_output": "[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n"
    },
    {
      "input": {"scenario":"initialize_client","platform":"ios","options":{"dsn":"","enableAutoSessionTracking":false}},
      "expected_output": "[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n[a specific boolean flag string — refer to featureFlags.json]\n"
    }
  ]
}
```

---

### Feature 2: Native Bridge Startup

**As a developer**, I want to start native crash reporting only when it has enough configuration and is explicitly enabled, so I can avoid unwanted bridge calls and still receive actionable warnings.

**Expected Behavior / Usage:**

The input describes bridge startup options. When a DSN and native-enable flag are present, the bridge is initialized. Without a DSN, startup is declined and a warning is emitted without a bridge call. When native support is explicitly disabled with reminders enabled, startup is declined, native state is disabled, and the disabled warning is emitted without a bridge call.

**Test Cases:** `rcb_tests/public_test_cases/feature2_native_bridge_startup.json`

```json
{
  "description": "Starts or declines the native bridge according to DSN and native-enable options, reporting warnings and bridge calls.",
  "cases": [
    {
      "input": {"scenario":"start_native_bridge","options":{"dsn":"test","enableNative":true}},
      "expected_output": "native_started=true\nbridge_call=initialize\n"
    },
    {
      "input": {"scenario":"start_native_bridge","options":{"enableNative":true}},
      "expected_output": "native_started=false\nwarning=Warning: No DSN was provided. The Sentry SDK will be disabled. Native SDK will also not be initalized.\nbridge_call_count=0\n"
    },
    {
      "input": {"scenario":"start_native_bridge","options":{"dsn":"test","enableNative":false,"enableNativeNagger":true}},
      "expected_output": "native_started=false\nnative_enabled=false\nwarning=Note: Native Sentry SDK is disabled.\nbridge_call_count=0\n"
    }
  ]
}
```

---

### Feature 3: Event Envelope Transport

**As a developer**, I want to send error events through the native bridge in a structured envelope, so I can preserve event metadata and detect disabled native transport paths.

**Expected Behavior / Usage:**

The input describes an event send or transport send request. Enabled native sending produces a three-line envelope signal: a header with event identity and SDK metadata, an item header with content type, byte length, and item type, and a payload where the event message is nested under a message field. When native sending is disabled, the output is a neutral native-disabled error and no native length or capture bridge calls occur. The transport adapter delegates to the native event sender and surfaces the returned status.

**Test Cases:** `rcb_tests/public_test_cases/feature3_event_envelope_transport.json`

```json
{
  "description": "Serializes an error event into a native envelope and delegates transport sends through the native event sender.",
  "cases": [
    {
      "input": {"scenario":"send_error_event","event":{"event_id":"event0","message":"test","sdk":{"name":"test-sdk-name","version":"1.2.3"}}},
      "expected_output": "envelope.header={\"event_id\":\"event0\",\"sdk\":{\"name\":\"test-sdk-name\",\"version\":\"1.2.3\"}}\nenvelope.item={\"content_type\":\"application/json\",\"length\":99,\"type\":\"event\"}\nenvelope.payload={\"event_id\":\"event0\",\"message\":{\"message\":\"test\"},\"sdk\":{\"name\":\"test-sdk-name\",\"version\":\"1.2.3\"}}\ncapture_status=ok\n"
    },
    {
      "input": {"scenario":"send_error_event","enabled":false,"event":{}},
      "expected_output": "error=native_disabled\nbridge_length_calls=0\nbridge_capture_calls=0\n"
    },
    {
      "input": {"scenario":"send_event_through_transport","event":{}},
      "expected_output": "transport_status=200\nsend_event_calls=1\n"
    }
  ]
}
```

---

### Feature 4: Native Availability and Crash Forwarding

**As a developer**, I want to query native bridge availability and forward explicit crash requests, so I can verify native integration instead of silently bypassing it.

**Expected Behavior / Usage:**

The input describes either a native availability check or an explicit crash request. Availability output reports both module loading and native-client availability. A crash request forwards exactly one crash call to the native bridge and reports the bridge call signal.

**Test Cases:** `rcb_tests/public_test_cases/feature4_native_availability_and_crash.json`

```json
{
  "description": "Reports whether the native bridge is available and forwards crash requests when native support is enabled.",
  "cases": [
    {
      "input": {"scenario":"check_native_bridge_availability","plugin_available":true},
      "expected_output": "module_loaded=true\nnative_client_available=true\n"
    },
    {
      "input": {"scenario":"trigger_native_crash"},
      "expected_output": "bridge_call=crash\ncrash_calls=1\n"
    }
  ]
}
```

---

### Feature 5: Scope Data Synchronization

**As a developer**, I want to synchronize user identity, tags, extras, and contextual values to a native bridge, so I can keep native crash reports aligned with application scope data.

**Expected Behavior / Usage:**

The input describes scope data to sync. User identity is split into default identity keys and other custom keys, with empty custom-key maps preserved. Tag and extra values are string-safe: strings remain unchanged and non-strings are JSON stringified. Context values are sent as context payloads on platforms that support context, null clears context, and Android-style platforms fall back to extra payloads.

**Test Cases:** `rcb_tests/public_test_cases/feature5_scope_data_sync.json`

```json
{
  "description": "Synchronizes user identity, tags, extra data, and contextual data to the native bridge using string-safe payloads.",
  "cases": [
    {
      "input": {"scenario":"sync_user_identity","user":{"email":"hello@sentry.io","id":"3.1234587","unique":"123"}},
      "expected_output": "bridge_call=set_user\npayload={\"defaultUserKeys\":{\"email\":\"hello@sentry.io\",\"id\":\"3.1234587\"},\"otherUserKeys\":{\"unique\":\"123\"}}\n"
    },
    {
      "input": {"scenario":"sync_user_identity","user":{"id":"Hello"}},
      "expected_output": "bridge_call=set_user\npayload={\"defaultUserKeys\":{\"id\":\"Hello\"},\"otherUserKeys\":{}}\n"
    },
    {
      "input": {"scenario":"sync_tag","key":"key","value":"value"},
      "expected_output": "bridge_call=set_tag\npayload={\"key\":\"key\",\"value\":\"value\"}\n"
    },
    {
      "input": {"scenario":"sync_tag","key":"key","value":0},
      "expected_output": "bridge_call=set_tag\npayload={\"key\":\"key\",\"value\":\"0\"}\n"
    },
    {
      "input": {"scenario":"sync_tag","key":"key","value":{}},
      "expected_output": "bridge_call=set_tag\npayload={\"key\":\"key\",\"value\":\"{}\"}\n"
    },
    {
      "input": {"scenario":"sync_extra","key":"key","value":{"hello":"world"}},
      "expected_output": "bridge_call=set_extra\npayload={\"key\":\"key\",\"value\":\"{\\\"hello\\\":\\\"world\\\"}\"}\n"
    },
    {
      "input": {"scenario":"sync_context","platform":"ios","key":"key","value":{"hello":"world"}},
      "expected_output": "bridge_call=set_context\npayload={\"key\":\"key\",\"value\":{\"hello\":\"world\"}}\n"
    },
    {
      "input": {"scenario":"sync_context","platform":"ios","key":"key","value":null},
      "expected_output": "bridge_call=set_context\npayload={\"key\":\"key\",\"value\":null}\n"
    },
    {
      "input": {"scenario":"sync_context","platform":"android","key":"key","value":{"hello":"world"}},
      "expected_output": "bridge_call=set_extra\npayload={\"key\":\"key\",\"value\":\"{\\\"hello\\\":\\\"world\\\"}\"}\n"
    }
  ]
}
```

---

### Feature 6: Severity Normalization

**As a developer**, I want to normalize legacy severity names before they cross the native bridge, so I can avoid unsupported severity values while preserving valid ones.

**Expected Behavior / Usage:**

The input lists severity names. Legacy log is normalized to debug and legacy critical is normalized to fatal. Already-supported severity names are emitted unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature6_severity_normalization.json`

```json
{
  "description": "Normalizes deprecated severity names while preserving already-supported severity names.",
  "cases": [
    {
      "input": {"scenario":"normalize_severity_levels","levels":["log","critical"]},
      "expected_output": "input=log normalized=debug\ninput=critical normalized=fatal\n"
    },
    {
      "input": {"scenario":"normalize_severity_levels","levels":["debug","fatal","info","warning","error"]},
      "expected_output": "input=debug normalized=debug\ninput=fatal normalized=fatal\ninput=info normalized=info\ninput=warning normalized=warning\ninput=error normalized=error\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
