## Product Requirement Document

# Reactive Resource Pool - Asynchronous Borrowing and Lifecycle Management

## Project Goal

Build a reactive resource pooling library that allows developers to allocate, borrow, reuse, invalidate, and dispose scarce asynchronous resources without writing custom queueing, capacity accounting, timeout, and cleanup logic.

---

## Background & Problem

Without this library, developers are forced to manually track resource capacity, pending borrowers, idle resources, lifecycle callbacks, and shutdown state. This leads to duplicated concurrency code, inconsistent cleanup behavior, subtle leaks, and fragile error handling.

With this library, developers configure allocation limits, reuse order, lifecycle handlers, and eviction rules, then interact with a pool through asynchronous borrow and release operations while the pool maintains observable metrics and deterministic lifecycle behavior.

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

### Feature 1: Capacity Permit Accounting

**As a developer**, I want pool capacity to be tracked by a reusable permit policy, so I can enforce allocation limits consistently before resources are created.

**Expected Behavior / Usage:**

*1.1 Bounded Capacity Permits — finite capacity accounting with minimum warmup semantics*

A bounded permit policy is configured with a minimum and maximum capacity. It initially reports the maximum as available. A positive or zero request grants no more than remaining capacity; while currently granted capacity is below the configured minimum, a request can be increased to satisfy the minimum warmup target. Negative requests grant zero. Returning capacity increases the available count, but returning more capacity than the configured maximum allows must be rejected. Rejection is rendered as `error=too_many_permits_returned` with the returned amount on a separate line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_bounded_capacity_permits.json`

```json
{
  "description": "A bounded capacity controller grants requested capacity up to its configured maximum, performs minimum-size warmup grants when below the minimum, reports remaining capacity after each operation, and rejects returns that would exceed the maximum.",
  "cases": [
    {
      "input": {
        "scenario": "size_strategy_sequence",
        "min": 0,
        "max": 1,
        "operations": [
          {
            "op": "get",
            "value": [a specific out-of-range error code]
          },
          {
            "op": "get",
            "value": 1
          }
        ]
      },
      "expected_output": "initial_permits=1\n[a specific out-of-range error code]\n[a specific out-of-range error code]\n[a specific out-of-range error code]=0\n[a specific out-of-range error code]\n"
    }
  ]
}
```

*1.2 Unbounded Capacity Permits — unlimited capacity accounting*

An unbounded permit policy always reports an effectively unlimited remaining capacity value. Positive requests are granted exactly as requested, non-positive requests grant zero, and returned capacity is accepted without reducing the reported availability.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_unbounded_capacity_permits.json`

```json
{
  "description": "An unbounded capacity controller always reports effectively unlimited remaining capacity, grants any positive requested amount, grants nothing for non-positive requests, and accepts returned capacity without reducing the reported availability.",
  "cases": [
    {
      "input": {
        "scenario": "unbounded_strategy_sequence",
        "operations": [
          {
            "op": "get",
            "value": [a specific out-of-range error code]
          },
          {
            "op": "get",
            "value": [a specific out-of-range error code]0
          }
        ]
      },
      "expected_output": "initial_permits=2147483647\n[a specific out-of-range error code]00\npermits=2147483647\nget([a specific out-of-range error code]0)=[a specific out-of-range error code]0\npermits=2147483647\n"
    }
  ]
}
```

---

### Feature 2: Allocation Inputs and Eviction Predicates

**As a developer**, I want allocation and eviction rules to be expressed declaratively, so I can control resource creation and reuse without duplicating lifecycle checks.

**Expected Behavior / Usage:**

*2.1 Idle-Time Eviction — threshold-based reuse eligibility*

An idle-time rule receives a time-to-live threshold and a list of resource idle durations. Each resource is marked for eviction when its idle duration is equal to or greater than the threshold; shorter idle durations remain reusable. The output lists each resource index, idle duration, and boolean eviction decision.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_idle_time_eviction.json`

```json
{
  "description": "An idle-time eviction rule marks a resource for eviction when its idle duration is equal to or greater than the configured time-to-live, while shorter idle durations remain reusable.",
  "cases": [
    {
      "input": {
        "scenario": "idle_ttl_predicate",
        "ttl_ms": 3000,
        "idle_ms": [
          4000,
          2000,
          3000
        ]
      },
      "expected_output": "resource[0].idle_ms=4000\nresource[0].evict=true\nresource[1].idle_ms=2000\nresource[1].evict=false\nresource[2].idle_ms=3000\nresource[2].evict=true\n"
    }
  ]
}
```

*2.2 Source Stream Allocation — one resource per allocation request*

A configured allocation source can be single-valued or multi-valued. For one allocation request, the pool consumes exactly one resource value. If the source can emit more than one value, later values are not consumed for that request. The output reports the allocated value and how many source invocations occurred.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_publisher_source_allocation.json`

```json
{
  "description": "A source stream used for allocation yields exactly one resource value to an allocation request; a multi-value source is cancelled after the first emitted value so later values are not consumed.",
  "cases": [
    {
      "input": {
        "scenario": "publisher_source_single",
        "source": "single"
      },
      "expected_output": "allocated_value=1\nsource_invocations=1\n"
    }
  ]
}
```

---

### Feature 3: Pool Borrowing, Reuse, Limits, Shutdown, and Context

**As a developer**, I want a pool to manage asynchronous borrowing and lifecycle transitions, so I can safely reuse scarce resources under concurrency and shutdown pressure.

**Expected Behavior / Usage:**

*3.1 Borrow/Release Metrics — observable resource counts*

A pool exposes allocated, idle, and borrowed counts. Before any borrow, all counts are zero for a lazily allocating pool. Acquiring a resource increments allocated and borrowed counts. Releasing the resource leaves the allocation count unchanged, increments idle count, and decrements borrowed count. The output includes the borrowed resource value and all metric transitions.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_pool_acquire_release_metrics.json`

```json
{
  "description": "A resource pool exposes externally visible counts for allocated, idle, and borrowed resources; acquiring a resource moves it into the borrowed count, and releasing it moves it into the idle count without changing total allocation.",
  "cases": [
    {
      "input": {
        "scenario": "pool_acquire_release_metrics",
        "reuse_order": "lru"
      },
      "expected_output": "before.allocated=0\nbefore.idle=0\nbefore.acquired=0\nacquired.value=1\nafter_acquire.allocated=1\nafter_acquire.idle=0\nafter_acquire.acquired=1\nafter_release.allocated=1\nafter_release.idle=1\nafter_release.acquired=0\n"
    }
  ]
}
```

*3.2 Minimum Warmup on First Borrow — lazy allocation to minimum size*

A pool configured with a positive minimum does not allocate during construction. The first borrow triggers allocation up to the minimum size: one resource is borrowed and the remaining newly allocated resources become idle. A second borrow consumes one idle resource without increasing total allocation. The output reports construction state, post-borrow allocation and idle counts, and total allocation-source invocations.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_minimum_warmup_on_first_acquire.json`

```json
{
  "description": "A pool configured with a positive minimum does not allocate at construction time; the first borrow warms up to the minimum, leaving all non-borrowed warmed resources idle, and later borrows consume those idle resources without extra allocation.",
  "cases": [
    {
      "input": {
        "scenario": "pool_warmup_minimum",
        "reuse_order": "lru",
        "min": 4,
        "max": 8
      },
      "expected_output": "constructor.allocated=0\nafter_first.allocated=4\nafter_first.idle=3\nafter_second.allocated=4\nafter_second.idle=2\nallocation_count=4\n"
    }
  ]
}
```

*3.3 Idle Resource Reuse Order — oldest-idle versus newest-idle selection*

When several resources are idle, the configured reuse order determines which idle resource is borrowed next. Least-recent reuse returns the oldest idle resource first. Most-recent reuse returns the newest idle resource first. The output reports idle count after release, the first two resource values borrowed again, and the remaining idle count.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_idle_resource_reuse_order.json`

```json
{
  "description": "When multiple resources are idle, the configured reuse order determines which idle resource is borrowed first: oldest idle first for least-recent reuse, newest idle first for most-recent reuse.",
  "cases": [
    {
      "input": {
        "scenario": "idle_reuse_order",
        "reuse_order": "mru"
      },
      "expected_output": "idle_after_release=3\nfirst_reacquire=3\nsecond_reacquire=1\nidle_after_reacquire=1\n"
    }
  ]
}
```

*3.4 Pending Acquire Limits — bounded waiting queue behavior*

When no idle resources exist and the pool has reached its maximum allocation, a pending-acquire limit controls whether new borrow requests can wait. If no pending requests are allowed, the next request fails immediately with `error=pending_acquire_limit` and `reason=no_pending_allowed`. If one pending request is allowed, that request waits and the following request fails with `reason=queue_limit_reached`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_pending_acquire_limits.json`

```json
{
  "description": "When a pool has no idle resources and has reached its allocation maximum, a pending-acquire limit controls whether additional borrow requests may wait; if the limit is zero or already reached, the request fails with a neutral pending-limit error.",
  "cases": [
    {
      "input": {
        "scenario": "pending_acquire_limit",
        "reuse_order": "lru",
        "max_pending": 0
      },
      "expected_output": "warmup=1\nfirst=1\nsecond=2\nerror=pending_acquire_limit\nreason=no_pending_allowed\n"
    },
    {
      "input": {
        "scenario": "pending_acquire_limit",
        "reuse_order": "mru",
        "max_pending": 1
      },
      "expected_output": "warmup=1\nfirst=1\nsecond=2\nthird=pending\npending=1\nerror=pending_acquire_limit\nreason=queue_limit_reached\n"
    }
  ]
}
```

*3.5 Disposed Pool Rejects Borrow — shutdown-state enforcement*

A pool exposes whether it is disposed. After disposal, the disposed state is true and a later borrow request must fail with the neutral error `error=pool_shutdown`; it must not allocate or return a resource.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_disposed_pool_rejects_acquire.json`

```json
{
  "description": "Once a pool has been disposed, its disposed state becomes observable and a later borrow request fails with a neutral shutdown error instead of allocating or returning a resource.",
  "cases": [
    {
      "input": {
        "scenario": "disposed_pool_acquire",
        "reuse_order": "lru"
      },
      "expected_output": "before_dispose.disposed=false\nafter_dispose.disposed=true\nerror=pool_shutdown\n"
    }
  ]
}
```

*3.6 Release/Invalidate Idempotency — first completion action wins*

A borrowed resource can be completed only once. If release happens first, the resource becomes idle and the release handler count increments once; a later invalidation does not change metrics or destroy count. If invalidation happens first, allocation drops to zero and the destroy handler count increments once; a later release does not change metrics or release count.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_release_invalidate_idempotency.json`

```json
{
  "description": "A borrowed resource can be completed only once: after release, later invalidation is ignored; after invalidation, later release is ignored. Metrics and lifecycle handler counts reflect only the first completion action.",
  "cases": [
    {
      "input": {
        "scenario": "release_invalidate_idempotency",
        "reuse_order": "lru",
        "first_action": "release"
      },
      "expected_output": "before.allocated=1\nbefore.idle=0\nbefore.acquired=1\nafter.allocated=1\nafter.idle=1\nafter.acquired=0\nrelease_count=1\ndestroy_count=0\n"
    }
  ]
}
```

*3.7 Contextual Allocation — per-request data applies only to new resources*

When allocation receives request context, newly created resources are based on the context from the request that caused their creation. Later borrows that reuse idle resources must return the existing resource value rather than replacing it with the later request context. The output lists the values seen by four borrows.

**Test Cases:** `rcb_tests/public_test_cases/feature3_7_contextual_allocation.json`

```json
{
  "description": "Per-request contextual data is visible to allocation when a new resource is created, while reusing an idle resource preserves the original resource value rather than replacing it with the later request context.",
  "cases": [
    {
      "input": {
        "scenario": "contextual_allocation",
        "reuse_order": "lru"
      },
      "expected_output": "first=1\nsecond=2\nthird=1\nfourth=2\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_bounded_capacity_permits.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_bounded_capacity_permits@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
