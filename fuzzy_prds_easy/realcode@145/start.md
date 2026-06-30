## Product Requirement Document

# Persistent HTTP Worker Runtime - Long-Lived Application Server Integration Layer

## Project Goal

Build a runtime integration layer that lets a traditional request/response web application run as a long-lived, multi-request worker process instead of being booted fresh on every request. The layer keeps the application alive between requests for speed, while transparently handling the cross-request hazards that a persistent process introduces: lifecycle signalling, controlled process recycling, stale resource cleanup, per-request state isolation, service discovery at boot time, and metric declaration. Developers get the performance of a resident process without having to manually reason about what state survives between requests.

---

## Background & Problem

In the classic execution model, a web application is rebuilt from scratch for every incoming request: configuration is parsed, services are wired, connections are opened, the request is served, and then everything is torn down. This is simple and leak-proof, but slow, because all of that setup cost is paid on every single request.

Running the application as a persistent worker that handles many requests in a loop removes that repeated setup cost, but it shifts the burden onto the developer. State that used to be discarded after each request now survives: database connections go stale, error-reporting context bleeds from one request into the next, and an application that has entered an unrecoverable internal state stays broken for every subsequent request the worker serves. Without a coordinating layer, developers must hand-write fragile cleanup code and process-recycling heuristics, which is repetitive and error-prone.

With this runtime layer, the worker loop, the recycling policy, the resource-recycling hooks, and the per-request isolation are all handled for you. You write ordinary request handlers; the layer decides when to reuse the warm process and when to rebuild it, cleans up shared resources between requests, isolates per-request context, and emits the lifecycle and metric signals an operator needs.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This project spans several distinct responsibilities (a request loop, recycling policies, per-request middleware, boot-time discovery, metric declaration), so it MUST be organized as a multi-file, multi-module repository with clear separation between the core domain and the execution/test adapter. Do not collapse it into a single god-file, and do not over-engineer the smaller leaf components.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a black-box contract for the execution adapter, NOT the internal data model. The core logic (worker loop, policies, middleware) must be fully decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating JSON scenarios into idiomatic calls against the core and rendering the neutral stdout contract.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep the request loop, each recycling policy, each middleware, the discovery pass, and the output formatter as distinct units.
   - **Open/Closed Principle (OCP):** New recycling policies and new middleware must be addable without modifying the worker loop.
   - **Liskov Substitution Principle (LSP):** Every recycling policy must be substitutable wherever the policy abstraction is expected; an aggregate policy is itself a policy.
   - **Interface Segregation Principle (ISP):** The policy abstraction and the middleware abstraction must be small and cohesive.
   - **Dependency Inversion Principle (DIP):** The worker loop must depend on policy/middleware abstractions, not concrete implementations or I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface (a handler that yields a response and may defer trailing work; a middleware that wraps the next handler) must be elegant and idiomatic to the target language.
   - **Resilience:** A failure in a request handler must be contained: the client still receives a well-formed error response, the worker shuts down cleanly, and the failure never silently corrupts the next request. Errors must be modeled explicitly, not via generic faults.

---

## Core Features

### Feature 1: Process Recycling Policy

**As a developer**, I want the worker to decide automatically whether to keep the warm process or rebuild it after each request, so I can run a persistent server without it getting stuck in a broken state or accumulating unsafe leftover state.

**Expected Behavior / Usage:**

A recycling policy answers one question per request: should the worker rebuild the application before serving the next request? Multiple independent policies can be combined, and a dedicated policy reacts to errors observed while serving a request.

*1.1 Aggregate Recycling Vote — combine several independent policies into one*

An aggregate policy holds zero or more member policies and recycles if and only if at least one member votes to recycle (logical OR). With no members it never recycles. The vote is reported as a single decision line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_chain_reboot.json`

```json
{
    "description": "Combine several independent reboot voters into one aggregate decision. The aggregate votes to recycle the worker if and only if at least one member votes yes; an empty set never recycles. Input lists each member's vote (true=wants recycle); output reports the aggregate decision.",
    "cases": [
        {"input": {"handler": "reboot", "op": "reboot_chain", "strategies": []}, "expected_output": "should_reboot=false\n"},
        {"input": {"handler": "reboot", "op": "reboot_chain", "strategies": [true, false]}, "expected_output": "should_reboot=true\n"},
        {"input": {"handler": "reboot", "op": "reboot_chain", "strategies": [false, true]}, "expected_output": "should_reboot=true\n"},
        {"input": {"handler": "reboot", "op": "reboot_chain", "strategies": [false, false]}, "expected_output": "should_reboot=false\n"}
    ]
}
```

*1.2 Error-Driven Recycling Policy — a policy that reacts to per-request signals*

This policy starts each request abstaining (no recycle). It watches signals seen while serving the request and then reports a decision. It also supports an explicit force-recycle signal and a reset operation.

*1.2.1 Error categories and the allow-list*

If an unexpected error is seen during the request, the policy votes to recycle (the worker may be in a tainted state). If the error's category is on a configured allow-list, it does not recycle. Allow-list membership is by category hierarchy: an error whose category is a sub-type of an allowed category is also tolerated. Input is the allow-list and the ordered signals seen during the request; output is the decision.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_1_on_exception_reboot.json`

```json
{
    "description": "A reboot voter that decides per-request whether the worker must recycle based on errors seen while handling the request. A fresh voter abstains. Any unexpected error makes it vote to recycle; an error whose category is on the allow-list (including categories that are sub-types of an allowed category) does not. Input is the allow-list of tolerated error categories plus an ordered list of signals observed during the request; output reports the final decision.",
    "cases": [
        {"input": {"handler": "reboot", "op": "on_exception", "allowed": ["app"], "actions": []}, "expected_output": "should_reboot=false\n"},
        {"input": {"handler": "reboot", "op": "on_exception", "allowed": ["app"], "actions": [{"type": "exception", "category": "runtime"}]}, "expected_output": "should_reboot=true\n"},
        {"input": {"handler": "reboot", "op": "on_exception", "allowed": ["app"], "actions": [{"type": "exception", "category": "app"}]}, "expected_output": "should_reboot=false\n"},
        {"input": {"handler": "reboot", "op": "on_exception", "allowed": ["app"], "actions": [{"type": "exception", "category": "app_child"}]}, "expected_output": "should_reboot=false\n"}
    ]
}
```

*1.2.2 Forced recycle and per-request reset*

The policy can be told to recycle explicitly via a force signal carrying a human-readable reason; when forced it both surfaces the reason and votes to recycle. A reset operation clears any error or force signal accumulated during the request, returning the policy to abstain. Input is the ordered signals (errors, force-with-reason, reset); output reports any forced reason followed by the decision.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_2_force_reboot_and_clear.json`

```json
{
    "description": "The same per-request reboot voter can also be told to recycle explicitly via a force-reboot signal carrying a human-readable reason, and its per-request state can be reset. When forced, the voter both records the reason (emitted as a dedicated field) and votes to recycle. Resetting the voter clears any previously observed error or force signal, returning it to abstain. Input is the ordered list of signals (errors, force-with-reason, reset); output reports any forced reason followed by the final decision.",
    "cases": [
        {"input": {"handler": "reboot", "op": "on_exception", "allowed": ["app"], "actions": [{"type": "force", "reason": "something bad happened"}]}, "expected_output": "forced_reboot_reason=something bad happened\nshould_reboot=true\n"},
        {"input": {"handler": "reboot", "op": "on_exception", "allowed": ["app"], "actions": [{"type": "exception", "category": "runtime"}, {"type": "clear"}]}, "expected_output": "should_reboot=false\n"},
        {"input": {"handler": "reboot", "op": "on_exception", "allowed": ["app"], "actions": [{"type": "force", "reason": "manual recycle"}, {"type": "clear"}]}, "expected_output": "should_reboot=false\n"}
    ]
}
```

---

### Feature 2: Persistent Request Worker Loop

**As a developer**, I want a worker that serves queued requests one after another in a warm process, signals its lifecycle, sends responses, contains handler failures, and recycles the application when the policy says so, so I get a fast resident server with safe behavior.

**Expected Behavior / Usage:**

The worker pulls requests from a queue and serves each by invoking the application handler. It surfaces lifecycle and request outcomes as observable signals.

*2.1 Trusted-proxy resolution at request time*

The worker can be configured with a trusted-proxy list and a trusted-header bitmask so forwarded client information is honored only from trusted peers. A special token meaning "the immediate peer address" is resolved at request time to the actual remote address of the incoming connection. Input is the configured proxy list (possibly containing that token), the header bitmask, and the peer address; output is the effective resolved proxy list and the active trusted-header set.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_trusted_proxies.json`

```json
{
    "description": "On startup the worker can be configured with a trusted-proxy list so client IP / forwarded headers are honored only from those proxies. The special token meaning 'the immediate peer address' is resolved at request time to the actual remote address of the incoming connection. Input provides the configured proxy list (which may include that special token), the trusted-header bitmask, and the peer address of an incoming request; output reports the effective resolved proxy list and the active trusted-header set.",
    "cases": [
        {"input": {"handler": "worker", "op": "worker_trusted_proxies", "requests": 1, "responder": "ok", "trusted_proxies": "10.0.0.1,REMOTE_ADDR", "trusted_headers": 1, "remote_addr": "10.0.0.2"}, "expected_output": "trusted_proxies=10.0.0.1,10.0.0.2\ntrusted_header_set=1\n"},
        {"input": {"handler": "worker", "op": "worker_trusted_proxies", "requests": 1, "responder": "ok", "trusted_proxies": "192.168.0.1,REMOTE_ADDR", "trusted_headers": 1, "remote_addr": "203.0.113.7"}, "expected_output": "trusted_proxies=192.168.0.1,203.0.113.7\ntrusted_header_set=1\n"}
    ]
}
```

*2.2 Lifecycle events*

The worker emits a start event before it begins accepting requests and a stop event once the request loop ends. Even with an empty queue it announces start then stop, in that order. Input is the queued-request count; output is the ordered list of lifecycle events.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_lifecycle_events.json`

```json
{
    "description": "The worker emits lifecycle events as it runs: a start event before it begins accepting requests and a stop event once the request loop ends. With no requests queued, the worker still announces start then stop. Input is the number of queued requests (here none); output is the ordered list of lifecycle events emitted.",
    "cases": [
        {"input": {"handler": "worker", "op": "worker_events", "requests": 0, "responder": "none"}, "expected_output": "event=worker_start\nevent=worker_stop\n"}
    ]
}
```

*2.3 Serving a request with deferred trailing work*

For each request the worker invokes the handler, sends the produced response to the client, and only then runs any trailing work the handler deferred until after the response was sent. Input is a queued request whose handler yields a body and then performs deferred work; output reports lifecycle events, the number of responses sent, the first response body, and whether the deferred work executed.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_handle_request.json`

```json
{
    "description": "For each queued request the worker invokes the application handler and sends the produced response to the client. The handler may continue doing deferred work after the response has been sent (the response is dispatched before that trailing work runs). Input is a queued request whose handler yields a body and then performs deferred work; output reports the lifecycle events, the number of responses sent, the first response body, and whether the deferred work executed.",
    "cases": [
        {"input": {"handler": "worker", "op": "worker_handle", "requests": 1, "responder": "ok"}, "expected_output": "event=worker_start\nevent=worker_stop\nresponses=1\nfirst_response_content=hello\ndeferred_work_ran=true\n"}
    ]
}
```

*2.4 Failure containment*

If a handler throws, the worker sends a generic 500 error response, stops the underlying worker, and ends the loop without serving further queued requests. In non-debug mode the original error message is suppressed from the response body; in debug mode it is included to aid debugging. Input queues two requests against a throwing handler plus a debug flag and the thrown message; output reports the response status, whether the thrown message leaked into the body, whether the worker stopped, and the lifecycle events.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_error_stops_worker.json`

```json
{
    "description": "If the application handler throws while processing a request, the worker sends a generic 500 error response to the client, stops the underlying worker, and ends the request loop (it does not proceed to the next queued request). In non-debug mode the original exception message is hidden from the response body; in debug mode the message is included to aid debugging. Input queues two requests against a throwing handler, with a debug flag and the thrown message; output reports the response status, whether the thrown message leaked into the body, whether the worker was stopped, and the lifecycle events.",
    "cases": [
        {"input": {"handler": "worker", "op": "worker_error", "requests": 2, "responder": "throw", "message": "internal failure detail", "debug": false}, "expected_output": "response_status=500\nerror_message_in_body=false\nworker_stopped=true\nevent=worker_start\nevent=worker_stop\n"},
        {"input": {"handler": "worker", "op": "worker_error", "requests": 2, "responder": "throw", "message": "internal failure detail", "debug": true}, "expected_output": "response_status=500\nerror_message_in_body=true\nworker_stopped=true\nevent=worker_start\nevent=worker_stop\n"}
    ]
}
```

*2.5 Applying the recycling decision*

After each request the worker consults its recycling policy. If the policy abstains, warm application state is preserved and no rebuild occurs. If the policy votes to recycle, the worker rebuilds the application state and emits a rebuilt event before continuing. Input is one queued request plus the per-request votes; output reports how many rebuilds occurred and the ordered lifecycle events.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_reboot_after_request.json`

```json
{
    "description": "After each handled request the worker consults its reboot voter. If the voter abstains, the application state is preserved across requests and no rebuild happens. If the voter votes to recycle, the worker rebuilds the application state and emits a kernel-rebooted event before continuing. Input is one queued request plus the per-request reboot votes; output reports how many rebuilds occurred and the ordered lifecycle events.",
    "cases": [
        {"input": {"handler": "worker", "op": "worker_reboot", "requests": 1, "responder": "ok", "reboot_per_call": [false]}, "expected_output": "reboots=0\nevent=worker_start\nevent=worker_stop\n"},
        {"input": {"handler": "worker", "op": "worker_reboot", "requests": 1, "responder": "ok", "reboot_per_call": [true]}, "expected_output": "reboots=1\nevent=worker_start\nevent=kernel_rebooted\nevent=worker_stop\n"}
    ]
}
```

---

### Feature 3: Metric Collector Declaration

**As a developer**, I want to declare named metric collectors at worker startup, so my monitoring backend knows about my gauges, counters, and histograms from the moment the process comes up.

**Expected Behavior / Usage:**

At startup each configured collector definition is declared to the metrics backend. A definition has a type — gauge, counter, or histogram — plus optional namespace, subsystem, help text, label names, and (for histograms) bucket boundaries. The declaration preserves exactly the supplied fields and leaves the rest empty. An unrecognized type is rejected as a neutral error naming the offending type rather than being declared.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_declare_metrics.json`

```json
{
    "description": "At worker startup, configured metric collector definitions are declared to the metrics backend. Each definition has a type (gauge, counter, or histogram) plus optional namespace, subsystem, help text, label names, and (for histograms) bucket boundaries. The declaration preserves exactly the fields supplied, leaving the rest empty. Input is a map of collector name to its definition; output lists each declared collector with its resolved type, namespace, subsystem, help, labels, and buckets.",
    "cases": [
        {"input": {"handler": "metrics", "collectors": {"gauge": {"type": "gauge", "labels": ["hello"]}, "counter": {"type": "counter", "namespace": "foo", "help": "count something"}, "histo": {"type": "histogram", "buckets": [0.1, 0.5, 1], "subsystem": "bar"}}}, "expected_output": "metric=gauge\ntype=gauge\nnamespace=\nsubsystem=\nhelp=\nlabels=hello\nbuckets=\nmetric=counter\ntype=counter\nnamespace=foo\nsubsystem=\nhelp=count something\nlabels=\nbuckets=\nmetric=histo\ntype=histogram\nnamespace=\nsubsystem=bar\nhelp=\nlabels=\nbuckets=0.1,0.5,1\n"}
    ]
}
```

---

### Feature 4: Service-Contract Discovery & Registration

**As a developer**, I want tagged services to be automatically wired against the remote-call contracts they implement during application build, so I don't have to register each service-to-contract mapping by hand.

**Expected Behavior / Usage:**

When the application is assembled, every service marked as a remote-call service is scanned. For each such service, the system finds every service-contract interface it implements and registers the service once per contract. A service implementing a single contract registers once; a service implementing several contracts registers once per contract, in discovery order; any plain (non-contract) interface the service also implements is ignored. The output is a list of (service id, contract) registrations.

**Test Cases:** `rcb_tests/public_test_cases/feature4_grpc_service_registration.json`

```json
{
    "description": "During container build, services tagged as gRPC services are scanned and registered against every service-contract interface they implement. A service implementing one contract registers once; a service implementing several contracts registers once per contract; any non-contract interface it also implements is ignored. Input is the list of tagged services, each with an id and which contract-implementation shape it has; output lists each registration as a (service id, contract alias) pair in discovery order.",
    "cases": [
        {"input": {"handler": "grpc", "services": [{"id": "simple", "kind": "single"}, {"id": "multiple", "kind": "multi"}]}, "expected_output": "register service=simple interface=grpc_single\nregister service=multiple interface=grpc_foo\nregister service=multiple interface=grpc_bar\n"}
    ]
}
```

---

### Feature 5: Stale Database Resource Recycling

**As a developer**, I want the layer to clean up database connections and entity managers between requests in a long-lived worker, so a dead socket or an unusable manager from one request never breaks the next one.

**Expected Behavior / Usage:**

A per-request middleware brackets request handling: it recycles stale connections before the request and inspects managers after the request.

*5.1 Pre-request connection liveness recycling*

Before handling a request, the middleware inspects each connection that has actually been initialized and currently reports as connected. For those it issues a lightweight liveness probe; if the probe fails it closes the connection so a fresh one is opened on next use. Connections that were never initialized, or that report disconnected, are skipped entirely (no probe). Healthy connections are left open. Input describes whether the connection was initialized, whether it reports connected, and whether the probe succeeds; output reports whether a probe was attempted and whether the connection was closed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_connection_recycling.json`

```json
{
    "description": "Before handling a request, the middleware recycles stale database connections so a long-lived worker never reuses a dead socket. It only inspects connections that have actually been initialized and are currently connected; for those it issues a lightweight liveness probe and closes the connection if the probe fails, leaving healthy connections untouched. Input describes whether the connection service was initialized, whether it reports connected, and whether the liveness probe succeeds; output reports whether a probe was attempted and whether the connection was closed.",
    "cases": [
        {"input": {"handler": "doctrine", "connection_present": false, "connected": false, "manager": "none"}, "expected_output": "ping_attempted=false\nconnection_closed=false\nreboot_forced=false\n"},
        {"input": {"handler": "doctrine", "connection_present": true, "connected": false, "manager": "none"}, "expected_output": "ping_attempted=false\nconnection_closed=false\nreboot_forced=false\n"},
        {"input": {"handler": "doctrine", "connection_present": true, "connected": true, "pingable": false, "manager": "none"}, "expected_output": "ping_attempted=true\nconnection_closed=true\nreboot_forced=false\n"},
        {"input": {"handler": "doctrine", "connection_present": true, "connected": true, "pingable": true, "manager": "none"}, "expected_output": "ping_attempted=true\nconnection_closed=false\nreboot_forced=false\n"}
    ]
}
```

*5.2 Post-request manager-state handling*

After handling a request, the middleware inspects each initialized entity manager. A closed (unusable) manager cannot be reopened in place, so the middleware forces a full application rebuild before the next request. A manager that is a lazy proxy is skipped, because the framework reopens it automatically on next access. A healthy open manager needs no action. Input describes the manager's state (closed, lazy proxy, or open); output reports whether an application rebuild was forced.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_manager_reset.json`

```json
{
    "description": "After handling a request, the same middleware inspects each initialized entity manager. A closed (unusable) manager cannot be reopened in-place, so the middleware forces a full application rebuild for the next request. A manager that is a lazy proxy is skipped (the framework reopens it automatically), and a healthy open manager needs no action. Input describes the entity manager's state (closed, lazy proxy, or open); output reports whether an application rebuild was forced.",
    "cases": [
        {"input": {"handler": "doctrine", "connection_present": true, "connected": false, "manager": "closed"}, "expected_output": "ping_attempted=false\nconnection_closed=false\nreboot_forced=true\n"},
        {"input": {"handler": "doctrine", "connection_present": true, "connected": false, "manager": "lazy"}, "expected_output": "ping_attempted=false\nconnection_closed=false\nreboot_forced=false\n"},
        {"input": {"handler": "doctrine", "connection_present": true, "connected": false, "manager": "open"}, "expected_output": "ping_attempted=false\nconnection_closed=false\nreboot_forced=false\n"}
    ]
}
```

---

### Feature 6: Per-Request Error-Reporting Scope Isolation

**As a developer**, I want the error-reporting context to be isolated per request in a long-lived worker, so debugging context recorded for one request never leaks onto an error reported by a later request.

**Expected Behavior / Usage:**

A per-request middleware opens a fresh reporting scope around each request and tears it down afterward. Context attached during one request (such as a breadcrumb) lives only in that request's scope and must not appear on an error event captured during a subsequent request. Input is a sequence of requests, each flagged for whether it attaches a breadcrumb before capturing an error; output reports the number of breadcrumbs on the error event captured by the final request — which must be zero when the breadcrumb was attached only during an earlier request.

**Test Cases:** `rcb_tests/public_test_cases/feature6_error_scope_isolation.json`

```json
{
    "description": "The error-reporting middleware isolates each request's reporting scope so context recorded during one request never leaks into a later one. A breadcrumb added while handling the first request must not appear on the error event captured during the second request. Input is a sequence of requests, each flagged for whether it adds a breadcrumb before capturing an error; output reports the number of breadcrumbs attached to the error event captured by the final request.",
    "cases": [
        {"input": {"handler": "sentry", "requests": [{"add_breadcrumb": true}, {"add_breadcrumb": false}]}, "expected_output": "last_event_breadcrumbs=0\n"}
    ]
}
```

---

### Feature 7: Debug-Dump Rerouting Under the HTTP Runtime

**As a developer**, I want debug dumps to be captured by the request profiler instead of being printed to the process output when running under the HTTP runtime, so dumped values show up in my debugging tools rather than corrupting the worker's output stream.

**Expected Behavior / Usage:**

When the worker starts under the HTTP runtime, the global debug-dump facility is rerouted to a worker-provided dumper, so any dumped value is captured for the request profiler rather than written to the process output stream. Input is the runtime mode and a value to dump; output reports whether the dump facility was rerouted and the captured value.

**Test Cases:** `rcb_tests/public_test_cases/feature7_dump_handler_redirect.json`

```json
{
    "description": "When the worker starts under the HTTP runtime, the global debug-dump facility is rerouted to the worker-provided dumper so dumped values are captured by the request profiler instead of being written to the process output. Input is the runtime mode and a value to dump; output reports whether the dump facility was rerouted and the captured value.",
    "cases": [
        {"input": {"handler": "vardumper", "mode": "http", "value": "foo"}, "expected_output": "handler_redirected=true\ndumped_value=foo\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the worker loop, the recycling policies, the per-request middleware, the boot-time discovery pass, and the metric declaration, with the core domain decoupled from I/O and following the SOLID principles and organization constraints above.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a JSON scenario from stdin, routes it to the matching core logic, invokes that logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. The adapter is responsible for normalizing any internal fault into a neutral `error=<category>` contract line and must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_chain_reboot.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_chain_reboot@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains only the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- match the shutdown behavior pattern defined in C012
- apply the legacy mode fallback logic from the diagnostics module
