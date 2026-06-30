## Product Requirement Document

# Replica Read-Routing Library - Send Database Reads to Replicas Safely

## Project Goal

Build a read-routing library for applications backed by a primary/replica database topology that lets developers send selected read queries to a replica node instead of the primary, with explicit, predictable rules for when a replica is used, when execution falls back to the primary, and when an error is raised. The library wraps a unit of work in a *distribution scope*; reads issued inside that scope are eligible for the replica while writes and transactional work continue to target the primary.

---

## Background & Problem

Without this library, every database read hits the primary node, even though most reads are perfectly happy to be served slightly-stale data from a replica. Developers who try to route reads manually must thread connection-selection logic through every query, reason about replication lag by hand, and remember to send writes and transactions back to the primary. This leads to error-prone boilerplate, accidental stale reads after a write, and primary nodes overloaded by traffic that could have been offloaded.

With this library, a developer wraps a block of work in a distribution scope and the routing happens automatically: reads in the scope go to a replica, writes and transactions stay on the primary, and configurable guards decide what happens when the replica is lagging or unavailable. A global mode can flip the default so that reads are distributed everywhere unless explicitly pinned back to the primary.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This system has several distinct responsibilities (scope/context state management, pool selection, lag measurement, failover policy, background-job integration, logging). It MUST NOT be a single "god file"; lay it out as a clear multi-file tree (core domain modules plus a separate execution/test adapter). Do not over-engineer, but do not collapse genuinely separate concerns either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter only**, not the internal data model. The core routing logic must be completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON scenarios into idiomatic calls to the core domain and rendering results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Separate scenario parsing, scope/context management, pool selection, lag measurement, failover policy, and output formatting into distinct units.
   - **OCP:** The selection engine must be open to new routing/failover policies without modifying existing ones.
   - **LSP:** Connection/pool abstractions must be substitutable.
   - **ISP:** Keep the scope interface small and cohesive.
   - **DIP:** Core logic depends on abstractions (a pool selector, a lag source), not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public entry point should be an elegant block/scope construct idiomatic to the target language, hiding pool-selection internals.
   - **Resilience:** Edge cases (lag exceeded, lag unknown, no replicas available, invalid options) must be modeled as explicit error categories rather than generic faults.

---

## Core Features

### Feature 1: Default Primary Routing

**As a developer**, I want reads to go to the primary by default, so I can adopt the library without changing existing behavior until I opt in.

**Expected Behavior / Usage:**

When default-distribution mode is off and no distribution scope is active, every read is served by the primary node. The adapter emits one `read=<node>` line per read, where `<node>` is `primary` or `replica`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_default_routing.json`

```json
{
    "description": "With no distribution scope active and default mode off, a read is served by the primary database.",
    "cases": [
        { "input": { "program": [ { "op": "read" } ] }, "expected_output": "read=primary\n" }
    ]
}
```

---

### Feature 2: Scoped Read Distribution

**As a developer**, I want to wrap a block of work in a distribution scope, so that reads inside it use a replica while writes and transactions stay on the primary.

**Expected Behavior / Usage:**

*2.1 Reads inside a scope use the replica — writes inside the scope do not pin later reads*

A read outside any scope uses the primary. Inside a distribution scope, reads use the replica. A write performed inside a plain scope does NOT pin subsequent reads back to the primary; later reads in the same scope still use the replica. Each read emits `read=primary` or `read=replica`; a `write` step produces no output.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_block_reads_replica.json`

```json
{
    "description": "A read executed outside any scope uses the primary; inside a distribution scope reads use the replica, and a write performed inside the scope does not pin later reads back to the primary.",
    "cases": [
        {
            "input": { "program": [
                { "op": "write" },
                { "op": "read" },
                { "op": "scope", "options": {}, "body": [ { "op": "read" }, { "op": "write" }, { "op": "read" } ] }
            ] },
            "expected_output": "read=primary\nread=replica\nread=replica\n"
        }
    ]
}
```

*2.2 Transactions inside a scope use the primary*

A read wrapped in a transaction, even inside a distribution scope, is served by the primary, because transactional work must run on the writable node.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_transaction_primary.json`

```json
{
    "description": "A read wrapped in a transaction inside a distribution scope is served by the primary, because transactional work must stay on the writable node.",
    "cases": [
        {
            "input": { "program": [
                { "op": "scope", "options": {}, "body": [ { "op": "transaction", "body": [ { "op": "read" } ] } ] }
            ] },
            "expected_output": "read=primary\n"
        }
    ]
}
```

---

### Feature 3: Default-Distribution Mode

**As a developer**, I want a global switch that distributes reads everywhere by default, so I can offload the primary across the whole application while keeping write-consistency guarantees.

**Expected Behavior / Usage:**

*3.1 Reads use the replica by default; a write pins later reads to the primary*

When default-distribution mode is on, a plain read (outside any explicit scope) uses the replica. After a write, subsequent reads are pinned to the primary so a caller never reads its own write from a stale replica.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_by_default_sticky.json`

```json
{
    "description": "When default-distribution mode is on, a plain read uses the replica; after a write, subsequent reads are pinned to the primary for consistency.",
    "cases": [
        {
            "input": { "by_default": true, "program": [ { "op": "read" }, { "op": "write" }, { "op": "read" } ] },
            "expected_output": "read=replica\nread=primary\n"
        }
    ]
}
```

*3.2 A scope inside default mode keeps reads on the replica; pinning resumes after the scope*

With default-distribution mode on, reads inside an explicit distribution scope stay on the replica even after a write within that scope. Once the scope exits, the earlier write pins the next plain read to the primary.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_block_inside_default.json`

```json
{
    "description": "With default-distribution mode on, reads inside a distribution scope stay on the replica even after a write within the scope; once the scope exits, an earlier write pins the next read to the primary.",
    "cases": [
        {
            "input": { "by_default": true, "program": [
                { "op": "scope", "options": {}, "body": [ { "op": "read" }, { "op": "write" }, { "op": "read" } ] },
                { "op": "read" }
            ] },
            "expected_output": "read=replica\nread=replica\nread=primary\n"
        }
    ]
}
```

*3.3 Forcing the primary inside default mode*

With default-distribution mode on, opening a scope that forces the primary (`"primary": true`) routes that scope's reads back to the primary.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_primary_override.json`

```json
{
    "description": "With default-distribution mode on, opening a scope that forces the primary routes its reads back to the primary.",
    "cases": [
        {
            "input": { "by_default": true, "program": [
                { "op": "scope", "options": { "primary": true }, "body": [ { "op": "read" } ] }
            ] },
            "expected_output": "read=primary\n"
        }
    ]
}
```

---

### Feature 4: Replica-Lag Guard

**As a developer**, I want to refuse (or down-route) replica reads when replication lag is too high, so I never serve dangerously stale data.

**Expected Behavior / Usage:**

A scope may declare a maximum acceptable lag in seconds (`"max_lag": N`). Before running, the library measures the replica lag and compares it to the threshold. The threshold may also be configured globally via `default_options`. In these contracts the measured lag is supplied by the scenario via the `"lag"` field (a number, or `null` when the lag cannot be determined); when `"lag"` is absent, the live value is measured.

*4.1 Lag over threshold raises*

When the measured lag exceeds the threshold, opening the scope raises a lag-exceeded error before any read runs. The error renders as `error=too_much_lag` plus a `message=` line stating the threshold. The same outcome holds whether the threshold is supplied per scope or via global defaults.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_max_lag_exceeded.json`

```json
{
    "description": "When a maximum replica-lag threshold is set and the measured lag exceeds it, opening the scope raises a lag-exceeded error before any read runs. The threshold may be supplied per scope or via global defaults.",
    "cases": [
        {
            "input": { "lag": 2, "program": [ { "op": "scope", "options": { "max_lag": 1 }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "error=too_much_lag\nmessage=[the default message for replica lag errors on the tree] 1 seconds\n"
        }
    ]
}
```

*4.2 Lag at or below threshold proceeds on the replica*

When the measured lag is at or below the threshold (whether supplied low or measured live), reads proceed on the replica with no error.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_max_lag_under.json`

```json
{
    "description": "When a maximum replica-lag threshold is set and the measured lag is at or below it (whether stubbed low or measured live), reads proceed on the replica.",
    "cases": [
        {
            "input": { "lag": 0, "program": [ { "op": "scope", "options": { "max_lag": 1 }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "read=replica\n"
        }
    ]
}
```

*4.3 Unknown lag raises and names the connection*

When the replica lag cannot be determined (`"lag": null`) and a threshold is set, opening the scope raises a lag-exceeded error whose message states the lag is unknown on the named connection (the default connection renders as `default`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_lag_unknown.json`

```json
{
    "description": "When the replica lag cannot be determined (unknown/nil) and a lag threshold is set, opening the scope raises a lag-exceeded error naming the connection.",
    "cases": [
        {
            "input": { "lag": null, "program": [ { "op": "scope", "options": { "max_lag": 1 }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "error=too_much_lag\nmessage=Replica lag is nil on default\n"
        }
    ]
}
```

*4.4 Lag failover routes to the primary instead of raising*

When lag failover is enabled (`"lag_failover": true`), exceeding the threshold — or being unable to measure lag — does not raise. Instead a message is logged (rendered as a `log=` line) and reads fall back to the primary for that scope.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_lag_failover.json`

```json
{
    "description": "When lag failover is enabled, exceeding the lag threshold (or being unable to measure lag) does not raise; instead a message is logged and reads fall back to the primary.",
    "cases": [
        {
            "input": { "lag": 2, "program": [ { "op": "scope", "options": { "max_lag": 1, "lag_failover": true }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "log=[the default message for replica lag errors on the tree] 1 seconds. Falling back to master pool.\nread=primary\n"
        },
        {
            "input": { "lag": null, "program": [ { "op": "scope", "options": { "max_lag": 1, "lag_failover": true }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "log=Replica lag is nil on default. Falling back to master pool.\nread=primary\n"
        }
    ]
}
```

*4.5 Lag checked against a named connection*

The lag check may be targeted at a specific named connection (`"lag_on": "<name>"`, or a list of names). When that connection's lag exceeds the threshold, the raised error names the connection.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_lag_on_connection.json`

```json
{
    "description": "When the lag threshold is checked against a named connection (supplied singly or as a list) and that connection's lag exceeds the threshold, the raised error names that connection.",
    "cases": [
        {
            "input": { "lag": 2, "program": [ { "op": "scope", "options": { "max_lag": 1, "lag_on": "User" }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "error=too_much_lag\nmessage=[the default message for replica lag errors on the tree] 1 seconds on User connection\n"
        }
    ]
}
```

---

### Feature 5: Replication-Lag Reference Value

**As a developer**, I want to read the current replication lag as a plain number, so I can monitor or branch on it.

**Expected Behavior / Usage:**

A reference call returns the current replica lag in seconds as a numeric value, rendered as `replication_lag=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_replication_lag.json`

```json
{
    "description": "The current replica replication lag can be read as a numeric value.",
    "cases": [
        { "input": { "lag": 2, "program": [ { "op": "replication_lag" } ] }, "expected_output": "replication_lag=2\n" }
    ]
}
```

---

### Feature 6: Replica Availability & Failover

**As a developer**, I want a clear policy for when no replicas are available, so I can choose between graceful failover and an explicit error.

**Expected Behavior / Usage:**

A scenario can mark all replicas as unavailable via `"blacklist_replicas": true`.

*6.1 No replicas available falls back to the primary*

By default, when no replicas are available, a distribution scope logs the situation (a `log=` line) and falls back to the primary. This holds whether or not default-distribution mode is on.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_failover_to_primary.json`

```json
{
    "description": "When no replicas are available, a distribution scope logs the situation and falls back to the primary. This holds whether or not default-distribution mode is on.",
    "cases": [
        {
            "input": { "blacklist_replicas": true, "program": [ { "op": "scope", "options": {}, "body": [ { "op": "read" } ] } ] },
            "expected_output": "log=No replicas available. Falling back to master pool.\nread=primary\n"
        }
    ]
}
```

*6.2 Failover disabled raises*

When failover is disabled (`"failover": false`) and no replicas are available, opening the scope raises a no-replicas-available error. This holds whether or not default-distribution mode is on.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_failover_disabled.json`

```json
{
    "description": "When no replicas are available and failover is disabled, opening the scope raises a no-replicas-available error. This holds whether or not default-distribution mode is on.",
    "cases": [
        {
            "input": { "blacklist_replicas": true, "program": [ { "op": "scope", "options": { "failover": false }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "error=no_replicas_available\nmessage=No replicas available\n"
        }
    ]
}
```

---

### Feature 7: Forced Replica Reads

**As a developer**, I want to force a scope's reads onto the replica even when distribution is otherwise off, so I can opt specific work into replica reads.

**Expected Behavior / Usage:**

*7.1 Forcing the replica routes reads to the replica*

Forcing replica use for a scope (`"replica": true`) routes its reads to the replica even when default-distribution mode is off; reads outside the scope still use the primary. A SQL comment prefix on a query (`"prefix"`) does not change routing.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_force_replica.json`

```json
{
    "description": "Forcing replica use for a scope routes its reads to the replica even when default-distribution mode is off; reads outside the scope still use the primary. SQL comment prefixes do not change routing.",
    "cases": [
        {
            "input": { "program": [
                { "op": "read", "prefix": "/*hi*/" },
                { "op": "scope", "options": { "replica": true }, "body": [ { "op": "read", "prefix": "/*hi*/" } ] }
            ] },
            "expected_output": "read=primary\nread=replica\n"
        }
    ]
}
```

*7.2 Forced replica with no replicas available falls back to the primary*

When the replica is forced but no replicas are available, the library logs the situation and falls back to the primary.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_force_replica_failover.json`

```json
{
    "description": "Forcing replica use when no replicas are available logs the situation and falls back to the primary.",
    "cases": [
        {
            "input": { "blacklist_replicas": true, "program": [ { "op": "scope", "options": { "replica": true }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "log=No replicas available. Falling back to master pool.\nread=primary\n"
        }
    ]
}
```

*7.3 Forced replica with failover disabled raises*

When the replica is forced, failover is disabled, and no replicas are available, opening the scope raises a no-replicas-available error.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_force_replica_failover_disabled.json`

```json
{
    "description": "Forcing replica use when no replicas are available and failover is disabled raises a no-replicas-available error.",
    "cases": [
        {
            "input": { "blacklist_replicas": true, "program": [ { "op": "scope", "options": { "replica": true, "failover": false }, "body": [ { "op": "read" } ] } ] },
            "expected_output": "error=no_replicas_available\nmessage=No replicas available\n"
        }
    ]
}
```

---

### Feature 8: Background-Job Integration

**As a developer**, I want background jobs to participate in read distribution, so scheduled work also offloads reads to replicas.

**Expected Behavior / Usage:**

A background job can declare that its work runs inside a distribution scope. The adapter runs the job and emits `job=<node>` for the node that served the job's read.

*8.1 A distribution-scoped job reads from the replica*

A job declared to distribute its reads (`"role": "read_only"`) runs its read on the replica.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_job_distribution.json`

```json
{
    "description": "A background job declared to distribute its reads runs its reads on the replica.",
    "cases": [
        { "input": { "program": [ { "op": "job", "role": "read_only" } ] }, "expected_output": "job=replica\n" }
    ]
}
```

*8.2 Under default mode, a read-then-write job reads from the replica on every run*

With default-distribution mode on, a job that both reads and writes (`"role": "read_write"`) runs its read on the replica on each invocation, because the routing context is reset between job runs (so a prior run's write does not pin the next run).

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_job_by_default.json`

```json
{
    "description": "With default-distribution mode on, a background job that both reads and writes runs its read on the replica on each invocation, because job context is reset between runs.",
    "cases": [
        {
            "input": { "by_default": true, "program": [ { "op": "job", "role": "read_write" }, { "op": "job", "role": "read_write" } ] },
            "expected_output": "job=replica\njob=replica\n"
        }
    ]
}
```

---

### Feature 9: Lazy-Query Warning

**As a developer**, I want a warning when a scope returns an unexecuted query, so I learn to force execution inside the scope instead of accidentally running it on the primary later.

**Expected Behavior / Usage:**

When a distribution scope returns a query object that has not been executed yet (a deferred/lazy query), the library logs an advisory message telling the caller to force execution inside the scope. The adapter renders it as a `log=` line; no read node is emitted because the query never ran.

**Test Cases:** `rcb_tests/public_test_cases/feature9_lazy_relation_warning.json`

```json
{
    "description": "When a distribution scope returns a query object that has not been executed yet, a warning is logged advising the caller to force execution inside the scope.",
    "cases": [
        {
            "input": { "program": [ { "op": "scope", "options": {}, "body": [ { "op": "lazy_read" } ] } ] },
            "expected_output": "log=Call `to_a` inside block to execute query on replica\n"
        }
    ]
}
```

---

### Feature 10: Input Validation

**As a developer**, I want misuse of the scope entry point to fail loudly with a clear category, so mistakes surface immediately.

**Expected Behavior / Usage:**

*10.1 Opening a scope without a body of work*

Invoking the scope entry point without a block/body raises a missing-block error, rendered as `error=[a specific error sentinel that triggers an abort]` with a `message=` line.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_[a specific error sentinel that triggers an abort].json`

```json
{
    "description": "Invoking the distribution entry point without a block raises a missing-block error.",
    "cases": [
        { "input": { "program": [ { "op": "scope_without_block" } ] }, "expected_output": "error=[a specific error sentinel that triggers an abort]\nmessage=Missing block\n" }
    ]
}
```

*10.2 Opening a scope with unrecognized options*

Invoking the scope entry point with options it does not recognize raises an unknown-keywords error listing the offending keys in their given order, rendered as `error=[the category of error for invalid option keys]` with a `message=` line.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_[the category of error for invalid option keys].json`

```json
{
    "description": "Invoking the distribution entry point with options it does not recognize raises an unknown-keywords error listing the offending keys in order.",
    "cases": [
        {
            "input": { "program": [ { "op": "scope", "options": { "hi": 1, "bye": 2 }, "body": [] } ] },
            "expected_output": "error=[the category of error for invalid option keys]\nmessage=Unknown keywords: hi, bye\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the routing rules above (scope/context state, pool selection, lag guard, failover policy, background-job integration, logging). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint — a multi-file tree separating core concerns from the execution adapter.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON scenario from stdin, drives the core routing against a primary/replica pair, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. The wire contract is line-oriented: `read=<node>`, `job=<node>`, `replication_lag=<value>`, `log=<message>`, and for failures `error=<category>` followed by `message=<text>`. Errors MUST be normalized to language-neutral categories (`too_much_lag`, `no_replicas_available`, `[a specific error sentinel that triggers an abort]`, `[the category of error for invalid option keys]`) with no host-language exception class names or runtime artifacts in stdout. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_default_routing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_default_routing@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- rephrase as a vague internal reference that requires grepping the codebase
- rephrase as a vague internal reference that requires grepping the codebase
