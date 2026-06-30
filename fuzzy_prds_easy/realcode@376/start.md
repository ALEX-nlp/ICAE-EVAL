## Product Requirement Document

# Mobile Telemetry Runtime Support - Session, Buffering, Persistence, and Enrichment Contracts

## Project Goal

Build a mobile telemetry runtime support library that allows developers to attach session context, enrich telemetry records, buffer signals until exporters become available, persist retryable signal batches, and schedule lightweight background work without duplicating fragile lifecycle and storage logic.

---

## Background & Problem

Without this library, developers are forced to manually track application foreground/background transitions, rotate session identifiers, attach contextual attributes to every telemetry item, coordinate delayed exporter setup, and manage temporary disk storage. This leads to repetitive code, missed edge cases around timeouts and retries, inconsistent telemetry metadata, and maintenance issues across application modules.

With this library, telemetry clients get a consistent runtime layer for session lifecycle decisions, signal buffering, disk export retries, storage directory management, periodic retry execution, log enrichment, and slow-rendering polling configuration.

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

### Feature 1: Session Timeout Evaluation

**As a developer**, I want session timeout decisions to respect app lifecycle state and activity bumps, so I can rotate telemetry sessions only when inactivity rules require it.

**Expected Behavior / Usage:**

The input provides a timeout duration in milliseconds and a sequence of lifecycle/time operations. `background` places the app in background timeout mode, `foreground` marks the next activity as the first foreground activity after backgrounding, `advance` moves the clock forward by the given milliseconds, `bump` records telemetry activity and resets the timeout counter, and `check` emits one line. While already foregrounded, checks must not time out regardless of elapsed time. While backgrounded, a check must time out once elapsed time since the latest bump reaches the configured timeout. After returning to foreground, the first activity check still observes the background timeout window; a following bump returns the app to normal foreground behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature1_session_timeout.json`

```json
{
  "description": "Evaluate whether a mobile telemetry session has timed out after lifecycle changes, activity bumps, and elapsed time advances.",
  "cases": [
    {
      "input": {"timeout_ms": 900000, "events": [{"op": "background"}, {"op": "bump"}, {"op": "advance", "ms": 900000}, {"op": "check"}, {"op": "bump"}, {"op": "check"}]},
      "expected_output": "timed_out=true\ntimed_out=false\n"
    }
  ]
}
```

---

### Feature 2: Session Identifier Stability and Rotation

**As a developer**, I want session identifiers to be stable during an active session and rotate after lifetime or timeout expiration, so telemetry can be grouped into correct user sessions.

**Expected Behavior / Usage:**

The input provides a maximum session lifetime, an ordered sequence of timeout responses, and `get`/`advance` events. Each `get` emits the request index, whether the returned identifier is a 32-character lowercase hexadecimal value, and whether it is new, the same as the previous request, or changed from the previous request. The first request creates a valid identifier. Repeated requests before expiration reuse the identifier. A request at or beyond the configured lifetime, or a request for which the timeout source reports expiration, rotates to a different valid identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature2_session_identity.json`

```json
{
  "description": "Request telemetry session identifiers over time and report whether identifiers are well formed and whether each request reused or rotated the active identifier.",
  "cases": [
    {
      "input": {"lifetime_ms": 14400000, "timeout_sequence": [false, false], "events": [{"op": "get"}, {"op": "get"}, {"op": "advance", "ms": 14400000}, {"op": "get"}]},
      "expected_output": "session_index=0\nformat=hex32\nrelation=new\nsession_index=1\nformat=hex32\nrelation=same\nsession_index=2\nformat=hex32\nrelation=changed\n"
    }
  ]
}
```

---

### Feature 3: In-Memory Signal Buffering Before Exporter Attachment

**As a developer**, I want telemetry exports, flushes, and shutdowns issued before the real exporter is attached to be buffered and completed later, so startup telemetry is not lost during delayed exporter initialization.

**Expected Behavior / Usage:**

The input selects a signal type (`span` or `log`), a buffer capacity, and ordered operations. `export` before delegate attachment stores items up to capacity and returns a pending result if at least one item was accepted; if the buffer is already full, the extra export returns `error:buffer_overflow` and the new items are not delivered. `flush` and `shutdown` before delegate attachment return pending results and are invoked once the delegate is attached. After `set_delegate`, buffered items are exported in a single delegate export call and pending flush/shutdown calls are forwarded. Operations after delegate attachment return success immediately and are sent directly to the delegate. Output reports every operation result plus delegate-observable item delivery and call counts.

**Test Cases:** `rcb_tests/public_test_cases/feature3_buffering_exporter.json`

```json
{
  "description": "Apply export, flush, shutdown, and delegate-attachment operations to an in-memory telemetry exporter and report buffered item delivery plus operation result states.",
  "cases": [
    {
      "input": {"signal": "span", "capacity": 2, "operations": [{"op": "export", "items": ["first", "second"]}, {"op": "export", "items": ["third"]}, {"op": "flush"}, {"op": "set_delegate"}]},
      "expected_output": "export_result=0:pending\nexport_result=1:error:buffer_overflow\nflush_result=2:pending\ndelegate_items=first,second\ndelegate_exports=1\ndelegate_flushes=1\ndelegate_shutdowns=0\n"
    }
  ]
}
```

---

### Feature 4: Stored Signal Batch Export Coordination

**As a developer**, I want stored span, metric, and log batches to be exported with a consistent timeout and combined success signal, so retry loops can continue only while useful work is being drained.

**Expected Behavior / Usage:**

The input declares which stored-signal exporters are available, the boolean result sequence each exporter should return, an optional timeout in milliseconds, and an operation: `spans`, `metrics`, `logs`, or `each`. Single-signal operations call only the requested available exporter and return its boolean result; if that exporter is unavailable, they return false and make no calls. The `each` operation attempts all three signal kinds in span, metric, and log order and returns true if any one of the available exports succeeds. Every actual exporter call receives the configured timeout, or 5000 milliseconds when no timeout is provided. Output reports the combined exported result, call counts, and timeout values for called exporters.

**Test Cases:** `rcb_tests/public_test_cases/feature4_disk_export_batches.json`

```json
{
  "description": "Attempt to export one stored batch for spans, metrics, and logs with configured exporter availability, exporter outcomes, and export timeout.",
  "cases": [
    {
      "input": {"availability": {"spans": true, "metrics": true, "logs": true}, "results": {"spans": [false], "metrics": [true], "logs": [false]}, "operation": "each"},
      "expected_output": "exported=true\nspans_calls=1\nspans_timeout_ms=5000\nmetrics_calls=1\nmetrics_timeout_ms=5000\nlogs_calls=1\nlogs_timeout_ms=5000\n"
    }
  ]
}
```

---

### Feature 5: Disk Persistence Directories and Size Limits

**As a developer**, I want telemetry persistence paths and size limits to be resolved consistently, so signal buffering uses predictable directories and safe temporary workspace cleanup.

**Expected Behavior / Usage:**

The input provides an application cache directory and an operation. For `signals_dir`, the system returns a custom signal directory when one is supplied; otherwise it returns `<cache_dir>/opentelemetry/signals`, creating the directory if needed. For `temporary_dir`, the system returns `<cache_dir>/opentelemetry/temp`, creates it if needed, and removes all preexisting files and nested files before returning it. For `max_file_size`, the configured maximum file size is returned unchanged. For `max_folder_size`, the per-signal folder quota is the configured total cache size divided by three using integer division. Output reports paths relative to the test root, existence, remaining entry count, or computed size.

**Test Cases:** `rcb_tests/public_test_cases/feature5_disk_storage_paths.json`

```json
{
  "description": "Resolve disk storage directories and cache sizing for telemetry persistence, including default paths, custom signal paths, temporary-directory cleanup, and per-signal folder quotas.",
  "cases": [
    {
      "input": {"cache_dir": "cache", "operation": "temporary_dir", "preexisting": ["old.tmp", "nested/old.tmp"]},
      "expected_output": "path=cache/opentelemetry/temp\nexists=true\nentries=0\n"
    }
  ]
}
```

---

### Feature 6: Periodic Runnable Delay and Rescheduling

**As a developer**, I want reusable periodic work to honor a minimum delay and stop policy, so background retry tasks do not run too frequently and can stop rescheduling themselves.

**Expected Behavior / Usage:**

The input provides a minimum delay and a sequence of run attempts. Before each attempt, the clock advances by `advance_ms`, and `stop_after_run` controls whether the task should stop after an actual execution. The first attempt is eligible immediately. Later attempts execute only when the current time is at least the previous execution time plus the minimum delay. After each attempt, the task enqueues itself for another loop unless its stop policy is true after execution. Output reports the attempt index, total number of actual executions so far, and total enqueue requests so far.

**Test Cases:** `rcb_tests/public_test_cases/feature6_periodic_work.json`

```json
{
  "description": "Run a reusable periodic task with a minimum delay and stop policy, then report execution count and whether the task scheduled itself for another loop.",
  "cases": [
    {
      "input": {"minimum_delay_ms": 5000, "runs": [{"advance_ms": 0, "stop_after_run": false}, {"advance_ms": 4999, "stop_after_run": false}, {"advance_ms": 1, "stop_after_run": true}]},
      "expected_output": "run_index=0\ntimes_run=1\nenqueued=1\nrun_index=1\ntimes_run=1\nenqueued=2\nrun_index=2\ntimes_run=2\nenqueued=2\n"
    }
  ]
}
```

---

### Feature 7: Log Record Attribute Enrichment

**As a developer**, I want log records to be enriched with session, screen, or global attributes at emit time, so downstream telemetry has consistent contextual metadata.

**Expected Behavior / Usage:**

The input selects an enrichment processor. `session` reads the current session identifier from the supplied provider and attaches it as `session.id`. `screen` reads the current visible screen name and attaches it as `screen.name`. `global` accepts one or more supplied attribute sets and emits one log record per set; each emit must use the supplier's current attributes rather than caching an earlier value. Output reports the attached attribute key/value pair or, for global enrichment, each emit index and the complete attached attribute set in key-sorted `key=value` form.

**Test Cases:** `rcb_tests/public_test_cases/feature7_log_enrichment.json`

```json
{
  "description": "Emit log records through enrichment processors and report the telemetry attributes attached from session identity, current screen name, or a supplied global attribute set.",
  "cases": [
    {
      "input": {"processor": "global", "attribute_sets": [{"service.name": "checkout"}, {"device.model": "tablet"}]},
      "expected_output": "emit_index=0\nattributes=service.name=checkout\nemit_index=1\nattributes=device.model=tablet\n"
    }
  ]
}
```

---

### Feature 8: Slow-Rendering Poll Interval Configuration

**As a developer**, I want slow-rendering detection to expose a positive polling interval setting, so frame monitoring can be tuned without accepting invalid intervals.

**Expected Behavior / Usage:**

The input provides an ordered list of interval updates in milliseconds. The default interval is 1000 milliseconds. A positive update replaces the current interval. A zero or negative update is rejected and leaves the current interval unchanged. Output reports the retained interval after all updates.

**Test Cases:** `rcb_tests/public_test_cases/feature8_slow_rendering_config.json`

```json
{
  "description": "Configure the polling interval for slow-rendering detection and report the interval retained after each update attempt.",
  "cases": [
    {
      "input": {"updates_ms": [3000, -1000]},
      "expected_output": "interval_ms=3000\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- when  θερπογραμματοratio indicates activity
- for emit_index logic
