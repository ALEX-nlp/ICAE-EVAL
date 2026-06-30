## Product Requirement Document

# Application Metrics Collector — Aggregation, Validation, Lifecycle & Scrape Endpoint

## Project Goal

Build a pluggable metrics-collection component that gathers numeric runtime metrics contributed by other parts of an application, validates that the collection is well-formed, periodically samples each metric, and exposes the collected values over a single HTTP scrape endpoint — so operators can monitor a service without every subsystem having to wire up its own metrics plumbing.

---

## Background & Problem

A running service is composed of many subsystems, each of which can report numeric health/usage signals (queue depths, job counts, latencies, etc.). Without a shared collector, each subsystem has to invent its own way of registering, naming, sampling and exposing these signals, leading to duplicated plumbing, inconsistent naming, name clashes, and no single endpoint a monitoring system can scrape.

This component solves that by acting as a central collector. Other subsystems advertise themselves as *metric providers*: each provider can validate itself and, when asked, hand over a list of metrics. A metric has a unique name, an optional human-readable description, and a read function that returns its current numeric value. The collector aggregates metrics from all providers, enforces well-formedness rules, periodically samples every metric, and serves the latest values from one HTTP endpoint. The whole thing can be switched off with a single toggle, in which case it becomes inert (no gathering, no endpoint).

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

### Feature 1: Metric Aggregation During Provisioning

**As a developer**, I want the collector to gather metrics from all metric-provider subsystems when it starts up, so the whole application's metrics are assembled in one place with clear, staged failure reporting.

**Expected Behavior / Usage:**

Provisioning prepares the collector for use. A request carries a `namespace`, an optional `collect_interval`, a `disable_collect` toggle, and a list of `providers`. Each provider has an `id`, an optional `validate_error` (when present, the provider declares itself invalid), an optional `metrics_error` (when present, the provider fails to produce its metrics), and a list of `metrics` (each with a `name`, optional `description`, and a `has_read` flag stating whether it carries a read function).

When `disable_collect` is true, provisioning succeeds immediately without consulting any provider, and reports the collection mode as disabled. When collection is enabled, provisioning proceeds in two ordered stages: first every provider is initialized and self-validated, then every valid provider is asked for its metrics, which are aggregated. If any provider declares itself invalid, provisioning fails at the provider-validation stage. If a provider validates but then fails to produce its metrics, provisioning fails at the metrics-collection stage. When every provider validates and yields its metrics, provisioning succeeds with collection enabled. The result reports whether provisioning succeeded (`provisioned=true|false`); on success it also reports `collect=enabled|disabled`; on failure it reports a neutral `error` category naming the stage that failed (`provider_validation` or `metrics_collection`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_provisioning.json`

```json
{
    "description": "Provision the metrics-collection component. When collection is enabled, the component gathers metrics from every registered provider component before it can run; provisioning happens in two ordered stages. First each provider is initialized and self-validated; if any provider reports itself invalid, provisioning fails at the provider-validation stage. Then each valid provider is asked for its list of metrics; if any provider fails to produce its metrics, provisioning fails at the metrics-collection stage. When all providers validate and yield their metrics, provisioning succeeds with collection enabled. When collection is disabled, provisioning succeeds immediately without consulting any provider. The result reports whether provisioning succeeded, and on success the collection mode, and on failure a neutral category naming the stage that failed.",
    "cases": [
        {
            "input": {"operation": "provision", "namespace": "app", "providers": [{"id": "alpha", "metrics": [{"name": "jobs", "description": "Number of jobs.", "has_read": true}]}]},
            "expected_output": "provisioned=true[the exact line separator literal used in output formatting]collect=enabled[the exact line separator literal used in output formatting]"
        },
        {
            "input": {"operation": "provision", "namespace": "app", "providers": [{"id": "alpha", "validate_error": "boom", "metrics": []}]},
            "expected_output": "provisioned=false[the exact line separator literal used in output formatting]error=provider_validation[the exact line separator literal used in output formatting]"
        }
    ]
}
```

---

### Feature 2: Configuration Validation

**As a developer**, I want the collector to reject malformed metric configurations up front, so misconfigured metrics fail fast with a precise reason instead of producing a broken scrape endpoint.

**Expected Behavior / Usage:**

After provisioning, validation checks the assembled configuration. When collection is disabled, validation always passes. When collection is enabled, the following rules are checked in order and the first violated rule decides the outcome: (1) the `namespace` must not be empty; (2) every gathered metric must have a non-empty name; (3) every gathered metric must carry a read function (`has_read` true); (4) metric names must be unique across all gathered metrics. A passing configuration reports `valid=true`. A failing configuration reports `[a configuration sentinel that guards against empty namespaces]` together with a neutral `error` category identifying the broken rule: `namespace_empty`, `metric_name_empty`, `metric_read_missing`, or `metric_duplicate`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_validation.json`

```json
{
    "description": "Validate the configuration of the metrics-collection component after provisioning. When collection is disabled, validation always passes regardless of any other setting. When collection is enabled, the following rules are checked in order: the metrics namespace must not be empty; every gathered metric must have a non-empty name; every gathered metric must carry a read function that supplies its current value; and metric names must be unique across all gathered metrics. The first violated rule determines the outcome. A passing configuration reports validity; a failing one reports invalidity together with a neutral category identifying which rule was broken (empty namespace, empty metric name, missing read function, or duplicate metric name).",
    "cases": [
        {
            "input": {"operation": "validate", "namespace": "app", "providers": [{"id": "alpha", "metrics": [{"name": "jobs", "has_read": true}, {"name": "queue", "has_read": true}]}]},
            "expected_output": "valid=true[the exact line separator literal used in output formatting]"
        },
        {
            "input": {"operation": "validate", "namespace": "app", "providers": [{"id": "alpha", "metrics": [{"name": "jobs", "has_read": true}, {"name": "jobs", "has_read": true}]}]},
            "expected_output": "[a configuration sentinel that guards against empty namespaces][the exact line separator literal used in output formatting]error=metric_duplicate[the exact line separator literal used in output formatting]"
        }
    ]
}
```

---

### Feature 3: Lifecycle Control

**As a developer**, I want clear start/stop semantics and a status message reflecting the collection mode, so the host application can manage the collector's lifecycle and surface its state on startup.

**Expected Behavior / Usage:**

*3.1 Startup Message — the human-readable status the collector announces on startup.*

The startup message reflects the current collection mode. When collection is disabled, the collector announces that collecting is turned off. When collection is enabled, it announces that it is collecting metrics. The output is exactly the announcement text.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_startup_message.json`

```json
{
    "description": "Report the startup message of the metrics-collection component. The message reflects the current collection mode: when collection is disabled the component announces that collecting is turned off, and when collection is enabled it announces that it is collecting metrics. The output is exactly the announcement text.",
    "cases": [
        {
            "input": {"operation": "startup_message", "disable_collect": true, "namespace": "app"},
            "expected_output": "collect disabled[the exact line separator literal used in output formatting]"
        },
        {
            "input": {"operation": "startup_message", "namespace": "app"},
            "expected_output": "collecting metrics[the exact line separator literal used in output formatting]"
        }
    ]
}
```

*3.2 Start Collection — begin periodic sampling of the gathered metrics.*

Starting the collector after provisioning. When collection is disabled, starting is a no-op that succeeds immediately. When collection is enabled, the collector begins periodically sampling each gathered metric using the configured collection interval, and starting succeeds. The result reports whether the start succeeded (`started=true`) and the active collection mode (`collect=enabled|disabled`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_start_collection.json`

```json
{
    "description": "Start the metrics-collection component after provisioning. When collection is disabled, starting is a no-op that succeeds immediately. When collection is enabled, the component begins periodically sampling each gathered metric (using the configured collection interval) and starting succeeds. The result reports whether the start succeeded and the active collection mode.",
    "cases": [
        {
            "input": {"operation": "start", "disable_collect": true, "namespace": "app"},
            "expected_output": "started=true[the exact line separator literal used in output formatting]collect=disabled[the exact line separator literal used in output formatting]"
        },
        {
            "input": {"operation": "start", "namespace": "app", "collect_interval": "1s", "providers": [{"id": "alpha", "metrics": [{"name": "jobs", "has_read": true}]}]},
            "expected_output": "started=true[the exact line separator literal used in output formatting]collect=enabled[the exact line separator literal used in output formatting]"
        }
    ]
}
```

*3.3 Stop — tear the collector down.*

Stopping the collector always succeeds and requires no teardown work. The result simply reports that the collector stopped (`stopped=true`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_stop.json`

```json
{
    "description": "Stop the metrics-collection component. Stopping always succeeds and requires no teardown work; the result simply reports that the component stopped.",
    "cases": [
        {
            "input": {"operation": "stop", "namespace": "app"},
            "expected_output": "stopped=true[the exact line separator literal used in output formatting]"
        }
    ]
}
```

---

### Feature 4: HTTP Scrape Endpoint Exposure

**As a developer**, I want the collector to contribute its scrape endpoint to the application's HTTP router only when collection is active, so monitoring systems can pull metrics over HTTP without exposing a dead route when collection is off.

**Expected Behavior / Usage:**

The collector contributes HTTP routes to the host application. When collection is disabled, it contributes no routes. When collection is enabled, it contributes exactly one route: an HTTP `GET` endpoint at the path `/prometheus/metrics`. The route also carries a per-route logging switch; setting `disable_route_logging` to true turns logging off for that route. The result reports the number of contributed routes (`routes=<n>`) and, for each route, its HTTP `method`, `path`, and whether logging is disabled (`disable_logging=true|false`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_metrics_route.json`

```json
{
    "description": "Expose the HTTP route through which collected metrics are scraped. When collection is disabled, the component contributes no routes. When collection is enabled, it contributes exactly one route: an HTTP GET endpoint at the metrics path. The route also carries a per-route logging switch; enabling the route-logging-disabled setting turns logging off for that route. The result reports the number of contributed routes and, for each, its HTTP method, path, and whether logging is disabled.",
    "cases": [
        {
            "input": {"operation": "routes", "disable_collect": true, "namespace": "app"},
            "expected_output": "routes=0[the exact line separator literal used in output formatting]"
        },
        {
            "input": {"operation": "routes", "namespace": "app"},
            "expected_output": "routes=1[the exact line separator literal used in output formatting]method=GET [a specific route path and disable_logging flag combination for logging safety] [a specific route path and disable_logging flag combination for logging safety][the exact line separator literal used in output formatting]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic (metric aggregation, validation rules, lifecycle, route exposure) must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `operation` selects the behavior to exercise (`provision`, `validate`, `startup_message`, `start`, `stop`, `routes`); the remaining fields (`namespace`, `collect_interval`, `disable_collect`, `disable_route_logging`, `providers`) configure the collector and the metric-provider subsystems it gathers from. Native errors raised by the core must be translated by the adapter into the neutral `error=<category>` lines specified above; the scrape endpoint is an HTTP `GET` at `/prometheus/metrics`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- provider declares metrics_error
- method=1s
